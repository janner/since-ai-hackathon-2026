"""The R16 agreement check on a small synthetic run."""

import csv

import pytest

from scripts.eval_3074 import main


def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_agreement_and_differences(tmp_path, capsys):
    run = tmp_path / "run.csv"
    labels = tmp_path / "labels.csv"
    write_csv(
        run,
        ("ntc_id", "class", "margin_db"),
        [
            {"ntc_id": "a", "class": "near", "margin_db": "-1.0"},
            {"ntc_id": "b", "class": "exceeds", "margin_db": "0.5"},
        ],
    )
    write_csv(
        labels,
        ("ntc_id", "label", "rationale"),
        [
            {"ntc_id": "a", "label": "near", "rationale": "inside the band"},
            {"ntc_id": "b", "label": "near", "rationale": "on the boundary"},
        ],
    )

    assert main(["--run", str(run), "--labels", str(labels)]) == 0

    output = capsys.readouterr().out
    assert "own labels: 1/2 agree (50.0%)" in output
    assert "run=exceeds" in output and "own=near" in output


def test_a_classified_notice_without_a_label_fails(tmp_path):
    run = tmp_path / "run.csv"
    labels = tmp_path / "labels.csv"
    write_csv(run, ("ntc_id", "class"), [{"ntc_id": "a", "class": "near"}])
    write_csv(labels, ("ntc_id", "label"), [])

    with pytest.raises(SystemExit, match="no label for: a"):
        main(["--run", str(run), "--labels", str(labels)])
