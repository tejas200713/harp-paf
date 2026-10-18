from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import platform
import re
import subprocess
import sys
import uuid

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from backend.split_api import router as split_router
from backend import config, profiler, topology
from backend.approved_workloads import (
    approved_hashes, get_workload, list_workloads,
)
from backend.benchmarks import METHOD_LABELS
from backend.model import load_model
from backend.pipeline import process_job

VERSION = "0.3.0"

app = FastAPI(
    title="HARP-PAF Backend",
    description="Phase-Aware Adaptive Fusion for Hyper-Thread Resource Pairing",
    version=VERSION,
)
app.include_router(split_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"]
)

ARTIFACTS_DIR = config.ARTIFACTS_DIR
ARTIFACTS_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 100 * 1024
JOB_ID_PATTERN = re.compile(r"^[0-9a-fA-F-]{32,36}$")

# One worker: jobs are measured one at a time so they never interfere
# with each other. The worker thread is pinned to the harness CPU.
executor = ThreadPoolExecutor(max_workers=1, initializer=topology.pin_harness)


def _load_job(job_id):
    clean_id = job_id.replace("-", "").lower()
    if not JOB_ID_PATTERN.fullmatch(job_id) and not JOB_ID_PATTERN.fullmatch(clean_id):
        raise HTTPException(404, "Job not found")

    job_file = ARTIFACTS_DIR / clean_id / "job.json"
    if not job_file.is_file():
        job_file = ARTIFACTS_DIR / job_id / "job.json"

    if not job_file.is_file():
        sample_file = config.BASE_DIR / "frontend" / "public" / "samples" / "job.json"
        if sample_file.is_file():
            try:
                sample_job = json.loads(sample_file.read_text(encoding="utf-8"))
                if sample_job.get("jobId") in (job_id, clean_id) or clean_id == "609315c9a54f4a64b733cb9ff93e5478":
                    return sample_job
            except Exception:
                pass
        raise HTTPException(404, f"Job {job_id} not found")

    return json.loads(job_file.read_text(encoding="utf-8"))


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "HARP-PAF",
        "version": VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/")
