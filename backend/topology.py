"""CPU topology discovery (Linux sysfs or the Windows processor API).

SMT siblings are read from the operating system rather than assumed, so a
pair of tasks is placed on the two hardware threads of one physical core.
On hybrid CPUs (P-cores with SMT, E-cores without) only the fastest SMT
cores host task pairs, and the harness runs on a single-thread core so it
does not steal a P-core. Under a hypervisor (for example WSL2) Linux sees
the virtual topology exposed to the guest; `virtualized` says so.
"""

from functools import lru_cache
from pathlib import Path
import os

from backend import config

SYSFS_CPU = Path("/sys/devices/system/cpu")
WINDOWS = os.name == "nt"

if WINDOWS:
    from backend import platform_win


def _read(path, default=None):
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return default


def _cpuinfo_value(prefix):
    for line in (_read("/proc/cpuinfo", "") or "").splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return None


def _linux_cores():
    allowed = sorted(os.sched_getaffinity(0))
    cores = {}

    for cpu in allowed:
        base = SYSFS_CPU / f"cpu{cpu}" / "topology"
        package = _read(base / "physical_package_id", "0")
        core = _read(base / "core_id", str(cpu))
        capacity = _read(SYSFS_CPU / f"cpu{cpu}" / "cpu_capacity", "0")
        entry = cores.setdefault((package, core), {"cpus": [], "efficiencyClass": 0})
        entry["cpus"].append(cpu)
        entry["efficiencyClass"] = max(entry["efficiencyClass"], int(capacity or 0))

    caches = [
        {
            "level": _read(index / "level"),
            "type": _read(index / "type"),
            "size": _read(index / "size"),
            "sharedCpuList": _read(index / "shared_cpu_list"),
        }
        for index in sorted(SYSFS_CPU.glob("cpu0/cache/index*"))
    ]
    flags = _cpuinfo_value("flags") or ""

    return {
        "allowed": allowed,
        "cores": list(cores.values()),
        "caches": caches,
        "cpuModel": _cpuinfo_value("model name"),
        "virtualized": " hypervisor" in f" {flags}",
        "source": "sysfs",
    }


def _windows_cores():
    allowed = set(platform_win.process_affinity())
    cores, caches = platform_win.logical_processor_information()
    usable = []

    for core in cores:
        cpus = [c for c in core["cpus"] if c in allowed]
        if cpus:
            usable.append({"cpus": cpus, "efficiencyClass": core["efficiencyClass"]})

    return {
        "allowed": sorted(allowed),
        "cores": usable,
        "caches": caches,
        "cpuModel": platform_win.cpu_model(),
        "virtualized": False,
        "source": "GetLogicalProcessorInformationEx",
    }


@lru_cache(maxsize=1)
def discover():
    info = _windows_cores() if WINDOWS else _linux_cores()
    cores = sorted(
        ({"cpus": sorted(c["cpus"]), "efficiencyClass": c["efficiencyClass"]}
         for c in info["cores"]),
        key=lambda c: (-c["efficiencyClass"], c["cpus"]),
    )
    smt = [c for c in cores if len(c["cpus"]) >= 2]
    single = [c for c in cores if len(c["cpus"]) == 1]
    fastest = max((c["efficiencyClass"] for c in smt), default=0)
    smt_pairs = [tuple(c["cpus"][:2]) for c in smt if c["efficiencyClass"] == fastest]

    # Harness on the slowest single-thread core if there is one, otherwise
    # sacrifice the last SMT pair.
    if single:
        harness_cpu = single[-1]["cpus"][0]
        task_pairs = smt_pairs
    elif len(smt_pairs) >= 2:
        harness_cpu = smt_pairs[-1][0]
        task_pairs = smt_pairs[:-1]
    else:
        harness_cpu = None
        task_pairs = smt_pairs

    smt_verified = bool(task_pairs)

    if not smt_verified:
        # No sibling information: fall back to adjacent logical CPUs.
        usable = [c for c in info["allowed"] if c != harness_cpu]
        task_pairs = [
            (usable[i], usable[i + 1]) for i in range(0, len(usable) - 1, 2)
        ]

    return {
        "platform": "windows" if WINDOWS else "linux",
        "topologySource": info["source"],
        "cpuModel": info["cpuModel"],
        "virtualized": info["virtualized"],
        "allowedCpus": info["allowed"],
        "logicalCpuCount": len(info["allowed"]),
        "physicalCoreCount": len(cores),
        "threadsPerCore": max((len(c["cpus"]) for c in cores), default=1),
        "hybrid": len({c["efficiencyClass"] for c in cores}) > 1,
        "cores": cores,
        "siblingGroups": [c["cpus"] for c in cores],
        "smtPairs": [tuple(c["cpus"][:2]) for c in smt],
        "taskPairs": task_pairs,
        "harnessCpu": harness_cpu,
        "smtSiblingsFromSysfs": smt_verified,
        "caches": info["caches"],
    }


def task_slots():
    """SMT sibling pairs used for task pairs (config.SMT_CORES of them)."""

    slots = discover()["taskPairs"][:config.SMT_CORES]

    if not slots:
        raise RuntimeError("At least one pair of logical CPUs is required")

    return slots


def pin_harness():
    """Pin the calling thread to the harness CPU, if one exists."""

    cpu = discover()["harnessCpu"]

    if cpu is None:
        return

    if WINDOWS:
        platform_win.set_thread_affinity([cpu])
    else:
        os.sched_setaffinity(0, {cpu})
