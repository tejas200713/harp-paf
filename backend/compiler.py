from pathlib import Path
import subprocess


def compile_program(source_path, output_path, language="cpp"):
    source_path = Path(source_path)
    output_path = Path(output_path)

    if language not in ("c", "cpp"):
        raise ValueError("Unsupported language")

    compiler = "g++" if language == "cpp" else "gcc"

    flags = [
        "-O2",
        "-std=c++17" if language == "cpp" else "-std=c11",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        compiler,
        *flags,
        str(source_path),
        "-o",
        str(output_path),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
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
            "stderr": "Compilation timed out after 30 seconds",
            "command": command,
        }
