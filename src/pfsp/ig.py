"""Method 2, the researched method: iterated greedy with local search for weighted tardiness.

Source: Ruiz and Stützle (2008, EJOR 187, 1143-1159), the IG_RS_LS algorithm for flow shops with
the total weighted tardiness objective (their Figs. 2 and 3), which adapts the iterated greedy of
Ruiz and Stützle (2007, EJOR 177, 2033-2049).

Representation: a permutation of all jobs, timed by the execution rule in timing.py.

1. Initialization (NEH_EWDD). Order the jobs by earliest weighted due date, i.e. ascending
   d_j / w_j, then insert them one at a time, each at the position of the partial sequence that
   gives the best objective (the NEH insertion step).
2. Local search. Remove jobs one at a time in random order without repetition, reinsert each at its
   best position, and keep the move only if it strictly improves the objective. Repeat passes until
   a pass makes no improvement, so the result is a local optimum of the insertion neighborhood.
3. Iterate. Remove d jobs chosen at random (destruction), reinsert them one by one at their best
   positions in the order removed (construction), and apply the local search. Accept the result if
   it is better than the incumbent, otherwise with probability exp(-(F(new) - F(incumbent)) /
   Temperature), where Temperature = T * (sum of all processing times) / (n * m * 10).
4. Stop after a fixed number of iterations (the time cap is only a safety limit) and return the
   best sequence found.

Settings follow the source: d = 4 and T = 0.5. Three choices are this project's own:
- The objective is compared lexicographically, total weighted tardiness first and total waiting
  between stages (the brief's secondary measure) second, so ties in tardiness, which are common
  when many jobs finish early, are broken toward less work piling up between stages. The
  acceptance probability uses the tardiness difference, as in the source.
- The initial sequence is the better of NEH_EWDD and the rule to beat's EDD sequence, so the
  method can never return a sequence worse than the rule.
- The stopping rule is an iteration count with a fixed seed, as the project guide requires for
  reproducible results, rather than the source's CPU-time limit.
"""

from __future__ import annotations

import math
import time

import numpy as np

from .data import Instance
from .rule import edd_sequence
from .timing import best_insertion, evaluate, insert

DEFAULT_ITERATIONS = 5000
DEFAULT_SEED = 522
DEFAULT_TIME_CAP = 300.0
DESTRUCTION_SIZE = 4
TEMPERATURE_FACTOR = 0.5


class _Problem:
    """Instance arrays bundled for the compiled kernels, with a count of insertion searches."""

    def __init__(self, instance: Instance):
        self.args = (instance.release, instance.due, instance.weight, instance.p)
        self.searches = 0

    def value(self, seq: np.ndarray) -> tuple[float, float]:
        return evaluate(seq, *self.args)

    def best_insertion(self, seq: np.ndarray, job: int) -> tuple[int, float, float]:
        self.searches += 1
        pos, twt, waiting = best_insertion(seq, job, *self.args)
        return int(pos), float(twt), float(waiting)


def ewdd_order(instance: Instance) -> list[int]:
    """Jobs in ascending d_j / w_j (a zero weight sorts last), ties by job identifier."""

    def key(j: int):
        ratio = instance.due[j] / instance.weight[j] if instance.weight[j] > 0 else math.inf
        return (ratio, instance.job_ids[j])

    return sorted(range(instance.n), key=key)


def neh(problem: _Problem, order: list[int]) -> np.ndarray:
    """NEH insertion: build the sequence by inserting each job of `order` at its best position."""
    seq = np.array(order[:1], dtype=np.int64)
    for job in order[1:]:
        pos, _, _ = problem.best_insertion(seq, job)
        seq = insert(seq, pos, job)
    return seq


def local_search(problem: _Problem, seq: np.ndarray, rng: np.random.Generator):
    """Descent in the insertion neighborhood (Ruiz and Stützle 2008, Fig. 2)."""
    value = problem.value(seq)
    improve = True
    while improve:
        improve = False
        for job in rng.permutation(seq):
            rest = seq[seq != job]
            pos, twt, waiting = problem.best_insertion(rest, job)
            if (twt, waiting) < value:
                seq, value = insert(rest, pos, job), (twt, waiting)
                improve = True
    return seq, value


def iterated_greedy(
    instance: Instance,
    iterations: int = DEFAULT_ITERATIONS,
    seed: int = DEFAULT_SEED,
    time_cap: float = DEFAULT_TIME_CAP,
    d: int = DESTRUCTION_SIZE,
    T: float = TEMPERATURE_FACTOR,
) -> tuple[np.ndarray, dict]:
    """Run IG_RS_LS and return (best sequence, details of the run for summary.json)."""
    began = time.perf_counter()
    rng = np.random.default_rng(seed)
    problem = _Problem(instance)
    n = instance.n

    start_neh = neh(problem, ewdd_order(instance))
    start_edd = edd_sequence(instance)
    neh_value, edd_value = problem.value(start_neh), problem.value(start_edd)
    start = start_neh if neh_value <= edd_value else start_edd

    seq, value = local_search(problem, start, rng)
    best, best_value, best_iteration = seq, value, 0
    temperature = T * float(instance.p.sum()) / (n * instance.m * 10)
    d = min(d, n - 1)
    stop_reason = f"completed {iterations} iterations"
    done = 0
    for done in range(1, iterations + 1):
        if d < 1:
            stop_reason = "a single job needs no search"
            break
        if time.perf_counter() - began > time_cap:
            stop_reason = f"time cap of {time_cap} s reached after {done - 1} iterations"
            done -= 1
            break
        # Destruction: remove d distinct jobs chosen at random, keeping the order of removal.
        positions = rng.choice(n, size=d, replace=False)
        removed = seq[positions]
        partial = np.delete(seq, positions)
        # Construction: reinsert each removed job at its best position.
        for job in removed:
            pos, _, _ = problem.best_insertion(partial, job)
            partial = insert(partial, pos, job)
        candidate, candidate_value = local_search(problem, partial, rng)
        # Acceptance criterion with a constant temperature.
        if candidate_value < value:
            seq, value = candidate, candidate_value
            if value < best_value:
                best, best_value, best_iteration = seq, value, done
        elif rng.random() <= math.exp(-(candidate_value[0] - value[0]) / temperature):
            seq, value = candidate, candidate_value

    details = {
        "source": "Ruiz and Stuetzle (2008), IG_RS_LS for total weighted tardiness",
        "seed": seed,
        "iterations_requested": iterations,
        "iterations_run": done,
        "stop_reason": stop_reason,
        "time_cap_seconds": time_cap,
        "destruction_size": d,
        "temperature_factor": T,
        "temperature": temperature,
        "initial_neh_ewdd": {"total_weighted_tardiness": neh_value[0], "waiting": neh_value[1]},
        "initial_rule": {"total_weighted_tardiness": edd_value[0], "waiting": edd_value[1]},
        "initial_used": "NEH_EWDD" if neh_value <= edd_value else "EDD rule",
        "best_found_at_iteration": best_iteration,
        "insertion_searches": problem.searches,
    }
    return best, details


def neh_ewdd(instance: Instance) -> tuple[np.ndarray, dict]:
    """NEH_EWDD alone, reported in the comparison as a construction-only reference."""
    problem = _Problem(instance)
    return neh(problem, ewdd_order(instance)), {"insertion_searches": problem.searches}
