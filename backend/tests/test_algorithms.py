"""Unit tests for the platform-independent parts of HARP-PAF.

    python -m pytest backend/tests
"""

from itertools import combinations
import random

from backend import config
from backend.baselines import port_matching, random_matching
from backend.features import align, pair_features
from backend.fusion import FEATURES, fuse, static_only
from backend.model import fit, nnls, pair_cost, default_model
from backend.pairing import (
    all_matchings, matching_cost, matching_count, minimum_matching,
)
from backend.phases import detect
from backend.static_features import classify, static_estimates
from backend.stats import spearman, summarize


def _static(**mix):
    base = dict.fromkeys(config.RESOURCES, 0.0)
    base.update(mix)
    total = sum(base.values())
    return {
        "instructionMix": {k: v / total for k, v in base.items()},
        "memoryOperandShare": base["load_store"] / total,
    }


def test_matching_is_optimal_against_brute_force():
    rng = random.Random(1)

    for n in (2, 3, 4, 5, 6, 7, 8):
        ids = [f"T{i:02d}" for i in range(n)]
        costs = {(a, b): rng.random() for a, b in combinations(ids, 2)}
        pairs, total = minimum_matching(ids, costs)
        nodes = ids + ([config.IDLE] if n % 2 else [])
        best = min(matching_cost(m, costs) for m in all_matchings(nodes))

        assert abs(total - best) < 1e-12
        assert sorted(t for p in pairs for t in p if t != config.IDLE) == ids


def test_matching_count():
    assert matching_count(4) == 3
    assert matching_count(8) == 105
    assert matching_count(5) == 15


def test_port_pairs_most_with_least_intensive():
    statics = {
        "A": _static(fp_simd=9, int_alu=1),
        "B": _static(fp_simd=5, int_alu=5),
        "C": _static(fp_simd=1, int_alu=9),
        "D": _static(fp_simd=0, int_alu=10),
    }
    assert port_matching(list(statics), statics) == [["A", "D"], ["B", "C"]]

    del statics["D"]
    assert port_matching(list(statics), statics) == [["A", config.IDLE], ["B", "C"]]


def test_random_matching_covers_every_task():
    pairs = random_matching(["a", "b", "c", "d", "e"], random.Random(3))
    flat = sorted(t for p in pairs for t in p)
    assert flat == sorted(["a", "b", "c", "d", "e", config.IDLE])


def test_nnls_recovers_nonnegative_coefficients():
    rng = random.Random(0)
    truth = [0.05, 0.8, 0.0, 0.3]
    rows = [[1.0] + [rng.random() for _ in range(3)] for _ in range(60)]
    targets = [sum(a * b for a, b in zip(r, truth)) for r in rows]
    fitted = nnls(rows, targets)

    assert all(abs(a - b) < 1e-4 for a, b in zip(fitted, truth))


def test_fit_and_cost_are_sane():
    rng = random.Random(2)
    names = [f"k{i}" for i in range(7)]
    samples = []

    for a, b in combinations(names, 2):
        z = {f: rng.random() for f in config.PAIR_FEATURES}
        y = 0.6 * z["R"] + 0.4 * z["B"] - 0.1 * z["S"]
        samples.append({"pair": [a, b], "z": z, "y": y, "yWorst": 1.4 * y})

    model = fit(samples)
    assert model["trainingMae"] < 0.05
    assert model["heldOutMae"] is not None

    cost = pair_cost(samples[0]["z"], default_model(), 0.9, 0.9)
    assert cost["finalPairCost"] >= cost["predictedSlowdown"] >= 0


def test_phase_detection_finds_two_phases():
    windows = []
    for i in range(20):
        measures = (
            {"intensity": 0.8, "footprint": 0.1, "bandwidth": 0.0, "branch_miss": 0.0}
            if i < 10 else
            {"intensity": 0.2, "footprint": 0.9, "bandwidth": 0.7, "branch_miss": 0.0}
        )
        windows.append({"progress": (i / 20, (i + 1) / 20), "measures": measures})

    result = detect(windows)

    assert len(result["phases"]) == 2
    assert abs(sum(p["share"] for p in result["phases"]) - 1) < 1e-9
    assert result["segments"][0]["end"] == 0.5


