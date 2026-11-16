# Encoding

Full UCSUR chart reference and worked examples for the Cistercian numeral
font.

## Code point ranges

| Range | Contents | Behavior |
|---|---|---|
| U+EBA0-EBA9 | Units 0-9 | Base glyph. U+EBA0 is the bare stave (zero). |
| U+EBB1-EBB9 | Tens 1-9 | Zero-advance overlay |
| U+EBC1-EBC9 | Hundreds 1-9 | Zero-advance overlay |
| U+EBD1-EBD9 | Thousands 1-9 | Zero-advance overlay |
| U+F0000-U+F270F | Precomposed 0-9999 | Supplementary PUA-A, one glyph per number |

The overlay ranges skip the "0" slot: there is no overlay glyph for a zero
digit, since an empty place is just the absence of that overlay character
(see `cistercian.glyphs.overlay_codepoint`, which only accepts digits 1-9).

## Sequence form

A number is written as the units glyph followed by its nonzero-place
overlays, in tens/hundreds/thousands order. The always-on `rlig` feature
turns any such sequence into the matching precomposed glyph.

| Number | Sequence | Code points |
|---|---|---|
| 3 | units(3) | U+EBA3 |
| 23 | units(3), tens(2) | U+EBA3 U+EBB2 |
| 230 | units(0), tens(3), hundreds(2) | U+EBA0 U+EBB3 U+EBC2 |
| 9230 | units(0), tens(3), hundreds(2), thousands(9) | U+EBA0 U+EBB3 U+EBC2 U+EBD9 |

## Precomposed glyphs

`cistercian.num.NNNN` (`NNNN` zero-padded) at `U+F0000 + NNNN` exists for
every number 0-9999, so any of these resolve to the same glyph for 9230:

- Typing the sequence above (resolved via `rlig`).
- Typing `9230` with `ss01` enabled, once merged into a font with ASCII
  digit glyphs (see `cistercian.features.build_ss01_fea`'s docstring for the
  leading-zero and run-length-5+ edge cases).
- Addressing `U+F240E` (`0xF0000 + 9230`) directly.

## Letters

`spec/letters.json` maps A-Z to the numerals 1-26. With
`mapping_mode: "shared"` (the default), lowercase shares the same numeral as
its uppercase counterpart; `mapping_mode: "extended"` instead gives
lowercase the numerals 27-52. `ss02` applies this mapping, once merged into
a font with Latin letter glyphs.
