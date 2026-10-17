# Documentation guide — updating the HARP-PAF manuscript

The current manuscript (`HARP FINAL DOCUMENTATION.1.pdf`) was written
**before** the system was built: it says "no performance improvement is
claimed", has placeholder figures/tables, and its Equations 1–8 turned out
not to predict slowdown. The system is now built and measured. Your job is
to bring the manuscript up to date using **only** the facts and numbers in
this guide and in `docs/results/`. Read [README.md](README.md) first.

**Where to work:** put your files in `docs/manuscript/` (Word/LaTeX source,
figures in `docs/manuscript/figures/`, exported PDF). Push to `sanjay`.

**Golden rules**
1. Every number must come from this guide or from `docs/results/*.json`.
   Don't round differently in different places; use the values below.
2. Results are from **one machine, one core, 8 workloads, 10 repetitions**.
   Say so. Don't claim the method works on all CPUs or real applications.
3. Keep the related-work section; it is fine. Add one new reference (Bubble-Up, below).

---

## 1. What changed compared with the draft (big picture)

| Draft said | Final system |
|---|---|
| Pair workloads once with a minimum-weight matching (Blossom) | **Dynamic SMT co-scheduling**: whenever a hardware thread frees up, start the waiting program predicted to slow down least next to the program still running. The matching is kept as a comparison variant ("static pairs"). |
| Equations 1–8 (R, K, B, O, X, S) predict slowdown | They did **not** predict better than guessing the average (held-out error 0.129 vs 0.133). Replaced by the **bottleneck sensitivity × aggressiveness** model (held-out error 0.069). Keep Eq. 1–8 only as the "original model" in a comparison table. |
| Runtime profiling with perf | **Intel EMON** (VTune) hardware counters on Windows, **plus stressor probes** that measure how sensitive each program is to each shared resource. |
| Objective: execution time or throughput | Objective fixed as **makespan on one SMT core** (total time for the set of programs). Throughput, ANTT and STP also reported. |
| Baselines Random and PORT | Random, PORT, **OS default**, **serial (no SMT)** and **HARP-PAF static pairs**. |
| MongoDB database | **No database**: results are stored as JSON files. Remove MongoDB from the paper (Sections 4.1, 5, ref [30]). |
| Linux / WSL | **Native Windows 11** on an Intel i5-1235U (Linux is also supported by the code). |

## 2. Title, abstract, keywords

**Title** can stay. Optional subtitle: "…with Dynamic SMT Co-Scheduling".

**Abstract** — rewrite the last three paragraphs. Suggested text (adapt freely):

> HARP-PAF characterises each workload by fusing static analysis of the
> compiled binary with runtime evidence: per-phase hardware-counter profiles
> collected with Intel EMON and interference sensitivities measured by
> co-running the workload with five resource-specific stressor kernels. A
> regression model predicts the slowdown of any workload pair from the
> sensitivity of each thread to its most contended resource and the
> aggressiveness of its co-runner on that resource. A dynamic scheduler uses
> these predictions to choose co-runners on the two hardware threads of one
> physical core so that no thread idles while work remains.
>
> On an Intel Core i5-1235U (one SMT performance core) with eight
> resource-specific workloads and ten repetitions, HARP-PAF completed the
> workload set in a median of 3.20 s, compared with 3.49 s for random
> co-scheduling, 3.53 s for the operating-system scheduler, 3.74 s for
> port-contention-aware pairing (PORT) and 5.47 s for serial execution; it
> was faster than every baseline in at least nine of ten repetitions. The
> slowdown model reached a held-out mean absolute error of 0.069 (rank
> correlation 0.84) on 55 measured training pairs, against 0.129 for the
> originally proposed feature equations. The results are from a single
> processor and a small workload set; broader validation is future work.

**Keywords:** add "Dynamic co-scheduling", "Interference sensitivity",
"Intel EMON"; keep the others.

## 3. Section 1 (Introduction)

* Remove "These are design goals rather than claims of completed
  functionality" and the sentence saying values must be filled later.
* Replace the four contributions with:
  1. a fusion of static binary analysis with phase-level hardware counters
     and measured interference sensitivity;
  2. a bottleneck sensitivity × aggressiveness model of pairwise SMT slowdown,
     validated on held-out workloads;
  3. a phase-aware dynamic SMT co-scheduler that keeps both hardware
     threads busy;
  4. a controlled evaluation against Random, PORT, OS default, serial and a
     static-matching variant, with drift-free measurement on a laptop CPU.

