"""Optimality benchmark: solve the mixed-integer program on the two smallest instances and compare
its proven optimum with both methods' results from the deterministic comparison."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from pfsp_check import check_decision

from .compare import DATA, computer
from .data import load_instance
from .ig import iterated_greedy
from .mip import DEFAULT_TIME_LIMIT, solve_mip
from .output import build_decision
from .rule import edd_sequence
from .timing import evaluate

INSTANCES = ["hand_checkable", "development_small"]


def run(out_dir: Path) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for name in INSTANCES:
        instance = load_instance(DATA / name)
        args = (instance.release, instance.due, instance.weight, instance.p)
        order, report = solve_mip(instance, DEFAULT_TIME_LIMIT)
        row = {"instance": name, "jobs": instance.n, **{k: report[k] for k in
               ("status", "objective", "dual_bound", "gap", "seconds", "nodes", "time_limit_seconds")}}
        if order is not None:
            path = out_dir / "decisions" / name / "decision.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(build_decision(instance, order), indent=2) + "\n")
            checked = check_decision(DATA / name, path)
            row["feasible"] = checked["feasible"]
            row["checked_total_weighted_tardiness"] = checked["measures"]["total_weighted_tardiness"]
            row["checked_total_waiting"] = checked["measures"]["downstream_waiting_time"]
        row["rule_total_weighted_tardiness"] = evaluate(edd_sequence(instance), *args)[0]
        ig_twt, ig_waiting = evaluate(iterated_greedy(instance)[0], *args)
        row["ig_total_weighted_tardiness"] = ig_twt
        row["ig_total_waiting"] = ig_waiting
        rows.append(row)
        print(f"{name:20s} {report['status']:10s} optimum {row.get('checked_total_weighted_tardiness')} "
              f"bound {report['dual_bound']:.3f}  {report['seconds']:.1f} s  iterated greedy {ig_twt:g}", flush=True)

    with (out_dir / "benchmark.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    settings = {"solver": f"HiGHS {solve_version()}", "time_limit_seconds": DEFAULT_TIME_LIMIT,
                "threads": 1, "mip_rel_gap": 0.0, "computer": computer()}
    (out_dir / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
    _write_markdown(out_dir / "benchmark.md", rows, settings)
    return rows


def solve_version() -> str:
    import highspy

    return highspy.Highs().version()


def _write_markdown(path: Path, rows, settings) -> None:
    lines = [
        "# Optimality benchmark",
        "",
        f"The positional mixed-integer program (see src/pfsp/mip.py) solved with {settings['solver']}, one thread, "
        f"a relative gap tolerance of 0, and a {settings['time_limit_seconds']:.0f} s limit, on "
        f"{settings['computer']['cpu']}. The solver's job order is re-timed by the execution rule and the "
        "independent checker confirms it and supplies the measures. The other columns repeat the two methods' "
        "results with their default settings.",
        "",
        "| Instance | Jobs | Solver status | Optimal TWT | Dual bound | Seconds | Nodes | Waiting of the solver's order | EDD rule TWT | Iterated greedy TWT | Iterated greedy waiting |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['instance']} | {row['jobs']} | {row['status']} | {row['checked_total_weighted_tardiness']:g} | "
            f"{row['dual_bound']:.3f} | {row['seconds']:.1f} | {row['nodes']} | {row['checked_total_waiting']:g} | "
            f"{row['rule_total_weighted_tardiness']:g} | {row['ig_total_weighted_tardiness']:g} | "
            f"{row['ig_total_waiting']:g} |"
        )
    path.write_text("\n".join(lines) + "\n")
