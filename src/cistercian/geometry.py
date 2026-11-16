"""Turn the digit spec into filled outlines.

Coordinates are font units (y-up), on the grid documented in ``spec/digits.json``
(``upm`` units per em). This module has no fontTools imports so it can be tested
on its own: it only produces plain point lists and :mod:`shapely` geometries.

Each digit (1-9) is specified in a local "quadrant" frame: ``u`` runs from 0 (at
the stave) to 1 (the outer edge), and ``v`` runs from 0 (the far end of the
quadrant, away from the stave's midpoint) to 1 (the near end, at the
midpoint). The four places place that frame on the stave with a mirror and/or
flip:

- units: top-right, no mirror, no flip.
- tens: top-left, mirrored left-right (reflection of units).
- hundreds: bottom-right, flipped top-bottom (reflection of units).
- thousands: bottom-left, both mirrored and flipped.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import jsonschema
from shapely.affinity import affine_transform
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from cistercian.errors import SpecError

Place = Literal["units", "tens", "hundreds", "thousands"]
PLACES: tuple[Place, ...] = ("units", "tens", "hundreds", "thousands")

_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "spec"
    / "schema"
    / "digits.schema.json"
)


@dataclass(frozen=True)
class Stave:
    """The vertical stave's x position and its top/bottom y extent."""

    x: float
    y_top: float
    y_bottom: float


@dataclass(frozen=True)
class Quadrant:
    """The size of one quadrant's local (u, v) box, in font units."""

    width: float
    height: float


@dataclass(frozen=True)
class DigitShape:
    """One digit's geometry: one or more stroked polylines.

    A polyline with 3+ points is buffered as a single stroke, so shapely
    gives its interior bends a clean mitred join; segments that do not
    connect to one another are separate (shorter) polylines in the list.
    """

    segments: tuple[tuple[tuple[float, float], ...], ...]


@dataclass(frozen=True)
class DigitSpec:
    """The parsed, validated contents of ``spec/digits.json``."""

    upm: int
    advance_width: int
    stroke_width: float
    stave: Stave
    quadrant: Quadrant
    digits: dict[str, DigitShape]


def load_digit_spec(path: str | Path) -> DigitSpec:
    """Load and validate ``digits.json``.

    Args:
        path: Path to the spec file.

    Returns:
        The parsed spec.

    Raises:
        SpecError: The file is missing, is not valid JSON, or fails the schema.
    """
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SpecError(f"{path}: file not found") from exc
    except json.JSONDecodeError as exc:
        raise SpecError(f"{path}: invalid JSON ({exc})") from exc

    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(raw, schema)
    except jsonschema.ValidationError as exc:
        raise SpecError(f"{path}: {exc.message} at {list(exc.absolute_path)}") from exc

    digits: dict[str, DigitShape] = {}
    for key, value in raw["digits"].items():
        segments = tuple(
            tuple((float(x), float(y)) for x, y in segment)
            for segment in value["segments"]
        )
        digits[key] = DigitShape(segments=segments)

    return DigitSpec(
        upm=raw["upm"],
        advance_width=raw["advance_width"],
        stroke_width=raw["stroke_width"],
        stave=Stave(
            x=raw["stave"]["x"],
            y_top=raw["stave"]["y_top"],
            y_bottom=raw["stave"]["y_bottom"],
        ),
        quadrant=Quadrant(
            width=raw["quadrant"]["width"], height=raw["quadrant"]["height"]
        ),
        digits=digits,
    )


def _stroke_polyline(points: tuple[tuple[float, float], ...], width: float) -> Polygon:
    """Turn a polyline into a filled stroke outline (flat caps, mitred joins)."""
    from shapely.geometry import LineString

    return LineString(points).buffer(width / 2, cap_style="flat", join_style="mitre")


def build_stave_polygon(spec: DigitSpec) -> BaseGeometry:
    """Build the bare vertical stave, in absolute font coordinates."""
    stave = spec.stave
    return _stroke_polyline(
        ((stave.x, stave.y_bottom), (stave.x, stave.y_top)), spec.stroke_width
    )


def _build_digit_local(digit: str, spec: DigitSpec) -> BaseGeometry | None:
    """Build one digit's shape in local (u, v) units, scaled to the quadrant size.

    Returns None for digit "0" (no mark).
    """
    shape = spec.digits[digit]
    width, height = spec.quadrant.width, spec.quadrant.height

    def scale(point: tuple[float, float]) -> tuple[float, float]:
        u, v = point
        return (u * width, v * height)

    if not shape.segments:
        return None

    polygons = [
        _stroke_polyline(tuple(scale(p) for p in segment), spec.stroke_width)
        for segment in shape.segments
    ]
    merged = unary_union(polygons)
    return merged if merged.is_empty else orient_geometry(merged)


