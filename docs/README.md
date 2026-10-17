# HARP-PAF — team handoff

The **backend is finished and measured** (branch `sanjay`). Two jobs are
left, and they can run in parallel:

| Who | Guide | What you deliver |
|---|---|---|
| Frontend team | [FRONTEND_GUIDE.md](FRONTEND_GUIDE.md) | Dashboard pages that show the new results (6 methods, schedules, sensitivities, model accuracy) |
| Documentation team | [DOCUMENTATION_GUIDE.md](DOCUMENTATION_GUIDE.md) | Updated manuscript (`HARP FINAL DOCUMENTATION`) with the final method, equations and measured results |

You do **not** need to run any measurements. Real data from our final run is
already in this folder:

| Folder / file | What it is | Used by |
|---|---|---|
| `api-samples/results.json` | Exact response of `GET /api/jobs/{id}/results` for the final experiment | Frontend |
| `api-samples/job.json` | Exact response of `GET /api/jobs/{id}` (full job record) | Frontend |
| `api-samples/system.json`, `workloads.json`, `jobs.json`, `health.json` | The other API responses | Frontend |
| `results/experiment-8-workloads-10-reps.json` | Full record of the final experiment | Documentation |
| `results/calibration-model-sa.json` | Final calibrated slowdown model (55 measured training pairs) | Documentation |
| `results/calibration-model-eq1-8.json` | The old Equations 1–8 model, for the comparison table | Documentation |

## The project in one paragraph

HARP-PAF decides which programs should share **one physical CPU core** that
runs two hardware threads at once (simultaneous multithreading / Hyper-Threading).
For each program it combines **static analysis of the compiled code**
(instruction mix from `objdump`) with **runtime measurements** (Intel EMON
hardware counters and "stressor" probes), predicts how much any two programs
slow each other down, and then **schedules programs onto the two hardware
threads dynamically** so the whole set finishes as early as possible. We
compare it against Random, PORT (port-contention pairing), its own static
pairing, the OS scheduler, and running everything one by one (serial).

**Headline result** (8 workloads, one P-core of an Intel i5-1235U, 10
repetitions): HARP-PAF finished in **3.20 s** vs Random 3.49 s, OS 3.53 s,
PORT 3.74 s and serial 5.47 s, and was faster than every baseline in 9–10 of
10 repetitions.

## Getting the code

```sh
git clone https://github.com/tejas200713/harp-paf.git   # first time only
cd harp-paf
git fetch origin
git checkout sanjay
git pull origin sanjay
```

## Rules for pushing to `sanjay`

1. **Pull before you start and before you push:** `git pull --rebase origin sanjay`.
2. Commit small, focused changes with clear messages, e.g.
   `Frontend: add schedule Gantt chart` or `Docs: rewrite Section 3.6 equations`.
3. Push with `git push origin sanjay`. If it is rejected, run
   `git pull --rebase origin sanjay`, fix any conflicts, and push again.
   Never use `git push --force`.
4. Stay in your area: frontend team only changes `frontend/`; documentation
   team only adds/changes files under `docs/manuscript/` (create it). Do not
   change `backend/`; if something in the data looks wrong or missing, ask
   Sanjay.
5. Never commit `node_modules/`, `venv/`, `artifacts/` or `.env` files
   (they are already in `.gitignore`).
