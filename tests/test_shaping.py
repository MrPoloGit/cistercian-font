"""HarfBuzz shaping turns digit strings and UCSUR sequences into the expected glyphs."""

from __future__ import annotations

from pathlib import Path

import pytest
import uharfbuzz as hb

from cistercian.glyphs import (
    overlay_codepoint,
    precomposed_glyph_name,
    units_codepoint,
)


def _shape(
    font_path: Path, text: str, features: dict[str, bool] | None = None
) -> list[str]:
    blob = hb.Blob.from_file_path(str(font_path))
    face = hb.Face(blob)
    font = hb.Font(face)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, features or {})
    return [font.glyph_to_string(info.codepoint) for info in buf.glyph_infos]


def test_ucsur_sequence_ligates_to_the_precomposed_glyph(full_ttf_path: Path) -> None:
    # 9230 = units 0 (bare stave) + tens 3 + hundreds 2 + thousands 9.
    text = "".join(
        chr(cp)
        for cp in (
            units_codepoint(0),
            overlay_codepoint("tens", 3),
            overlay_codepoint("hundreds", 2),
            overlay_codepoint("thousands", 9),
        )
    )
    assert _shape(full_ttf_path, text) == [precomposed_glyph_name(9230)]


def test_units_codepoint_alone_shapes_to_its_own_glyph(full_ttf_path: Path) -> None:
    assert _shape(full_ttf_path, chr(units_codepoint(7))) == ["cistercian.units.7"]


def test_precomposed_codepoint_is_directly_addressable(full_ttf_path: Path) -> None:
    assert _shape(full_ttf_path, chr(0xF0000 + 9999)) == [precomposed_glyph_name(9999)]


@pytest.mark.parametrize("number", [0, 7, 23, 150, 9999, 4002])
def test_ss01_converts_a_clean_digit_run(merged_font_path: Path, number: int) -> None:
    assert _shape(merged_font_path, str(number), {"ss01": True}) == [
        precomposed_glyph_name(number)
    ]


def test_ss01_without_the_feature_leaves_plain_digits(merged_font_path: Path) -> None:
    assert _shape(merged_font_path, "23", {}) == ["two", "three"]


def test_ss01_leading_zero_run_stays_plain(merged_font_path: Path) -> None:
    assert _shape(merged_font_path, "0123", {"ss01": True}) == [
        "zero",
        "one",
        "two",
        "three",
    ]


def test_ss01_run_longer_than_four_stays_plain(merged_font_path: Path) -> None:
    assert _shape(merged_font_path, "12345", {"ss01": True}) == [
        "one",
        "two",
        "three",
        "four",
        "five",
    ]


def test_ss01_lone_zero_becomes_bare_stave(merged_font_path: Path) -> None:
    # cistercian.num.0000 is a trivial composite of the bare stave (cistercian.units.0).
    assert _shape(merged_font_path, "0", {"ss01": True}) == [precomposed_glyph_name(0)]


def test_ss01_adjacent_runs_convert_independently(merged_font_path: Path) -> None:
    assert _shape(merged_font_path, "12 34", {"ss01": True}) == [
        precomposed_glyph_name(12),
        "space",
        precomposed_glyph_name(34),
    ]


def test_ss02_uppercase_letter_maps_to_its_value(merged_font_path: Path) -> None:
    assert _shape(merged_font_path, "C", {"ss02": True}) == [precomposed_glyph_name(3)]


def test_ss02_lowercase_shares_the_uppercase_numeral_by_default(
    merged_font_path: Path,
) -> None:
    assert _shape(merged_font_path, "c", {"ss02": True}) == [precomposed_glyph_name(3)]


def test_ss02_z_maps_to_26(merged_font_path: Path) -> None:
    assert _shape(merged_font_path, "Z", {"ss02": True}) == [precomposed_glyph_name(26)]
