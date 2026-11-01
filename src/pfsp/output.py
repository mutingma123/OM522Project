"""Turn a sequence into a schedule, compute its measures, and write decision.json and summary.json.

decision.json keeps the structure of worked-example/solution.json: a `sequence` list of job
identifiers and a `schedule` list with one entry per job-stage pair. Times are written at full
precision, because the instructor's checker compares each duration with the input to within 1e-8.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .data import Instance
from .timing import start_completion


def _number(value: float) -> int | float:
    """Write whole numbers as integers, as the worked example does, and keep every other value."""
    value = float(value)
    return int(value) if value.is_integer() else value


def build_decision(instance: Instance, seq: np.ndarray) -> dict:
    start, completion = start_completion(seq, instance.release, instance.p)
    schedule = [
        {
            "job_id": instance.job_ids[job],
            "stage_id": stage,
            "start": _number(start[i, k]),
            "completion": _number(completion[i, k]),
        }
        for i, job in enumerate(seq)
        for k, stage in enumerate(instance.stage_ids)
    ]
    return {"sequence": [instance.job_ids[job] for job in seq], "schedule": schedule}


def measures(instance: Instance, seq: np.ndarray) -> dict:
    """The worked example's measures, computed by the tool (the checker recomputes them itself)."""
    start, completion = start_completion(seq, instance.release, instance.p)
    finish = completion[:, -1]
    tardiness = np.maximum(finish - instance.due[seq], 0.0)
    makespan = float(completion.max())
    busy = instance.p.sum(axis=0)
    return {
        "makespan": _number(makespan),
        "total_weighted_tardiness": _number(float(instance.weight[seq] @ tardiness)),
        "on_time_rate": float(np.mean(finish <= instance.due[seq])),
        "jobs_completed": int(len(seq)),
        "downstream_waiting_time": _number(float((start[:, 1:] - completion[:, :-1]).sum())),
        "idle_time_by_stage": {
            stage: _number(makespan - busy[k]) for k, stage in enumerate(instance.stage_ids)
        },
    }


def write_outputs(output_dir: Path, decision: dict, summary: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "decision.json").write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
