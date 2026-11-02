"""Stress test of the two fixed plans when processing times turn out different from the data.

Uncertain input (from the brief): processing times. Each scenario multiplies every processing
time by an independent lognormal factor with mean 1 and coefficient of variation 0.2. The 30
scenarios are generated from a fixed seed and saved to CSV files before either method runs, and
both plans are then executed on the files read back, so they face identical realizations.

Execution rule (from the brief): keep the planned sequence and start every operation as early as
the realized processing times allow. Each realized schedule is confirmed by the independent
checker against that scenario's processing times.

A sweep over further coefficients of variation (0.1 to 0.8, 30 scenarios each from documented
seeds) looks for the variability at which the recommendation would change. Only the main test's
scenarios are saved, because the sweep is an extension beyond the required test.
"""

from __future__ import annotations

import csv
import json
import math
import tempfile
import time
from pathlib import Path

import numpy as np

from pfsp_check import check_decision

from .compare import DATA, computer
from .data import load_instance
from .figures import COLORS, LABELS, new_figure, save
from .ig import DEFAULT_ITERATIONS, DEFAULT_SEED, iterated_greedy
from .output import build_decision
from .rule import edd_sequence
from .timing import start_completion

INSTANCE = "development_medium"
SEED = 20261103
SCENARIOS = 30
CV = 0.2
SWEEP_CVS = [0.1, 0.2, 0.3, 0.5, 0.8]
SWEEP_SEED = 6522
METHODS = ["rule", "ig"]


def lognormal_factors(rng: np.random.Generator, shape, cv: float) -> np.ndarray:
    """Independent lognormal factors with mean 1 and coefficient of variation cv."""
    sigma = math.sqrt(math.log(1.0 + cv * cv))
    return rng.lognormal(mean=-sigma * sigma / 2.0, sigma=sigma, size=shape)


def generate(instance, rng, count: int, cv: float) -> list[np.ndarray]:
    return [instance.p * lognormal_factors(rng, instance.p.shape, cv) for _ in range(count)]


def save_scenarios(instance, scenarios, folder: Path) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for s, p in enumerate(scenarios, start=1):
        path = folder / f"scenario_{s:02d}.csv"
        with path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["job_id", "stage_id", "processing_time"])
            for j, job in enumerate(instance.job_ids):
                for k, stage in enumerate(instance.stage_ids):
                    writer.writerow([job, stage, repr(float(p[j, k]))])
        paths.append(path)
    return paths


def read_scenario(instance, path: Path) -> np.ndarray:
    """Read a saved scenario back into a processing-time matrix, matching identifiers by value."""
    jobs = {job: j for j, job in enumerate(instance.job_ids)}
    stages = {stage: k for k, stage in enumerate(instance.stage_ids)}
    p = np.full(instance.p.shape, np.nan)
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            p[jobs[row["job_id"]], stages[row["stage_id"]]] = float(row["processing_time"])
    if np.isnan(p).any():
        raise ValueError(f"{path.name} lacks a processing time for some job-stage pair")
    return p


def execute(instance, seq: np.ndarray, p: np.ndarray) -> dict:
    """Run a fixed sequence on realized times by the execution rule and measure the result."""
    start, completion = start_completion(seq, instance.release, p)
    tardiness = np.maximum(completion[:, -1] - instance.due[seq], 0.0)
    return {
        "start": start,
        "completion": completion,
        "total_weighted_tardiness": float(instance.weight[seq] @ tardiness),
        "total_waiting": float((start[:, 1:] - completion[:, :-1]).sum()),
        "makespan": float(completion.max()),
        "late_jobs": int((tardiness > 0).sum()),
    }


def realized_decision(instance, seq, result) -> dict:
    return {
        "sequence": [instance.job_ids[j] for j in seq],
        "schedule": [
            {"job_id": instance.job_ids[job], "stage_id": stage,
             "start": float(result["start"][i, k]), "completion": float(result["completion"][i, k])}
            for i, job in enumerate(seq) for k, stage in enumerate(instance.stage_ids)
        ],
    }


