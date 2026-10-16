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
MODEL_FILE = ARTIFACTS_DIR / "model" / "coefficients.json"

# Compilation and sandboxing.
CPP_FLAGS = ["-O2", "-std=c++17"]
C_FLAGS = ["-O2", "-std=c11"]
MAX_MEMORY_BYTES = 768 * 1024 * 1024
CPU_LIMIT_SECONDS = 120
RUN_TIMEOUT_SECONDS = 60
MAX_OUTPUT_BYTES = 65536
MIN_WORKLOADS = 2
MAX_WORKLOADS = 16

# Solo timing and evaluation.
SOLO_REPETITIONS = 3
EVAL_REPETITIONS = 5
MIN_EVAL_REPETITIONS = 3
MAX_EVAL_REPETITIONS = 15
BOOTSTRAP_SAMPLES = 2000

# Profiling mode: "auto" uses perf when hardware counters work,
# otherwise interference probing against stressor kernels.
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

# Stressor kernels used for probing (fallback runtime profiler).
PROBE_KERNELS = ("int", "fp", "stream", "cache", "branch")

# Static analysis (Algorithm A).
LOOP_WEIGHT = 10.0          # assumed iterations per loop nesting level
STATIC_INTENSITY = 0.5      # assumed issue intensity when IPC is unknown

# Runtime normalisation (Algorithm B).
IPC_REFERENCE = 4.0                     # nominal issue width
FOOTPRINT_REFERENCE_PKI = 20.0          # LLC references per kilo-instruction
BRANCH_MPKI_REFERENCE = 10.0            # branch misses per kilo-instruction
SENSITIVITY_REFERENCE = 0.5             # probe slowdown mapped to demand 1.0
B_SOCKET = _env_float("HARP_B_SOCKET", 20e9)   # bytes/s reference
CACHE_LINE_BYTES = 64

# Phase detection.
PHASE_THRESHOLD = 0.25
PHASE_MIN_WINDOWS = 3

# Adaptive fusion: x = q*d + (1-q)*s.
Q_MAX = 0.9                 # static evidence always keeps some weight
CV_REFERENCE_WINDOW = 0.5   # window-level variation giving zero confidence
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

# Regression defaults used until calibration has been run (Equation 9).
DEFAULT_COEFFICIENTS = {
    "intercept": 0.0, "R": 0.6, "K": 0.4, "B": 0.5,
    "O": 0.1, "X": 0.2, "S": 0.2,
}
DEFAULT_WORST_SCALE = 1.5
DEFAULT_RMSE = 0.10

# Risk- and fairness-adjusted cost (Equation 11).
RISK_MU = _env_float("HARP_RISK_MU", 1.0)
RISK_NU = _env_float("HARP_RISK_NU", 0.5)
RISK_TAU = _env_float("HARP_RISK_TAU", 0.25)

IDLE = "IDLE"
