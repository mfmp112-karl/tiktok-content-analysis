"""What the caption does, and whether it matters.

Two separate questions live here.

**Which caption features travel.** Each structural feature — a question, a
number, a direct address to the viewer — splits the catalogue in two and gets
tested against reach. Features are correlated with each other and with the
creator's mood, so a "strong" verdict means the gap is real, not that the
feature caused it. The report says so.

**Whether the openers are templated.** This is the one that tends to bite.
In the account this tool grew out of, clustering isolated ~350 videos whose
captions all began the same promotional way, pulling roughly half the account's
average reach. Nobody had noticed, because each caption looked fine on its own.
Repetition is only visible in aggregate, which is exactly what this measures.
"""
from __future__ import annotations

import re
from collections import Counter

from .. import text as texttool
from ..stats import welch_verdict
from .aggregates import caption

_EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF⬀-⯿]")
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)

#: Openers are compared on their first this-many words.
OPENER_WORDS = 4
#: An opener has to appear this often before it counts as a template.
TEMPLATE_MIN = 3


def _strip_tags(text: str) -> str:
    return re.sub(r"#\w+", " ", text or "").strip()


FEATURES = {
    "asks a question": lambda c: "?" in c,
    "contains a number": lambda c: bool(re.search(r"\d", c)),
    "opens with a number": lambda c: bool(re.match(r"^\W*\d", c)),
    "addresses the viewer ('you')": lambda c: bool(re.search(r"\byou\b|\byour\b", c, re.I)),
    "first person ('I', 'my')": lambda c: bool(re.search(r"\bi\b|\bmy\b|\bi'm\b", c, re.I)),
    "how-to framing": lambda c: bool(re.search(r"\bhow to\b|\bhow i\b", c, re.I)),
    "uses emoji": lambda c: bool(_EMOJI.search(c)),
    "has a call to action": lambda c: bool(re.search(
        r"\bcomment\b|\bfollow\b|\bsave\b|\bshare\b|\btag\b|\blink in bio\b|\bdm\b", c, re.I)),
    "SHOUTS a word": lambda c: bool(re.search(r"\b[A-Z]{3,}\b", c)),
    "mentions another account": lambda c: "@" in c,
    "no caption text": lambda c: not _strip_tags(c),
}


def features(videos: list[dict]) -> list[dict]:
    """Test each structural feature against reach."""
    rows = []
    for name, fn in FEATURES.items():
        has, hasnt = [], []
        for v in videos:
            c = caption(v)
            (has if fn(c) else hasnt).append(v.get("views") or 0)
        if len(has) < 3:
            continue
        avg_has = round(sum(has) / len(has)) if has else 0
        avg_not = round(sum(hasnt) / len(hasnt)) if hasnt else 0
        p, verdict = welch_verdict(has, hasnt)
        rows.append({
            "feature": name,
            "n_with": len(has),
            "n_without": len(hasnt),
            "avg_with": avg_has,
            "avg_without": avg_not,
            "lift": round((avg_has / avg_not - 1) * 100) if avg_not else 0,
            "p": p,
            "verdict": verdict,
        })
    rows.sort(key=lambda r: -r["lift"])
    return rows


def _opener(text: str) -> str:
    words = _WORD.findall(_strip_tags(text).lower())
    return " ".join(words[:OPENER_WORDS])


def repetition(videos: list[dict]) -> dict:
    """How templated are the openers, and does repeating one cost reach?"""
    openers: dict[str, list[dict]] = {}
    for v in videos:
        key = _opener(caption(v))
        if not key:
            continue
        openers.setdefault(key, []).append(v)

    templated = {k: vs for k, vs in openers.items() if len(vs) >= TEMPLATE_MIN}
    captioned = [v for v in videos if _opener(caption(v))]
    n_templated = sum(len(vs) for vs in templated.values())

    rows = []
    for key, vs in sorted(templated.items(), key=lambda kv: -len(kv[1])):
        mine = [v.get("views") or 0 for v in vs]
        ids = {v["video_id"] for v in vs}
        rest = [v.get("views") or 0 for v in captioned if v["video_id"] not in ids]
        p, verdict = welch_verdict(mine, rest)
        avg_rest = round(sum(rest) / len(rest)) if rest else 0
        avg_mine = round(sum(mine) / len(mine))
        rows.append({
            "opener": key,
            "n": len(vs),
            "avg": avg_mine,
            "vs_rest": round((avg_mine / avg_rest - 1) * 100) if avg_rest else 0,
            "p": p,
            "verdict": verdict,
        })

    # Pooled test: every templated post against every non-templated one.
    pooled_p, pooled_verdict = 1.0, "too early to tell"
    if templated:
        tmpl_ids = {v["video_id"] for vs in templated.values() for v in vs}
        a = [v.get("views") or 0 for v in captioned if v["video_id"] in tmpl_ids]
        b = [v.get("views") or 0 for v in captioned if v["video_id"] not in tmpl_ids]
        pooled_p, pooled_verdict = welch_verdict(a, b)

    return {
        "distinct_openers": len(openers),
        "captioned_posts": len(captioned),
        "templated_posts": n_templated,
        "templated_share": round(n_templated / len(captioned) * 100, 1) if captioned else 0.0,
        "repeated_openers": rows[:12],
        "pooled_p": pooled_p,
        "pooled_verdict": pooled_verdict,
    }


def winning_hooks(videos: list[dict], limit: int = 12) -> list[dict]:
    """Actual openers from the account's best-performing posts.

    The calendar draws its hook suggestions from here rather than from a
    generic swipe file, so what comes back is in the creator's own voice.
    """
    avg = (sum(v.get("views") or 0 for v in videos) / len(videos)) if videos else 0
    winners = [v for v in videos if (v.get("views") or 0) > avg * 1.2 and _strip_tags(caption(v))]
    winners.sort(key=lambda v: -(v.get("views") or 0))
    seen: set[str] = set()
    out = []
    for v in winners:
        text = _strip_tags(caption(v)).replace("\n", " ").strip()
        key = _opener(text)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "hook": texttool.truncate(text, 140),
            "views": v.get("views") or 0,
            "index": round((v.get("views") or 0) / avg * 100) if avg else 100,
            "theme": v.get("theme") or "",
            "url": v.get("url") or "",
        })
        if len(out) >= limit:
            break
    return out


def build(videos: list[dict]) -> dict:
    return {
        "features": features(videos),
        "repetition": repetition(videos),
        "winning_hooks": winning_hooks(videos),
    }
