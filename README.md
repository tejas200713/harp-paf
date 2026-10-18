# HARP-PAF

HARP-PAF is a C++ workload analysis and scheduling research platform. It
provides a web interface for analyzing approved C++ workloads under
different scheduling strategies, and a separate tool for splitting a
supported single C++ program into multiple source files and comparing
build times.

This guide is written for anyone cloning or downloading the repository
on their own computer. It does not depend on the original developer's
folder paths.

## Features

### Multi-workload runtime analysis

-   Upload 2--16 approved C++ workload programs.
-   Validate and compile the submitted workloads.
-   Verify workload output and inspect execution logs.
-   Compare scheduling strategies and view makespan, slowdown,
    contention, task metrics, and prediction results where measurements
    are available.
-   Review job progress and saved analysis results.

This workflow accepts only workloads approved by the backend's workload
manifest. Arbitrary C++ files are not automatically approved for
execution.

### Single Code Optimization

-   Paste a C++ program or upload a `.cpp` file.
-   Analyze supported C++ source structure.
-   Generate a header and multiple `.cpp` translation units for eligible
    programs.
-   Compile and link the generated source files.
-   Compare the original build time with the split build time.
-   Check whether the original and generated executables produce
    matching output for the tested input.
-   Inspect and download generated source files.

The splitter supports a restricted subset of C++. It may reject programs
containing constructs or dependencies it cannot safely transform.
Generated source files are intended to be linked into one executable;
they are not necessarily separate runnable programs.

## Technology stack

-   React and Vite
-   Python and FastAPI
-   GCC/G++ compiler toolchain
-   Tree-sitter and tree-sitter-cpp for C++ syntax parsing

## Requirements

Install the following on your computer before starting:

1.  **Git** --- to clone the repository, or download the repository ZIP
    from GitHub.
2.  **Python 3** --- use a version supported by the dependencies in
    `backend/requirements.txt`.
3.  **Node.js and npm** --- use a current supported Node.js LTS release.
4.  **A C++ compiler** --- GCC/G++ must be installed and available on
    your terminal's `PATH`.

On Windows, GCC/G++ can be installed using a distribution such as MSYS2.
On Linux, use your distribution's package manager. On macOS, install a
suitable compiler toolchain such as Xcode Command Line Tools or GCC.
Compiler commands and availability can vary by operating system.

## Get the project

Clone the repository:

``` bash
git clone https://github.com/tejas200713/harp-paf.git
cd harp-paf
```

Alternatively, download the repository ZIP from GitHub and extract it.
Open a terminal in the extracted project root---the directory containing
the `backend` and `frontend` folders.

## Backend setup

### 1. Create a virtual environment

**Windows PowerShell:**

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux or macOS:**

``` bash
python3 -m venv .venv
source .venv/bin/activate
```

If PowerShell blocks environment activation, use an appropriate local
execution-policy setting or run the environment's Python executable
directly. Avoid changing system-wide security settings unnecessarily.

### 2. Install Python dependencies

From the project root, with the virtual environment activated:

``` bash
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

### 3. Start the backend

From the project root:

``` bash
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
```

Keep this terminal open while using the application.

Backend health endpoint:

-   http://127.0.0.1:8000/health

Interactive API documentation:

-   http://127.0.0.1:8000/docs

## Frontend setup

Open a **second terminal** at the project root.

Move into the frontend directory and install the dependencies:

``` bash
cd frontend
npm install
```

Start the development server:

``` bash
npm run dev
```

Open the URL printed by Vite in the terminal. The default is usually:

-   http://localhost:5173

Keep the frontend terminal open as well.

## Use the application

### Single Code Optimization

1.  Start both backend and frontend servers.
2.  Open `http://localhost:5173/single-code` if Vite is using its
    default port.
3.  Paste supported C++ source code or upload a `.cpp` file.
4.  Select **Split & Compare**.
5.  Review the compilation measurements, output-verification status,
    original and split outputs, and generated source files.
6.  Download generated files if needed.

If Vite prints a different port, use the URL it provides. If the backend
is configured for a different host or port, update the frontend API
configuration accordingly.

### Multi-workload analysis

1.  Open the web application.
2.  Select **New analysis**.
3.  Choose 2--16 approved workload files from the repository's examples
    and workload manifest.
4.  Select the number of repetitions supported by the interface.
5.  Submit the analysis and wait for the job to finish.
6.  Open the results dashboard and other analysis views.