## 4. Section 2 (Related work)

Keep 2.1–2.15. Add a short subsection (it is the basis of our probing):

**2.16 Mars et al. (2011) — Bubble-Up.** Measures an application's
sensitivity to memory-subsystem pressure by co-running it with a tunable
"bubble" and predicts co-location interference from sensitivity and the
pressure a co-runner generates. HARP-PAF applies the same
sensitivity/pressure idea at SMT-core level with five stressors and
counter-based aggressiveness. Reference to add:

> J. Mars, L. Tang, R. Hundt, K. Skadron, and M. L. Soffa, "Bubble-Up:
> Increasing Utilization in Modern Warehouse Scale Computers via Sensible
> Co-locations," Proceedings of the IEEE/ACM International Symposium on
> Microarchitecture (MICRO), 2011, pp. 248–259. doi:10.1145/2155620.2155650.

References [16]–[30] are listed but never cited in the text: cite them where
relevant or remove them. Remove [30] (MongoDB).

## 5. Section 3 (Proposed work) — rewrite

### 3.1 Problem formulation (replace)
Given a set W of n workloads and one physical core with two hardware
threads (SMT siblings), find a schedule that assigns workloads to the two
threads over time so that the **makespan** (time until all workloads
finish) is minimal. Each workload runs once, without preemption. References:
serial execution (each workload alone, one after another) and the OS
scheduler (all workloads started at once on the two threads).

### 3.2 System architecture (Figure 1 — draw this)
Boxes and arrows, left to right:
`C++ source` → `Compile (GCC -O2)` → `Verify output` →
**Algorithm A**: `Static analysis (objdump, instruction mix, loop weights)` and
**Algorithm B**: `Runtime profiling: EMON counters (phases) + stressor probes (sensitivity)` →
`Adaptive fusion (per workload, phase, feature)` →
`Slowdown model (sensitivity × aggressiveness)` →
`Dynamic SMT co-scheduler` → `Execution on one P-core (CPU 0/1)` →
`Measurement & evaluation`. A side box "Calibration (training kernels)"
feeds the slowdown model.

### 3.3 Detailed methodology (replace the steps)
1. **Environment and topology.** Hardware threads that share a core are read
   from the OS (Windows `GetLogicalProcessorInformationEx`; Linux sysfs).
   On the hybrid i5-1235U only performance cores have SMT; workloads run on
   P-core 0 (logical CPUs 0 and 1), the measurement harness on E-core CPU 11.
   Every process is pinned before it starts executing.
2. **Static features (Algorithm A).** The binary is disassembled with
   `objdump`; only user functions reachable from `main` are analysed.
   Instructions are classified into integer ALU, multiply/divide, FP/SIMD,
   load/store and branch, and weighted by 10 per loop-nesting level
   (loops = backward branches). Output: static instruction mix and proxies.
3. **Runtime profiling (Algorithm B).**
   * *Counters:* EMON samples 13 events (instructions, cycles, LLC
     references/misses, branches, branch misses, divider activity, FP scalar
     and vector, loads, stores, front-end bubbles, back-end-bound slots) in
     two groups of 50 ms, giving 100 ms windows. Partial windows at the
     start/end are dropped.
   * *Phases:* a new segment starts when a window differs from the running
     segment mean by more than 0.25 in any normalised measure; segments
     shorter than 2 windows are merged; similar segments share a phase label.
     Windows are positioned by instruction progress (0–100 % of retired
     instructions).
   * *Sensitivity probes:* the workload is run on CPU 0 while a stressor
     kernel runs on its sibling CPU 1, for each of five stressors (integer
     ALU, FP/divider, memory stream, cache, branch). Sensitivity = slowdown
     against its solo time.
4. **Adaptive fusion.** For every workload, phase and feature, static and
   runtime estimates are combined with a confidence weight (Eq. F below).
   Concatenation is not used: the weight changes per workload, phase and feature.
5. **Pair prediction.** Pair slowdown is predicted with the bottleneck
   sensitivity × aggressiveness model (Eqs. S1–S4), fitted on 55 pairs of
   10 training kernels (never the evaluation workloads), validated by
   leave-one-workload-out.
