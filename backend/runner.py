"""Single verified execution of a compiled workload (any platform)."""

from pathlib import Path
import os

from backend.execution import ProcessSpec, run_group


def run_program(executable_path, expected_output, timeout=5, cpus=None):
    executable = Path(executable_path).resolve()

    if not executable.is_file():
        return {
            "success": False,
            "verified": False,
            "error": "Executable not found"
        }

    cpus = tuple(cpus or range(os.cpu_count() or 1))

    try:
        run = run_group(
            [ProcessSpec("program", [executable], cpus)],
            timeout=timeout,
            cwd=executable.parent,
        )
    except Exception as exc:
        return {
            "success": False,
            "verified": False,
            "error": str(exc)
        }

    entry = run["processes"]["program"]
    timed_out = run["timedOut"]
    stdout = entry.get("stdout", "")
    verified = (
        not timed_out
        and entry.get("exitCode") == 0
        and expected_output is not None
        and stdout == expected_output.strip()
    )

    return {
        "success": verified,
        "verified": verified,
        "timedOut": timed_out,
        "outputExceeded": False,
        "executionTime": entry.get("wallSeconds"),
        "exitCode": entry.get("exitCode"),
        "stdout": stdout,
        "stderr": entry.get("stderr", ""),
        "error": (
            "Execution timed out" if timed_out
            else "Output or exit code mismatch" if not verified
            else None
        )
    }
