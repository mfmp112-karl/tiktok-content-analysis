#!/usr/bin/env python3
"""Two report-safety canaries, borrowed from named defects in a sibling
project's content-review process (the org's asksidney-raven-critic skill,
which gates a different content pipeline — these two checks are the ideas
worth reusing here, not a dependency on that skill).

1. No new hard truncation. `tta/text.py`'s `truncate()` cuts at a word
   boundary; a caption cut with a raw `text[:140]` slice can split a word
   mid-way, which reads like a bug rather than a summary. This greps the
   source for that shape wherever it isn't going through `truncate()`.

2. No raw label leaking into prose. Theme names are stored as slash-joined
   term triples ("Fix / Trader / Itself") — precise in a table, awful in a
   sentence. `themes.readable()` exists to convert one into the other and
   never emits " / " in its own output, so that substring appearing inside
   a paragraph/list/heading in the rendered report (rather than a table
   cell) means something skipped the conversion.

Requires a local `~/.raven/tta.sqlite3` with at least one analysed account
(pass its handle as the one argument) — reads local data only, no network.
Run from the repo root: `python scripts/check_report_safety.py <handle>`
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

#: A slice of a name that plausibly holds caption/text content, not going
#: through tta.text.truncate(). Flags text[:N] / caption[:N] / hook[:N] and
#: similar — deliberately narrow so it doesn't flag unrelated list slicing
#: like `rows[:12]` or `out[:limit]`, which aren't text truncation at all.
_HARD_SLICE = re.compile(
    r"\b(text|caption|title|summary|hook|bio|desc|opener)\w*\[\s*:\s*\d+\s*\]")


def _check_no_hard_slices() -> tuple[bool, str]:
    hits = []
    for py in ROOT.joinpath("tta").rglob("*.py"):
        if py.name == "text.py":
            continue   # the helper itself is allowed to slice
        for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            if not _HARD_SLICE.search(line):
                continue
            if "truncate(" in line or "noqa: hard-slice" in line:
                continue   # already safe, or an explained, non-prose exception
            hits.append(f"{py.relative_to(ROOT)}:{i}: {line.strip()}")
    return (not hits, "no hard text slices found" if not hits
            else f"{len(hits)} found:\n    " + "\n    ".join(hits))


#: Same shape themes.readable() splits on: two-or-more slash-separated
#: terms. Deliberately requires a letter on each side of the slash so a
#: stray "/" in a URL or date doesn't false-positive.
_RAW_LABEL = re.compile(r"[A-Za-z][\w'’]*\s*/\s*[A-Za-z]")
#: Tags where prose actually lives — a raw label inside a <table> cell is
#: expected and fine; themes.readable()'s own docstring says so.
_PROSE_TAG = re.compile(
    r"<(p|li|h[1-4]|figcaption)[^>]*>(.*?)</\1>", re.S)


def _check_no_raw_labels(handle: str) -> tuple[bool, str]:
    from tta import store
    from tta.analyse import aggregates as ag, cadence, hooks, themes
    from tta.calendar import build as calbuild, recommend
    from tta.report import html as rhtml

    with store.connect() as conn:
        videos = store.load_videos(conn, handle)
    if not videos:
        return (False, f"no local data for @{handle} — run driver.py against "
                        f"it first, or pass an account that's already cached")

    analysis = ag.build(videos)
    hook_info = hooks.build(videos)
    cad = cadence.build(videos, analysis["weekday"], analysis["hour"])
    shortlisted = themes.shortlist(analysis["theme"])
    calls = themes.calls(analysis["theme"])
    demand = {"topics": [], "peers": [], "gaps": [], "last30days": [],
              "l30_clusters": [], "coverage": []}
    recs = recommend.build(analysis=analysis, theme_calls=calls,
                           shortlist=shortlisted, hook_info=hook_info,
                           cadence_info=cad, research=demand, profile_audit=None)
    cal = calbuild.build(shortlist=shortlisted, theme_calls=calls,
                         winning_hooks=hook_info["winning_hooks"],
                         best_slot=cad["best_slot"])
    ctx = {
        "meta": {"handle": handle, "accessed_via": "check_report_safety.py",
                 "harvest_tier": "local cache", "generated": rhtml.now_stamp(),
                 "version": "check"},
        "creator": {}, "analysis": analysis, "themes": {"k": 0, "method": "cached"},
        "hooks": hook_info, "cadence": cad, "theme_calls": calls,
        "profile_audit": None, "peers": [], "research": demand,
        "calendar": cal, "recommendations": recs,
        "limits": rhtml.default_limits(), "narrative": {},
    }
    doc = rhtml.render(ctx)

    leaks = []
    for tag, inner in _PROSE_TAG.findall(doc):
        if "<table" in inner or "<th>" in inner or "<td" in inner:
            continue   # a real table cell got swallowed by a stray <p>/<li>
                       # elsewhere in the document — not a prose leak, a
                       # regex-boundary artifact; table cells showing raw
                       # labels are correct per themes.readable()'s own rule
        stripped = re.sub(r"<[^>]+>", "", inner)
        if _RAW_LABEL.search(stripped):
            leaks.append(f"<{tag}>: {stripped[:80]!r}")
    return (not leaks, "no raw labels found in prose" if not leaks
            else f"{len(leaks)} found:\n    " + "\n    ".join(leaks[:10]))


def main() -> int:
    from tta import console
    console.setup()

    if len(sys.argv) != 2:
        print("usage: python scripts/check_report_safety.py <handle>")
        return 2
    handle = sys.argv[1].lstrip("@").lower()

    rows = []
    ok, detail = _check_no_hard_slices()
    rows.append(("No hard-truncated text (word-boundary safe)", ok, detail))
    ok, detail = _check_no_raw_labels(handle)
    rows.append(("No raw theme labels leaking into prose", ok, detail))

    print()
    failed = 0
    for label, ok, detail in rows:
        print(f"[{'  OK  ' if ok else ' FAIL '}] {label}")
        print(f"    {detail}")
        if not ok:
            failed += 1
    print()
    print("All clear." if not failed else f"{failed} check(s) failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
