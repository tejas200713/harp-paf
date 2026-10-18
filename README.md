# HARP-PAF

**HARP-PAF** is a research and experimentation platform for analyzing
C++ workloads, exploring simultaneous multithreading (SMT)
co-scheduling, and comparing compilation strategies.

The project contains two separate workflows:

1.  **Multi-workload runtime analysis** --- submit approved C++
    benchmark workloads and inspect execution measurements, scheduling
    comparisons, contention estimates, and analysis results.
2.  **Single Code Optimization** --- submit one supported C++ source
    file, split eligible functions into multiple translation units,
    compile and link the generated program, and compare the original and
    split build times.

> **Important:** These workflows measure different things. The
> multi-workload workflow studies runtime scheduling of independent
> programs. Single Code Optimization compares build/compilation time for
> one program. Splitting source files does not automatically make the
> resulting program run faster.

## Features

### Multi-workload analysis

-   Submit 2--16 approved C++ workload source files.
-   Validate and compile workloads, then verify their output.
-   Inspect job progress and execution output.
-   View the results dashboard, scheduling timeline, pair analysis, task
    metrics, prediction model, and job pipeline stages.
-   Compare scheduling methods using the measurements produced by a run.

Live execution in this workflow is restricted to workloads accepted by
the backend's approved-workload manifest. Arbitrary C++ uploads should
not be treated as approved workloads.

### Single Code Optimization

-   Paste C++ source code or upload a `.cpp` file.
-   Analyze supported source structure using a C++ syntax tree.
-   Generate a header and separate `.cpp` translation units when the
    input meets the splitter's supported restrictions.
-   Compile the original and generated versions and compare their build
    times.
-   Verify that the original and split executables produce matching
    output for the tested input.
-   View and download generated source files.

The current splitter is deliberately conservative and supports only a
subset of C++. It may reject or be unable to safely transform programs
that use complex dependencies, globals, macros, templates, namespaces,
overloads, or other unsupported constructs. A successful syntax parse
alone does not prove full C++ semantic equivalence.

## Technology stack

-   **Frontend:** React and Vite
-   **Backend:** Python and FastAPI
-   **Compiler:** GCC/G++ toolchain
-   **C++ syntax parsing:** Tree-sitter and tree-sitter-cpp
-   **Runtime analysis:** HARP-PAF profiling, contention analysis,
    prediction, and scheduling pipeline

## Repository layout

``` text
Latestsofar/
├── backend/
│   ├── app.py
│   ├── split_api.py
│   ├── source_splitter.py
│   ├── compile_benchmark.py
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── services/
│       │   └── api.js
│       └── SingleCodeOptimization.jsx
├── examples/
│   └── ...
└── splitter_test.cpp
```

The repository may contain additional backend modules, tests,
configuration files, and frontend components not shown in this
abbreviated tree.

## Prerequisites

Install and configure:

-   Python compatible with the project's backend dependencies
-   Node.js and npm
-   GCC/G++ available in the terminal's `PATH`
-   Git

The commands below use Windows PowerShell and the local project folder
used during development. Adjust the path if your clone is stored
elsewhere.

## Setup and run locally

### 1. Open the project

``` powershell
cd C:\Users\jimk7\Desktop\Projects\CompilerDesign\Latestsofar
```

### 2. Set up the Python environment

If the project virtual environment already exists:

``` powershell
.\venv\Scripts\Activate.ps1
```

If dependencies need to be installed, use the repository's dependency
file:

``` powershell
python -m pip install -r backend\requirements.txt
```

### 3. Start the FastAPI backend

In a terminal at the project root:

``` powershell
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
```

Backend health check:

-   http://127.0.0.1:8000/health

Interactive API documentation:

-   http://127.0.0.1:8000/docs

### 4. Start the React frontend

Open a second terminal:

``` powershell
cd C:\Users\jimk7\Desktop\Projects\CompilerDesign\Latestsofar\frontend
npm install
npm run dev
```

Open the local frontend URL printed by Vite. The default development URL
in this setup is:

-   http://localhost:5173

### 5. Use Single Code Optimization

Open:

-   http://localhost:5173/single-code

