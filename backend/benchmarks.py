
"""Controlled local WSL benchmark for four approved workloads.

This is a demonstration of affinity-based placement, not
proof of SMT sibling scheduling or hardware-level speedup.
"""

import json
import os
import signal
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

from backend.approved_workloads import get_expected_output

BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"

BASELINE_PAIRS = (
    ("T01", "T04"),
    ("T02", "T03"),
)

PAIR_CPU_SETS = ((0, 1), (2, 3))
TIMEOUT_SECONDS = 5
MAX_OUTPUT_BYTES = 65536


def run_plan(job_dir, job, pairs, allowed_cpus):
    """Run four verified executables concurrently."""

    assignments = {}
    for pair, cpus in zip(pairs, PAIR_CPU_SETS):
        for task_id in pair:
            if task_id in assignments:
                raise ValueError("Duplicate task assignment")
            assignments[task_id] = cpus

    if set(assignments) != {"T01", "T02", "T03", "T04"}:
        raise ValueError("Each task must appear exactly once")

    if not set(sum(PAIR_CPU_SETS, ())).issubset(allowed_cpus):
        raise ValueError("Required CPU IDs are unavailable")

    processes = {}
    streams = {}
    started = time.perf_counter()

    try:
        for index, metadata in enumerate(job["files"], start=1):
            task_id = metadata["taskId"]
            executable = job_dir / f"task{index}"

            if not executable.is_file():
                raise FileNotFoundError(executable)

            stdout_file = tempfile.TemporaryFile(mode="w+b")
            stderr_file = tempfile.TemporaryFile(mode="w+b")
            streams[task_id] = (stdout_file, stderr_file)

            cpu_arg = ",".join(
                str(cpu) for cpu in assignments[task_id]
            )

            process = subprocess.Popen(
                [
                    "taskset",
                    "-c",
                    cpu_arg,
                    str(executable),
                ],
                stdin=subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                start_new_session=True,
                cwd=str(job_dir),
            )
            processes[task_id] = process

        deadline = started + TIMEOUT_SECONDS

        while any(p.poll() is None for p in processes.values()):
            if time.perf_counter() >= deadline:
                raise TimeoutError("Benchmark exceeded 5 seconds")
            time.sleep(0.001)

        elapsed = time.perf_counter() - started
        results = []

        for metadata in job["files"]:
            task_id = metadata["taskId"]
            process = processes[task_id]
            stdout_file, stderr_file = streams[task_id]

            stdout_file.seek(0)
            stderr_file.seek(0)

            stdout_bytes = stdout_file.read(MAX_OUTPUT_BYTES + 1)
            stderr_bytes = stderr_file.read(MAX_OUTPUT_BYTES + 1)

            if (
                len(stdout_bytes) > MAX_OUTPUT_BYTES
                or len(stderr_bytes) > MAX_OUTPUT_BYTES
            ):
                raise RuntimeError(f"{task_id}: output too large")

            stdout = stdout_bytes.decode(
                "utf-8", errors="replace"
            ).strip()

            stderr = stderr_bytes.decode(
                "utf-8", errors="replace"
            ).strip()

            expected = get_expected_output(
                job["language"], metadata["sha256"]
            )

            if (
                expected is None
                or process.returncode != 0
                or stdout != expected.strip()
            ):
                raise RuntimeError(
                    f"{task_id}: output verification failed; "
                    f"exit={process.returncode}; "
                    f"stdout={stdout!r}; stderr={stderr!r}"
                )

            results.append({
                "taskId": task_id,
                "verified": True,
                "exitCode": process.returncode,
                "cpus": list(assignments[task_id]),
            })

        return {
            "makespanSeconds": elapsed,
            "taskResults": results,
        }

    finally:
        for process in processes.values():
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

        for process in processes.values():
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass

        for stdout_file, stderr_file in streams.values():
            stdout_file.close()
            stderr_file.close()


def benchmark_job(job_id, repetitions=5):
    if not (
        len(job_id) == 32
        and all(c in "0123456789abcdef" for c in job_id)
    ):
        raise ValueError("Invalid job ID")

    job_dir = ARTIFACTS_DIR / job_id
    job = json.loads(
        (job_dir / "job.json").read_text(encoding="utf-8")
    )


    if job["status"] not in ("paired", "running", "completed"):
        raise ValueError("Job must have completed pairing")

    if job["language"] != "cpp":
        raise ValueError("Only reviewed C++ benchmark supported")

    if not 3 <= repetitions <= 5:
        raise ValueError("Use 3 to 5 repetitions")

    selected = tuple(
        tuple(pair) for pair in job["selectedPairs"]
    )

    if set(sum(selected, ())) != {
        "T01", "T02", "T03", "T04"
    }:
        raise ValueError("Invalid selected pairing")

    if set(selected) == set(BASELINE_PAIRS):
        raise ValueError("Baseline and selected plans are identical")

    allowed_cpus = set(os.sched_getaffinity(0))

    if not {0, 1, 2, 3}.issubset(allowed_cpus):
        raise ValueError("CPU IDs 0-3 are not available")

    raw_runs = {"baseline": [], "selected": []}

    # Alternate which plan executes first to reduce order bias.
    for iteration in range(repetitions):
        order = (
            ("baseline", "selected")
            if iteration % 2 == 0
            else ("selected", "baseline")
        )

        for plan_name in order:
            pairs = (
                BASELINE_PAIRS
                if plan_name == "baseline"
                else selected
            )

            result = run_plan(
                job_dir, job, pairs, allowed_cpus
            )

            raw_runs[plan_name].append(
                result["makespanSeconds"]
            )

            print(
                f"Run {iteration + 1} | {plan_name}: "
                f'{result["makespanSeconds"]:.6f} s',
                flush=True,
            )

    baseline_median = statistics.median(
        raw_runs["baseline"]
    )

    selected_median = statistics.median(
        raw_runs["selected"]
    )

    result = {
        "measurementMode": "local-wsl2",
        "measurementType": "four-process-launch-to-exit-wall-time",
        "baselinePairs": BASELINE_PAIRS,
        "selectedPairs": selected,
        "cpuSets": PAIR_CPU_SETS,
        "verifiedSmtSiblings": False,
        "repetitions": repetitions,
        "rawRuns": raw_runs,
        "baselineMedianSeconds": baseline_median,
        "selectedMedianSeconds": selected_median,
        "speedup": baseline_median / selected_median,
        "runtimeReductionPercent": (
            (baseline_median - selected_median)
            / baseline_median * 100
        ),
        "notes": (
            "Includes Python process-launch overhead. "
            "CPU sets are WSL virtual logical CPUs. "
            "No hardware counters or verified SMT topology. "
            "Workloads are very short; results may be noisy."
        ),
    }

    output_file = job_dir / "benchmark.json"
    output_file.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m backend.benchmarks JOB_ID"
        )

    result = benchmark_job(sys.argv[1])

    print("\n=== BENCHMARK SUMMARY ===")
    print(
        "Baseline median:",
        f'{result["baselineMedianSeconds"]:.6f} s'
    )
    print(
        "Selected median:",
        f'{result["selectedMedianSeconds"]:.6f} s'
    )
    print(
        "Speedup:",
        f'{result["speedup"]:.4f}x'
    )
    print(
        "Runtime reduction:",
        f'{result["runtimeReductionPercent"]:.2f}%'
    )
    print("Results saved to benchmark.json")
