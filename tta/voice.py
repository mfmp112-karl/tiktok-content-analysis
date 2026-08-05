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
        "Watch time, retention, traffic sources, and who your audience is — "
        "only TikTok can show you those, inside your own analytics. I "
        "haven’t guessed at them.",
        "Watch time, retention, traffic sources and audience demographics are "
        "owner-only and are not in this report.")


# ------------------------------------------------------------- report byline

def byline() -> str:
    return _say(f"Read by {NAME}", "TikTok Content Analysis")


def cover_note(posts: int, span: str) -> str:
    """One line under the cover figure. Counts the work before judging it."""
    if _plain:
        return ""
    return (f"I read all {posts:,} of them, over {span}. Here’s what I "
            f"found — and what I couldn’t tell yet.")


# ============================================================ the report's prose
#
# The report is the thing that gets printed, forwarded and read six months
# later, so it carries her voice as much as the terminal does. Same rules apply:
# she narrates, but she does not touch the numbers. Every table header, every
# verdict and every figure stays neutral, because a voice in front of a
# statistic is a statistic nobody trusts.
#
# Each entry pairs her wording with a plain one. --plain is not a downgrade —
# it is the same document written by nobody in particular.

def report(key: str, **kw) -> str:
    """Look up a piece of report copy, voiced or plain."""
    voiced, plain = _REPORT[key]
    text = plain if _plain else voiced
    return text.format(**kw) if kw else text


