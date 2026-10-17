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
import random
import statistics

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

    if expected is not None and entry["stdout"].strip() != expected.strip():
        raise RuntimeError(
            f"{task_id}: output verification failed; stdout={entry['stdout'][:200]!r}"
        )


def _run_specs(specs, tasks):
    run = run_group(specs)

    if run["timedOut"]:
        raise TimeoutError("Benchmark run exceeded the timeout")

    seconds = {}

    for spec in specs:
        entry = run["processes"][spec.key]
        _verify(spec.key, entry, tasks[spec.key]["expected"])
        seconds[spec.key] = entry["wallSeconds"]

    return run["makespanSeconds"], seconds


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
        makespan += wave_makespan
        seconds.update(wave_seconds)

    return makespan, seconds, len(waves)


def run_linux(tasks, slots):
    pair_count = math.ceil(len(tasks) / 2)
    cpus = tuple(sorted({c for slot in slots[:pair_count] for c in slot}))
    specs = [ProcessSpec(t, tasks[t]["argv"], cpus) for t in sorted(tasks)]
    makespan, seconds = _run_specs(specs, tasks)
    return makespan, seconds, 1


def _run_metrics(method, pairs, makespan, seconds, solo, waves):
    slowdown = {t: seconds[t] / solo[t] - 1 for t in seconds}
    pair_slowdowns = []

    for a, b in pairs or []:
        if config.IDLE in (a, b):
            continue
        pair_slowdowns.append({
            "pair": [a, b],
            "measured": 0.5 * (slowdown[a] + slowdown[b]),
            "measuredWorst": max(slowdown[a], slowdown[b]),
            "measuredPairSeconds": max(seconds[a], seconds[b]),
        })

    return {
        "method": method,
        "pairs": pairs,
        "waves": waves,
        "makespanSeconds": makespan,
        "throughput": len(seconds) / makespan,
        "stp": sum(solo[t] / seconds[t] for t in seconds),
        "antt": statistics.fmean(seconds[t] / solo[t] for t in seconds),
        "worstTaskSlowdown": max(slowdown.values()),
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
        makespan += run_makespan
        seconds.update(run_seconds)

    return makespan, seconds, len(tasks)


def _summarize(runs, run_log, seed, repetitions):
    serial_seconds = statistics.median(r["makespanSeconds"] for r in runs["serial"])
    methods = {}

    for method, records in runs.items():
        makespan = summarize([r["makespanSeconds"] for r in records], seed)
        methods[method] = {
            "label": METHOD_LABELS[method],
            "makespan": makespan,
            # Benefit of SMT co-running over the measured serial runs
            # (every workload alone, one after another, on the same core).
            "smtGainVsSerialPercent": (
                (serial_seconds - makespan["median"]) / serial_seconds * 100
            ),
            "throughput": summarize([r["throughput"] for r in records], seed),
            "decisionSecondsMedian": statistics.median(
                r["decisionSeconds"] for r in records
            ),
            "stp": summarize([r["stp"] for r in records], seed),
            "antt": summarize([r["antt"] for r in records], seed),
            "worstTaskSlowdown": summarize(
                [r["worstTaskSlowdown"] for r in records], seed
            ),
            "taskSlowdownMedian": {
                t: statistics.median(r["taskSlowdown"][t] for r in records)
                for t in records[0]["taskSlowdown"]
            },
            "taskSecondsMedian": {
                t: statistics.median(r["taskSeconds"][t] for r in records)
                for t in records[0]["taskSeconds"]
            },
        }

    harp = [r["makespanSeconds"] for r in runs["harp"]]
    harp_median = statistics.median(harp)
    harp_throughput = methods["harp"]["throughput"]["median"]
    comparisons = {}

    for method in runs:
        if method == "harp":
            continue
        baseline = [r["makespanSeconds"] for r in runs[method]]
        baseline_median = statistics.median(baseline)
        comparisons[method] = {
            "label": METHOD_LABELS[method],
            "speedup": baseline_median / harp_median,
            "speedupCi95": ratio_of_medians_ci(baseline, harp, seed=seed),
            "runtimeReductionPercent": (
                (baseline_median - harp_median) / baseline_median * 100
            ),
            "throughputGainPercent": (
                (harp_throughput / methods[method]["throughput"]["median"] - 1) * 100
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
