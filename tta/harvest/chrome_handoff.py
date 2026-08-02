"""Tier 3: hand the job to the user's own browser, with their permission.

When both yt-dlp and camofox are blocked, the only thing left that TikTok will
reliably serve is a real, already-logged-in browser session. This module does
**not** drive that browser. It produces the instructions for an agent to do so
and the ingest function for whatever comes back.

That separation is the point. Tier 3 uses the user's authenticated session on a
site they are logged into, which is not something a script should reach for on
its own initiative. So the flow is: this module says what is needed, the agent
asks the user, and nothing happens until the user says yes.
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import store

#: Run in the page's console (or by an agent driving the real browser) to read
#: the grid. Same fields as the other two tiers produce.
EXTRACT_JS = r"""
(() => {
  const out = [];
  document.querySelectorAll('a[href*="/video/"]').forEach(a => {
    const m = a.href.match(/@([\w.\-]+)\/video\/(\d+)/);
    if (!m) return;
    const card = a.closest('[data-e2e]') || a.parentElement || a;
    const views = card.querySelector('[data-e2e*="video-views"], strong[title]');
    const img = card.querySelector('img[alt]');
    out.push({
      video_id: m[2],
      creator: m[1],
      url: a.href.split('?')[0],
      views_text: views ? views.textContent.trim() : '',
      title: img ? (img.getAttribute('alt') || '') : ''
    });
  });
  return JSON.stringify(out);
})()
"""


def permission_request(handle: str) -> str:
    """What the agent should put to the user before touching their browser."""
    return (
        f"Both the public data path and the stealth browser were blocked for "
        f"@{handle}.\n\n"
        f"The remaining option is to read the profile through your own Chrome, "
        f"using the session you are already signed into. That means this tool "
        f"would be acting inside your logged-in TikTok account — read-only, no "
        f"posting, no following, no messages — but it is your account, so it "
        f"needs your explicit go-ahead.\n\n"
        f"May I open https://www.tiktok.com/@{handle} in your browser and read "
        f"the video grid? Say no and the run will finish with whatever was "
        f"already gathered."
    )


def instructions(handle: str) -> str:
    return (
        f"1. Open https://www.tiktok.com/@{handle}\n"
        f"2. Scroll to the bottom of the video grid so every post has loaded.\n"
        f"3. Evaluate the script in `chrome_handoff.EXTRACT_JS` and save the "
        f"JSON it returns.\n"
        f"4. Feed it back with `ingest(conn, handle, path_or_list)`."
    )


def ingest(conn, handle: str, payload) -> int:
    """Accept whatever the browser produced and store it like any other tier."""
    from .camofox import parse_count

    if isinstance(payload, (str, Path)) and Path(str(payload)).exists():
        payload = json.loads(Path(str(payload)).read_text(encoding="utf-8"))
    elif isinstance(payload, str):
        payload = json.loads(payload)
    if isinstance(payload, dict):
        payload = payload.get("items") or payload.get("videos") or []

    handle = store.norm_handle(handle)
    rows = []
    for item in payload or []:
        vid = str(item.get("video_id") or item.get("id") or "").strip()
        if not vid:
            continue
        views = item.get("views")
        if views is None:
            views = parse_count(item.get("views_text", "")) or 0
        rows.append({
            "video_id": vid,
            "url": item.get("url") or f"https://www.tiktok.com/@{handle}/video/{vid}",
            "title": item.get("title") or "",
            "views": views,
            "likes": item.get("likes") or 0,
            "comments": item.get("comments") or 0,
            "shares": item.get("shares") or 0,
            "duration": item.get("duration"),
            "uploaded": item.get("uploaded"),
        })
    written = store.upsert_videos(conn, handle, rows)
    conn.commit()
    return written
