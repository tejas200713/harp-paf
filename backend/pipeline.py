"""Background processing of one HARP-PAF job.

Stages (stageIndex):
  1 compile             4 runtime profiling + fusion
  2 static analysis     5 pair costs + global matching
  3 verified solo run   6 repeated comparative benchmark
                        8 completed
"""

from datetime import datetime, timezone
import json
import os
import secrets
import time

from backend import config, profiler, topology
from backend.analysis import characterize, pair_table
from backend.approved_workloads import get_expected_output
from backend.baselines import port_matching, port_pressure
from backend.benchmarks import evaluate
from backend.compiler import compile_program
from backend.model import load_model
from backend.pairing import matching_count, minimum_matching, ranked_matchings
from backend.runner import run_program
from backend.stats import mae, rmse, spearman


class JobStore:
    def __init__(self, job_id):
        self.dir = config.ARTIFACTS_DIR / job_id
        self.file = self.dir / "job.json"
        self.job = json.loads(self.file.read_text(encoding="utf-8"))

    def save(self, **updates):
        self.job.update(updates)
        temporary = self.file.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.job, indent=2), encoding="utf-8")
        os.replace(temporary, self.file)


def _trim_profile(profile):
    """Drop bulky raw fields before storing the profile in job.json."""

    runtime = dict(profile["runtime"])
    runtime.pop("phaseProfile", None)
    return {**profile, "runtime": runtime}


def prediction_accuracy(pair_rows, observations):
    lookup = {(r["taskA"], r["taskB"]): r for r in pair_rows}
    points = []

    for item in observations:
        row = lookup.get(tuple(item["pair"]))
        if row:
            points.append({
                "pair": item["pair"],
                "runs": item["count"],
                "predicted": row["predictedSlowdown"],
                "measured": item["measured"],
                "predictedWorst": row["predictedWorstSlowdown"],
                "measuredWorst": item["measuredWorst"],
            })

    if not points:
        return {"points": [], "mae": None, "rmse": None, "spearman": None}

    predicted = [p["predicted"] for p in points]
    measured = [p["measured"] for p in points]
    return {
        "points": points,
        "count": len(points),
        "mae": mae(predicted, measured),
        "rmse": rmse(predicted, measured),
        "spearman": spearman(predicted, measured),
    }


def _stage(store, index, text):
    store.save(status="running", stageIndex=index, stage=text)


def process_job(job_id, repetitions=config.EVAL_REPETITIONS):
    store = JobStore(job_id)
    job = store.job

    try:
        _run(store, job, repetitions)
    except Exception as exc:
        store.save(
            status="failed",
            error=f"{type(exc).__name__}: {exc}",
            failedAt=datetime.now(timezone.utc).isoformat(),
        )


def _run(store, job, repetitions):
    language = job["language"]
    files = job["files"]
    task_ids = [f["taskId"] for f in files]
    binaries = {f["taskId"]: store.dir / f"task{i}" for i, f in enumerate(files, 1)}
    expected = {
        f["taskId"]: get_expected_output(language, f["sha256"]) for f in files
    }

    _stage(store, 1, "Compiling source files")
    compilation = []

    for f in files:
        result = compile_program(store.dir / f["savedName"], binaries[f["taskId"]], language)
        compilation.append({
            "taskId": f["taskId"], "filename": f["originalName"],
            **{k: result[k] for k in ("success", "exitCode", "stdout", "stderr")},
        })

    store.save(compilationResults=compilation)

    if not all(c["success"] for c in compilation):
        store.save(status="failed", stageIndex=2, stage="Compilation failed",
                   error="One or more source files failed to compile")
        return

    _stage(store, 3, "Executing and verifying programs")
    execution = []

    for f in files:
        result = run_program(binaries[f["taskId"]], expected[f["taskId"]],
                             timeout=config.RUN_TIMEOUT_SECONDS)
        execution.append({
            "taskId": f["taskId"], "filename": f["originalName"],
            **{k: result.get(k) for k in (
                "success", "verified", "executionTime", "exitCode",
                "stdout", "stderr", "timedOut", "error")},
        })

    store.save(executionResults=execution)

    if not all(e["verified"] for e in execution):
        store.save(status="failed", stageIndex=4,
                   stage="Program execution or verification failed",
                   error="One or more programs failed verification")
        return

    topo = topology.discover()
    slots = topology.task_slots()
    mode = profiler.profiling_mode()
    store.save(topology=topo, profilingMode=mode, perf=profiler.perf_status())

    _stage(store, 4, f"Static analysis and runtime profiling ({mode} mode)")
    characterized = {}

    for task_id in task_ids:
        store.save(stage=f"Profiling {task_id} ({mode} mode)")
        characterized[task_id] = characterize(
            task_id, binaries[task_id], [binaries[task_id]], slots[0], mode,
            store.dir, expected[task_id],
        )

    store.save(characterization={
        t: {**c, "profile": _trim_profile(c["profile"])}
        for t, c in characterized.items()
    })

    _stage(store, 5, "Calculating pair costs and global matching")
    model = load_model(mode)
    decision_started = time.perf_counter()
    pair_rows, costs, _ = pair_table(task_ids, characterized, model)
    harp_pairs, minimum_cost = minimum_matching(task_ids, costs)
    decision_seconds = time.perf_counter() - decision_started
    statics = {t: c["static"] for t, c in characterized.items()}
    port_pairs = port_matching(task_ids, statics)

    store.save(
        model={k: v for k, v in model.items() if k != "samples"},
        pairCosts=pair_rows,
        selectedPairs=harp_pairs,
        selectedMatching={"pairs": harp_pairs, "totalCost": minimum_cost},
        minimumCost=minimum_cost,
        allMatchings=ranked_matchings(task_ids, costs) or [],
        matchingsEvaluated=matching_count(len(task_ids)),
        portPairs=port_pairs,
        portPressure={t: port_pressure(s) for t, s in statics.items()},
        decisionSeconds=decision_seconds,
    )

    _stage(store, 6, f"Running comparative benchmark ({repetitions} repetitions)")
    tasks = {
        t: {"argv": [binaries[t]], "expected": expected[t]} for t in task_ids
    }
    solo = {
        t: characterized[t]["profile"]["solo"]["median"] for t in task_ids
    }
    seed = secrets.randbits(31)
    evaluation = evaluate(
        tasks, solo, {"harp": harp_pairs, "port": port_pairs},
        slots, repetitions, seed,
    )
    accuracy = prediction_accuracy(pair_rows, evaluation["pairObservations"])
    methods = evaluation["methods"]
    random_comparison = evaluation["comparisons"]["random"]

    store.save(
        evaluation=evaluation,
        predictionAccuracy=accuracy,
        benchmark={
            # Summary kept for the existing dashboard: baseline = Random.
            "baselineName": "Random",
            "baselineMedianSeconds": methods["random"]["makespan"]["median"],
            "selectedMedianSeconds": methods["harp"]["makespan"]["median"],
            "speedup": random_comparison["speedup"],
            "runtimeReductionPercent": random_comparison["runtimeReductionPercent"],
            "repetitions": repetitions,
            "cpuSets": slots,
            "rawRuns": {
                "baseline": [r["makespanSeconds"] for r in evaluation["runs"]["random"]],
                "selected": [r["makespanSeconds"] for r in evaluation["runs"]["harp"]],
            },
        },
        status="completed",
        stageIndex=8,
        stage="Profiling, pairing and comparative benchmarking completed",
        completedAt=datetime.now(timezone.utc).isoformat(),
    )
