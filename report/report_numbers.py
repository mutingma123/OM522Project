"""Print every number the report quotes, computed from the data and the results files.

Run from the repository root: pixi run python report/report_numbers.py
"""

import csv
import json
import statistics
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA, RESULTS = ROOT / "data", ROOT / "results"


def rows(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def pct_lower(base, new):
    return 100.0 * (base - new) / base


print("== Data")
for name in ["hand_checkable", "development_small", "development_medium", "development_large", "edge_case"]:
    jobs = rows(DATA / name / "jobs.csv")
    times = [float(r["processing_time"]) for r in rows(DATA / name / "processing_times.csv")]
    stages = rows(DATA / name / "stages.csv")
    release = [float(r["release_time"]) for r in jobs]
    due = [float(r["due_date"]) for r in jobs]
    weights = sorted({int(r["weight"]) for r in jobs})
    window = [d - r for d, r in zip(due, release)]
    print(f"{name}: jobs {len(jobs)}, stages {len(stages)}, p {min(times):g} to {max(times):g} "
          f"(mean {statistics.mean(times):.1f}), release {min(release):g} to {max(release):g}, "
          f"due minus release {min(window):g} to {max(window):g} (median {statistics.median(window):g}), weights {weights}")

print("== Deterministic comparison")
comp = rows(RESULTS / "comparison" / "comparison.csv")
by = {(r["instance"], r["method"]): r for r in comp}
for inst in ["hand_checkable", "development_small", "development_medium", "development_large"]:
    rule, ig, neh = by[inst, "rule"], by[inst, "ig"], by[inst, "neh"]
    rt, it, nt = (float(x["total_weighted_tardiness"]) for x in (rule, ig, neh))
    rw, iw, nw = (float(x["total_waiting"]) for x in (rule, ig, neh))
    print(f"{inst}: TWT rule {rt:g} ig {it:g} neh {nt:g} | ig lower by {pct_lower(rt, it):.1f}% | neh lower by {pct_lower(rt, nt):.1f}% "
          f"| ig vs neh lower by {pct_lower(nt, it) if nt else 0:.1f}% | waiting rule {rw:g} ig {iw:g} neh {nw:g} ig change {100*(iw-rw)/rw:+.1f}% "
          f"| on-time rule {float(rule['on_time_rate']):.3f} ig {float(ig['on_time_rate']):.3f} | makespan rule {rule['makespan']} ig {ig['makespan']} "
          f"| seconds ig {float(ig['computation_seconds']):.2f} | feasible {rule['feasible']} {ig['feasible']} {neh['feasible']}")
seeds = rows(RESULTS / "comparison" / "ig_seeds.csv")
for inst in ["hand_checkable", "development_small", "development_medium", "development_large"]:
    v = [float(r["total_weighted_tardiness"]) for r in seeds if r["instance"] == inst]
    print(f"seeds {inst}: {sorted(v)}")
print(json.loads((RESULTS / "comparison" / "settings.json").read_text())["computer"])

print("== Benchmark")
for r in rows(RESULTS / "benchmark" / "benchmark.csv"):
    print({k: r[k] for k in ("instance", "status", "checked_total_weighted_tardiness", "dual_bound", "seconds", "nodes",
                              "checked_total_waiting", "ig_total_weighted_tardiness", "ig_total_waiting")})

print("== Stress")
summary = json.loads((RESULTS / "stress" / "summary.json").read_text())
for m, v in summary["methods"].items():
    print(m, json.dumps(v))
rule, ig = summary["methods"]["rule"], summary["methods"]["ig"]
print(f"mean TWT lower by {pct_lower(rule['total_weighted_tardiness']['mean'], ig['total_weighted_tardiness']['mean']):.1f}%, "
      f"p90 lower by {pct_lower(rule['total_weighted_tardiness']['p90'], ig['total_weighted_tardiness']['p90']):.1f}%, "
      f"mean waiting lower by {pct_lower(rule['total_waiting']['mean'], ig['total_waiting']['mean']):.1f}%")
print(f"increase from plan: rule +{rule['total_weighted_tardiness']['mean'] - rule['deterministic_total_weighted_tardiness']:.1f}, "
      f"ig +{ig['total_weighted_tardiness']['mean'] - ig['deterministic_total_weighted_tardiness']:.1f}")
print("ig better in", summary["ig_better_tardiness_in_scenarios"], "of 30; seed", summary["manifest"]["seed"])
per = rows(RESULTS / "stress" / "per_scenario.csv")
for m in ("rule", "ig"):
    v = [float(r["total_weighted_tardiness"]) for r in per if r["method"] == m]
    print(m, "TWT range", min(v), max(v))
for e in summary["sweep"]:
    print(f"cv {e['cv']}: rule mean {e['rule']['mean']:.1f} p90 {e['rule']['p90']:.1f} | ig mean {e['ig']['mean']:.1f} p90 {e['ig']['p90']:.1f} "
          f"| ig lower by {pct_lower(e['rule']['mean'], e['ig']['mean']):.1f}% | better {e['ig_better_in_scenarios']}")

print("== Derived figures quoted in the text")
for name in ["development_small", "development_medium", "development_large"]:
    jobs = rows(DATA / name / "jobs.csv")
    times = rows(DATA / name / "processing_times.csv")
    release = [float(r["release_time"]) for r in jobs]
    per_job = {}
    for r in times:
        per_job[r["job_id"]] = per_job.get(r["job_id"], 0.0) + float(r["processing_time"])
    span = max(release) - min(release)
    print(f"{name}: release span {span:g} min, arrival rate {len(jobs) / span:.3f} jobs per min, "
          f"mean total processing per job {statistics.mean(per_job.values()):.1f} min")
print(f"plan to mean TWT ratio: rule {rule['total_weighted_tardiness']['mean'] / rule['deterministic_total_weighted_tardiness']:.2f}, "
      f"ig {ig['total_weighted_tardiness']['mean'] / ig['deterministic_total_weighted_tardiness']:.2f}")
print(f"absolute mean TWT reduction at cv 0.2 main test: {rule['total_weighted_tardiness']['mean'] - ig['total_weighted_tardiness']['mean']:.1f}")
for e in summary["sweep"]:
    print(f"cv {e['cv']}: absolute mean TWT reduction {e['rule']['mean'] - e['ig']['mean']:.1f}; "
          f"ig p90 above rule mean: {e['ig']['p90'] > e['rule']['mean']}")

print("== Slack budget and standard errors")
for name in ["development_small", "development_medium", "development_large"]:
    jobs = {r["job_id"]: r for r in rows(DATA / name / "jobs.csv")}
    total = {}
    for r in rows(DATA / name / "processing_times.csv"):
        total[r["job_id"]] = total.get(r["job_id"], 0.0) + float(r["processing_time"])
    budget = [float(jobs[j]["due_date"]) - float(jobs[j]["release_time"]) - total[j] for j in jobs]
    print(f"{name}: median of (due - release - total processing) {statistics.median(budget):g} min, "
          f"jobs with a negative budget {sum(b < 0 for b in budget)}")
print("main test reduction", summary["tardiness_reduction"])
for e in summary["sweep"]:
    print(f"cv {e['cv']}: reduction {e['reduction']['mean']:.1f} (se {e['reduction']['standard_error']:.1f})")

print("== Figures added after the fresh-context review")
for inst in ["development_small", "development_medium", "development_large"]:
    rt, it, nt = (float(by[inst, m]["total_weighted_tardiness"]) for m in ("rule", "ig", "neh"))
    print(f"{inst}: ig leaves {100 * it / rt:.1f}% of the rule's TWT; search lowers NEH by {nt - it:g} weighted minutes")
s5, s8 = (next(e for e in summary["sweep"] if e["cv"] == c)["reduction"] for c in (0.5, 0.8))
print(f"drop 0.5 to 0.8: {s5['mean'] - s8['mean']:.1f}, combined standard error {(s5['standard_error']**2 + s8['standard_error']**2) ** 0.5:.1f}")
wins = summary["ig_better_tardiness_in_scenarios"] + sum(e["ig_better_in_scenarios"] for e in summary["sweep"])
print(f"iterated greedy better in {wins} of {30 * (1 + len(summary['sweep']))} paired scenarios")
print("main test reduction p10 and minimum", round(summary["tardiness_reduction"]["p10"], 1), round(summary["tardiness_reduction"]["minimum"], 1))
for e in summary["sweep"]:
    print(f"cv {e['cv']}: reduction p10 {e['reduction']['p10']:.1f}, minimum {e['reduction']['minimum']:.1f}")
print("processing times on the 45-job instance:", len(rows(DATA / "development_medium" / "processing_times.csv")))
