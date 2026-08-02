"""The five post types and the five-day rotation.

Method credit: themarketingfmpodcast. The wording here is our own — what is
reproduced is the structure (five types, one per day, repeating six times over
thirty days), which is the part that does the work.

Each type exists to do a different job, and the reason the rotation is fixed is
that left to instinct most people post one type almost exclusively. Spreading
them evenly is the whole intervention.
"""
from __future__ import annotations

POST_TYPES = [
    {
        "name": "EDUCATE",
        "does": "Builds authority. The most shareable type, and the one most "
                "likely to reach people who have never heard of you.",
        "how": "Teach one genuinely useful thing, completely, for free. No pitch "
               "anywhere in it. Lead with the lesson rather than the product.",
        "shape": "Teach one thing about {theme} that most people get wrong.",
    },
    {
        "name": "PROOF",
        "does": "Converts people who already trust you. Replaces a sales pitch, "
                "because the result does the arguing.",
        "how": "Show the before and after. Real numbers, real timeframes, real "
               "names where you have permission.",
        "shape": "Show a real result from {theme} — where it started, what you "
                 "changed, where it ended.",
    },
    {
        "name": "ENGAGE",
        "does": "Feeds the algorithm. Comments and replies are the cheapest reach "
                "you will ever get.",
        "how": "Ask something they actually want to answer, and make it about "
               "them rather than about you.",
        "shape": "Ask your audience the one thing you most want to know about "
                 "how they approach {theme}.",
    },
    {
        "name": "OFFER",
        "does": "The direct revenue driver. One per five days is the right "
                "frequency — more than that and it reads as desperate.",
        "how": "Be specific: what exactly, for how much, by when, and precisely "
               "what to do next.",
        "shape": "Make one specific, time-bound offer connected to {theme}. Say "
                 "exactly what they get and exactly what to do.",
    },
    {
        "name": "MIRROR",
        "does": "The highest-connection post. Aimed at people who do not yet know "
                "they have the problem you solve.",
        "how": "Describe their exact frustration in the words they use in their "
               "own head. Sell nothing at all. Just mirror it back.",
        "shape": "Describe the frustration someone hits with {theme}, in their "
                 "words, and sell nothing.",
    },
]

NAMES = [t["name"] for t in POST_TYPES]
CYCLE = len(POST_TYPES)


def type_for_day(day: int) -> dict:
    """Day 1 is EDUCATE; the cycle repeats every five days."""
    return POST_TYPES[(day - 1) % CYCLE]


def mix(days: list[dict]) -> list[dict]:
    """Counts per post type, for the mix chart and the workbook summary."""
    rows = []
    for t in POST_TYPES:
        n = sum(1 for d in days if d["post_type"] == t["name"])
        rows.append({"name": t["name"], "n": n,
                     "share": round(n / len(days) * 100) if days else 0,
                     "does": t["does"], "verdict": "n/a"})
    return rows
