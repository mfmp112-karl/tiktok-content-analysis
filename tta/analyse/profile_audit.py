"""The profile a visitor actually lands on.

Reach gets someone to a video; the profile is what turns them into a follower.
The checks here follow a widely-taught creator checklist — picture, bio, link,
pinned content — with one rule applied throughout: **only check what can be
checked.**

So the bio is measured properly (length, how it scans, whether it names who it
is for, whether it says what you get, whether there is a way through to
anything). The profile picture is not scored. Judging whether an image "looks
clean at small size" from its bytes would need real image analysis, and a
fabricated score is worse than no score. Instead the report renders the actual
avatar at the three sizes it appears at in the wild — profile, comment thread,
crowded feed — and lets the creator see the problem for themselves, which is
what would convince them anyway.
"""
from __future__ import annotations

import base64
import re
import urllib.request

#: Words that signal the bio is addressed to somebody in particular.
AUDIENCE_HINTS = re.compile(
    r"\bfor\s+(?:the\s+)?\w+|\bhelping\b|\bhelp\s+you\b|\byour\b|\byou\b|"
    r"\bbeginners?\b|\bwomen\b|\bmen\b|\bmums?\b|\bmoms?\b|\bstudents?\b|"
    r"\bcreators?\b|\bfounders?\b|\bathletes?\b|\btraders?\b", re.I)

#: Words that signal a promise rather than a description.
VALUE_HINTS = re.compile(
    r"\bhow to\b|\blearn\b|\bteach\b|\btips?\b|\bguide\b|\bfree\b|\bdaily\b|"
    r"\bweekly\b|\bget\b|\bbuild\b|\bgrow\b|\bmake\b|\bstart\b|\bcoach\w*\b|"
    r"\btrain\w*\b|\brecipes?\b|\breviews?\b", re.I)

CTA_HINTS = re.compile(r"\blink\b|\bbelow\b|\bdm\b|\bemail\b|\bbook\b|\bjoin\b|"
                       r"\bsubscribe\b|\bshop\b|👇|⬇|👉", re.I)

BIO_MAX_LINES = 4
BIO_MAX_CHARS = 200


def _fetch_avatar(url: str, timeout: int = 15) -> str | None:
    """Inline the avatar so the report stays a single self-contained file."""
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            kind = resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
    except Exception:
        return None
    if not data or len(data) > 3_000_000:
        return None
    return f"data:{kind};base64," + base64.b64encode(data).decode("ascii")


def audit(profile: dict | None, *, video_count: int = 0) -> dict | None:
    """Turn a captured profile into pass/fix rows."""
    if not profile:
        return None

    bio = (profile.get("bio") or "").strip()
    lines = [ln for ln in bio.splitlines() if ln.strip()]
    link = (profile.get("link") or "").strip()
    checks: list[dict] = []

    # --- picture ---------------------------------------------------------
    has_avatar = bool(profile.get("avatar"))
    checks.append({
        "name": "Profile picture",
        "pass": has_avatar,
        "detail": ("Shown below at three sizes. Most people only ever see "
                   "the smallest one."
                   if has_avatar else "No profile picture could be read."),
        "fix": ("Look at the smallest version. Can't tell what it is? "
                "Simplify: one subject, plain background, little or no text."),
    })

    # --- bio -------------------------------------------------------------
    if not bio:
        checks.append({"name": "Bio", "pass": False,
                       "detail": "Empty.",
                       "fix": "Two or three short lines: who this is for, and what "
                              "they get by following."})
    else:
        scans = len(lines) <= BIO_MAX_LINES and len(bio) <= BIO_MAX_CHARS
        checks.append({
            "name": "Bio scans quickly",
            "pass": scans,
            "detail": f"{len(bio)} characters across {len(lines)} line(s).",
            "fix": (f"People scan bios, they don't read them. Keep it under "
                    f"{BIO_MAX_LINES} short lines and {BIO_MAX_CHARS} "
                    f"characters."),
        })
        named = bool(AUDIENCE_HINTS.search(bio))
        checks.append({
            "name": "Bio names who it is for",
            "pass": named,
            "detail": ("It addresses a particular reader." if named else
                       "It describes the account, but not who it is for."),
            "fix": "Say who this is for. A reader who sees themselves in "
                   "line one has already decided to stay.",
        })
        promises = bool(VALUE_HINTS.search(bio))
        checks.append({
            "name": "Bio says what they get",
            "pass": promises,
            "detail": ("There is a promise in it." if promises else
                       "No stated benefit to following."),
            "fix": "Add the payoff — what turns up on their feed if they follow.",
        })

    # --- link ------------------------------------------------------------
    checks.append({
        "name": "Link",
        "pass": bool(link),
        "detail": link or "No link on the profile.",
        "fix": ("Add one, even with nothing to sell. Send the attention "
                "somewhere that's yours — not rented from an algorithm."),
    })
    if bio and not CTA_HINTS.search(bio) and link:
        checks.append({
            "name": "Bio points at the link",
            "pass": False,
            "detail": "There is a link, but the bio never mentions it.",
            "fix": "Spend the last line of the bio telling people why to tap it.",
        })

    # --- catalogue -------------------------------------------------------
    checks.append({
        "name": "Enough posted to judge",
        "pass": video_count >= 30,
        "detail": f"{video_count} public posts.",
        "fix": "Under thirty posts, almost nothing here can be proven yet. "
               "Keep posting — the picture gets clearer.",
    })

    passed = sum(1 for c in checks if c["pass"])
    return {
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "avatar_data_uri": _fetch_avatar(profile.get("avatar", "")),
        "source": profile.get("source"),
        "followers": profile.get("followers"),
        "bio": bio,
        "link": link,
    }
