"""The ``cistercian build`` and ``cistercian merge`` subcommands."""

from __future__ import annotations

from pathlib import Path

from cistercian.cli import main


def test_build_writes_requested_formats(
    digits_spec_path, letters_spec_path, tmp_path: Path
) -> None:
    out_dir = tmp_path / "dist"
    code = main(
        [
            "build",
            "--digits",
            str(digits_spec_path),
            "--letters",
            str(letters_spec_path),
            "--out",
            str(out_dir),
            "--numbers",
            "20",
            "--formats",
            "ttf,woff2",
        ]
    )
    assert code == 0
    assert (out_dir / "Cistercian-Regular.ttf").exists()
    assert (out_dir / "Cistercian-Regular.woff2").exists()
    assert not (out_dir / "Cistercian-Regular.otf").exists()


def test_build_all_formats_by_default(
    digits_spec_path, letters_spec_path, tmp_path: Path
) -> None:
    out_dir = tmp_path / "dist"
    code = main(
        [
            "build",
            "--digits",
            str(digits_spec_path),
            "--letters",
            str(letters_spec_path),
            "--out",
            str(out_dir),
            "--numbers",
            "20",
        ]
    )
    assert code == 0
    for ext in ("ttf", "otf", "woff2"):
        assert (out_dir / f"Cistercian-Regular.{ext}").exists()


def test_merge_writes_output_font(
    digits_spec_path, letters_spec_path, base_font_path: Path, tmp_path: Path
) -> None:
    out_path = tmp_path / "merged.ttf"
    code = main(
        [
            "merge",
            str(base_font_path),
            "--digits",
            str(digits_spec_path),
            "--letters",
            str(letters_spec_path),
            "--out",
            str(out_path),
            "--numbers",
            "20",
        ]
    )
    assert code == 0
    assert out_path.exists()


def test_merge_reports_spec_errors_without_a_traceback(
    letters_spec_path, base_font_path: Path, tmp_path: Path, capsys
) -> None:
    code = main(
        [
            "merge",
            str(base_font_path),
            "--digits",
            str(tmp_path / "missing.json"),
            "--letters",
            str(letters_spec_path),
            "--out",
            str(tmp_path / "merged.ttf"),
        ]
    )
    assert code == 1
    assert "error:" in capsys.readouterr().err
