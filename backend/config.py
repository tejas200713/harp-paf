"""Tunable constants for HARP-PAF.

Every value here is a documented default rather than a measured quantity.
Values that the manuscript says must be estimated from data (the regression
coefficients) are overwritten by `python -m backend.calibrate`; the rest
should be reported in the parameter-setup table of the manuscript.
"""

import os
from pathlib import Path


def _env_float(name, default):
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
EXAMPLES_DIR = BASE_DIR / "examples"
KERNELS_SOURCE = Path(__file__).resolve().parent / "kernels" / "stressors.cpp"
KERNELS_BUILD_DIR = ARTIFACTS_DIR / "kernels"
MODEL_DIR = ARTIFACTS_DIR / "model"   # coefficients-<mode>.json per profiling mode
MEASUREMENT_LOCK = ARTIFACTS_DIR / ".measurement.lock"

WINDOWS = os.name == "nt"

if WINDOWS:
    _toolchain_candidates = [
        Path(r"C:\Program Files\CodeBlocks\MinGW\bin"),
        Path(r"C:\msys64\ucrt64\bin"),
        Path(r"C:\msys64\mingw64\bin"),
    ]
    for _p in _toolchain_candidates:
        if _p.is_dir() and str(_p).lower() not in os.environ.get("PATH", "").lower():
            os.environ["PATH"] = f"{_p};" + os.environ.get("PATH", "")

# Compilation and sandboxing. On Windows binaries are linked statically so
# they do not depend on the MinGW runtime DLLs being on PATH.
EXE_SUFFIX = ".exe" if WINDOWS else ""
_LINK_FLAGS = ["-static"] if WINDOWS else []
CPP_FLAGS = ["-O2", "-std=c++17", *_LINK_FLAGS]
C_FLAGS = ["-O2", "-std=c11", *_LINK_FLAGS]
MAX_MEMORY_BYTES = 768 * 1024 * 1024
CPU_LIMIT_SECONDS = 120
RUN_TIMEOUT_SECONDS = 60
MAX_OUTPUT_BYTES = 65536
MIN_WORKLOADS = 2
MAX_WORKLOADS = 16

# SMT experiment scope. HARP-PAF is about simultaneous multithreading: two
# hardware threads sharing ONE physical core. By default every method runs
# its pairs one after another on a single SMT core, so the measured effect is
# co-runner choice on that core, not parallelism across cores.
SMT_CORES = max(1, int(os.environ.get("HARP_SMT_CORES", "1")))

# Objective (manuscript Section 3.1): "makespan" = total time for the
# workload set on the SMT core(s). Pair cost J is in seconds.
OBJECTIVE = "makespan"

# Solo timing and evaluation.
SOLO_REPETITIONS = 3
# Unmeasured runs before solo timing: the first launches of a freshly
# compiled binary are slowed by on-access antivirus scanning and cold caches.
WARMUP_RUNS = 1
# Seconds of full load on the SMT core before calibration, profiling and
# evaluation, so laptop CPUs leave low-power states and reach a steady
# clock before anything is timed.
WARMUP_SECONDS = float(os.environ.get("HARP_WARMUP_SECONDS", "10"))
EVAL_REPETITIONS = 5
MIN_EVAL_REPETITIONS = 3
MAX_EVAL_REPETITIONS = 15
BOOTSTRAP_SAMPLES = 2000

# Profiling mode: "auto" uses hardware counters when they work (perf on
# Linux, EMON on Windows), otherwise interference probing against stressor
# kernels. Force with HARP_PROFILE_MODE=perf|emon|probe.
PROFILE_MODE = os.environ.get("HARP_PROFILE_MODE", "auto")
PERF_INTERVAL_MS = 100
PERF_EVENTS = (
    "instructions",
    "cycles",
    "cache-references",
    "cache-misses",
    "branch-instructions",
    "branch-misses",
    "stalled-cycles-frontend",
    "stalled-cycles-backend",
)

# Intel EMON (VTune) counter collection on Windows; needs an elevated
# process and the VTune sampling driver. Two explicit groups, each with
# the fixed instruction/cycle counters so every group normalises itself.
EMON_PATH = os.environ.get(
    "HARP_EMON",
    r"C:\Program Files (x86)\Intel\oneAPI\vtune\latest\bin64\emon.exe",
)
EMON_INTERVAL_SECONDS = 0.05   # per group; two groups -> 100 ms windows
EMON_GROUPS = (
    ("INST_RETIRED.ANY", "CPU_CLK_UNHALTED.THREAD",
     "LONGEST_LAT_CACHE.REFERENCE", "LONGEST_LAT_CACHE.MISS",
     "BR_INST_RETIRED.ALL_BRANCHES", "BR_MISP_RETIRED.ALL_BRANCHES",
     "ARITH.DIV_ACTIVE", "FP_ARITH_INST_RETIRED.SCALAR"),
    ("INST_RETIRED.ANY", "CPU_CLK_UNHALTED.THREAD",
     "FP_ARITH_INST_RETIRED.VECTOR", "MEM_INST_RETIRED.ALL_LOADS",
     "MEM_INST_RETIRED.ALL_STORES", "IDQ_BUBBLES.CORE",
     "TOPDOWN.BACKEND_BOUND_SLOTS"),
)
PIPELINE_WIDTH = 6          # Golden Cove issue slots per cycle (top-down)
EMON_ACTIVE_FRACTION = 0.2  # windows below this share of peak instructions
                            # are before/after the workload and are dropped
