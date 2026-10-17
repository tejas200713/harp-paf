# Frontend guide — HARP-PAF dashboard

The React app in `frontend/` was built for an older backend (4 fixed demo
files, one "fixed baseline", heuristic pair costs). The backend now returns
much richer, **measured** data. Your job is to update the pages so they show
it correctly. Read [README.md](README.md) first for git rules.

**Stack:** React 19, React Router 7, Recharts 3, Vite 8, lucide-react icons.
Everything is in `frontend/src/App.jsx` (one big file) plus
`frontend/src/services/api.js` (backend calls). Node 22 is used on our machine.

---

## 1. Run the frontend

```sh
cd frontend
npm install        # first time only
npm run dev        # opens on http://localhost:5173
npm run build      # must succeed before you push
```

## 2. Work with real data, without the backend (do this first)

Running real jobs needs Windows admin rights, Intel VTune and ~15 minutes per
job, so **build against the saved responses** in `docs/api-samples/`.

**Task 0 — add a "sample data" switch** (one small commit):

1. Copy the samples into the app's public folder:
   ```sh
   mkdir -p frontend/public/samples
   cp docs/api-samples/*.json frontend/public/samples/
   ```
2. In `frontend/src/services/api.js`, add at the top:
   ```js
   const USE_SAMPLES = import.meta.env.VITE_USE_SAMPLES === '1';

   async function sample(name) {
     const response = await fetch(`/samples/${name}.json`);
     return response.json();
   }
   ```
   and at the start of each function return the matching sample when the
   switch is on:
   | Function | Sample file |
   |---|---|
   | `getResults(id)` | `results` |
   | `getJob(id)` | `job` |
   | `listJobs()` | `jobs` |
   | `getSystem()` | `system` |
   | `checkHealth()` | `health` |
   | new `getWorkloads()` → `GET /api/workloads` | `workloads` |

   Example: `export async function getResults(id) { if (USE_SAMPLES) return sample('results'); ... }`
3. Run with samples: `VITE_USE_SAMPLES=1 npm run dev`
   (PowerShell: `$env:VITE_USE_SAMPLES="1"; npm run dev`).
   The job ID in the samples is `609315c9a54f4a64b733cb9ff93e5478`, so open
   `http://localhost:5173/results/609315c9a54f4a64b733cb9ff93e5478`.

## 3. Running the real backend (optional, Windows)

Only needed for a final end-to-end check. Ask Sanjay to do it on his laptop,
or follow `backend/README.md` (MSYS2 GCC, Python venv, VTune). Backend:
`uvicorn backend.app:app --host 127.0.0.1 --port 8000` from an **admin**
terminal. The frontend already talks to `http://127.0.0.1:8000`.

---

## 4. What the backend returns now

### Method keys, labels and colours (use the same everywhere)

| Key | Label (from API) | Meaning | Suggested colour |
|---|---|---|---|
| `harp` | HARP-PAF | Our method: dynamic scheduling with the slowdown model | `#4bd6d2` (cyan, always highlighted) |
| `harp_static` | HARP-PAF (static pairs) | Our model, but fixed pairs run one after another | `#2a8f8c` |
| `port` | PORT | Pairs by execution-port pressure only | `#8a7cf6` |
| `random` | Random | Random co-runner choice | `#f2a65a` |
| `linux` | OS default | All programs at once, Windows/Linux scheduler decides | `#e06c75` |
| `serial` | Serial (no SMT) | Each program alone, one after another (reference) | `#6b7a93` (grey) |

Always take the label from `methods[key].label`; don't hard-code text.

### Units

* All times are **seconds** (show as `3.20 s`; values < 1 s may be shown in ms).
* Slowdowns are **fractions**: `0.13` means **+13 %**.
* `smtGainVsSerialPercent` and `runtimeReductionPercent` are already percent.
* `speedup` is a ratio: `1.168` → **1.17×**.

### `GET /api/jobs/{id}/results` — `api-samples/results.json`