Paste a supported C++ program or upload a `.cpp` file, then select
**Split & Compare**. Review the generated files, compilation
measurements, output verification, and original/split program outputs.

### 6. Use multi-workload analysis

Open the frontend and select **New analysis**. Upload 2--16 approved
workload files from the project's examples/manifest-approved set, choose
the repetition count, and start the analysis. When the job completes,
inspect its results dashboard and other analysis views.

## API endpoints

The principal endpoints include:

  ------------------------------------------------------------------------------
  Method                  Endpoint                       Purpose
  ----------------------- ------------------------------ -----------------------
  `GET`                   `/health`                      Backend health check

  `GET`                   `/api/workloads`               List approved workloads

  `POST`                  `/api/jobs`                    Create a multi-workload
                                                         analysis job

  `GET`                   `/api/jobs`                    List saved jobs

  `GET`                   `/api/jobs/{job_id}`           Retrieve job
                                                         information

  `GET`                   `/api/jobs/{job_id}/results`   Retrieve analysis
                                                         results

  `POST`                  `/api/split/analyze`           Analyze, split,
                                                         compile, and compare a
                                                         single C++ source file
  ------------------------------------------------------------------------------

See `/docs` for the live API schema and request parameters.

## Understanding the measurements

### Runtime-analysis workflow

The multi-workload workflow measures the execution and scheduling
behavior of independent workload programs. Results can include makespan,
per-method comparisons, slowdown, contention estimates, task profiles,
and prediction information, depending on the data collected by the run
and the available platform support.

### Single-code build comparison

The single-code workflow compares the original program's build time with
the build time for generated translation units plus linking. The
reported speedup is calculated from the measured times; it is not a
guarantee that splitting will be faster.

-   A speedup greater than `1.0×` means the split build was faster in
    that measurement.
-   A speedup below `1.0×` means the split build was slower.
-   One measurement is not sufficient to establish a reliable
    performance conclusion. Repeat runs and report variability before
    making general claims.
-   Matching output on one test input is a useful check, but does not
    prove semantic equivalence for all inputs.

Do not confuse compilation/build time with the runtime of the resulting
application.

## Safety and limitations

-   The single-code endpoint compiles and executes submitted C++ code.
    Keep the development backend bound to `127.0.0.1` and use trusted
    code only.
-   **Do not expose the single-code compilation/execution endpoint
    publicly without a properly designed sandbox and resource
    controls.** Production use requires isolation,
    CPU/memory/time/output limits, safe temporary workspaces,
    concurrency limits, and robust cleanup and error handling.
-   The source splitter supports a restricted subset of C++; unsupported
    or ambiguous transformations should be rejected rather than
    presented as successful.
-   Generated `.cpp` files are translation units intended to be linked
    into one executable. They are not necessarily independent runnable
    programs and should not be submitted as separate workloads to the
    legacy multi-workload analysis endpoint.
-   Hardware counters and profiling data depend on platform and tool
    availability. Missing measurements should be identified as
    unavailable rather than fabricated.
-   Benchmark results can vary with compiler version, compiler flags,
    system load, CPU configuration, and run order.

## Development checks

Frontend production build:

``` powershell
cd frontend
npm run build
```

Backend health check:

``` powershell
curl.exe http://127.0.0.1:8000/health
```

Single-code API smoke test, when `splitter_test.cpp` is present in the
repository root:

``` powershell
curl.exe -X POST "http://127.0.0.1:8000/api/split/analyze" -F "file=@splitter_test.cpp"
```

Run the backend tests using the test commands and configuration defined
by the repository. Before committing changes, inspect `git status` and
avoid committing generated executables, build artifacts, virtual
environments, or unrelated files.

## Contributing

1.  Create a feature branch.
2.  Keep changes focused and preserve the existing multi-workload
    analysis API and scheduling pipeline.
3.  Add or update tests for behavior changes, unsupported source
    constructs, and failure cases.
4.  Run the frontend build and relevant backend tests.
5.  Review `git diff` and `git status` before committing.

## License

Add the project's actual license here if one has been chosen. Do not
assume that the repository is licensed for reuse until its license is
confirmed.
