"""Unit tests for the platform-independent parts of HARP-PAF.

    python -m pytest backend/tests
"""

from itertools import combinations
import random

from backend import config, emon
from backend.baselines import port_matching, random_matching
from backend.features import align, pair_features, remaining
from backend.scheduler import HarpPolicy, PortPolicy
from backend.fusion import FEATURES, fuse, static_only
from backend.model import default_model, fit, nnls, pair_cost, pair_duration
from backend.pairing import (
    all_matchings, matching_cost, matching_count, minimum_matching,
)
from backend.phases import detect
from backend.static_features import classify, static_estimates, user_functions
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

    cost = pair_cost(samples[0]["z"], default_model(), 0.9, 0.9, 1.0, 2.0)
    assert cost["predictedSlowdown"] >= 0
    assert cost["finalPairCost"] >= cost["predictedPairSeconds"] >= 2.0


def test_pair_duration_overlap_model():
    # Longer task 2 s, shorter 1 s, 30% slowdown while overlapping.
    assert abs(pair_duration(1.0, 2.0, 0.3) - 2.3) < 1e-12
    # No interference: the core is busy for the longer task only.
    assert pair_duration(1.5, 1.0, 0.0) == 1.5


def test_idle_costs_make_matching_isolate_the_right_task():
    # Three tasks: pairing B with C is cheap, A alone costs its solo time.
    costs = {("A", "B"): 5.0, ("A", "C"): 5.0, ("B", "C"): 1.2,
             ("A", config.IDLE): 1.0, ("B", config.IDLE): 1.0,
             ("C", config.IDLE): 1.0}
    pairs, total = minimum_matching(["A", "B", "C"], costs)
    assert sorted(map(sorted, pairs)) == [["A", config.IDLE], ["B", "C"]]
    assert abs(total - 2.2) < 1e-12


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


def test_remaining_cuts_phase_timeline_at_progress():
    fused = {"segments": [
        {"start": 0.0, "end": 0.5, "phase": 0},
        {"start": 0.5, "end": 1.0, "phase": 1},
    ]}
    rest = remaining(fused, 0.75)
    assert rest["segments"] == [{"start": 0.0, "end": 1.0, "phase": 1}]
    rest = remaining(fused, 0.25)
    assert [round(s["end"], 6) for s in rest["segments"]] == [round(1 / 3, 6), 1.0]


def _policy_inputs():
    compute = {k: 0.0 for k in FEATURES} | {"u_int_alu": 0.9, "stall_be_core": 0.9}
    memory = {k: 0.0 for k in FEATURES} | {"bandwidth": 0.9, "footprint": 0.9,
                                           "stall_be_mem": 0.9}

    def task(features, solo, fp_share):
        return {
            "fused": {"phases": [{"id": 0, "fused": features}],
                      "segments": [{"start": 0.0, "end": 1.0, "phase": 0}],
                      "meanConfidence": 0.5},
            "profile": {"solo": {"median": solo}},
            "static": _static(fp_simd=fp_share, int_alu=1 - fp_share),
        }

    return {
        "MEM1": task(memory, 1.0, 0.0),
        "MEM2": task(memory, 1.2, 0.0),
        "CPU1": task(compute, 0.8, 0.9),
    }


def test_harp_policy_avoids_memory_co_runner_for_memory_task():
    characterized = _policy_inputs()
    policy = HarpPolicy(characterized, default_model())

    assert policy.start(["MEM1", "MEM2", "CPU1"]) == "MEM2"   # longest first
    choice, slowdown = policy.choose("MEM2", 0.0, ["MEM1", "CPU1"])
    assert choice == "CPU1"
    assert slowdown >= 0


def test_port_policy_pairs_intensive_with_light():
    policy = PortPolicy(_policy_inputs())

    assert policy.start(["MEM1", "MEM2", "CPU1"]) == "CPU1"   # most port-intensive
    assert policy.choose("CPU1", 0.0, ["MEM1", "MEM2"])[0] == "MEM2"


