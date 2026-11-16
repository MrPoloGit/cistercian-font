"""``--merge``: add the Cistercian glyphs and feature rules to a base font.

Only a TrueType (``glyf``-based) base font is supported: composites need a
``glyf`` table, and a CFF/OTF base would need every precomposed glyph
flattened and re-inserted into the CFF charstrings index instead.
"""

from __future__ import annotations

from pathlib import Path

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.fontBuilder import buildCmapSubTable
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable

from cistercian.build import _draw_simple, _feature_text, _flatten, _lsb
from cistercian.errors import MergeError
from cistercian.geometry import load_digit_spec
from cistercian.glyphs import (
    GlyphDef,
    build_cmap,
    build_overlay_glyphs,
    build_precomposed_glyphs,
    build_unit_glyphs,
    rescale_glyph,
)

_RESTRICTED_LICENSE_EMBEDDING = 0x0002  # OS/2.fsType bit 1


def _check_license(base: TTFont, base_path: str | Path) -> None:
    os2 = base.get("OS/2", None)
    if os2 is not None and getattr(os2, "fsType", 0) & _RESTRICTED_LICENSE_EMBEDDING:
        raise MergeError(
            f"{base_path}: fsType 0x{os2.fsType:04x} forbids modification "
            "(restricted-license embedding bit is set)"
        )


def _rebuild_cmap(font: TTFont, cmapping: dict[int, str]) -> None:
    highest = max(cmapping) if cmapping else 0
    subtables = []
    if highest > 0xFFFF:
        bmp = {k: v for k, v in cmapping.items() if k < 0x10000}
        subtables.append(buildCmapSubTable(cmapping, 12, 3, 10))
    else:
        bmp = cmapping
    subtables.append(buildCmapSubTable(bmp, 4, 3, 1))
    subtables.append(buildCmapSubTable(bmp, 4, 0, 3))
    cmap = newTable("cmap")
    cmap.tableVersion = 0
    cmap.tables = subtables
    font["cmap"] = cmap


def merge_font(
    base_path: str | Path,
    out_path: str | Path,
    digit_spec_path: str | Path,
    letter_spec_path: str | Path,
    *,
    numbers: range | None = None,
) -> TTFont:
    """Merge the Cistercian glyphs and features into a copy of a base font.

    Args:
        base_path: The base font to merge into (read, never modified in place).
        out_path: Where to write the merged font.
        digit_spec_path: Path to ``spec/digits.json``.
        letter_spec_path: Path to ``spec/letters.json``.
        numbers: Which precomposed numbers to add (default: all of 0-9999).

    Raises:
        MergeError: The base font has no ``glyf`` table, or its licence
            (``OS/2.fsType``) forbids modification.
    """
    base = TTFont(base_path)
    _check_license(base, base_path)
    if "glyf" not in base:
        raise MergeError(
            f"{base_path}: only TrueType (glyf) base fonts are supported in v1"
        )

    digit_spec = load_digit_spec(digit_spec_path)
    base_upm = base["head"].unitsPerEm
    scale = base_upm / digit_spec.upm

    base_cmap = base["cmap"].getBestCmap()

    glyphs: dict[str, GlyphDef] = {}
    glyphs.update(build_unit_glyphs(digit_spec))
    glyphs.update(build_overlay_glyphs(digit_spec))
    glyphs.update(build_precomposed_glyphs(digit_spec, numbers))
    glyphs = {name: rescale_glyph(g, scale) for name, g in glyphs.items()}

    existing_names = set(base.getGlyphOrder())
    new_names = [n for n in sorted(glyphs) if n not in existing_names]
    base.setGlyphOrder([*base.getGlyphOrder(), *new_names])

    glyf = base["glyf"]
    hmtx = base["hmtx"]
    simple_first = [n for n in new_names if glyphs[n].contours is not None]
    composite_next = [n for n in new_names if glyphs[n].components is not None]
    for name in simple_first + composite_next:
        glyph_def = glyphs[name]
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
        hmtx[name] = (glyph_def.advance_width, lsb)

    merged_cmap = {**base_cmap, **build_cmap(numbers)}
    _rebuild_cmap(base, merged_cmap)

    feature_text = _feature_text(
        glyphs, digit_spec_path, letter_spec_path, numbers, base_cmap
    )
    addOpenTypeFeaturesFromString(base, feature_text)

    base.save(str(out_path))
    return base


__all__ = ["merge_font"]