| Field | Type | What to do with it |
|---|---|---|
| `summary` | object | Headline cards. `harpMakespan`, `baselineMakespan` (Random), `speedup` (vs Random), `repetitions`, `worstTaskSlowdown`, `harpThroughput` (programs/second), `decisionSeconds` |
| `makespan[]` | `{name, method, value}` | Bar chart of median total time per method (lower is better) |
| `throughput[]` | `{name, method, value}` | Bar chart, programs completed per second (higher is better) |
| `methods[key]` | object | Per method: `label`, `makespan` `{median, mean, std, min, max, q1, q3, ci95:[low, high], n}`, `smtGainVsSerialPercent`, `throughput`, `stp`, `antt` (each with `median` etc.), `worstTaskSlowdown`, `taskSlowdownMedian {T01: 0.13, …}`, `taskSecondsMedian`, `decisionSecondsMedian` |
| `comparisons[key]` | object | HARP-PAF vs that method: `speedup`, `speedupCi95 [low, high]`, `runtimeReductionPercent`, `throughputGainPercent`, `harpFasterInRuns` (out of `summary.repetitions`) |
| `rawRuns[key]` | number[] | Makespan of each repetition per method (also old keys `baseline`, `selected`; ignore those) |
| `runOrder[]` | `{repetition, method, makespanSeconds}` | Order the runs actually happened in (optional) |
| `timelines[key]` | array or `null` | **Schedule of repetition 1**: `{task, cpu, start, end, startedWith, predictedSlowdown}`; `null` for `serial` and `linux` |
| `serialSoloSeconds` | number | Median serial makespan (the "no SMT" reference) |
| `objective` | string | `"makespan"` |
| `pairs[]` | object | One per pair of programs: `taskA`, `taskB`, `features {H}`, `contributions {H_int, H_fp, H_stream, H_cache, H_branch}`, `predictedSlowdown`, `predictedWorstSlowdown`, `uncertainty`, `predictedPairSeconds`, `soloSeconds [a, b]`, `finalPairCost` |
| `selectedPairs`, `portPairs` | `[[a,b],…]` | Fixed pairs chosen by HARP-PAF (static variant) and by PORT |
| `allMatchings[]` | `{matching, pairs, totalCost}` | Cheapest 10 pairings; `matchingsEvaluated` = how many exist (105) |
| `tasks[]` | object | Per program: `id`, `filename`, `solo`, `soloCv`, `coRun`, `slowdown`, `instructions`, `cycles`, `ipc`, `cacheMisses`, `branchMisses`, `sensitivity {int, fp, stream, cache, branch}`, `staticProfile` (`instructionMix`, `maxLoopDepth`, `functionsAnalysed`…), `phases[]` (`id`, `share`, `static`, `dynamic`, `confidence`, `fused`), `phaseSegments [{start, end, phase}]`, `meanConfidence`, `profilingSeconds` |
| `prediction` | object | `points[]` (predicted vs measured per pair), `mae`, `pairSecondsMape`… — small here (4 pairs); use `model` for accuracy instead |
| `model` | object | `source` (`calibrated` / `heuristic-defaults`), `featureSet` (`sa`), `coefficients {intercept, H}`, `trainingMae`, `heldOutMae`, `sampleCount`, `fittedAt`, `stressorSignatures`, `kernelSensitivity` |
| `system` | object | `verifiedSmt`, `counterTool`, `cpuSets` (`[[0,1]]` = the core used), `topology` |
| `outputByTask[]` | object | Each program's verified stdout/stderr |

### Other endpoints

| Endpoint | Sample | Notes |
|---|---|---|
| `GET /api/system` | `system.json` | `cpuModel`, `cores[]` (`cpus`, `efficiencyClass`: 1 = P-core, 0 = E-core), `hybrid`, `taskCpuPairs`, `harnessCpu`, `hardwareCountersAvailable`, `counterTool`, `counterUnavailableReason`, `profilingMode`, `smtCoresUsed`, `objective`, `model{…}`, compilers. *The sample was taken from a non-admin terminal, so it shows `probe` mode and the default model — that's expected.* |
| `GET /api/workloads` | `workloads.json` | Approved programs: `file`, `kind`, `description` |
| `GET /api/jobs` | `jobs.json` | History list; `baselineName` is now `Random` |
| `GET /api/jobs/{id}` | `job.json` | Full record; `stageIndex` 0–8 and `stage` text for the progress page |
| `POST /api/jobs` | — | Form fields `language=cpp`, `files` (2–16 files), optional `repetitions` (3–15). Returns immediately with `status: "running"`; poll `GET /api/jobs/{id}` |

---

## 5. Tasks (one commit each is ideal)

Each task lists **what to build**, **which fields** and **how to check it**.
Check every page with the sample data and make sure nothing says
"Illustrative", "WSL", "heuristic" or "Fixed baseline" any more.

### Task 1 — Results dashboard (`LiveResults` in App.jsx) — most important
* **Metric cards:** HARP-PAF makespan, speedup vs Random, gain vs serial
  (`methods.harp.smtGainVsSerialPercent`), ANTT of HARP-PAF, repetitions.
* **Makespan chart:** all six methods from `makespan[]`, error bars from
  `methods[key].makespan.ci95`, HARP-PAF highlighted, serial greyed.
* **Comparison table:** one row per entry in `comparisons`: method,
  speedup (`1.17×`), 95 % CI, runtime reduction %, "faster in X / 10 runs".
* **ANTT chart** (`methods[key].antt.median`): shows that OS default makes
  each program wait ~4.3× its solo time while HARP-PAF stays at 1.12×.
* **Per-repetition line chart:** one line per method from `rawRuns[key]`.
* ✅ Check: HARP-PAF bar = 3.20 s, PORT = 3.74 s, serial = 5.47 s;
  PORT row shows 1.17× (1.08–1.21), faster in 10/10.

### Task 2 — Schedule view (new page `/schedule/:id`, add to sidebar)
* A Gantt chart with two rows ("Hardware thread CPU 0", "CPU 1"), x-axis in
  seconds, one bar per item in `timelines.harp` from `start` to `end`,
  labelled with the task ID / file name.
