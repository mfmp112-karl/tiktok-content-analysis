"""What the niche is posting, read through the stealth browser.

This replaces a paid research API. TikTok's own search and hashtag pages are
public, and camofox can read them without getting bot-blocked, so the demand
signal costs nothing per run. The trade is that it is slower and noisier than an
API would be — a scroll of a hashtag page is a sample, not a census — and the
report is explicit about that rather than presenting it as exhaustive.

Peer profiles are read for a different reason: to see how other accounts in the
same niche describe who they are for. Positioning is visible in a bio in a way
it never is in a view count.
"""
from __future__ import annotations

import re
import urllib.parse

from ..harvest import camofox

#: How deep to scroll each page. Small on purpose — this is a temperature
#: reading, and each extra scroll is another request against a public site.
DEFAULT_SCROLLS = 8
MAX_TOPICS = 4
MAX_PEERS = 6

#: Discovery tags, not topics. They are on almost every post in every niche, so
#: they dominate any frequency count while saying nothing about subject matter.
#: Without this filter the calendar ends up instructing someone to "teach one
#: thing about #fyp", which is not a content idea.
GENERIC_TAGS = {
    "fyp", "fypシ", "fypage", "foryou", "foryoupage", "viral", "viralvideo",
    "trending", "trend", "tiktok", "explore", "xyzbca", "capcut", "duet",
    "funny", "comedy", "love", "follow", "like", "video", "reels", "shorts",
}

_WORD = re.compile(r"[a-z][a-z'’]+")
_TAG = re.compile(r"#(\w+)")


def candidate_tags(topic: str) -> list[str]:
    """Plausible real hashtags for a theme label, most likely first.

    Theme labels are phrases like "workout and glutes". Concatenating the whole
    phrase produces #workoutandglutes, which does not exist and earns a 410 —
    so the individual words are tried first, since those are the tags people
    actually use.
    """
    words = [w for w in re.split(r"[^a-z0-9]+", topic.lower()) if len(w) > 2
             and w not in ("and", "the", "your", "with")]
    tags = list(words)
    if len(words) >= 2:
        tags.append("".join(words[:2]))
    return tags[:3]


def hashtag_page(topic: str, *, scrolls: int = DEFAULT_SCROLLS, log=print) -> dict:
    """Try the likeliest real hashtags for this theme; first one that loads wins."""
    last_error = None
    for tag in candidate_tags(topic):
        url = f"https://www.tiktok.com/tag/{urllib.parse.quote(tag)}"
        log(f"    #{tag}")
        try:
            cards = camofox.scroll_harvest(url, max_scrolls=scrolls, log=log)
        except camofox.PageUnavailable as exc:
            log(f"      no such tag ({exc})")
            last_error = exc
            continue
        if cards:
            return _summarise(topic, cards, source=f"#{tag}")
    if last_error:
        log(f"    no usable hashtag for {topic!r}")
    return _summarise(topic, [], source="no hashtag found")


def search_page(topic: str, *, scrolls: int = DEFAULT_SCROLLS, log=print) -> dict:
    url = "https://www.tiktok.com/search?q=" + urllib.parse.quote(topic)
    log(f"    search: {topic}")
    cards = camofox.scroll_harvest(url, max_scrolls=scrolls, log=log)
    return _summarise(topic, cards, source=f"search '{topic}'")


