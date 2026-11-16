"""The JSON Schema validates digits.json/letters.json and rejects bad input."""

from __future__ import annotations

import json

import pytest

from cistercian.errors import SpecError
from cistercian.features import load_letter_spec
from cistercian.geometry import load_digit_spec


def test_digits_json_validates(digits_spec_path) -> None:
    spec = load_digit_spec(digits_spec_path)
    assert spec.upm == 1000
    assert set(spec.digits) == {str(d) for d in range(10)}


def test_letters_json_validates(letters_spec_path) -> None:
    spec = load_letter_spec(letters_spec_path)
    assert spec.mapping_mode == "shared"
    assert spec.letters["A"] == 1
    assert spec.letters["Z"] == 26


def test_digits_json_rejects_missing_required_key(tmp_path, digits_spec_path) -> None:
    broken = json.loads(digits_spec_path.read_text())
    del broken["stroke_width"]
    path = tmp_path / "digits.json"
    path.write_text(json.dumps(broken))
    with pytest.raises(SpecError):
        load_digit_spec(path)


def test_digits_json_rejects_unknown_top_level_key(tmp_path, digits_spec_path) -> None:
    broken = json.loads(digits_spec_path.read_text())
    broken["sparkle"] = True
    path = tmp_path / "digits.json"
    path.write_text(json.dumps(broken))
    with pytest.raises(SpecError):
        load_digit_spec(path)


def test_digits_json_rejects_a_point_with_three_coordinates(
    tmp_path, digits_spec_path
) -> None:
    broken = json.loads(digits_spec_path.read_text())
    broken["digits"]["1"]["segments"][0][0] = [0, 0, 0]
    path = tmp_path / "digits.json"
    path.write_text(json.dumps(broken))
    with pytest.raises(SpecError):
        load_digit_spec(path)


def test_letters_json_rejects_wrong_letter_count(tmp_path, letters_spec_path) -> None:
    broken = json.loads(letters_spec_path.read_text())
    del broken["letters"]["Z"]
    path = tmp_path / "letters.json"
    path.write_text(json.dumps(broken))
    with pytest.raises(SpecError):
        load_letter_spec(path)


def test_missing_file_raises_spec_error(tmp_path) -> None:
    with pytest.raises(SpecError):
        load_digit_spec(tmp_path / "nope.json")