6. **Scheduling.** Dynamic SMT co-scheduling (Algorithm 3).

Figures: Fig. 2 CPU topology (2 P-cores × 2 threads, 8 E-cores; highlight
CPU 0/1 and harness CPU 11). Fig. 3 static pipeline. Fig. 4 phase timeline
of w8 (see §7 for data).

### 3.5 Modules table (replace)
| Module | Function | Output |
|---|---|---|
| Topology discovery | Real SMT siblings and P/E cores from the OS | Core used, harness CPU |
| Static analysis | Instruction mix of user code, loop-weighted | Static profile |
| Counter profiling (EMON) | 100 ms counter windows, phase detection | Phases, per-phase usage |
| Sensitivity probing | Co-run with 5 stressor kernels | Sensitivity vector |
| Adaptive fusion | Confidence-weighted static/runtime combination | Fused per-phase features |
| Slowdown model | Bottleneck sensitivity × aggressiveness, NNLS | Predicted pair slowdown |
| Dynamic scheduler | Online co-runner choice on 2 hardware threads | Schedule (timeline) |
| Evaluation | All methods, same core, shuffled order, 10 reps | Makespan, ANTT, STP, CIs |

### 3.6 Equations (replace 3.6.1–3.6.8; keep 3.6.9 as the static variant)

**(F) Adaptive fusion** — for workload i, phase t, feature k:
`x(i,k,t) = q(i,k,t)·d(i,k,t) + (1 − q(i,k,t))·s(i,k)`,
where s = static estimate, d = runtime estimate,
`q = Q_max · max(0, 1 − σ/σ_ref) · min(1, n_t / n_min)`;
σ = within-phase standard deviation of the normalised measure,
σ_ref = 0.25, Q_max = 0.9, n_t = windows in the phase, n_min = 2.
q = 0 when the runtime measure is unavailable.

**(S1) Sensitivity:** `sens(i,k) = T(i | stressor k) / T_solo(i) − 1`, capped at 2.0.

**(S2) Aggressiveness:** `aggr(j,k,t) = min(1.5, x(j, agg_k, t) / g_k)`,
where g_k is stressor k's own value (its "signature", measured during
calibration), and the usage measures are:
* integer: `min(1, IPC · m_int / 5)` (5 integer ALU ports);
* FP/divider: `max(divider busy fraction, min(1, IPC · m_fp / 3))` (3 vector ports);
* memory stream: `LLC misses · 64 B / Δt / B_socket` (B_socket = 20 GB/s);
* cache: `footprint · (1 − LLC miss ratio)`, footprint = LLC references per
  kilo-instruction / 40;
* branch: branch misses per kilo-instruction / 40.
  (m = runtime instruction-mix share.)

**(S3) Bottleneck interaction** (π_t = weight of aligned phase interval t):
`H(i,j) = Σ_t π_t · ½ · [ max_k sens(i,k)·aggr(j,k,t) + max_k sens(j,k)·aggr(i,k,t) ]`
Each thread is slowed mainly by its most contended resource; using the
maximum avoids counting overlapping contention twice.

**(S4) Predicted slowdown:** `ŷ(i,j) = max(0, b0 + b·H(i,j))`; calibrated
b0 = 0.0381, b = 0.7003 (non-negative least squares). A second model with
the same form predicts the worse of the two threads' slowdowns, d̂_worst.

**(Eq. 10, keep)** measured target `y = ½[(T_i|j / T_i_solo − 1) + (T_j|i / T_j_solo − 1)]`.

**(D) Pair duration:** `D(i,j) = max(T_i, T_j) + min(T_i, T_j) · ŷ(i,j)`.

**(Eq. 11, update)** `J(i,j) = D(i,j) + min(T_i,T_j)·[μ·max(0, d̂_worst − τ) + ν·σ_ij]`,
`σ_ij = RMSE_heldout · (1.5 − 0.5(q̄_i + q̄_j))`, μ = 1.0, ν = 0.5, τ = 0.25. J is in seconds.

**(R) Dynamic choice rule:** when a hardware thread frees while workload r
runs on its sibling at estimated progress
`p = min(0.95, elapsed / (T_r · (1 + ŷ_r)))`, start the waiting workload c
minimising `ŷ(r_[p,1], c) + μ·max(0, d̂_worst − τ) + ν·σ`, where r_[p,1] is
r's remaining phases. Ties → longer solo time first. On an idle core the
longest workload starts first.

