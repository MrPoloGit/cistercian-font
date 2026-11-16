"""Overlays have zero advance; units glyphs and precomposed glyphs do not."""

from __future__ import annotations

from cistercian.geometry import load_digit_spec
from cistercian.glyphs import (
    build_overlay_glyphs,
    build_precomposed_glyphs,
    build_unit_glyphs,
)


def test_overlay_glyphs_have_zero_advance_width(digits_spec_path) -> None:
    spec = load_digit_spec(digits_spec_path)
    for glyph_def in build_overlay_glyphs(spec).values():
        assert glyph_def.advance_width == 0


def test_units_glyphs_have_the_full_advance_width(digits_spec_path) -> None:
    spec = load_digit_spec(digits_spec_path)
    for glyph_def in build_unit_glyphs(spec).values():
        assert glyph_def.advance_width == spec.advance_width


def test_precomposed_glyphs_have_the_full_advance_width(digits_spec_path) -> None:
    spec = load_digit_spec(digits_spec_path)
    for glyph_def in build_precomposed_glyphs(spec, numbers=range(50)).values():
        assert glyph_def.advance_width == spec.advance_width


def test_overlay_glyphs_have_a_mark_outline_for_every_nonzero_digit(
    digits_spec_path,
) -> None:
    spec = load_digit_spec(digits_spec_path)
    overlays = build_overlay_glyphs(spec)
    assert len(overlays) == 3 * 9  # tens/hundreds/thousands x digits 1-9
    for glyph_def in overlays.values():
        assert glyph_def.contours is not None
        assert len(glyph_def.contours) > 0