def test_phase_detection_merges_short_spikes_and_reuses_labels():
    windows = []
    pattern = [0.8] * 6 + [0.1] + [0.8] * 3 + [0.2] * 6 + [0.8] * 6
    for i, value in enumerate(pattern):
        windows.append({
            "progress": (i / len(pattern), (i + 1) / len(pattern)),
            "measures": {"intensity": value},
        })

    result = detect(windows)
    labels = [s["phase"] for s in result["segments"]]

    assert len(result["phases"]) == 2
    assert labels[0] == labels[-1]


def test_fusion_uses_static_when_runtime_missing():
    static = _static(int_alu=6, load_store=4)
    fused = static_only(static)
    s = static_estimates(static)

    assert fused["phases"][0]["fused"] == s
    assert set(FEATURES) == set(s)


def test_fusion_weights_runtime_by_confidence():
    static = _static(int_alu=5, load_store=5)
    profile = {
        "mode": "probe",
        "solo": {"cv": 0.0},
        "phaseProfile": {
            "phases": [{
                "id": 0, "share": 1.0, "windowCount": 0, "cv": {},
                "measures": {f"sens_{k}": 1.0 for k in config.PROBE_KERNELS},
            }],
            "segments": [{"start": 0.0, "end": 1.0, "phase": 0}],
        },
    }
    phase = fuse(static, profile)["phases"][0]
    s = static_estimates(static)

    expected = config.Q_MAX * 1.0 + (1 - config.Q_MAX) * s["bandwidth"]
    assert abs(phase["fused"]["bandwidth"] - expected) < 1e-12

    profile["solo"]["cv"] = 1.0  # very noisy timing: fall back to static
    phase = fuse(static, profile)["phases"][0]
    assert phase["fused"]["bandwidth"] == s["bandwidth"]


def test_pair_features_follow_phase_alignment():
    compute = {k: 0.0 for k in FEATURES} | {"u_int_alu": 1.0, "stall_be_core": 1.0}
    memory = {k: 0.0 for k in FEATURES} | {"bandwidth": 1.0, "footprint": 0.9,
                                           "stall_be_mem": 1.0}

    def workload(phases, segments):
        return {"phases": [{"id": i, "fused": p} for i, p in enumerate(phases)],
                "segments": segments}

    phased = workload([compute, memory], [
        {"start": 0.0, "end": 0.5, "phase": 0},
        {"start": 0.5, "end": 1.0, "phase": 1},
    ])
    streaming = workload([memory], [{"start": 0.0, "end": 1.0, "phase": 0}])

    assert len(align(phased, streaming)) == 2
    z = pair_features(phased, streaming)
    # Bandwidth overlaps only in the second half of the phased workload.
    assert abs(z["B"] - 0.5) < 1e-12
    assert abs(z["K"] - 0.5 * 0.8) < 1e-12


def test_classify_att_syntax():
    assert classify("movq", "$0x0,-0x8(%rbp)") == ("load_store", True)
    assert classify("mov", "%rax,%rbx") == ("int_alu", False)
    assert classify("mulps", "%xmm1,%xmm0") == ("fp_simd", False)
    assert classify("sqrtsd", "%xmm0,%xmm0") == ("fp_simd", False)
    assert classify("imul", "%rax,%rbx") == ("mul_div", False)
    assert classify("divq", "%rcx") == ("mul_div", False)
    assert classify("jne", "1150 <main+0x20>") == ("branch", False)
    assert classify("add", "(%rax),%rbx") == ("int_alu", True)


def test_stats_helpers():
    summary = summarize([1.0, 2.0, 3.0, 4.0, 5.0])
    assert summary["median"] == 3.0
    assert summary["ci95"][0] <= 3.0 <= summary["ci95"][1]
    assert abs(spearman([1, 2, 3, 4], [10, 20, 30, 40]) - 1.0) < 1e-12
