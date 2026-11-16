"""Render a contact sheet of glyphs as SVG, for visual checking.

Draws each requested precomposed glyph's outline (resolved through the glyf
table, so composites are handled automatically) into a labelled grid cell.
"""

from __future__ import annotations

from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

from cistercian.glyphs import precomposed_glyph_name

CELL_SIZE = 120
PADDING = 10


def render_contact_sheet(font: TTFont, numbers: list[int], columns: int = 10) -> str:
    """Render ``numbers`` (each 0-9999) from ``font`` as an SVG contact sheet.

    Args:
        font: A font built by :func:`cistercian.build.build_ttf` (or any font
            whose glyph set includes the requested precomposed glyphs).
        numbers: Which numbers to render, in order.
        columns: How many cells per row.

    Returns:
        A standalone SVG document as a string.
    """
    upm = font["head"].unitsPerEm
    glyph_set = font.getGlyphSet()
    rows = (len(numbers) + columns - 1) // columns
    width = columns * CELL_SIZE
    height = rows * CELL_SIZE
    scale = (CELL_SIZE - 2 * PADDING) / upm

    cells = []
    for index, number in enumerate(numbers):
        col, row = index % columns, index // columns
        x = col * CELL_SIZE + PADDING
        y = row * CELL_SIZE + PADDING
        name = precomposed_glyph_name(number)
        pen = SVGPathPen(glyph_set)
        # Flip y (font space is y-up, SVG is y-down) and fit into the cell.
        transform = (scale, 0, 0, -scale, x, y + CELL_SIZE - 2 * PADDING)
        glyph_set[name].draw(TransformPen(pen, transform))
        path = pen.getCommands()
        label_y = row * CELL_SIZE + CELL_SIZE - 2
        label_x = col * CELL_SIZE + CELL_SIZE / 2
        cells.append(
            f'<path d="{path}" fill="#1a1a1a" />'
            f'<text x="{label_x}" y="{label_y}" font-size="9" '
            f'text-anchor="middle" fill="#666">{number}</text>'
        )

    body = "\n".join(cells)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        f'<rect width="{width}" height="{height}" fill="white" />\n{body}\n</svg>\n'
    )


def write_contact_sheet(font: TTFont, numbers: list[int], out_path: str | Path) -> None:
    """Render and write a contact sheet SVG to ``out_path``."""
    Path(out_path).write_text(render_contact_sheet(font, numbers), encoding="utf-8")


__all__ = ["render_contact_sheet", "write_contact_sheet"]