def _summarise(topic: str, cards: list[dict], *, source: str) -> dict:
    views = [c["views"] for c in cards if c.get("views")]
    tags: dict[str, int] = {}
    creators: dict[str, int] = {}
    for c in cards:
        for t in _TAG.findall(c.get("text", "")):
            key = t.lower()
            tags[key] = tags.get(key, 0) + 1
        if c.get("creator"):
            creators[c["creator"]] = creators.get(c["creator"], 0) + 1

    top_tags = sorted(tags.items(), key=lambda kv: -kv[1])[:8]
    top_creators = sorted(creators.items(), key=lambda kv: -kv[1])[:MAX_PEERS]
    return {
        "topic": topic,
        "source": source,
        "posts": len(cards),
        "median_views": sorted(views)[len(views) // 2] if views else None,
        "top_hashtags": [f"#{t}" for t, _ in top_tags],
        "creators": [c for c, _ in top_creators],
        "evidence": ", ".join(f"#{t}" for t, _ in top_tags[:4]) or f"{len(cards)} posts seen",
    }


def peers(handles: list[str], *, log=print) -> list[dict]:
    """Read how neighbouring accounts position themselves."""
    out = []
    for handle in handles[:MAX_PEERS]:
        handle = handle.lstrip("@").lower()
        try:
            data = camofox.profile(handle, log=log)
        except Exception as exc:
            # One unreadable peer must not cost the other five, let alone the run.
            log(f"    @{handle}: {type(exc).__name__}: {exc}")
            continue
        if not data:
            continue
        out.append({
            "handle": handle,
            "nickname": data.get("nickname"),
            "followers": data.get("followers"),
            "bio": (data.get("bio") or "").replace("\n", " ").strip(),
            "link": data.get("link") or "",
        })
    return out


def audience_words(peer_rows: list[dict]) -> list[str]:
    """Words peers repeatedly use to name who they are for."""
    from ..analyse.themes import STOPWORDS
    counts: dict[str, int] = {}
    for p in peer_rows:
        for w in set(_WORD.findall((p.get("bio") or "").lower())):
            if len(w) > 3 and w not in STOPWORDS:
                counts[w] = counts.get(w, 0) + 1
    return [w for w, n in sorted(counts.items(), key=lambda kv: -kv[1]) if n >= 2][:12]


def run(topics: list[str], *, scrolls: int = DEFAULT_SCROLLS,
        with_peers: bool = True, exclude: list[str] | None = None,
        log=print) -> dict:
    """Gather demand signal for the shortlisted themes.

    Returns topics, peer profiles and a coverage report. If camofox is not
    running, everything comes back empty and coverage says exactly why.
    """
    coverage = []
    if not camofox.healthy():
        coverage.append({
            "source": "TikTok (via camofox)", "ok": False,
            "note": "camofox is not running, so no TikTok research was gathered.",
        })
        return {"topics": [], "peers": [], "audience_words": [], "coverage": coverage,
                "gaps": []}

    rows, peer_handles = [], []
    for topic in topics[:MAX_TOPICS]:
        row = None
        try:
            row = hashtag_page(topic, scrolls=scrolls, log=log)
        except Exception as exc:
            log(f"    {topic}: hashtag route failed - {type(exc).__name__}: {exc}")
        # Search is the fallback for *both* "no such tag" and "the tag route
        # raised", not only for a tag that loaded and happened to be empty.
        if row is None or not row["posts"]:
            try:
                row = search_page(topic, scrolls=scrolls, log=log)
            except Exception as exc:
                log(f"    {topic}: search route failed - {type(exc).__name__}: {exc}")
                coverage.append({"source": f"TikTok '{topic}'", "ok": False,
                                 "note": str(exc)[:120]})
                continue
        rows.append(row)
        peer_handles.extend(row["creators"])

    reached = sum(r["posts"] for r in rows)
    coverage.append({
        "source": "TikTok (via camofox)",
        "ok": reached > 0,
        "note": (f"{reached} posts sampled across {len(rows)} topic pages"
                 if reached else "pages opened but no cards were readable"),
    })

    peer_rows = []
    if with_peers and peer_handles:
        seen, ordered = set(), []
        for h in peer_handles:
            if h.lower() not in seen:
                seen.add(h.lower())
                ordered.append(h)
        log("  reading peer profiles...")
        peer_rows = peers(ordered, log=log)
        coverage.append({
            "source": "Peer profiles", "ok": bool(peer_rows),
            "note": f"{len(peer_rows)} of {len(ordered[:MAX_PEERS])} read",
        })

    # Hashtags the niche uses a lot that this account does not already cover.
    # Filtered twice: generic discovery tags carry no topic, and a tag the
    # account already posts under is not a gap — suggesting it back would be
    # telling someone to start doing the thing they are already doing.
    own = {t.lstrip("#").lower() for t in (exclude or [])}
    gaps: list[str] = []
    for r in rows:
        for tag in r["top_hashtags"]:
            bare = tag.lstrip("#").lower()
            if bare in GENERIC_TAGS or bare in own or tag in gaps:
                continue
            gaps.append(tag)

    return {
        "topics": rows,
        "peers": peer_rows,
        "audience_words": audience_words(peer_rows),
        "coverage": coverage,
        "gaps": gaps[:3],
    }
