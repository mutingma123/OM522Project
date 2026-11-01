"""The researched method: feasibility, the margin over the rule, reproducibility, and optimality on
the hand-checkable case."""

import itertools
import json

import numpy as np
import pytest
from conftest import DATA, DEVELOPMENT, run_tool

from pfsp.data import load_instance
from pfsp.ig import ewdd_order, iterated_greedy
from pfsp.output import build_decision
from pfsp.rule import edd_sequence
from pfsp.timing import evaluate
from pfsp_check import check_decision


def objective(instance, seq):
    return evaluate(np.asarray(seq, dtype=np.int64), instance.release, instance.due, instance.weight, instance.p)


@pytest.mark.parametrize("name", ["hand_checkable", *DEVELOPMENT])
def test_ig_is_feasible_and_beats_the_rule(tmp_path, name):
    instance = load_instance(DATA / name)
    seq, details = iterated_greedy(instance, iterations=300)
    path = tmp_path / "decision.json"
    path.write_text(json.dumps(build_decision(instance, seq)))
    report = check_decision(DATA / name, path)
    assert report["feasible"], report["violations"]
    rule_twt = objective(instance, edd_sequence(instance))[0]
    assert report["measures"]["total_weighted_tardiness"] < rule_twt - 0.001
    assert details["iterations_run"] == 300


def test_same_seed_same_sequence():
    instance = load_instance(DATA / "development_medium")
    first, _ = iterated_greedy(instance, iterations=100, seed=11)
    second, _ = iterated_greedy(instance, iterations=100, seed=11)
    assert first.tolist() == second.tolist()


def test_hand_checkable_reaches_the_brute_force_optimum():
    instance = load_instance(DATA / "hand_checkable")
    optimum = min(objective(instance, perm) for perm in itertools.permutations(range(instance.n)))
    seq, _ = iterated_greedy(instance, iterations=50)
    assert objective(instance, seq) == optimum


def test_ewdd_order_ties_by_identifier():
    instance = load_instance(DATA / "hand_checkable")
    order = [instance.job_ids[j] for j in ewdd_order(instance)]
    ratios = [instance.due[instance.job_ids.index(j)] / instance.weight[instance.job_ids.index(j)] for j in order]
    assert ratios == sorted(ratios)


def test_default_solve_command_on_a_fresh_copy(copy_instance, tmp_path):
    """The command the instructor runs: default settings, fresh instance, checked decision."""
    instance = copy_instance("development_medium")
    out = tmp_path / "out"
    result = run_tool("pfsp", "solve", str(instance), str(out))
    assert result.returncode == 0, result.stderr
    summary = json.loads((out / "summary.json").read_text())
    assert summary["method"] == "ig" and summary["details"]["iterations_run"] == 5000
    check = run_tool("pfsp_check", str(instance), str(out / "decision.json"))
    assert check.returncode == 0, check.stdout
