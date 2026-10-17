# HARP-PAF backend

FastAPI service that compiles approved C++ workloads, characterises them
with two fused analyses, pairs them onto the two hardware threads of one
SMT core, and measures the result against Random, PORT and OS-default
placement. Runs on native Windows and on Linux.

The experiment is about simultaneous multithreading only: by default every
method runs on a single physical SMT core (`HARP_SMT_CORES=1`), so the
measured effect is the choice of co-runners on that core, not parallelism
across cores. The objective is makespan (total time for the workload set).

## Pipeline

| Stage | Module | What happens |
|---|---|---|
| Validate | `app.py`, `approved_workloads.py` | 2–16 files; SHA-256 must match a file in `examples/manifest.json` |
| Compile | `compiler.py` | `g++ -O2 -std=c++17` (`-static` on Windows) |
| Verify | `runner.py` | each program runs once; stdout must equal the manifest's expected output |
| Topology | `topology.py`, `platform_win.py` | SMT siblings from Linux sysfs or `GetLogicalProcessorInformationEx`; pairs only on the fastest SMT cores (P-cores); harness on a single-thread E-core |
| **Algorithm A – static** | `static_features.py` | `objdump` instruction mix (int ALU, mul/div, FP/SIMD, load/store, branch) of user functions reachable from `main`, weighted ×10 per loop-nesting level |
| **Algorithm B – runtime** | `profiler.py`, `emon.py`, `phases.py` | hardware-counter windows (EMON on Windows, `perf` on Linux) → phase segmentation and runtime instruction mix; without counters, sensitivity probing against stressor kernels |
| **Adaptive fusion** | `fusion.py` | `x = q·d + (1−q)·s` per workload, phase and feature; `q` from measurement availability and stability |
| Pair features | `features.py` | Equations 1–8 (R, K, B, O, X, S) on phase-aligned fused features |
| Cost model | `model.py` | Equations 9–11: NNLS slowdown regression, worst-case model; pair cost `J` = predicted time the core is busy with the pair (seconds) plus risk/uncertainty terms |
| Matching | `pairing.py` | exact minimum-weight perfect matching (subset DP); an unpaired task runs alone at its solo time |
| Baselines | `baselines.py` | Random (redrawn per repetition), PORT (static port-pressure folding), OS default (all workloads time-shared on the same two threads) |
| Evaluation | `benchmarks.py`, `stats.py` | all methods on the same SMT core, shuffled order, verified outputs; makespan, gain over serial execution, throughput, STP, ANTT, slowdown, bootstrap CIs, prediction error |

Processes are pinned before they execute (Linux: `sched_setaffinity` in the
child; Windows: created suspended, pinned, placed in a limiting Job Object,
then resumed). Jobs run one at a time on a background worker pinned to the
harness CPU; `artifacts/<jobId>/job.json` is updated after every stage.

## Setup — Windows

1. MSYS2 UCRT64 toolchain: `pacman -S mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-binutils`,
   with `C:\msys64\ucrt64\bin` on `PATH` ahead of any older MinGW.
2. `python -m venv venv; .\venv\Scripts\Activate.ps1; pip install -r backend\requirements.txt`
3. Optional, for hardware counters: Intel VTune Profiler, then once in an
   admin PowerShell: `amplxe-sepreg.exe -i` (in VTune's `bin64`). EMON
   needs an **elevated** process, so run calibration, experiments or the
   server from an admin terminal to profile in `emon` mode; otherwise the
   backend uses probe mode.

## Setup — Linux / WSL2

```sh
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
sudo apt install binutils g++          # objdump and the compiler
sudo apt install linux-tools-generic   # optional: perf (native Linux only)
```

For counters on native Linux: `sudo sysctl kernel.perf_event_paranoid=1`.
Under WSL2 `perf` is normally unavailable and the sibling map is virtual,
so results there are not representative.

`HARP_PROFILE_MODE=perf|emon|probe` forces a profiling mode.

## Calibrate once per machine and mode

```sh
python -m backend.calibrate --repetitions 3
```

Profiles the ten training kernels in `backend/kernels/stressors.cpp`,
co-runs all 55 kernel pairs on one SMT core, fits the regression
coefficients and reports leave-one-workload-out error. Output:
`artifacts/model/coefficients.json`. A model is used only on the platform,
CPU model and profiling mode it was fitted with; otherwise jobs fall back
to documented defaults labelled `heuristic-defaults`.

## Run

```sh
uvicorn backend.app:app --host 127.0.0.1 --port 8000
python -m backend.experiment --repetitions 5     # full comparison from the CLI
python -m pytest backend/tests                   # unit tests (any OS)
```

## API

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | |
| GET | `/api/workloads` | approved workloads from the manifest |
| POST | `/api/jobs` | form: `language=cpp`, `files` (2–16), optional `repetitions` (3–15, default 5); returns immediately, job runs in background |
| GET | `/api/jobs` | job list |
| GET | `/api/jobs/{id}` | full job record, including per-stage progress |
| GET | `/api/jobs/{id}/results` | dashboard payload: per-method summaries, comparisons, pairs, tasks, prediction accuracy (409 until completed) |
| GET | `/api/system` | topology, counter availability, profiling mode, model status |

## Parameters

All tunable constants (SMT cores, loop weight, normalisation references,
EMON events and interval, phase threshold, `Q_MAX`, resource weights `ω`,
default `β`, `μ`, `ν`, `τ`, …) are in `config.py` with their meaning; report
them in the manuscript's parameter table. `HARP_SMT_CORES`,
`HARP_RISK_MU`, `HARP_RISK_NU`, `HARP_RISK_TAU`, `HARP_B_SOCKET` and
`HARP_EMON` can be set from the environment.

## Workloads

`examples/w1`–`w8` each stress one resource for about one second
(integer ALU, divider, scalar FP, SIMD, memory bandwidth, memory latency,
branches, and a three-phase mix). The original `task1`–`task4` remain
approved but run for milliseconds, too short for meaningful measurement.
To add a workload: put the source in `examples/` and add its expected
output to `manifest.json`.

## Limitations

* With fixed pairs, a hardware thread idles once the shorter task of a
  pair finishes; the OS-default baseline never idles a thread.
* Phase alignment assumes co-running workloads progress proportionally.
* Probe mode yields one whole-program phase per workload.
* EMON multiplexes two counter groups; group-only totals (cache, branch)
  cover about half of the run.
* When workloads in a pair differ in length, the longer one finishes alone;
  measured slowdown (Equation 10) includes that effect in both training and
  evaluation.
