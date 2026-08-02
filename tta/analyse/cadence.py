"""How often they post, and whether it actually buys them anything.

"Post daily" is the most repeated piece of creator advice there is, and it is
plausible: more posts means more shots on goal and faster learning. But it is
still a claim, and this tool has an account's real history sitting right there,
so it gets tested rather than repeated.

The test compares months where the account posted above its own median rate
against months where it posted below, on the reach of the posts themselves. A
"too early to tell" here is the common and correct answer for most accounts,
and is far more useful than a confident rule pulled from someone else's data.
"""
from __future__ import annotations

import statistics as st
from collections import defaultdict
from datetime import timedelta

from ..stats import welch_verdict
from .aggregates import when


def _by_month(videos: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for v in videos:
        d = when(v)
        if d:
            groups[d.strftime("%Y-%m")].append(v)
    return groups


def gaps(videos: list[dict]) -> dict:
    """Streaks and silences, in days."""
    dates = sorted({d.date() for d in (when(v) for v in videos) if d})
    if len(dates) < 2:
        return {"longest_gap": 0, "longest_streak": 0, "median_gap": 0.0,
                "active_days": len(dates), "silences": []}

    deltas = [(b - a).days for a, b in zip(dates, dates[1:])]
    streak = best_streak = 1
    for gap in deltas:
        streak = streak + 1 if gap == 1 else 1
        best_streak = max(best_streak, streak)

    silences = []
    for a, b in zip(dates, dates[1:]):
        if (b - a).days >= 7:
            silences.append({"from": a.isoformat(), "to": b.isoformat(),
                             "days": (b - a).days})
    silences.sort(key=lambda s: -s["days"])

    return {
        "longest_gap": max(deltas),
        "longest_streak": best_streak,
        "median_gap": round(st.median(deltas), 1),
        "active_days": len(dates),
        "silences": silences[:5],
    }


def consistency(videos: list[dict]) -> dict:
    """Does posting more in a month go with better reach in that month?"""
    months = _by_month(videos)
    if len(months) < 4:
        return {"verdict": "too early to tell", "p": 1.0,
                "note": "fewer than four months of history",
                "busy_avg": 0, "quiet_avg": 0, "median_posts": 0}

    counts = {m: len(vs) for m, vs in months.items()}
    median_posts = st.median(counts.values())
    busy, quiet = [], []
    for m, vs in months.items():
        target = busy if counts[m] > median_posts else quiet
        target.extend(v.get("views") or 0 for v in vs)

    p, verdict = welch_verdict(busy, quiet)
    return {
        "verdict": verdict,
        "p": p,
        "median_posts": median_posts,
        "busy_avg": round(sum(busy) / len(busy)) if busy else 0,
        "quiet_avg": round(sum(quiet) / len(quiet)) if quiet else 0,
        "busy_n": len(busy),
        "quiet_n": len(quiet),
        "note": "",
    }


def rhythm(videos: list[dict]) -> dict:
    """Posts per week, recent versus lifetime."""
    dates = sorted(d for d in (when(v) for v in videos) if d)
    if not dates:
        return {"per_week": 0.0, "recent_per_week": 0.0, "trend": "no dates"}

    span = max(1, (dates[-1] - dates[0]).days)
    per_week = round(len(dates) / span * 7, 1)

    cutoff = dates[-1] - timedelta(days=56)
    recent = [d for d in dates if d >= cutoff]
    recent_span = max(1, (dates[-1] - max(cutoff, dates[0])).days)
    recent_per_week = round(len(recent) / recent_span * 7, 1)

    if recent_per_week > per_week * 1.25:
        trend = "speeding up"
    elif recent_per_week < per_week * 0.75:
        trend = "slowing down"
    else:
        trend = "steady"

    return {"per_week": per_week, "recent_per_week": recent_per_week, "trend": trend}


def best_slot(weekday_rows: list[dict], hour_rows: list[dict]) -> dict:
    """The day and hour to anchor the calendar on.

    Only returns a *confident* slot when the split actually cleared
    significance. Otherwise it hands back the best-indexing option clearly
    labelled as unproven, so the calendar can still be built without the report
    pretending it knows something it does not.
    """
    def pick(rows):
        if not rows:
            return None, False
        proven = [r for r in rows if r["verdict"] in ("strong", "moderate")]
        pool = proven or rows
        best = max(pool, key=lambda r: r["index"])
        return best, bool(proven)

    day, day_proven = pick(weekday_rows)
    hour, hour_proven = pick(hour_rows)
    return {
        "day": day["name"] if day else None,
        "day_index": day["index"] if day else None,
        "day_proven": day_proven,
        "hour": hour["name"] if hour else None,
        "hour_index": hour["index"] if hour else None,
        "hour_proven": hour_proven,
    }


def build(videos: list[dict], weekday_rows=None, hour_rows=None) -> dict:
    return {
        "gaps": gaps(videos),
        "consistency": consistency(videos),
        "rhythm": rhythm(videos),
        "best_slot": best_slot(weekday_rows or [], hour_rows or []),
    }
