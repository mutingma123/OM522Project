"""The three tests that the project guide (Section 2.5) requires of every submission."""

import csv
import json

from conftest import DATA, run_tool


def test_1_rule_reproduces_worked_example(copy_instance, tmp_path):
    """The rule to beat reproduces the worked example's decision and every measure."""
    instance = copy_instance("hand_checkable")
    out = tmp_path / "out"
    result = run_tool("pfsp", "solve", str(instance), str(out), "--method", "rule")
    assert result.returncode == 0, result.stderr

    decision = json.loads((out / "decision.json").read_text())
    expected = json.loads((DATA / "worked-example" / "solution.json").read_text())
    assert decision == expected

    check = run_tool(
        "pfsp_check", str(instance), str(out / "decision.json"),
        "--expect", str(DATA / "worked-example" / "metrics.json"),
    )
    assert check.returncode == 0, check.stdout
    assert "FEASIBLE" in check.stdout and "Every measure matches" in check.stdout

    measures = json.loads((out / "summary.json").read_text())["measures"]
    metrics = json.loads((DATA / "worked-example" / "metrics.json").read_text())
    for key, value in metrics.items():
        assert measures[key] == value, key


def test_2_edge_case_is_rejected(copy_instance, tmp_path):
    """The supplied edge case (a zero processing time) is rejected: message naming the file and
    column, no decision.json, nonzero exit."""
    instance = copy_instance("edge_case")
    out = tmp_path / "out"
    result = run_tool("pfsp", "solve", str(instance), str(out))
    assert result.returncode != 0
    assert "processing_times.csv" in result.stderr
    assert "processing_time" in result.stderr
    assert not (out / "decision.json").exists()


def test_3_missing_required_column_is_rejected(copy_instance, tmp_path):
    """A copied instance with a required column deleted is rejected with a clear message."""
    instance = copy_instance("development_small")
    jobs = instance / "jobs.csv"
    with jobs.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    with jobs.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["job_id", "release_time", "weight"])
        writer.writeheader()
        writer.writerows({k: row[k] for k in ("job_id", "release_time", "weight")} for row in rows)

    out = tmp_path / "out"
    result = run_tool("pfsp", "solve", str(instance), str(out))
    assert result.returncode != 0
    assert "jobs.csv, column due_date: required column is missing" in result.stderr
    assert not (out / "decision.json").exists()
