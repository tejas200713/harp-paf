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


def _kill(process):
    if WINDOWS:
        platform_win.kill(process)
        return

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


def _read(stream):
    stream.seek(0)
    data = stream.read(config.MAX_OUTPUT_BYTES + 1)
    return data[:config.MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")


class ProcessGroup:
    """Processes started one by one; wait_any() reports the next to finish.

    Used directly by the dynamic SMT scheduler and, through run_group, for
    fixed groups. Results carry wall time from each process's own launch,
    CPU time, exit code, and (after close) its captured output.
    """

    def __init__(self, cwd=None):
        self.cwd = cwd
        self.started = time.perf_counter()
        self.specs = {}
        self.processes = {}
        self.streams = {}
        self.launched = {}
        self.results = {}
        self.pending = set()
        self._pidfds = {}

    def start(self, spec):
        stdout_file = tempfile.TemporaryFile()
        stderr_file = tempfile.TemporaryFile()
        self.specs[spec.key] = spec
        self.streams[spec.key] = (stdout_file, stderr_file)
        self.launched[spec.key] = time.perf_counter()
        process = _start(spec, stdout_file, stderr_file, self.cwd)
        self.processes[spec.key] = process

        if not spec.background:
            self.pending.add(spec.key)
            if not WINDOWS and hasattr(os, "pidfd_open"):
                try:
                    self._pidfds[os.pidfd_open(process.pid)] = spec.key
                except OSError:
                    pass

        return self.launched[spec.key]

    def _record(self, key, ended, user, system):
        self.results[key] = {
            "wallSeconds": ended - self.launched[key],
            "startTime": self.launched[key] - self.started,
            "endTime": ended - self.started,
            "userSeconds": user,
            "systemSeconds": system,
            "exitCode": self.processes[key].returncode,
        }
        self.pending.discard(key)

    def _reap_linux(self, key):
        process = self.processes[key]
        pid, status, usage = os.wait4(process.pid, os.WNOHANG)

        if pid == 0:
            return False

        process.returncode = os.waitstatus_to_exitcode(status)
        self._record(key, time.perf_counter(), usage.ru_utime, usage.ru_stime)
        return True

    def wait_any(self, deadline):
        """Key of the next foreground process to finish, or None on timeout."""

        while self.pending:
            remaining = deadline - time.perf_counter()

            if remaining <= 0:
                return None

            if WINDOWS:
                keys = sorted(self.pending)
                index = platform_win.wait_any(
                    [self.processes[k] for k in keys], remaining
                )
                if index is None:
                    return None
                ended = time.perf_counter()
                key = keys[index]
                self.processes[key].wait()
                user, system = platform_win.process_times(self.processes[key])
                self._record(key, ended, user, system)
                return key

            fds = {fd: k for fd, k in self._pidfds.items() if k in self.pending}

            if fds and len(fds) == len(self.pending):
                ready, _, _ = select.select(list(fds), [], [], remaining)
                for fd in ready:
                    key = fds[fd]
                    if self._reap_linux(key):
                        os.close(fd)
                        del self._pidfds[fd]
                        return key
            else:
                time.sleep(0.0005)
                for key in sorted(self.pending):
                    if self._reap_linux(key):
                        return key

        return None

    def close(self):
        """Kill what is still running and collect outputs; return results."""

        for process in self.processes.values():
            _kill(process)

        for fd in self._pidfds:
            os.close(fd)
        self._pidfds = {}

        for key, spec in self.specs.items():
            stdout_file, stderr_file = self.streams[key]
            entry = self.results.setdefault(key, {"exitCode": None})
            entry["stdout"] = _read(stdout_file).strip()
            entry["stderr"] = _read(stderr_file).strip()
            entry["cpus"] = list(spec.cpus)
            entry["background"] = spec.background
            stdout_file.close()
            stderr_file.close()

        return self.results


def run_group(specs, timeout=None, cwd=None):
    """Run processes concurrently; return per-key results and makespan."""

    timeout = timeout or config.RUN_TIMEOUT_SECONDS
    group = ProcessGroup(cwd)
    timed_out = False

    try:
        for spec in specs:
            group.start(spec)

        deadline = group.started + timeout

        while group.pending:
            if group.wait_any(deadline) is None:
                timed_out = True
                break

    finally:
        results = group.close()

    foreground = [s.key for s in specs if not s.background]
    makespan = (
        max(results[k]["endTime"] for k in foreground)
        if foreground and not timed_out
        else None
    )

    for entry in results.values():
        entry.pop("startTime", None)
        entry.pop("endTime", None)

    return {
        "makespanSeconds": makespan,
        "timedOut": timed_out,
        "processes": results,
    }
