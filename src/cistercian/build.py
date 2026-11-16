"""Assemble the Cistercian font: cmap, glyf, metrics, GDEF, and ss01/ss02/rlig.

Builds a TrueType (composite glyphs) and/or CFF/OTF (flattened outlines,
since CFF has no composites) font object from the glyph definitions in
:mod:`cistercian.glyphs`, then exports TTF, OTF and WOFF2.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.fontBuilder import FontBuilder
from fontTools.misc.timeTools import timestampSinceEpoch
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from cistercian.features import (
    build_rlig_fea,
    build_ss01_fea,
    build_ss02_fea,
    load_letter_spec,
)
from cistercian.geometry import load_digit_spec
from cistercian.glyphs import (
    GlyphDef,
    build_cmap,
    build_overlay_glyphs,
    build_precomposed_glyphs,
    build_unit_glyphs,
)

FAMILY_NAME = "Cistercian"
NOTDEF = ".notdef"


def _ordered_glyph_set(
    spec_path: str | Path, letter_path: str | Path, numbers: range | None
) -> tuple[dict[str, GlyphDef], dict[int, str], list[str]]:
    digit_spec = load_digit_spec(spec_path)
    load_letter_spec(letter_path)  # discarded: only its validation matters here

    glyphs: dict[str, GlyphDef] = {}
    glyphs.update(build_unit_glyphs(digit_spec))
    glyphs.update(build_overlay_glyphs(digit_spec))
    glyphs.update(build_precomposed_glyphs(digit_spec, numbers))

    glyph_order = [NOTDEF, *sorted(glyphs)]
    cmap = build_cmap(numbers)
    return glyphs, cmap, glyph_order


def _draw_simple(
    pen: object, contours: tuple[tuple[tuple[int, int], ...], ...]
) -> None:
    for ring in contours:
        pen.moveTo(ring[0])  # type: ignore[attr-defined]
        for point in ring[1:]:
            pen.lineTo(point)  # type: ignore[attr-defined]
        pen.closePath()  # type: ignore[attr-defined]


def _flatten(
    glyph: GlyphDef, glyphs: dict[str, GlyphDef]
) -> tuple[tuple[tuple[int, int], ...], ...]:
    """Resolve a (possibly composite) glyph into a flat tuple of contours."""
    if glyph.contours is not None:
        return glyph.contours
    assert glyph.components is not None
    contours: list[tuple[tuple[int, int], ...]] = []
    for component in glyph.components:
        part = glyphs[component.glyph_name]
        for ring in _flatten(part, glyphs):
            contours.append(
                tuple((x + component.dx, y + component.dy) for x, y in ring)
            )
    return tuple(contours)


def _lsb(contours: tuple[tuple[tuple[int, int], ...], ...]) -> int:
    xs = [x for ring in contours for x, _ in ring]
    return min(xs) if xs else 0


def _feature_text(
    glyphs: dict[str, GlyphDef],
    digit_spec_path: str | Path,
    letter_spec_path: str | Path,
    numbers: range | None,
    cmap_for_ss: dict[int, str] | None,
) -> str:
    digit_spec = load_digit_spec(digit_spec_path)
    letter_spec = load_letter_spec(letter_spec_path)

    overlay_names = [name for name, g in glyphs.items() if g.advance_width == 0]
    gdef = "table GDEF {\n"
    for name in sorted(overlay_names):
        gdef += f"    GlyphClassDef , , [{name}], ;\n"
    gdef += "} GDEF;\n"

    parts = [gdef, build_rlig_fea(digit_spec, numbers)]
    if cmap_for_ss is not None:
        parts.append(build_ss01_fea(cmap_for_ss, numbers))
        parts.append(build_ss02_fea(letter_spec, cmap_for_ss, numbers))
    return "\n".join(parts)


def build_ttf(
    digit_spec_path: str | Path,
    letter_spec_path: str | Path,
    *,
    numbers: range | None = None,
    include_ss_features: bool = False,
    version: str = "0.1.0",
) -> TTFont:
    """Build the TrueType (composite-glyph) font.

    Args:
        digit_spec_path: Path to ``spec/digits.json``.
        letter_spec_path: Path to ``spec/letters.json``.
        numbers: Which precomposed numbers to build (default: all of 0-9999).
        include_ss_features: Include ``ss01``/``ss02``. Only valid once the
            font also has ASCII digit and Latin letter glyphs in its cmap
            (true for ``--merge``, not for the bare standalone font).
        version: Font version, written into the name table.
    """
    glyphs, cmap, glyph_order = _ordered_glyph_set(
        digit_spec_path, letter_spec_path, numbers
    )
    digit_spec = load_digit_spec(digit_spec_path)

    fb = FontBuilder(digit_spec.upm, isTTF=True)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(cmap)

    glyf: dict[str, object] = {NOTDEF: TTGlyphPen(None).glyph()}
    metrics: dict[str, tuple[int, int]] = {NOTDEF: (digit_spec.advance_width, 0)}

    def add(name: str, glyph_def: GlyphDef) -> None:
        pen = TTGlyphPen(glyf)
        if glyph_def.contours is not None:
            _draw_simple(pen, glyph_def.contours)
            lsb = _lsb(glyph_def.contours)
        else:
            assert glyph_def.components is not None
            for component in glyph_def.components:
                pen.addComponent(
                    component.glyph_name, (1, 0, 0, 1, component.dx, component.dy)
                )
            lsb = _lsb(_flatten(glyph_def, glyphs))
        glyf[name] = pen.glyph()
        metrics[name] = (glyph_def.advance_width, lsb)

    # Units and overlays first (precomposed composites reference them).
    for name, glyph_def in glyphs.items():
        if glyph_def.contours is not None:
            add(name, glyph_def)
    for name, glyph_def in glyphs.items():
        if glyph_def.components is not None:
            add(name, glyph_def)

    fb.setupGlyf(glyf)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=digit_spec.upm, descent=0)
    fb.setupOS2(
        sTypoAscender=digit_spec.upm,
        sTypoDescender=0,
        usWinAscent=digit_spec.upm,
        usWinDescent=0,
    )
    fb.setupNameTable(
        {
            "familyName": FAMILY_NAME,
            "styleName": "Regular",
            "version": f"Version {version}",
        }
    )
    fb.setupPost()

    feature_text = _feature_text(
        glyphs,
        digit_spec_path,
        letter_spec_path,
        numbers,
        cmap if include_ss_features else None,
    )
    addOpenTypeFeaturesFromString(fb.font, feature_text)

    _set_deterministic_timestamp(fb.font)
    return fb.font


def build_otf(
    digit_spec_path: str | Path,
    letter_spec_path: str | Path,
    *,
    numbers: range | None = None,
    include_ss_features: bool = False,
    version: str = "0.1.0",
) -> TTFont:
    """Build the CFF/OTF font, with composites flattened into plain outlines."""
    glyphs, cmap, glyph_order = _ordered_glyph_set(
        digit_spec_path, letter_spec_path, numbers
    )
    digit_spec = load_digit_spec(digit_spec_path)

    fb = FontBuilder(digit_spec.upm, isTTF=False)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(cmap)

    charstrings: dict[str, object] = {}
    metrics: dict[str, tuple[int, int]] = {}
    for name, glyph_def in glyphs.items():
        contours = _flatten(glyph_def, glyphs)
        pen = T2CharStringPen(glyph_def.advance_width, None)
        _draw_simple(pen, contours)
        charstrings[name] = pen.getCharString()
        metrics[name] = (glyph_def.advance_width, _lsb(contours))
    notdef_pen = T2CharStringPen(digit_spec.advance_width, None)
    charstrings[NOTDEF] = notdef_pen.getCharString()
    metrics[NOTDEF] = (digit_spec.advance_width, 0)

    fb.setupCFF(FAMILY_NAME, {"FullName": FAMILY_NAME}, charstrings, {})
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=digit_spec.upm, descent=0)
    fb.setupOS2(
        sTypoAscender=digit_spec.upm,
        sTypoDescender=0,
        usWinAscent=digit_spec.upm,
        usWinDescent=0,
    )
    fb.setupNameTable(
        {
            "familyName": FAMILY_NAME,
            "styleName": "Regular",
            "version": f"Version {version}",
        }
    )
    fb.setupPost()

    feature_text = _feature_text(
        glyphs,
        digit_spec_path,
        letter_spec_path,
        numbers,
        cmap if include_ss_features else None,
    )
    addOpenTypeFeaturesFromString(fb.font, feature_text)

    _set_deterministic_timestamp(fb.font)
    return fb.font


def _set_deterministic_timestamp(font: TTFont) -> None:
    """Pin head.created/modified to SOURCE_DATE_EPOCH, if set (reproducible builds)."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    when = int(epoch) if epoch else int(time.time())
    stamp = timestampSinceEpoch(when)
    font["head"].created = stamp
    font["head"].modified = stamp