def orient_geometry(geom: BaseGeometry) -> BaseGeometry:
    """Apply the TrueType winding convention (CW exterior, CCW holes) to a geometry."""
    if isinstance(geom, Polygon):
        return orient(geom, sign=-1.0)
    if isinstance(geom, MultiPolygon):
        return MultiPolygon([orient(p, sign=-1.0) for p in geom.geoms])
    return geom


def _place_transform(
    place: Place, spec: DigitSpec
) -> tuple[float, float, float, float, float, float]:
    """The affine matrix [a, b, d, e, xoff, yoff] mapping local (u*w, v*h)
    onto the stave.

    ``v=0``'s anchor (``yoff``) is inset from the stave's actual tip by half
    the stroke width, not placed exactly on it: a mark's ``v=0`` end is
    itself a stroke of that width, so anchoring it exactly at the tip would
    let the stroke's far half overshoot past the stave's own flat end cap
    (visible as a stray sliver, worst for a diagonal, whose corner pokes out
    at an angle instead of straight up). Insetting keeps every ``v=0`` mark
    flush with, not beyond, the stave's cap.
    """
    stave = spec.stave
    inset = spec.stroke_width / 2
    sx = 1.0 if place in ("units", "hundreds") else -1.0
    if place in ("units", "tens"):
        sy, yoff = -1.0, stave.y_top - inset
    else:
        sy, yoff = 1.0, stave.y_bottom + inset
    return (sx, 0.0, 0.0, sy, stave.x, yoff)


def build_quadrant_polygon(
    digit: str, place: Place, spec: DigitSpec
) -> BaseGeometry | None:
    """Build one digit's mark at one place on the stave, in absolute font coordinates.

    Returns None for digit "0" (an empty corner has no mark).
    """
    local = _build_digit_local(digit, spec)
    if local is None or local.is_empty:
        return None
    placed = affine_transform(local, _place_transform(place, spec))
    return orient_geometry(placed)


def build_units_glyph_polygon(digit: str, spec: DigitSpec) -> BaseGeometry:
    """Build the base units glyph (U+EBA0-EBA9): the stave plus its corner mark."""
    stave = build_stave_polygon(spec)
    mark = build_quadrant_polygon(digit, "units", spec)
    if mark is None:
        return orient_geometry(stave)
    return orient_geometry(unary_union([stave, mark]))


def build_overlay_polygon(place: Place, digit: str, spec: DigitSpec) -> BaseGeometry:
    """Build a zero-advance overlay mark (tens/hundreds/thousands, digit 1-9)."""
    if digit == "0":
        raise SpecError("there is no overlay glyph for digit 0 (an empty corner)")
    if place == "units":
        raise SpecError("units has no overlay; it is part of the base glyph")
    mark = build_quadrant_polygon(digit, place, spec)
    assert mark is not None  # digit != "0" always yields a mark
    return mark


def polygon_rings(geom: BaseGeometry) -> list[list[tuple[int, int]]]:
    """Flatten a (Multi)Polygon into integer-rounded rings for pen drawing.

    Exterior rings keep TrueType's clockwise convention; interior rings (holes)
    stay counterclockwise. Call :func:`orient_geometry` first if the
    geometry's winding is not already known to be correct.
    """
    rings: list[list[tuple[int, int]]] = []
    polygons = geom.geoms if isinstance(geom, MultiPolygon) else [geom]
    for polygon in polygons:
        if polygon.is_empty:
            continue
        rings.append([(round(x), round(y)) for x, y in polygon.exterior.coords[:-1]])
        for interior in polygon.interiors:
            rings.append([(round(x), round(y)) for x, y in interior.coords[:-1]])
    return rings


def mirror_x(geom: BaseGeometry, x: float) -> BaseGeometry:
    """Mirror a geometry left-right across the vertical line ``x`` (symmetry tests)."""
    return affine_transform(geom, (-1.0, 0.0, 0.0, 1.0, 2 * x, 0.0))


def flip_y(geom: BaseGeometry, y: float) -> BaseGeometry:
    """Flip a geometry top-bottom across the horizontal line ``y`` (symmetry tests)."""
    return affine_transform(geom, (1.0, 0.0, 0.0, -1.0, 0.0, 2 * y))


__all__ = [
    "PLACES",
    "DigitShape",
    "DigitSpec",
    "Place",
    "Quadrant",
    "Stave",
    "build_overlay_polygon",
    "build_quadrant_polygon",
    "build_stave_polygon",
    "build_units_glyph_polygon",
    "flip_y",
    "load_digit_spec",
    "mirror_x",
    "orient_geometry",
    "polygon_rings",
]
