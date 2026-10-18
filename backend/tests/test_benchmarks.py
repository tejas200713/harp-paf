import pytest
from backend import benchmarks, config
from backend.stats import summarize

def test_verify_success():
    entry = {"exitCode": 0, "stdout": "DONE\n", "stderr": ""}
    # Should not raise
    benchmarks._verify("T01", entry, "DONE")

def test_verify_failure_exit():
    entry = {"exitCode": 1, "stdout": "FAIL\n", "stderr": "error msg"}
    with pytest.raises(RuntimeError) as exc:
        benchmarks._verify("T01", entry, None)
    assert "exit=1" in str(exc.value)

def test_verify_failure_stdout():
    entry = {"exitCode": 0, "stdout": "ACTUAL\n", "stderr": ""}
    with pytest.raises(RuntimeError) as exc:
        benchmarks._verify("T01", entry, "EXPECTED")
    assert "output verification failed" in str(exc.value)

def test_run_metrics_zero_division():
    # If solo time is 0 or makespan is 0, safe_div prevents ZeroDivisionError
    solo = {"T01": 0.0, "T02": 0.5}
    seconds = {"T01": 0.1, "T02": 0.6}
    pairs = [["T01", "T02"]]
    res = benchmarks._run_metrics("harp", pairs, 0.0, seconds, solo, 1)
    assert res["method"] == "harp"
    assert res["throughput"] > 0
    assert "stp" in res
    assert "antt" in res

def test_summarize():
    runs = {
        "serial": [
            {
                "repetition": 1,
                "makespanSeconds": 1.0,
                "throughput": 2.0,
                "stp": 2.0,
                "antt": 1.0,
                "worstTaskSlowdown": 0.1,
                "taskSlowdown": {"T01": 0.0, "T02": 0.0},
                "taskSeconds": {"T01": 0.5, "T02": 0.5},
                "decisionSeconds": 0.001,
                "pairSlowdowns": []
            }
        ],
        "harp": [
            {
                "repetition": 1,
                "makespanSeconds": 0.8,
                "throughput": 2.5,
                "stp": 2.2,
                "antt": 0.9,
                "worstTaskSlowdown": 0.1,
                "taskSlowdown": {"T01": 0.05, "T02": 0.05},
                "taskSeconds": {"T01": 0.55, "T02": 0.55},
                "decisionSeconds": 0.002,
                "pairSlowdowns": [{"pair": ["T01", "T02"], "measured": 0.05, "measuredWorst": 0.05, "measuredPairSeconds": 0.55}]
            }
        ]
    }
    summary = benchmarks._summarize(runs, [], seed=42, repetitions=1)
    assert "methods" in summary
    assert "harp" in summary["methods"]
    assert "comparisons" in summary
