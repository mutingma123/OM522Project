"""Load an option 6 instance directory and apply the four input checks.

The data dictionary requires a tool to reject input that fails any of four checks, with a message
naming the file and column:

1. every required file and column is present;
2. every value has its declared type, and every column that schema.json marks as not nullable is
   filled;
3. every identifier referenced from another file exists; and
4. processing times are positive.

The loader collects every failure it finds rather than stopping at the first one, so a planner sees
the whole list at once. Missing or invalid values are never replaced by defaults.
"""

from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Required files and columns, with the types the data dictionary declares. schema.json in the
# instance directory overrides a declared type when it names one of the known types.
REQUIRED = {
    "jobs.csv": {
        "job_id": "string",
        "release_time": "integer",
        "due_date": "integer",
        "weight": "integer",
    },
    "stages.csv": {
        "stage_id": "string",
        "sequence": "integer",
    },
    "processing_times.csv": {
        "job_id": "string",
        "stage_id": "string",
        "processing_time": "integer",
    },
}
KNOWN_TYPES = {"string", "integer", "number"}
_INTEGER = re.compile(r"[+-]?\d+")


class InputError(Exception):
    """Raised when an instance fails one or more input checks. Holds every message found."""

    def __init__(self, messages: list[str]):
        self.messages = messages
        super().__init__("\n".join(messages))


@dataclass(frozen=True)
class Instance:
    """A validated instance. Jobs keep their jobs.csv row order and stages follow `sequence`."""

    name: str
    job_ids: tuple[str, ...]
    stage_ids: tuple[str, ...]
    release: np.ndarray  # shape (n,)
    due: np.ndarray  # shape (n,)
    weight: np.ndarray  # shape (n,)
    p: np.ndarray  # shape (n, m), p[j, k] is job j's time at the k-th stage in line order
    time_unit: str

    @property
    def n(self) -> int:
        return len(self.job_ids)

    @property
    def m(self) -> int:
        return len(self.stage_ids)


def _declared_types(directory: Path, errors: list[str]) -> dict[str, dict[str, str]]:
    """Return the declared type of every required column, taking schema.json into account."""
    types = {name: dict(cols) for name, cols in REQUIRED.items()}
    schema_path = directory / "schema.json"
    if not schema_path.is_file():
        return types
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        files = schema["files"]
    except (OSError, ValueError, KeyError, TypeError):
        # schema.json is supporting metadata, not a required input, so fall back to the data
        # dictionary's types instead of rejecting the instance.
        return types
    for file_name, columns in types.items():
        for column in (files.get(file_name) or {}).get("columns", []):
            declared = column.get("type") if isinstance(column, dict) else None
            if column.get("name") in columns and declared in KNOWN_TYPES:
                columns[column["name"]] = declared
    return types


def _parse(value: str, declared: str) -> object | None:
    """Parse one cell as its declared type, returning None when the text does not fit the type."""
    if declared == "string":
        return value
    if declared == "integer":
        return int(value) if _INTEGER.fullmatch(value) else None
    try:
        number = float(value)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _read_table(
    directory: Path, file_name: str, declared: dict[str, str], errors: list[str]
) -> list[dict[str, object]] | None:
    """Read one CSV, check its columns and value types, and return its typed rows."""
    path = directory / file_name
    if not path.is_file():
        errors.append(f"{file_name}: required file is missing from {directory.name}")
        return None
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        header = [name.strip() for name in (reader.fieldnames or [])]
        missing = [column for column in declared if column not in header]
        for column in missing:
            errors.append(f"{file_name}, column {column}: required column is missing")
        if missing:
            return None
        reader.fieldnames = header
        rows = []
        for line, raw in enumerate(reader, start=2):
            row: dict[str, object] = {"_line": line}
            for column, kind in declared.items():
                text = (raw.get(column) or "").strip()
                if text == "":
                    errors.append(f"{file_name}, column {column}, line {line}: value is empty")
                    continue
                value = _parse(text, kind)
                if value is None:
                    errors.append(
                        f"{file_name}, column {column}, line {line}: '{text}' is not of type {kind}"
                    )
                    continue
                row[column] = value
            rows.append(row)
    if not rows:
        errors.append(f"{file_name}: file has a header but no data rows")
    return rows


