"""Hardware-counter profiling on Windows with Intel EMON (VTune).

EMON samples counters system-wide, per logical CPU, in fixed intervals.
The workload is pinned to one SMT thread by HARP-PAF itself (EMON would
otherwise share or move it), EMON runs on the harness E-core, and only the
workload's CPU column is used.

Output format (one block per interval, groups multiplexed in turn):

    EVENT<TAB>TSC ticks<TAB>count CPU0<TAB>count CPU1 ...
    ----------   (next group)
    ==========   (next interval)

Every group carries the fixed instruction and cycle counters, so each
group's counts are normalised within the group's own sub-interval.
"""

from functools import lru_cache
import math
import os
import subprocess

from backend import config


def _clip(value, low=0.0, high=1.0):
    return max(low, min(high, value))


@lru_cache(maxsize=1)
def status():
    if os.name != "nt":
        return {"available": False, "reason": "EMON is used on Windows only"}

    if not os.path.isfile(config.EMON_PATH):
        return {"available": False, "reason": f"EMON not found at {config.EMON_PATH}"}

    try:
        result = subprocess.run(
            [config.EMON_PATH, "-l1", "-t0.05", "-C", "INST_RETIRED.ANY"],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "reason": str(exc)}

    if result.returncode != 0:
        text = (result.stdout + result.stderr).strip().splitlines()
        reason = next(
            (line for line in text if "administrative" in line or "driver" in line),
            text[-1] if text else f"exit code {result.returncode}",
        )
        return {"available": False, "reason": reason.strip()}

    return {"available": True, "reason": None}


def command(output_file, seconds):
    """EMON command collecting both groups for at least `seconds`."""

    per_loop = config.EMON_INTERVAL_SECONDS * len(config.EMON_GROUPS)
    loops = math.ceil(seconds / per_loop) + 2
    groups = ";".join(",".join(g) for g in config.EMON_GROUPS)
    return [
        config.EMON_PATH,
        f"-t{config.EMON_INTERVAL_SECONDS}",
        f"-l{loops}",
        "-C", groups,
        "-f", str(output_file),
    ]


def _number(text):
    text = text.strip().replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def parse(text, cpu):
    """[{event: count, "_tsc": ticks}] per group sub-interval, for one CPU."""

    samples = []
    current = {}

    def flush():
        if current:
            samples.append(dict(current))
            current.clear()

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith("----") or stripped.startswith("===="):
            flush()
            continue

        fields = line.split("\t")

        if len(fields) < 3 + cpu or "." not in fields[0] or " " in fields[0]:
            continue

        tsc = _number(fields[1])
        value = _number(fields[2 + cpu])

        if tsc is None:
            continue

        current["_tsc"] = tsc
        if value is not None:
            current[fields[0].strip()] = value

    flush()
    return samples


