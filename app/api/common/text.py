"""Text helpers shared across API modules."""

import re
import unicodedata


_SLUG_STRIP_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str, max_length: int = 200) -> str:
    """Convert arbitrary text into a URL-safe slug.

    Lowercases, strips diacritics, replaces non-alphanumeric runs with hyphens,
    trims leading/trailing hyphens, and truncates to ``max_length``.
    Returns "untitled" if the input collapses to an empty string.
    """
    normalized = unicodedata.normalize("NFKD", text)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower()
    hyphenated = _SLUG_STRIP_RE.sub("-", lowered).strip("-")
    if not hyphenated:
        return "untitled"
    if len(hyphenated) > max_length:
        hyphenated = hyphenated[:max_length].rstrip("-") or "untitled"
    return hyphenated
