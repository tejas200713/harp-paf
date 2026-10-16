from pathlib import Path
import os
import resource
import selectors
import signal
import subprocess
import time

from backend import config


MAX_OUTPUT = 10000
MAX_MEMORY = config.MAX_MEMORY_BYTES


def _set_limits():
    resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY, MAX_MEMORY))
    resource.setrlimit(
        resource.RLIMIT_CPU,
        (config.CPU_LIMIT_SECONDS, config.CPU_LIMIT_SECONDS + 1),
    )
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run_program(executable_path, expected_output, timeout=5):
    executable = Path(executable_path).resolve()

    if not executable.is_file():
        return {
            "success": False,
            "verified": False,
            "error": "Executable not found"
        }

    process = None
    start = time.perf_counter()
    stdout_data = bytearray()
    stderr_data = bytearray()
    timed_out = False
    output_exceeded = False

    try:
        process = subprocess.Popen(
            [str(executable)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            preexec_fn=_set_limits,
        )

        selector = selectors.DefaultSelector()

        try:
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")

            while selector.get_map():
                if time.perf_counter() - start >= timeout:
                    timed_out = True
                    break

                events = selector.select(timeout=0.05)

                for key, _ in events:
                    chunk = os.read(key.fileobj.fileno(), 4096)

                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue

                    target = (
                        stdout_data
                        if key.data == "stdout"
                        else stderr_data
                    )

                    if len(target) + len(chunk) > MAX_OUTPUT:
                        output_exceeded = True
                        break

                    target.extend(chunk)

                if output_exceeded:
                    break

            if timed_out or output_exceeded:
                os.killpg(process.pid, signal.SIGKILL)

            process.wait(timeout=2)

        finally:
            selector.close()

        elapsed = time.perf_counter() - start

        stdout = stdout_data.decode("utf-8", errors="replace").strip()
        stderr = stderr_data.decode("utf-8", errors="replace")

        verified = (
            not timed_out
            and not output_exceeded
            and process.returncode == 0
            and stdout == expected_output.strip()
        )

        return {
            "success": verified,
            "verified": verified,
            "timedOut": timed_out,
            "outputExceeded": output_exceeded,
            "executionTime": elapsed,
            "exitCode": process.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "error": (
                "Execution timed out" if timed_out
                else "Output size exceeded" if output_exceeded
                else "Output or exit code mismatch" if not verified
                else None
            )
        }

    except Exception as exc:
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=2)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                pass

        return {
            "success": False,
            "verified": False,
            "error": str(exc)
        }
