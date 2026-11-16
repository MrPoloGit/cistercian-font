# Design

Visual design and geometry decisions. See `cistercian.geometry`'s module
docstring for the exact coordinate math.

## Stave and quadrants

The stave is a vertical stroke (`spec/digits.json`'s `stave.x`,
`stave.y_top`, `stave.y_bottom`). Each place value (units, tens, hundreds,
thousands) draws its digit mark in a quadrant box next to one end of the
stave:

- units: top-right.
- tens: top-left (mirror of units).
- hundreds: bottom-right (vertical flip of units).
- thousands: bottom-left (mirror and flip of units).

A digit's shape is specified once, in `spec/digits.json`, as a local
`(u, v)` frame (`u`: 0 at the stave to 1 at the outer edge; `v`: 0 at the far
end of the quadrant to 1 at the near end, towards the stave's midpoint).
`cistercian.geometry` places that local shape onto each of the four
quadrants with the matching mirror/flip, so there is exactly one source of
truth for every digit's shape — changing `spec/digits.json`'s `"3"` entry
changes the diagonal in all four places at once, and `tests/test_symmetry.py`
checks the mirror/flip relationship holds.

## Digit shapes

- **1**: horizontal stroke at the far end (`v=0`), touching the stave.
- **2**: horizontal stroke at the near end (`v=1`, the stave's midpoint),
  touching the stave.
- **3**: diagonal falling from the far stave corner (`v=0`) to the near outer
  corner (`v=1`).
- **4**: diagonal rising from the near stave corner (`v=1`) to the far outer
  corner (`v=0`).
- **5**: 4 plus 1 (one connected polyline: near stave corner (`v=1`) to the
  far outer corner (`v=0`) to the far stave corner (`v=0`)), stroked hollow
  like every other digit — not filled, unlike the font's original design.
- **6**: a vertical stroke at the outer edge, spanning the full quadrant
  height, not touching the stave.
- **7, 8, 9**: 6 combined with 1, 2, or both, each written as a single
  connected polyline (not separate touching segments) so shapely gives the
  shared corner a clean mitred join instead of a union seam.
- **0**: no mark (an empty corner, or the bare stave for the whole number 0).

Every stroke that touches the stave does so at `u=0`; see "Stave-flush
strokes" below for why `v=0` strokes are anchored slightly inside the
stave's tip rather than exactly on it.

## Stroke rendering

Every digit is specified as one or more straight polylines (`segments` in
`spec/digits.json`); `cistercian.geometry` turns each into a filled outline
via Shapely's `buffer()` (flat caps, mitred joins) at `stroke_width`, then
unions any separate polylines into a single outline per digit. This keeps
the spec purely geometric (points and a width), with no outline-fitting
logic duplicated per digit.

A digit whose strokes connect (7, 8, 9) is one polyline with 3+ points, not
several 2-point segments that happen to share an endpoint: buffering it in
one `buffer()` call lets Shapely's own mitred join handle the corner, instead
of unioning two independently flat-capped rectangles, which leaves a
stray triangular seam at the shared point whenever the two pieces meet at
anything other than a right angle.

### Stave-flush strokes

A stroke's `v=0` end sits at the stave's own tip (the quadrant's far
boundary is the stave's `y_top` or `y_bottom`). Naively anchoring `v=0`
exactly there is wrong: that end is itself a stroke of nonzero width, so its
far half — the half beyond the anchor point, in the direction the stave does
*not* extend — oversteps the stave's flat end cap. For an axis-aligned
stroke (digit 1) that is a clean 90° step, roughly as wide as the stroke
itself, sitting where the two should instead be flush; for a diagonal
(digit 3, or 9's corner) it is an angled sliver, since the stroke's corner
pokes out sideways as well as past the tip. `_place_transform` fixes this by
insetting the `v=0` anchor by half the stroke width (`spec.stroke_width / 2`)
back into the stave, so the stroke's far edge lands exactly on the stave's
cap instead of past it.

## Overlay anchoring

Overlay glyphs (tens/hundreds/thousands) carry zero advance width, and their
outline coordinates are in the *same* absolute coordinate space as the units
glyph's own stave — not relative to a (0, 0) origin local to the overlay.
That is what makes the overlay land in the right place purely from an
OpenType shaping engine placing zero-advance glyphs at the same pen position
as the glyph before them, with no GPOS anchoring needed, and what makes
`--merge` predictable: the same rescaling (`cistercian.glyphs.rescale_glyph`)
applies uniformly to the stave and every overlay.
