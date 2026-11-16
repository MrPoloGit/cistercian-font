"""Font assembly: TTF composites, flattened OTF/CFF outlines, and WOFF2 export."""

from __future__ import annotations

from pathlib import Path

from fontTools.ttLib import TTFont

from cistercian.build import build_all, build_otf, build_ttf, save_woff2
from cistercian.glyphs import precomposed_glyph_name


def test_build_ttf_has_composite_precomposed_glyphs(
    digits_spec_path, letters_spec_path
) -> None:
    font = build_ttf(str(digits_spec_path), str(letters_spec_path), numbers=range(20))
    glyf = font["glyf"]
    glyph = glyf[precomposed_glyph_name(9)]
    assert glyph.isComposite()


def test_build_otf_flattens_composites_into_plain_outlines(
    digits_spec_path, letters_spec_path
) -> None:
    font = build_otf(str(digits_spec_path), str(letters_spec_path), numbers=range(20))
    assert "CFF " in font
    assert "glyf" not in font
    cff = font["CFF "].cff[font["CFF "].cff.fontNames[0]]
    assert precomposed_glyph_name(9) in cff.CharStrings


def test_ttf_and_otf_agree_on_cmap(digits_spec_path, letters_spec_path) -> None:
    ttf = build_ttf(str(digits_spec_path), str(letters_spec_path), numbers=range(20))
    otf = build_otf(str(digits_spec_path), str(letters_spec_path), numbers=range(20))
    assert ttf["cmap"].getBestCmap() == otf["cmap"].getBestCmap()


def test_save_woff2_round_trips_and_restores_flavor(
    digits_spec_path, letters_spec_path, tmp_path: Path
) -> None:
    font = build_ttf(str(digits_spec_path), str(letters_spec_path), numbers=range(20))
    assert font.flavor is None
    out = tmp_path / "test.woff2"
    save_woff2(font, out)
    assert font.flavor is None  # restored after saving
    assert out.exists()
    reloaded = TTFont(str(out))
    assert reloaded.flavor == "woff2"


def test_build_all_writes_three_formats(
    digits_spec_path, letters_spec_path, tmp_path: Path
) -> None:
    paths = build_all(
        str(digits_spec_path), str(letters_spec_path), tmp_path, numbers=range(20)
    )
    assert set(paths) == {"ttf", "otf", "woff2"}
    for path in paths.values():
        assert path.exists()
        assert path.stat().st_size > 0


def test_deterministic_timestamp_from_source_date_epoch(
    digits_spec_path, letters_spec_path, monkeypatch
) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")
    font_a = build_ttf(str(digits_spec_path), str(letters_spec_path), numbers=range(5))
    font_b = build_ttf(str(digits_spec_path), str(letters_spec_path), numbers=range(5))
    assert font_a["head"].created == font_b["head"].created
    assert font_a["head"].modified == font_b["head"].modified
