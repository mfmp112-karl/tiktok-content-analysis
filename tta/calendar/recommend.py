"""What to actually make — the section a creator turns to first.

Everything else in the report explains the past. This turns it into a short
list of specific things to film, and it draws on three sources that answer
three different questions:

* **The account's own data** — which themes and formats already travel here.
* **What the niche is posting** (camofox) — the tags and topics with attention
  on them right now.
* **What the niche is asking** (last30days) — real questions people typed into
  Reddit and elsewhere in the last thirty days. These are the best prompts in
  the whole tool, because a question someone actually asked is already proof
  that the answer is wanted.

The framing of the recommendations follows the creator playbook credited in
the report: a content style is found by testing several, dropping what does
not travel, and replacing it — so recommendations come in four kinds, matching
the four calls a theme can get.
"""
from __future__ import annotations

import re

from .. import text as texttool
from ..analyse.themes import readable

#: Formats worth naming, keyed to the account's own measured strengths.
#: Each entry is (headline, evidence, move) — the report states the evidence
#: before the move, never the other way round.
FORMAT_MOVES = {
    "long": ("Go longer than feels comfortable",
             "Your longer posts do better.",
             "try one idea, explained well, instead of a quick clip."),
    "short": ("Cut harder",
              "Your shorter posts do better.",
              "get to the point fast — and stop before the idea runs dry."),
    "reply": ("Reply to comments on camera",
              "Your replies to comments do better than standalone posts.",
              "mine your comment section for the next five videos."),
    "original": ("Lead with your own ideas",
                 "Your original posts do better than your replies.",
                 "treat comment replies as filler, not fuel."),
}

#: Somebody wanting to know something. A question mark, or a question opener
#: at the start of the sentence — "what" buried mid-sentence usually is not one.
_QUESTION = re.compile(
    r"\?|^\s*(how|what|why|when|where|which|should|can|could|is|are|does|do|"
    r"any|anyone|has anyone|help|advice|tips?)\b", re.I)

#: Things that look like discussion but are not a question a creator can film.
#: Launch posts and link-dumps dominate Hacker News results and would otherwise
#: fill the recommendations with "Answer this: Show HN: <someone's side project>".
_JUNK = re.compile(
    r"^\s*(show hn|ask hn:?\s*$|launch hn|tell hn)\b"
    r"|^\s*https?://"
    r"|\b(v?\d+\.\d+(\.\d+)?\s*(release|released)?)\b"
    r"|\b(open[- ]source|github|repo|api|cli|app release|beta|changelog)\b"
    r"|\b(discount|promo code|sign up|subscribe now|buy now|link in bio)\b"
    # A year in parentheses is how aggregators mark an old article. The research
    # window is the last 30 days, so this is a resurfaced link, not a live
    # question — and dated advice is the last thing to build a calendar on.
    r"|\(\s*(19|20)\d{2}\s*\)\s*$",
    re.I)

#: A question that could be answered on camera is short and plain.
MAX_QUESTION_LEN = 110


def _clean(text: str, limit: int = 120) -> str:
    return texttool.truncate(text, limit)


def is_filmable_question(title: str) -> bool:
    """Would answering this on camera make sense?"""
    t = (title or "").strip()
    if not t or len(t) > MAX_QUESTION_LEN:
        return False
    if _JUNK.search(t):
        return False
    return bool(_QUESTION.search(t))


def from_questions(l30_items: list[dict], l30_clusters: list[dict],
                   limit: int = 5) -> list[dict]:
    """Turn real questions from the last 30 days into things to film.

    Filtered hard. The research skill returns everything it found, which for a
    software-adjacent query is mostly product launches — and a recommendation
    reading "Answer this: Show HN: open-source workout tracker" is worse than
    no recommendation, because it makes the whole list look automated.
    """
    out, seen = [], set()

    for source_rows, note in ((l30_clusters, "This came up more than once in the "
                                             "last 30 days."),
                              (l30_items, "Someone asked this in the last 30 "
                                          "days and the thread got engagement.")):
        for row in source_rows:
            title = _clean(row.get("title", ""))
            key = title.lower()
            if not title or key in seen or not is_filmable_question(title):
                continue
            seen.add(key)
            summary = (row.get("summary") or "").strip()
            # Sources often set the summary to the title. Echoing it back under
            # the headline reads like a bug, so fall through to the note.
            echoes = summary[:60].lower().strip(" .…") == title[:60].lower().strip(" .…")  # noqa: hard-slice — comparison only, never displayed
            out.append({
                "kind": "answer",
                "headline": f"Answer this: “{title}”",
                "why": (note if (echoes or len(summary) <= 30)
                        else texttool.truncate(summary, 170)),
                "source": (", ".join(row.get("sources") or [])
                           or row.get("source") or "last30days"),
                "engagement": row.get("engagement") or row.get("engagement_total"),
            })
    return out[:limit]


