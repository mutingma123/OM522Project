"""The checker confirms valid decisions and catches each kind of violation it is meant to catch."""

import json

import numpy as np
import pytest
from conftest import DATA, DEVELOPMENT

from pfsp.data import load_instance
from pfsp.output import build_decision
from pfsp.rule import edd_sequence
from pfsp.timing import best_insertion, evaluate, insert
from pfsp_check import check_decision


def write_decision(tmp_path, decision):
    path = tmp_path / "decision.json"
    path.write_text(json.dumps(decision))
    return path


@pytest.mark.parametrize("name", ["hand_checkable", *DEVELOPMENT])
def test_checker_confirms_rule_and_agrees_with_solver(tmp_path, name):
    instance = load_instance(DATA / name)
    seq = edd_sequence(instance)
    report = check_decision(DATA / name, write_decision(tmp_path, build_decision(instance, seq)))
    assert report["feasible"], report["violations"]
    twt, waiting = evaluate(seq, instance.release, instance.due, instance.weight, instance.p)
    assert report["measures"]["total_weighted_tardiness"] == pytest.approx(twt)
    assert report["measures"]["downstream_waiting_time"] == pytest.approx(waiting)
    assert report["notes"] == []


@pytest.fixture
def worked():
    return json.loads((DATA / "worked-example" / "solution.json").read_text())


def violations(tmp_path, decision):
    return check_decision(DATA / "hand_checkable", write_decision(tmp_path, decision))["violations"]


def test_wrong_duration(tmp_path, worked):
    worked["schedule"][0]["completion"] += 1e-6  # beyond the 1e-8 tolerance
    assert any("J001 at S1: runs" in v for v in violations(tmp_path, worked))


def test_start_before_release(tmp_path, worked):
    worked["schedule"][0]["start"] -= 1
    worked["schedule"][0]["completion"] -= 1
    assert any("before its release" in v for v in violations(tmp_path, worked))


def test_stage_order(tmp_path, worked):
    worked["schedule"][1]["start"] -= 1  # J001 at S2 before it completes S1
    worked["schedule"][1]["completion"] -= 1
    assert any("J001 at S2: starts at 23 before it completes S1" in v for v in violations(tmp_path, worked))


def test_overlap_and_sequence_change(tmp_path, worked):
    # Move J002 at S1 to start at 20, overlapping J001 (13 to 24), and make the sequence differ.
    worked["schedule"][4].update(start=10, completion=24)
    found = violations(tmp_path, worked)
    assert any("S1: J001 starts at 13 while J002 runs until 24" in v for v in found)
    assert any("S1: processing order" in v for v in found)


def test_missing_and_duplicate_entries(tmp_path, worked):
    worked["schedule"].append(dict(worked["schedule"][0]))
    del worked["schedule"][5]
    found = violations(tmp_path, worked)
    assert "J001 at S1: scheduled more than once" in found
    assert "J002 at S2: not scheduled" in found


def test_sequence_missing_a_job(tmp_path, worked):
    worked["sequence"].remove("J004")
    assert "sequence: J004 is missing" in violations(tmp_path, worked)


def test_delayed_start_is_feasible_but_noted(tmp_path, worked):
    for entry in worked["schedule"]:
        if entry["job_id"] == "J004" and entry["stage_id"] == "S4":
            entry["start"] += 5
            entry["completion"] += 5
    report = check_decision(DATA / "hand_checkable", write_decision(tmp_path, worked))
    assert report["feasible"]
    assert report["notes"] == ["1 operation(s) start later than the sequence requires"]
    assert report["measures"]["total_weighted_tardiness"] == 281 + 4 * 5


def test_best_insertion_matches_brute_force():
    instance = load_instance(DATA / "development_small")
    rng = np.random.default_rng(3)
    for _ in range(20):
        seq = rng.permutation(instance.n).astype(np.int64)
        job, rest = seq[0], seq[1:]
        pos, twt, waiting = best_insertion(rest, job, instance.release, instance.due, instance.weight, instance.p)
        values = [
            evaluate(insert(rest, k, job), instance.release, instance.due, instance.weight, instance.p)
            for k in range(rest.size + 1)
        ]
        assert values[pos] == (twt, waiting)
        assert min(values) == (twt, waiting)
        assert pos == values.index(min(values))
