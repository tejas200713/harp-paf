"""Controlled comparison of HARP-PAF against Random, PORT and OS default.

Methods
  harp          HARP-PAF dynamic SMT co-scheduling (backend.scheduler)
  port, random  the same dynamic executor with the PORT / Random policy
  harp_static   HARP-PAF's global minimum-cost matching, executed as fixed
                pairs one after another (a thread idles when the shorter
                task of a pair finishes)
  linux         OS default: every workload starts at once on the same two
                sibling threads and the OS scheduler time-shares them
  serial        every workload alone on one thread of the core, one after
                another (no SMT); its per-task times are that repetition's
                solo reference for slowdown, STP and ANTT, so clock drift
                between repetitions cancels out

Protocol (identical for every method):

* the same verified executables, the same SMT core(s) (sibling hardware
  threads from the OS topology, config.SMT_CORES of them; one by default)
  and the same timeout;
* every repetition runs every method once, in a freshly shuffled order,
  to spread drift and thermal effects across methods;
* the Random policy is seeded, so runs are reproducible;
* every task's output is verified on every run.

Per run: makespan, throughput (workloads completed per second), STP
(sum of solo/co-run time, i.e. weighted speedup), ANTT (mean co-run/solo
time), per-task slowdown and, for every co-running pair, the measured mean
and worst excess slowdown (Equation 10).
"""

import math
from pathlib import Path
import random
import statistics
import sys

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend import config
from backend.execution import ProcessSpec, run_group
from backend.scheduler import run_dynamic
from backend.stats import ratio_of_medians_ci, summarize

METHOD_LABELS = {
    "harp": "HARP-PAF",
    "harp_static": "HARP-PAF (static pairs)",
    "port": "PORT",
    "random": "Random",
    "linux": "OS default",
    "serial": "Serial (no SMT)",
}


def _verify(task_id, entry, expected):
    if entry.get("exitCode") != 0:
        raise RuntimeError(
            f"{task_id}: exit={entry.get('exitCode')}; "
            f"stderr={entry.get('stderr', '')[:300]!r}"
        )

    if expected is not None and entry.get("stdout", "").strip() != expected.strip():
        raise RuntimeError(
            f"{task_id}: output verification failed; stdout={entry.get('stdout', '')[:200]!r}"
        )


def _run_specs(specs, tasks):
    if not specs:
        return 0.0, {}

    run = run_group(specs)

    if run["timedOut"]:
        raise TimeoutError("Benchmark run exceeded the timeout")

    seconds = {}

    for spec in specs:
        entry = run["processes"].get(spec.key)
        if not entry:
            raise RuntimeError(f"{spec.key}: missing execution results")
        _verify(spec.key, entry, tasks[spec.key]["expected"])
        seconds[spec.key] = entry["wallSeconds"]

    return run["makespanSeconds"] or 0.0, seconds


def run_pairs(tasks, pairs, slots):
    makespan = 0.0
    seconds = {}
    waves = [pairs[i:i + len(slots)] for i in range(0, len(pairs), len(slots))]

    for wave in waves:
        specs = []
        for pair, slot in zip(wave, slots):
            members = [t for t in pair if t != config.IDLE]
            for task_id, cpu in zip(members, slot):
                specs.append(ProcessSpec(task_id, tasks[task_id]["argv"], (cpu,)))
        wave_makespan, wave_seconds = _run_specs(specs, tasks)
        makespan += wave_makespan or 0.0
        seconds.update(wave_seconds)

    return makespan, seconds, len(waves)


def run_linux(tasks, slots):
    pair_count = math.ceil(len(tasks) / 2)
    cpus = tuple(sorted({c for slot in slots[:pair_count] for c in slot}))
    specs = [ProcessSpec(t, tasks[t]["argv"], cpus) for t in sorted(tasks)]
    makespan, seconds = _run_specs(specs, tasks)
    return makespan, seconds, 1


