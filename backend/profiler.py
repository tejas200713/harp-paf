"""Algorithm B: runtime profiling.

Every workload's sensitivity to each shared resource is measured by
probing (below). Three interchangeable profilers then provide the phase
profile and resource usage:

* perf mode   - (Linux) `perf stat -I` samples hardware counters in fixed
                windows; windows are segmented into phases (backend.phases).
* emon mode   - (Windows) Intel EMON samples counters per CPU while the
                workload runs pinned; also measures the runtime instruction
                mix (backend.emon). Requires an elevated process.
* probe mode  - when hardware counters are unavailable (for example under
                WSL2), each workload is co-run on an SMT sibling with
                stressor kernels that saturate one resource each; the
                slowdown it suffers is its interference sensitivity to that
                resource. This yields a single whole-program phase.

Solo runtimes (sibling idle) are measured separately in both modes and are
the reference for slowdown (Equation 10) and profiling overhead.
"""

from functools import lru_cache
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend import config, emon, kernels, phases, topology
from backend.execution import ProcessGroup, ProcessSpec, run_group
from backend.stats import cv


def _clip(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def _normalise_event(name):
    name = name.split("/")[1] if "/" in name else name
    return name.split(":")[0]


@lru_cache(maxsize=1)
def perf_status():
    if not shutil.which("perf"):
        return {"available": False, "reason": "perf binary not found",
                "supportedEvents": []}

    try:
        result = subprocess.run(
            ["perf", "stat", "-x", ",", "-e", ",".join(config.PERF_EVENTS),
             "--", "true"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "reason": str(exc), "supportedEvents": []}

    supported = set()

    for line in result.stderr.splitlines():
        fields = line.split(",")
        if len(fields) > 3 and fields[0].replace(".", "").isdigit():
            supported.add(_normalise_event(fields[2] or fields[3]))

    required = {"instructions", "cycles"}

    if not required.issubset(supported):
        return {
            "available": False,
            "reason": (result.stderr.strip().splitlines() or ["counters unsupported"])[-1],
            "supportedEvents": sorted(supported),
        }

    return {"available": True, "reason": None,
            "supportedEvents": sorted(supported)}


def counter_status():
    """Hardware-counter availability for this platform."""

    if os.name == "nt":
        return {"tool": "emon", **emon.status()}
    return {"tool": "perf", **perf_status()}


def profiling_mode():
    if config.PROFILE_MODE in ("perf", "emon", "probe"):
        return config.PROFILE_MODE
    status = counter_status()
    return status["tool"] if status["available"] else "probe"


def warm_up(cpus, seconds=None):
    """Keep `cpus` fully busy for a while so clock speeds settle."""

    seconds = config.WARMUP_SECONDS if seconds is None else seconds

    if seconds <= 0:
        return

    group = ProcessGroup()
    try:
        for index, cpu in enumerate(cpus):
            group.start(ProcessSpec(f"warmup{index}", kernels.argv("int"), (cpu,),
                                    background=True))
        time.sleep(seconds)
    finally:
        group.close()


def _check(entry, expected, label):
    if entry.get("exitCode") != 0:
        raise RuntimeError(
            f"{label}: exit code {entry.get('exitCode')}; {entry.get('stderr', '')[:300]}"
        )

    if expected is not None and entry.get("stdout", "").strip() != expected.strip():
        raise RuntimeError(f"{label}: output verification failed")


def solo_times(argv, slot, repetitions, expected=None, label="task"):
    """Wall time with the SMT sibling idle."""

    samples = []

    for _ in range(config.WARMUP_RUNS):
        warmup = run_group([ProcessSpec("task", argv, (slot[0],))])
        _check(warmup["processes"]["task"], expected, label)

    for _ in range(repetitions):
        run = run_group([ProcessSpec("task", argv, (slot[0],))])
        entry = run["processes"]["task"]
        if run["timedOut"]:
            raise RuntimeError(f"{label}: solo run timed out")
        _check(entry, expected, label)
        samples.append(entry["wallSeconds"])

    return {
        "samples": samples,
        "median": statistics.median(samples),
        "cv": cv(samples),
    }


def parse_perf_intervals(text):
    """Parse `perf stat -I -x ,` output into per-window event counts."""

    intervals = {}
    unsupported = set()

    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue

        fields = [f.strip() for f in line.split(",")]

        if len(fields) < 4:
            continue

        try:
            timestamp = float(fields[0])
        except ValueError:
            continue

        event = _normalise_event(fields[3])
        window = intervals.setdefault(timestamp, {})

        try:
            window[event] = window.get(event, 0.0) + float(fields[1])
        except ValueError:
            unsupported.add(event)

    return [intervals[t] | {"_time": t} for t in sorted(intervals)], unsupported


def perf_windows(raw):
    windows = []
    total_instructions = sum(w.get("instructions", 0.0) for w in raw)
    progress = 0.0
    previous_time = 0.0

    for counts in raw:
        dt = counts["_time"] - previous_time
        previous_time = counts["_time"]
        instructions = counts.get("instructions", 0.0)
        cycles = counts.get("cycles", 0.0)

        if instructions <= 0 or cycles <= 0 or total_instructions <= 0:
            continue

        kilo = instructions / 1000
        refs = counts.get("cache-references")
        misses = counts.get("cache-misses")
        branch_misses = counts.get("branch-misses")
        fe = counts.get("stalled-cycles-frontend")
        be = counts.get("stalled-cycles-backend")
        start = progress
        progress += instructions / total_instructions

        measures = {
            "ipc": instructions / cycles,
            "intensity": _clip(instructions / cycles / config.IPC_REFERENCE),
            "footprint": (
                _clip(refs / kilo / config.FOOTPRINT_REFERENCE_PKI)
                if refs is not None else None
            ),
            "bandwidth": (
                _clip(misses * config.CACHE_LINE_BYTES / dt / config.B_SOCKET)
                if misses is not None and dt > 0 else None
            ),
            "bandwidthBytesPerSecond": (
                misses * config.CACHE_LINE_BYTES / dt
                if misses is not None and dt > 0 else None
            ),
            "branch_miss": (
                _clip(branch_misses / kilo / config.BRANCH_MPKI_REFERENCE)
                if branch_misses is not None else None
            ),
            "stall_fe": _clip(fe / cycles) if fe is not None else None,
            "stall_be": _clip(be / cycles) if be is not None else None,
            "llc_miss_ratio": (
                _clip(misses / refs) if misses is not None and refs else None
            ),
        }
        windows.append({"progress": (start, progress), "measures": measures})

    return windows


def profile_perf(argv, slot, output_file, expected=None, label="task"):
    command = [
        "perf", "stat", "-I", str(config.PERF_INTERVAL_MS), "-x", ",",
        "-o", str(output_file), "-e", ",".join(config.PERF_EVENTS), "--",
        *argv,
    ]
    run = run_group([ProcessSpec("task", command, (slot[0],))])
    entry = run["processes"]["task"]

    if run["timedOut"]:
        raise RuntimeError(f"{label}: perf run timed out")

    _check(entry, expected, label)
    raw, unsupported = parse_perf_intervals(
        output_file.read_text(encoding="utf-8", errors="replace")
    )
    detected = phases.detect(perf_windows(raw))
    totals = {}

    for counts in raw:
        for event, value in counts.items():
            if event != "_time":
                totals[event] = totals.get(event, 0.0) + value

    return {
        "wallSeconds": entry["wallSeconds"],
        "phaseProfile": detected,
        "totals": totals,
        "unsupportedEvents": sorted(unsupported),
    }


def profile_emon(argv, slot, output_file, solo, expected=None, label="task"):
    """Workload pinned to slot[0]; EMON samples system-wide on the harness CPU."""

    harness = topology.discover()["harnessCpu"]
    emon_cpus = (harness,) if harness is not None else tuple(
        c for c in topology.discover()["allowedCpus"] if c not in slot
    )
    run = run_group([
        ProcessSpec("emon", emon.command(output_file, solo["median"] * 1.5 + 0.5),
                    emon_cpus),
        ProcessSpec("task", argv, (slot[0],)),
    ], timeout=config.RUN_TIMEOUT_SECONDS + solo["median"] * 2)
    entry = run["processes"]["task"]

    if run["timedOut"]:
        raise RuntimeError(f"{label}: EMON run timed out")

    _check(entry, expected, label)

    if run["processes"]["emon"]["exitCode"] != 0:
        raise RuntimeError(f"{label}: EMON failed: {run['processes']['emon']['stdout'][-300:]}")

    samples = emon.parse(
        output_file.read_text(encoding="utf-8", errors="replace"), slot[0]
    )
    windows, totals = emon.windows(samples)

    return {
        "wallSeconds": entry["wallSeconds"],
        "phaseProfile": phases.detect(windows),
        "totals": totals,
        "windowCount": len(windows),
    }


def profile_probe(argv, slot, solo, expected=None, label="task"):
    sensitivity = {}
    times = {}

    for name in config.PROBE_KERNELS:
        run = run_group([
            ProcessSpec("task", argv, (slot[0],)),
            ProcessSpec("stressor", kernels.argv(name), (slot[1],), background=True),
        ])
        entry = run["processes"]["task"]

        if run["timedOut"]:
            raise RuntimeError(f"{label}: probe {name} timed out")

        _check(entry, expected, label)
        times[name] = entry["wallSeconds"]
        sensitivity[name] = max(0.0, entry["wallSeconds"] / solo["median"] - 1)

    measures = {
        f"sens_{name}": _clip(value / config.SENSITIVITY_REFERENCE)
        for name, value in sensitivity.items()
    }

    return {
        "wallSeconds": sum(times.values()),
        "probeTimes": times,
        "sensitivity": sensitivity,
        "phaseProfile": phases.single_phase(measures),
    }


def profile_workload(argv, slot, mode, workdir, key, expected=None):
    started = time.perf_counter()
    solo = solo_times(argv, slot, config.SOLO_REPETITIONS, expected, key)

    # Sensitivity to each shared resource is always measured by probing;
    # counters (when available) add phases and resource usage.
    probe = profile_probe(argv, slot, solo, expected, key)

    if mode == "perf":
        runtime = profile_perf(argv, slot, workdir / f"{key}.perf.csv", expected, key)
        overhead = runtime["wallSeconds"] / solo["median"] - 1
    elif mode == "emon":
        runtime = profile_emon(argv, slot, workdir / f"{key}.emon.txt", solo, expected, key)
        overhead = runtime["wallSeconds"] / solo["median"] - 1
    else:
        runtime = probe
        overhead = None

    return {
        "mode": mode,
        "solo": solo,
        "runtime": runtime,
        "sensitivity": probe["sensitivity"],
        "probeTimes": probe["probeTimes"],
        "phaseProfile": runtime["phaseProfile"],
        "perfOverheadFraction": overhead,
        "profilingSeconds": time.perf_counter() - started,
    }
