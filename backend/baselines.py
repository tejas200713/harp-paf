"""Comparison methods evaluated against HARP-PAF.

Random  - a uniformly random perfect matching, redrawn for every
          repetition from a seeded generator (stored with the job).
PORT    - port-contention-aware pairing after Saito and Fujimoto [11]:
          each workload is ranked by its static SIMD/FP execution-port
          pressure (vector/FP plus multiply/divide instruction share) and
          the most port-intensive workload is paired with the least
          intensive one, the second-most with the second-least, and so on.
          It uses one signal only: no runtime evidence, phases or model.
Linux   - no pinning: all workloads start together and the Linux
          scheduler places them on the same set of logical CPUs that the
          paired methods use.
"""

from backend import config
from backend.pairing import with_idle


def random_matching(task_ids, rng):
    nodes = with_idle(task_ids)
    rng.shuffle(nodes)
    return [sorted(nodes[i:i + 2]) for i in range(0, len(nodes), 2)]


def port_pressure(static):
    mix = static["instructionMix"]
    return mix["fp_simd"] + mix["mul_div"]


def port_matching(task_ids, static_profiles):
    ranked = sorted(
        task_ids,
        key=lambda t: (-port_pressure(static_profiles[t]), t),
    )

    if len(ranked) % 2:
        # The most port-intensive workload gets a core to itself.
        ranked.append(config.IDLE)

    pairs = []

    while ranked:
        pairs.append(sorted([ranked.pop(0), ranked.pop(-1)]))

    return pairs