**Original Equations 1–8:** move to a subsection "Original feature model"
and report its accuracy in Table 4 (§7). Fix Eq. 3 (truncated, and uses
C_shared_private instead of C_eff) and remove the X and S lines duplicated
inside Eq. 5.

**3.6.9 Global pair selection** stays, as the "HARP-PAF static pairs" variant:
exact minimum-cost perfect matching (dynamic programming over subsets,
same optimum as Blossom); an odd workload out runs alone.

### 3.7 Algorithms (replace)
**Algorithm 1 — Characterise workload w:** compile; verify output; warm up
the core 10 s; measure solo time (1 warm-up + 3 runs, median); EMON
collection → windows → phases; 5 stressor probes → sensitivity; static
analysis; fuse.

**Algorithm 2 — Calibrate (once per machine):** characterise 10 training
kernels (int, div, fp, simd, stream, chase, cache, branch, l1, phased);
record stressor signatures g_k; for all 55 kernel pairs (incl. a kernel with
itself), 3 repetitions of {solo a, solo b, co-run} in shuffled order →
median per-task slowdowns → y, y_worst; fit b0, b by NNLS; report
leave-one-workload-out error.

**Algorithm 3 — Dynamic SMT co-scheduling:** fill both threads (idle core:
longest first; otherwise rule R); when any workload finishes, record it and
fill the free thread with rule R; repeat until all are done.

**Algorithm 4 — Evaluation:** warm up; for each of 10 repetitions run every
method once in a freshly shuffled order (HARP-PAF, PORT, Random, HARP-PAF
static pairs, serial, OS default) on the same core; verify every output;
use that repetition's serial run as the solo reference.

## 6. Section 4.1 — Table 1 (hardware/software, final values)

| Item | Value |
|---|---|
| CPU | Intel Core i5-1235U (Alder Lake-P), 2 P-cores (Golden Cove, SMT) + 8 E-cores (Gracemont), 12 logical CPUs |
| Core used | P-core 0 = logical CPUs 0 and 1; harness on E-core CPU 11 |
| Caches (P-core) | L1d 48 KB, L1i 32 KB, L2 1.25 MB per core; L3 12 MB shared |
| Clock | 2.5 GHz TSC, up to 4.4 GHz turbo |
| Memory | 16 GB DDR4-3200 (2 × 8 GB) |
| OS | Windows 11 Home (build 10.0.26300) |
| Compiler | GCC 16.2.0 (MSYS2 UCRT64), `-O2 -std=c++17 -static` |
| Disassembler | GNU objdump (MSYS2 binutils) |
| Counters | Intel VTune Profiler 2026.4, EMON V11.61, SEP driver 5.61 |
| Backend | Python 3.13.7, FastAPI 0.143.3, Uvicorn 0.54.0 |
| Frontend | React 19.3.0, Vite 8.3.4, Recharts 3.10.1, Node.js 22.19.0 |
| Storage | JSON files per job (no database) |
| Workloads | 8 C++ programs `examples/w1`–`w8` (Table 2) |

**Commands** (CODE BLOCK in 4.1):
```
python -m backend.calibrate --repetitions 3      # once, admin terminal
python -m backend.experiment --repetitions 10    # the evaluation
uvicorn backend.app:app --host 127.0.0.1 --port 8000
cd frontend && npm run dev
```

**Table 2 — workloads** (solo time = median from the experiment):

| ID | File | Stresses | Solo (s) | IPC |
|---|---|---|---|---|
| T01 | w1_integer_hash | integer ALU / multiplier | 0.681 | 2.67 |
| T02 | w2_integer_divide | integer divider (latency) | 0.578 | 0.50 |
| T03 | w3_fp_sqrt_chain | scalar FP sqrt/divide chain | 0.717 | 2.23 |
| T04 | w4_simd_saxpy | SIMD on L1-resident arrays | 0.595 | 5.93 |
| T05 | w5_memory_stream | memory bandwidth (64 MiB) | 0.740 | 2.34 |
| T06 | w6_pointer_chase | memory latency (32 MiB) | 0.624 | 0.15 |
| T07 | w7_branch_heavy | unpredictable branches | 0.609 | 0.95 |
| T08 | w8_phased_mix | integer → stream → branch phases | 0.901 | 1.61 |