Only use files approved by the backend's manifest for this workflow. A
source file compiling successfully on your computer does not mean it is
approved by the application.

## API reference

The backend exposes these principal endpoints:

  ------------------------------------------------------------------------------
  Method                  Endpoint                       Purpose
  ----------------------- ------------------------------ -----------------------
  `GET`                   `/health`                      Check backend health

  `GET`                   `/api/workloads`               List approved workloads

  `POST`                  `/api/jobs`                    Submit a multi-workload
                                                         analysis

  `GET`                   `/api/jobs`                    List saved jobs

  `GET`                   `/api/jobs/{job_id}`           Retrieve a job

  `GET`                   `/api/jobs/{job_id}/results`   Retrieve job results

  `POST`                  `/api/split/analyze`           Analyze and benchmark a
                                                         single C++ source file
  ------------------------------------------------------------------------------

Visit `http://127.0.0.1:8000/docs` while the backend is running to see
the actual request schemas and available endpoints.

## Understanding the results

### Runtime scheduling measurements

The multi-workload workflow studies the execution behavior of
independent programs and compares scheduling strategies. Depending on
the platform and available measurements, results may include makespan,
slowdown, contention, throughput, task profiles, and prediction metrics.

### Compilation measurements

The Single Code Optimization workflow compares the time required to
build the original program with the time required to compile generated
translation units and link them into a program.

-   A reported speedup above `1.0×` means the split build was faster in
    that measurement.
-   A reported speedup below `1.0×` means the split build was slower.
-   Small programs may take longer to build after splitting because of
    extra compiler startup and linking overhead.
-   Results can vary with compiler version, build flags, CPU, system
    load, and run order. Repeat measurements before drawing conclusions.
-   Matching output for a test case is useful evidence, but does not
    prove equivalence for every possible input.

**Build time and application runtime are different metrics.** Do not
interpret a faster build as proof that the resulting application
executes faster.

## Troubleshooting

### The frontend cannot connect to the backend

-   Confirm the backend terminal is still running.
-   Open `http://127.0.0.1:8000/health`.
-   Check the frontend API base URL and any proxy configuration.
-   Check the browser developer console and the backend terminal for the
    actual error.

### The C++ compiler is not found

Run:

``` bash
g++ --version
```

If the command is not found, install GCC/G++ and add its executable
directory to your `PATH`. Restart the terminal after changing
environment variables.

### Python dependencies fail to install

-   Confirm the virtual environment is activated.
-   Confirm you are running the command from the project root.
-   Check the Python version and the error message for the dependency
    that failed.
-   Install the packages listed in `backend/requirements.txt`; do not
    assume dependencies installed globally are available inside the
    virtual environment.

### The source splitter rejects a program

The splitter only supports a restricted subset of C++. Rejection may be
expected when the code contains syntax, declarations, or dependencies
that cannot safely be moved between translation units. Use a small
supported example to verify the setup before trying more complex code.

### The page or API returns an error

Check that both servers are running, inspect the browser's Network and
Console tabs, and read the backend traceback. Use the live API
documentation at `/docs` to confirm endpoint paths and request fields.

## Security notes

The single-code endpoint compiles and executes submitted C++ code. It is
intended for controlled local development and trusted test inputs.

**Do not deploy this service to a public server as-is.** Before allowing
untrusted users to submit code, implement a strong sandbox and process
isolation, CPU and memory limits, execution timeouts, output-size
limits, temporary-directory isolation and cleanup, concurrency controls,
and robust error handling. Binding the development backend to
`127.0.0.1` keeps it local to the computer.

## Development and validation

From the project root, check the backend health:

``` bash
curl http://127.0.0.1:8000/health
```

On Windows PowerShell, `curl.exe` can be used if `curl` resolves to a
PowerShell alias.

Build the frontend:

``` bash
cd frontend
npm run build
```

If the repository includes backend tests, run them using the test
configuration and instructions maintained in the repository.

Before submitting changes, inspect `git status` and avoid committing
virtual environments, generated executables, local secrets, or unrelated
build artifacts.

## Contributing

1.  Create a separate Git branch for your change.
2.  Keep the existing runtime-analysis workflow and the single-code
    build workflow distinct.
3.  Add tests for new behavior and failure cases.
4.  Run the frontend build and relevant backend tests.
5.  Review the final diff before committing.

## License

Check the repository for a `LICENSE` file before reusing or
redistributing this project. If no license is present, do not assume
that reuse is permitted.