def _run_metrics(method, pairs, makespan, seconds, solo, waves):
    def safe_div(num, den, default=0.0):
        return num / den if den and den > 0 else default

    slowdown = {t: safe_div(seconds[t], solo.get(t, 0.0), default=1.0) - 1 for t in seconds}
    pair_slowdowns = []

    for a, b in pairs or []:
        if config.IDLE in (a, b):
            continue
        pair_slowdowns.append({
            "pair": [a, b],
            "measured": 0.5 * (slowdown.get(a, 0.0) + slowdown.get(b, 0.0)),
            "measuredWorst": max(slowdown.get(a, 0.0), slowdown.get(b, 0.0)),
            "measuredPairSeconds": max(seconds.get(a, 0.0), seconds.get(b, 0.0)),
        })

    safe_makespan = max(0.0001, makespan or 0.0)
    return {
        "method": method,
        "pairs": pairs,
        "waves": waves,
        "makespanSeconds": makespan or 0.0,
        "throughput": len(seconds) / safe_makespan,
        "stp": sum(safe_div(solo.get(t, 0.0), seconds[t], 1.0) for t in seconds),
        "antt": statistics.fmean(safe_div(seconds[t], solo.get(t, 0.0), 1.0) for t in seconds) if seconds else 1.0,
        "worstTaskSlowdown": max(slowdown.values()) if slowdown else 0.0,
        "taskSeconds": seconds,
        "taskSlowdown": slowdown,
        "pairSlowdowns": pair_slowdowns,
    }


def evaluate(tasks, solo, policies, plans, slots, repetitions, seed, include_linux=True):
    """
    tasks:    {task_id: {"argv": [...], "expected": str | None}}
    solo:     {task_id: median solo seconds}
    policies: {method: scheduler policy} executed dynamically
    plans:    {method: fixed pairs} executed as pairs one after another
    """

    if not config.MIN_EVAL_REPETITIONS <= repetitions <= config.MAX_EVAL_REPETITIONS:
        raise ValueError("Unsupported repetition count")

    methods = (list(policies) + list(plans) + ["serial"]
               + (["linux"] if include_linux else []))
    order_rng = random.Random(seed)
    runs = {m: [] for m in methods}
    run_log = []
    timeout = config.RUN_TIMEOUT_SECONDS + 3 * sum(solo.values())

    for repetition in range(repetitions):
        order = methods[:]
        order_rng.shuffle(order)
        raw = {}

        for method in order:
            pairs = timeline = None
            decision = 0.0

            if method == "linux":
                makespan, seconds, waves = run_linux(tasks, slots)
            elif method == "serial":
                makespan, seconds, waves = run_serial(tasks, slots)
            elif method in plans:
                pairs = plans[method]
                makespan, seconds, waves = run_pairs(tasks, pairs, slots)
            else:
                result = run_dynamic(tasks, solo, slots, policies[method], timeout)
                makespan, seconds, waves = result["makespanSeconds"], result["taskSeconds"], 1
                timeline, decision = result["timeline"], result["decisionSeconds"]

            raw[method] = (pairs, makespan, seconds, waves, timeline, decision)
            run_log.append({
                "repetition": repetition + 1,
                "method": method,
                "makespanSeconds": makespan,
            })

        reference = raw["serial"][2]

        for method in methods:
            pairs, makespan, seconds, waves, timeline, decision = raw[method]
            record = _run_metrics(method, pairs, makespan, seconds, reference, waves)
            record["repetition"] = repetition + 1
            record["timeline"] = timeline
            record["decisionSeconds"] = decision
            runs[method].append(record)

    return _summarize(runs, run_log, seed, repetitions)


def run_serial(tasks, slots):
    """Each workload alone on the first thread of the core, one after another."""

    makespan = 0.0
    seconds = {}

    for task_id in sorted(tasks):
        run_makespan, run_seconds = _run_specs(
            [ProcessSpec(task_id, tasks[task_id]["argv"], (slots[0][0],))], tasks
        )
        makespan += run_makespan or 0.0
        seconds.update(run_seconds)

    return makespan, seconds, len(tasks)


