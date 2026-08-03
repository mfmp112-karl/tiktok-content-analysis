"""Using a signed-in TikTok session, so audience-controlled accounts can be read.

Some creators switch on audience controls, which makes TikTok serve their
profile only to signed-in visitors: follower counts render as "-" and the video
grid is empty. No amount of stealth gets around that, because it is a
permission, not a bot check. The only answer is to be signed in.

The shape that works here is a **cookie file the user exports themselves**,
pointed at with `--cookies`. It is fed to yt-dlp for the fast path and imported
into camofox for the browser path, so both tiers see the same session.

Three things this module will not do, on purpose:

* **It never asks for a password and never logs anybody in.** The user
  authenticates in their own browser, in their own hands, and exports the
  result. This code only ever consumes a file that already exists.
* **It never prints cookie values.** Diagnostics report names, domains and
  expiry dates only.
* **It does not fetch, sync or copy the file anywhere.** The path is read at
  run time and that is all.

A word that belongs in the docs and in your head: a cookie file is a
credential. Anyone holding it is signed in as that account. Use a throwaway
account made for this, keep the file outside the repo, and treat losing it the
way you would treat losing a password.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

ENV_COOKIES = "TTA_COOKIES"

#: The cookies TikTok actually uses to recognise a session. Everything else in
#: an export is analytics noise and is not worth importing.
SESSION_COOKIES = {"sessionid", "sessionid_ss", "sid_tt", "sid_guard",
                   "uid_tt", "msToken", "tt_csrf_token", "ttwid"}


class SessionError(RuntimeError):
    pass


def cookie_path(explicit: str | None = None) -> Path | None:
    """Where the cookie file is, if there is one."""
    for candidate in (explicit, os.getenv(ENV_COOKIES)):
        if candidate:
            p = Path(candidate).expanduser()
            return p if p.exists() else None
    # A conventional default, so a returning user need not pass the flag.
    from .. import paths
    default = paths.home() / "tiktok-cookies.txt"
    return default if default.exists() else None


# ------------------------------------------------------------ Netscape parsing

def parse_netscape(path: Path) -> list[dict]:
    """Read a Netscape/`cookies.txt` file into dicts.

    This is the format every cookie-export extension emits and the one yt-dlp
    expects, so it is the only one worth supporting.
    """
    out = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            # "#HttpOnly_" is a real prefix, not a comment.
            if not line.startswith("#HttpOnly_"):
                continue
            line = line[len("#HttpOnly_"):]
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        domain, _flag, cpath, secure, expires, name, value = parts[:7]
        try:
            expiry = int(expires)
        except ValueError:
            expiry = 0
        out.append({
            "name": name, "value": value, "domain": domain, "path": cpath or "/",
            "expires": expiry, "secure": secure.upper() == "TRUE",
            "httpOnly": False, "sameSite": "Lax",
        })
    return out


def describe(path: Path) -> dict:
    """What is in the file, without ever revealing a value."""
    cookies = parse_netscape(path)
    tiktok = [c for c in cookies if "tiktok" in c["domain"]]
    session = [c for c in tiktok if c["name"] in SESSION_COOKIES]
    now = time.time()
    expiries = [c["expires"] for c in session if c["expires"] > 0]
    soonest = min(expiries) if expiries else 0
    return {
        "path": str(path),
        "total": len(cookies),
        "tiktok": len(tiktok),
        "session_cookies": sorted(c["name"] for c in session),
        "has_login": any(c["name"] in ("sessionid", "sessionid_ss") for c in session),
        "expires_at": soonest,
        "expired": bool(soonest and soonest < now),
        "days_left": round((soonest - now) / 86400, 1) if soonest else None,
    }


def status(explicit: str | None = None) -> dict:
    """One dict describing the configured session, for the doctor and the run."""
    path = cookie_path(explicit)
    if not path:
        return {"configured": False, "usable": False,
                "note": "no cookie file configured"}
    try:
        info = describe(path)
    except OSError as exc:
        return {"configured": True, "usable": False, "note": f"unreadable: {exc}"}

    if not info["has_login"]:
        return {"configured": True, "usable": False, "path": str(path),
                "note": ("file has no TikTok sessionid - it was probably "
                         "exported while signed out")}
    if info["expired"]:
        return {"configured": True, "usable": False, "path": str(path),
                "note": "the session has expired; sign in again and re-export"}

    # A cookie export contains everything the browser profile has ever visited,
    # not just the site you were looking at. Exported from a normal daily
    # browser that is thousands of cookies for every service the person is
    # signed into — a far more sensitive file than they think they made, and
    # they will leave it in Downloads. Worth saying out loud, with the number.
    note = (f"{info['tiktok']} TikTok cookies, signed in, "
            f"{info['days_left']} days left")
    spill = info["total"] - info["tiktok"]
    if spill > info["tiktok"]:
        note += (f" — but the file also holds {spill:,} cookies for other sites. "
                 f"Export from a browser profile used only for this.")
    return {"configured": True, "usable": True, "path": str(path),
            "note": note, "other_site_cookies": spill, **info}


# --------------------------------------------------------------------- wiring

def ytdlp_opts(explicit: str | None = None) -> dict:
    """Extra yt-dlp options for a signed-in pull."""
    path = cookie_path(explicit)
    return {"cookiefile": str(path)} if path else {}


def import_into_camofox(explicit: str | None = None, *, log=print) -> bool:
    """Push the session into camofox so the browser path is signed in too."""
    from . import camofox
    path = cookie_path(explicit)
    if not path or not camofox.healthy():
        return False

    cookies = [c for c in parse_netscape(path) if "tiktok" in c["domain"]]
    if not cookies:
        return False
    # The endpoint caps at 500, and the session cookies are the only ones that
    # matter, so send those first and fill the rest opportunistically.
    ranked = sorted(cookies, key=lambda c: c["name"] not in SESSION_COOKIES)
    try:
        camofox._api("POST", f"/sessions/{camofox.USER_ID}/cookies",
                     {"cookies": ranked[:500]}, timeout=45)
        log(f"    signed-in session imported into camofox "
            f"({len(ranked[:500])} cookies)")
        return True
    except Exception as exc:
        log(f"    could not import session into camofox: "
            f"{type(exc).__name__}: {exc}")
        return False


HOW_TO = """\
To read accounts that have audience controls switched on, this tool needs to be
signed in to TikTok. It will not log in for you and will never ask for a
password - you export a session from your own browser and point it at the file.

