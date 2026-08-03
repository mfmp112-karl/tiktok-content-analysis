"""Raven — who she is, and every line she says.

All of her voice lives in this one file. Scattering personality through the
codebase is how tone drifts: one module gets chatty, another stays clinical,
and the whole thing reads like it was written by a committee. Here it can be
read top to bottom, edited in one place, and switched off entirely.

**Who she is.** Raven reads an account's whole history and reports back what
she found. Her defining trait is already in the rest of this codebase: she will
not overclaim. She says "not enough data yet" more often than anything else,
and she draws unproven findings as hollow outlines so a skimming reader cannot
mistake them for facts. The personality here is not decoration bolted onto a
statistics tool — it is a name and a voice given to a discipline the tool
already had.

**How she talks.** Plainly, in the first person, without hurry. She does not
celebrate ordinary things and never uses an exclamation mark. She is warm
underneath but not encouraging for its own sake, because false encouragement is
the thing that sends a creator off to change what was working. When she does
not know, she says so and tells you what would change that.

**What she never does.** No bird puns, no emoji, no cawing. The corvid is in
how she behaves — watching, counting, bringing things back — not in costume.
She stays out of the statistics entirely: verdicts, numbers and error messages
that need acting on are written straight, because a joke in front of a fact is
a fact nobody reads.

`--plain` silences her everywhere. Some people want a tool rather than a
character, scripts want parseable output, and both are reasonable.
"""
from __future__ import annotations

import os

NAME = "Raven"
TAGLINE = "reads your whole account and tells you what she actually found"

#: Set TTA_PLAIN=1, or pass --plain, for output with no voice at all.
ENV_PLAIN = "TTA_PLAIN"

_plain = bool(os.getenv(ENV_PLAIN))


def set_plain(value: bool) -> None:
    global _plain
    _plain = value


def is_plain() -> bool:
    return _plain


def _say(voiced: str, plain: str) -> str:
    return plain if _plain else voiced


# ------------------------------------------------------------------- openings

def greeting(handle: str) -> str:
    return _say(f"{NAME} is reading @{handle}.",
                f"=== @{handle} ===")


def mark() -> str:
    """The standing signature for the doctor header.

    Kept short on purpose. This has to sit inside 80 columns on somebody
    else's terminal, and ASCII art ages badly — the character has to survive
    being plain text.
    """
    return _say(f"{NAME}  ·  TikTok content analysis", "TikTok Content Analysis")


def strapline() -> str:
    """The longer line, for places with room for it."""
    return _say(f"{NAME} {TAGLINE}.", "")


# --------------------------------------------------------------------- steps

STEPS = {
    "harvest": ("Fetching everything this account has posted",
                "Reading the public catalogue"),
    "profile": ("Looking at the profile a visitor lands on",
                "Reading the profile"),
    "analyse": ("Working out what actually travelled, and what only looked like it",
                "Analysing"),
    "research": ("Seeing what the rest of the niche is doing",
                 "What the niche is posting"),
    "calendar": ("Laying out the next thirty days",
                 "Building the 30-day calendar"),
    "report": ("Writing it up", "Writing the report"),
}


def step(key: str) -> str:
    voiced, plain = STEPS[key]
    return _say(voiced, plain)


# -------------------------------------------------------- moments worth a line

def found(n: int, new: int) -> str:
    if _plain:
        return f"  {n} videos stored ({new} new)"
    if new == 0 and n:
        return f"  {n} posts, nothing new since last time. Going back through them."
    if n == 0:
        return "  Nothing yet."
    return f"  {n} posts{f', {new} of them new' if new != n else ''}. Going through them."


def verdicts(strong: int, moderate: int, total: int) -> str:
    """Her signature moment. Most accounts land in the first branch, and that
    is the one worth getting right — an account with nothing proven yet is not
    a failure and should not be told it is."""
    if _plain:
        return f"  {strong} strong, {moderate} moderate, {total} findings"
    if total == 0:
        return "  Not enough here to say anything yet."
    if strong == 0 and moderate == 0:
        return ("  Nothing here is settled yet. I would rather tell you that "
                "than guess at it.")
    if strong == 0:
        return (f"  {moderate} early signal{'s' if moderate != 1 else ''}, "
                f"nothing conclusive. Worth watching, not worth rearranging "
                f"everything for.")
    return (f"  {strong} thing{'s' if strong != 1 else ''} I am confident about"
            + (f", {moderate} more worth watching." if moderate else "."))


def themes_found(k: int, effective: float | None) -> str:
    if _plain:
        return f"  {k} themes"
    if effective and effective < 1.6:
        return (f"  {k} themes, but the feed reads as barely more than one. "
                f"That is either focus or a rut, and you will know which.")
    if effective:
        return f"  {k} themes. The feed reads as about {effective} distinct styles."
    return f"  {k} themes."


def blocked(handle: str) -> str:
    return _say(
        f"  I cannot see @{handle}. TikTok is only showing this one to "
        f"signed-in visitors — the creator has audience controls on. That is a "
        f"door they closed, not a wall I can get around.",
        f"  @{handle} is only visible to signed-in visitors (audience controls).")


def finished(seconds: float, where: str) -> str:
    return _say(f"  Done in {seconds:.0f}s. It is all in {where}.",
                f"Done in {seconds:.0f}s -> {where}")


def cannot_measure() -> str:
    return _say(
        "Watch time, retention, traffic sources and who your audience is are "
        "TikTok's to give and it only gives them to you, inside your own "
        "analytics. I have not tried to guess at them.",
        "Watch time, retention, traffic sources and audience demographics are "
        "owner-only and are not in this report.")


# ------------------------------------------------------------- report byline

def byline() -> str:
    return _say(f"Read by {NAME}", "TikTok Content Analysis")


def cover_note(posts: int, span: str) -> str:
    """One line under the cover figure. Counts the work before judging it."""
    if _plain:
        return ""
    return (f"I went through all {posts:,} of them, over {span}. "
            f"Here is what I found, and what I could not tell yet.")
