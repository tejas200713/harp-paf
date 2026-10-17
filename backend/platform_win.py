"""Windows primitives for topology, pinning, timing and limits (ctypes only).

Processes are created suspended, pinned with SetProcessAffinityMask,
placed in a Job Object (memory/CPU limits, killed with the job) and only
then resumed, so no instruction runs on the wrong CPU. Waiting uses
WaitForMultipleObjects; CPU times come from GetProcessTimes.
"""

import ctypes
from ctypes import wintypes
import subprocess

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
ntdll = ctypes.WinDLL("ntdll")

CREATE_SUSPENDED = 0x00000004
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
RELATION_PROCESSOR_CORE = 0
RELATION_CACHE = 2
RELATION_ALL = 0xFFFF
LTP_PC_SMT = 0x1

JOB_OBJECT_LIMIT_PROCESS_TIME = 0x00000002
JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS = 9


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


kernel32.GetCurrentProcess.restype = wintypes.HANDLE
kernel32.GetCurrentThread.restype = wintypes.HANDLE
kernel32.GetProcessAffinityMask.argtypes = [
    wintypes.HANDLE, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]
kernel32.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
kernel32.SetThreadAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
kernel32.SetThreadAffinityMask.restype = ctypes.c_size_t
kernel32.GetLogicalProcessorInformationEx.argtypes = [
    ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD)]
kernel32.CreateJobObjectW.restype = wintypes.HANDLE
kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
kernel32.SetInformationJobObject.argtypes = [
    wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.WaitForMultipleObjects.argtypes = [
    wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE), wintypes.BOOL, wintypes.DWORD]
kernel32.WaitForMultipleObjects.restype = wintypes.DWORD
kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]


def _check(ok, what):
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error(), what)


def mask_of(cpus):
    mask = 0
    for cpu in cpus:
        mask |= 1 << cpu
    return mask


def cpus_of(mask):
    return [bit for bit in range(mask.bit_length()) if mask >> bit & 1]


def process_affinity():
    process_mask = ctypes.c_size_t()
    system_mask = ctypes.c_size_t()
    _check(kernel32.GetProcessAffinityMask(
        kernel32.GetCurrentProcess(), ctypes.byref(process_mask),
        ctypes.byref(system_mask)), "GetProcessAffinityMask")
    return cpus_of(process_mask.value)


def set_thread_affinity(cpus):
    _check(kernel32.SetThreadAffinityMask(
        kernel32.GetCurrentThread(), mask_of(cpus)), "SetThreadAffinityMask")


def logical_processor_information():
    """Return (cores, caches) for processor group 0.

    cores:  [{"cpus": [...], "smt": bool, "efficiencyClass": int}]
            (a higher EfficiencyClass means a faster core, e.g. P-cores)
    caches: [{"level", "type", "size", "sharedCpuList"}]
    """

    length = wintypes.DWORD(0)
    kernel32.GetLogicalProcessorInformationEx(RELATION_ALL, None, ctypes.byref(length))
    buffer = ctypes.create_string_buffer(length.value)
    _check(kernel32.GetLogicalProcessorInformationEx(
        RELATION_ALL, buffer, ctypes.byref(length)), "GetLogicalProcessorInformationEx")
    raw = buffer.raw
    cores, caches = [], []
    offset = 0
    cache_types = {0: "Unified", 1: "Instruction", 2: "Data", 3: "Trace"}

    while offset < length.value:
        relationship = int.from_bytes(raw[offset:offset + 4], "little")
        size = int.from_bytes(raw[offset + 4:offset + 8], "little")
        body = offset + 8

        if relationship == RELATION_PROCESSOR_CORE:
            # PROCESSOR_RELATIONSHIP: Flags, EfficiencyClass, Reserved[20],
            # GroupCount, then GROUP_AFFINITY[] aligned to 8 bytes.
            flags = raw[body]
            efficiency = raw[body + 1]
            mask = int.from_bytes(raw[body + 24:body + 32], "little")
            group = int.from_bytes(raw[body + 32:body + 34], "little")
            if group == 0:
                cores.append({
                    "cpus": cpus_of(mask),
                    "smt": bool(flags & LTP_PC_SMT),
                    "efficiencyClass": efficiency,
                })
        elif relationship == RELATION_CACHE:
            # CACHE_RELATIONSHIP: Level, Associativity, LineSize, CacheSize,
            # Type, Reserved[18], GroupCount, GROUP_AFFINITY[].
            level = raw[body]
            cache_size = int.from_bytes(raw[body + 4:body + 8], "little")
            cache_type = int.from_bytes(raw[body + 8:body + 12], "little")
            mask = int.from_bytes(raw[body + 32:body + 40], "little")
            caches.append({
                "level": str(level),
                "type": cache_types.get(cache_type, str(cache_type)),
                "size": f"{cache_size // 1024}K",
                "sharedCpuList": ",".join(str(c) for c in cpus_of(mask)),
            })

        offset += size

    return cores, caches


