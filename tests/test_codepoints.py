"""All component glyphs exist at the right code points."""

from __future__ import annotations

from cistercian.glyphs import (
    HUNDREDS_BASE,
    PRECOMPOSED_BASE,
    TENS_BASE,
    THOUSANDS_BASE,
    UNITS_BASE,
    build_cmap,
    overlay_codepoint,
    overlay_glyph_name,
    precomposed_codepoint,
    precomposed_glyph_name,
    units_codepoint,
    units_glyph_name,
)


def test_units_base_is_eba0() -> None:
    assert UNITS_BASE == 0xEBA0


def test_tens_base_is_ebb1() -> None:
    assert TENS_BASE == 0xEBB1


def test_hundreds_base_is_ebc1() -> None:
    assert HUNDREDS_BASE == 0xEBC1


def test_thousands_base_is_ebd1() -> None:
    assert THOUSANDS_BASE == 0xEBD1


def test_precomposed_base_is_f0000() -> None:
    assert PRECOMPOSED_BASE == 0xF0000


def test_units_codepoints_span_eba0_to_eba9() -> None:
    assert [units_codepoint(d) for d in range(10)] == list(range(0xEBA0, 0xEBAA))


def test_overlay_codepoints_skip_zero() -> None:
    for place, base in (("tens", 0xEBB1), ("hundreds", 0xEBC1), ("thousands", 0xEBD1)):
        assert [overlay_codepoint(place, d) for d in range(1, 10)] == list(
            range(base, base + 9)
        )


def test_precomposed_codepoint_9230_matches_wikipedia_example() -> None:
    assert precomposed_codepoint(9230) == 0xF0000 + 9230


def test_cmap_maps_every_component_codepoint_to_its_glyph() -> None:
    cmap = build_cmap(numbers=range(1))
    for digit in range(10):
        assert cmap[units_codepoint(digit)] == units_glyph_name(digit)
    for place in ("tens", "hundreds", "thousands"):
        for digit in range(1, 10):
            assert cmap[overlay_codepoint(place, digit)] == overlay_glyph_name(
                place, digit
            )  # type: ignore[arg-type]


def test_cmap_maps_precomposed_codepoints_in_range() -> None:
    cmap = build_cmap(numbers=range(5))
    for n in range(5):
        assert cmap[precomposed_codepoint(n)] == precomposed_glyph_name(n)
    assert precomposed_codepoint(5) not in cmap