def save_woff2(font: TTFont, path: str | Path) -> None:
    """Save ``font`` as a WOFF2 file at ``path``, leaving ``font.flavor`` as it was."""
    original_flavor = font.flavor
    try:
        font.flavor = "woff2"
        font.save(str(path))
    finally:
        font.flavor = original_flavor


def build_all(
    digit_spec_path: str | Path,
    letter_spec_path: str | Path,
    out_dir: str | Path,
    *,
    numbers: range | None = None,
    include_ss_features: bool = False,
    version: str = "0.1.0",
) -> dict[str, Path]:
    """Build and write ``Cistercian-Regular.{ttf,otf,woff2}`` into ``out_dir``."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ttf = build_ttf(
        digit_spec_path,
        letter_spec_path,
        numbers=numbers,
        include_ss_features=include_ss_features,
        version=version,
    )
    otf = build_otf(
        digit_spec_path,
        letter_spec_path,
        numbers=numbers,
        include_ss_features=include_ss_features,
        version=version,
    )

    ttf_path = out_dir / "Cistercian-Regular.ttf"
    otf_path = out_dir / "Cistercian-Regular.otf"
    woff2_path = out_dir / "Cistercian-Regular.woff2"

    ttf.save(str(ttf_path))
    otf.save(str(otf_path))
    save_woff2(ttf, woff2_path)

    return {"ttf": ttf_path, "otf": otf_path, "woff2": woff2_path}


__all__ = ["build_all", "build_otf", "build_ttf", "save_woff2"]
