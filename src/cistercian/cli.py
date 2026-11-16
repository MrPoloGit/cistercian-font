"""Command-line entry point: ``cistercian build`` and ``cistercian merge``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cistercian.build import build_otf, build_ttf, save_woff2
from cistercian.contact_sheet import write_contact_sheet
from cistercian.errors import MergeError, SpecError
from cistercian.merge import merge_font

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DIGITS = REPO_ROOT / "spec" / "digits.json"
DEFAULT_LETTERS = REPO_ROOT / "spec" / "letters.json"


def _add_spec_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--digits", default=str(DEFAULT_DIGITS), help="path to digits.json"
    )
    parser.add_argument(
        "--letters", default=str(DEFAULT_LETTERS), help="path to letters.json"
    )


def _numbers_arg(value: str) -> range | None:
    if value == "all":
        return None
    return range(int(value))


def cmd_build(args: argparse.Namespace) -> int:
    numbers = args.numbers
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    formats = set(args.formats.split(","))
    ttf = build_ttf(args.digits, args.letters, numbers=numbers, version=args.version)
    if "ttf" in formats:
        ttf.save(str(out_dir / "Cistercian-Regular.ttf"))
    if "woff2" in formats:
        save_woff2(ttf, out_dir / "Cistercian-Regular.woff2")
    if "otf" in formats:
        otf = build_otf(
            args.digits, args.letters, numbers=numbers, version=args.version
        )
        otf.save(str(out_dir / "Cistercian-Regular.otf"))
    print(f"Built {out_dir} ({args.formats})")
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    numbers = args.numbers
    merge_font(args.base, args.out, args.digits, args.letters, numbers=numbers)
    print(f"Merged into {args.out}")
    return 0


def cmd_contact_sheet(args: argparse.Namespace) -> int:
    numbers = list(args.numbers if args.numbers is not None else range(10000))
    font = build_ttf(args.digits, args.letters, numbers=range(max(numbers) + 1))
    write_contact_sheet(font, numbers, args.out)
    print(f"Wrote {args.out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cistercian")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_cmd = subparsers.add_parser(
        "build", help="build the standalone Cistercian font"
    )
    _add_spec_args(build_cmd)
    build_cmd.add_argument("--out", default="dist", help="output directory")
    build_cmd.add_argument(
        "--formats", default="ttf,otf,woff2", help="comma-separated: ttf,otf,woff2"
    )
    build_cmd.add_argument(
        "--numbers",
        type=_numbers_arg,
        default=None,
        help="how many precomposed numbers to include (0..N-1), or 'all' (default)",
    )
    build_cmd.add_argument("--version", default="0.1.0", help="font version")
    build_cmd.set_defaults(func=cmd_build)

    merge_cmd = subparsers.add_parser("merge", help="merge into a base font")
    _add_spec_args(merge_cmd)
    merge_cmd.add_argument("base", help="base font to merge into")
    merge_cmd.add_argument("--out", required=True, help="output font path")
    merge_cmd.add_argument(
        "--numbers",
        type=_numbers_arg,
        default=None,
        help="how many precomposed numbers to include (0..N-1), or 'all' (default)",
    )
    merge_cmd.set_defaults(func=cmd_merge)

    sheet_cmd = subparsers.add_parser(
        "contact-sheet", help="render an SVG contact sheet for visual checking"
    )
    _add_spec_args(sheet_cmd)
    sheet_cmd.add_argument("--out", default="contact-sheet.svg", help="output SVG path")
    sheet_cmd.add_argument(
        "--numbers",
        type=_numbers_arg,
        default=range(100),
        help="how many numbers to render (0..N-1), or 'all' (default: 0..99)",
    )
    sheet_cmd.set_defaults(func=cmd_contact_sheet)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (SpecError, MergeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