def summarize(values: list[float]) -> dict:
    return {"mean": float(np.mean(values)), "p90": float(np.percentile(values, 90))}


def paired_reduction(rule: list[float], ig: list[float]) -> dict:
    """Mean of the per-scenario reduction (rule minus iterated greedy) and its standard error."""
    diff = np.asarray(rule) - np.asarray(ig)
    return {
        "mean": float(diff.mean()),
        "standard_error": float(diff.std(ddof=1) / np.sqrt(diff.size)),
        "p10": float(np.percentile(diff, 10)),
        "minimum": float(diff.min()),
    }


def run(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    instance_dir = DATA / INSTANCE
    instance = load_instance(instance_dir)

    # 1. Scenarios first, saved before any method runs.
    rng = np.random.default_rng(SEED)
    paths = save_scenarios(instance, generate(instance, rng, SCENARIOS, CV), out_dir / "scenarios")
    manifest = {
        "instance": INSTANCE,
        "uncertain_input": "processing_times.csv, processing_time",
        "model": "each processing time times an independent lognormal factor, mean 1",
        "coefficient_of_variation": CV,
        "scenarios": SCENARIOS,
        "seed": SEED,
        "generator": "numpy.random.default_rng(seed).lognormal(mean=-s^2/2, sigma=s), s^2 = ln(1 + cv^2), "
                     "drawn job by job and stage by stage in jobs.csv and stage order, scenario after scenario",
        "files": [path.name for path in paths],
    }
    (out_dir / "scenarios" / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # 2. The deterministic plans, built from the original data with default settings.
    plans = {"rule": edd_sequence(instance)}
    began = time.perf_counter()
    plans["ig"], details = iterated_greedy(instance)
    ig_seconds = time.perf_counter() - began
    for method, seq in plans.items():
        (out_dir / f"plan_{method}.json").write_text(json.dumps(build_decision(instance, seq), indent=2) + "\n")

    # 3. Execute both fixed plans on every saved scenario, and check every realized schedule.
    rows = []
    with tempfile.TemporaryDirectory() as scratch:
        for s, path in enumerate(paths, start=1):
            p = read_scenario(instance, path)
            for method, seq in plans.items():
                result = execute(instance, seq, p)
                decision_path = Path(scratch) / f"{method}_{s:02d}.json"
                decision_path.write_text(json.dumps(realized_decision(instance, seq, result)))
                report = check_decision(instance_dir, decision_path, processing_times=path)
                rows.append({
                    "scenario": s, "method": method,
                    "total_weighted_tardiness": report["measures"]["total_weighted_tardiness"],
                    "total_waiting": report["measures"]["downstream_waiting_time"],
                    "makespan": report["measures"]["makespan"],
                    "late_jobs": result["late_jobs"],
                    "hard_constraint_violations": len(report["violations"]),
                })
    _write_csv(out_dir / "per_scenario.csv", rows)

    deterministic = {method: execute(instance, seq, instance.p) for method, seq in plans.items()}
    summary = {
        "manifest": manifest,
        "ig_settings": {"iterations": DEFAULT_ITERATIONS, "seed": DEFAULT_SEED,
                        "iterations_run": details["iterations_run"], "seconds": ig_seconds},
        "computer": computer(),
        "methods": {},
    }
    for method in METHODS:
        mine = [r for r in rows if r["method"] == method]
        summary["methods"][method] = {
            "deterministic_total_weighted_tardiness": deterministic[method]["total_weighted_tardiness"],
            "deterministic_total_waiting": deterministic[method]["total_waiting"],
            "total_weighted_tardiness": summarize([r["total_weighted_tardiness"] for r in mine]),
            "total_waiting": summarize([r["total_waiting"] for r in mine]),
            "scenarios_breaking_a_hard_constraint": sum(r["hard_constraint_violations"] > 0 for r in mine),
            "planned_late_jobs": deterministic[method]["late_jobs"],
            "mean_late_jobs": float(np.mean([r["late_jobs"] for r in mine])),
            **slack_profile(instance, plans[method], deterministic[method]),
        }
    pairs = [(a["total_weighted_tardiness"], b["total_weighted_tardiness"])
             for a, b in zip(rows[0::2], rows[1::2])]
    summary["ig_better_tardiness_in_scenarios"] = sum(ig < rule for rule, ig in pairs)
    summary["tardiness_reduction"] = paired_reduction([p[0] for p in pairs], [p[1] for p in pairs])
    summary["sweep"] = sweep(instance, plans)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    _write_markdown(out_dir / "stress.md", summary)
    _plot_scenarios(out_dir / "stress_per_scenario.png", rows)
    _plot_sweep(out_dir / "stress_cv_sweep.png", summary["sweep"])
    return summary


def slack_profile(instance, seq, result) -> dict:
    """Planned slack of the jobs a plan finishes on time. A job is at risk when its slack is below
    one standard deviation of its own total processing time under the stress model, i.e.
    CV * sqrt(sum_k p_jk^2) for independent factors with coefficient of variation CV."""
    slack = instance.due[seq] - result["completion"][:, -1]
    own_sd = CV * np.sqrt((instance.p[seq] ** 2).sum(axis=1))
    on_time = slack >= 0
    return {
        "planned_on_time_jobs": int(on_time.sum()),
        "planned_median_slack_of_on_time_jobs": float(np.median(slack[on_time])) if on_time.any() else None,
        "planned_on_time_jobs_with_slack_below_own_sd": int((on_time & (slack < own_sd)).sum()),
    }


def sweep(instance, plans) -> list[dict]:
    """Repeat the execution at several coefficients of variation, 30 scenarios each."""
    results = []
    for index, cv in enumerate(SWEEP_CVS):
        rng = np.random.default_rng(SWEEP_SEED + index)
        scenarios = generate(instance, rng, SCENARIOS, cv)
        entry = {"cv": cv, "seed": SWEEP_SEED + index}
        values = {}
        for method, seq in plans.items():
            values[method] = [execute(instance, seq, p)["total_weighted_tardiness"] for p in scenarios]
            entry[method] = summarize(values[method])
        entry["ig_better_in_scenarios"] = sum(i < r for r, i in zip(values["rule"], values["ig"]))
        entry["reduction"] = paired_reduction(values["rule"], values["ig"])
        results.append(entry)
    return results


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(path: Path, summary: dict) -> None:
    m = summary["methods"]
    lines = [
        "# Stress test of the fixed plans",
        "",
        f"Instance {INSTANCE}. Each processing time is multiplied by an independent lognormal factor "
        f"with mean 1 and coefficient of variation {CV}. {SCENARIOS} scenarios come from seed {SEED} and "
        "are saved in scenarios/ before either method runs. Each plan keeps its sequence and starts every "
        "operation as early as the realized times allow. The independent checker confirms every realized "
        "schedule against its scenario. The 90th percentile uses linear interpolation.",
        "",
        "| Method | Planned TWT | Mean TWT | 90th percentile TWT | Planned waiting | Mean waiting | 90th percentile waiting | Scenarios breaking a hard constraint |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    names = {"rule": "EDD rule", "ig": "Iterated greedy"}
    for method in METHODS:
        v = m[method]
        lines.append(
            f"| {names[method]} | {v['deterministic_total_weighted_tardiness']:,.1f} | "
            f"{v['total_weighted_tardiness']['mean']:,.1f} | {v['total_weighted_tardiness']['p90']:,.1f} | "
            f"{v['deterministic_total_waiting']:,.1f} | {v['total_waiting']['mean']:,.1f} | "
            f"{v['total_waiting']['p90']:,.1f} | {v['scenarios_breaking_a_hard_constraint']} |"
        )
    lines += [
        "",
        "| Method | Late jobs in the plan | Mean late jobs across scenarios | On-time jobs in the plan | Median slack of on-time jobs | On-time jobs with slack below one standard deviation of their own processing |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for method in METHODS:
        v = m[method]
        lines.append(
            f"| {names[method]} | {v['planned_late_jobs']} | {v['mean_late_jobs']:.1f} | {v['planned_on_time_jobs']} | "
            f"{v['planned_median_slack_of_on_time_jobs']:.1f} | {v['planned_on_time_jobs_with_slack_below_own_sd']} |"
        )
    lines += [
        "",
        f"Iterated greedy has the lower weighted tardiness in {summary['ig_better_tardiness_in_scenarios']} "
        f"of {SCENARIOS} scenarios; the mean per-scenario reduction is {summary['tardiness_reduction']['mean']:,.1f} weighted minutes "
        f"with a standard error of {summary['tardiness_reduction']['standard_error']:,.1f}; its 10th percentile is "
        f"{summary['tardiness_reduction']['p10']:,.1f} and its smallest value {summary['tardiness_reduction']['minimum']:,.1f}.",
        "",
        "## Sweep over variability",
        "",
        "| Coefficient of variation | Seed | Rule mean TWT | Rule 90th percentile | Iterated greedy mean TWT | Iterated greedy 90th percentile | Mean reduction (standard error) | 10th percentile of the reduction | Smallest reduction | Scenarios where iterated greedy is better |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for e in summary["sweep"]:
        lines.append(
            f"| {e['cv']} | {e['seed']} | {e['rule']['mean']:,.1f} | {e['rule']['p90']:,.1f} | "
            f"{e['ig']['mean']:,.1f} | {e['ig']['p90']:,.1f} | {e['reduction']['mean']:,.1f} ({e['reduction']['standard_error']:,.1f}) | "
            f"{e['reduction']['p10']:,.1f} | {e['reduction']['minimum']:,.1f} | "
            f"{e['ig_better_in_scenarios']} of {SCENARIOS} |"
        )
    path.write_text("\n".join(lines) + "\n")


def _plot_scenarios(path: Path, rows) -> None:
    fig, axes = new_figure(2, width=11)
    panels = [("total_weighted_tardiness", "Total weighted tardiness (weighted minutes)"),
              ("total_waiting", "Total waiting between stages (minutes)")]
    for ax, (key, title) in zip(axes, panels):
        for method in METHODS:
            mine = [r for r in rows if r["method"] == method]
            ax.scatter([r["scenario"] for r in mine], [r[key] for r in mine], s=40,
                       color=COLORS[method], edgecolor="#fcfcfb", linewidth=1.5, label=LABELS[method], zorder=3)
        ax.set_title(title)
        ax.set_xlabel("Scenario")
        ax.set_xticks([1, 5, 10, 15, 20, 25, 30])
        ax.set_ylim(bottom=0)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2)
    fig.suptitle(f"Fixed plans on {SCENARIOS} processing-time scenarios ({INSTANCE}, CV {CV})", fontweight="bold")
    save(fig, path, rect=(0, 0.08, 1, 1))


def _plot_sweep(path: Path, sweep_rows) -> None:
    fig, axes = new_figure(1, width=6.5)
    ax = axes[0]
    cvs = [e["cv"] for e in sweep_rows]
    for method in METHODS:
        means = [e[method]["mean"] for e in sweep_rows]
        ax.plot(cvs, means, color=COLORS[method], linewidth=2, marker="o", markersize=7,
                markeredgecolor="#fcfcfb", markeredgewidth=2, label=LABELS[method])
    ax.set_title("Mean total weighted tardiness as variability grows")
    ax.set_xlabel("Coefficient of variation of processing times")
    ax.set_ylabel("Weighted minutes")
    ax.set_xticks(cvs)
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper left")
    save(fig, path)