def _unique_ids(rows: list[dict], file_name: str, column: str, errors: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered = []
    for row in rows:
        value = row.get(column)
        if value is None:
            continue
        if value in seen:
            errors.append(f"{file_name}, column {column}, line {row['_line']}: '{value}' is repeated")
        else:
            seen.add(value)
            ordered.append(value)
    return ordered


def load_instance(directory: str | Path) -> Instance:
    """Validate and load an instance directory. Raises InputError listing every failed check."""
    directory = Path(directory)
    errors: list[str] = []
    if not directory.is_dir():
        raise InputError([f"{directory.name}: input directory does not exist"])

    types = _declared_types(directory, errors)
    tables = {name: _read_table(directory, name, types[name], errors) for name in REQUIRED}
    if any(table is None for table in tables.values()):
        raise InputError(errors)
    jobs, stages, times = tables["jobs.csv"], tables["stages.csv"], tables["processing_times.csv"]

    job_ids = _unique_ids(jobs, "jobs.csv", "job_id", errors)
    stage_ids = _unique_ids(stages, "stages.csv", "stage_id", errors)

    # Stage order comes from the sequence column, whose values must run from 1 to the stage count.
    order = {}
    for row in stages:
        if "stage_id" in row and "sequence" in row:
            order.setdefault(row["stage_id"], row["sequence"])
    if sorted(order.values()) != list(range(1, len(order) + 1)):
        errors.append(
            f"stages.csv, column sequence: values {sorted(order.values())} do not run from 1 to "
            f"{len(order)} without gaps or repeats"
        )

    job_index = {job: j for j, job in enumerate(job_ids)}
    stage_list = sorted(order, key=order.get)
    stage_index = {stage: k for k, stage in enumerate(stage_list)}
    p = np.full((len(job_ids), len(stage_list)), np.nan)
    for row in times:
        line = row["_line"]
        job, stage, value = row.get("job_id"), row.get("stage_id"), row.get("processing_time")
        if job is not None and job not in job_index:
            errors.append(
                f"processing_times.csv, column job_id, line {line}: '{job}' does not appear in jobs.csv"
            )
            continue
        if stage is not None and stage not in stage_index:
            errors.append(
                f"processing_times.csv, column stage_id, line {line}: '{stage}' does not appear in "
                "stages.csv"
            )
            continue
        if value is not None and value <= 0:
            errors.append(
                f"processing_times.csv, column processing_time, line {line}: {value} is not positive"
            )
            continue
        if job is None or stage is None or value is None:
            continue
        j, k = job_index[job], stage_index[stage]
        if not np.isnan(p[j, k]):
            errors.append(
                f"processing_times.csv, columns job_id and stage_id, line {line}: pair "
                f"({job}, {stage}) is repeated"
            )
            continue
        p[j, k] = value

    if not errors:
        for j, k in zip(*np.nonzero(np.isnan(p))):
            errors.append(
                f"processing_times.csv, columns job_id and stage_id: no row for pair "
                f"({job_ids[j]}, {stage_list[k]})"
            )
    if errors:
        raise InputError(errors)

    by_job = {row["job_id"]: row for row in jobs}
    time_unit = "minutes"
    info_path = directory / "instance.json"
    if info_path.is_file():
        try:
            time_unit = json.loads(info_path.read_text(encoding="utf-8")).get("time_unit", time_unit)
        except (OSError, ValueError, AttributeError):
            pass
    return Instance(
        name=directory.resolve().name,
        job_ids=tuple(job_ids),
        stage_ids=tuple(stage_list),
        release=np.array([by_job[job]["release_time"] for job in job_ids], dtype=float),
        due=np.array([by_job[job]["due_date"] for job in job_ids], dtype=float),
        weight=np.array([by_job[job]["weight"] for job in job_ids], dtype=float),
        p=p,
        time_unit=time_unit,
    )