def windows(samples):
    """Pair consecutive group samples into windows of normalised measures."""

    group_a = [s for s in samples if "LONGEST_LAT_CACHE.REFERENCE" in s]
    group_b = [s for s in samples if "MEM_INST_RETIRED.ALL_LOADS" in s]
    pairs = []

    for a, b in zip(group_a, group_b):
        # If EMON dropped the fixed counters from group B, assume the same
        # rate as in group A (adjacent sub-interval of equal length).
        b = {"INST_RETIRED.ANY": a.get("INST_RETIRED.ANY", 0),
             "CPU_CLK_UNHALTED.THREAD": a.get("CPU_CLK_UNHALTED.THREAD", 0), **b}
        a = {"INST_RETIRED.ANY": 0, "CPU_CLK_UNHALTED.THREAD": 0, **a}
        pairs.append((a, b))

    if not pairs:
        return [], {}

    tsc_per_second = sorted(s["_tsc"] for s in group_a)[len(group_a) // 2] \
        / config.EMON_INTERVAL_SECONDS
    peak = max(a.get("INST_RETIRED.ANY", 0) + b.get("INST_RETIRED.ANY", 0)
               for a, b in pairs)
    active = [
        (a, b) for a, b in pairs
        if a.get("INST_RETIRED.ANY", 0) + b.get("INST_RETIRED.ANY", 0)
        >= config.EMON_ACTIVE_FRACTION * peak
    ]
    total_instructions = sum(
        a["INST_RETIRED.ANY"] + b["INST_RETIRED.ANY"] for a, b in active
    )
    totals = {"instructions": 0.0, "cycles": 0.0, "cache-misses": 0.0,
              "cache-references": 0.0, "branch-misses": 0.0, "branches": 0.0}
    result = []
    progress = 0.0

    for a, b in active:
        inst_a, clk_a = a["INST_RETIRED.ANY"], a["CPU_CLK_UNHALTED.THREAD"]
        inst_b, clk_b = b["INST_RETIRED.ANY"], b["CPU_CLK_UNHALTED.THREAD"]

        if min(inst_a, inst_b, clk_a, clk_b) <= 0:
            continue

        kilo_a = inst_a / 1000
        seconds_a = a["_tsc"] / tsc_per_second
        slots_b = config.PIPELINE_WIDTH * clk_b
        fp = a.get("FP_ARITH_INST_RETIRED.SCALAR", 0) / inst_a \
            + b.get("FP_ARITH_INST_RETIRED.VECTOR", 0) / inst_b
        memory = (b.get("MEM_INST_RETIRED.ALL_LOADS", 0)
                  + b.get("MEM_INST_RETIRED.ALL_STORES", 0)) / inst_b
        branch = a.get("BR_INST_RETIRED.ALL_BRANCHES", 0) / inst_a
        divider = a.get("ARITH.DIV_ACTIVE", 0) / clk_a
        mix = {
            "fp_simd": _clip(fp), "load_store": _clip(memory),
            "branch": _clip(branch), "mul_div": _clip(divider),
        }
        mix["int_alu"] = max(0.0, 1.0 - sum(mix.values()))
        mix_total = sum(mix.values()) or 1.0
        misses = a.get("LONGEST_LAT_CACHE.MISS", 0)
        references = a.get("LONGEST_LAT_CACHE.REFERENCE", 0)
        branch_misses = a.get("BR_MISP_RETIRED.ALL_BRANCHES", 0)
        instructions = inst_a + inst_b
        start = progress
        progress += instructions / total_instructions

        measures = {
            "ipc": (inst_a + inst_b) / (clk_a + clk_b),
            "intensity": _clip((inst_a + inst_b) / (clk_a + clk_b) / config.IPC_REFERENCE),
            "footprint": _clip(references / kilo_a / config.FOOTPRINT_REFERENCE_PKI),
            "bandwidth": _clip(
                misses * config.CACHE_LINE_BYTES / seconds_a / config.B_SOCKET
            ),
            "bandwidthBytesPerSecond": misses * config.CACHE_LINE_BYTES / seconds_a,
            "branch_miss": _clip(branch_misses / kilo_a / config.BRANCH_MPKI_REFERENCE),
            "stall_fe": _clip(b.get("IDQ_BUBBLES.CORE", 0) / slots_b),
            "stall_be": _clip(b.get("TOPDOWN.BACKEND_BOUND_SLOTS", 0) / slots_b),
            **{f"mix_{r}": v / mix_total for r, v in mix.items()},
        }
        result.append({"progress": (start, progress), "measures": measures})

        totals["instructions"] += instructions
        totals["cycles"] += clk_a + clk_b
        totals["cache-misses"] += misses
        totals["cache-references"] += references
        totals["branch-misses"] += branch_misses
        totals["branches"] += a.get("BR_INST_RETIRED.ALL_BRANCHES", 0)

    # Instructions and cycles cover both groups; the other totals come from
    # group A only, i.e. about half of the workload's run time.
    return result, totals
