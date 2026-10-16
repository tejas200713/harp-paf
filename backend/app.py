


from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import uuid

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from backend.compiler import compile_program
from backend.runner import run_program
from backend.approved_workloads import APPROVED_WORKLOADS, get_expected_output
from backend.features import analyze_workloads
from backend.benchmarks import benchmark_job
app = FastAPI(
    title="HARP-PAF Backend",
    description="Hardware-Aware Resource Pairing API",
    version="0.2.0"
)

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

BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 100 * 1024
JOB_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "HARP-PAF",
        "version": "0.2.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/")
def home():
    return {
        "message": "HARP-PAF backend is running",
        "docs": "/docs",
        "health": "/health"
    }


@app.post("/api/jobs", status_code=201)
async def create_job(
    language: str = Form(...),
    files: list[UploadFile] = File(...)
):
    if language not in ("c", "cpp"):
        raise HTTPException(400, "Language must be c or cpp")

    if len(files) != 4:
        raise HTTPException(400, "Exactly four files are required")

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

        saved_name = f"task{index}{extension}"
        contents.append(content)

        saved_files.append({
            "taskId": f"T{index:02d}",
            "originalName": filename,
            "savedName": saved_name,
            "size": len(content),
            "sha256": hashlib.sha256(content).hexdigest()
        })
    # This local prototype only accepts four reviewed demo programs.
    approved_hashes = set(APPROVED_WORKLOADS[language])

    submitted_hashes = [
        metadata["sha256"] for metadata in saved_files
    ]

    if (
        len(set(submitted_hashes)) != 4
        or set(submitted_hashes) != approved_hashes
    ):
        raise HTTPException(
            400,
            "Live execution is restricted to the four approved demonstration programs"
        )

    job_id = uuid.uuid4().hex
    job_dir = ARTIFACTS_DIR / job_id
    job_dir.mkdir(mode=0o700)

    for metadata, content in zip(saved_files, contents):
        (job_dir / metadata["savedName"]).write_bytes(content)

    job = {
        "jobId": job_id,
        "status": "queued",
        "stageIndex": 0,
        "stage": "Files saved; compilation pending",
        "language": language,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "files": saved_files,
        "measurementMode": "local-wsl2"
    }

    job_file = job_dir / "job.json"

    def save_job():
        job_file.write_text(
            json.dumps(job, indent=2),
            encoding="utf-8"
        )

    save_job()

    job["status"] = "running"
    job["stageIndex"] = 1
    job["stage"] = "Compiling source files"
    job["compilationResults"] = []
    save_job()

    all_success = True

    for index, metadata in enumerate(saved_files, start=1):
        source_path = job_dir / metadata["savedName"]
        output_path = job_dir / f"task{index}"

        result = compile_program(
            source_path,
            output_path,
            language
        )

        job["compilationResults"].append({
            "taskId": metadata["taskId"],
            "filename": metadata["originalName"],
            "success": result["success"],
            "exitCode": result["exitCode"],
            "stdout": result["stdout"],
            "stderr": result["stderr"]
        })

        job["stage"] = f"Compiled {index} of 4 files"
        save_job()

        if not result["success"]:
            all_success = False

    if all_success:
        job["status"] = "running"
        job["stageIndex"] = 3
        job["stage"] = "Executing and verifying programs"
        job["executionResults"] = []
        save_job()

        all_verified = True

        for index, metadata in enumerate(saved_files, start=1):
            executable = job_dir / f"task{index}"

            expected_output = get_expected_output(
                language,
                metadata["sha256"]
            )

            result = run_program(
                executable,
                expected_output,
                timeout=5
            )

            job["executionResults"].append({
                "taskId": metadata["taskId"],
                "filename": metadata["originalName"],
                "success": result.get("success", False),
                "verified": result.get("verified", False),
                "executionTime": result.get("executionTime"),
                "exitCode": result.get("exitCode"),
                "stdout": result.get("stdout"),
                "stderr": result.get("stderr"),
                "timedOut": result.get("timedOut", False),
                "error": result.get("error")
            })

            job["stage"] = f"Executed {index} of 4 programs"
            save_job()

            if not result.get("verified"):
                all_verified = False

        if all_verified:
            job["status"] = "running"
            job["stageIndex"] = 4
            job["stage"] = "Calculating heuristic pairing costs"
            save_job()

            try:
                pairing_result = analyze_workloads()

                job["pairingAnalysis"] = pairing_result

                job["pairCosts"] = pairing_result["pairCosts"]
                job["allMatchings"] = pairing_result["allMatchings"]

                job["selectedMatching"] = pairing_result[
                    "selectedMatching"
                ]

                job["selectedPairs"] = pairing_result[
                    "selectedPairs"
                ]


                job["status"] = "paired"
                job["stageIndex"] = 5
                job["stage"] = "Heuristic pairing complete"
                save_job()

                # Start real repeated benchmarking.
                job["status"] = "running"
                job["stageIndex"] = 6
                job["stage"] = "Running repeated benchmarks"
                save_job()


                benchmark_result = benchmark_job(
                    job_id,
                    repetitions=5
                )

                job["benchmark"] = benchmark_result
                job["status"] = "completed"
                job["stageIndex"] = 8
                job["stage"] = (
                    "Compilation, execution, pairing "
                    "and benchmarking completed"
                )

            except Exception as exc:
                failed_during_benchmark = job.get("stageIndex", 0) >= 6

                job["status"] = "failed"
                job["stageIndex"] = 6 if failed_during_benchmark else 5
                job["stage"] = (
                    "Benchmark execution failed"
                    if failed_during_benchmark
                    else "Heuristic pairing failed"
                )
                job["error"] = f"{type(exc).__name__}: {exc}"
        else:
            job["status"] = "failed"
            job["stageIndex"] = 4
            job["stage"] = "Program execution or verification failed"
            job["error"] = "One or more programs failed verification"

    else:
        job["status"] = "failed"
        job["stageIndex"] = 2
        job["stage"] = "Compilation failed"
        job["error"] = "One or more source files failed to compile"

    save_job()

    return job

