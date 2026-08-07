# Limits, and what could be done about them

Written from building and testing this, not from imagining it. Everything in
the first half is a real limit you will hit; the second half is what would
actually fix each one, roughly ordered by value divided by effort.

---

## Part 1 — Hard limits

These cannot be engineered around. They are properties of TikTok, not of this
tool, and any tool claiming otherwise is guessing.

### Owner-only metrics are unavailable, full stop

**Watch time, retention curves, average view duration, traffic sources,
follower growth over time, and audience demographics** are served by TikTok only
to the account owner, inside their own analytics. There is no public endpoint,
no scrape, and no browser trick that exposes them for an account you do not own.

This matters more than it sounds, because most creator advice is *about* watch
time. Where that is true, this tool tests what it can measure — reach by theme,
by length, by caption feature — and says plainly which is which. It does not
substitute engagement rate for retention and hope nobody notices.

### Correlation, not causation

Every finding here is "posts with X got more views than posts without X". That
is not "X caused more views". Caption features overlap with each other and with
the mood the creator was in that week; a theme that performs well may be one
they only make when they have something genuinely good to say.

The report states this on the hooks page and the method page. It is a real
ceiling on what any observational analysis of one account can claim.

### Deleted and private posts are invisible

The analysis covers what is public *right now*. A creator who deleted their
weakest posts will look better than they were; one who archived a viral run will
look worse. There is no way to know either happened.

### Small accounts genuinely cannot be measured

Groups under eight posts are never called significant, and on an account under a
few hundred posts almost every finding comes back "not enough data yet". This is
correct, not a defect — but it does mean the tool is least useful precisely
where people most want reassurance. The countdown ("+6 posts to settle") is the
best answer available, and it is a consolation rather than a solution.

---

## Part 2 — Current limits that could be fixed

### Data collection

**Theme names shift between runs of the same account.** yt-dlp sometimes returns
the *sound name* instead of the caption in `title`, inconsistently for the same
video. A cluster called `Sound / Original / <name>` is that, not a real theme.
`--no-cluster` pins previous themes as a workaround.
→ *Fix:* detect sound-name titles (they match a narrow set of patterns) and
exclude them from clustering input rather than letting them form a cluster.

**Comment text is never read.** Only counts. The comment section is the single
richest source of content ideas a creator owns, and it is sitting right there.
→ *Fix:* camofox can open a video and scroll comments. Expensive per video, so
it would only be worth doing for the top ~20 posts.

**No transcripts.** Captions are analysed; what is actually *said* in the video
is not. Two videos with identical captions can be completely different.
→ *Fix:* local Whisper on a smart sample — the top 50 and bottom 50 posts, where
the learning is. Free and unattended, but adds a heavy optional dependency and
hours of runtime.

**Audio and trending sounds are ignored** entirely, despite sound choice being a
major reach factor on TikTok.
→ *Fix:* the sound id is available in the page data; grouping by it and testing
reach would be a genuinely new axis and is not much work.

**No competitor comparison.** The tool analyses one account at a time. Peer bios
are read, but peer *performance* is not.
→ *Fix:* a `compare` mode indexing several accounts against the field median.
The statistics for it already exist in `analyse/aggregates.py`.

**Research quality varies enormously by niche.** `last30days` without API keys
leans on Reddit and Hacker News, which is strong for tech and business topics
and thin for fitness, beauty and lifestyle — exactly the niches most TikTok
creators are in. In testing, a fitness query returned eight results of which
zero were usable questions.
→ *Fix:* niche-aware source selection, and treating TikTok comments (above) as a
question source, which would be far better targeted than Hacker News.

### Analysis

**Clustering is shallow on short captions.** Silhouette scores sit around 0.04
for typical caption lengths — the clusters are real but weakly separated, which
is why the tool prefers fewer of them. `sentence-transformers` helps and is
optional because it costs 2GB.
→ *Fix:* a small quantised embedding model would get most of the benefit at a
fraction of the size.

**No time-aware analysis.** Everything is pooled across the account's whole
history. An account that changed direction six months ago is analysed as one
thing, and its old identity drags on every average.
→ *Fix:* changepoint detection on the monthly series, then analyse eras
separately. This is probably the highest-value analytical improvement here.

**Multiple comparisons are not corrected.** Around thirty tests run per report.
At p < 0.05 you would expect roughly one or two false positives per run by
chance alone.
→ *Fix:* Benjamini-Hochberg across each family of tests. Straightforward, and it
would make "solid evidence" mean what it says.

