"""Pinned process groups with per-process timing.

Linux: each child is pinned with sched_setaffinity before exec (no taskset
launch overhead) and reaped individually with wait4.
Windows: each child is created suspended, pinned, placed in a limiting
Job Object and resumed (backend.platform_win); WaitForMultipleObjects
reports each exit.

Either way every task gets its own wall time and CPU time even when
several run together. Background processes (stressor kernels) are killed
as soon as all foreground processes finish.
"""

from dataclasses import dataclass
import os
import subprocess
import tempfile
import time

from backend import config

WINDOWS = os.name == "nt"

if WINDOWS:
    from backend import platform_win
else:
    import resource
    import select
    import signal


@dataclass
class ProcessSpec:
    key: str
    argv: list
    cpus: tuple
    background: bool = False


def _child_setup(cpus):
    def setup():
        os.sched_setaffinity(0, set(cpus))
        resource.setrlimit(
            resource.RLIMIT_AS,
            (config.MAX_MEMORY_BYTES, config.MAX_MEMORY_BYTES),
        )
        resource.setrlimit(
            resource.RLIMIT_CPU,
            (config.CPU_LIMIT_SECONDS, config.CPU_LIMIT_SECONDS + 1),
        )
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    return setup


def _reap(key, process, launched, results):
    pid, status, usage = os.wait4(process.pid, os.WNOHANG)

    if pid == 0:
        return False

    ended = time.perf_counter()
    process.returncode = os.waitstatus_to_exitcode(status)
    results[key] = {
        "wallSeconds": ended - launched[key],
        "endTime": ended,
        "userSeconds": usage.ru_utime,
        "systemSeconds": usage.ru_stime,
        "exitCode": process.returncode,
    }
    return True


def _wait_foreground(processes, pending, launched, results, deadline):
    """Reap foreground processes; return True on timeout."""

    pidfds = {}

    if hasattr(os, "pidfd_open"):
        for key in pending:
            try:
                pidfds[os.pidfd_open(processes[key].pid)] = key
            except OSError:
                pidfds = {}
                break

    try:
        while pending:
            remaining = deadline - time.perf_counter()

            if remaining <= 0:
                return True

            if pidfds:
                ready, _, _ = select.select(
                    list(pidfds), [], [], remaining
                )
                for fd in ready:
                    key = pidfds[fd]
                    if _reap(key, processes[key], launched, results):
                        pending.discard(key)
                        del pidfds[fd]
                        os.close(fd)
            else:
                time.sleep(0.0005)
                for key in list(pending):
                    if _reap(key, processes[key], launched, results):
                        pending.discard(key)

        return False

    finally:
        for fd in pidfds:
            os.close(fd)


def _kill(process):
    if process.returncode is not None:
        return

    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass

    try:
        os.waitpid(process.pid, 0)
    except ChildProcessError:
        pass

    process.returncode = -signal.SIGKILL


def _wait_foreground_windows(processes, pending, launched, results, deadline):
    """Windows equivalent of _wait_foreground; return True on timeout."""

    while pending:
        remaining = deadline - time.perf_counter()

        if remaining <= 0:
            return True

        keys = sorted(pending)
        index = platform_win.wait_any([processes[k] for k in keys], remaining)

        if index is None:
            return True

        ended = time.perf_counter()
        key = keys[index]
        process = processes[key]
        process.wait()
        user, system = platform_win.process_times(process)
        results[key] = {
            "wallSeconds": ended - launched[key],
            "endTime": ended,
            "userSeconds": user,
            "systemSeconds": system,
            "exitCode": process.returncode,
        }
        pending.discard(key)

    return False


def _start(spec, stdout_file, stderr_file, cwd):
    argv = [str(arg) for arg in spec.argv]

    if WINDOWS:
        return platform_win.start_pinned(
            argv, spec.cpus, config.MAX_MEMORY_BYTES, config.CPU_LIMIT_SECONDS,
            stdin=subprocess.DEVNULL, stdout=stdout_file, stderr=stderr_file,
            cwd=str(cwd) if cwd else None,
        )

    return subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=stdout_file,
        stderr=stderr_file,
        cwd=str(cwd) if cwd else None,
        start_new_session=True,
        preexec_fn=_child_setup(spec.cpus),
    )


def _read(stream):
    stream.seek(0)
    data = stream.read(config.MAX_OUTPUT_BYTES + 1)
    return data[:config.MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")


def run_group(specs, timeout=None, cwd=None):
    """Run processes concurrently; return per-key results and makespan."""

    timeout = timeout or config.RUN_TIMEOUT_SECONDS
    processes = {}
    streams = {}
    launched = {}
    results = {}
    timed_out = False
    started = time.perf_counter()

    try:
        for spec in specs:
            stdout_file = tempfile.TemporaryFile()
            stderr_file = tempfile.TemporaryFile()
            streams[spec.key] = (stdout_file, stderr_file)
            launched[spec.key] = time.perf_counter()
            processes[spec.key] = _start(spec, stdout_file, stderr_file, cwd)

        pending = {spec.key for spec in specs if not spec.background}
        wait = _wait_foreground_windows if WINDOWS else _wait_foreground
        timed_out = wait(processes, pending, launched, results, started + timeout)

    finally:
        for process in processes.values():
            if WINDOWS:
                platform_win.kill(process)
            else:
                _kill(process)

    foreground = [s.key for s in specs if not s.background]
    makespan = (
        max(results[k]["endTime"] for k in foreground) - started
        if foreground and not timed_out
        else None
    )

    for spec in specs:
        stdout_file, stderr_file = streams[spec.key]
        entry = results.setdefault(spec.key, {"exitCode": None})
        entry["stdout"] = _read(stdout_file).strip()
        entry["stderr"] = _read(stderr_file).strip()
        entry["cpus"] = list(spec.cpus)
        entry["background"] = spec.background
        entry.pop("endTime", None)
        stdout_file.close()
        stderr_file.close()

    return {
        "makespanSeconds": makespan,
        "timedOut": timed_out,
        "processes": results,
    }
