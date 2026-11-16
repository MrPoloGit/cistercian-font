"""Every number 0-9999 has a precomposed glyph with sane composite structure."""

from __future__ import annotations

import pytest
from fontTools.ttLib import TTFont
from hypothesis import given
from hypothesis import strategies as st

from cistercian.geometry import load_digit_spec
from cistercian.glyphs import (
    build_precomposed_glyphs,
    decompose,
    precomposed_glyph_name,
)


def test_decompose_covers_the_full_range() -> None:
    for n in range(10000):
        units, tens, hundreds, thousands = decompose(n)
        assert units + 10 * tens + 100 * hundreds + 1000 * thousands == n


@given(st.integers(min_value=0, max_value=9999))
def test_decompose_is_the_inverse_of_place_value(n: int) -> None:
    units, tens, hundreds, thousands = decompose(n)
    assert 0 <= units <= 9
    assert 0 <= tens <= 9
    assert 0 <= hundreds <= 9
    assert 0 <= thousands <= 9
    assert units + 10 * tens + 100 * hundreds + 1000 * thousands == n


def test_decompose_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        decompose(10000)
    with pytest.raises(ValueError):
        decompose(-1)


def test_every_number_has_a_glyph_definition(digits_spec_path) -> None:
    spec = load_digit_spec(digits_spec_path)
    glyphs = build_precomposed_glyphs(spec, numbers=range(10000))
    for n in range(10000):
        assert precomposed_glyph_name(n) in glyphs


def test_full_font_has_a_cmap_entry_for_every_number(full_ttf: TTFont) -> None:
    best = full_ttf["cmap"].getBestCmap()
    for n in range(10000):
        assert (0xF0000 + n) in best
        assert best[0xF0000 + n] == precomposed_glyph_name(n)


def test_full_font_glyph_order_has_no_duplicates(full_ttf: TTFont) -> None:
    order = full_ttf.getGlyphOrder()
    assert len(order) == len(set(order))
