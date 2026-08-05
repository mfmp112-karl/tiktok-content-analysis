"""Small text helpers shared across analysis and report modules.

One rule lives here: never cut a string mid-word. A caption truncated to
"...consist" instead of "...consistency" reads like a bug, not a summary —
a named defect (the "truncation/garbling check") from the org's own
Raven-critic skill, worth guarding against here even though that skill
gates a different pipeline.
"""
from __future__ import annotations

import re

_WS = re.compile(r"\s+")


def truncate(text: str, limit: int, *, ellipsis: str = "…") -> str:
    """Cut `text` to at most `limit` characters, at a word boundary.

    Collapses internal whitespace first, so `limit` counts visible
    characters rather than formatting. If the first word alone is longer
    than `limit`, it is cut hard — a word longer than the limit is not
    something a word boundary can save, so this falls back to the old
    behaviour rather than returning an oversized string.
    """
    text = _WS.sub(" ", (text or "").strip())
    if len(text) <= limit:
        return text
    room = max(limit - len(ellipsis), 0)
    cut = text[:room]
    space = cut.rfind(" ")
    cut = cut[:space] if space > 0 else text[:room]
    return cut.rstrip() + ellipsis