def build(*, analysis: dict, theme_calls: dict, shortlist: list[dict],
          hook_info: dict, cadence_info: dict, research: dict,
          profile_audit: dict | None) -> list[dict]:
    """The ordered list of recommendations. Strongest evidence first."""
    recs: list[dict] = []

    # --- 1. double down on what already travels ---------------------------
    # Every "why" below follows one shape: what currently works, and why —
    # then, separately, what the good move is. Evidence first, move second,
    # never blended into one clause. Ogilvy #10: facts don't stand alone.
    for theme in shortlist:
        call = theme_calls.get(theme["name"], {}).get("call")
        if call == "keep":
            recs.append({
                "kind": "more",
                "headline": f"Make more about {readable(theme['name'])}",
                "why": (f"What's working: {readable(theme['name'])}. "
                        f"{theme['n']} posts, {theme['index']}% of your "
                        f"average. That's proven. Good move: make more."),
                "source": "your own catalogue",
            })
        elif call == "test" and theme["index"] >= 115:
            need = theme.get("needs")
            settle = f" About {need} more posts would settle it." if need else ""
            recs.append({
                "kind": "test",
                "headline": f"Test {readable(theme['name'])} properly",
                "why": (f"Early signal: {readable(theme['name'])} is at "
                        f"{theme['index']}% of your average, across "
                        f"{theme['n']} posts. Promising, not proven yet."
                        f"{settle} Good move: test it properly before you "
                        "commit more time."),
                "source": "your own catalogue",
            })

    # --- 2. stop what demonstrably does not ------------------------------
    for name, call in theme_calls.items():
        if call.get("call") != "ditch":
            continue
        row = next((r for r in analysis["theme"] if r["name"] == name), None)
        if not row:
            continue
        recs.append({
            "kind": "stop",
            "headline": f"Stop making {readable(name)} in its current form",
            "why": (f"What's not working: {readable(name)}. {row['n']} posts "
                    f"at {row['index']}% of your average. That gap is real. "
                    f"Good move: don't drop it yet — change how you shoot "
                    "and caption it first."),
            "source": "your own catalogue",
        })

    # --- 3. format moves --------------------------------------------------
    dur = [r for r in analysis["duration"] if r["verdict"] in ("strong", "moderate")]
    if dur:
        best = max(dur, key=lambda r: r["index"])
        key = "long" if "60" in best["name"] or "35" in best["name"] else "short"
        head, evidence, move = FORMAT_MOVES[key]
        recs.append({"kind": "format", "headline": head,
                     "why": (f"What's working: {evidence} ({best['name']} runs "
                             f"at {best['index']}% of your average across "
                             f"{best['n']} posts.) Good move: {move}"),
                     "source": "your own catalogue"})

    fmt = [r for r in analysis["format"] if r["verdict"] in ("strong", "moderate")]
    if fmt:
        best = max(fmt, key=lambda r: r["index"])
        key = "reply" if "reply" in best["name"].lower() else "original"
        head, evidence, move = FORMAT_MOVES[key]
        recs.append({"kind": "format", "headline": head,
                     "why": f"What's working: {evidence} Good move: {move}",
                     "source": "your own catalogue"})

    # --- 4. answer what the niche is asking ------------------------------
    recs.extend(from_questions(research.get("last30days") or [],
                               research.get("l30_clusters") or []))

    # --- 5. cover a gap the niche has and this account does not ----------
    for tag in (research.get("gaps") or [])[:2]:
        recs.append({
            "kind": "gap",
            "headline": f"Try {readable(tag)}",
            "why": (f"What's happening: {readable(tag)} is trending in "
                    f"your niche. You haven't posted it. Good move: try "
                    "it once — don't commit yet."),
            "source": "TikTok niche scan",
        })

    # --- 6. fix the profile, if it is leaking ----------------------------
    if profile_audit:
        failing = [c for c in profile_audit["checks"] if not c["pass"]]
        if failing:
            first = failing[0]
            tail = (f" ({len(failing)} profile checks need attention.)"
                     if len(failing) > 1 else "")
            recs.append({
                "kind": "profile",
                "headline": f"Fix your profile: {first['name'].lower()}",
                "why": (f"What's leaking: {first['detail']}{tail} "
                        f"Good move: {first.get('fix', '')}".strip()),
                "source": "profile audit",
            })

    # --- 7. cadence -------------------------------------------------------
    rhythm = cadence_info.get("rhythm", {})
    if rhythm.get("trend") == "slowing down":
        recs.append({
            "kind": "cadence",
            "headline": "Get back to your old posting rate",
            "why": (f"What's slipping: you post {rhythm.get('recent_per_week')} "
                    f"times a week now, against {rhythm.get('per_week')} "
                    f"normally. Good move: get back to your old rate. "
                    "Nothing else here can help while output keeps dropping."),
            "source": "your own catalogue",
        })

    rep = hook_info.get("repetition", {})
    if rep.get("templated_share", 0) >= 15:
        recs.append({
            "kind": "hooks",
            "headline": "Break up your opening lines",
            "why": (f"What's dragging: {rep['templated_share']}% of your "
                    f"captions open the same way, reused three times or "
                    f"more. That's a quiet drag on reach. Good move: mix "
                    "up your openers."),
            "source": "hook teardown",
        })

    return recs


KIND_LABEL = {
    "more": "Do more of this",
    "test": "Worth testing",
    "stop": "Stop or rework",
    "format": "Change the format",
    "answer": "Answer a real question",
    "gap": "Try something new",
    "profile": "Fix the profile",
    "cadence": "Post more often",
    "hooks": "Vary your hooks",
}
