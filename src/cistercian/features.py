"""OpenType features: ``ss01``, ``ss02``, and the always-on UCSUR ligatures.

``ss01`` (digits) and ``ss02`` (letters) substitute glyphs that live outside
this package's own glyph set (ASCII digits, Latin letters). This module never
assumes a glyph name for them; it resolves ASCII/Latin code points against
whichever cmap it is given, so the same generator works for the standalone
font (if it carries those glyphs) and for ``--merge`` (against the base
font's own cmap and glyph names). See ``cistercian.merge``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import jsonschema

from cistercian.errors import SpecError
from cistercian.geometry import DigitSpec
from cistercian.glyphs import (
    decompose,
    overlay_glyph_name,
    precomposed_glyph_name,
    units_glyph_name,
)

_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "spec"
    / "schema"
    / "letters.schema.json"
)

MappingMode = Literal["shared", "extended"]


@dataclass(frozen=True)
class LetterSpec:
    """The parsed, validated contents of ``spec/letters.json``."""

    mapping_mode: MappingMode
    letters: dict[str, int]


def load_letter_spec(path: str | Path) -> LetterSpec:
    """Load and validate ``letters.json``.

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

    return LetterSpec(mapping_mode=raw["mapping_mode"], letters=dict(raw["letters"]))


def letter_value(spec: LetterSpec, letter: str) -> int:
    """The numeral value (1-26, or 1-52 if lowercase is extended) for one letter."""
    if letter.isupper():
        return spec.letters[letter]
    base = spec.letters[letter.upper()]
    return base if spec.mapping_mode == "shared" else base + 26


def _glyph_for_codepoint(cmap: dict[int, str], codepoint: int) -> str:
    try:
        return cmap[codepoint]
    except KeyError as exc:
        raise SpecError(
            f"U+{codepoint:04X} is not in the target font's cmap; "
            "ss01/ss02 need the base font to already have it"
        ) from exc


def build_rlig_fea(spec: DigitSpec, numbers: range | None = None) -> str:
    """Build the ``rlig`` feature: UCSUR digit sequences resolve to precomposed glyphs.

    This only references this package's own glyph names, so it works in every
    font this package builds, standalone or merged. Rules are sorted longest
    sequence first so a 4-glyph sequence is not shadowed by a shorter rule
    sharing its prefix.

    Args:
        spec: The digit geometry spec (only used to confirm digits 0-9 exist).
        numbers: Which precomposed numbers have a glyph (default: all of
            0-9999); a rule is only emitted for a number in this range.
    """
    numbers = numbers if numbers is not None else range(10000)
    rules: list[tuple[int, str]] = []
    for number in numbers:
        units, tens, hundreds, thousands = decompose(number)
        sequence = [units_glyph_name(units)]
        for place, digit in (
            ("tens", tens),
            ("hundreds", hundreds),
            ("thousands", thousands),
        ):
            if digit:
                sequence.append(overlay_glyph_name(place, digit))  # type: ignore[arg-type]
        if len(sequence) < 2:
            continue
        rule = f"    sub {' '.join(sequence)} by {precomposed_glyph_name(number)};"
        rules.append((len(sequence), rule))
    rules.sort(key=lambda item: item[0], reverse=True)
    body = "\n".join(rule for _, rule in rules)
    return f"feature rlig {{\n{body}\n}} rlig;\n"


_DIGIT_NAMES = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
]


def build_ss01_fea(cmap: dict[int, str], numbers: range | None = None) -> str:
    """Build the ``ss01`` feature: runs of 1-4 ASCII digits resolve to a numeral.

    Edge cases:

    - A run longer than 4 digits is left as plain digits.
    - A run with a leading zero is left as plain digits, except a lone "0",
      which becomes the bare stave.

    The 10,000 specific digit-sequence rules live in their own plain
    (non-contextual) lookup, ``ss01_numbers``, so they compile down to a
    handful of compact ligature/single-substitution subtables instead of one
    chaining-context subtable per rule (which overflows a lookup's offsets
    well before 10,000 rules). Three generic "ignore" guards (not preceded by
    a digit; not the start of a 5+ digit run; a lone zero is not followed by
    a digit) live in a second, contextual lookup that invokes ``ss01_numbers``
    only at the true start of a 1-4 digit run.

    Args:
        cmap: The target font's own cmap, used to resolve ASCII digit glyph
            names (see the module docstring).
        numbers: Which precomposed numbers have a glyph (default: all of
            0-9999); a rule is only emitted for a number in this range.
    """
    numbers = numbers if numbers is not None else range(10000)
    digit_glyphs = [_glyph_for_codepoint(cmap, 0x30 + i) for i in range(10)]
    digit_class = f"[{' '.join(digit_glyphs)}]"
    zero_glyph = digit_glyphs[0]

    rules: list[tuple[int, str]] = []
    for number in numbers:
        text = str(number)
        if len(text) > 1 and text[0] == "0":
            continue
        sequence = [digit_glyphs[int(ch)] for ch in text]
        rule = f"    sub {' '.join(sequence)} by {precomposed_glyph_name(number)};"
        rules.append((len(sequence), rule))
    rules.sort(key=lambda item: item[0], reverse=True)
    specific = "\n".join(rule for _, rule in rules)

    return (
        f"lookup ss01_numbers {{\n{specific}\n}} ss01_numbers;\n\n"
        "feature ss01 {\n"
        "    lookup ss01_guard {\n"
        f"        ignore sub {digit_class} {digit_class}';\n"
        f"        ignore sub {digit_class}'"
        f" {digit_class} {digit_class} {digit_class} {digit_class};\n"
        f"        ignore sub {zero_glyph}' {digit_class};\n"
        f"        sub {digit_class}' lookup ss01_numbers;\n"
        "    } ss01_guard;\n"
        "} ss01;\n"
    )


def build_ss02_fea(
    letter_spec: LetterSpec, cmap: dict[int, str], numbers: range | None = None
) -> str:
    """Build the ``ss02`` feature: A-Z (and a-z) resolve to the numerals 1-26 (or 1-52).

    Args:
        letter_spec: The parsed letter mapping.
        cmap: The target font's own cmap, used to resolve Latin letter glyph names.
        numbers: Which precomposed numbers have a glyph (default: all of
            0-9999); a letter is skipped if its numeral value falls outside it.
    """
    numbers = numbers if numbers is not None else range(10000)
    rules: list[str] = []
    for upper in sorted(letter_spec.letters):
        for letter in (upper, upper.lower()):
            value = letter_value(letter_spec, letter)
            if value not in numbers:
                continue
            glyph = _glyph_for_codepoint(cmap, ord(letter))
            rules.append(f"    sub {glyph} by {precomposed_glyph_name(value)};")
    body = "\n".join(rules)
    return f"feature ss02 {{\n{body}\n}} ss02;\n"


__all__ = [
    "LetterSpec",
    "MappingMode",
    "build_rlig_fea",
    "build_ss01_fea",
    "build_ss02_fea",
    "letter_value",
    "load_letter_spec",
]
