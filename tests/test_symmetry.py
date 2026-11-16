"""Corner reflections are symmetric: tens/hundreds/thousands mirror/flip units.

These checks mirror or flip the units-corner mark independently of the
production transform in ``geometry.build_quadrant_polygon``, so they catch a
bug in that transform rather than reproducing it.
"""

from __future__ import annotations

import pytest

from cistercian.errors import SpecError
from cistercian.geometry import (
    build_overlay_polygon,
    build_quadrant_polygon,
    flip_y,
    load_digit_spec,
    mirror_x,
)


def _assert_same_shape(a, b, tolerance: float = 1e-6) -> None:
    assert a.symmetric_difference(b).area < tolerance


@pytest.mark.parametrize("digit", range(1, 10))
def test_tens_mirrors_units_across_the_stave(digits_spec_path, digit: int) -> None:
    spec = load_digit_spec(digits_spec_path)
    units = build_quadrant_polygon(str(digit), "units", spec)
    tens = build_quadrant_polygon(str(digit), "tens", spec)
    _assert_same_shape(mirror_x(units, spec.stave.x), tens)


@pytest.mark.parametrize("digit", range(1, 10))
def test_hundreds_flips_units_across_the_stave_midpoint(
    digits_spec_path, digit: int
) -> None:
    spec = load_digit_spec(digits_spec_path)
    units = build_quadrant_polygon(str(digit), "units", spec)
    hundreds = build_quadrant_polygon(str(digit), "hundreds", spec)
    y_mid = (spec.stave.y_top + spec.stave.y_bottom) / 2
    _assert_same_shape(flip_y(units, y_mid), hundreds)


@pytest.mark.parametrize("digit", range(1, 10))
def test_thousands_mirrors_and_flips_units(digits_spec_path, digit: int) -> None:
    spec = load_digit_spec(digits_spec_path)
    units = build_quadrant_polygon(str(digit), "units", spec)
    thousands = build_quadrant_polygon(str(digit), "thousands", spec)
    y_mid = (spec.stave.y_top + spec.stave.y_bottom) / 2
    reflected = flip_y(mirror_x(units, spec.stave.x), y_mid)
    _assert_same_shape(reflected, thousands)


def test_digit_zero_has_no_mark_at_any_place(digits_spec_path) -> None:
    spec = load_digit_spec(digits_spec_path)
    for place in ("units", "tens", "hundreds", "thousands"):
        assert build_quadrant_polygon("0", place, spec) is None


def test_overlay_glyph_for_digit_zero_is_rejected(digits_spec_path) -> None:
    spec = load_digit_spec(digits_spec_path)
    for place in ("tens", "hundreds", "thousands"):
        with pytest.raises(SpecError):
            build_overlay_polygon(place, "0", spec)
