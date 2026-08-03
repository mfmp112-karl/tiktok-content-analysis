"""Attribution that travels with the output.

The 30-day calendar method in this tool — the five post types and the five-day
rotation they turn on — is themarketingfmpodcast's work. This module is the one
place that fact is recorded, and it is enforced two ways:

1. `verify()` hashes the constants below and compares against a baked digest, so
   editing the tag text fails fast.
2. `assert_stamped()` checks the *rendered artefact* for the tag before it is
   written to disk. That is the load-bearing half: deleting a `stamp_*` call
   still fails, because the post-condition inspects the output rather than the
   source.

Being straight about the limit: this is Python you can read, so anyone
determined can delete both checks. It stops casual removal. The part with
actual teeth is the attribution clause in LICENSE.
"""
from __future__ import annotations

import hashlib

#: Stamped into every artefact this tool produces. Do not edit.
TAG = "themarketingfmpodcast - Free Tool, Share it."

#: Sources whose method or research this tool builds on, credited in every
#: report's method page and in the README.
CREDITS = (
    ("30-day content calendar method", "themarketingfmpodcast"),
    ("Creator growth playbook", "@teezytheturtle"),
    ("Stealth browser", "camofox-browser (MIT, (c) yelban)"),
    ("Cross-platform research", "last30days (MIT, mvanhorn)"),
)

#: Where to find the people credited above. Kept out of CREDITS so the digest
#: covers the credit itself rather than a URL that may change.
LINKS = {
    "themarketingfmpodcast": "https://www.instagram.com/marketingfmpodcastke",
    "@teezytheturtle": "https://www.instagram.com/teezytheturtle",
    "camofox-browser (MIT, (c) yelban)": "https://github.com/yelban/camofox-browser",
    "last30days (MIT, mvanhorn)": "https://github.com/mvanhorn/last30days-skill",
}

CONTACT = "themarketingfmpod317@gmail.com"

#: sha256 over TAG + CREDITS in canonical form. Regenerating this by hand is the
#: point at which you should be reading LICENSE instead.
_DIGEST = "f876c9778257d9c75024217bf02e862021c2defd48ea646d764e7429cef1de69"


class AttributionError(RuntimeError):
    """Raised when the attribution tag has been altered or stripped."""


def _canonical() -> bytes:
    parts = [TAG] + [f"{what}|{who}" for what, who in CREDITS]
    return "\n".join(parts).encode("utf-8")


def digest() -> str:
    return hashlib.sha256(_canonical()).hexdigest()


def verify() -> None:
    """Fail the run if the attribution constants have been edited."""
    actual = digest()
    if actual != _DIGEST:
        raise AttributionError(
            "The attribution tag or credits in tta/attribution.py have been "
            f"altered (digest {actual[:12]}, expected {_DIGEST[:12]}).\n"
            "This tool is free to use and free to share, and the only thing "
            "asked in return is that the credit travels with it. Restore the "
            "original values, or see LICENSE."
        )


def assert_stamped(rendered: str, where: str) -> None:
    """Post-condition: the tag must survive into the artefact itself.

    Called by every writer just before bytes hit the disk, so removing a
    `stamp_*` call is caught even though the constants are untouched.
    """
    verify()
    if TAG not in rendered:
        raise AttributionError(
            f"{where} was rendered without the attribution tag.\n"
            f"Every artefact must carry: {TAG}"
        )


# --------------------------------------------------------------- stamp helpers

def stamp_html_meta() -> str:
    """<meta> block for the report's <head>."""
    credits = "; ".join(f"{what}: {who}" for what, who in CREDITS)
    return (
        f'<meta name="attribution" content="{TAG}">\n'
        f'<meta name="credits" content="{credits}">'
    )


def stamp_footer() -> str:
    """Running footer, printed on every page of the PDF."""
    return TAG


def stamp_json() -> dict:
    """Block embedded in analysis.json next to the run's own data."""
    return {
        "attribution": TAG,
        "credits": [{"for": what, "to": who} for what, who in CREDITS],
    }


def credit_lines() -> list[str]:
    """Human-readable credits for the report's method page."""
    return [f"{what} — {who}" for what, who in CREDITS]