## 7. Section 4.2 — Parameter table (all from `backend/config.py`)

| Parameter | Value |
|---|---|
| Repetitions (evaluation / calibration / solo timing) | 10 / 3 / 3 (+1 warm-up run) |
| Core warm-up before measuring | 10 s |
| EMON interval | 50 ms per group, 2 groups → 100 ms windows |
| Phase threshold / minimum length | 0.25 / 2 windows |
| Loop weight (static analysis) | 10 per nesting level |
| Fusion: Q_max, σ_ref | 0.9, 0.25 |
| Stressor kernels | int, fp, stream, cache, branch |
| Sensitivity cap / aggressiveness cap | 2.0 / 1.5 |
| Port capacities (Golden Cove) | 5 integer ALU, 3 vector/FP |
| Normalisation | IPC 4; 40 LLC refs/kilo-instr; 40 branch misses/kilo-instr; B_socket 20 GB/s |
| Model coefficients (fitted) | b0 = 0.0381, b = 0.7003 |
| Risk terms | μ = 1.0, ν = 0.5, τ = 0.25 |
| Stressor signatures g_k (fitted) | int 0.416, fp 0.160, stream 0.573, cache 0.915, branch 0.751 |

## 8. Section 4.3 — Metrics (update the table)
Keep slowdown, makespan, prediction error, profiling overhead, decision
time. Add: **gain vs serial** = (T_serial − makespan)/T_serial;
**ANTT** = mean over workloads of T_co-run / T_solo (lower is better);
**STP** = Σ T_solo / T_co-run (higher is better); **throughput** = workloads
per second; **speedup** = median makespan of baseline / median makespan of
HARP-PAF, with a 95 % bootstrap confidence interval (2000 resamples).

## 9. Section 4.5 — Results (the tables to insert)

**Table 3 — Makespan on one SMT core (8 workloads, 10 repetitions)**

| Method | Median makespan (s) | 95 % CI | Gain vs serial | Throughput (workloads/s) | ANTT |
|---|---|---|---|---|---|
| **HARP-PAF** | **3.202** | 3.116–3.400 | **+41.4 %** | **2.50** | **1.12** |
| Random | 3.495 | 3.453–3.651 | +36.0 % | 2.29 | 1.21 |
| OS default | 3.530 | 3.433–3.646 | +35.4 % | 2.27 | 4.32 |
| HARP-PAF (static pairs) | 3.563 | 3.526–3.649 | +34.8 % | 2.25 | 1.18 |
| PORT | 3.741 | 3.583–3.802 | +31.5 % | 2.14 | 1.20 |
| Serial (no SMT) | 5.465 | 5.425–5.684 | 0 % | 1.46 | 1.00 |

**Table 4 — HARP-PAF compared with each baseline**

| Baseline | Speedup | 95 % CI | Runtime reduction | HARP-PAF faster in |
|---|---|---|---|---|
| PORT | 1.168× | 1.075–1.206 | 14.4 % | 10 / 10 |
| HARP-PAF static pairs | 1.113× | 1.043–1.160 | 10.1 % | 10 / 10 |
| OS default | 1.102× | 1.020–1.156 | 9.3 % | 9 / 10 |
| Random | 1.091× | 1.025–1.159 | 8.4 % | 10 / 10 |
| Serial | 1.707× | 1.606–1.795 | 41.4 % | 10 / 10 |

**Table 5 — Slowdown-model accuracy** (55 measured training pairs,
leave-one-workload-out, 100 held-out predictions)

| Model | Held-out MAE | Rank correlation |
|---|---|---|
| Always predict the mean | 0.133 | – |
| Original Equations 1–8 (`calibration-model-eq1-8.json`, earlier calibration) | 0.129 | 0.33 |
| Bottleneck sensitivity × aggressiveness (final) | **0.069** | **0.84** |

Training MAE of the final model 0.066 (≈ held-out, so no overfitting).
Decision time of the scheduler: median 1.5 ms per run.

