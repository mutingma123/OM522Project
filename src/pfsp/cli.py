"""Command line for the decision tool: `python -m pfsp solve <input_dir> <output_dir>`."""

from __future__ import annotations

import argparse
import os
import platform
import sys
import time
from pathlib import Path

from .data import InputError, load_instance
from .ig import DEFAULT_ITERATIONS, DEFAULT_SEED, DEFAULT_TIME_CAP, iterated_greedy, neh_ewdd
from .output import build_decision, measures, write_outputs
from .rule import edd_sequence


def user_path(text: str) -> Path:
    """Resolve a path the way the user typed it. Pixi runs tasks from the project root and records
    the directory the command was typed in as INIT_CWD, so relative paths resolve against that."""
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = Path(os.environ.get("INIT_CWD", os.getcwd())) / path
    return path.resolve()


def run_method(instance, method: str, args) -> tuple[object, dict]:
    """Run one method and return (sequence or None, settings and stopping details)."""
    if method == "ig":
        return iterated_greedy(instance, iterations=args.iterations, seed=args.seed, time_cap=args.time_cap)
    if method == "rule":
        return edd_sequence(instance), {"rule": "earliest due date, ties by job_id"}
    if method == "neh":
        return neh_ewdd(instance)
    raise ValueError(f"unknown method {method}")


def solve(args) -> int:
    input_dir, output_dir = user_path(args.input_dir), user_path(args.output_dir)
    if output_dir == input_dir:
        print("The output directory must differ from the input directory.", file=sys.stderr)
        return 2
    try:
        instance = load_instance(input_dir)
    except InputError as error:
        print(f"Input rejected ({len(error.messages)} problem(s)); no decision.json written:", file=sys.stderr)
        for message in error.messages:
            print(f"  {message}", file=sys.stderr)
        return 1

    began = time.perf_counter()
    seq, details = run_method(instance, args.method, args)
    elapsed = time.perf_counter() - began
    if seq is None:
        print("no feasible decision found")
        return 0

    found = measures(instance, seq)
    summary = {
        "status": "decision written",
        "instance": str(input_dir.name),
        "jobs": instance.n,
        "stages": instance.m,
        "time_unit": instance.time_unit,
        "method": args.method,
        "details": details,
        "computation_seconds": elapsed,
        "computer": f"{platform.processor() or platform.machine()} ({platform.system()})",
        "measures": found,
    }
    write_outputs(output_dir, build_decision(instance, seq), summary)
    print(f"{args.method} on {input_dir.name}: {instance.n} jobs, {instance.m} stages")
    print(f"  total weighted tardiness     {found['total_weighted_tardiness']}")
    print(f"  total waiting between stages {found['downstream_waiting_time']}")
    print(f"  computation time (s)         {elapsed:.3f}")
    print(f"  wrote {output_dir / 'decision.json'} and summary.json")
    return 0


def results_dir(text: str | None, default: str) -> Path:
    from .compare import ROOT

    return user_path(text) if text else ROOT / "results" / default


def compare(args) -> int:
    from . import compare as comparison

    comparison.run(results_dir(args.out, "comparison"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pfsp", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    p_solve = commands.add_parser("solve", help="solve one instance directory")
    p_solve.add_argument("input_dir")
    p_solve.add_argument("output_dir")
    p_solve.add_argument(
        "--method", choices=["ig", "rule", "neh"], default="ig",
        help="ig: researched method (default); rule: the rule to beat; neh: NEH_EWDD construction only",
    )
    p_solve.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS, help="ig stopping rule")
    p_solve.add_argument("--seed", type=int, default=DEFAULT_SEED, help="ig random seed")
    p_solve.add_argument("--time-cap", type=float, default=DEFAULT_TIME_CAP, help="ig safety cap, seconds")
    p_solve.set_defaults(handler=solve)

    p_compare = commands.add_parser("compare", help="deterministic comparison on four instances")
    p_compare.add_argument("--out", help="output directory (default results/comparison)")
    p_compare.set_defaults(handler=compare)

    args = parser.parse_args(argv)
    return args.handler(args)