**The engagement-rate figures ignore follower count** unless camofox supplied
one. Per-1k-follower normalisation exists in the older sibling project and was
not ported.

**Hook analysis is caption-only.** The on-screen text hook — which is the actual
hook on TikTok — is never seen.
→ *Fix:* OCR on the first frame. Real work, high value.

### Output

**The 3D pie trades accuracy for appearance.** Perspective makes near slices look
larger than far ones of equal size. Every slice carries its exact percentage and
the figures repeat in the legend and table, so nothing depends on judging an
angle — but a flat chart would be a better instrument.

**No trend or delta reporting.** Each run is a snapshot. "Replies gained 18% this
month" is impossible even though the history is sitting in the database.
→ *Fix:* compare against the previous stored run. The data model already
supports it; this is mostly reporting work.

**Calendar prompts are templated.** They fill in a theme name, so they read as
generated. The hooks are drawn from the account's real posts, which helps, but
the prompts themselves are formulaic.
→ *Fix:* generate them from the actual captions of that theme's best posts. Doable
without an API key.

**Theme names are term triples** — "Workout / Glutes / Strong" — which are precise
in a table and clumsy in a sentence.

**The PDF is A4 only**, with no Letter option, and the HTML is not responsive
below about 700px.

### Operational

**No tests.** Verification was done by running the whole pipeline against real
accounts and inspecting the output. That catches integration failures well and
regressions not at all.
→ *Fix:* fixture-based unit tests on `stats`, `themes`, `store` and the parsers.
`stats.test_against_scipy()` is the pattern to follow.

**Scraping is inherently brittle.** TikTok changes its DOM without notice. The
profile reader already needs three strategies because the hydration payload
appears only sometimes. Expect breakage, and expect it silently.
→ *Fix:* a `--selftest` that runs against a known account and asserts the shape
of what comes back, so breakage is detected rather than discovered.

**Rate limiting is not handled deliberately.** There is a polite gap between
enumeration passes and scroll-until-stagnant on browser pages, but no backoff,
no quota, and no guard against someone analysing fifty accounts in a loop.

**camofox restarted on a loop — root cause found and fixed (2026-08-07).**
The `~/.camofox-browser` server was restarting its browser every ~176 seconds,
even with zero active sessions, on `Protocol error
(Browser.setDefaultViewport): Found property ".viewport.isMobile" - false
which is not described in this scheme`. Cause: the local install had resolved
`playwright-core` to `1.61.1`, which sends an `isMobile` field the bundled
Juggler protocol schema doesn't recognise — upstream (`jo-inc/camofox-browser`)
declares `playwright-core: ^1.58.0`, a caret range that floats forward and let
`npm install` pick up an incompatible newer version. Fix: pinned
`playwright-core` to an exact `1.58.1` in `~/.camofox-browser/package.json`
and did a clean `node_modules`/lockfile reinstall so the pin actually resolves
(a caret pin alone doesn't hold). Verified: `node -p
"require('playwright-core/package.json').version"` reports `1.58.1`;
`server.log` ran 4.5+ minutes past the old restart interval with zero
`isMobile`/`restarting browser` lines; `driver.py --selftest` and a direct
`camofox.profile('sidneynyaga')` call both completed via the real browser path
(`"source":"dom"`) with no restart. This is a fix to the external
camofox-browser install, not to this repo — it will drift back if that
install's `node_modules` is ever wiped and reinstalled without the pin.

The profile read also tries a plain, browser-free HTTP fetch first
(`camofox.profile_via_html`) — TikTok server-renders the same hydration JSON
into the static page for a real fraction of requests, so a hit skips camofox
entirely. This stays as a genuine reliability layer independent of the fix
above, since it avoids the browser round-trip even when camofox is healthy.

**No CI**, no packaging, no release process. Installation is `git clone` plus
two pip packages, which is the right trade for now but means updates are manual.

---

## If you only fix three things

1. **Era detection** — analysing an account that changed direction as if it never
   did is the biggest source of wrong conclusions in the tool today.
2. **Comments as a source** — for both content ideas and audience language, and
   far better targeted than the current keyless web research.
3. **Multiple-comparison correction** — because the whole design rests on the
   verdicts being trustworthy, and right now one or two per report are not.
