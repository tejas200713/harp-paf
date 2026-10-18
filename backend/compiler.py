from pathlib import Path
import subprocess

from backend import config


def compile_program(source_path, output_path, language="cpp", extra_flags=()):
    source_path = Path(source_path)
    output_path = Path(output_path)

    if language not in ("c", "cpp"):
        raise ValueError("Unsupported language")

    compiler = "g++" if language == "cpp" else "gcc"
    flags = config.CPP_FLAGS if language == "cpp" else config.C_FLAGS

    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        compiler,
        *flags,
        *extra_flags,
        str(source_path),
        "-o",
        str(output_path),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        return {
            "success": result.returncode == 0,
            "exitCode": result.returncode,
            "stdout": result.stdout[:10000],
            "stderr": result.stderr[:10000],
            "command": command,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "exitCode": None,
            "stdout": "",
            "stderr": "Compilation timed out after 60 seconds",
            "command": command,
        }
    except OSError as exc:
        return {
            "success": False,
            "exitCode": None,
            "stdout": "",
            "stderr": f"Failed to execute compiler {compiler!r}: {exc}",
            "command": command,
        }