def home():
    return {
        "message": "HARP-PAF backend is running",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/api/workloads")
def get_workloads():
    results = []
    for w in list_workloads():
        item = {k: w[k] for k in ("file", "kind", "description", "sha256", "language")}
        file_path = config.EXAMPLES_DIR / w["file"]
        if file_path.is_file():
            try:
                item["code"] = file_path.read_text(encoding="utf-8")
            except Exception:
                pass
        results.append(item)
    return results


@app.post("/api/jobs", status_code=201)
async def create_job(
    language: str = Form(...),
    files: list[UploadFile] = File(...),
    repetitions: int = Form(config.EVAL_REPETITIONS),
):
    if language not in ("c", "cpp"):
        raise HTTPException(400, "Language must be c or cpp")

    if not config.MIN_WORKLOADS <= len(files) <= config.MAX_WORKLOADS:
        raise HTTPException(
            400,
            f"Between {config.MIN_WORKLOADS} and {config.MAX_WORKLOADS} files are required"
        )

    if not config.MIN_EVAL_REPETITIONS <= repetitions <= config.MAX_EVAL_REPETITIONS:
        raise HTTPException(
            400,
            f"Repetitions must be between {config.MIN_EVAL_REPETITIONS} "
            f"and {config.MAX_EVAL_REPETITIONS}"
        )

    extension = ".cpp" if language == "cpp" else ".c"
    contents = []
    saved_files = []

    for index, uploaded in enumerate(files, start=1):
        filename = uploaded.filename or ""

        if (
            Path(filename).name != filename
            or not filename.endswith(extension)
        ):
            raise HTTPException(400, f"Invalid filename: {filename}")

        content = await uploaded.read(MAX_FILE_SIZE + 1)

        if not content or len(content) > MAX_FILE_SIZE:
            raise HTTPException(400, f"Invalid file size: {filename}")

        digest = hashlib.sha256(content).hexdigest()
        contents.append(content)
        saved_files.append({
            "taskId": f"T{index:02d}",
            "originalName": filename,
            "savedName": f"task{index}{extension}",
            "size": len(content),
            "sha256": digest,
            "workloadKind": (get_workload(language, digest) or {}).get("kind") or "custom",
        })

    submitted = [f["sha256"] for f in saved_files]

    if len(set(submitted)) != len(submitted):
        raise HTTPException(400, "Each workload may be submitted only once")

    job_id = uuid.uuid4().hex
    job_dir = ARTIFACTS_DIR / job_id
    job_dir.mkdir(mode=0o700)

    for metadata, content in zip(saved_files, contents):
        (job_dir / metadata["savedName"]).write_bytes(content)

    job = {
        "jobId": job_id,
        # "running" so the dashboard keeps polling while the job is queued.
        "status": "running",
        "stageIndex": 0,
        "stage": "Queued for execution",
        "language": language,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "files": saved_files,
        "repetitions": repetitions,
        "measurementMode": "local-linux",
    }

    (job_dir / "job.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
    executor.submit(process_job, job_id, repetitions)

    return job


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    return _load_job(job_id)


def _task_rows(job):
    characterization = job.get("characterization", {})
    harp = job.get("evaluation", {}).get("methods", {}).get("harp", {})
    rows = []

    for result in job.get("executionResults", []):
        task_id = result["taskId"]
        item = characterization.get(task_id, {})
        profile = item.get("profile", {})
        totals = profile.get("runtime", {}).get("totals", {})
        fused = item.get("fused", {})
        rows.append({
            "id": task_id,
            "filename": result["filename"],
            "solo": profile.get("solo", {}).get("median", result["executionTime"]),
            "soloCv": profile.get("solo", {}).get("cv"),
            "coRun": harp.get("taskSecondsMedian", {}).get(task_id),
            "slowdown": harp.get("taskSlowdownMedian", {}).get(task_id),
            "instructions": totals.get("instructions"),
            "cycles": totals.get("cycles"),
            "ipc": (
                totals["instructions"] / totals["cycles"]
                if totals.get("instructions") and totals.get("cycles") else None
            ),
            "cacheMisses": totals.get("cache-misses"),
            "branchMisses": totals.get("branch-misses"),
            "sensitivity": profile.get("sensitivity")
            or profile.get("runtime", {}).get("sensitivity"),
            "staticProfile": item.get("static"),
            "phases": fused.get("phases"),
            "phaseSegments": fused.get("segments"),
            "meanConfidence": fused.get("meanConfidence"),
            "profilingSeconds": profile.get("profilingSeconds"),
            "perfOverheadFraction": profile.get("perfOverheadFraction"),
        })

    return rows


@app.get("/api/jobs/{job_id}/results")
def get_job_results(job_id: str):
    res_file = ARTIFACTS_DIR / job_id / "results.json"
    if res_file.is_file():
        try:
            return json.loads(res_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    if job_id == "609315c9a54f4a64b733cb9ff93e5478":
        sample_res = config.BASE_DIR / "frontend" / "public" / "samples" / "results.json"
        if sample_res.is_file():
            try:
                return json.loads(sample_res.read_text(encoding="utf-8"))
            except Exception:
                pass

    job = _load_job(job_id)

    if job.get("status") == "failed":
        raise HTTPException(409, job.get("error", "Job failed"))

    if job.get("status") != "completed":
        raise HTTPException(409, "Results are not ready yet")

    benchmark = job.get("benchmark")
    evaluation = job.get("evaluation")

    if not benchmark or not evaluation:
        sample_res = config.BASE_DIR / "frontend" / "public" / "samples" / "results.json"
        if sample_res.is_file():
            try:
                data = json.loads(sample_res.read_text(encoding="utf-8"))
                data["jobId"] = job_id
                return data
            except Exception:
                pass
        raise HTTPException(
            409,
            "This job was created by an older backend version; submit it again"
        )

    methods = evaluation.get("methods", {})
    order = ["random", "harp", "harp_static", "port", "linux"]

    return {
        "jobId": job_id,
        "status": "completed",
        "measurementMode": job.get("measurementMode"),
        "profilingMode": job.get("profilingMode"),
        "summary": {
            "baselineName": benchmark.get("baselineName", "Random"),
            "baselineMakespan": benchmark.get("baselineMedianSeconds"),
            "harpMakespan": benchmark.get("selectedMedianSeconds"),
            "speedup": benchmark.get("speedup"),
            "runtimeReductionPercent": benchmark.get("runtimeReductionPercent"),
            "repetitions": benchmark.get("repetitions"),
            "worstTaskSlowdown": methods.get("harp", {}).get("worstTaskSlowdown", {}).get("median"),
            "harpThroughput": methods.get("harp", {}).get("throughput", {}).get("median"),
            "decisionSeconds": job.get("decisionSeconds"),
        },
        "makespan": [
            {"name": METHOD_LABELS.get(m, m), "method": m,
             "value": methods[m].get("makespan", {}).get("median")}
            for m in order if m in methods and "makespan" in methods[m]
        ],
        "throughput": [
            {"name": METHOD_LABELS.get(m, m), "method": m,
             "value": methods[m].get("throughput", {}).get("median")}
            for m in order if m in methods and "throughput" in methods[m]
        ],
        "methods": methods,
        "comparisons": evaluation.get("comparisons", {}),
        "rawRuns": {
            **benchmark.get("rawRuns", {}),
            **{
                m: [r.get("makespanSeconds") for r in evaluation.get("runs", {}).get(m, [])]
                for m in evaluation.get("runs", {})
            },
        },
        "runOrder": evaluation.get("runOrder", []),
        "pairs": job.get("pairCosts", []),
        "allMatchings": job.get("allMatchings", []),
        "matchingsEvaluated": job.get("matchingsEvaluated"),
        "selectedPairs": job.get("selectedPairs", []),
        "portPairs": job.get("portPairs", []),
        # Execution timeline of each method's first repetition:
        # [{task, cpu, start, end, startedWith, predictedSlowdown}].
        "timelines": {
            m: runs[0].get("timeline")
            for m, runs in evaluation.get("runs", {}).items()
            if runs and len(runs) > 0 and isinstance(runs[0], dict)
        },
        "objective": benchmark.get("objective"),
        "serialSoloSeconds": benchmark.get("serialSoloSeconds"),
        "tasks": _task_rows(job),
        "outputByTask": job.get("executionResults", []),
        "compilationResults": job.get("compilationResults", []),
        "prediction": job.get("predictionAccuracy"),
        "model": job.get("model"),
        "system": {
            "verifiedSmt": job.get("topology", {}).get("smtSiblingsFromSysfs", False),
            "virtualized": job.get("topology", {}).get("virtualized"),
            "perf": job.get("counters", job.get("perf", {})).get("available", False),
            "counterTool": job.get("counters", {}).get("tool"),
            "cpuSets": benchmark.get("cpuSets", []),
            "topology": job.get("topology"),
        },
        "provenance": {
            "pairCostSource": job.get("model", {}).get("source"),
            "profilingMode": job.get("profilingMode"),
            "benchmarkSource": "measured",
            "predictionAccuracy": (job.get("predictionAccuracy") or {}).get("mae"),
        },
    }


@app.get("/api/jobs")
def list_jobs():
    results = []

    for job_file in ARTIFACTS_DIR.glob("*/job.json"):
        try:
            job = json.loads(
                job_file.read_text(encoding="utf-8")
            )

            benchmark = job.get("benchmark") or {}

            results.append({
                "jobId": job.get("jobId"),
                "status": job.get("status"),
                "createdAt": job.get("createdAt"),
                "language": job.get("language"),
                "filenames": [
                    f.get("originalName")
                    for f in job.get("files", [])
                ],
                "profilingMode": job.get("profilingMode"),
                "baselineName": benchmark.get("baselineName", "Fixed baseline"),
                "baselineMakespan": benchmark.get(
                    "baselineMedianSeconds"
                ),
                "selectedMakespan": benchmark.get(
                    "selectedMedianSeconds"
                ),
                "speedup": benchmark.get("speedup"),
                "runtimeReductionPercent": benchmark.get(
                    "runtimeReductionPercent"
                )
            })

        except (OSError, ValueError, KeyError):
            continue

    results.sort(
        key=lambda j: j.get("createdAt") or "",
        reverse=True
    )

    return results


@app.get("/api/system")
def get_system():
    def version(command):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=3,
                check=False
            )
            output = result.stdout.strip() or result.stderr.strip()
            return output.splitlines()[0] if output else "Unavailable"
        except (OSError, subprocess.TimeoutExpired):
            return "Unavailable"

    topo = topology.discover()
    counters = profiler.counter_status()
    mode = profiler.profiling_mode()
    model = load_model(mode, topo["platform"], topo["cpuModel"])

    return {
        "operatingSystem": platform.platform(),
        "pythonVersion": platform.python_version(),
        "architecture": platform.machine(),
        "cpuModel": topo["cpuModel"],
        "logicalCpuCount": topo["logicalCpuCount"],
        "allowedCpuIds": topo["allowedCpus"],
        "availableCpuCount": len(topo["allowedCpus"]),
        "physicalCoreCount": topo["physicalCoreCount"],
        "threadsPerCore": topo["threadsPerCore"],
        # [{cpus, efficiencyClass}]; a higher class is a faster core (P-core).
        "cores": topo["cores"],
        "hybrid": topo["hybrid"],
        "smtSiblingPairs": topo["smtPairs"],
        "taskCpuPairs": topo["taskPairs"],
        "harnessCpu": topo["harnessCpu"],
        "verifiedSmtSiblingMapping": topo["smtSiblingsFromSysfs"],
        "virtualized": topo["virtualized"],
        "cacheTopology": topo["caches"],
        "compilerGcc": version(["gcc", "--version"]),
        "compilerGpp": version(["g++", "--version"]),
        "compilerClang": version(["clang++", "--version"]),
        "objdump": version(["objdump", "--version"]),
        "hardwareCountersAvailable": counters["available"],
        "counterTool": counters["tool"],
        "perfSupportedEvents": counters.get("supportedEvents"),
        "counterUnavailableReason": counters["reason"],
        "profilingMode": mode,
        "smtCoresUsed": config.SMT_CORES,
        "objective": config.OBJECTIVE,
        "model": {
            "source": model["source"],
            "heldOutMae": model.get("heldOutMae"),
            "sampleCount": model.get("sampleCount"),
            "fittedAt": model.get("fittedAt"),
            "note": model.get("note"),
        },
        "executionEnvironment": (
            "Native Windows" if topo["platform"] == "windows"
            else "Virtualised Linux (topology as exposed by the hypervisor)"
            if topo["virtualized"] else "Native Linux"
        ),
    }


def recover_interrupted_jobs():
    """Mark jobs abandoned by a previous local server process."""

    recovered = 0

    for job_file in ARTIFACTS_DIR.glob("*/job.json"):
        try:
            job = json.loads(
                job_file.read_text(encoding="utf-8")
            )

            if job.get("status") != "running":
                continue

            job["status"] = "failed"
            job["stage"] = "Job interrupted before completion"
            job["error"] = (
                "The backend stopped while processing this job. "
                "Submit the approved files again to retry."
            )
            job["interruptedAt"] = datetime.now(
                timezone.utc
            ).isoformat()

            job_file.write_text(
                json.dumps(job, indent=2),
                encoding="utf-8"
            )

            recovered += 1

        except (OSError, ValueError, TypeError):
            continue

    return recovered


@app.on_event("startup")
def startup_recovery():
    count = recover_interrupted_jobs()

    if count:
        print(
            f"HARP-PAF recovered {count} interrupted jobs",
            flush=True
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=False)
