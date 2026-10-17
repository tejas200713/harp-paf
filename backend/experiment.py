"""Run one HARP-PAF comparison from the command line (no web server).

    python -m backend.experiment [--repetitions 5] [w1_integer_hash.cpp ...]

Without file names all eight w*.cpp workloads in examples/ are used. The
job is stored under artifacts/<jobId>/ exactly like a job submitted through
the API, so it also appears in the dashboard's history. Run from an
elevated terminal on Windows to profile with EMON hardware counters.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import uuid

from backend import config, topology
from backend.approved_workloads import get_workload
from backend.pipeline import process_job


def create_job(names, repetitions):
    job_id = uuid.uuid4().hex
    job_dir = config.ARTIFACTS_DIR / job_id
    job_dir.mkdir(parents=True)
    files = []

    for index, name in enumerate(names, start=1):
        content = (config.EXAMPLES_DIR / name).read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        workload = get_workload("cpp", digest)

        if not workload:
            raise SystemExit(f"{name} is not an approved workload")

        (job_dir / f"task{index}.cpp").write_bytes(content)
        files.append({
            "taskId": f"T{index:02d}", "originalName": name,
            "savedName": f"task{index}.cpp", "size": len(content),
            "sha256": digest, "workloadKind": workload.get("kind"),
        })

    job = {
        "jobId": job_id, "status": "running", "stageIndex": 0,
        "stage": "Queued for execution", "language": "cpp",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "files": files, "repetitions": repetitions,
        "measurementMode": "local-cli",
    }
    (job_dir / "job.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
    return job_id


def report(job):
    evaluation = job["evaluation"]
    accuracy = job["predictionAccuracy"]
    names = {f["taskId"]: f["originalName"] for f in job["files"]}

    print(f"\nProfiling mode: {job['profilingMode']}   model: {job['model']['source']}"
          f"   SMT core(s): {job['benchmark']['cpuSets']}")
    for task_id, item in job["characterization"].items():
        print(f"  {task_id} {names[task_id]:24s} solo {item['profile']['solo']['median']:.3f} s"
              f"  phases {len(item['fused']['phases'])}"
              f"  confidence {item['fused']['meanConfidence']:.2f}")

    print(f"\nHARP-PAF pairs: {job['selectedPairs']}  (predicted {job['minimumCost']:.3f} s)")
    print(f"PORT pairs:     {job['portPairs']}")
    print(f"Serial (each workload alone, one after another; measured median): "
          f"{evaluation['serialSoloSeconds']:.3f} s\n")
    print(f"{'method':24s} {'makespan (median, 95% CI)':30s} {'vs serial':>9s} {'ANTT':>6s}")

    for method, summary in evaluation["methods"].items():
        makespan = summary["makespan"]
        print(f"{summary['label']:24s} {makespan['median']:7.3f} s "
              f"[{makespan['ci95'][0]:.3f}, {makespan['ci95'][1]:.3f}]"
              f"{summary['smtGainVsSerialPercent']:+12.1f}% {summary['antt']['median']:6.2f}")

    harp_timeline = evaluation["runs"]["harp"][0]["timeline"]
    print("\nHARP-PAF schedule (first repetition):")
    for item in harp_timeline:
        partner = item["startedWith"] or "-"
        print(f"  cpu {item['cpu']}: {item['task']} {item['start']:6.3f}-{item['end']:6.3f} s"
              f"  started next to {partner}"
              f"  (predicted slowdown {item['predictedSlowdown']:.2f})")

    print()
    for method, comparison in evaluation["comparisons"].items():
        print(f"HARP-PAF vs {comparison['label']:24s} speedup {comparison['speedup']:.3f}x "
              f"(95% CI {comparison['speedupCi95'][0]:.3f}-{comparison['speedupCi95'][1]:.3f}), "
              f"faster in {comparison['harpFasterInRuns']}/{evaluation['repetitions']} runs")

    if accuracy.get("mae") is not None:
        rank = accuracy["pairSecondsSpearman"]
        print(f"\nPrediction: slowdown MAE {accuracy['mae']:.3f}, "
              f"pair-duration MAPE {accuracy['pairSecondsMape']:.1f}%, "
              f"rank correlation {'n/a' if rank is None else f'{rank:.2f}'} "
              f"over {accuracy['count']} observed pairs")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("workloads", nargs="*")
    parser.add_argument("--repetitions", type=int, default=config.EVAL_REPETITIONS)
    args = parser.parse_args()
    names = args.workloads or sorted(p.name for p in config.EXAMPLES_DIR.glob("w*.cpp"))

    topology.pin_harness()
    job_id = create_job(names, args.repetitions)
    print(f"Job {job_id}: {len(names)} workloads, {args.repetitions} repetitions")
    process_job(job_id, args.repetitions)
    job = json.loads((config.ARTIFACTS_DIR / job_id / "job.json").read_text(encoding="utf-8"))

    if job["status"] != "completed":
        raise SystemExit(f"Job failed: {job.get('error')}")

    report(job)


if __name__ == "__main__":
    main()
