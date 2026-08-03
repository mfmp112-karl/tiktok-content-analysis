---
name: raven
description: Raven analyses any public TikTok account and generates a 30-day content calendar. Use when asked to analyse, audit, review or research a TikTok account or creator, to build a TikTok or short-form content calendar or content plan, to find what themes and hooks work on an account, or to produce a TikTok performance report or PDF. Triggers include "analyse this tiktok account", "tiktok content calendar", "audit my tiktok", "what should I post", "content plan for @handle", "ask Raven", "run Raven on".
user_invocable: true
argument_hint: "@handle"
license: MIT
---

# Raven — TikTok content analysis

Raven reads a public TikTok account's whole catalogue, works out what has
actually worked, and writes a 30-day content calendar plus a print-ready PDF.

No API key, no account, no paid service. Two Python packages and a browser you
almost certainly already have.

**Her one defining habit: she will not overclaim.** Most findings on a young
account come back "not enough data yet" and she says so plainly, in the chart
marks as well as the words. Do not talk her out of that when you narrate the
report — it is the whole point of her. `--plain` drops the voice entirely for
scripts and for people who want a tool rather than a character.

**All paths below are relative to this skill's own directory.**

## Run it (the agent path)

```bash
python driver.py --doctor
```

Run this first, always. It prints what is installed, what is missing, and the
one line that fixes each. Present its output to the user before going further —
the optional items change how complete the report will be.

```bash
python driver.py @handle
```

That is the whole thing: harvest, profile, analyse, research, calendar, report.
It prints progress per step and finishes with a folder path.

Useful variations, all verified:

```bash
python driver.py @handle --no-research --no-open
python driver.py @handle --cap 2000 --attempts 4 --scrolls 4 --topics 2
python driver.py @handle --no-cluster --since 2026-01-01
```

| Flag | Why you would use it |
|---|---|
| `--no-research` | Skips niche research. Cuts a 3-minute run to about 40 seconds. |
| `--no-profile` | Skips the camofox profile read (no follower count, no profile audit). |
| `--no-cluster` | Reuses themes already stored. Fast re-runs. |
| `--cap N` / `--attempts N` | Large accounts. TikTok's pagination depth is non-deterministic. |
| `--scrolls N` / `--topics N` | How deep and how wide the research goes. Each costs real time. |
| `--since YYYY-MM-DD` | Ignore older posts. |
| `--narrative FILE` | JSON of written commentary to fold into the report — see below. |
| `--plain` | Drop Raven's voice. Terse, parseable output. |
| `--cookies FILE` | A signed-in session, for accounts with audience controls on. |

## Accounts you cannot read signed out

Some creators switch on **audience controls**, which makes TikTok serve their
profile to signed-in visitors only. Follower counts render as `-`, the video
grid is empty, and yt-dlp fails with `Unable to extract secondary user ID`.
This is a permission, not a bot check — no amount of stealth gets past it, and
the tool now detects it and says so rather than reporting the account as
private.

The fix is a signed-in session, supplied as a cookies.txt file:

```bash
python driver.py --help-session
python driver.py @handle --cookies /path/to/cookies.txt
python driver.py --doctor
```

The file is used by yt-dlp for the fast path and imported into camofox via
`POST /sessions/:userId/cookies` for the browser path, so both tiers are signed
in. Saved at `~/.raven/tiktok-cookies.txt` it is picked up
without the flag.

**Never log a user in and never ask for a password.** They export a session
from their own browser; this tool only ever reads a file that already exists,
and never prints a cookie value — the doctor reports names, counts and expiry
only. Tell them to use a throwaway account: the file is a credential, and
automated reading can get an account rate-limited.

Expired sessions are detected and reported as expired, which matters because
the failure mode otherwise looks identical to a private account.

## What the report contains

Ten sections, in this order. The two that people read first are **What to make
next** and **The next 30 days**.

| Section | What it answers |
|---|---|
| Cover | Which account, read through which session, when, by what version — plus the ethical-use notice. |
| At a glance | The shape of the account, and what this report cannot tell you. |
| **What to make next** | A numbered list of specific things to film, ordered by evidence. |
| Reach and trajectory | Where it is heading, month by month. |
| What this account is about | Themes as a 3D pie, with Keep / Ditch / Test more / Try. |
| Who you are talking to | Profile audit and how peers position themselves. |
| Hooks and captions | Which caption features travel; whether openers are templated. |
| Timing and consistency | Best day and hour, and whether posting more has helped. |
| What the niche is talking about | Demand signal, and what people are actually asking. |
| **The next 30 days** | The calendar, on the five-day rotation. |
| The frameworks behind this | The creator playbook, stated so it can be used without the report. |
| Method, limits and credits | How every number was produced. |

## What it writes

Everything lands in `~/.raven/reports/<handle>/<timestamp>/`:

| File | What it is |
|---|---|
| `report.pdf` | The report. A4, charts, provenance and ethics notice on the cover. |
| `report.html` | Same document, opens in any browser. Always written. |
| `calendar.xlsx` | Six tabs: how to use, post type guide, the 30-day grid, hook library, content mix, progress tracker. |
| `analysis.json` | Every computed figure. This is what you narrate from. |
| `videos.csv` | The raw catalogue. |

The account database is a single file at `~/.raven/tta.sqlite3`.
Re-running an account is incremental — it only fetches what is new.

## Writing the narration

The report renders complete and sound with no narration at all. To add prose,
read `analysis.json`, write a JSON file of section commentary, and pass it:

```bash
python driver.py @handle --narrative notes.json
```

