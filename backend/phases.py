"""Phase detection over fixed-interval runtime windows.

Windows are positioned by instruction progress (cumulative retired
instructions), not wall time, so two workloads can be aligned on relative
progress even when co-running slows one of them down.

1. Segmentation: a new segment starts when a window differs from the
   running mean of the current segment by more than PHASE_THRESHOLD
   (L-infinity distance over normalised measures).
2. Segments shorter than PHASE_MIN_WINDOWS are merged into the most
   similar neighbour (filters warm-up and transient spikes).
3. Segments with similar means receive the same phase label, so a
   program that returns to an earlier behaviour reuses that phase.

pi[t] for a phase is the fraction of instruction progress spent in it.
"""

import statistics

from backend import config

DETECTION_KEYS = ("intensity", "footprint", "bandwidth", "branch_miss")


def _vector(measures):
    return {k: measures.get(k) for k in DETECTION_KEYS}


def _mean(windows):
    mean = {}

    for key in DETECTION_KEYS:
        values = [w["measures"].get(key) for w in windows]
        values = [v for v in values if v is not None]
        mean[key] = statistics.fmean(values) if values else None

    return mean


def _distance(a, b):
    diffs = [
        abs(a[k] - b[k])
        for k in DETECTION_KEYS
        if a.get(k) is not None and b.get(k) is not None
    ]
    return max(diffs) if diffs else 0.0


def single_phase(measures=None):
    return {
        "phases": [{
            "id": 0,
            "share": 1.0,
            "windowCount": 0,
            "measures": measures or {},
            "cv": {},
            "std": {},
        }],
        "segments": [{"start": 0.0, "end": 1.0, "phase": 0}],
        "windowCount": 0,
    }


def detect(windows, threshold=None, min_windows=None):
    """windows: [{"progress": (start, end), "measures": {...}}]."""

    threshold = threshold or config.PHASE_THRESHOLD
    min_windows = min_windows or config.PHASE_MIN_WINDOWS

    if not windows:
        return single_phase()

    segments = [[windows[0]]]

    for window in windows[1:]:
        if _distance(_vector(window["measures"]), _mean(segments[-1])) > threshold:
            segments.append([window])
        else:
            segments[-1].append(window)

    while len(segments) > 1:
        short = [i for i, s in enumerate(segments) if len(s) < min_windows]

        if not short:
            break

        i = min(short, key=lambda n: len(segments[n]))
        neighbours = [n for n in (i - 1, i + 1) if 0 <= n < len(segments)]
        target = min(
            neighbours,
            key=lambda n: _distance(_mean(segments[i]), _mean(segments[n])),
        )
        low, high = sorted((i, target))
        segments[low:high + 1] = [segments[low] + segments[high]]

    centroids = []
    labelled = []

    for segment in segments:
        mean = _mean(segment)
        label = next(
            (n for n, c in enumerate(centroids) if _distance(c, mean) <= threshold),
            None,
        )

        if label is None:
            label = len(centroids)
            centroids.append(mean)

        labelled.append((label, segment))

    phases = []

    for label in range(len(centroids)):
        members = [w for l, seg in labelled if l == label for w in seg]
        share = sum(w["progress"][1] - w["progress"][0] for w in members)
        keys = {k for w in members for k in w["measures"]}
        measures = {}
        cvs = {}
        stds = {}

        for key in keys:
            values = [w["measures"][key] for w in members
                      if w["measures"].get(key) is not None]
            if values:
                mean = statistics.fmean(values)
                spread = statistics.stdev(values) if len(values) > 1 else 0.0
                measures[key] = mean
                stds[key] = spread
                cvs[key] = spread / mean if mean else 0.0
            else:
                measures[key] = None

        phases.append({
            "id": label,
            "share": share,
            "windowCount": len(members),
            "measures": measures,
            "cv": cvs,
            "std": stds,
        })

    return {
        "phases": phases,
        "segments": [
            {
                "start": seg[0]["progress"][0],
                "end": seg[-1]["progress"][1],
                "phase": label,
            }
            for label, seg in labelled
        ],
        "windowCount": len(windows),
    }
