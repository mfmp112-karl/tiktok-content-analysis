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
    "cover.sub": (
        "I read every post this account has published. This is what I found.",
        "A read of what this account has actually published, and a 30-day plan "
        "built from it."),
    "cover.intro": (
        "I have put what I am most sure about first, and I have been careful to "
        "say when I am not sure. Where you see “not enough data yet”, "
        "I mean it — it is not a hedge, it is the honest state of the "
        "evidence, and acting on those rows is how people talk themselves out "
        "of the thing that was working.",
        "The pages that follow move from what this account is, to what has "
        "worked, to what to post next. Every finding carries a note on how much "
        "evidence sits behind it — read those as carefully as the numbers."),
    "cover.ethics": (
        "I exist to help people grow their accounts by understanding what they "
        "have already made. I read public data only, take nothing TikTok does "
        "not show any logged-out visitor, and automate no engagement of any "
        "kind. Please do not point me at anyone in order to harass, impersonate "
        "or target them.",
        "This was built to help people grow their accounts meaningfully — by "
        "understanding what they have already published and deciding what to "
        "make next. It reads public data only, takes nothing that TikTok does "
        "not show any logged-out visitor, and automates no engagement of any "
        "kind. Please do not use it to harass, impersonate, or target anyone."),

    # --- at a glance ---------------------------------------------------------
    "glance.sub": (
        "The shape of the account, before I interpret anything.",
        "The shape of the account before any interpretation."),
    "glance.limits": (
        "What I could not tell you",
        "What this report cannot tell you"),

    # --- recommendations -----------------------------------------------------
    "recs.sub": (
        "Things to film, in the order I would do them. The first few come out "
        "of your own numbers; the later ones from what the rest of your niche "
        "is doing and asking.",
        "Specific things to film, ordered by how much evidence sits behind "
        "them. The first few come from this account's own numbers; the later "
        "ones from what the niche is posting and asking right now."),

    # --- reach ---------------------------------------------------------------
    "reach.sub": (
        "Which way this is going, month by month.",
        "Where the account is heading, month by month."),

    # --- themes --------------------------------------------------------------
    "themes.sub": (
        "I did not decide these in advance. I grouped your captions and let the "
        "themes fall out of what you actually write about.",
        "Themes discovered from the captions themselves, not chosen in advance."),
    "themes.howto": (
        "How to read what I have called each one",
        "How to read the call"),
    "themes.calls": (
        "<b>Keep</b> beats your average and I have the evidence for it. "
        "<b>Ditch</b> trails your average and I have the evidence for that too. "
        "<b>Test more</b> means it looks promising or poor but rests on too few "
        "posts for me to say — which is the honest answer for most themes on "
        "most accounts, and I would rather give it than invent a verdict. "
        "<b>Try</b> is something your niche is doing that you have not.",
        "<b>Keep</b> beats the account average with evidence behind it. "
        "<b>Ditch</b> trails the average with evidence behind it. "
        "<b>Test more</b> looks promising or poor but rests on too few posts to "
        "judge. <b>Try</b> is a theme with outside demand that this account has "
        "not covered yet."),

    # --- audience ------------------------------------------------------------
    "audience.sub": (
        "The profile someone lands on after a video, and how the accounts "
        "around you introduce themselves.",
        "The profile a visitor lands on, and how peers in this niche position "
        "themselves."),
    "audience.peers": (
        "Read these as positioning, not as competition: who they say they are "
        "for, and what they promise in return for a follow.",
        "Read these as competitive intelligence on positioning: who they say "
        "they are for, and what they promise."),
    "audience.avatar": (
        "Your picture at profile size, at comment size, and at the size it "
        "appears in a crowded feed. Most people only ever see the smallest one.",
        "Your picture at profile size, at comment size, and at the size it "
        "appears in a busy feed."),

    # --- hooks ---------------------------------------------------------------
    "hooks.sub": (
        "What your opening line does, and whether it shows up in the numbers.",
        "What the opening line does, and whether it shows up in the numbers."),
    "hooks.caveat": (
        "These overlap with each other, and with whatever mood you were in that "
        "week. When I say a gap is real, I mean the gap is real — not that the "
        "feature caused it.",
        "These features overlap with each other and with the mood the creator "
        "was in. A result here says the gap is real, not that the feature "
        "caused it."),
    "hooks.winners": (
        "Openings that already worked here",
        "Openings that worked on this account"),
    "hooks.winners.sub": (
        "Pulled from posts that beat your own average, so the voice is already "
        "yours. Reuse the shape, not the words.",
        "Taken from posts that beat the account average, so the voice is "
        "already the creator's own."),

    # --- timing --------------------------------------------------------------
    "timing.sub": (
        "When you post, and whether it has made any difference.",
        "When this account posts, and whether it matters."),
    "timing.cadence": (
        "“Post daily” is good advice in general. This is whether it has "
        "shown up in your own numbers yet.",
        "“Post daily” is good advice in general. This is whether it has "
        "shown up in this account's own numbers so far."),

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
        "Where I could and could not get to",
        "Which sources were reachable"),
    "demand.coverage.sub": (
        "A partial look is not the whole picture, so here is exactly what I "
        "managed to read.",
        "A partial pull is not the whole picture, so this states plainly what "
        "was and was not consulted."),

    # --- calendar ------------------------------------------------------------
    "calendar.sub": (
        "Thirty days built from your own strongest themes and your own best "
        "openings, on a five-day rotation.",
        "A day-by-day plan built from this account's own strongest themes and "
        "openings, on a five-day rotation."),
    "calendar.note": (
        "The same thirty days are in the spreadsheet next to this, with room "
        "for your caption and a box to tick when it goes out.",
        "The same calendar is in the accompanying spreadsheet, with columns for "
        "your caption, platform and whether you posted."),

    # --- frameworks ----------------------------------------------------------
    "frameworks.sub": (
        "The playbook my checks are built on, credited to @teezytheturtle. I am "
        "setting it out so you can use it without me.",
        "The creator playbook these checks are built on, credited to "
        "@teezytheturtle. Stated here so you can apply it without the report."),

    # --- method --------------------------------------------------------------
    "method.how": (
        "How I got these numbers",
        "How the numbers were produced"),
    "method.unavailable": (
        "What I genuinely cannot see",
        "What is genuinely unavailable"),
    "method.significance": (
        "I test every comparison with Welch's t-test on log-transformed views. "
        "View counts are wildly skewed, so without the log one viral post "
        "carries a whole bucket and I end up telling you something that is not "
        "true. I never call a group of fewer than eight posts significant, "
        "however large the gap looks — “solid evidence” means p &lt; 0.01 and "
        "“early signal” means p &lt; 0.05. Everything else I report as not "
        "settled.",
        "Every comparison is tested with Welch's t-test on log-transformed "
        "views. View counts are heavily skewed, so one viral post can otherwise "
        "carry a whole bucket. Groups under eight posts are never called "
        "significant, however large the gap looks. “Solid evidence” means "
        "p &lt; 0.01; “early signal” means p &lt; 0.05; anything else is "
        "reported as not enough data yet."),
    "method.owner_only": (
        "Watch time, retention curves, traffic sources, follower growth over "
        "time and who your audience is are things TikTok shows only to the "
        "account owner, inside their own analytics. I cannot reach them for an "
        "account I do not own, and neither can anything else. A good deal of "
        "creator advice rests on those numbers; where it does, I have tested "
        "what I can measure instead and told you which is which rather than "
        "inventing a stand-in.",
        "Watch time, retention curves, traffic sources, follower growth over "
        "time and audience demographics are served by TikTok <strong>only to "
        "the account owner</strong>, inside their own analytics. No tool can "
        "obtain them for an account it does not own. Where creator advice "
        "depends on those numbers, this report tests what it can measure "
        "instead and says so rather than inventing a proxy."),
    "method.timezone": (
        "I converted upload times in this machine's local timezone, so “best "
        "hour” is in your clock, not UTC.",
        "Upload times are converted in this machine's local timezone, so "
        "“best hour” is in your clock, not UTC."),
}
