"""Phase-aware adaptive fusion of static and runtime evidence.

For workload i, phase t and feature k:

    x(i,k,t) = q(i,k,t) * d(i,k,t) + (1 - q(i,k,t)) * s(i,k)

s is the static estimate (Algorithm A), d the runtime estimate
(Algorithm B) and q in [0, Q_MAX] the confidence in the runtime estimate:

* q = 0 when the runtime profiler cannot observe feature k
  (for example an unsupported perf event), so static evidence is used;
* otherwise q = Q_MAX * stability * support, where stability falls
  linearly to 0 as the measurement's coefficient of variation reaches
  CV_REFERENCE (within-phase window variation in perf mode, run-to-run
  solo variation in probe mode), and support = min(1, windows /
  PHASE_MIN_WINDOWS) penalises phases observed in very few windows.

Q_MAX < 1 keeps some static weight even for a clean measurement.
Plain concatenation would be static and runtime side by side; here the
weights change per workload, per phase and per feature.
"""

from backend import config
from backend.static_features import static_estimates

FEATURES = (
    *(f"u_{r}" for r in config.RESOURCES),
    "footprint", "bandwidth", "stall_fe", "stall_be_mem",
    "stall_be_core", "branch_miss",
)


def _stability(variation, reference):
    return max(0.0, 1.0 - variation / reference)


def _perf_estimates(measures, cvs, static, windows):
    mix = static["instructionMix"]
    support = min(1.0, windows / config.PHASE_MIN_WINDOWS)
    d, q = {}, {}

    def put(feature, value, source_key):
        if value is None:
            d[feature], q[feature] = None, 0.0
            return
        d[feature] = value
        q[feature] = config.Q_MAX * support * _stability(
            cvs.get(source_key, 0.0), config.CV_REFERENCE_WINDOW
        )

    intensity = measures.get("intensity")

    for r in config.RESOURCES:
        put(f"u_{r}", None if intensity is None else mix[r] * intensity,
            "intensity")

    footprint = measures.get("footprint")
    be = measures.get("stall_be")
    put("footprint", footprint, "footprint")
    put("bandwidth", measures.get("bandwidth"), "bandwidth")
    put("branch_miss", measures.get("branch_miss"), "branch_miss")
    put("stall_fe", measures.get("stall_fe"), "stall_fe")
    put("stall_be_mem",
        None if be is None or footprint is None else be * footprint,
        "stall_be")
    put("stall_be_core",
        None if be is None or footprint is None else be * (1 - footprint),
        "stall_be")
    return d, q


def _probe_estimates(measures, solo_cv):
    sens = {k[5:]: v for k, v in measures.items() if k.startswith("sens_")}
    confidence = config.Q_MAX * _stability(solo_cv, config.CV_REFERENCE_SOLO)
    d = {
        "u_int_alu": sens.get("int"),
        "u_mul_div": sens.get("int"),
        "u_fp_simd": sens.get("fp"),
        "u_load_store": sens.get("cache"),
        "u_branch": sens.get("branch"),
        "footprint": sens.get("cache"),
        "bandwidth": sens.get("stream"),
        "branch_miss": sens.get("branch"),
        "stall_fe": sens.get("branch"),
        "stall_be_mem": max(sens.get("stream", 0.0), sens.get("cache", 0.0)),
        "stall_be_core": max(sens.get("int", 0.0), sens.get("fp", 0.0)),
    }
    q = {k: (0.0 if v is None else confidence) for k, v in d.items()}
    return d, q


def fuse(static, profile):
    """Return the fused, phase-aware representation of one workload."""

    s = static_estimates(static)
    phase_profile = profile["phaseProfile"]
    fused_phases = []

    for phase in phase_profile["phases"]:
        if profile["mode"] == "perf":
            d, q = _perf_estimates(
                phase["measures"], phase["cv"], static, phase["windowCount"]
            )
        else:
            d, q = _probe_estimates(phase["measures"], profile["solo"]["cv"])

        x = {
            k: q[k] * d[k] + (1 - q[k]) * s[k] if d.get(k) is not None else s[k]
            for k in FEATURES
        }
        fused_phases.append({
            "id": phase["id"],
            "share": phase["share"],
            "static": s,
            "dynamic": d,
            "confidence": q,
            "fused": x,
        })

    return {
        "mode": profile["mode"],
        "phases": fused_phases,
        "segments": phase_profile["segments"],
        "meanConfidence": sum(
            p["share"] * sum(p["confidence"].values()) / len(FEATURES)
            for p in fused_phases
        ),
    }


def static_only(static):
    """Fused representation with q = 0 everywhere (used by ablations)."""

    s = static_estimates(static)
    return {
        "mode": "static",
        "phases": [{
            "id": 0, "share": 1.0, "static": s, "dynamic": {},
            "confidence": {k: 0.0 for k in FEATURES}, "fused": s,
        }],
        "segments": [{"start": 0.0, "end": 1.0, "phase": 0}],
        "meanConfidence": 0.0,
    }
