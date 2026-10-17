"""Pair-level interference features.

Two feature sets (config.FEATURE_SET):

* "sa" (default): sensitivity x aggressiveness per shared resource, see
  sa_features(). Validated against measured pairs; replaces Equations 1-8.
* "eq": the manuscript's original Equations 1-8, documented below.

Two workloads are aligned on relative instruction progress: [0, 1] is cut
at the union of both workloads' phase boundaries, and each resulting
interval t has weight pi[t] equal to its length. Within an interval each
workload is in exactly one phase, whose fused features are used. This
assumes both workloads start together and progress proportionally.

    R = sum_t pi[t] * sum_c omega[c] * u[i,c,t] * u[j,c,t]          (1)
    F_pair[t] = F_i[t] + F_j[t]   (no verified shared reuse)        (2)
    K = sum_t pi[t] * clip((F_pair[t] - C_eff) / C_eff, 0, 1)       (3)
    B = sum_t pi[t] * b_i[t] * b_j[t]                               (4)
    O = sum_t pi[t] * cosine(stall_i[t], stall_j[t])                (5)
    X = sum_t pi[t] * m_i[t] * m_j[t]                               (6)
    S = sum_t pi[t] * 0.5 * (FE_i[t]*BE_j[t] + BE_i[t]*FE_j[t])     (7)
    z = [R, K, B, O, X, S]                                          (8)

Footprints and bandwidths are already normalised by the effective shared
cache (C_eff = 1) and B_socket respectively.
"""

import math

from backend import config


def _phase_at(fused, position):
    for segment in fused["segments"]:
        if segment["start"] <= position <= segment["end"]:
            phase_id = segment["phase"]
            break
    else:
        phase_id = fused["segments"][-1]["phase"]

    return next(p["fused"] for p in fused["phases"] if p["id"] == phase_id)


def align(fused_i, fused_j):
    """Return [(pi_t, x_i_t, x_j_t)] over the union of phase boundaries."""

    cuts = {0.0, 1.0}

    for fused in (fused_i, fused_j):
        for segment in fused["segments"]:
            cuts.update((segment["start"], segment["end"]))

    cuts = sorted(c for c in cuts if 0.0 <= c <= 1.0)
    intervals = []

    for start, end in zip(cuts, cuts[1:]):
        if end - start <= 1e-9:
            continue
        middle = (start + end) / 2
        intervals.append(
            (end - start, _phase_at(fused_i, middle), _phase_at(fused_j, middle))
        )

    total = sum(pi for pi, _, _ in intervals) or 1.0
    return [(pi / total, a, b) for pi, a, b in intervals]


def remaining(fused, progress):
    """The part of a workload still to run, from `progress` (0..1) to the end.

    Segments are cut at `progress` and rescaled to [0, 1], so a task that is
    already in its last phase is compared only on that phase.
    """

    progress = max(0.0, min(progress, 0.999))
    span = 1.0 - progress
    segments = [
        {
            "start": (max(s["start"], progress) - progress) / span,
            "end": (s["end"] - progress) / span,
            "phase": s["phase"],
        }
        for s in fused["segments"]
        if s["end"] > progress
    ]
    return {**fused, "segments": segments or fused["segments"][-1:]}


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def sa_breakdown(fused_i, fused_j, sensitivity_i, sensitivity_j, signatures):
    """Per-resource contributions sens x aggr (for explanation only)."""

    return _sa_terms(fused_i, fused_j, sensitivity_i, sensitivity_j, signatures)[1]


def sa_features(fused_i, fused_j, sensitivity_i, sensitivity_j, signatures):
    """Bottleneck sensitivity x aggressiveness:

        H = sum_t pi[t] * 1/2 * ( max_k sens_i,k * aggr_j,k[t]
                                + max_k sens_j,k * aggr_i,k[t] )

    sens_i,k   measured slowdown of i next to stressor k (probing)
    aggr_j,k   j's fused usage of resource k divided by the stressor's own
               usage (signatures), i.e. "how much of a stressor k j is"

    Each thread is slowed mainly by its most contended resource; taking the
    maximum avoids counting the same contention several times (stressors
    overlap). Phases enter through aggressiveness, aligned on instruction
    progress.
    """

    return {"H": _sa_terms(fused_i, fused_j, sensitivity_i, sensitivity_j, signatures)[0]}


def _sa_terms(fused_i, fused_j, sensitivity_i, sensitivity_j, signatures):
    keys = tuple(signatures)
    bottleneck = 0.0
    breakdown = {f"H_{k}": 0.0 for k in keys}

    def aggression(x, k):
        reference = signatures[k]
        if reference <= 0:
            return 0.0
        return min(config.AGGRESSIVENESS_CAP, x[f"agg_{k}"] / reference)

    def sensitivity(values, k):
        return max(0.0, min(config.SENSITIVITY_CAP, values.get(k, 0.0)))

    for pi, a, b in align(fused_i, fused_j):
        suffered_i = {k: sensitivity(sensitivity_i, k) * aggression(b, k) for k in keys}
        suffered_j = {k: sensitivity(sensitivity_j, k) * aggression(a, k) for k in keys}
        bottleneck += pi * 0.5 * (max(suffered_i.values()) + max(suffered_j.values()))
        for k in keys:
            breakdown[f"H_{k}"] += pi * 0.5 * (suffered_i[k] + suffered_j[k])

    return bottleneck, breakdown


def pair_vector(char_i, char_j, model, progress_i=0.0):
    """Model features for workloads i and j (characterize() outputs).

    progress_i > 0 restricts i to its remaining phases (dynamic scheduling).
    """

    fused_i = remaining(char_i["fused"], progress_i) if progress_i else char_i["fused"]

    if model.get("featureSet") == "eq":
        return pair_features(fused_i, char_j["fused"])

    return sa_features(
        fused_i, char_j["fused"],
        char_i["profile"]["sensitivity"], char_j["profile"]["sensitivity"],
        model.get("stressorSignatures") or config.DEFAULT_SIGNATURES,
    )


def pair_features(fused_i, fused_j):
    z = dict.fromkeys(config.PAIR_FEATURES, 0.0)

    for pi, a, b in align(fused_i, fused_j):
        z["R"] += pi * sum(
            weight * a[f"u_{c}"] * b[f"u_{c}"]
            for c, weight in config.RESOURCE_WEIGHTS.items()
        )
        z["K"] += pi * max(0.0, min(1.0, a["footprint"] + b["footprint"] - 1.0))
        z["B"] += pi * a["bandwidth"] * b["bandwidth"]

        stall_a = (a["stall_fe"], a["stall_be_mem"], a["stall_be_core"])
        stall_b = (b["stall_fe"], b["stall_be_mem"], b["stall_be_core"])
        z["O"] += pi * _cosine(stall_a, stall_b)
        z["X"] += pi * a["branch_miss"] * b["branch_miss"]

        be_a = min(1.0, a["stall_be_mem"] + a["stall_be_core"])
        be_b = min(1.0, b["stall_be_mem"] + b["stall_be_core"])
        z["S"] += pi * 0.5 * (a["stall_fe"] * be_b + be_a * b["stall_fe"])

    return z
