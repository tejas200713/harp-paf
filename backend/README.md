# HARP-PAF backend

FastAPI service that compiles approved C++ workloads, characterises them
with two fused analyses, pairs them onto SMT sibling threads, and measures
the result against Random, PORT and Linux-default placement.

## Pipeline

| Stage | Module | What happens |
|---|---|---|
| Validate | `app.py`, `approved_workloads.py` | 2–16 files; SHA-256 must match a file in `examples/manifest.json` |
| Compile | `compiler.py` | `g++ -O2 -std=c++17` |
| Verify | `runner.py` | each program runs once; stdout must equal the manifest's expected output |
| Topology | `topology.py` | SMT sibling pairs from `/sys/devices/system/cpu/*/topology`; one core reserved for the harness |
| **Algorithm A – static** | `static_features.py` | `objdump` instruction mix (int ALU, mul/div, FP/SIMD, load/store, branch), weighted ×10 per loop-nesting level |
| **Algorithm B – runtime** | `profiler.py`, `phases.py` | `perf stat -I 100` windows → phase segmentation; or, without counters, sensitivity probing against stressor kernels |
| **Adaptive fusion** | `fusion.py` | `x = q·d + (1−q)·s` per workload, phase and feature; `q` from measurement availability and stability |
| Pair features | `features.py` | Equations 1–8 (R, K, B, O, X, S) on phase-aligned fused features |
| Cost model | `model.py` | Equations 9–11: NNLS regression, worst-case model, risk/uncertainty-adjusted cost `J` |
| Matching | `pairing.py` | exact minimum-weight perfect matching (subset DP, IDLE node for odd counts) |
| Baselines | `baselines.py` | Random (redrawn per repetition), PORT (static port-pressure folding), Linux default |
| Evaluation | `benchmarks.py`, `stats.py` | all methods, same cores, shuffled order, verified outputs; makespan, throughput, STP, ANTT, slowdown, bootstrap CIs, prediction MAE |

Jobs run one at a time on a background worker pinned to the harness CPU;
the job file (`artifacts/<jobId>/job.json`) is updated after every stage.

## Setup (Linux / WSL2)

```sh
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
sudo apt install binutils g++          # objdump and the compiler
sudo apt install linux-tools-generic   # optional: perf (native Linux only)
```

For hardware counters on native Linux, allow user-space profiling:
`sudo sysctl kernel.perf_event_paranoid=1`. Under WSL2 `perf` is normally
unavailable and the backend uses probe mode automatically
(`HARP_PROFILE_MODE=perf|probe` forces a mode).

## Calibrate once per machine

```sh
python -m backend.calibrate --repetitions 3
```

Profiles the ten training kernels in `backend/kernels/stressors.cpp`,
co-runs all 55 kernel pairs, fits the regression coefficients and reports
leave-one-workload-out error. Output: `artifacts/model/coefficients.json`.
Until this has been run, jobs use documented default coefficients and are
labelled `heuristic-defaults`. A model is only used in the profiling mode
it was fitted in.

## Run

```sh
uvicorn backend.app:app --host 127.0.0.1 --port 8000
python -m pytest backend/tests           # unit tests (any OS)
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
| GET | `/api/system` | topology, perf availability, profiling mode, model status |

## Parameters

All tunable constants (loop weight, normalisation references, phase
threshold, `Q_MAX`, resource weights `ω`, default `β`, `μ`, `ν`, `τ`, …)
are in `config.py` with their meaning; report them in the manuscript's
parameter table. `HARP_RISK_MU`, `HARP_RISK_NU`, `HARP_RISK_TAU` and
`HARP_B_SOCKET` can be set from the environment.

## Workloads

`examples/w1`–`w8` each stress one resource for about one second
(integer ALU, divider, scalar FP, SIMD, memory bandwidth, memory latency,
branches, and a three-phase mix). The original `task1`–`task4` remain
approved but run for milliseconds, too short for meaningful measurement.
To add a workload: put the source in `examples/` and add its expected
output to `manifest.json`.

## Limitations

* Under WSL2 the sibling map is the hypervisor's virtual topology, and
  hybrid CPUs (P-cores/E-cores) add run-to-run noise; `/api/system` reports
  `virtualized`.
* Phase alignment assumes co-running workloads progress proportionally.
* Probe mode yields one whole-program phase per workload.
* When workloads in a pair differ in length, the longer one finishes alone;
  measured slowdown (Equation 10) includes that effect in both training and
  evaluation.
