"""Deterministic comparison on the hand-checkable case and the three development sizes.

Every method receives the same input files. Each decision is exported, then confirmed and measured
by the independent checker, so the reported feasibility and measures come from pfsp_check rather
than from the method that produced the decision. Computation time covers the method alone (not
loading or writing), measured after the compiled kernels have been warmed up once.
"""

from __future__ import annotations

import csv
import itertools
import json
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from pfsp_check import check_decision

from .data import load_instance
from .figures import COLORS, INK_SECONDARY, LABELS, new_figure, save
from .ig import DEFAULT_ITERATIONS, DEFAULT_SEED, DEFAULT_TIME_CAP, iterated_greedy, neh_ewdd
from .output import build_decision
from .rule import edd_sequence
from .timing import evaluate

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
INSTANCES = ["hand_checkable", "development_small", "development_medium", "development_large"]
METHODS = ["rule", "ig", "neh"]
EXTRA_SEEDS = [1, 2, 3, 4, 5]


def computer() -> dict:
    """Describe the computer, for the statement every comparison must carry."""
    cpu = platform.processor() or platform.machine()
    try:
        if sys.platform.startswith("linux"):
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if line.startswith("model name"):
                    cpu = line.split(":", 1)[1].strip()
                    break
        elif sys.platform == "darwin":
            cpu = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True
            ).stdout.strip() or cpu
    except OSError:
        pass
    import numba

    return {
        "cpu": cpu,
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "numpy": np.__version__,
        "numba": numba.__version__,
    }


def solve_with(method: str, instance, seed: int = DEFAULT_SEED):
    if method == "rule":
        return edd_sequence(instance), {}
    if method == "ig":
        return iterated_greedy(instance, seed=seed)
    return neh_ewdd(instance)


def warm_up() -> None:
    """Compile the kernels once so the first timed run does not include compilation."""
    instance = load_instance(DATA / "hand_checkable")
    iterated_greedy(instance, iterations=2)


def checked_row(instance_dir: Path, decision_path: Path) -> dict:
    report = check_decision(instance_dir, decision_path)
    measures = report["measures"]
    return {
        "feasible": report["feasible"],
        "violations": len(report["violations"]),
        "total_weighted_tardiness": measures["total_weighted_tardiness"],
        "total_waiting": measures["downstream_waiting_time"],
        "makespan": measures["makespan"],
        "on_time_rate": measures["on_time_rate"],
    }


def brute_force_optimum(instance) -> tuple[np.ndarray, float]:
    """Enumerate every sequence (only for the six-job case) as a labeled benchmark."""
    args = (instance.release, instance.due, instance.weight, instance.p)
    began = time.perf_counter()
    best = min(itertools.permutations(range(instance.n)), key=lambda s: evaluate(np.array(s, dtype=np.int64), *args))
    return np.array(best, dtype=np.int64), time.perf_counter() - began