def test_classify_att_syntax():
    assert classify("movq", "$0x0,-0x8(%rbp)") == ("load_store", True)
    assert classify("mov", "%rax,%rbx") == ("int_alu", False)
    assert classify("mulps", "%xmm1,%xmm0") == ("fp_simd", False)
    assert classify("sqrtsd", "%xmm0,%xmm0") == ("fp_simd", False)
    assert classify("imul", "%rax,%rbx") == ("mul_div", False)
    assert classify("divq", "%rcx") == ("mul_div", False)
    assert classify("jne", "1150 <main+0x20>") == ("branch", False)
    assert classify("add", "(%rax),%rbx") == ("int_alu", True)


def test_user_functions_follow_calls_from_main_only():
    functions = {
        "main": [(1, "call", "10 <__main>"), (2, "call", "20 <left(int)>"),
                 (3, "call", "30 <memset>"), (4, "call", "40 <std::ostream::put(char)>")],
        "__main": [(10, "ret", "")],
        "left(int)": [(20, "call", "50 <helper()+0x4>")],
        "memset": [(30, "ret", "")],
        "std::ostream::put(char)": [(40, "ret", "")],
        "helper()": [(50, "ret", "")],
        "unused()": [(60, "ret", "")],
    }
    assert user_functions(functions) == ["helper()", "left(int)", "main"]


def test_emon_parse_reads_one_cpu_column_and_pairs_groups():
    def row(event, cpu0, cpu1):
        return f"{event}\t125,000,000\t{cpu0:,}\t{cpu1:,}\t"

    block = "\n".join([
        "Version Info: public V11.61",
        row("INST_RETIRED.ANY", 5, 200_000_000),
        row("CPU_CLK_UNHALTED.THREAD", 9, 100_000_000),
        row("LONGEST_LAT_CACHE.REFERENCE", 0, 4_000_000),
        row("LONGEST_LAT_CACHE.MISS", 0, 1_000_000),
        row("BR_INST_RETIRED.ALL_BRANCHES", 0, 20_000_000),
        row("BR_MISP_RETIRED.ALL_BRANCHES", 0, 400_000),
        row("ARITH.DIV_ACTIVE", 0, 0),
        row("FP_ARITH_INST_RETIRED.SCALAR", 0, 0),
        "----------",
        row("INST_RETIRED.ANY", 5, 200_000_000),
        row("CPU_CLK_UNHALTED.THREAD", 9, 100_000_000),
        row("FP_ARITH_INST_RETIRED.VECTOR", 0, 0),
        "MEM_INST_RETIRED.ALL_LOADS\t125,000,000\tN/A\t40,000,000\t",
        row("MEM_INST_RETIRED.ALL_STORES", 0, 20_000_000),
        row("IDQ_BUBBLES.CORE", 0, 60_000_000),
        row("TOPDOWN.BACKEND_BOUND_SLOTS", 0, 120_000_000),
        "==========",
    ])
    samples = emon.parse(block, cpu=1)
    windows, totals = emon.windows(samples)
    m = windows[0]["measures"]

    assert len(samples) == 2 and len(windows) == 1
    assert abs(m["ipc"] - 2.0) < 1e-12
    assert abs(m["footprint"] - 20 / 20.0) < 1e-12          # 20 refs per kilo-instr
    assert abs(m["branch_miss"] - 2 / 10.0) < 1e-12         # 2 MPKI
    assert abs(m["stall_fe"] - 0.1) < 1e-12                  # 60M / (6 * 100M)
    assert abs(sum(m[f"mix_{r}"] for r in config.RESOURCES) - 1) < 1e-12
    assert abs(m["mix_load_store"] - 0.3) < 1e-12
    assert totals["instructions"] == 400_000_000


def test_measurement_lock_blocks_a_second_measurement(tmp_path, monkeypatch):
    import pytest
    from backend.measurement_lock import MeasurementBusy, measurement_lock

    monkeypatch.setattr(config, "MEASUREMENT_LOCK", tmp_path / "lock")

    with measurement_lock("first"):
        with pytest.raises(MeasurementBusy, match="first"):
            with measurement_lock("second"):
                pass

    with measurement_lock("third"):
        pass


def test_stats_helpers():
    summary = summarize([1.0, 2.0, 3.0, 4.0, 5.0])
    assert summary["median"] == 3.0
    assert summary["ci95"][0] <= 3.0 <= summary["ci95"][1]
    assert abs(spearman([1, 2, 3, 4], [10, 20, 30, 40]) - 1.0) < 1e-12