_REPORT: dict[str, tuple[str, str]] = {

    # --- cover ---------------------------------------------------------------
    "cover.intro": (
        "I put what I’m most sure about first. When I’m not sure, I say so. "
        "“Not enough data yet” means just that. Don’t act on those rows — "
        "you might drop the one thing that was working.",
        "The pages ahead move from what this account is, to what has worked, "
        "to what to post next. Each finding says how much proof stands "
        "behind it. Read that as closely as the numbers."),
    "cover.ethics": (
        "I help people grow their accounts. I look at what they’ve already "
        "made. I only read public data — nothing a logged-out visitor "
        "couldn’t see. I never post, follow, like, or message anyone. "
        "Please don’t use me to harass, impersonate, or target someone.",
        "Built to help people grow their accounts. Looks at what they’ve "
        "already made. Reads public data only — nothing a logged-out "
        "visitor couldn’t see. Automates no engagement of any kind. Please "
        "don’t use it to harass, impersonate, or target anyone."),

    # --- at a glance ---------------------------------------------------------
    "glance.sub": (
        "The shape of the account, before I say what it means.",
        "The shape of the account, before any interpreting."),
    "glance.limits": (
        "What I couldn’t tell you",
        "What this report cannot tell you"),

    # --- recommendations -----------------------------------------------------
    "recs.sub": (
        "Film these in this order. The first ones come from your own "
        "numbers. The last ones come from what your niche is doing and "
        "asking.",
        "Things to film, ordered by how much proof backs each one. The "
        "first ones come from this account's own numbers. The rest come "
        "from what the niche is posting and asking now."),

    # --- reach ---------------------------------------------------------------
    "reach.sub": (
        "Which way this is going, month by month.",
        "Where the account is heading, month by month."),

    # --- themes --------------------------------------------------------------
    "themes.sub": (
        "I didn’t pick these ahead of time. I grouped your captions, and "
        "these themes fell out on their own.",
        "Themes discovered from the captions themselves, not chosen in advance."),
    "themes.howto": (
        "How to read each label",
        "How to read the call"),
    "themes.calls": (
        "<b>Keep</b>: beats your average, and I can prove it. <b>Ditch</b>: "
        "trails your average, and I can prove that too. <b>Test more</b>: "
        "looks good or bad, but too few posts to be sure — the true answer "
        "for most themes on most accounts. <b>Try</b>: your niche is doing "
        "this and you aren’t.",
        "<b>Keep</b>: beats the account average, proven. <b>Ditch</b>: "
        "trails the average, proven. <b>Test more</b>: looks good or bad, "
        "too few posts to judge. <b>Try</b>: outside demand this account "
        "hasn’t covered yet."),

    # --- audience ------------------------------------------------------------
    "audience.sub": (
        "The profile people land on after a video. And how the accounts "
        "around you introduce themselves.",
        "The profile a visitor lands on, and how peers in this niche "
        "position themselves."),
    "audience.peers": (
        "Read these as ideas, not rivals. Who do they say they’re for? "
        "What do they promise for a follow?",
        "Who these accounts say they’re for, and what they promise for a "
        "follow."),
    "audience.avatar": (
        "Your picture at three sizes: profile, comment, and busy feed. Most "
        "people only ever see the smallest one.",
        "Your picture at profile size, at comment size, and at the size it "
        "appears in a busy feed."),

    # --- hooks ---------------------------------------------------------------
    "hooks.sub": (
        "What your opening line does, and whether it shows up in the numbers.",
        "What the opening line does, and whether it shows up in the numbers."),
    "hooks.caveat": (
        "These features overlap each other, and your mood that week. A "
        "real gap means the gap is real — not that this one thing caused it.",
        "These features overlap each other and the creator’s mood. A real "
        "gap means real — not that this one feature caused it."),
    "hooks.winners": (
        "Openings that already worked here",
        "Openings that worked on this account"),
    "hooks.winners.sub": (
        "Taken from posts that beat your average. The voice is already "
        "yours — reuse the shape, not the words.",
        "Taken from posts that beat the account average, so the voice is "
        "already the creator's own."),

    # --- timing --------------------------------------------------------------
    "timing.sub": (
        "When you post, and whether it has made any difference.",
        "When this account posts, and whether it matters."),
    "timing.cadence": (
        "“Post daily” is good advice. This is whether it’s shown up in "
        "your numbers yet.",
        "“Post daily” is good advice. This is whether it’s shown up in "
        "this account’s numbers yet."),

    # --- demand --------------------------------------------------------------
    "demand.sub": (
        "What the rest of your niche was doing while I was looking.",
        "Outside demand signal, gathered at the time of this run."),
    "demand.questions.sub": (
        "Questions people actually typed out in the last 30 days. Each one is a "
        "video somebody already wants.",
        "Questions posted in the last 30 days, gathered by the last30days "
        "skill. Each of these is a video somebody already wants."),
    "demand.coverage": (
        "Where I got to, and where I didn’t",
        "Which sources were reachable"),
    "demand.coverage.sub": (
        "A partial look isn’t the whole picture. Here’s exactly what I read.",
        "A partial pull is not the whole picture, so this states plainly what "
        "was and was not consulted."),

    # --- calendar ------------------------------------------------------------
    "calendar.sub": (
        "Thirty days, built from your strongest themes and your best "
        "openings. A five-day rotation. Where I found one, each day points "
        "to a real post of yours to build from.",
        "A day-by-day plan built from this account’s own strongest themes "
        "and openings, on a five-day rotation. Where one exists, each day "
        "links to a real post from this account’s own catalogue."),
    "calendar.note": (
        "The same thirty days are in the spreadsheet too. There’s room for "
        "your caption, and a box to check when it’s posted.",
        "The same calendar is in the accompanying spreadsheet, with columns for "
        "your caption, platform and whether you posted."),

    # --- method --------------------------------------------------------------
    "method.how": (
        "How I got these numbers",
        "How the numbers were produced"),
    "method.unavailable": (
        "What I genuinely cannot see",
        "What is genuinely unavailable"),
    "method.significance": (
        "I test every comparison with a standard statistics test (Welch’s "
        "t-test), on a log scale. Without that, one viral post can throw "
        "off a whole group. I never call a group proven with fewer than "
        "eight posts, no matter how big the gap looks. “Solid evidence” "
        "and “early signal” are two proof levels; anything weaker I call "
        "not settled.",
        "Every comparison uses a standard statistics test (Welch’s "
        "t-test), on a log scale. Without that, one viral post can throw "
        "off a whole group. Groups under eight posts are never called "
        "proven, no matter how big the gap looks. “Solid evidence” and "
        "“early signal” are two proof levels; anything weaker is reported "
        "as not settled."),
    "method.owner_only": (
        "Watch time, retention, traffic sources, follower growth, and who "
        "your audience is — TikTok shows these only to the account owner. "
        "I can’t get them for an account I don’t own. No tool can. A lot "
        "of creator advice leans on those numbers. Where it does, I tested "
        "what I could measure instead, and said plainly which is which.",
        "Watch time, retention, traffic sources, follower growth, and who "
        "your audience is — TikTok shows these <strong>only to the "
        "account owner</strong>, inside their own analytics. No tool can "
        "get them for an account it does not own. Where creator advice "
        "depends on those numbers, this report tests what it can measure "
        "instead and says so plainly."),
    "method.timezone": (
        "I converted upload times in this machine's local timezone, so “best "
        "hour” is in your clock, not UTC.",
        "Upload times are converted in this machine's local timezone, so "
        "“best hour” is in your clock, not UTC."),
}
