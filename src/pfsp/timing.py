"""Timing of a fixed job sequence on the line, and the two measures the methods optimize.

Every function here applies the execution rule shared by both methods and the stress test: keep
the sequence, and start each operation at the later of the job's completion at the previous stage
(or its release, at the first stage) and the stage's completion of the previous job in the
sequence. A sequence is an int64 array of job indices into the Instance arrays.

The kernels are compiled with Numba because the researched method evaluates many thousands of
candidate sequences. They are plain loops, so each line can be read as the recurrence above.
"""

from __future__ import annotations

import numpy as np
from numba import njit


@njit(cache=True)
def start_completion(seq, release, p):
    """Return (start, completion), each of shape (len(seq), m), indexed by position and stage."""
    n = seq.size
    m = p.shape[1]
    start = np.empty((n, m))
    completion = np.empty((n, m))
    stage_free = np.full(m, -np.inf)  # completion of the previous job at each stage
    for i in range(n):
        job = seq[i]
        ready = release[job]  # completion at the previous stage, or release at the first
        for k in range(m):
            s = max(ready, stage_free[k])
            ready = s + p[job, k]
            stage_free[k] = ready
            start[i, k] = s
            completion[i, k] = ready
    return start, completion


@njit(cache=True)
def _append(job, stage_free, release, due, weight, p):
    """Schedule one job after the current stage_free times, updating them in place.

    Returns the job's weighted tardiness and its waiting between stages.
    """
    m = p.shape[1]
    ready = release[job]
    waiting = 0.0
    for k in range(m):
        s = max(ready, stage_free[k])
        if k > 0:
            waiting += s - ready
        ready = s + p[job, k]
        stage_free[k] = ready
    tardiness = ready - due[job]
    return (weight[job] * tardiness if tardiness > 0.0 else 0.0), waiting


@njit(cache=True)
def evaluate(seq, release, due, weight, p):
    """Return (total weighted tardiness, total waiting between stages) of a sequence."""
    stage_free = np.full(p.shape[1], -np.inf)
    twt = 0.0
    waiting = 0.0
    for i in range(seq.size):
        wt, w = _append(seq[i], stage_free, release, due, weight, p)
        twt += wt
        waiting += w
    return twt, waiting


@njit(cache=True)
def best_insertion(seq, job, release, due, weight, p):
    """Find the position at which inserting `job` into `seq` gives the best objective.

    Positions are compared on total weighted tardiness, then on total waiting, and an exact tie
    goes to the earliest position. Returns (position, twt, waiting).

    The jobs before the insertion point are timed once and carried forward. A candidate stops
    early once its running totals can no longer beat the best position found, which is valid
    because both totals only grow as jobs are appended.
    """
    length = seq.size
    m = p.shape[1]
    prefix_free = np.full(m, -np.inf)
    prefix_twt = 0.0
    prefix_wait = 0.0
    work = np.empty(m)
    best_pos = 0
    best_twt = np.inf
    best_wait = np.inf
    for pos in range(length + 1):
        for k in range(m):
            work[k] = prefix_free[k]
        wt, w = _append(job, work, release, due, weight, p)
        twt = prefix_twt + wt
        waiting = prefix_wait + w
        pruned = twt > best_twt or (twt == best_twt and waiting >= best_wait)
        i = pos
        while not pruned and i < length:
            wt, w = _append(seq[i], work, release, due, weight, p)
            twt += wt
            waiting += w
            pruned = twt > best_twt or (twt == best_twt and waiting >= best_wait)
            i += 1
        if not pruned:
            best_pos = pos
            best_twt = twt
            best_wait = waiting
        if pos < length:
            wt, w = _append(seq[pos], prefix_free, release, due, weight, p)
            prefix_twt += wt
            prefix_wait += w
    return best_pos, best_twt, best_wait


def insert(seq: np.ndarray, pos: int, job: int) -> np.ndarray:
    """Return a copy of `seq` with `job` placed at `pos`."""
    return np.concatenate((seq[:pos], np.array([job], dtype=np.int64), seq[pos:]))