@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    if not JOB_ID_PATTERN.fullmatch(job_id):
        raise HTTPException(404, "Job not found")

    job_file = ARTIFACTS_DIR / job_id / "job.json"

    if not job_file.is_file():
        raise HTTPException(404, "Job not found")

    return json.loads(job_file.read_text(encoding="utf-8"))

@app.get("/api/jobs/{job_id}/results")
def get_job_results(job_id: str):
    if not JOB_ID_PATTERN.fullmatch(job_id):
        raise HTTPException(404, "Job not found")

    job_dir = ARTIFACTS_DIR / job_id
    job_file = job_dir / "job.json"

    if not job_file.is_file():
        raise HTTPException(404, "Job not found")

    job = json.loads(job_file.read_text(encoding="utf-8"))

    if job.get("status") == "failed":
        raise HTTPException(
            409,
            job.get("error", "Job failed")
        )

    if job.get("status") != "completed":
        raise HTTPException(
            202,
            "Results are not ready yet"
        )

    benchmark = job.get("benchmark")

    if not benchmark:
        raise HTTPException(
            409,
            "Completed job has no benchmark data"
        )

    return {
        "jobId": job_id,
        "status": "completed",
        "measurementMode": job.get("measurementMode"),
        "summary": {
            "baselineMakespan": benchmark["baselineMedianSeconds"],
            "harpMakespan": benchmark["selectedMedianSeconds"],
            "speedup": benchmark["speedup"],
            "runtimeReductionPercent": benchmark[
                "runtimeReductionPercent"
            ],
            "repetitions": benchmark["repetitions"],
            "worstTaskSlowdown": None
        },
        "makespan": [
            {
                "name": "Fixed baseline",
                "value": benchmark["baselineMedianSeconds"]
            },
            {
                "name": "Heuristic pairing",
                "value": benchmark["selectedMedianSeconds"]
            }
        ],
        "rawRuns": benchmark["rawRuns"],
        "pairs": job.get("pairCosts", []),
        "allMatchings": job.get("allMatchings", []),
        "selectedPairs": job.get("selectedPairs", []),
        "tasks": [
            {
                "id": result["taskId"],
                "filename": result["filename"],
                "solo": result["executionTime"],
                "coRun": None,
                "slowdown": None,
                "instructions": None,
                "cycles": None,
                "phases": None
            }
            for result in job.get("executionResults", [])
        ],
        "outputByTask": job.get("executionResults", []),
        "system": {
            "verifiedSmt": False,
            "perf": False,
            "cpuSets": benchmark.get("cpuSets", [])
        },
        "provenance": {
            "pairCostSource": "illustrative heuristic",
            "benchmarkSource": "measured local WSL",
            "predictionAccuracy": None
        }
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
    import os
    import platform
    import subprocess

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

    allowed_cpus = sorted(os.sched_getaffinity(0))

    return {
        "operatingSystem": platform.platform(),
        "pythonVersion": platform.python_version(),
        "architecture": platform.machine(),
        "logicalCpuCount": os.cpu_count(),
        "allowedCpuIds": allowed_cpus,
        "availableCpuCount": len(allowed_cpus),
        "compilerGcc": version(["gcc", "--version"]),
        "compilerGpp": version(["g++", "--version"]),
        "compilerClang": version(["clang++", "--version"]),
        "verifiedSmtSiblingMapping": False,
        "physicalCoreCount": None,
        "cacheTopology": None,
        "hardwareCountersAvailable": False,
        "executionEnvironment": "Ubuntu WSL local prototype"
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
