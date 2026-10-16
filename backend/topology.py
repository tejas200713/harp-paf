"""CPU topology discovery from Linux sysfs.

SMT siblings are read from /sys/devices/system/cpu/cpu*/topology rather
than assumed, so a pair of tasks is placed on the two hardware threads of
one physical core. Under a hypervisor (for example WSL2) the reported
topology is the virtual one exposed to the guest; `virtualized` says so.
"""

from functools import lru_cache
from pathlib import Path
import os

SYSFS_CPU = Path("/sys/devices/system/cpu")


def _read(path, default=None):
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return default


def _cpu_model():
    for line in (_read("/proc/cpuinfo", "") or "").splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return None


def _virtualized():
    for line in (_read("/proc/cpuinfo", "") or "").splitlines():
        if line.startswith("flags"):
            return " hypervisor" in line
    return False


def _caches():
    caches = []

    for index in sorted(SYSFS_CPU.glob("cpu0/cache/index*")):
        caches.append({
            "level": _read(index / "level"),
            "type": _read(index / "type"),
            "size": _read(index / "size"),
            "sharedCpuList": _read(index / "shared_cpu_list"),
        })

    return caches


@lru_cache(maxsize=1)
def discover():
    allowed = sorted(os.sched_getaffinity(0))
    cores = {}

    for cpu in allowed:
        base = SYSFS_CPU / f"cpu{cpu}" / "topology"
        package = _read(base / "physical_package_id", "0")
        core = _read(base / "core_id", str(cpu))
        cores.setdefault((package, core), []).append(cpu)

    groups = sorted(sorted(cpus) for cpus in cores.values())
    smt_pairs = [tuple(g[:2]) for g in groups if len(g) >= 2]
    single = [g[0] for g in groups if len(g) == 1]

    # The harness (Python poller) runs on its own core when possible, so
    # it does not steal cycles from the measured pairs.
    if len(smt_pairs) >= 2:
        harness_cpu = smt_pairs[-1][0]
        task_pairs = smt_pairs[:-1]
    elif single:
        harness_cpu = single[-1]
        task_pairs = smt_pairs
    else:
        harness_cpu = None
        task_pairs = smt_pairs

    smt_verified = bool(task_pairs)

    if not smt_verified:
        # No sibling information: fall back to adjacent logical CPUs.
        usable = [c for c in allowed if c != harness_cpu]
        task_pairs = [
            (usable[i], usable[i + 1])
            for i in range(0, len(usable) - 1, 2)
        ]

    return {
        "cpuModel": _cpu_model(),
        "virtualized": _virtualized(),
        "allowedCpus": allowed,
        "logicalCpuCount": len(allowed),
        "physicalCoreCount": len(groups),
        "threadsPerCore": max((len(g) for g in groups), default=1),
        "siblingGroups": groups,
        "smtPairs": smt_pairs,
        "taskPairs": task_pairs,
        "harnessCpu": harness_cpu,
        "smtSiblingsFromSysfs": smt_verified,
        "caches": _caches(),
    }


def task_slots():
    """CPU pairs (one physical core each) available for task pairs."""

    slots = discover()["taskPairs"]

    if not slots:
        raise RuntimeError("At least one pair of logical CPUs is required")

    return slots


def pin_harness():
    """Pin the calling thread to the harness CPU, if one exists."""

    cpu = discover()["harnessCpu"]

    if cpu is not None:
        os.sched_setaffinity(0, {cpu})
