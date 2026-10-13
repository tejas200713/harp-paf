
"""Transparent, illustrative workload heuristic for HARP-PAF.

All profile values are manually assigned estimates based on
the four reviewed C++ demonstration programs.

These are NOT measured hardware resource demands.
"""

from itertools import combinations

from backend.pairing import TASK_IDS, find_best_matching


# Resource scores: 0 = low/absent, 3 = high.
#
# Source observations:
# T01: integer addition loop
# T02: modulo-heavy integer loop with volatile accesses
# T03: vector initialization and sequential traversal
# T04: floating-point square root loop
#
# These are illustrative ordinal profiles, not calibrated
# predictions of performance or SMT contention.

WORKLOAD_PROFILES = {
    "T01": {
        "integer": 3,
        "floating_point": 0,
        "memory": 1,
        "modulo": 0,
    },
    "T02": {
        "integer": 2,
        "floating_point": 0,
        "memory": 2,
        "modulo": 3,
    },
    "T03": {
        "integer": 2,
        "floating_point": 0,
        "memory": 3,
        "modulo": 2,
    },
    "T04": {
        "integer": 0,
        "floating_point": 3,
        "memory": 1,
        "modulo": 0,
    },
}

WEIGHTS = {
    "integer": 1.0,
    "floating_point": 1.0,
    "memory": 1.5,
    "modulo": 1.0,
}


def calculate_pair_cost(task_a, task_b):
    """Calculate a weighted resource-overlap heuristic."""

    profile_a = WORKLOAD_PROFILES[task_a]
    profile_b = WORKLOAD_PROFILES[task_b]

    components = {}

    for resource, weight in WEIGHTS.items():
        # Normalized overlap between 0 and 1.
        overlap = (
            profile_a[resource] * profile_b[resource]
        ) / 9.0

        components[resource] = round(
            overlap * weight, 6
        )

    total = round(sum(components.values()), 6)

    return {
        "taskA": task_a,
        "taskB": task_b,
        "finalPairCost": total,
        "features": components,
        "source": "heuristic",
        "predictedSlowdown": None,
    }


def analyze_workloads():
    """Evaluate six pairs and all three perfect matchings."""

    pair_results = []
    pair_costs = {}

    for task_a, task_b in combinations(TASK_IDS, 2):
        result = calculate_pair_cost(task_a, task_b)

        pair_results.append(result)
        pair_costs[(task_a, task_b)] = result[
            "finalPairCost"
        ]

    matching_result = find_best_matching(pair_costs)

    return {
        "model": "manual-resource-overlap-v1",
        "modelType": "illustrative-heuristic",
        "measuredPredictionAccuracy": None,
        "pairCosts": pair_results,
        "allMatchings": matching_result["allMatchings"],
        "selectedMatching": matching_result[
            "selectedMatching"
        ],
        "selectedPairs": matching_result["selectedPairs"],
        "minimumCost": matching_result["minimumCost"],
        "profiles": WORKLOAD_PROFILES,
        "weights": WEIGHTS,
    }


if __name__ == "__main__":
    result = analyze_workloads()

    print("HARP-PAF HEURISTIC ANALYSIS")
    print("---------------------------")

    for pair in result["pairCosts"]:
        print(
            pair["taskA"],
            "+",
            pair["taskB"],
            "=",
            f'{pair["finalPairCost"]:.6f}'
        )

    print("\nMATCHINGS")

    for matching in result["allMatchings"]:
        print(
            matching["matching"],
            "cost:",
            f'{matching["totalCost"]:.6f}'
        )

    print("\nSELECTED PAIRS")

    for task_a, task_b in result["selectedPairs"]:
        print(task_a, "+", task_b)

    print("\nMODEL:", result["model"])
    print("DATA SOURCE: ILLUSTRATIVE HEURISTIC")

    assert len(result["pairCosts"]) == 6
    assert len(result["allMatchings"]) == 3
    assert len(result["selectedPairs"]) == 2

    used_tasks = [
        task
        for pair in result["selectedPairs"]
        for task in pair
    ]

    assert len(set(used_tasks)) == 4
    assert set(used_tasks) == set(TASK_IDS)

    print("\nSTEP 10.2 TEST PASSED")
