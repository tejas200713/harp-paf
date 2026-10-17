# HARP-PAF Frontend Dashboard

The HARP-PAF dashboard is built with React 19, React Router 7, Recharts 3, and Vite 8. It presents real, hardware-measured performance data from the HARP-PAF dynamic SMT co-scheduling backend.

## Features

- **Results Dashboard (`/results/:id`)**: Compare HARP-PAF makespan against 5 baselines (Random, PORT, OS default scheduler, static pairs, and serial execution), with 95% confidence intervals, speedup ratios, ANTT charts, and per-repetition trends.
- **Hardware Thread Schedule (`/schedule/:id`)**: Gantt timeline showing exact task placement, duration, co-runner overlap, and predicted slowdown across sibling hardware threads (CPU 0 and CPU 1).
- **Pair Analysis (`/pairs/:id`)**: 8×8 pairwise slowdown & cost heatmap, breakdown of resource contention contributions (integer ALU, FP/divider, memory bandwidth, cache, branch), selected pairs comparison, and top matching rankings.
- **Task Metrics (`/tasks/:id`)**: Detailed per-workload telemetry table (solo/co-run time, IPC, cycles, instructions, cache & branch misses), interference sensitivity bar charts, static instruction mix, and execution phase segments.
- **Prediction Analysis (`/predictions/:id`)**: Evaluates the calibrated bottleneck sensitivity × aggressiveness model (MAE 0.069 on 55 training pairs) against baseline equations.
- **System Information (`/system`)**: 12-core physical CPU map highlighting active SMT core (CPUs 0, 1) and harness CPU, alongside Intel EMON counter diagnostics and compilation tools.
- **History & Reports (`/history`)**: Search previous analysis jobs, with CSV and JSON summary exports.
- **New Analysis (`/upload`)**: Select 2–16 workloads and configure repetition counts (3–15) for benchmarking.

## Running Locally

```sh
npm install
npm run dev
```

### Running with Sample Data

To develop and test against saved real experiment data without running the backend service:

```sh
# PowerShell:
$env:VITE_USE_SAMPLES="1"; npm run dev

# Linux / Bash:
VITE_USE_SAMPLES=1 npm run dev
```

The sample experiment ID is `609315c9a54f4a64b733cb9ff93e5478`. Open:
`http://localhost:5173/results/609315c9a54f4a64b733cb9ff93e5478`

### Production Build

```sh
npm run build
npm run preview
```
