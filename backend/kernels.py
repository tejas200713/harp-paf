"""Build and launch the stressor/training kernels in kernels/stressors.cpp.

Each kernel is compiled into its own binary (-DKERNEL=<id>) so that its
static instruction mix reflects only that kernel. Without an argument a
kernel runs until killed (interference probing); with an argument it runs
a fixed number of work units and exits (calibration training data).
"""

import hashlib

from backend import config
from backend.compiler import compile_program

KERNEL_IDS = {
    "int": 1, "div": 2, "fp": 3, "simd": 4, "stream": 5,
    "chase": 6, "cache": 7, "branch": 8, "l1": 9, "phased": 10,
}

# Work units giving roughly one second per kernel on a ~3 GHz core.
TRAINING_UNITS = {
    "int": 390, "div": 560, "fp": 260, "simd": 1600, "stream": 115,
    "chase": 8, "cache": 360, "branch": 150, "l1": 900, "phased": 2,
}


def build(name):
    source = config.KERNELS_SOURCE.read_bytes()
    digest = hashlib.sha256(
        source + " ".join(config.CPP_FLAGS).encode()
    ).hexdigest()[:12]
    output = config.KERNELS_BUILD_DIR / f"{name}-{digest}"

    if output.is_file():
        return output

    result = compile_program(
        config.KERNELS_SOURCE, output, "cpp",
        extra_flags=[f"-DKERNEL={KERNEL_IDS[name]}"],
    )

    if not result["success"]:
        raise RuntimeError(f"Kernel {name} failed to compile: {result['stderr']}")

    return output


def argv(name, units=None):
    binary = build(name)
    return [binary] if units is None else [binary, str(units)]
