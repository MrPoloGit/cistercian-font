"""Shared fixtures: spec paths and a synthetic base font for merge/shaping tests."""

from __future__ import annotations

import string
from pathlib import Path

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from cistercian.build import build_ttf
from cistercian.merge import merge_font

REPO_ROOT = Path(__file__).resolve().parent.parent
DIGITS_SPEC = REPO_ROOT / "spec" / "digits.json"
LETTERS_SPEC = REPO_ROOT / "spec" / "letters.json"

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
BASE_UPM = 2048


@pytest.fixture
def digits_spec_path() -> Path:
    return DIGITS_SPEC


@pytest.fixture
def letters_spec_path() -> Path:
    return LETTERS_SPEC


def _build_synthetic_base(path: Path) -> Path:
    """Write a tiny synthetic TrueType font with ASCII digits and Latin letters.

    Stands in for a real base font in merge tests, so they do not depend on
    any font being installed on the test machine.
    """
    chars = (
        list(string.digits)
        + list(string.ascii_uppercase)
        + list(string.ascii_lowercase)
    )
    names = {ch: (_DIGIT_NAMES[int(ch)] if ch.isdigit() else ch) for ch in chars}
    names[" "] = "space"
    glyph_order = [".notdef", *sorted(set(names.values()))]

    fb = FontBuilder(BASE_UPM, isTTF=True)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap({ord(ch): name for ch, name in names.items()})

    glyf = {}
    metrics = {}
    for name in glyph_order:
        pen = TTGlyphPen(None)
        if name not in (".notdef", "space"):
            pen.moveTo((100, 0))
            pen.lineTo((900, 0))
            pen.lineTo((900, 1400))
            pen.lineTo((100, 1400))
            pen.closePath()
        glyf[name] = pen.glyph()
        metrics[name] = (1000, 100)
    fb.setupGlyf(glyf)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=1800, descent=-400)
    fb.setupOS2(
        sTypoAscender=1800, sTypoDescender=-400, usWinAscent=1800, usWinDescent=400
    )
    fb.setupNameTable({"familyName": "TestBase", "styleName": "Regular"})
    fb.setupPost()
    fb.font.save(str(path))
    return path


@pytest.fixture
def base_font_path(tmp_path: Path) -> Path:
    return _build_synthetic_base(tmp_path / "base.ttf")


@pytest.fixture(scope="session")
def full_ttf() -> TTFont:
    """The complete standalone font, all 10,000 glyphs. Built once per test run."""
    return build_ttf(str(DIGITS_SPEC), str(LETTERS_SPEC), numbers=range(10000))


@pytest.fixture(scope="session")
def full_ttf_path(tmp_path_factory: pytest.TempPathFactory, full_ttf: TTFont) -> Path:
    path = tmp_path_factory.mktemp("full-font") / "Cistercian-Regular.ttf"
    full_ttf.save(str(path))
    return path


@pytest.fixture(scope="session")
def merged_font_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A synthetic base font merged with the full 0-9999 range. Built once per run."""
    tmp_dir = tmp_path_factory.mktemp("merge")
    base_path = _build_synthetic_base(tmp_dir / "base.ttf")
    out_path = tmp_dir / "merged.ttf"
    merge_font(
        base_path, out_path, str(DIGITS_SPEC), str(LETTERS_SPEC), numbers=range(10000)
    )
    return out_path
