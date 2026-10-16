"""Offline calibration of the slowdown model (Equations 9 and 10).

    python -m backend.calibrate [--repetitions 3] [--kernels int,div,...]

The training set is the stressor kernels in kernels/stressors.cpp, never
the example workloads, so the model is evaluated on workloads it has not
seen. For every unordered kernel pair (including a kernel with itself) the
two kernels are co-run on the two SMT siblings of one physical core; the
median per-task co-run times and the solo times give the measured mean and
worst excess slowdown. Coefficients are fitted by non-negative least
squares and checked with leave-one-workload-out validation.

The model is saved to artifacts/model/coefficients.json together with the
profiling mode it was fitted in; jobs only use it in the same mode.
"""

import argparse
from datetime import datetime, timezone
from itertools import combinations_with_replacement
import statistics

from backend import config, kernels, profiler, topology
from backend.analysis import characterize
from backend.execution import ProcessSpec, run_group
from backend.features import pair_features
from backend.model import fit, save_model


def co_run(argv_a, argv_b, slot, repetitions):
    times_a, times_b = [], []

    for _ in range(repetitions):
        run = run_group([
            ProcessSpec("a", argv_a, (slot[0],)),
            ProcessSpec("b", argv_b, (slot[1],)),
        ])
        if run["timedOut"]:
            raise RuntimeError("Calibration co-run timed out")
        for key in ("a", "b"):
            if run["processes"][key]["exitCode"] != 0:
                raise RuntimeError(f"Kernel failed: {run['processes'][key]['stderr']}")
        times_a.append(run["processes"]["a"]["wallSeconds"])
        times_b.append(run["processes"]["b"]["wallSeconds"])

    return statistics.median(times_a), statistics.median(times_b)


def calibrate(names, repetitions):
    topology.pin_harness()
    slot = topology.task_slots()[0]
    mode = profiler.profiling_mode()
    workdir = config.ARTIFACTS_DIR / "calibration" / datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")
    workdir.mkdir(parents=True, exist_ok=True)
    argvs = {n: kernels.argv(n, kernels.TRAINING_UNITS[n]) for n in names}
    characterized = {}

    print(f"Profiling mode: {mode}; CPU pair {slot}", flush=True)

    for name in names:
        characterized[name] = characterize(
            name, kernels.build(name), argvs[name], slot, mode, workdir
        )
        print(f"  profiled {name}: solo "
              f"{characterized[name]['profile']['solo']['median']:.3f} s", flush=True)

    samples = []

    for a, b in combinations_with_replacement(names, 2):
        time_a, time_b = co_run(argvs[a], argvs[b], slot, repetitions)
        slow_a = time_a / characterized[a]["profile"]["solo"]["median"] - 1
        slow_b = time_b / characterized[b]["profile"]["solo"]["median"] - 1
        sample = {
            "pair": [a, b],
            "z": pair_features(characterized[a]["fused"], characterized[b]["fused"]),
            "y": 0.5 * (slow_a + slow_b),
            "yWorst": max(slow_a, slow_b),
            "slowdowns": [slow_a, slow_b],
        }
        samples.append(sample)
        print(f"  {a:>6} + {b:<6} measured mean slowdown {sample['y']:+.3f}", flush=True)

    model = fit(samples)
    topo = topology.discover()
    model.update({
        "profilingMode": mode,
        "kernels": names,
        "repetitions": repetitions,
        "cpuModel": topo["cpuModel"],
        "virtualized": topo["virtualized"],
        "cpuPair": list(slot),
        "samples": samples,
    })
    save_model(model)
    return model


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--kernels", default=",".join(kernels.KERNEL_IDS))
    args = parser.parse_args()
    names = [n.strip() for n in args.kernels.split(",") if n.strip()]

    unknown = set(names) - set(kernels.KERNEL_IDS)
    if unknown:
        raise SystemExit(f"Unknown kernels: {', '.join(sorted(unknown))}")

    model = calibrate(names, args.repetitions)

    print("\n=== CALIBRATED MODEL ===")
    for key, value in model["coefficients"].items():
        print(f"  beta_{key:<9} {value:.4f}")
    print(f"  training MAE        {model['trainingMae']:.4f}")
    if model["heldOutMae"] is not None:
        print(f"  held-out MAE (LOWO) {model['heldOutMae']:.4f} "
              f"over {model['heldOutCount']} pairs")
    print(f"Saved to {config.MODEL_FILE}")


if __name__ == "__main__":
    main()
