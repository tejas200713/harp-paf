"""Offline calibration of the slowdown model (Equations 9 and 10).

    python -m backend.calibrate [--repetitions 3] [--kernels int,div,...]

The training set is the stressor kernels in kernels/stressors.cpp, never
the example workloads, so the model is evaluated on workloads it has not
seen. The SMT core is first warmed up to a steady clock. For every
unordered kernel pair (including a kernel with itself) the two kernels are
co-run on the two SMT siblings of one physical core, and each repetition
also times both kernels alone right next to the co-run (shuffled order),
so clock drift cancels out; the median per-task ratios give the measured
mean and worst excess slowdown. Coefficients are fitted by non-negative
least squares and checked with leave-one-workload-out validation.

The model is saved to artifacts/model/coefficients.json together with the
profiling mode it was fitted in; jobs only use it in the same mode.
"""

import argparse
from datetime import datetime, timezone
from itertools import combinations_with_replacement
import random
import statistics

from backend import config, kernels, profiler, topology
from backend.analysis import characterize
from backend.execution import ProcessSpec, run_group
from backend.features import pair_vector
from backend.measurement_lock import measurement_lock
from backend.model import fit, save_model


def stressor_signatures(characterized):
    """Each probe stressor's own fused aggressiveness on its resource.

    Aggressiveness of any workload is normalised by these, so "1.0" means
    "uses resource k as heavily as stressor k does".
    """

    signatures = dict(config.DEFAULT_SIGNATURES)

    for name in config.PROBE_KERNELS:
        if name in characterized:
            phases = characterized[name]["fused"]["phases"]
            signatures[name] = sum(p["share"] * p["fused"][f"agg_{name}"] for p in phases)

    return signatures


def _timed(specs):
    run = run_group(specs)

    if run["timedOut"]:
        raise RuntimeError("Calibration run timed out")

    for key, entry in run["processes"].items():
        if entry["exitCode"] != 0:
            raise RuntimeError(f"Kernel failed: {entry['stderr']}")

    return {key: entry["wallSeconds"] for key, entry in run["processes"].items()}


def co_run(argv_a, argv_b, slot, repetitions, rng):
    """Median per-task slowdown of a co-run against adjacent solo runs.

    Every repetition times solo a, solo b and the co-run back to back in a
    shuffled order, so slow drift in clock speed cancels out of the ratio.
    """

    ratios_a, ratios_b = [], []

    for _ in range(repetitions):
        steps = ["solo_a", "solo_b", "co"]
        rng.shuffle(steps)
        times = {}

        for step in steps:
            if step == "solo_a":
                times["solo_a"] = _timed([ProcessSpec("a", argv_a, (slot[0],))])["a"]
            elif step == "solo_b":
                times["solo_b"] = _timed([ProcessSpec("b", argv_b, (slot[0],))])["b"]
            else:
                co = _timed([
                    ProcessSpec("a", argv_a, (slot[0],)),
                    ProcessSpec("b", argv_b, (slot[1],)),
                ])
                times["co_a"], times["co_b"] = co["a"], co["b"]

        ratios_a.append(times["co_a"] / times["solo_a"] - 1)
        ratios_b.append(times["co_b"] / times["solo_b"] - 1)

    return statistics.median(ratios_a), statistics.median(ratios_b)


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

    print(f"Profiling mode: {mode}; CPU pair {slot}; warming up "
          f"{config.WARMUP_SECONDS:.0f} s", flush=True)
    profiler.warm_up(slot)
    rng = random.Random(0)

    for name in names:
        characterized[name] = characterize(
            name, kernels.build(name), argvs[name], slot, mode, workdir
        )
        print(f"  profiled {name}: solo "
              f"{characterized[name]['profile']['solo']['median']:.3f} s", flush=True)

    signatures = stressor_signatures(characterized)
    provisional = {"featureSet": config.FEATURE_SET, "stressorSignatures": signatures}
    print(f"  stressor signatures: { {k: round(v, 3) for k, v in signatures.items()} }",
          flush=True)
    samples = []

    for a, b in combinations_with_replacement(names, 2):
        slow_a, slow_b = co_run(argvs[a], argvs[b], slot, repetitions, rng)
        sample = {
            "pair": [a, b],
            "z": pair_vector(characterized[a], characterized[b], provisional),
            "y": 0.5 * (slow_a + slow_b),
            "yWorst": max(slow_a, slow_b),
            "slowdowns": [slow_a, slow_b],
        }
        samples.append(sample)
        print(f"  {a:>6} + {b:<6} measured mean slowdown {sample['y']:+.3f}", flush=True)

    model = fit(samples, config.FEATURE_SET)
    topo = topology.discover()
    model.update({
        "stressorSignatures": signatures,
        "kernelSensitivity": {
            n: characterized[n]["profile"]["sensitivity"] for n in names
        },
        "profilingMode": mode,
        "platform": topo["platform"],
        "kernels": names,
        "repetitions": repetitions,
        "cpuModel": topo["cpuModel"],
        "virtualized": topo["virtualized"],
        "cpuPair": list(slot),
        "samples": samples,
    })
    model["savedTo"] = str(save_model(model))
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

    with measurement_lock("calibration"):
        model = calibrate(names, args.repetitions)

    print("\n=== CALIBRATED MODEL ===")
    for key, value in model["coefficients"].items():
        print(f"  beta_{key:<9} {value:.4f}")
    print(f"  training MAE        {model['trainingMae']:.4f}")
    if model["heldOutMae"] is not None:
        print(f"  held-out MAE (LOWO) {model['heldOutMae']:.4f} "
              f"over {model['heldOutCount']} pairs")
    print(f"Saved to {model['savedTo']}")


if __name__ == "__main__":
    main()
