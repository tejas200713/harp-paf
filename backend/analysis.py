"""HARP-PAF analysis shared by the job pipeline and calibration.

characterize()  static analysis + runtime profiling + adaptive fusion
pair_table()    Equations 1-11 for every candidate pair
"""

from itertools import combinations
import time

from backend import config, profiler
from backend.features import pair_vector, sa_breakdown
from backend.fusion import fuse
from backend.model import pair_cost
from backend.static_features import analyze_binary


def characterize(task_id, binary, argv, slot, mode, workdir, expected=None):
    static = analyze_binary(binary)
    profile = profiler.profile_workload(
        argv, slot, mode, workdir, task_id, expected
    )
    return {
        "static": static,
        "profile": profile,
        "fused": fuse(static, profile),
    }


def pair_table(task_ids, characterized, model):
    """Pair rows plus the cost table for matching.

    A task paired with IDLE runs alone on the core: its cost is its solo
    time.
    """

    started = time.perf_counter()
    rows = []
    solo = {t: characterized[t]["profile"]["solo"]["median"] for t in task_ids}
    costs = {tuple(sorted((t, config.IDLE))): solo[t] for t in task_ids}

    for a, b in combinations(sorted(task_ids), 2):
        fa = characterized[a]["fused"]
        fb = characterized[b]["fused"]
        z = pair_vector(characterized[a], characterized[b], model)
        cost = pair_cost(
            z, model, fa["meanConfidence"], fb["meanConfidence"], solo[a], solo[b]
        )
        costs[(a, b)] = cost["finalPairCost"]
        rows.append({
            "taskA": a,
            "taskB": b,
            "features": z,
            "contributions": (
                sa_breakdown(
                    fa, fb,
                    characterized[a]["profile"]["sensitivity"],
                    characterized[b]["profile"]["sensitivity"],
                    model.get("stressorSignatures") or config.DEFAULT_SIGNATURES,
                )
                if model.get("featureSet") != "eq" else None
            ),
            **cost,
            "source": model["source"],
        })

    return rows, costs, time.perf_counter() - started
