"""Global workload-pair selection (manuscript Section 3.6.9).

Workloads are nodes of a complete graph with edge weights J_ij. The
selected placement is a minimum-weight perfect matching, computed exactly
by dynamic programming over subsets (O(2^n * n), n <= 16). It returns the
same optimum a Blossom implementation would, and ties are broken
deterministically by the lexicographic order of task IDs.

When the number of workloads is odd an IDLE node is added; pairing a
workload with IDLE means it runs alone on a physical core, at the cost given
for (task, IDLE) in the cost table (its solo time), or 0 if none is given.
"""

from functools import lru_cache
from itertools import islice

from backend import config


def with_idle(task_ids):
    task_ids = sorted(task_ids)
    return task_ids + [config.IDLE] if len(task_ids) % 2 else task_ids


def _key(a, b):
    return tuple(sorted((a, b)))


def edge_cost(costs, a, b):
    if config.IDLE in (a, b):
        return costs.get(_key(a, b), 0.0)
    return costs[_key(a, b)]


def minimum_matching(task_ids, costs):
    nodes = with_idle(task_ids)
    n = len(nodes)

    if n > config.MAX_WORKLOADS + 1:
        raise ValueError("Too many workloads for exact matching")

    @lru_cache(maxsize=None)
    def solve(mask):
        if mask == 0:
            return 0.0, ()

        first = (mask & -mask).bit_length() - 1
        rest = mask & ~(1 << first)
        best = None

        for second in range(first + 1, n):
            if not rest & (1 << second):
                continue
            sub_cost, sub_pairs = solve(rest & ~(1 << second))
            cost = edge_cost(costs, nodes[first], nodes[second]) + sub_cost
            if best is None or cost < best[0] - 1e-12:
                best = (cost, ((nodes[first], nodes[second]),) + sub_pairs)

        return best

    total, pairs = solve((1 << n) - 1)
    return [list(p) for p in pairs], total


def all_matchings(nodes):
    if not nodes:
        yield []
        return

    first, rest = nodes[0], nodes[1:]

    for i, partner in enumerate(rest):
        for tail in all_matchings(rest[:i] + rest[i + 1:]):
            yield [[first, partner]] + tail


def matching_cost(pairs, costs):
    return sum(edge_cost(costs, a, b) for a, b in pairs)


def ranked_matchings(task_ids, costs, limit=10):
    """Cheapest `limit` matchings (enumerated only for small n)."""

    nodes = with_idle(task_ids)

    if len(nodes) > 10:
        return None

    scored = sorted(
        (
            {"pairs": m, "totalCost": matching_cost(m, costs)}
            for m in all_matchings(nodes)
        ),
        key=lambda item: item["totalCost"],
    )
    return [
        {"matching": f"M{i}", **item}
        for i, item in enumerate(islice(scored, limit), start=1)
    ]


def matching_count(task_count):
    count = 1

    for odd in range(task_count + task_count % 2 - 1, 0, -2):
        count *= odd

    return count
