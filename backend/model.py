"""Slowdown regression and adjusted pair cost (Equations 9-11).

    y_hat = max(0, b0 + bR*R + bK*K + bB*B + bO*O + bX*X - bS*S)    (9)
    y     = 0.5 * [(T_i|j / T_i_solo - 1) + (T_j|i / T_j_solo - 1)] (10)
    J     = y_hat + mu * max(0, d_worst - tau) + nu * sigma          (11)

All slope coefficients are non-negative (the synergy term enters with a
minus sign); the intercept is unconstrained. They are fitted by
non-negative least squares on measured pairs of the training kernels
(`python -m backend.calibrate`). d_worst comes from a second model with
the same features fitted to the worse of the two per-task slowdowns.
sigma is the held-out RMSE scaled by how much the pair relies on static
evidence: sigma = rmse * (1.5 - 0.5 * (q_i + q_j)).

Until calibration has been run, documented heuristic defaults are used
and every result is labelled `heuristic-defaults`.
"""

from datetime import datetime, timezone
import json

from backend import config
from backend.stats import mae, rmse

FEATURES = config.PAIR_FEATURES


def _row(z):
    return [1.0] + [-z[f] if f == "S" else z[f] for f in FEATURES]


def nnls(rows, targets, free=(0,), iterations=20000, tolerance=1e-12):
    """Least squares with x >= 0 except indices in `free` (coordinate descent)."""

    n = len(rows[0])
    gram = [[sum(r[a] * r[b] for r in rows) for b in range(n)] for a in range(n)]
    rhs = [sum(r[a] * t for r, t in zip(rows, targets)) for a in range(n)]
    x = [0.0] * n

    for _ in range(iterations):
        largest = 0.0

        for k in range(n):
            if gram[k][k] <= 0:
                continue
            gradient = sum(gram[k][m] * x[m] for m in range(n)) - rhs[k]
            value = x[k] - gradient / gram[k][k]
            if k not in free:
                value = max(0.0, value)
            largest = max(largest, abs(value - x[k]))
            x[k] = value

        if largest < tolerance:
            break

    return x


def _to_coefficients(vector):
    return {"intercept": vector[0], **dict(zip(FEATURES, vector[1:]))}


def raw_prediction(z, coefficients):
    row = _row(z)
    vector = [coefficients["intercept"]] + [coefficients[f] for f in FEATURES]
    return sum(a * b for a, b in zip(row, vector))


def fit(samples):
    """samples: [{"pair": (a, b), "z": {...}, "y": float, "yWorst": float}]."""

    rows = [_row(s["z"]) for s in samples]
    mean_model = _to_coefficients(nnls(rows, [s["y"] for s in samples]))
    worst_model = _to_coefficients(nnls(rows, [s["yWorst"] for s in samples]))

    # Leave-one-workload-out: every pair containing w is held out.
    workloads = sorted({w for s in samples for w in s["pair"]})
    predicted, measured = [], []

    for held_out in workloads:
        train = [s for s in samples if held_out not in s["pair"]]
        test = [s for s in samples if held_out in s["pair"]]

        if len(train) < len(FEATURES) + 1 or not test:
            continue

        model = _to_coefficients(
            nnls([_row(s["z"]) for s in train], [s["y"] for s in train])
        )
        for s in test:
            predicted.append(max(0.0, raw_prediction(s["z"], model)))
            measured.append(s["y"])

    training_predictions = [
        max(0.0, raw_prediction(s["z"], mean_model)) for s in samples
    ]

    return {
        "source": "calibrated",
        "coefficients": mean_model,
        "worstCoefficients": worst_model,
        "trainingMae": mae(training_predictions, [s["y"] for s in samples]),
        "heldOutMae": mae(predicted, measured) if predicted else None,
        "heldOutRmse": rmse(predicted, measured) if predicted else None,
        "heldOutCount": len(predicted),
        "sampleCount": len(samples),
        "fittedAt": datetime.now(timezone.utc).isoformat(),
    }


def default_model():
    worst = {
        k: (v * config.DEFAULT_WORST_SCALE if k != "intercept" else v)
        for k, v in config.DEFAULT_COEFFICIENTS.items()
    }
    return {
        "source": "heuristic-defaults",
        "coefficients": dict(config.DEFAULT_COEFFICIENTS),
        "worstCoefficients": worst,
        "heldOutRmse": None,
        "profilingMode": None,
    }


def load_model(mode):
    """Calibrated model for this profiling mode, else heuristic defaults."""

    try:
        model = json.loads(config.MODEL_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default_model()

    if model.get("profilingMode") != mode:
        fallback = default_model()
        fallback["note"] = (
            f"Calibrated model was fitted in {model.get('profilingMode')} "
            f"mode; current mode is {mode}"
        )
        return fallback

    return model


def save_model(model):
    config.MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.MODEL_FILE.write_text(json.dumps(model, indent=2), encoding="utf-8")


def pair_cost(z, model, confidence_i, confidence_j):
    raw = raw_prediction(z, model["coefficients"])
    predicted = max(0.0, raw)
    worst = max(predicted, raw_prediction(z, model["worstCoefficients"]))
    error = model.get("heldOutRmse") or config.DEFAULT_RMSE
    sigma = error * (1.5 - 0.5 * (confidence_i + confidence_j))
    cost = (
        predicted
        + config.RISK_MU * max(0.0, worst - config.RISK_TAU)
        + config.RISK_NU * sigma
    )

    return {
        "predictedSlowdown": predicted,
        "unclampedPrediction": raw,
        "predictedWorstSlowdown": worst,
        "uncertainty": sigma,
        "finalPairCost": cost,
    }