Keys: `summary`, `glance`, `reach`, `themes`, `audience`, `hooks`, `timing`,
`demand`, `calendar`. Values are plain text; a blank line starts a paragraph.

**Never invent a number.** Every figure you write must come from
`analysis.json`. And respect the verdicts: anything marked `too early to tell`
is not a finding, and writing about it as though it were defeats the entire
point of the report.

## Gotchas

These all cost real time to discover.

- **camofox has an undocumented `/tabs/:id/evaluate` endpoint.** Its own
  SKILL.md and API reference list only navigate/click/type/scroll/snapshot/
  links/screenshot. `evaluate` runs arbitrary JS and returns JSON, which is the
  only reason reading TikTok profiles is reliable. Also undocumented:
  `/extract`, `/viewport`, `/images`, `/wait`, `/press`.

- **`__UNIVERSAL_DATA_FOR_REHYDRATION__` is often simply absent.** The same
  profile URL serves it on one load and not the next. A reader that depends on
  it reports "login wall" for pages that rendered perfectly. `camofox.PROFILE_JS`
  tries hydration JSON, then labelled DOM nodes, then visible text.

- **camofox needs about 12 seconds on a TikTok profile.** At 6 seconds the page
  is still a `Log in` shell with `document.title == ""`. Poll for the data
  rather than sleeping a constant.

- **camofox restarts its browser under you.** Requests then fail with
  `code: "browser_restarted"` and every existing `tabId` is void. Open a new tab
  rather than retrying the old one.

- **A concatenated theme phrase is not a hashtag.** `#workoutandglutes` returns
  HTTP 410 and no amount of retrying helps. Try the individual words, then fall
  back to search. Do not retry 4xx.

- **Generic tags poison theme discovery.** `#fyp`, `#viral` and `#foryou` are on
  everything, so a naive frequency count makes them the top "topic" and the
  calendar ends up saying "teach one thing about #fyp".

- **Silhouette scores on short captions are tiny and flat** — k=4 and k=7 will
  differ by 0.004. Taking the strict maximum shatters an account into themes
  nobody can act on. Prefer the smallest k within tolerance of the best.

- **Windows console is cp1252 and TikTok captions are full of emoji.** Printing
  one crashes the process mid-run. Every entry point calls `tta.console.setup()`
  before anything else.

- **`chrome --screenshot=name.png` writes relative to Chrome's cwd**, not yours.
  Pass an absolute path or the file appears somewhere surprising.

- **Camoufox cannot make a PDF.** It is a Firefox fork, and Playwright's
  `page.pdf()` is Chromium-only. The camofox PDF route screenshots the page and
  wraps the images; it is a genuine fallback, not an equal option.

- **Almost everything will say "not enough data yet"** on an account under a few
  hundred posts. That is correct behaviour, not a bug. Groups under 8 posts are
  never called significant.

- **yt-dlp sometimes returns the sound name instead of the caption** in `title`,
  and not consistently for the same video across pulls. Re-analysing an account
  can therefore produce different theme names — a cluster called
  `Sound / Original / <name>` is this, not a real theme. The clustering itself
  is deterministic (fixed seed); the input text is what moved. Use
  `--no-cluster` when you want a re-run to match a previous report exactly.

- **last30days must be called as `--emit json --output FILE`.** The compact
  emitter plus a `--save-dir` glob returns nothing while still exiting zero, so
  the report says "ran but returned nothing usable" and it reads like the
  skill's fault. Also: more than one copy is usually installed and they drift
  many versions apart, so pick by the `version:` in frontmatter — older builds
  have no `--register` or `--output`.

- **Send it one topic, not a concatenation.** Joining two mechanical theme
  labels produced the query "workout and glutes cardio and work", which came
  back as eight Hacker News product launches.

- **Research results need a junk filter.** Left unfiltered, the recommendations
  read "Answer this: Show HN: open-source workout tracker". `recommend.
  is_filmable_question` drops launches, link-dumps, promos and titles ending in
  a parenthesised year, and requires an actual question shape.

- **Two runs at once used to deadlock.** The database is opened WAL with a
  60-second busy timeout, which fixes it — but a database created by an older
  version stays in rollback mode, and the conversion can only happen when no
  other run holds the file. `--doctor` reports the journal mode.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `No module named 'yt_dlp'` | `pip install yt-dlp openpyxl` |
| `HarvestBlocked: enumerated nothing` | Account is private, renamed, or TikTok is blocking this machine. Start camofox and re-run; the driver falls back automatically. |
| `camofox could not open ... HTTP 500` | Cold start. It retries. If it persists, restart the server. |
| `profile did not hydrate` | Rate limiting. Wait a few minutes, or run with `--no-profile`. |
| Chrome prints a 0-byte PDF | Another Chrome is holding the profile dir. The driver uses a fresh temp profile per run, so this means a stale lock — delete it or set `TTA_BROWSER`. |
| `AttributionError` | The credit line in `tta/attribution.py` was altered. Restore it. |
| Run is very slow | Research dominates. `--no-research`, or lower `--scrolls` and `--topics`. |

## Start camofox

Optional, but it unlocks follower counts, the profile audit and niche research.

```bash
node ~/.camofox-browser/node_modules/@askjo/camofox-browser/server.js
```

Or via the skill's own wrapper, which is bash-only (Git Bash or WSL on Windows):

```bash
bash ~/.claude/skills/camofox-browser/scripts/camofox.sh start
```

## Attribution

The 30-day calendar method — the five post types and the five-day rotation — is
themarketingfmpodcast's. Every artefact this tool writes carries
`themarketingfmpodcast - Free Tool, Share it.`, and the run fails if that has
been stripped. See `LICENSE`.
