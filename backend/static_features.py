"""Algorithm A: static instruction-mix analysis of compiled binaries.

The compiled executable is disassembled with objdump. Only user code is
analysed: the functions reachable from `main` through direct calls,
excluding compiler-runtime and standard-library functions (this matters on
Windows, where binaries are statically linked). Each instruction is
assigned to one execution-resource class, and instructions inside loops are
weighted by LOOP_WEIGHT per nesting level (loops are found as backward
branches inside a function). The result is a static estimate of how the
program's dynamic work is distributed across shared SMT resources.

Static proxies are indicators, not measurements: the analysis cannot see
array sizes, trip counts or library code, which is why runtime evidence is
fused with it later.
"""

import re
import subprocess

from backend import config

# Compiler runtime stubs that are not part of the workload.
SKIPPED_FUNCTIONS = {
    "_start", "_init", "_fini", "deregister_tm_clones",
    "register_tm_clones", "__do_global_dtors_aux", "frame_dummy",
    "__libc_csu_init", "__libc_csu_fini", "_dl_relocate_static_pie",
}

FUNCTION_RE = re.compile(r"^([0-9a-f]+) <(.+)>:$")
INSTRUCTION_RE = re.compile(
    r"^\s+([0-9a-f]+):\s+(\S+)(?:\s+(.*))?$"
)
TARGET_RE = re.compile(r"^([0-9a-f]+)\b")

IGNORED = {"nop", "nopw", "nopl", "endbr64", "endbr32", "int3", "hlt",
           "cs", "data16"}
MUL_DIV = {"mul", "imul", "div", "idiv", "mulx"}
VECTOR_REGISTER_RE = re.compile(r"%(xmm|ymm|zmm)\d|%st\b")
MOVES = ("mov", "push", "pop", "stos", "lods", "cmov")


def classify(mnemonic, operands):
    """Return (resource class, has memory operand) for an x86-64 insn.

    Operands are in AT&T syntax as printed by objdump.
    """

    m = mnemonic
    has_memory = "(" in operands and not m.startswith("lea")

    if m.startswith("j") or m.startswith(("call", "ret", "loop")):
        return "branch", has_memory

    if m in MUL_DIV or m.rstrip("bwlq") in MUL_DIV:
        return "mul_div", has_memory

    if (
        VECTOR_REGISTER_RE.search(operands)
        or m.startswith("v")
        or m.startswith("f") and not m.startswith("fs")
    ):
        return "fp_simd", has_memory

    if m.startswith(MOVES) and not m.startswith("cmov"):
        if has_memory or m.startswith(("push", "pop")):
            return "load_store", has_memory
        return "int_alu", has_memory

    return "int_alu", has_memory


LIBRARY_PREFIXES = ("std::", "_", "operator", "__gnu", "decltype")
# C library functions that static linking (Windows) pulls into .text.
C_LIBRARY = {
    "memset", "memcpy", "memmove", "memcmp", "strlen", "strcmp", "strcpy",
    "malloc", "calloc", "realloc", "free", "abort", "exit", "atexit",
    "printf", "fprintf", "sprintf", "snprintf", "puts", "putchar", "fwrite",
    "strtol", "strtoul", "strtoll", "strtoull", "atoi", "rand", "srand",
    "sqrt", "sqrtf", "sin", "cos", "tan", "exp", "log", "pow", "fabs",
    "floor", "ceil", "fmod", "atan2",
}
OFFSET_RE = re.compile(r"\+0x[0-9a-f]+$")


