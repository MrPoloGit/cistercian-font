"""A contact sheet is rendered for visual checking."""

from __future__ import annotations

from pathlib import Path

from cistercian.build import build_ttf
from cistercian.cli import main
from cistercian.contact_sheet import render_contact_sheet, write_contact_sheet


def test_render_contact_sheet_produces_one_path_per_number(
    digits_spec_path, letters_spec_path
) -> None:
    font = build_ttf(str(digits_spec_path), str(letters_spec_path), numbers=range(30))
    svg = render_contact_sheet(font, list(range(30)), columns=10)
    assert svg.startswith("<svg")
    assert svg.count("<path") == 30


def test_write_contact_sheet_writes_a_file(
    digits_spec_path, letters_spec_path, tmp_path: Path
) -> None:
    font = build_ttf(str(digits_spec_path), str(letters_spec_path), numbers=range(10))
    out = tmp_path / "sheet.svg"
    write_contact_sheet(font, list(range(10)), out)
    assert out.exists()
    assert out.read_text().startswith("<svg")


def test_cli_contact_sheet_subcommand(
    digits_spec_path, letters_spec_path, tmp_path: Path
) -> None:
    out = tmp_path / "sheet.svg"
    code = main(
        [
            "contact-sheet",
            "--digits",
            str(digits_spec_path),
            "--letters",
            str(letters_spec_path),
            "--out",
            str(out),
            "--numbers",
            "15",
        ]
    )
    assert code == 0
    assert out.exists()
