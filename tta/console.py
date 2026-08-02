"""Console output that survives Windows.

The Windows console defaults to cp1252, and TikTok captions are full of emoji.
Printing one crashes the process with a UnicodeEncodeError halfway through a
run — after the network work is done but before anything useful is written,
which is the worst possible place to fail.

Every entry point calls `setup()` first. This is not optional politeness; it is
the difference between the tool working and not working on the platform most of
its users are on.
"""
from __future__ import annotations

import io
import sys


def setup() -> None:
    """Force UTF-8 on stdout/stderr, replacing anything unencodable."""
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name)
        buffer = getattr(stream, "buffer", None)
        if buffer is None:                       # already wrapped, or redirected oddly
            continue
        setattr(sys, name, io.TextIOWrapper(buffer, encoding="utf-8",
                                            errors="replace", line_buffering=True))


def safe(text: str) -> str:
    """Last resort for a string headed somewhere we do not control."""
    return (text or "").encode("utf-8", "replace").decode("utf-8", "replace")