def cpu_model():
    import winreg

    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        return winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
    except OSError:
        return None


def _create_job(memory_bytes, cpu_seconds):
    job = kernel32.CreateJobObjectW(None, None)
    _check(job, "CreateJobObjectW")
    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = (
        JOB_OBJECT_LIMIT_PROCESS_MEMORY
        | JOB_OBJECT_LIMIT_PROCESS_TIME
        | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    )
    info.BasicLimitInformation.PerProcessUserTimeLimit = int(cpu_seconds * 10_000_000)
    info.ProcessMemoryLimit = memory_bytes
    _check(kernel32.SetInformationJobObject(
        job, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
        ctypes.byref(info), ctypes.sizeof(info)), "SetInformationJobObject")
    return job


def start_pinned(argv, cpus, memory_bytes, cpu_seconds, **popen_kwargs):
    """Start a process suspended, pin and limit it, then resume it."""

    process = subprocess.Popen(argv, creationflags=CREATE_SUSPENDED, **popen_kwargs)
    job = None

    try:
        _check(kernel32.SetProcessAffinityMask(int(process._handle), mask_of(cpus)),
               "SetProcessAffinityMask")
        job = _create_job(memory_bytes, cpu_seconds)
        _check(kernel32.AssignProcessToJobObject(job, int(process._handle)),
               "AssignProcessToJobObject")
        status = ntdll.NtResumeProcess(int(process._handle))
        if status != 0:
            raise OSError(f"NtResumeProcess failed: 0x{status & 0xFFFFFFFF:08x}")
    except BaseException:
        process.kill()
        process.wait()
        if job:
            kernel32.CloseHandle(job)
        raise

    process.job_handle = job
    return process


def kill(process):
    job = getattr(process, "job_handle", None)

    if process.poll() is None:
        if job:
            kernel32.TerminateJobObject(job, 1)
        else:
            process.kill()
        process.wait()

    if job:
        kernel32.CloseHandle(job)
        process.job_handle = None


def wait_any(processes, timeout_seconds):
    """Index of a finished process, or None on timeout."""

    handles = (wintypes.HANDLE * len(processes))(
        *[int(p._handle) for p in processes])
    milliseconds = max(0, int(timeout_seconds * 1000))
    result = kernel32.WaitForMultipleObjects(len(processes), handles, False, milliseconds)

    if result == WAIT_TIMEOUT:
        return None
    if WAIT_OBJECT_0 <= result < WAIT_OBJECT_0 + len(processes):
        return result - WAIT_OBJECT_0
    raise ctypes.WinError(ctypes.get_last_error(), "WaitForMultipleObjects")


def process_times(process):
    """(user seconds, system seconds) of a process."""

    creation, exit_time, kernel, user = (wintypes.FILETIME() for _ in range(4))
    _check(kernel32.GetProcessTimes(
        int(process._handle), ctypes.byref(creation), ctypes.byref(exit_time),
        ctypes.byref(kernel), ctypes.byref(user)), "GetProcessTimes")

    def seconds(ft):
        return ((ft.dwHighDateTime << 32) | ft.dwLowDateTime) / 10_000_000

    return seconds(user), seconds(kernel)
