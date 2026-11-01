"""Check an exported decision against the input files, recomputing everything from those two sources.

Usage: python -m pfsp_check <input_dir> <decision.json> [--processing-times FILE] [--expect FILE]

The checker reads only the instance CSVs and decision.json. It uses the standard library alone and
shares no code with the methods, so a mistake in the solver's timing or measures cannot be repeated
here. It confirms the four required constraints of the brief, reports every job and stage that
violates one, and recomputes each measure from the reported starts and completions rather than
trusting totals written by a method. Every comparison of times allows the 1e-8 tolerance that the
instructor's checker allows.

Exit status: 0 when the decision is feasible (and matches --expect, if given), 1 when it is not,
and 2 when the input files or the decision file cannot be read.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from pathlib import Path

TOL = 1e-8


class Unreadable(Exception):
    pass


def _rows(path: Path, columns: list[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise Unreadable(f"{path.name}: file is missing")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        header = [name.strip() for name in (reader.fieldnames or [])]
        for column in columns:
            if column not in header:
                raise Unreadable(f"{path.name}, column {column}: column is missing")
        reader.fieldnames = header
        return [{key: (value or "").strip() for key, value in row.items() if key} for row in reader]


def _float(text: str, where: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise Unreadable(f"{where}: '{text}' is not a number") from None
    if not math.isfinite(value):
        raise Unreadable(f"{where}: '{text}' is not a finite number")
    return value


def read_inputs(input_dir: Path, processing_times: Path | None = None):
    """Return (jobs, stages, p): jobs maps job_id to (release, due, weight), stages is the stage
    order, and p maps (job_id, stage_id) to a processing time."""
    jobs = {}
    for row in _rows(input_dir / "jobs.csv", ["job_id", "release_time", "due_date", "weight"]):
        where = f"jobs.csv, job {row['job_id']}"
        jobs[row["job_id"]] = (
            _float(row["release_time"], f"{where}, release_time"),
            _float(row["due_date"], f"{where}, due_date"),
            _float(row["weight"], f"{where}, weight"),
        )
    stage_rows = _rows(input_dir / "stages.csv", ["stage_id", "sequence"])
    stages = [row["stage_id"] for row in sorted(stage_rows, key=lambda r: _float(r["sequence"], "stages.csv, sequence"))]
    times_path = processing_times or input_dir / "processing_times.csv"
    p = {}
    for row in _rows(times_path, ["job_id", "stage_id", "processing_time"]):
        where = f"{times_path.name}, job {row['job_id']} at {row['stage_id']}"
        p[(row["job_id"], row["stage_id"])] = _float(row["processing_time"], f"{where}, processing_time")
    return jobs, stages, p


def check_decision(input_dir, decision_path, processing_times=None) -> dict:
    """Check one decision. Returns a report with `feasible`, `violations`, `measures`, and `notes`."""
    input_dir, decision_path = Path(input_dir), Path(decision_path)
    jobs, stages, p = read_inputs(input_dir, Path(processing_times) if processing_times else None)
    try:
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise Unreadable(f"{decision_path}: cannot be read as JSON ({error})") from None
    if not isinstance(decision, dict):
        raise Unreadable(f"{decision_path}: top level is not an object")

    violations: list[str] = []
    notes: list[str] = []

    # The sequence lists every job exactly once.
    sequence = decision.get("sequence")
    if not isinstance(sequence, list) or not all(isinstance(job, str) for job in sequence):
        violations.append("sequence: missing or not a list of job identifiers")
        sequence = []
    seen = set()
    for job in sequence:
        if job not in jobs:
            violations.append(f"sequence: {job} does not appear in jobs.csv")
        elif job in seen:
            violations.append(f"sequence: {job} appears more than once")
        seen.add(job)
    for job in jobs:
        if job not in seen:
            violations.append(f"sequence: {job} is missing")

    # Constraint 1, first part: one schedule entry per job-stage pair, with valid identifiers.
    entries = decision.get("schedule")
    if not isinstance(entries, list):
        violations.append("schedule: missing or not a list")
        entries = []
    times: dict[tuple[str, str], tuple[float, float]] = {}
    for position, entry in enumerate(entries):
        label = f"schedule entry {position}"
        if not isinstance(entry, dict):
            violations.append(f"{label}: not an object")
            continue
        job, stage = entry.get("job_id"), entry.get("stage_id")
        start, completion = entry.get("start"), entry.get("completion")
        if job not in jobs:
            violations.append(f"{label}: job_id {job!r} does not appear in jobs.csv")
            continue
        if stage not in stages:
            violations.append(f"{label}: stage_id {stage!r} does not appear in stages.csv")
            continue
        numeric = all(
            isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
            for v in (start, completion)
        )
        if not numeric:
            violations.append(f"{job} at {stage}: start and completion must be finite numbers")
            continue
        if (job, stage) in times:
            violations.append(f"{job} at {stage}: scheduled more than once")
            continue
        times[(job, stage)] = (float(start), float(completion))
    for job in jobs:
        for stage in stages:
            if (job, stage) not in times:
                violations.append(f"{job} at {stage}: not scheduled")

    # Constraint 1, second part: no interruption, so each duration equals the processing time.
    for (job, stage), (start, completion) in times.items():
        expected = p.get((job, stage))
        if expected is None:
            violations.append(f"{job} at {stage}: no processing time in the input")
        elif abs((completion - start) - expected) > TOL:
            violations.append(
                f"{job} at {stage}: runs {completion - start!r} from {start!r} to {completion!r}, "
                f"but its processing time is {expected!r}"
            )

    # Constraint 3: release at the first stage, then stage order.
    for job, (release, _, _) in jobs.items():
        previous = None
        for stage in stages:
            if (job, stage) not in times:
                previous = None
                continue
            start, completion = times[(job, stage)]
            if previous is None and stage == stages[0] and start < release - TOL:
                violations.append(f"{job} at {stage}: starts at {start!r} before its release {release!r}")
            if previous is not None and start < previous[1] - TOL:
                violations.append(
                    f"{job} at {stage}: starts at {start!r} before it completes {previous[0]} "
                    f"at {previous[1]!r}"
                )
            previous = (stage, completion)

    # Constraints 4 and 2: one job at a time per stage, in the common sequence at every stage.
    for stage in stages:
        on_stage = sorted(
            ((start, completion, job) for (job, s), (start, completion) in times.items() if s == stage)
        )
        for (s1, c1, j1), (s2, c2, j2) in zip(on_stage, on_stage[1:]):
            if s2 < c1 - TOL:
                violations.append(f"{stage}: {j2} starts at {s2!r} while {j1} runs until {c1!r}")
        order = [job for _, _, job in on_stage]
        if sequence and order != [job for job in sequence if (job, stage) in times]:
            violations.append(f"{stage}: processing order {order} differs from the sequence")

    report = {"feasible": not violations, "violations": violations, "notes": notes, "measures": None}
    if any(v.endswith("not scheduled") or v.startswith("schedule") for v in violations):
        return report

    # Measures, recomputed from the reported starts and completions.
    last = stages[-1]
    makespan = max(completion for _, completion in times.values())
    twt = 0.0
    on_time = 0
    for job, (_, due, weight) in jobs.items():
        finish = times[(job, last)][1]
        twt += weight * max(0.0, finish - due)
        on_time += finish <= due
    waiting = sum(
        times[(job, later)][0] - times[(job, earlier)][1]
        for job in jobs
        for earlier, later in zip(stages, stages[1:])
    )
    idle = {
        stage: makespan - sum(c - s for (_, st), (s, c) in times.items() if st == stage)
        for stage in stages
    }
    report["measures"] = {
        "makespan": makespan,
        "total_weighted_tardiness": twt,
        "on_time_rate": on_time / len(jobs),
        "jobs_completed": len(jobs),
        "downstream_waiting_time": waiting,
        "idle_time_by_stage": idle,
    }

    # Information only: operations that start later than the sequence requires. Such a schedule
    # is still feasible, but the brief's execution rule starts every operation as early as possible.
    if sequence and not violations:
        delayed = 0
        stage_free = {stage: -math.inf for stage in stages}
        for job in sequence:
            ready = jobs[job][0]
            for stage in stages:
                start, completion = times[(job, stage)]
                if start > max(ready, stage_free[stage]) + TOL:
                    delayed += 1
                ready = stage_free[stage] = completion
        if delayed:
            notes.append(f"{delayed} operation(s) start later than the sequence requires")
    return report


def compare_expected(found: dict, expected: dict, tol: float = 1e-6) -> list[str]:
    """List the measures in `expected` (e.g. a worked-example metrics.json) that `found` misses."""
    mismatches = []
    for key, want in expected.items():
        have = found.get(key)
        if isinstance(want, dict) and isinstance(have, dict):
            mismatches += [f"{key}.{m}" for m in compare_expected(have, want, tol)]
        elif have is None or not isinstance(want, (int, float)) or abs(have - want) > tol:
            mismatches.append(f"{key}: expected {want!r}, recomputed {have!r}")
    return mismatches


def _resolve(text: str) -> Path:
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = Path(os.environ.get("INIT_CWD", os.getcwd())) / path
    return path.resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pfsp_check", description=__doc__.split("\n")[0])
    parser.add_argument("input_dir")
    parser.add_argument("decision")
    parser.add_argument("--processing-times", help="realized processing times to check against")
    parser.add_argument("--expect", help="metrics.json whose values the recomputed measures must match")
    parser.add_argument("--json", help="write the full report to this file")
    args = parser.parse_args(argv)

    try:
        report = check_decision(
            _resolve(args.input_dir),
            _resolve(args.decision),
            _resolve(args.processing_times) if args.processing_times else None,
        )
    except Unreadable as error:
        print(f"Cannot check: {error}", file=sys.stderr)
        return 2

    status = 0
    if report["feasible"]:
        print("FEASIBLE: every required constraint holds")
    else:
        print(f"INFEASIBLE: {len(report['violations'])} violation(s)")
        for violation in report["violations"]:
            print(f"  {violation}")
        status = 1
    for note in report["notes"]:
        print(f"  note: {note}")
    if report["measures"]:
        print("Recomputed measures:")
        for key, value in report["measures"].items():
            print(f"  {key}: {value}")
    if args.expect and report["measures"]:
        expected = json.loads(_resolve(args.expect).read_text(encoding="utf-8"))
        mismatches = compare_expected(report["measures"], expected)
        report["expected_mismatches"] = mismatches
        if mismatches:
            print("Measures differ from " + args.expect + ":")
            for mismatch in mismatches:
                print(f"  {mismatch}")
            status = 1
        else:
            print(f"Every measure matches {args.expect}")
    if args.json:
        Path(_resolve(args.json)).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return status