THE SETUP WORTH DOING PROPERLY

A cookie export contains every cookie the browser profile holds, not just the
site you were looking at. Exported from your everyday browser that is a file
containing your email, your bank, your everything - thousands of cookies, any
one of which is a live session. So use a browser profile that has never been
anywhere else:

  1. Make a separate email address for this.

  2. Make a NEW BROWSER PROFILE for it. In Chrome: your avatar, top right ->
     Add -> a new profile, not signed into anything. This is the step that
     actually matters. A profile that has only ever visited tiktok.com can only
     ever export tiktok.com cookies, so the file you produce is worth almost
     nothing to anyone who finds it.

  3. In that profile only, sign up for a TikTok account and sign in. It needs
     no posts, no picture and no followers - it only ever reads. Do not use
     your main account: automated reading can get an account rate-limited or
     restricted, and this is the one you can afford to lose.

  4. Install a "cookies.txt" extension in that profile. Check its reviews and
     permissions first - these can read cookies for every site by design, so
     prefer one that is open-source and works offline.

  5. On a tiktok.com page, export. The file should start with
     "# Netscape HTTP Cookie File".

  6. Save it as ~/.raven/tiktok-cookies.txt and it is picked up
     automatically, or pass it explicitly:
        python driver.py @handle --cookies /path/to/cookies.txt

     Do not leave it in Downloads.

Check it with:  python driver.py --doctor

The doctor reports how many TikTok cookies the file holds and how many days the
session has left. If it also holds a pile of cookies for other sites, it will
say so - that means it came from a browser profile with a life of its own, and
you should redo step 2.

WHAT THIS DOES NOT DO

A separate profile separates cookies. It does not make you a different person:
TikTok can still associate accounts by device and network. Treat the reader
account as disposable rather than as anonymous.

Sessions expire, usually within a few weeks. When one does the doctor says so,
which matters because an expired session and a private account look identical
from the outside."""
