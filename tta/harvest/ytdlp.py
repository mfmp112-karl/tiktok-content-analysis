"""Tier 1: enumerate a public account's whole catalogue with yt-dlp.

yt-dlp's *flat* enumeration already carries per-video metrics — views, likes,
comments, repost_count, timestamp, duration, title — at roughly 70ms per video.
One bulk pass gets everything without downloading a single video file, which is
why this is the default path and why the tool needs no API key.

The awkward part is that **TikTok throttles deep pagination non-deterministically**.
The same call has returned 630, then 1,000, then the full 1,824 videos on
consecutive tries. So we enumerate repeatedly and accumulate the union until an
attempt stops adding anything new. Each pass is written to the database before
the next one starts, so a run interrupted halfway leaves real progress behind
rather than nothing.
"""
from __future__ import annotations

import time
from datetime import datetime, date

from .. import store

DEFAULT_CAP = 3000        # well above any realistic single-account catalogue
DEFAULT_ATTEMPTS = 4
POLITE_GAP = 3.0          # seconds between passes


class HarvestBlocked(RuntimeError):
    """Raised when enumeration yields nothing — the trigger for tier 2."""


def _entry_to_row(entry: dict, handle: str) -> dict:
    ts = entry.get("timestamp")
    vid = str(entry["id"])
    return {
        "video_id": vid,
        "url": entry.get("url") or f"https://www.tiktok.com/@{handle}/video/{vid}",
        "title": entry.get("title") or "",
        "views": entry.get("view_count") or 0,
        "likes": entry.get("like_count") or 0,
        "comments": entry.get("comment_count") or 0,
        # yt-dlp reports TikTok shares under repost_count.
        "shares": entry.get("repost_count") or 0,
        "reposts": 0,
        "duration": entry.get("duration"),
        "uploaded": datetime.fromtimestamp(ts).isoformat(timespec="seconds") if ts else None,
    }


def _enumerate(handle: str, cap: int, cookies: str | None = None) -> tuple[dict, dict]:
    import yt_dlp
    from . import session
    opts = {
        "extract_flat": "in_playlist",
        "quiet": True,
        "no_warnings": True,
        "playlistend": cap,
        "ignoreerrors": True,
        **session.ytdlp_opts(cookies),
    }
    with yt_dlp.YoutubeDL(opts) as y:
        info = y.extract_info(f"https://www.tiktok.com/@{handle}", download=False) or {}
    entries = {str(e["id"]): e for e in (info.get("entries") or []) if e and e.get("id")}
    return entries, info


def _profile_from(info: dict) -> dict:
    """Only the keys yt-dlp actually returned.

    Missing keys are omitted rather than written as NULL, so a later camofox
    capture that *does* know the follower count is not overwritten by a
    yt-dlp pass that doesn't.
    """
    raw = {
        "nickname": info.get("channel") or info.get("uploader") or info.get("title"),
        "followers": info.get("channel_follower_count"),
        "bio": info.get("description"),
    }
    return {k: v for k, v in raw.items() if v not in (None, "")}


def pull(conn, handle: str, *, cap: int = DEFAULT_CAP, attempts: int = DEFAULT_ATTEMPTS,
         since: date | None = None, cookies: str | None = None,
         log=print) -> dict:
    """Enumerate and store one account. Returns a summary dict.

    Raises HarvestBlocked when nothing at all came back, which is the caller's
    signal to try the stealth browser instead.
    """
    handle = store.norm_handle(handle)
    already = store.known_video_ids(conn, handle)
    collected: dict[str, dict] = {}
    info: dict = {}
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        log(f"  pass {attempt}/{attempts}: enumerating @{handle} (cap {cap})...")
        started = time.time()
        try:
            entries, this_info = _enumerate(handle, cap, cookies)
        except Exception as exc:                 # network, throttle, private account
            last_error = exc
            log(f"    failed: {type(exc).__name__}: {exc}")
            if attempt < attempts:
                time.sleep(POLITE_GAP)
            continue

        info = this_info or info
        before = len(collected)
        collected.update(entries)
        gained = len(collected) - before
        log(f"    +{gained} new (total {len(collected)}) in {time.time() - started:.0f}s")

        # Persist this pass before attempting the next, so an interrupted run
        # still leaves the videos it did manage to reach.
        if gained:
            rows = [_entry_to_row(e, handle) for e in collected.values()]
            if since:
                rows = [r for r in rows if r["uploaded"] and
                        datetime.fromisoformat(r["uploaded"]).date() >= since]
            store.upsert_videos(conn, handle, rows)
            conn.commit()

        if gained == 0 and attempt > 1:
            log("    depth has stabilised")
            break
        if attempt < attempts:
            time.sleep(POLITE_GAP)

    if not collected:
        raise HarvestBlocked(
            f"yt-dlp enumerated nothing for @{handle}. The account may be private, "
            f"renamed, or TikTok may be blocking this machine."
            + (f" Last error: {last_error}" if last_error else "")
        )

    profile = _profile_from(info)
    if profile:
        store.upsert_creator(conn, handle, **profile)

    rows = [_entry_to_row(e, handle) for e in collected.values()]
    if since:
        rows = [r for r in rows if r["uploaded"] and
                datetime.fromisoformat(r["uploaded"]).date() >= since]
    store.upsert_videos(conn, handle, rows)
    store.upsert_creator(conn, handle, video_count=len(rows))
    conn.commit()

    fresh = {r["video_id"] for r in rows} - already
    return {
        "tier": "yt-dlp",
        "enumerated": len(collected),
        "stored": len(rows),
        "new": len(fresh),
        "already_had": len(already),
        "profile": profile,
    }