def _summarize(runs, run_log, seed, repetitions):
    serial_records = [r["makespanSeconds"] for r in runs.get("serial", []) if "makespanSeconds" in r]
    serial_seconds = statistics.median(serial_records) if serial_records else 0.0
    methods = {}

    def _default_metric(val=0.0):
        return {
            "n": 0, "median": val, "mean": val, "std": 0.0,
            "min": val, "max": val, "q1": val, "q3": val, "ci95": [val, val],
        }

    for method, records in runs.items():
        makespan = summarize([r["makespanSeconds"] for r in records], seed) or _default_metric(0.0)
        methods[method] = {
            "label": METHOD_LABELS.get(method, method),
            "makespan": makespan,
            # Benefit of SMT co-running over the measured serial runs
            # (every workload alone, one after another, on the same core).
            "smtGainVsSerialPercent": (
                (serial_seconds - makespan["median"]) / serial_seconds * 100
                if serial_seconds > 0 else 0.0
            ),
            "throughput": summarize([r["throughput"] for r in records], seed) or _default_metric(0.0),
            "decisionSecondsMedian": statistics.median(
                [r["decisionSeconds"] for r in records if r.get("decisionSeconds") is not None]
            ) if any(r.get("decisionSeconds") is not None for r in records) else 0.0,
            "stp": summarize([r["stp"] for r in records], seed) or _default_metric(0.0),
            "antt": summarize([r["antt"] for r in records], seed) or _default_metric(1.0),
            "worstTaskSlowdown": summarize(
                [r["worstTaskSlowdown"] for r in records], seed
            ) or _default_metric(0.0),
            "taskSlowdownMedian": {
                t: statistics.median(r["taskSlowdown"][t] for r in records if t in r.get("taskSlowdown", {}))
                for t in records[0].get("taskSlowdown", {})
            } if records else {},
            "taskSecondsMedian": {
                t: statistics.median(r["taskSeconds"][t] for r in records if t in r.get("taskSeconds", {}))
                for t in records[0].get("taskSeconds", {})
            } if records else {},
        }

    harp = [r["makespanSeconds"] for r in runs.get("harp", []) if "makespanSeconds" in r]
    harp_median = statistics.median(harp) if harp else 1.0
    harp_throughput = (methods.get("harp", {}).get("throughput") or {}).get("median", 1.0)
    comparisons = {}

    for method in runs:
        if method == "harp":
            continue
        baseline = [r["makespanSeconds"] for r in runs.get(method, []) if "makespanSeconds" in r]
        baseline_median = statistics.median(baseline) if baseline else 1.0
        med_thp = (methods.get(method, {}).get("throughput") or {}).get("median", 0.0)
        comparisons[method] = {
            "label": METHOD_LABELS.get(method, method),
            "speedup": baseline_median / harp_median if harp_median > 0 else 1.0,
            "speedupCi95": ratio_of_medians_ci(baseline, harp, seed=seed) if (baseline and harp) else [1.0, 1.0],
            "runtimeReductionPercent": (
                (baseline_median - harp_median) / baseline_median * 100
                if baseline_median > 0 else 0.0
            ),
            "throughputGainPercent": (
                (harp_throughput / med_thp - 1) * 100
                if med_thp > 0 else 0.0
            ),
            "harpFasterInRuns": sum(
                h < b for h, b in zip(harp, baseline)
            ),
        }

    observations = {}

    for records in runs.values():
        for record in records:
            for item in record["pairSlowdowns"]:
                key = tuple(sorted(item["pair"]))
                observations.setdefault(key, []).append(item)

    pair_observations = [
        {
            "pair": list(key),
            "count": len(items),
            "measured": statistics.fmean(i["measured"] for i in items),
            "measuredWorst": statistics.fmean(i["measuredWorst"] for i in items),
            "measuredPairSeconds": statistics.fmean(
                i["measuredPairSeconds"] for i in items
            ),
        }
        for key, items in sorted(observations.items())
    ]

    return {
        "repetitions": repetitions,
        "seed": seed,
        "serialSoloSeconds": serial_seconds,
        "methods": methods,
        "comparisons": comparisons,
        "runs": runs,
        "runOrder": run_log,
        "pairObservations": pair_observations,
    }


if __name__ == "__main__":
    print("HARP-PAF Benchmarking Module")
    print("Available scheduling methods:", list(METHOD_LABELS.keys()))
    print("Status: OK - Benchmarks module loaded successfully.")
