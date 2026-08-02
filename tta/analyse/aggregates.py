"""Every aggregate the report draws on, each one significance-tested.

The central idea is `split()`: carve the catalogue by some property, and for
each bucket report its size, its average reach *indexed against the account's
own average*, and whether that gap survives Welch's t-test against everything
else. Indexing matters because raw view counts are meaningless across accounts
of different sizes; the verdict matters because without it a six-post bucket
reads exactly like a six-hundred-post one.

A note on time: upload timestamps come back as Unix epochs and are converted in
the machine's local timezone. For a creator analysing their own account that is
almost always the right frame, but the report says so on its method page rather
than letting the reader assume UTC.
"""
from __future__ import annotations

import re
import statistics as st
from collections import defaultdict
from datetime import datetime

from ..stats import posts_needed, welch_verdict

#: Short-form duration buckets. Anything past a minute is "long" on TikTok.
DURATION_BUCKETS = [
    (0, 10, "under 10s"),
    (10, 20, "10-20s"),
    (20, 35, "20-35s"),
    (35, 60, "35-60s"),
    (60, 10 ** 6, "over 60s"),
]

CAPTION_BUCKETS = [
    (0, 40, "very short (<40)"),
    (40, 90, "short (40-90)"),
    (90, 160, "medium (90-160)"),
    (160, 10 ** 6, "long (160+)"),
]

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
            "Saturday", "Sunday"]

_HASHTAG = re.compile(r"#(\w+)")
_REPLY = re.compile(r"^\s*(reply to|replying to)\b", re.IGNORECASE)


def when(v: dict) -> datetime | None:
    raw = v.get("uploaded")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def caption(v: dict) -> str:
    return (v.get("title") or "").strip()


def hashtags(v: dict) -> list[str]:
    return [h.lower() for h in _HASHTAG.findall(caption(v))]


def is_reply(v: dict) -> bool:
    return bool(_REPLY.match(caption(v)))


def _bucket(value, buckets, default="unknown"):
    if value is None:
        return default
    for lo, hi, label in buckets:
        if lo <= value < hi:
            return label
    return default


# --------------------------------------------------------------------------- KPIs

def kpi(videos: list[dict]) -> dict:
    views = sorted(v.get("views") or 0 for v in videos)
    n = len(views)
    if not n:
        return {"n": 0}
    dates = [d for d in (when(v) for v in videos) if d]
    span = (max(dates) - min(dates)).days + 1 if dates else 0
    total_views = sum(views)

    def rate(field: str) -> float:
        got = sum(v.get(field) or 0 for v in videos)
        return round(got / total_views * 100, 2) if total_views else 0.0

    return {
        "n": n,
        "total_views": total_views,
        "avg": round(total_views / n),
        "median": round(st.median(views)),
        "p90": views[min(int(n * 0.9), n - 1)],
        "p10": views[int(n * 0.1)],
        "best": views[-1],
        "worst": views[0],
        "start": min(dates) if dates else None,
        "end": max(dates) if dates else None,
        "span_days": span,
        "per_week": round(n / span * 7, 1) if span else 0.0,
        "like_rate": rate("likes"),
        "comment_rate": rate("comments"),
        "share_rate": rate("shares"),
    }


# -------------------------------------------------------------------- the workhorse

def split(videos: list[dict], keyfn, *, label: str, min_n: int = 3,
          order=None) -> list[dict]:
    """Group by `keyfn` and significance-test each group against the rest.

    Returns rows sorted by index descending, or in `order` when the buckets have
    a natural sequence (days of the week should not be sorted by performance —
    a reader scans them as a calendar).
    """
    overall_avg = kpi(videos)["avg"] if videos else 0
    groups: dict[str, list[dict]] = defaultdict(list)
    for v in videos:
        k = keyfn(v)
        if k is not None:
            groups[str(k)].append(v)

    rows = []
    for name, members in groups.items():
        if len(members) < min_n:
            continue
        mine = [m.get("views") or 0 for m in members]
        ids = {m["video_id"] for m in members}
        rest = [v.get("views") or 0 for v in videos if v["video_id"] not in ids]
        p, verdict = welch_verdict(mine, rest)
        # For anything undecided, work out what would decide it. A verdict that
        # only says "unknown" gives the reader nowhere to go.
        need = posts_needed(mine, rest) if verdict == "too early to tell" else None
        avg = round(sum(mine) / len(mine))
        rows.append({
            "name": name,
            "n": len(members),
            "share": round(len(members) / len(videos) * 100, 1),
            "avg": avg,
            "median": round(st.median(mine)),
            "index": round(avg / overall_avg * 100) if overall_avg else 100,
            "delta": round((avg / overall_avg - 1) * 100) if overall_avg else 0,
            "p": p,
            "verdict": verdict,
            "needs": need,
            "dimension": label,
        })

    if order:
        pos = {name: i for i, name in enumerate(order)}
        rows.sort(key=lambda r: pos.get(r["name"], 999))
    else:
        rows.sort(key=lambda r: -r["index"])
    return rows


