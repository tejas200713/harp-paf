# HARP-PAF Frontend Demo

Frontend-only research dashboard prototype for HARP-PAF. The application uses local illustrative data and simulated job progress. It does not compile or execute source code, collect hardware counters, run the pairing algorithm, or benchmark workloads.

## Run locally

```sh
npm install
npm run dev
```

Open the local URL printed by Vite. To create a production build, run `npm run build`; `npm run preview` serves that build locally.

## Demo walkthrough

1. Start on Home and choose **Upload code**.
2. Choose **C** (default) or **C++**, then add matching `.c` or `.cpp` files, or switch to **Paste code**. Header files are not accepted as standalone program inputs.
3. Choose **Analyze & Optimize** to create a browser-local demo job.
4. Watch the simulated pipeline and inspect the **Program output** panel. Standard output/error remain unavailable in the frontend demo; no submitted code is executed.
5. Open the illustrative results dashboard, then use the sidebar to explore pair analysis, task profiles, prediction analysis, history, and system information.

Prediction accuracy and system details intentionally show empty or unavailable states because no measured evaluation set or backend hardware data is included. Demo jobs are stored in the browser's local storage.
