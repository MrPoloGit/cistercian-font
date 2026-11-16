"""Exceptions raised across the cistercian package."""


class SpecError(Exception):
    """A spec file (``digits.json`` or ``letters.json``) is invalid.

    The message names the offending file and, where possible, the offending key.
    """


class MergeError(Exception):
    """Merging the font into a base font failed.

    The message names the base font file and the reason (missing table,
    licence restriction, unit mismatch, ...).
    """
