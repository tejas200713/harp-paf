"""Dynamic SMT co-scheduling: online pairing on the hardware threads.

Each SMT core has two hardware threads. Whenever a thread becomes free and
workloads remain, a policy chooses which workload starts on it, given the
workload still running on the sibling thread (if any). No hardware thread
idles while work remains, so co-runner choice is the only difference
between policies.

Policies
  harp    Phase-aware. For each candidate, the pair features are computed
          between the candidate and the sibling's *remaining* phases (its progress is estimated from elapsed time and the
          slowdown predicted when it was started); the candidate with the
          lowest predicted slowdown plus risk (Eq. 9 and the Eq. 11 terms)
          starts. On an idle core the longest workload starts first, so a
          long task is not left running alone at the end.
  port    PORT rule: minimise port_pressure(sibling) * port_pressure(c);
          on an idle core the most port-intensive workload starts first.
  random  A uniformly random remaining workload (seeded).

Ties are broken by longer solo time, then task ID.
"""

import random
import time

from backend.baselines import port_pressure
from backend.execution import ProcessGroup, ProcessSpec
from backend.features import pair_vector
from backend.model import slowdown_risk


class HarpPolicy:
    name = "harp"

    def __init__(self, characterized, model):
        self.characterized = characterized
        self.solo = {t: c["profile"]["solo"]["median"] for t, c in characterized.items()}
        self.model = model

    def start(self, candidates):
        return max(candidates, key=lambda t: (self.solo[t], t))

    def estimate(self, running, progress, candidate):
        z = pair_vector(
            self.characterized[running], self.characterized[candidate],
            self.model, progress_i=progress,
        )
        return slowdown_risk(
            z, self.model,
            self.characterized[running]["fused"]["meanConfidence"],
            self.characterized[candidate]["fused"]["meanConfidence"],
        )

    def choose(self, running, progress, candidates):
        scored = {c: self.estimate(running, progress, c) for c in candidates}
        best = min(candidates, key=lambda c: (scored[c]["score"], -self.solo[c], c))
        return best, scored[best]["predictedSlowdown"]


class PortPolicy:
    name = "port"

    def __init__(self, characterized):
        self.pressure = {t: port_pressure(c["static"]) for t, c in characterized.items()}
        self.solo = {t: c["profile"]["solo"]["median"] for t, c in characterized.items()}

    def start(self, candidates):
        return max(candidates, key=lambda t: (self.pressure[t], self.solo[t], t))

    def choose(self, running, progress, candidates):
        best = min(
            candidates,
            key=lambda c: (self.pressure[running] * self.pressure[c],
                           -self.pressure[c], -self.solo[c], c),
        )
        return best, 0.0


class RandomPolicy:
    name = "random"

    def __init__(self, seed):
        self.rng = random.Random(seed)

    def start(self, candidates):
        return self.rng.choice(sorted(candidates))

    def choose(self, running, progress, candidates):
        return self.rng.choice(sorted(candidates)), 0.0


def run_dynamic(tasks, solo, slots, policy, timeout):
    """Execute all tasks on the SMT core(s) in `slots` under `policy`.

    Returns makespan, per-task wall seconds, the execution timeline and the
    time spent in scheduling decisions.
    """

    group = ProcessGroup()
    waiting = sorted(tasks)
    sibling = {}
    running = {}
    info = {}
    decision_seconds = 0.0

    for a, b in slots:
        sibling[a], sibling[b] = b, a
        running[a] = running[b] = None

    def progress_of(task):
        elapsed = time.perf_counter() - info[task]["launched"]
        expected = solo[task] * (1 + info[task]["expectedSlowdown"])
        return min(0.95, elapsed / expected) if expected > 0 else 0.0

    def fill():
        nonlocal decision_seconds

        for cpu in sorted(running):
            if running[cpu] is not None or not waiting:
                continue

            partner = running[sibling[cpu]]
            decided = time.perf_counter()

            if partner is None:
                choice, slowdown = policy.start(waiting), 0.0
            else:
                choice, slowdown = policy.choose(partner, progress_of(partner), waiting)

            decision_seconds += time.perf_counter() - decided
            waiting.remove(choice)
            launched = group.start(ProcessSpec(choice, tasks[choice]["argv"], (cpu,)))
            running[cpu] = choice
            info[choice] = {
                "cpu": cpu, "launched": launched, "expectedSlowdown": slowdown,
                "startedWith": partner,
            }

    try:
        fill()
        deadline = group.started + timeout

        while group.pending:
            finished = group.wait_any(deadline)

            if finished is None:
                raise TimeoutError("Dynamic SMT schedule exceeded the timeout")

            running[info[finished]["cpu"]] = None
            fill()

    finally:
        results = group.close()

    for task, entry in results.items():
        if entry.get("exitCode") != 0:
            raise RuntimeError(f"{task}: exit={entry.get('exitCode')}; "
                               f"stderr={entry.get('stderr', '')[:300]!r}")
        expected = tasks[task]["expected"]
        if expected is not None and entry["stdout"].strip() != expected.strip():
            raise RuntimeError(f"{task}: output verification failed")

    timeline = sorted(
        (
            {
                "task": task,
                "cpu": info[task]["cpu"],
                "start": entry["startTime"],
                "end": entry["endTime"],
                "startedWith": info[task]["startedWith"],
                "predictedSlowdown": info[task]["expectedSlowdown"],
            }
            for task, entry in results.items()
        ),
        key=lambda item: (item["start"], item["cpu"]),
    )

    return {
        "makespanSeconds": max(item["end"] for item in timeline),
        "taskSeconds": {t: e["wallSeconds"] for t, e in results.items()},
        "timeline": timeline,
        "decisionSeconds": decision_seconds,
    }
