"""Small dependency-free statistics helpers."""

import math
import random
import statistics


def summarize(samples, seed=0):
    values = [v for v in samples if v is not None]

    if not values:
        return None

    low, high = bootstrap_ci(values, statistics.median, seed=seed)

    return {
        "n": len(values),
        "median": statistics.median(values),
        "mean": statistics.fmean(values),
        "std": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
        "q1": _quantile(values, 0.25),
        "q3": _quantile(values, 0.75),
        "ci95": [low, high],
    }


def cv(values):
    values = [v for v in values if v is not None]

    if len(values) < 2:
        return 0.0

    mean = statistics.fmean(values)
    return statistics.stdev(values) / mean if mean else 0.0


def _quantile(values, q):
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low = math.floor(position)
    high = math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def bootstrap_ci(values, statistic, samples=2000, seed=0, level=0.95):
    if len(values) < 2:
        return values[0], values[0]

    rng = random.Random(seed)
    estimates = sorted(
        statistic(rng.choices(values, k=len(values)))
        for _ in range(samples)
    )
    tail = (1 - level) / 2
    return (
        estimates[int(tail * (samples - 1))],
        estimates[int((1 - tail) * (samples - 1))],
    )


def ratio_of_medians_ci(baseline, treatment, samples=2000, seed=0):
    """Bootstrap CI for median(baseline) / median(treatment)."""

    rng = random.Random(seed)
    estimates = sorted(
        statistics.median(rng.choices(baseline, k=len(baseline)))
        / statistics.median(rng.choices(treatment, k=len(treatment)))
        for _ in range(samples)
    )
    return [
        estimates[int(0.025 * (samples - 1))],
        estimates[int(0.975 * (samples - 1))],
    ]


def _ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0

    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2
        i = j + 1

    return ranks


def spearman(x, y):
    if len(x) < 3:
        return None

    rx, ry = _ranks(x), _ranks(y)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(
        sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)
    )
    return num / den if den else None


def mae(predicted, measured):
    return statistics.fmean(abs(p - m) for p, m in zip(predicted, measured))


def rmse(predicted, measured):
    return math.sqrt(
        statistics.fmean((p - m) ** 2 for p, m in zip(predicted, measured))
    )