# --------------------------------------------------------------------- dimensions

def by_weekday(videos):
    return split(videos, lambda v: (when(v).strftime("%A") if when(v) else None),
                 label="day of week", order=WEEKDAYS)


def by_hour(videos):
    rows = split(videos, lambda v: (f"{when(v).hour:02d}:00" if when(v) else None),
                 label="hour of day")
    return sorted(rows, key=lambda r: r["name"])


def by_duration(videos):
    return split(videos, lambda v: _bucket(v.get("duration"), DURATION_BUCKETS),
                 label="video length",
                 order=[b[2] for b in DURATION_BUCKETS])


def by_caption_length(videos):
    return split(videos, lambda v: _bucket(len(caption(v)), CAPTION_BUCKETS),
                 label="caption length",
                 order=[b[2] for b in CAPTION_BUCKETS])


def by_format(videos):
    return split(videos, lambda v: "reply to a comment" if is_reply(v) else "original post",
                 label="post format")


def by_hashtag_count(videos):
    def bucket(v):
        n = len(hashtags(v))
        return "no hashtags" if n == 0 else ("1-3 hashtags" if n <= 3 else "4+ hashtags")
    return split(videos, bucket, label="hashtag use",
                 order=["no hashtags", "1-3 hashtags", "4+ hashtags"])


def by_theme(videos):
    return split(videos, lambda v: v.get("theme"), label="theme")


def monthly(videos: list[dict]) -> list[dict]:
    """Reach trajectory. Not significance-tested — it is a time series, and the
    question it answers is 'which way is this going', not 'is this bucket real'."""
    groups: dict[str, list[int]] = defaultdict(list)
    for v in videos:
        d = when(v)
        if d:
            groups[d.strftime("%Y-%m")].append(v.get("views") or 0)
    rows = []
    for month in sorted(groups):
        vals = groups[month]
        rows.append({
            "month": month,
            "posts": len(vals),
            "avg": round(sum(vals) / len(vals)),
            "median": round(st.median(vals)),
            "best": max(vals),
        })
    return rows


def all_hashtags(videos: list[dict]) -> set[str]:
    """Every hashtag the account has used even once.

    Distinct from `top_hashtags`, which only reports tags used three or more
    times. For deciding what is a *gap* in someone's coverage, a single use is
    still coverage — suggesting #gym to an account that has posted it twice is
    not a content idea, it is noise.
    """
    tags: set[str] = set()
    for v in videos:
        tags.update(hashtags(v))
    return tags


def top_hashtags(videos: list[dict], limit: int = 15) -> list[dict]:
    counts: dict[str, list[int]] = defaultdict(list)
    for v in videos:
        for h in set(hashtags(v)):
            counts[h].append(v.get("views") or 0)
    overall = kpi(videos)["avg"] if videos else 0
    rows = [{
        "tag": f"#{tag}",
        "n": len(vals),
        "avg": round(sum(vals) / len(vals)),
        "index": round(sum(vals) / len(vals) / overall * 100) if overall else 100,
    } for tag, vals in counts.items() if len(vals) >= 3]
    rows.sort(key=lambda r: -r["n"])
    return rows[:limit]


def leaderboard(videos: list[dict], n: int = 10) -> dict:
    ranked = sorted(videos, key=lambda v: -(v.get("views") or 0))
    return {"top": ranked[:n], "bottom": ranked[-n:][::-1]}


def build(videos: list[dict]) -> dict:
    """Everything the report and the calendar need, in one pass."""
    return {
        "kpi": kpi(videos),
        "weekday": by_weekday(videos),
        "hour": by_hour(videos),
        "duration": by_duration(videos),
        "caption_length": by_caption_length(videos),
        "format": by_format(videos),
        "hashtag_use": by_hashtag_count(videos),
        "theme": by_theme(videos),
        "monthly": monthly(videos),
        "top_hashtags": top_hashtags(videos),
        "leaderboard": leaderboard(videos),
    }
