"""Further input checks: each of the four checks, reordered rows, and renamed identifiers."""

import csv
import random

import pytest
from conftest import DATA

from pfsp.data import InputError, load_instance
from pfsp.rule import edd_sequence
from pfsp.timing import evaluate


def rewrite(path, transform):
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields, rows = reader.fieldnames, list(reader)
    fields, rows = transform(fields, rows)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def rejection(directory) -> str:
    with pytest.raises(InputError) as error:
        load_instance(directory)
    return str(error.value)


def test_missing_file(copy_instance):
    instance = copy_instance("hand_checkable")
    (instance / "stages.csv").unlink()
    assert "stages.csv: required file is missing" in rejection(instance)


def test_wrong_type_and_empty_value(copy_instance):
    instance = copy_instance("hand_checkable")

    def damage(fields, rows):
        rows[0]["release_time"] = "early"
        rows[1]["weight"] = ""
        return fields, rows

    rewrite(instance / "jobs.csv", damage)
    message = rejection(instance)
    assert "jobs.csv, column release_time, line 2: 'early' is not of type integer" in message
    assert "jobs.csv, column weight, line 3: value is empty" in message


def test_unknown_identifier(copy_instance):
    instance = copy_instance("hand_checkable")

    def damage(fields, rows):
        rows[0]["job_id"] = "J999"
        return fields, rows

    rewrite(instance / "processing_times.csv", damage)
    message = rejection(instance)
    assert "processing_times.csv, column job_id, line 2: 'J999' does not appear in jobs.csv" in message


def test_negative_processing_time(copy_instance):
    instance = copy_instance("hand_checkable")

    def damage(fields, rows):
        rows[5]["processing_time"] = "-3"
        return fields, rows

    rewrite(instance / "processing_times.csv", damage)
    assert "column processing_time, line 7: -3 is not positive" in rejection(instance)


def test_missing_job_stage_pair(copy_instance):
    instance = copy_instance("hand_checkable")
    rewrite(instance / "processing_times.csv", lambda fields, rows: (fields, rows[1:]))
    assert "no row for pair (J001, S1)" in rejection(instance)


def test_reordered_rows_give_the_same_decision(copy_instance):
    """Identifiers are matched by value, so shuffling rows changes nothing."""
    original = load_instance(DATA / "development_small")
    shuffled_dir = copy_instance("development_small")
    rng = random.Random(7)
    for name in ("jobs.csv", "stages.csv", "processing_times.csv"):
        rewrite(shuffled_dir / name, lambda fields, rows: (fields, rng.sample(rows, len(rows))))
    shuffled = load_instance(shuffled_dir)

    seq_a = [original.job_ids[j] for j in edd_sequence(original)]
    seq_b = [shuffled.job_ids[j] for j in edd_sequence(shuffled)]
    assert seq_a == seq_b
    assert shuffled.stage_ids == original.stage_ids
    a = evaluate(edd_sequence(original), original.release, original.due, original.weight, original.p)
    b = evaluate(edd_sequence(shuffled), shuffled.release, shuffled.due, shuffled.weight, shuffled.p)
    assert a == b


def test_renamed_identifiers_are_accepted(copy_instance):
    instance = copy_instance("hand_checkable")
    rename = {"J001": "alpha", "S2": "paint"}
    for name in ("jobs.csv", "processing_times.csv", "stages.csv"):
        rewrite(
            instance / name,
            lambda fields, rows: (
                fields,
                [{k: rename.get(v, v) for k, v in row.items()} for row in rows],
            ),
        )
    loaded = load_instance(instance)
    assert "alpha" in loaded.job_ids and loaded.stage_ids[1] == "paint"