def _disassemble(binary):
    result = subprocess.run(
        ["objdump", "-d", "-C", "--no-show-raw-insn", "-j", ".text", str(binary)],
        capture_output=True, text=True, timeout=30, check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(f"objdump failed: {result.stderr.strip()}")

    return result.stdout


def _parse_functions(listing):
    functions = {}
    current = None

    for line in listing.splitlines():
        header = FUNCTION_RE.match(line)

        if header:
            current = header.group(2)
            functions[current] = []
            continue

        match = INSTRUCTION_RE.match(line)

        if current and match:
            address = int(match.group(1), 16)
            mnemonic = match.group(2)
            operands = (match.group(3) or "").split("#")[0].strip()
            functions[current].append((address, mnemonic, operands))

    return functions


def _loop_depths(instructions):
    """Nesting depth per instruction from backward branches."""

    if not instructions:
        return []

    first = instructions[0][0]
    last = instructions[-1][0]
    loops = []

    for address, mnemonic, operands in instructions:
        if not mnemonic.startswith("j"):
            continue

        target = TARGET_RE.match(operands)

        if not target:
            continue

        target_address = int(target.group(1), 16)

        if first <= target_address <= address <= last:
            loops.append((target_address, address))

    return [
        sum(1 for start, end in loops if start <= address <= end)
        for address, _, _ in instructions
    ]


def _call_target(operands):
    if "<" not in operands or ">" not in operands:
        return None
    name = operands[operands.index("<") + 1:operands.rindex(">")]
    return OFFSET_RE.sub("", name)


def _is_user_function(name):
    return (
        name == "main"
        or not name.startswith(LIBRARY_PREFIXES)
        and name not in SKIPPED_FUNCTIONS
        and name not in C_LIBRARY
        and "@" not in name
    )


def user_functions(functions):
    """Functions reachable from main via direct calls, user code only."""

    if "main" not in functions:
        return [n for n in functions
                if n not in SKIPPED_FUNCTIONS and not n.startswith("_GLOBAL__sub_I")]

    seen = {"main"}
    queue = ["main"]

    while queue:
        for _, mnemonic, operands in functions[queue.pop()]:
            if not mnemonic.startswith(("call", "jmp")):
                continue
            target = _call_target(operands)
            if target in functions and target not in seen and _is_user_function(target):
                seen.add(target)
                queue.append(target)

    return sorted(seen)


def analyze_binary(binary):
    functions = _parse_functions(_disassemble(binary))
    weights = {resource: 0.0 for resource in config.RESOURCES}
    memory_weight = 0.0
    total_weight = 0.0
    raw_count = 0
    max_depth = 0
    analysed = []

    for name in user_functions(functions):
        instructions = functions[name]
        analysed.append(name)
        depths = _loop_depths(instructions)

        for (address, mnemonic, operands), depth in zip(instructions, depths):
            if mnemonic in IGNORED:
                continue

            resource, has_memory = classify(mnemonic, operands)
            weight = config.LOOP_WEIGHT ** depth
            weights[resource] += weight
            total_weight += weight
            raw_count += 1
            max_depth = max(max_depth, depth)

            if has_memory:
                memory_weight += weight
                if resource != "load_store":
                    # A memory operand on a compute instruction also
                    # occupies a load/store port.
                    weights["load_store"] += weight
                    total_weight += weight

    if total_weight == 0:
        raise RuntimeError("No analysable instructions found")

    mix = {r: weights[r] / total_weight for r in config.RESOURCES}

    return {
        "method": "objdump-loop-weighted-instruction-mix",
        "instructionMix": mix,
        "memoryOperandShare": memory_weight / total_weight,
        "staticInstructionCount": raw_count,
        "maxLoopDepth": max_depth,
        "functionsAnalysed": analysed,
        "loopWeight": config.LOOP_WEIGHT,
    }


def static_estimates(static):
    """Map the static profile onto the shared feature space (s values)."""

    mix = static["instructionMix"]
    memory = static["memoryOperandShare"]
    estimates = {
        f"u_{r}": mix[r] * config.STATIC_INTENSITY
        for r in config.RESOURCES
    }
    footprint = min(1.0, memory * 1.5)
    estimates.update({
        "footprint": footprint,
        "bandwidth": footprint * 0.5,
        "stall_fe": mix["branch"],
        "stall_be_mem": memory * 0.5,
        "stall_be_core": (mix["mul_div"] + mix["fp_simd"]) * 0.5,
        "branch_miss": mix["branch"] * 0.5,
        # Aggressiveness proxies (weak; counters replace them when present).
        "agg_int": mix["int_alu"] * config.STATIC_INTENSITY,
        "agg_fp": (mix["fp_simd"] + mix["mul_div"]) * config.STATIC_INTENSITY,
        "agg_stream": footprint * 0.5,
        "agg_cache": footprint * 0.5,
        "agg_branch": mix["branch"] * 0.5,
    })
    return estimates
