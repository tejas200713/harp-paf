
from itertools import combinations
from math import isfinite


TASK_IDS = ("T01", "T02", "T03", "T04")


def find_best_matching(pair_costs):
    """
    Find the minimum-cost perfect matching of four tasks.

    pair_costs:
        Dictionary mapping task pairs to numeric costs.

    Returns:
        All three matchings and the selected matching.
    """

    required_pairs = list(combinations(TASK_IDS, 2))

    if set(pair_costs.keys()) != set(required_pairs):
        raise ValueError(
            "Exactly six pair costs are required: "
            "T01-T02, T01-T03, T01-T04, "
            "T02-T03, T02-T04, T03-T04"
        )

    for pair, cost in pair_costs.items():
        if isinstance(cost, bool) or not isinstance(cost, (int, float)):
            raise ValueError(f"Invalid cost for {pair}")

        if not isfinite(cost) or cost < 0:
            raise ValueError(f"Cost must be finite and non-negative: {pair}")

    matchings = [
        (("T01", "T02"), ("T03", "T04")),
        (("T01", "T03"), ("T02", "T04")),
        (("T01", "T04"), ("T02", "T03")),
    ]

    results = []

    for index, matching in enumerate(matchings, start=1):
        total_cost = sum(pair_costs[pair] for pair in matching)

        results.append({
            "matching": f"M{index}",
            "pairs": matching,
            "totalCost": total_cost,
        })

    best = min(results, key=lambda item: item["totalCost"])

    selected_tasks = [
        task
        for pair in best["pairs"]
        for task in pair
    ]

    assert len(selected_tasks) == 4
    assert set(selected_tasks) == set(TASK_IDS)

    return {
        "allMatchings": results,
        "selectedMatching": best,
        "selectedPairs": best["pairs"],
        "minimumCost": best["totalCost"],
    }


if __name__ == "__main__":
    # Synthetic test costs ONLY.
    # These are not measured performance values.

    test_costs = {
        ("T01", "T02"): 8,
        ("T01", "T03"): 2,
        ("T01", "T04"): 7,
        ("T02", "T03"): 6,
        ("T02", "T04"): 3,
        ("T03", "T04"): 9,
    }

    result = find_best_matching(test_costs)

    for item in result["allMatchings"]:
        print(
            item["matching"],
            item["pairs"],
            "Total cost:",
            item["totalCost"]
        )

    print()
    print("Selected:", result["selectedMatching"]["matching"])
    print("Selected pairs:", result["selectedPairs"])
    print("Minimum cost:", result["minimumCost"])

    assert result["selectedMatching"]["matching"] == "M2"
    assert result["minimumCost"] == 5

    print("STEP 10.1 TEST PASSED")
