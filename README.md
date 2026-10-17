# HARP-PAF — Phase-Aware SMT Co-Scheduling

HARP-PAF dynamically schedules programs onto the hardware threads of a simultaneous multithreading (SMT) CPU core to minimize execution makespan. It characterises workloads by combining static analysis of compiled binaries with runtime Intel EMON hardware counters and stressor probes, predicts pairwise slowdown, and online-dispatches co-runners so no hardware thread idles while work remains.

## Project Structure

- `frontend/`: React 19 + Vite dashboard for job submission, Gantt scheduling visualization, slowdown heatmaps, task telemetry, and model diagnostics.
- `backend/`: FastAPI service with MSYS2 GCC compilation, Intel EMON hardware counter measurement, stressor probe kernels, dynamic SMT scheduler, and calibrated slowdown regression model.
- `docs/`: Handoff documentation, API sample responses, and calibration records.
- `examples/`: Resource-specific benchmark workloads and workload manifest.

## Running the Frontend

```sh
cd frontend
npm install
npm run dev
```

To run with real saved experiment sample data without starting the backend:
```sh
# PowerShell:
$env:VITE_USE_SAMPLES="1"; npm run dev

# Linux / macOS / Bash:
VITE_USE_SAMPLES=1 npm run dev
```

To build for production:
```sh
cd frontend
npm run build
```

## Running the Backend (Windows 11)

From an administrator terminal:
```sh
uvicorn backend.app:app --host 127.0.0.1 --port 8000
```
