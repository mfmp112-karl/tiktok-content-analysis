"""Driving the camofox stealth browser over its REST API.

camofox wraps Camoufox, a Firefox fork with fingerprint spoofing done in C++,
which is what makes it useful when TikTok decides a machine looks automated.
This module is a thin client — it does not vendor or patch the skill, so the
upstream stays upgradable.

**The important discovery:** camofox exposes `POST /tabs/:id/evaluate`, which
runs arbitrary JavaScript in the page and hands back the result as JSON. Its own
SKILL.md and API reference do not mention it — they document only navigate,
click, type, scroll, snapshot, links and screenshot. That omission matters a
great deal here, because TikTok server-renders everything worth having into a
`__UNIVERSAL_DATA_FOR_REHYDRATION__` script tag. Reading that directly gives
exact follower counts, the bio, the avatar URL and the video list as structured
data, instead of regexing numbers out of an accessibility tree.

Three behaviours are not optional, all learned by watching it fail:

* **The first page load is slow.** Camoufox cold-starts well past the server's
  own timeout and returns a 500. Retry rather than give up.
* **The browser restarts underneath you.** Requests then fail with
  `browser_restarted` and every existing tab id is void. Open a fresh one.
* **TikTok needs time to settle.** At six seconds a profile still reads as a
  login wall; at twelve the real page is there. Polling for the data beats
  guessing a number.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

PORT = int(os.getenv("CAMOFOX_PORT", "9377"))
HOST = os.getenv("CAMOFOX_HOST", "127.0.0.1")
BASE = f"http://{HOST}:{PORT}"
USER_ID = "tta"

OPEN_ATTEMPTS = 4
SETTLE_POLLS = 8
SETTLE_GAP = 2.5


class CamofoxError(RuntimeError):
    pass


class BrowserRestarted(CamofoxError):
    """Every tab id is stale; open a new one."""


class PageUnavailable(CamofoxError):
    """The page itself said no — 404, 410 and friends. Not worth retrying."""


def _api(method: str, path: str, body: dict | None = None, timeout: int = 60,
         raw: bool = False):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = resp.read()
    if raw:
        return payload
    text = payload.decode("utf-8", "replace")
    if not text.strip().startswith(("{", "[")):
        return text
    out = json.loads(text)
    if isinstance(out, dict) and out.get("code") == "browser_restarted":
        raise BrowserRestarted(out.get("error", "browser restarted"))
    return out


def healthy(timeout: int = 4) -> bool:
    try:
        _api("GET", "/health", timeout=timeout)
        return True
    except Exception:
        return False


def start_server(wrapper: Path | None = None, wait: int = 60, log=print) -> bool:
    """Best effort. The wrapper is bash-only, so on Windows this needs Git Bash."""
    if healthy():
        return True
    server_js = (Path.home() / ".camofox-browser" / "node_modules" /
                 "@askjo" / "camofox-browser" / "server.js")
    try:
        if server_js.exists():
            env = {**os.environ, "PORT": str(PORT)}
            subprocess.Popen(["node", str(server_js)], env=env,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif wrapper and Path(wrapper).exists():
            subprocess.Popen(["bash", str(wrapper), "start"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            return False
    except (FileNotFoundError, OSError) as exc:
        log(f"    could not start camofox: {exc}")
        return False

    for _ in range(wait // 2):
        if healthy():
            return True
        time.sleep(2)
    return False


# ------------------------------------------------------------------------- tabs

def open_url(url: str, *, settle: float = 2.0, log=print) -> str:
    """Open a tab, retrying through the cold-start 500s. Returns the tab id."""
    last = None
    for attempt in range(1, OPEN_ATTEMPTS + 1):
        try:
            tab = _api("POST", "/tabs",
                       {"userId": USER_ID, "sessionKey": "default", "url": url},
                       timeout=120)
            time.sleep(settle)
            return tab["tabId"]
        except urllib.error.HTTPError as exc:
            last = exc
            # 4xx is the page telling us it does not exist or is not allowed.
            # Retrying that is just four times the load on someone else's server
            # for the same answer. Only warm-up and transport errors are worth
            # a second go.
            if 400 <= exc.code < 500 and exc.code != 429:
                raise PageUnavailable(f"{url} returned HTTP {exc.code}") from exc
            log(f"    tab launch {attempt}/{OPEN_ATTEMPTS} failed ({exc})")
            time.sleep(5)
        except (urllib.error.URLError, BrowserRestarted) as exc:
            last = exc
            log(f"    tab launch {attempt}/{OPEN_ATTEMPTS} failed ({exc}); "
                f"the browser may still be warming up")
            time.sleep(5)
    raise CamofoxError(f"camofox could not open {url}: {last}")


def close_tab(tab: str) -> None:
    try:
        _api("DELETE", f"/tabs/{tab}?userId={USER_ID}", timeout=15)
    except Exception:
        pass


def evaluate(tab: str, expression: str, timeout: int = 45):
    """Run JavaScript in the page and return the deserialised result.

    Every failure mode is translated into CamofoxError. Letting a raw
    urllib HTTPError escape from here once took down a whole run from an
    *optional* research step — callers should only ever have to know about
    one exception family.
    """
    try:
        out = _api("POST", f"/tabs/{tab}/evaluate",
                   {"userId": USER_ID, "expression": expression}, timeout=timeout)
    except BrowserRestarted:
        raise
    except urllib.error.HTTPError as exc:
        if 400 <= exc.code < 500 and exc.code != 429:
            raise PageUnavailable(f"evaluate returned HTTP {exc.code}") from exc
        raise CamofoxError(f"evaluate failed: HTTP {exc.code}") from exc
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise CamofoxError(f"evaluate failed: {type(exc).__name__}: {exc}") from exc

    if isinstance(out, dict):
        if out.get("ok"):
            return out.get("result")
        if out.get("error"):
            raise CamofoxError(str(out["error"]))
    return out


def scroll(tab: str, direction: str = "down") -> None:
    _api("POST", f"/tabs/{tab}/scroll", {"userId": USER_ID, "direction": direction},
         timeout=30)


def set_viewport(tab: str, width: int, height: int) -> None:
    try:
        _api("POST", f"/tabs/{tab}/viewport",
             {"userId": USER_ID, "width": width, "height": height}, timeout=20)
    except Exception:
        pass          # older builds lack this endpoint; the default size is fine


def screenshot(tab: str, path: Path, *, full_page: bool = True) -> bool:
    try:
        query = f"?userId={USER_ID}" + ("&fullPage=true" if full_page else "")
        data = _api("GET", f"/tabs/{tab}/screenshot{query}", timeout=120, raw=True)
    except Exception:
        return False
    if not data or not data.startswith(b"\x89PNG"):
        return False
    Path(path).write_bytes(data)
    return True


# ------------------------------------------------------------ TikTok page reading

#: Reads the profile header, trying three sources in descending order of
#: precision. TikTok is inconsistent about which of them a given page load
#: actually ships — the hydration payload is exact but frequently absent, and a
#: reader that depends on it alone will report "login wall" for a page that has
#: rendered perfectly well. So: hydration JSON, then labelled DOM nodes, then
#: the visible text. `source` records which one answered.
PROFILE_JS = """
(() => {
  const text = document.body ? (document.body.innerText || '') : '';
  const out = { ready: false, source: null, walled: false, len: text.length,
                sample: text.slice(0, 120) };

  // 1. the page's own hydration payload - exact numbers when it is there
  const el = document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__');
  if (el) {
    try {
      const scope = JSON.parse(el.textContent)['__DEFAULT_SCOPE__'] || {};
      const d = scope['webapp.user-detail'];
      if (d && d.userInfo) {
        const u = d.userInfo.user || {}, s = d.userInfo.stats || {};
        return { ready: true, source: 'hydration',
                 handle: u.uniqueId || null, nickname: u.nickname || null,
                 bio: u.signature || '', link: (u.bioLink || {}).link || '',
                 avatar: u.avatarLarger || u.avatarMedium || '',
                 verified: !!u.verified, private: !!u.privateAccount,
                 followers: s.followerCount ?? null,
                 following: s.followingCount ?? null,
                 hearts: s.heartCount ?? null, videos: s.videoCount ?? null };
      }
    } catch (e) { /* fall through */ }
  }

  // A wall, not an empty account. TikTok serves the profile shell with every
  // figure rendered as "-" when the creator has audience controls on, or when
  // it wants a login. Reporting that as "private or renamed" sends people
  // looking for the wrong problem.
  const walled = /audience controls|log in to tiktok|log in to make the most/i
                   .test(text);

  // Placeholder dashes are not data. Treating "-" as a value is what made the
  // DOM branch claim success with every field empty.
  const real = (s) => {
    const v = (s || '').trim();
    return (!v || v === '-' || v === '—') ? '' : v;
  };
  const pick = (sel) => { const n = document.querySelector(sel);
                          return real(n ? n.textContent : ''); };
  const meta = (p) => { const n = document.querySelector(`meta[property="${p}"]`);
                        return n ? n.getAttribute('content') || '' : ''; };

  // 2. labelled DOM nodes - counts arrive as display strings like "9.9M"
  const followers = pick('[data-e2e="followers-count"]');
  const following = pick('[data-e2e="following-count"]');
  const likes     = pick('[data-e2e="likes-count"]');
  if (followers) {
    const avatarNode = document.querySelector('[data-e2e="user-avatar"] img, header img');
    return { ready: true, source: 'dom', walled: walled,
             handle: pick('[data-e2e="user-title"]') || null,
             nickname: pick('[data-e2e="user-subtitle"]') || null,
             bio: pick('[data-e2e="user-bio"]') || meta('og:description') || '',
             link: (document.querySelector('[data-e2e="user-link"]') || {}).textContent || '',
             avatar: (avatarNode && avatarNode.src) || meta('og:image') || '',
             verified: !!document.querySelector('[data-e2e="user-verified"]'),
             private: /this account is private/i.test(text),
             followers_text: followers, following_text: following,
             hearts_text: likes, videos: null };
  }

  // 3. the visible text, as a last resort
  const m = text.match(
    /([\\d.,]+[KMB]?)\\s*Following\\s*([\\d.,]+[KMB]?)\\s*Followers\\s*([\\d.,]+[KMB]?)\\s*Likes/i);
  if (m) {
    return { ready: true, source: 'text', walled: walled,
             handle: null, nickname: null,
             bio: meta('og:description') || '', link: '',
             avatar: meta('og:image') || '',
             verified: false, private: /this account is private/i.test(text),
             following_text: m[1], followers_text: m[2], hearts_text: m[3],
             videos: null };
  }
  out.walled = walled;
  return out;
})()
"""

#: Video cards currently in the DOM.
#:
#: Two details make this work where naive scraping does not. The view count is
#: read from the element TikTok labels as such, rather than by grepping the
#: nearest number out of innerText — which happily returns a comment count, a
#: duration, or a stray "7". And the caption comes from the thumbnail image's
#: `alt` attribute, which carries the full caption including hashtags even
#: though nothing on the card displays it.
CARDS_JS = """
(() => {
  const out = [];
  document.querySelectorAll('a[href*="/video/"]').forEach(a => {
    const m = a.href.match(/@([\\w.\\-]+)\\/video\\/(\\d+)/);
    if (!m) return;
    const card = a.closest('[data-e2e]') || a.parentElement || a;
    const viewNode = card.querySelector('[data-e2e*="video-views"], strong[title]');
    const img = card.querySelector('img[alt]');
    const alt = img ? (img.getAttribute('alt') || '') : '';
    out.push({
      creator: m[1],
      id: m[2],
      url: a.href.split('?')[0],
      views: viewNode ? (viewNode.textContent || '').trim() : '',
      text: (alt || card.innerText || '').slice(0, 300)
    });
  });
  out.walled = walled;
  return out;
})()
"""


def parse_count(text: str) -> int | None:
    """'9.9M' -> 9900000, '1.2K' -> 1200, '9,674' -> 9674."""
    text = (text or "").strip().replace(",", "")
    m = re.match(r"^([\d.]+)\s*([KMB]?)$", text, re.IGNORECASE)
    if not m:
        return None
    mult = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[m.group(2).upper()]
    try:
        return int(float(m.group(1)) * mult)
    except ValueError:
        return None


def _normalise(data: dict) -> dict:
    """Give the DOM and text paths the same numeric fields as the JSON path.

    Those two only ever see display strings — "9.9M", "1,234" — so the counts
    are parsed here rather than leaving three shapes for callers to handle.
    """
    out = dict(data)
    for field in ("followers", "following", "hearts"):
        if out.get(field) is None and out.get(f"{field}_text"):
            out[field] = parse_count(out[f"{field}_text"])
    out["bio"] = (out.get("bio") or "").strip()
    return out


def profile(handle: str, *, log=print) -> dict | None:
    """Read a profile's header straight out of the page's hydration payload.

    Polls rather than sleeping a fixed amount: TikTok serves a login-wall shell
    first and swaps in the real page a moment later, and how long that takes
    varies enough that any constant is either flaky or wasteful.
    """
    handle = handle.lstrip("@").lower()
    url = f"https://www.tiktok.com/@{handle}"
    tab = None
    try:
        tab = open_url(url, settle=3.0, log=log)
        for attempt in range(SETTLE_POLLS):
            try:
                data = evaluate(tab, PROFILE_JS)
            except BrowserRestarted:
                close_tab(tab)
                tab = open_url(url, settle=3.0, log=log)
                continue
            if isinstance(data, dict) and data.get("ready"):
                return _normalise(data)
            if isinstance(data, dict) and data.get("walled"):
                log(f"    @{handle}: TikTok is requiring a login for this "
                    f"profile (the creator has audience controls on)")
                return {"walled": True, "handle": handle}
            time.sleep(SETTLE_GAP)
        log(f"    @{handle}: profile did not hydrate (login wall or rate limit)")
        return None
    except CamofoxError as exc:
        log(f"    @{handle}: {exc}")
        return None
    finally:
        if tab:
            close_tab(tab)


#: TikTok's internal id for an account, needed when the public extractor fails.
SECUID_JS = """
(() => {
  const el = document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__');
  if (!el) return { found: false };
  try {
    const d = JSON.parse(el.textContent)['__DEFAULT_SCOPE__'] || {};
    const u = ((d['webapp.user-detail'] || {}).userInfo || {}).user || {};
    return { found: !!u.secUid, secUid: u.secUid || null, id: u.id || null };
  } catch (e) { return { found: false }; }
})()
"""


def sec_uid(handle: str, *, log=print) -> str | None:
    """Read an account's `secUid` out of the page.

    yt-dlp's TikTok extractor sometimes cannot work this out for itself and
    fails with "Unable to extract secondary user ID", which reads like the
    account is gone. It is not — its own error message says the fix is to pass
    `tiktokuser:<secUid>` instead, and the value is sitting in the page's
    hydration payload where the browser can simply read it.

    So the two harvesters cooperate: camofox supplies the key, yt-dlp does the
    fast bulk enumeration it is good at.
    """
    handle = handle.lstrip("@").lower()
    tab = None
    try:
        tab = open_url(f"https://www.tiktok.com/@{handle}", settle=4.0, log=log)
        for _ in range(SETTLE_POLLS):
            try:
                data = evaluate(tab, SECUID_JS)
            except BrowserRestarted:
                close_tab(tab)
                tab = open_url(f"https://www.tiktok.com/@{handle}", settle=4.0, log=log)
                continue
            if isinstance(data, dict) and data.get("found"):
                return data["secUid"]
            time.sleep(SETTLE_GAP)
        return None
    except CamofoxError as exc:
        log(f"    could not read secUid for @{handle}: {exc}")
        return None
    finally:
        if tab:
            close_tab(tab)


def scroll_harvest(url: str, *, max_scrolls: int = 30, settle: float = 1.6,
                   stop_after_stagnant: int = 5, log=print) -> list[dict]:
    """Scroll a lazy-loading page and collect every video card it reveals.

    This is the generalised version of the scroll loop — it works on a profile
    grid, a hashtag page or a search results page, because all three lazy-load
    the same kind of card. Stops early once scrolling stops producing anything
    new, which is what "the end of the feed" actually looks like.
    """
    tab = None
    seen: dict[str, dict] = {}
    try:
        tab = open_url(url, settle=4.0, log=log)
        stagnant = 0
        for i in range(max_scrolls):
            try:
                cards = evaluate(tab, CARDS_JS) or []
            except BrowserRestarted:
                close_tab(tab)
                tab = open_url(url, settle=4.0, log=log)
                continue
            except CamofoxError as exc:
                log(f"    card read failed: {exc}")
                break

            before = len(seen)
            for card in cards:
                vid = str(card.get("id") or "")
                if vid and vid not in seen:
                    seen[vid] = {
                        "video_id": vid,
                        "creator": card.get("creator", ""),
                        "url": card.get("url", ""),
                        "views": parse_count(card.get("views", "")),
                        "text": (card.get("text") or "").strip(),
                    }
            gained = len(seen) - before
            stagnant = stagnant + 1 if gained == 0 else 0
            if (i + 1) % 5 == 0:
                log(f"    scroll {i + 1}/{max_scrolls}: {len(seen)} cards")
            if stagnant >= stop_after_stagnant:
                log(f"    feed exhausted after {i + 1} scrolls ({len(seen)} cards)")
                break
            scroll(tab)
            time.sleep(settle)
        return list(seen.values())
    except CamofoxError as exc:
        log(f"    scroll harvest failed: {exc}")
        return list(seen.values())
    finally:
        if tab:
            close_tab(tab)