**Figures to make** (Python/Excel from the JSON files):
* Fig. makespan bar chart with CI error bars — Table 3.
* Fig. ANTT bar chart — Table 3 (shows OS default makes each program wait 4.3× its solo time).
* Fig. HARP-PAF schedule as a Gantt chart (two rows: CPU 0, CPU 1) —
  `docs/api-samples/results.json` → `timelines.harp`. In repetition 1:
  CPU 0 ran T08, T07, T02, T04; CPU 1 ran T01, T06, T05, T03; finished at 3.11 s.
* Fig. sensitivity heatmap (8 workloads × 5 stressors) — `results.json` → `tasks[].sensitivity`.
* Fig. phase timeline of w8 — `tasks[]` entry T08 → `phaseSegments`.
* Fig. predicted vs measured slowdown for the 55 training pairs —
  `docs/results/calibration-model-sa.json` → `samples[]` (`y` measured;
  predicted = max(0, 0.0381 + 0.7003·z.H)).
* Fig. 7 screenshot of the working app (after the frontend team finishes).

**Discussion points to write**
* SMT itself helps: every co-scheduling method beats serial by 31–41 %;
  the choice of co-runner decides how much.
* HARP-PAF beats all baselines; the 95 % intervals of every speedup are
  above 1.0.
* Both ideas matter: dynamic scheduling vs static pairs with the same model
  (+11 %), and the model vs random choices with the same scheduler (+9 %).
* The OS scheduler almost matches on makespan by time-slicing all 8 programs
  but makes each one wait 4.3× its solo time (ANTT 4.32 vs 1.12).
* Why the model works: latency-bound programs (divide, FP chain, pointer
  chase) are insensitive and co-run almost for free; SIMD (IPC 5.9 on a
  6-wide core) is sensitive to everything; the scheduler pairs accordingly
  (e.g. stream next to branch, FP chain next to divide).
* Why Equations 1–8 failed: they multiply instruction *shares* instead of
  usage relative to port capacity, and treat a large footprint as harmful
  even when the program already misses the cache (pointer chase).

**Section 4.4 — comparison with related works:** a qualitative table
(method, platform, signal, reported gain). Feliu et al. [1]: POWER8,
cycle accounting, +4.7–8.8 % vs Linux; Saito & Fujimoto [11]: SIMD port
contention, up to 13.3 % on vRAN; Navarro et al. SYNPA [15]: ARM, 3 dispatch
counters; Mars et al. Bubble-Up: sensitivity/pressure for co-location.
State clearly that their numbers come from other hardware and workloads
and are **not** directly comparable to ours.

**Measurement methodology paragraph (important for credibility):** laptop
CPUs change clock speed; we observed the P-core at ~1 GHz at the start of a
run and ~4.3 GHz later, which made early measurements wrong. Fixes: 10 s
warm-up, solo references measured right next to each co-run during
calibration, a serial run inside every evaluation repetition used as that
repetition's reference, shuffled method order, and a lock so only one
measurement runs at a time.

**Limitations (Section 4.5 end / Section 5):** one processor and one core;
8 synthetic single-resource workloads; probing adds about 5 s per workload;
phase alignment assumes proportional progress; EMON needs admin rights and
the VTune driver; the model must be recalibrated per machine.

## 10. Section 5 (Conclusion) and end matter
* Replace the placeholders with: implementation environment (Table 1
  summary) and results summary (Table 3/4 headline numbers).
* Remove "Do not claim a significant improvement unless…" — we now have
  measured, repeated results with confidence intervals; keep the
  single-machine caveat.
* Future work: more workloads and real applications, other CPUs (AMD,
  server Xeon, Linux `perf` mode), both P-cores, cheaper profiling, online
  phase tracking.
* **Data and code availability:** "Code and data:
  https://github.com/tejas200713/harp-paf (branch `sanjay`), including the
  experiment record `docs/results/experiment-8-workloads-10-reps.json`."
* **Author contributions:** fill in.

## 11. Checklist before you push
- [ ] No "PLACEHOLDER", "Complete only after experiments" or "MongoDB" left.
- [ ] All numbers match Tables 1–5 of this guide.
- [ ] Every figure has a caption and is referenced in the text.
- [ ] References [16]–[30] cited or removed; Bubble-Up added.
- [ ] Single-machine limitation stated in abstract, results and conclusion.
- [ ] Source + PDF in `docs/manuscript/`, pushed to `sanjay`.
