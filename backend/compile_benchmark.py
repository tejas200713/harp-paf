
"""Compare single-file compilation with parallel multi-file compilation."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import time


def run_command(command):
    start = time.perf_counter()

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    return {
        "success": result.returncode == 0,
        "seconds": time.perf_counter() - start,
        "stderr": result.stderr,
        "stdout": result.stdout,
    }


def compare_compilation(original_file, generated_dir):
    original_file = Path(original_file).resolve()
    generated_dir = Path(generated_dir).resolve()

    sources = sorted(generated_dir.glob("*.cpp"))

    if len(sources) < 2:
        raise ValueError("At least two generated C++ files required")

    # Original compilation
    original_exe = generated_dir / "original_benchmark.exe"

    original = run_command([
        "g++", "-O2", "-std=c++17",
        str(original_file),
        "-o", str(original_exe)
    ])

    if not original["success"]:
        raise RuntimeError(original["stderr"])

    # Compile generated files independently, in parallel
    def compile_object(source):
        output = source.with_suffix(".o")
        result = run_command([
            "g++", "-O2", "-std=c++17",
            "-c", str(source),
            "-o", str(output)
        ])
        return output, result

    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=min(4, len(sources))) as pool:
        compiled = list(pool.map(compile_object, sources))

    failures = [
        result["stderr"]
        for _, result in compiled
        if not result["success"]
    ]

    if failures:
        raise RuntimeError("\n".join(failures))

    objects = [str(path) for path, _ in compiled]

    # Link all generated objects
    split_exe = generated_dir / "split_benchmark.exe"

    link = run_command([
        "g++", *objects, "-o", str(split_exe)
    ])

    if not link["success"]:
        raise RuntimeError(link["stderr"])

    split_seconds = time.perf_counter() - start

    # Verify program behaviour
    original_run = run_command([str(original_exe)])
    split_run = run_command([str(split_exe)])

    verified = (
        original_run["success"]
        and split_run["success"]
        and original_run["stdout"] == split_run["stdout"]
        and original_run["stderr"] == split_run["stderr"]
    )

    speedup = (
        original["seconds"] / split_seconds
        if split_seconds > 0 else 0
    )

    return {
        "originalCompileSeconds": round(original["seconds"], 4),
        "splitCompileSeconds": round(split_seconds, 4),
        "speedup": round(speedup, 3),
        "generatedSourceCount": len(sources),
        "outputVerified": verified,
        "originalOutput": original_run["stdout"],
        "splitOutput": split_run["stdout"],
    }


if __name__ == "__main__":
    from backend.source_splitter import split_source

    source = Path("splitter_test.cpp")
    output = Path("artifacts/splitter_test")

    split_source(source, output)

    result = compare_compilation(source, output)

    print("\nHARP-PAF Compilation Benchmark")
    print("--------------------------------")

    for key, value in result.items():
        print(f"{key}: {value}")
