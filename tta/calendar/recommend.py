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

from ..analyse.themes import readable

#: Formats worth naming, keyed to the account's own measured strengths.
FORMAT_MOVES = {
    "long": ("Go longer than feels comfortable",
             "Your longer posts travel further than your short ones. Try a "
             "single idea explained properly rather than a clip."),
    "short": ("Cut harder",
              "Your shorter posts travel further. Get to the point in the "
              "first two seconds and end before the idea runs out."),
    "reply": ("Reply to comments on camera",
              "Your replies to comments outperform your standalone posts. "
              "Mine your own comment section for the next five videos."),
    "original": ("Lead with your own ideas",
                 "Your original posts travel further than your replies. "
                 "Comment replies are filler here, not fuel."),
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
    text = re.sub(r"\s+", " ", (text or "").strip())
    return text if len(text) <= limit else text[:limit - 1] + "…"


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
            echoes = summary[:60].lower().strip(" .…") == title[:60].lower().strip(" .…")
            out.append({
                "kind": "answer",
                "headline": f"Answer this: “{title}”",
                "why": (note if (echoes or len(summary) <= 30) else summary[:170]),
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
    for theme in shortlist:
        call = theme_calls.get(theme["name"], {}).get("call")
        if call == "keep":
            recs.append({
                "kind": "more",
                "headline": f"Make more about {readable(theme['name'])}",
                "why": (f"{theme['n']} posts, averaging {theme['index']}% of your "
                        f"own average. This one is proven, not a hunch."),
                "source": "your own catalogue",
            })
        elif call == "test" and theme["index"] >= 115:
            need = theme.get("needs")
            tail = (f" About {need} more on this theme would settle it."
                    if need else "")
            recs.append({
                "kind": "test",
                "headline": f"Test {readable(theme['name'])} properly",
                "why": (f"It is running at {theme['index']}% of your average "
                        f"across {theme['n']} posts, which is promising but not "
                        f"yet provable.{tail}"),
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
            "why": (f"{row['n']} posts at {row['index']}% of your average, and "
                    f"that gap is real rather than noise. The topic may be fine "
                    f"— look at how these are shot and captioned before "
                    f"abandoning it."),
            "source": "your own catalogue",
        })

    # --- 3. format moves --------------------------------------------------
    dur = [r for r in analysis["duration"] if r["verdict"] in ("strong", "moderate")]
    if dur:
        best = max(dur, key=lambda r: r["index"])
        key = "long" if "60" in best["name"] or "35" in best["name"] else "short"
        head, why = FORMAT_MOVES[key]
        recs.append({"kind": "format", "headline": head,
                     "why": f"{why} ({best['name']} runs at {best['index']}% of "
                            f"your average across {best['n']} posts.)",
                     "source": "your own catalogue"})

    fmt = [r for r in analysis["format"] if r["verdict"] in ("strong", "moderate")]
    if fmt:
        best = max(fmt, key=lambda r: r["index"])
        key = "reply" if "reply" in best["name"].lower() else "original"
        head, why = FORMAT_MOVES[key]
        recs.append({"kind": "format", "headline": head, "why": why,
                     "source": "your own catalogue"})

    # --- 4. answer what the niche is asking ------------------------------
    recs.extend(from_questions(research.get("last30days") or [],
                               research.get("l30_clusters") or []))

    # --- 5. cover a gap the niche has and this account does not ----------
    for tag in (research.get("gaps") or [])[:2]:
        recs.append({
            "kind": "gap",
            "headline": f"Try {readable(tag)}",
            "why": (f"It is running through this niche right now and you have "
                    f"never posted under it. Treat it as an experiment, not a "
                    f"commitment."),
            "source": "TikTok niche scan",
        })

    # --- 6. fix the profile, if it is leaking ----------------------------
    if profile_audit:
        failing = [c for c in profile_audit["checks"] if not c["pass"]]
        if failing:
            first = failing[0]
            recs.append({
                "kind": "profile",
                "headline": f"Fix your profile: {first['name'].lower()}",
                "why": (f"{first['detail']} {first.get('fix', '')}".strip() +
                        (f" ({len(failing)} profile checks need attention.)"
                         if len(failing) > 1 else "")),
                "source": "profile audit",
            })

    # --- 7. cadence -------------------------------------------------------
    rhythm = cadence_info.get("rhythm", {})
    if rhythm.get("trend") == "slowing down":
        recs.append({
            "kind": "cadence",
            "headline": "Get back to your old posting rate",
            "why": (f"You are at {rhythm.get('recent_per_week')} posts a week "
                    f"against a lifetime {rhythm.get('per_week')}. Nothing in "
                    f"this report can improve while output is falling."),
            "source": "your own catalogue",
        })

    rep = hook_info.get("repetition", {})
    if rep.get("templated_share", 0) >= 15:
        recs.append({
            "kind": "hooks",
            "headline": "Break up your opening lines",
            "why": (f"{rep['templated_share']}% of your captions open with "
                    f"phrasing you have used at least three times. Repetition "
                    f"in the opener is one of the least visible drags on reach."),
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
