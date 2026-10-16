"""HARP-PAF analysis shared by the job pipeline and calibration.

characterize()  static analysis + runtime profiling + adaptive fusion
pair_table()    Equations 1-11 for every candidate pair
"""

from itertools import combinations
import time

from backend import profiler
from backend.features import pair_features
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
    started = time.perf_counter()
    rows = []
    costs = {}

    for a, b in combinations(sorted(task_ids), 2):
        fa = characterized[a]["fused"]
        fb = characterized[b]["fused"]
        z = pair_features(fa, fb)
        cost = pair_cost(z, model, fa["meanConfidence"], fb["meanConfidence"])
        costs[(a, b)] = cost["finalPairCost"]
        rows.append({
            "taskA": a,
            "taskB": b,
            "features": z,
            **cost,
            "source": model["source"],
        })

    return rows, costs, time.perf_counter() - started
