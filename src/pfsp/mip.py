"""Benchmark: the problem as a mixed-integer program, solved with HiGHS.

This is a labeled benchmark for the comparison, not one of the two methods. The program assigns
jobs to sequence positions:

    minimize    sum_j w_j T_j
    subject to  sum_q x[j,q] = 1 for every job j;  sum_j x[j,q] = 1 for every position q
                E[q,k] = B[q,k] + sum_j p[j,k] x[j,q]           (no interruption)
                B[q,1] >= sum_j r_j x[j,q]                       (release)
                B[q,k] >= E[q,k-1]   for k >= 2                  (stage order)
                B[q,k] >= E[q-1,k]   for q >= 2                  (one job at a time, common order)
                T_j >= E[q,m] - d_j - U_j (1 - x[j,q])           (tardiness of the job at position q)
                x binary, T >= 0

with U_j = max(0, max_i r_i + sum_{i,k} p[i,k] - d_j), an upper bound on job j's tardiness in any
schedule without idle time beyond the latest release. The job order in a solution is read from
x and re-timed by the shared execution rule, and the independent checker confirms that decision.
"""

from __future__ import annotations

import time

import highspy
import numpy as np

from .data import Instance

DEFAULT_TIME_LIMIT = 600.0


def solve_mip(instance: Instance, time_limit: float = DEFAULT_TIME_LIMIT) -> tuple[np.ndarray | None, dict]:
    """Solve the positional program. Returns (job order or None, solver report)."""
    n, m = instance.n, instance.m
    r, d, w, p = instance.release, instance.due, instance.weight, instance.p
    horizon = float(r.max() + p.sum())
    bound = np.maximum(0.0, horizon - d)
    earliest = min(0.0, float(r.min()))

    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("time_limit", float(time_limit))
    h.setOptionValue("mip_rel_gap", 0.0)
    h.setOptionValue("threads", 1)
    h.setOptionValue("random_seed", 0)

    x = {(j, q): h.addBinary() for j in range(n) for q in range(n)}
    begin = {(q, k): h.addVariable(lb=earliest) for q in range(n) for k in range(m)}
    end = {(q, k): h.addVariable(lb=earliest) for q in range(n) for k in range(m)}
    tardy = [h.addVariable(lb=0.0) for _ in range(n)]

    for j in range(n):
        h.addConstr(h.qsum(x[j, q] for q in range(n)) == 1)
    for q in range(n):
        h.addConstr(h.qsum(x[j, q] for j in range(n)) == 1)
        h.addConstr(begin[q, 0] - h.qsum(float(r[j]) * x[j, q] for j in range(n)) >= 0)
        for k in range(m):
            h.addConstr(end[q, k] - begin[q, k] - h.qsum(float(p[j, k]) * x[j, q] for j in range(n)) == 0)
            if k > 0:
                h.addConstr(begin[q, k] - end[q, k - 1] >= 0)
            if q > 0:
                h.addConstr(begin[q, k] - end[q - 1, k] >= 0)
        for j in range(n):
            h.addConstr(tardy[j] - end[q, m - 1] - float(bound[j]) * x[j, q] >= -float(d[j]) - float(bound[j]))
    objective = h.qsum(float(w[j]) * tardy[j] for j in range(n))

    began = time.perf_counter()
    h.minimize(objective)  # sets the objective and solves
    seconds = time.perf_counter() - began
    status = h.modelStatusToString(h.getModelStatus())
    info = h.getInfo()
    report = {
        "status": status,
        "time_limit_seconds": time_limit,
        "seconds": seconds,
        "objective": None,
        "dual_bound": float(info.mip_dual_bound),
        "gap": None,
        "nodes": int(info.mip_node_count),
        "highs_version": h.version(),
    }
    if info.primal_solution_status == 0:  # no feasible solution found within the limit
        return None, report
    values = h.getSolution().col_value
    position = np.array([[values[x[j, q].index] for q in range(n)] for j in range(n)])
    order = np.argsort(position.argmax(axis=1), kind="stable").astype(np.int64)
    report["objective"] = float(info.objective_function_value)
    report["gap"] = float(info.mip_gap)
    return order, report