EDGE_WINDOW_FRACTION = 0.6  # active windows with fewer instructions than this
                            # share of the median are partial (the workload
                            # started or ended inside them) and are dropped

# Stressor kernels used for probing (fallback runtime profiler).
PROBE_KERNELS = ("int", "fp", "stream", "cache", "branch")

# Static analysis (Algorithm A).
LOOP_WEIGHT = 10.0          # assumed iterations per loop nesting level
STATIC_INTENSITY = 0.5      # assumed issue intensity when IPC is unknown

# Runtime normalisation (Algorithm B).
IPC_REFERENCE = 4.0                     # nominal issue width
FOOTPRINT_REFERENCE_PKI = 40.0          # LLC references per kilo-instruction
BRANCH_MPKI_REFERENCE = 40.0            # branch misses per kilo-instruction
                                        # (high enough that measured kernels
                                        # do not saturate at 1.0)
SENSITIVITY_REFERENCE = 0.5             # probe slowdown mapped to demand 1.0
B_SOCKET = _env_float("HARP_B_SOCKET", 20e9)   # bytes/s reference
CACHE_LINE_BYTES = 64

# Phase detection.
PHASE_THRESHOLD = 0.25
PHASE_MIN_WINDOWS = 2       # 100 ms windows -> phases of at least 0.2 s

# Adaptive fusion: x = q*d + (1-q)*s.
Q_MAX = 0.9                 # static evidence always keeps some weight
STD_REFERENCE_WINDOW = 0.25 # within-phase spread of a [0,1] measure giving
                            # zero confidence (absolute, so near-zero
                            # quantities can still be measured confidently)
CV_REFERENCE_SOLO = 0.10    # run-to-run variation giving zero confidence

# Pair features (Equations 1-7).
RESOURCES = ("int_alu", "mul_div", "fp_simd", "load_store", "branch")
RESOURCE_WEIGHTS = {        # omega[c], sums to 1 (heuristic defaults)
    "int_alu": 0.20,
    "mul_div": 0.20,
    "fp_simd": 0.25,
    "load_store": 0.20,
    "branch": 0.15,
}
PAIR_FEATURES = ("R", "K", "B", "O", "X", "S")

# Pair-feature set used by the slowdown model:
#   "sa" - bottleneck sensitivity x aggressiveness (default):
#          H = 1/2 (max_k sens_i,k * aggr_j,k + max_k sens_j,k * aggr_i,k)
#   "eq" - the manuscript's original Equations 1-8 (R, K, B, O, X, S)
FEATURE_SET = os.environ.get("HARP_FEATURE_SET", "sa")
SA_FEATURES = ("H",)
SENSITIVITY_CAP = 2.0       # probe slowdowns above +200% are capped
AGGRESSIVENESS_CAP = 1.5    # at most 1.5x as aggressive as the stressor itself
PORT_CAPACITY = {           # Golden Cove ports per class (aggressiveness)
    "int_alu": 5, "fp_simd": 3,
}
# Aggressiveness of each stressor kernel itself (its counter signature),
# the reference that aggressiveness is normalised by. Calibration replaces
# these with values measured on the machine.
DEFAULT_SIGNATURES = {"int": 0.47, "fp": 0.36, "stream": 0.59, "cache": 0.98, "branch": 0.84}

# Regression defaults used until calibration has been run (Equation 9).
DEFAULT_COEFFICIENTS = {
    "eq": {"intercept": 0.0, "R": 0.6, "K": 0.4, "B": 0.5,
           "O": 0.1, "X": 0.2, "S": 0.2},
    "sa": {"intercept": 0.0, "H": 0.8},
}
DEFAULT_WORST_SCALE = 1.5
DEFAULT_RMSE = 0.10

# Risk- and fairness-adjusted cost (Equation 11).
RISK_MU = _env_float("HARP_RISK_MU", 1.0)
RISK_NU = _env_float("HARP_RISK_NU", 0.5)
RISK_TAU = _env_float("HARP_RISK_TAU", 0.25)

IDLE = "IDLE"