def run(out_dir: Path) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    warm_up()
    rows, seed_rows = [], []
    for name in INSTANCES:
        instance = load_instance(DATA / name)
        runs = [(method, *_timed(solve_with, method, instance)) for method in METHODS]
        if name == "hand_checkable":
            seq, seconds = brute_force_optimum(instance)
            runs.append(("optimum", seq, {}, seconds))
        for method, seq, details, seconds in runs:
            path = out_dir / "decisions" / name / method / "decision.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(build_decision(instance, seq), indent=2) + "\n")
            row = {"instance": name, "jobs": instance.n, "stages": instance.m, "method": method}
            row.update(checked_row(DATA / name, path))
            row["computation_seconds"] = round(seconds, 4)
            row["iterations_run"] = details.get("iterations_run", "")
            row["stop_reason"] = details.get("stop_reason", "")
            rows.append(row)
            print(f"{name:20s} {method:8s} TWT {row['total_weighted_tardiness']:>10g}  "
                  f"waiting {row['total_waiting']:>8g}  {seconds:8.3f} s  feasible={row['feasible']}", flush=True)
        for seed in EXTRA_SEEDS:
            seq, details, seconds = _timed(solve_with, "ig", instance, seed)
            twt, waiting = evaluate(seq, instance.release, instance.due, instance.weight, instance.p)
            seed_rows.append({"instance": name, "jobs": instance.n, "seed": seed,
                              "total_weighted_tardiness": twt, "total_waiting": waiting,
                              "computation_seconds": round(seconds, 4)})

    _write_csv(out_dir / "comparison.csv", rows)
    _write_csv(out_dir / "ig_seeds.csv", seed_rows)
    settings = {
        "ig_iterations": DEFAULT_ITERATIONS,
        "ig_seed": DEFAULT_SEED,
        "ig_time_cap_seconds": DEFAULT_TIME_CAP,
        "extra_seeds": EXTRA_SEEDS,
        "computer": computer(),
    }
    (out_dir / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
    _write_markdown(out_dir / "comparison.md", rows, seed_rows, settings)
    _plot(out_dir / "comparison.png", rows)
    return rows


def write_additional_measures(results: Path) -> list[dict]:
    """Makespan, on-time fraction, and idle time by stage of every saved decision, from the checker.
    A stage's idle time is the makespan minus its total processing time, as in the worked example."""
    sources = [(name, method, results / "comparison" / "decisions" / name / method / "decision.json")
               for name in INSTANCES for method in (*METHODS, "optimum")]
    sources += [(name, "highs", results / "benchmark" / "decisions" / name / "decision.json") for name in INSTANCES]
    rows = []
    for name, method, path in sources:
        if not path.is_file():
            continue
        found = check_decision(DATA / name, path)["measures"]
        row = {"instance": name, "method": method, "makespan": found["makespan"], "on_time_rate": found["on_time_rate"]}
        for k in range(1, 9):
            row[f"idle_S{k}"] = found["idle_time_by_stage"].get(f"S{k}", "")
        rows.append(row)
    _write_csv(results / "comparison" / "additional_measures.csv", rows)
    return rows


def _timed(function, *args):
    began = time.perf_counter()
    seq, details = function(*args)
    return seq, details, time.perf_counter() - began


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _fmt(value) -> str:
    if isinstance(value, float):
        return f"{value:,.0f}" if value.is_integer() else f"{value:,.3f}"
    return str(value)


def _cap_note(rows) -> str:
    capped = [row["instance"] for row in rows if "time cap" in str(row["stop_reason"])]
    return f"which stopped the run on {', '.join(capped)}." if capped else "which no run reached."


def _write_markdown(path: Path, rows, seed_rows, settings) -> None:
    names = {"rule": "EDD rule", "ig": "Iterated greedy", "neh": "NEH_EWDD only",
             "optimum": "Optimum (enumeration, benchmark)"}
    lines = [
        "# Deterministic comparison",
        "",
        f"Computer: {settings['computer']['cpu']}, {settings['computer']['os']}, Python "
        f"{settings['computer']['python']}. Iterated greedy runs {settings['ig_iterations']} iterations "
        f"with seed {settings['ig_seed']} and a {settings['ig_time_cap_seconds']:.0f} s safety cap, "
        f"{_cap_note(rows)} The rule and NEH_EWDD have no time limit and no randomness. "
        "Feasibility and every measure are recomputed by the independent checker from the exported "
        "decision. Times are in minutes; weighted tardiness is in weighted minutes.",
        "",
        "| Instance | Jobs | Method | Feasible | Total weighted tardiness | Total waiting | Makespan | On-time fraction | Seconds |",
        "| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['instance']} | {row['jobs']} | {names[row['method']]} | "
            f"{'yes' if row['feasible'] else 'NO'} | {_fmt(row['total_weighted_tardiness'])} | "
            f"{_fmt(row['total_waiting'])} | {_fmt(row['makespan'])} | {row['on_time_rate']:.3f} | "
            f"{row['computation_seconds']:.3f} |"
        )
    lines += ["", "## Iterated greedy under other seeds", "",
              f"The same settings with seeds {', '.join(map(str, EXTRA_SEEDS))} show how much the "
              "result depends on the seed.", "",
              "| Instance | Jobs | Default seed | Lowest | Median | Highest | EDD rule |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for name in INSTANCES:
        values = [r["total_weighted_tardiness"] for r in seed_rows if r["instance"] == name]
        default = next(r for r in rows if r["instance"] == name and r["method"] == "ig")
        rule = next(r for r in rows if r["instance"] == name and r["method"] == "rule")
        lines.append(
            f"| {name} | {default['jobs']} | {_fmt(default['total_weighted_tardiness'])} | "
            f"{_fmt(min(values))} | {_fmt(statistics.median(values))} | {_fmt(max(values))} | "
            f"{_fmt(rule['total_weighted_tardiness'])} |"
        )
    path.write_text("\n".join(lines) + "\n")


def _plot(path: Path, rows) -> None:
    """Each method's measures as a percentage of the rule's on the same instance, by size."""
    fig, axes = new_figure(2)
    jobs = sorted({row["jobs"] for row in rows})
    x = np.arange(len(jobs))
    panels = [("total_weighted_tardiness", "Weighted tardiness, % of the rule"),
              ("total_waiting", "Waiting between stages, % of the rule")]
    for ax, (key, title) in zip(axes, panels):
        rule = {row["jobs"]: row[key] for row in rows if row["method"] == "rule"}
        ax.axhline(100, color=COLORS["rule"], linewidth=2)
        ax.annotate("EDD rule = 100", (x[-1], 100), xytext=(0, 5), textcoords="offset points",
                    ha="right", color=INK_SECONDARY)
        for method in ("neh", "ig"):  # the researched method drawn last, on top where they meet
            values = [100 * row[key] / rule[row["jobs"]] for j in jobs for row in rows
                      if row["method"] == method and row["jobs"] == j]
            ax.plot(x, values, color=COLORS[method], linewidth=2, marker="o", markersize=7,
                    markeredgecolor="#fcfcfb", markeredgewidth=2, label=LABELS[method])
            ax.annotate(f"{values[-1]:.0f}", (x[-1], values[-1]), xytext=(8, 0),
                        textcoords="offset points", va="center", color=INK_SECONDARY)
        ax.set_xticks(x, [f"{j} jobs" for j in jobs])
        ax.set_title(title)
        ax.set_ylim(bottom=0)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles[::-1], labels[::-1], loc="lower center", ncol=2)
    fig.subplots_adjust(bottom=0.2)
    save(fig, path, rect=(0, 0.08, 1, 1))
