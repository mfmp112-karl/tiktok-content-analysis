# The growth playbook, and what this tool does with it

The profile audit and the content-style analysis are built on a widely-taught
creator growth playbook (credited: **@teezytheturtle**). Its advice: find your
niche by studying creators already in it, optimise the profile that converts
visitors into followers, find a unique content style by testing and dropping,
lead with a strong hook, and post daily.

**Every part of it is treated as a hypothesis to test against the account's own
data, not a rule to repeat.** That is the whole design stance here, and it is
worth defending: the account in front of you is better evidence about itself
than any general advice, and a report that just recites the advice back is
worth nothing to the person reading it.

## The mapping

| Playbook claim | What this tool does |
|---|---|
| Study creators already in your sub-niche | `research/tiktok_demand.py` reads peer profiles from hashtag and search pages and shows their bios verbatim. Positioning is legible in a bio in a way it never is in a view count. |
| Note how they name their audience in the bio | `audience_words()` finds words repeated across peer bios. |
| Profile picture must read at small size | Not scored — see below. Rendered at 96px, 40px and 24px so the creator sees it. |
| Bio should sell the follow, 3–4 short lines | Measured: length, line count, whether it names an audience, whether it states a benefit, whether it points at the link. |
| Have a link even with nothing to sell | Checked, with the reasoning attached. |
| Test styles, drop what fails, replace, repeat | This is theme clustering plus indexed reach. Each theme gets **Keep / Ditch / Test more / Try**. |
| Have a *unique* style, post it consistently | Herfindahl concentration over themes, reported as "your feed reads as about N distinct styles". |
| A great, unique hook | Caption features tested against reach, plus an n-gram check on opening phrasing. |
| Post daily | `cadence.consistency()` compares busy months against quiet months on this account's own reach. |
| Depth over 4-second trend posts | Duration and caption-length buckets, tested. |
| Watch time is what matters | **Cannot be measured.** See below. |

## Two places the tool deliberately refuses

**The profile picture is not scored.** Judging "does this read at 24px" from the
image bytes would need real image analysis, and the honest options were a
fabricated heuristic or nothing. Instead the report shows the actual avatar at
the three sizes it appears at in the wild and lets the creator decide — which is
what would have convinced them anyway. A made-up score would have looked more
sophisticated and been worse.

**Watch time and retention are unobtainable.** TikTok serves them only to the
account owner, inside their own analytics. No tool can get them for an account
it does not own. Since the playbook leans on watch time heavily, the report
states this plainly rather than substituting engagement rate and hoping nobody
notices the difference.

## Why "Ditch" is hard to earn

A theme is only called a loser if it is **below the account average *and* the
gap cleared a significance test**. A theme that merely looks weak stays in the
rotation as "Test more".

This is deliberate and it matters. Most creators are one bad report away from
abandoning the thing they are still getting good at. Groups under eight posts
are never called significant however large the gap looks, and on a young account
almost everything comes back "not enough data yet" — which is the correct
answer, and far more useful than a confident one drawn from noise.

## Evidence this works

Run against a 1,859-post account, the analysis independently identified two
large clusters of templated promotional captions — 245 and 193 posts, indexing
63 and 25 against the account's own average, both `strong`. That account's
owner had previously found the same two clusters by hand and reached the same
conclusion: the weak thing was not the topic, it was the promotional voice.
The clustering found it from captions alone, with no prior knowledge.
