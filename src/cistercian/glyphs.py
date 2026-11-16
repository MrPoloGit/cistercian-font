"""Glyph names, code points, and glyph definitions (outlines or composites).

Code points follow the UCSUR proposal (Hardy & Bettencourt, 2020). Glyph names
follow one scheme, generated only by the helpers below, never typed by hand:

- ``cistercian.units.N``, ``cistercian.tens.N``, ``cistercian.hundreds.N``,
  ``cistercian.thousands.N`` for the component glyphs (``N`` is a bare digit).
- ``cistercian.num.NNNN`` for the precomposed glyphs (``NNNN`` is zero-padded).
"""

from __future__ import annotations

from dataclasses import dataclass

from cistercian.errors import SpecError
from cistercian.geometry import (
    PLACES,
    DigitSpec,
    Place,
    build_overlay_polygon,
    build_units_glyph_polygon,
    polygon_rings,
)

# UCSUR Cistercian numerals block.
UNITS_BASE = 0xEBA0  # 0xEBA0-0xEBA9: units 0-9 (0xEBA0 is the bare stave).
TENS_BASE = 0xEBB1  # 0xEBB1-0xEBB9: tens 1-9, zero-advance overlay.
HUNDREDS_BASE = 0xEBC1  # 0xEBC1-0xEBC9: hundreds 1-9, zero-advance overlay.
THOUSANDS_BASE = 0xEBD1  # 0xEBD1-0xEBD9: thousands 1-9, zero-advance overlay.

# Precomposed glyphs for every number 0-9999, in Supplementary PUA-A.
PRECOMPOSED_BASE = 0xF0000

_OVERLAY_BASE = {
    "tens": TENS_BASE,
    "hundreds": HUNDREDS_BASE,
    "thousands": THOUSANDS_BASE,
}


def units_glyph_name(digit: int) -> str:
    """Glyph name for a units base glyph (digit 0-9)."""
    return f"cistercian.units.{digit}"


def overlay_glyph_name(place: Place, digit: int) -> str:
    """Glyph name for an overlay glyph (place in tens/hundreds/thousands, digit 1-9)."""
    return f"cistercian.{place}.{digit}"


def precomposed_glyph_name(number: int) -> str:
    """Glyph name for the precomposed glyph for a number 0-9999."""
    return f"cistercian.num.{number:04d}"


def units_codepoint(digit: int) -> int:
    """Code point for a units base glyph (digit 0-9)."""
    return UNITS_BASE + digit


def overlay_codepoint(place: Place, digit: int) -> int:
    """Code point for an overlay glyph (place in tens/hundreds/thousands, digit 1-9)."""
    return _OVERLAY_BASE[place] + (digit - 1)


def precomposed_codepoint(number: int) -> int:
    """Code point for the precomposed glyph for a number 0-9999."""
    return PRECOMPOSED_BASE + number


@dataclass(frozen=True)
class Component:
    """A reference to another glyph, placed at an offset (always (0, 0) here)."""

    glyph_name: str
    dx: int = 0
    dy: int = 0


@dataclass(frozen=True)
class GlyphDef:
    """One glyph: either an outline (contours) or a composite (components), not both."""

    name: str
    advance_width: int
    contours: tuple[tuple[tuple[int, int], ...], ...] | None = None
    components: tuple[Component, ...] | None = None

    def __post_init__(self) -> None:
        if (self.contours is None) == (self.components is None):
            raise SpecError(
                f"glyph {self.name}: must have exactly one of contours or components"
            )


def build_unit_glyphs(spec: DigitSpec) -> dict[str, GlyphDef]:
    """Build the 10 base units glyphs (stave + units-corner mark), digits 0-9."""
    glyphs: dict[str, GlyphDef] = {}
    for digit in range(10):
        polygon = build_units_glyph_polygon(str(digit), spec)
        rings = tuple(tuple(ring) for ring in polygon_rings(polygon))
        name = units_glyph_name(digit)
        glyphs[name] = GlyphDef(
            name=name, advance_width=spec.advance_width, contours=rings
        )
    return glyphs