* Tooltip: "started next to `startedWith`, predicted slowdown +X %".
* A dropdown to switch to `port`, `random`, `harp_static` timelines.
  For `linux`/`serial` show "No per-thread schedule (the OS decides / runs one at a time)".
* Recharts tip: a horizontal `BarChart` with a stacked transparent offset
  bar (`start`) plus the visible duration bar (`end - start`) works well.
* ✅ Check: HARP-PAF row CPU 0 starts with T08 at 0.00 s; whole schedule ends ≈ 3.11 s.

### Task 3 — Pair analysis (`LivePairAnalysis`)
* Heatmap over all task pairs (8×8) of `predictedSlowdown` (as %), or of
  `finalPairCost` with a toggle.
* Pair details: predicted slowdown, worst slowdown, uncertainty,
  predicted pair time (`predictedPairSeconds`), solo times, and a bar
  breakdown of `contributions` (which resource causes the slowdown:
  integer ports, FP/divider, memory bandwidth, cache, branches).
* Show `selectedPairs` (HARP-PAF static) and `portPairs` side by side.
* Matchings card: top 10 from `allMatchings` plus "out of 105".
* Remove the old integer/floating_point/memory/modulo bars.
* ✅ Check: the highest predicted slowdowns are T01+T04 (+55 %) and
  T04+T07 (+54 %); T04 (SIMD) is in 5 of the 6 costliest pairs.

### Task 4 — Task metrics (`LiveTaskMetrics`)
* Table: file, solo time, co-run time, slowdown %, IPC, instructions,
  cycles, cache misses, branch misses (now all measured — remove
  "Unavailable" where data exists).
* For a selected task: **sensitivity chart** (bars or radar of
  `sensitivity`: how much it slows down next to each stressor),
  **instruction mix** pie from `staticProfile.instructionMix`, and a
  **phase timeline** from `phaseSegments` (0–100 % of the run, coloured by phase).
* Optional: a small table of `phases[0].static` vs `dynamic` vs `fused`
  values with `confidence` (shows the static/runtime fusion).
* ✅ Check: T04 (SIMD) has IPC 5.93 and branch sensitivity 1.22;
  T06 (pointer chase) has stream sensitivity 1.25; T08 has 2 phases.

### Task 5 — Prediction analysis (`LivePredictionAnalysis`)
* Cards from `model`: model type ("Bottleneck sensitivity × aggressiveness"),
  held-out error `heldOutMae` (0.069), training error, number of
  calibration pairs `sampleCount` (55), coefficients `b0` and `b` (`coefficients.intercept`, `coefficients.H`).
* A short static comparison table (values from the documentation team):
  always-average 0.133, old Equations 1–8 0.129, new model 0.069.
* Scatter of `prediction.points` (predicted vs measured pair time) with a
  note that only the 4 static pairs are observed in an experiment.
* ✅ Check: held-out error shows 0.069; label says "calibrated".

### Task 6 — Upload & progress
* Upload: accept **2–16** `.cpp` files (not exactly 4), add a
  "Repetitions" number input (3–15, default 5) and send it as form field
  `repetitions`. Show the approved list from `/api/workloads` (file + description).
* Progress: replace the 8 stage labels with:
  1 Validate · 2 Compile · 3 Verify outputs · 4 Profile (counters + probes) ·
  5 Pair costs & model · 6 Benchmark (all methods) · 7 Save · 8 Done.
  Show the live `stage` text under the current step. Jobs take 10–15 min:
  say so on the page.
* ✅ Check: selecting 8 files is allowed; the request includes `repetitions`.

### Task 7 — System information (`SystemInfo`)
* Core map: 12 boxes from `cores[]`, P-cores (efficiencyClass 1) vs
  E-cores (0); highlight the SMT pair in use (`taskCpuPairs[0]`) and the
  harness CPU.
* Rows: CPU model, counter tool + available (+ `counterUnavailableReason`),
  profiling mode, model source / held-out error, objective, SMT cores used, compilers.
* Replace all "WSL" wording with "Windows / Linux".

### Task 8 — History & cleanup
* History: show `baselineName` ("Random") instead of "Fixed baseline".
* Delete unused mock code: `src/services/dataProvider.js`,
  `src/data/mockData.js`, the unused `Results` and `ProgramOutput`
  components and their imports in `App.jsx`.
* Pin versions in `frontend/package.json` (replace every `"latest"` with
  the version in `package-lock.json`, e.g. `"react": "19.3.0"`).
* Update `frontend/README.md` and the root `README.md` (they still say
  "frontend-only prototype").
* Home page: change the text to describe dynamic SMT co-scheduling and
  the headline result (copy wording from the documentation team).

## 6. Definition of done
* `npm run build` succeeds with no errors.
* All pages work with `VITE_USE_SAMPLES=1` and show the numbers listed in the ✅ checks.
* No page shows mock/illustrative values or WSL wording.
* Pushed to `sanjay` following the rules in [README.md](README.md).
