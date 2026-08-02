"""Turning the analysis into thirty dated, specific rows.

The rules, in priority order:

* **The post type rotation is fixed.** Six of each type across the month. This
  is the part of the method that is not negotiable, because the whole point is
  to stop someone posting nothing but OFFER or nothing but EDUCATE.

* **Themes rotate underneath it**, drawn from the shortlist rather than from
  every cluster found. A varied account gets variety; it does not get thirty
  days of whatever it happened to post most.

* **Themes marked Ditch are excluded**, but only when there was real evidence
  behind that call. A theme that merely *looks* weak on nine posts stays in the
  rotation, because dropping something on that basis is how a creator talks
  themselves out of the thing they are still learning to do.

* **OFFER lands on the account's best day** where one is known. Everything else
  falls where the rotation puts it.

* **Every row carries the confidence of the evidence behind its theme**, so a
  row built on a hunch is visibly a hunch.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..stats import plain
from . import cycle

WEEKDAY_INDEX = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
                 "Friday": 4, "Saturday": 5, "Sunday": 6}


def _rotation_offset(start: date, best_day: str | None) -> int:
    """Shift the cycle so the *first* OFFER lands on the best weekday.

    Only the first: a five-day cycle against a seven-day week means every post
    type visits every weekday as the month goes on, and no shift can prevent
    that. Which is arguably the better outcome anyway — it tests each type on
    each day instead of baking in a guess. The report says this plainly rather
    than claiming an anchor it cannot hold.
    """
    if not best_day or best_day not in WEEKDAY_INDEX:
        return 0
    offer_pos = cycle.NAMES.index("OFFER")          # 0-based position in the cycle
    for shift in range(cycle.CYCLE):
        # day number d has type index (d - 1 + shift) % 5
        for d in range(1, cycle.CYCLE + 1):
            if (d - 1 + shift) % cycle.CYCLE != offer_pos:
                continue
            when = start + timedelta(days=d - 1)
            if when.weekday() == WEEKDAY_INDEX[best_day]:
                return shift
    return 0


def _hook_for(theme: str, winning_hooks: list[dict], used: set[str]) -> str:
    """Prefer a hook the account itself already landed, within this theme."""
    for pool in (
        [h for h in winning_hooks if h.get("theme") == theme],
        list(winning_hooks),
    ):
        for h in pool:
            text = (h.get("hook") or "").strip()
            if text and text not in used:
                used.add(text)
                return text
    return ""


def build(*, shortlist: list[dict], theme_calls: dict, winning_hooks: list[dict],
          best_slot: dict, gaps: list[str] | None = None,
          start: date | None = None, days: int = 30) -> dict:
    """Produce the calendar. `shortlist` comes from themes.shortlist()."""
    start = start or date.today() + timedelta(days=1)
    gaps = gaps or []

    usable = [t for t in shortlist
              if theme_calls.get(t["name"], {}).get("call") != "ditch"]
    if not usable:
        usable = list(shortlist)
    theme_names = [t["name"] for t in usable] + gaps
    if not theme_names:
        theme_names = ["your main topic"]

    verdicts = {t["name"]: t.get("verdict", "too early to tell") for t in usable}
    for g in gaps:
        verdicts[g] = "too early to tell"

    best_day = best_slot.get("day") if best_slot.get("day_proven") else best_slot.get("day")
    shift = _rotation_offset(start, best_day)

    from ..analyse.themes import readable

    used_hooks: set[str] = set()
    rows = []
    for i in range(days):
        day_no = i + 1
        when = start + timedelta(days=i)
        ptype = cycle.POST_TYPES[(i + shift) % cycle.CYCLE]
        theme = theme_names[i % len(theme_names)]
        verdict = verdicts.get(theme, "too early to tell")
        rows.append({
            "day": day_no,
            "date": when.isoformat(),
            "weekday": when.strftime("%a"),
            "post_type": ptype["name"],
            "theme": theme,
            "prompt": ptype["shape"].format(theme=readable(theme)),
            "hook": _hook_for(theme, winning_hooks, used_hooks),
            "best_time": best_slot.get("hour") or "",
            "confidence": verdict,
            "confidence_plain": plain(verdict),
        })

    first_offer = next((r for r in rows if r["post_type"] == "OFFER"), None)
    return {
        "start": start.isoformat(),
        "days": rows,
        "mix": cycle.mix(rows),
        "themes_used": theme_names,
        "first_offer_on": first_offer["date"] if first_offer else None,
        "anchored_on": best_day,
        "anchor_proven": bool(best_slot.get("day_proven")),
        "anchor_note": (
            "The first OFFER is placed on this account's strongest weekday. "
            "After that the five-day rotation walks through the week, so each "
            "post type gets tried on each day — which is how you find out "
            "whether the day mattered."
        ) if best_day else "",
    }