def build_overlay_glyphs(spec: DigitSpec) -> dict[str, GlyphDef]:
    """Build the 27 zero-advance overlay glyphs: tens/hundreds/thousands x 1-9."""
    glyphs: dict[str, GlyphDef] = {}
    for place in PLACES:
        if place == "units":
            continue
        for digit in range(1, 10):
            polygon = build_overlay_polygon(place, str(digit), spec)
            rings = tuple(tuple(ring) for ring in polygon_rings(polygon))
            name = overlay_glyph_name(place, digit)
            glyphs[name] = GlyphDef(name=name, advance_width=0, contours=rings)
    return glyphs


def decompose(number: int) -> tuple[int, int, int, int]:
    """Split a number 0-9999 into (units, tens, hundreds, thousands) digits.

    Raises:
        ValueError: ``number`` is outside 0-9999.
    """
    if not 0 <= number <= 9999:
        raise ValueError(f"{number} is outside the 0-9999 range this font supports")
    return (
        number % 10,
        (number // 10) % 10,
        (number // 100) % 10,
        (number // 1000) % 10,
    )


def build_precomposed_glyph(number: int, spec: DigitSpec) -> GlyphDef:
    """Build one precomposed composite glyph for a number 0-9999.

    It references the units base glyph plus an overlay component per nonzero
    tens/hundreds/thousands digit, all at offset (0, 0): overlay outlines are
    already in the same absolute coordinate space as the units stave.
    """
    units, tens, hundreds, thousands = decompose(number)
    components = [Component(units_glyph_name(units))]
    for place, digit in (
        ("tens", tens),
        ("hundreds", hundreds),
        ("thousands", thousands),
    ):
        if digit:
            components.append(Component(overlay_glyph_name(place, digit)))  # type: ignore[arg-type]
    name = precomposed_glyph_name(number)
    return GlyphDef(
        name=name, advance_width=spec.advance_width, components=tuple(components)
    )


def build_precomposed_glyphs(
    spec: DigitSpec, numbers: range | None = None
) -> dict[str, GlyphDef]:
    """Build precomposed composite glyphs for ``numbers`` (default: all of 0-9999)."""
    numbers = numbers if numbers is not None else range(10000)
    return {
        precomposed_glyph_name(n): build_precomposed_glyph(n, spec) for n in numbers
    }


def rescale_glyph(glyph: GlyphDef, scale: float) -> GlyphDef:
    """Return a copy of ``glyph`` rescaled from this package's upm to another upm.

    Used by ``--merge`` to fit a base font's units-per-em.
    """
    advance_width = round(glyph.advance_width * scale)
    if glyph.contours is not None:
        contours = tuple(
            tuple((round(x * scale), round(y * scale)) for x, y in ring)
            for ring in glyph.contours
        )
        return GlyphDef(name=glyph.name, advance_width=advance_width, contours=contours)
    assert glyph.components is not None
    components = tuple(
        Component(c.glyph_name, round(c.dx * scale), round(c.dy * scale))
        for c in glyph.components
    )
    return GlyphDef(name=glyph.name, advance_width=advance_width, components=components)


def build_cmap(numbers: range | None = None) -> dict[int, str]:
    """Build the full cmap: component code points plus precomposed code points.

    Args:
        numbers: which precomposed numbers to include (default: all of 0-9999),
            matching the ``--no-precomposed`` build option.
    """
    cmap: dict[int, str] = {}
    for digit in range(10):
        cmap[units_codepoint(digit)] = units_glyph_name(digit)
    for place in ("tens", "hundreds", "thousands"):
        for digit in range(1, 10):
            cmap[overlay_codepoint(place, digit)] = overlay_glyph_name(place, digit)
    for n in numbers if numbers is not None else range(10000):
        cmap[precomposed_codepoint(n)] = precomposed_glyph_name(n)
    return cmap


__all__ = [
    "HUNDREDS_BASE",
    "PRECOMPOSED_BASE",
    "TENS_BASE",
    "THOUSANDS_BASE",
    "UNITS_BASE",
    "Component",
    "GlyphDef",
    "build_cmap",
    "build_overlay_glyphs",
    "build_precomposed_glyph",
    "build_precomposed_glyphs",
    "build_unit_glyphs",
    "decompose",
    "overlay_codepoint",
    "overlay_glyph_name",
    "precomposed_codepoint",
    "precomposed_glyph_name",
    "rescale_glyph",
    "units_codepoint",
    "units_glyph_name",
]
