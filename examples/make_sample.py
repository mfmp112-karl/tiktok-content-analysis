#!/usr/bin/env python3
"""Build the sample report from invented data.

The point of the sample is to show someone the *shape* of what they get before
they install anything. Publishing a real account's analysis to do that would
mean publishing a real person's numbers and captions in a repo they never
agreed to be in, so this generates a fictional account instead.

Everything below is made up. @example_creator does not exist. The figures are
shaped to be plausible rather than flattering — including a theme that is
genuinely underperforming and a pile of "not enough data yet" verdicts, because
that is what a real report looks like and a sample that hides it would be
advertising rather than documentation.

    python examples/make_sample.py
"""
from __future__ import annotations

import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tta import __version__, console, store                      # noqa: E402
from tta.analyse import aggregates as ag, cadence, hooks, themes  # noqa: E402
from tta.calendar import build as calbuild, recommend, workbook   # noqa: E402
from tta.report import html as rhtml, pdf                         # noqa: E402

HANDLE = "example_creator"
OUT = Path(__file__).resolve().parent / "sample-report"

#: (theme captions, relative reach). One theme deliberately underperforms.
THEMES = [
    (["3 ways to fix your {thing} in under a minute",
      "The {thing} mistake almost everyone makes",
      "How I finally understood {thing}",
      "Stop doing this with your {thing}",
      "{thing} explained properly, no jargon"], 1.6, ["setup", "lighting", "audio",
                                                      "framing", "editing"]),
    (["Day {n} of building this in public",
      "What {n} months of this actually looked like",
      "My honest numbers after {n} weeks",
      "Before and after {n} days"], 1.2, None),
    (["Answering your questions about {thing}",
      "You asked, so here it is: {thing}",
      "Replying to a comment about {thing}"], 1.0, ["gear", "pricing", "clients",
                                                    "software", "workflow"]),
    (["New drop out now, link in bio",
      "Last chance on this one",
      "Limited spots left, DM me",
      "Grab this before it goes"], 0.45, None),
]


def synth_videos(n: int = 180, seed: int = 11) -> list[dict]:
    rng = random.Random(seed)
    start = date.today() - timedelta(days=430)
    rows = []
    for i in range(n):
        pool, lift, things = THEMES[i % len(THEMES)]
        text = pool[rng.randrange(len(pool))]
        text = text.replace("{n}", str(rng.choice([7, 30, 60, 90, 100])))
        if things:
            text = text.replace("{thing}", rng.choice(things))
        else:
            text = text.replace("{thing}", "it")
        if rng.random() < 0.4:
            text += " " + rng.choice(["#creator", "#howto", "#smallbusiness",
                                      "#behindthescenes", "#tutorial"])

        when = datetime.combine(start + timedelta(days=int(i * 430 / n)),
                                datetime.min.time()) + timedelta(
            hours=rng.choice([8, 11, 13, 17, 18, 19, 21]),
            minutes=rng.randrange(60))
        base = rng.lognormvariate(7.4, 0.85) * lift
        views = int(base * (1 + i / n * 0.5))          # gentle growth over time
        rows.append({
            "video_id": f"sample{i:04d}",
            "url": f"https://www.tiktok.com/@{HANDLE}/video/sample{i:04d}",
            "title": text,
            "views": views,
            "likes": int(views * rng.uniform(0.05, 0.13)),
            "comments": int(views * rng.uniform(0.002, 0.012)),
            "shares": int(views * rng.uniform(0.001, 0.02)),
            "duration": rng.choice([9, 14, 18, 23, 27, 34, 41, 52, 68, 95]),
            "uploaded": when.isoformat(timespec="seconds"),
        })
    return rows


def main() -> int:
    console.setup()
    OUT.mkdir(parents=True, exist_ok=True)
    db = OUT / "_sample.sqlite3"
    if db.exists():
        db.unlink()

    with store.connect(db) as conn:
        store.upsert_videos(conn, HANDLE, synth_videos())
        store.upsert_creator(conn, HANDLE, followers=8420, following=112,
                             hearts=143000, nickname="Example Creator",
                             bio="I make things and show my working.\n"
                                 "New here every Tuesday.",
                             link="")
        conn.commit()
        videos = store.load_videos(conn, HANDLE)

        info = themes.cluster(videos, log=lambda m: None)
        store.set_themes(conn, HANDLE, info["assignments"])
        conn.commit()
        videos = store.load_videos(conn, HANDLE)
        creator = store.creator(conn, HANDLE)

    analysis = ag.build(videos)
    hook_info = hooks.build(videos)
    cad = cadence.build(videos, analysis["weekday"], analysis["hour"])
    shortlisted = themes.shortlist(analysis["theme"])
    calls = themes.calls(analysis["theme"])

    # No network in a sample build: the research block is rendered exactly as
    # it appears when camofox and last30days are not installed, which is also
    # the most common first-run state.
    demand = {
        "topics": [], "peers": [], "audience_words": [], "gaps": [],
        "last30days": [], "l30_clusters": [],
        "coverage": [
            {"source": "TikTok (via camofox)", "ok": False,
             "note": "not installed for this sample build"},
            {"source": "last30days (Reddit, Hacker News, web)", "ok": False,
             "note": "not installed for this sample build"},
        ],
    }

    recs = recommend.build(analysis=analysis, theme_calls=calls,
                           shortlist=shortlisted, hook_info=hook_info,
                           cadence_info=cad, research=demand, profile_audit=None)

    cal = calbuild.build(shortlist=shortlisted, theme_calls=calls,
                         winning_hooks=hook_info["winning_hooks"],
                         best_slot=cad["best_slot"])
    workbook.write(cal, handle=HANDLE,
                   winning_hooks=hook_info["winning_hooks"],
                   repetition=hook_info["repetition"],
                   out_path=OUT / "sample-calendar.xlsx")

    ctx = {
        "meta": {"handle": HANDLE,
                 "accessed_via": "sample build - no account was read",
                 "harvest_tier": "invented data (see examples/make_sample.py)",
                 "generated": rhtml.now_stamp(), "version": __version__},
        "creator": creator, "analysis": analysis, "themes": info,
        "hooks": hook_info, "cadence": cad, "theme_calls": calls,
        "profile_audit": None, "peers": [], "research": demand,
        "calendar": cal, "recommendations": recs,
        "limits": rhtml.default_limits(),
        "narrative": {
            "summary": "This is a sample report built from invented data, so "
                       "you can see the shape of the output before installing "
                       "anything. @example_creator is not a real account and "
                       "every number below is fictional.",
        },
    }

    result = pdf.write(rhtml.render(ctx), OUT, stem="sample-report",
                       log=lambda m: print(m))
    store.export_csv(videos, OUT / "sample-videos.csv")
    db.unlink(missing_ok=True)
    for junk in OUT.glob("_sample.sqlite3*"):
        junk.unlink(missing_ok=True)

    print(f"\nSample built in {OUT}")
    print(f"  {len(videos)} invented videos, {info['k']} themes, "
          f"{len(recs)} recommendations")
    if result["pdf"]:
        print(f"  {result['pdf'].name} ({result['pdf'].stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
