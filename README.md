# Cistercian

A font that renders Cistercian numerals (1-9999, plus a bare stave for 0)
and letters A-Z as numerals. It follows the Under-ConScript Unicode
Registry (UCSUR) proposal by Paul Hardy and Rebecca Bettencourt (2020), and
can be used standalone, as a CSS fallback font, or merged into another font.

## Install

```
pip install -e ".[dev]"
```

## Build the font

```
cistercian build --out dist
```

Writes `dist/Cistercian-Regular.{ttf,otf,woff2}`. Add `--numbers 100` while
iterating locally — the full 0-9999 build (default) takes about 15 seconds,
mostly compiling the `rlig`/`ss01` OpenType feature rules.

## Merge into a base font

```
cistercian merge path/to/Base-Regular.ttf --out Base-Cistercian.ttf
```

Copies the Cistercian glyphs and feature rules into a copy of the base font,
rescaled to its units-per-em. Only TrueType (`glyf`-based) base fonts are
supported in v1 (see "Limitations" below). Refuses to merge into a font
whose `OS/2.fsType` forbids modification.

## Render a contact sheet

```
cistercian contact-sheet --out sheet.svg --numbers 100
```

Renders the requested numbers' glyphs as a labelled SVG grid, for visual
checking.

## Encoding

| Range | Contents | Behavior |
|---|---|---|
| U+EBA0-EBA9 | Units 0-9 | Base glyph. U+EBA0 is the bare stave (zero). |
| U+EBB1-EBB9 | Tens 1-9 | Zero-advance overlay |
| U+EBC1-EBC9 | Hundreds 1-9 | Zero-advance overlay |
| U+EBD1-EBD9 | Thousands 1-9 | Zero-advance overlay |
| U+F0000-U+F270F | Precomposed 0-9999 | Supplementary PUA-A, one glyph per number |

A full number is the units glyph followed by its nonzero-place overlays
(e.g. 9230 is U+EBA0 U+EBB3 U+EBC2 U+EBD9); this always resolves to the
precomposed glyph via an always-on ligature feature (`rlig`). `ss01` turns
runs of 1-4 ASCII digits into a numeral (with the edge cases in section 5 of
the plan); `ss02` turns A-Z/a-z into the numerals 1-26. Both need the host
font to already have those glyphs, so they only apply once merged into a
base font (see "Limitations").

## Demo

```
cistercian build --out dist --formats woff2
python3 -m http.server 8000
# open http://localhost:8000/demo/index.html
```

A number converter, a letter converter, and a paginated 0-9999 chart.

## Limitations (v1)

- `--merge` only supports TrueType (`glyf`-based) base fonts; CFF/OTF bases
  are not yet supported.
- Runs longer than 4 ASCII digits are left as plain digits (no grouping).
- `ss01`/`ss02` are inert in the standalone font, since it has no ASCII
  digit or Latin letter glyphs of its own; use `--merge` to get a font where
  they do something.

## License

Code is MIT (`LICENSE`). The font itself is SIL Open Font License 1.1
(`OFL.txt`).
