# Installing this skill

Two audiences here. **Part 1** is for the person installing it. **Part 2** is
for Claude — what it should do on first run, and what it must ask permission
for. If you are handing this to someone non-technical, send them Part 1 and let
Claude read Part 2 itself.

---

# Part 1 — For the person installing

## The short version

```bash
git clone https://github.com/mfmp112-karl/tiktok-content-analysis ~/.claude/skills/tiktok-content-analysis
cd ~/.claude/skills/tiktok-content-analysis
pip install yt-dlp openpyxl
python driver.py --doctor
```

Then, in Claude Code, say:

> analyse this tiktok account for me and generate a content calendar — @someone

That is the whole installation. `--doctor` will tell you if anything is
missing, and each line it prints comes with the one command that fixes it.

## Step by step

### 1. Check you have Python 3.10 or newer

```bash
python --version
```

If that says 3.9 or lower, or "command not found", install Python from
[python.org](https://www.python.org/downloads/). On Windows, tick **"Add
Python to PATH"** in the installer — skipping it is the single most common
reason the next step fails.

### 2. Clone into your skills folder

The clone *location* is what makes it a Claude skill. It must go inside
`~/.claude/skills/`.

```bash
git clone https://github.com/mfmp112-karl/tiktok-content-analysis ~/.claude/skills/tiktok-content-analysis
```

On Windows in PowerShell, `~` works the same way:

```powershell
git clone https://github.com/mfmp112-karl/tiktok-content-analysis $HOME\.claude\skills\tiktok-content-analysis
```

If you would rather keep it somewhere else, clone wherever you like and run it
with `python driver.py` directly. You lose the trigger phrase, not the tool.

### 3. Install the two dependencies

```bash
pip install yt-dlp openpyxl
```

That is the entire list. If `pip` is not found, try `python -m pip install
yt-dlp openpyxl`.

### 4. Run the doctor

```bash
python driver.py --doctor
```

You should see something like this:

```
[  OK  ] Python 3.10+                     3.12.10
[  OK  ] yt-dlp                           installed
[  OK  ] openpyxl                         installed
[  OK  ] Chrome / Edge (for the PDF)      chrome.exe
[  OK  ] Folder for your data             C:\Users\you\.tiktok-content-analysis
[  --  ] camofox stealth browser          not running
[  --  ] Signed-in TikTok session         no cookie file configured
[  --  ] last30days skill                 not installed
[  --  ] sentence-transformers            not installed
```

**Anything marked `[  --  ]` is optional.** The tool runs without all of them.
Only `MISSING` blocks you.

### 5. Run it

```bash
python driver.py @someone
```

A small account takes about 40 seconds without research, or 3–4 minutes with
it. A 1,800-video account takes about 6 minutes. Everything lands in
`~/.tiktok-content-analysis/reports/<handle>/<timestamp>/` and opens
automatically when it finishes.

## The optional extras, and what each one buys you

| Extra | What you gain by adding it | Worth it? |
|---|---|---|
| **Chrome / Edge / Chromium / Brave** | A proper vector PDF. | You almost certainly have one. Edge ships with Windows. |
| **[camofox-browser](https://github.com/yelban/camofox-browser)** (needs Node 18+) | Follower count, the profile audit, and the niche research pages. | The biggest single upgrade. Adds roughly half the report. |
| **[last30days](https://github.com/mvanhorn/last30days-skill)** | What people are *asking* about your niche on Reddit, Hacker News and the web. | Strong for tech and business niches, thinner for lifestyle ones. |
| **A signed-in TikTok session** | Accounts that have audience controls switched on. | Only if you hit one. Run `python driver.py --help-session`. |
| **`sentence-transformers`** | Marginally better theme clustering. | Skip it unless you are analysing very large accounts. It is a ~2GB download. |

### Setting up a signed-in session (only if you hit a blocked account)

Some creators switch on **audience controls**, which makes TikTok serve their
profile only to signed-in visitors. You will know because the run stops and
tells you so.

**1. Make a throwaway TikTok account.** Not your main one. The export below is
a credential, and automated reading can get an account rate-limited. A spare
email is all it needs — no posts, no picture, no followers.

**2. Install a cookie export extension.** Search the Chrome Web Store for
"Get cookies.txt LOCALLY", or addons.mozilla.org for "cookies.txt" on Firefox.
Read the permissions first: these can read cookies for every site by design,
so prefer one that is open-source and works offline.

**3. Sign in as the throwaway account, stay on a tiktok.com page, click the
extension, and export.** Save the file somewhere private — not in this repo.
It should start with `# Netscape HTTP Cookie File`.

**4. Point the tool at it:**

```bash
python driver.py @handle --cookies /path/to/cookies.txt
```

Or save it as `~/.tiktok-content-analysis/tiktok-cookies.txt` to skip the flag.

**5. Confirm:** `python driver.py --doctor` will show either a working session
with days remaining, an expired one, or a file exported while signed out.

Full detail, including what the tool does and does not do with the file, is in
the [README](README.md#accounts-that-need-a-login).

### Starting camofox

```bash
node ~/.camofox-browser/node_modules/@askjo/camofox-browser/server.js
```

Leave that running in its own terminal while you use the tool. On Windows the
skill's own `camofox.sh` wrapper needs Git Bash or WSL — the command above
avoids the wrapper entirely.

## What it does to your machine

- Creates **one folder**: `~/.tiktok-content-analysis/`. One SQLite file for
  the accounts you analyse, one folder per report. Delete it and every trace of
  the tool's data is gone.
- Writes **nothing** anywhere else, and **uploads nothing anywhere**.
- Makes network requests only to TikTok (to read public pages) and, if you have
  the extras, to whatever `last30days` queries.
- Automates **no** engagement: no posting, following, liking, commenting or
  messaging. It only ever reads.

---

# Part 2 — For Claude

Read this before the first run in a session.

## On first invocation, always

1. **Run `python driver.py --doctor` and show the user the output.** Do not
   skip it and do not summarise it away. The optional items materially change
   how complete the report is, and the user should decide whether to install
   any of them before waiting several minutes for a run.
2. **If required items are missing**, give the user the exact fix line the
   doctor printed. Do not install anything on their behalf without asking.
3. **If optional items are missing**, say in one sentence what each one would
   add, then ask whether to proceed without them or wait. Do not editorialise
   further — most people will want to proceed.

## Permissions to ask for, and when

| Action | Ask first? | Why |
|---|---|---|
| Creating `~/.tiktok-content-analysis/` | **Yes, once** | It is a new folder in their home directory. Say what goes in it and that deleting it removes everything. |
| `pip install yt-dlp openpyxl` | **Yes** | Installing packages into their environment is their call. Offer the command; let them run it or approve it. |
| Running `driver.py @handle` | No | Reads public pages only. |
| Starting the camofox server | **Yes** | It launches a background browser process and, on first use, downloads ~300MB. |
| Using a signed-in session (`--cookies`) | **Yes, explicitly** | See below. This is the sensitive one. |
| Using the user's own logged-in Chrome | **Yes, explicitly** | Their authenticated session. Never do this on your own initiative. |
| Installing `sentence-transformers` | **Yes** | ~2GB. Almost never worth it. Say so. |

## The rules that are not negotiable

**Never ask for a TikTok password, and never log anyone in.** If an account
needs a signed-in session, point the user at `python driver.py --help-session`
and let them export a cookie file themselves. The tool consumes a file that
already exists; it never authenticates.

**Never print or echo a cookie value.** If you need to talk about a session,
use `python driver.py --doctor`, which reports cookie names, counts and days
remaining and nothing else.

**Tell them to use a throwaway TikTok account** for any signed-in reading. The
cookie file is a credential, and automated reading can get an account
rate-limited. Say this once, plainly, not repeatedly.

**Do not touch their real browser without explicit permission**, and when they
grant it, keep it read-only: open, scroll, read. No clicking anything that
follows, likes, posts, or sends.

## Reading the results

After a run finishes:

1. **Read `analysis.json`** — it holds every computed figure.
2. **Respect the verdicts.** Anything marked `too early to tell` is not a
   finding. Do not narrate it as one. On accounts under a few hundred posts,
   that will be most of the report, and saying so plainly is the correct
   outcome rather than a disappointing one.
3. **Never invent a number.** Every figure you quote must come from
   `analysis.json`.
4. Optionally write section commentary to a JSON file and re-render with
   `--narrative notes.json`. Keys: `summary`, `glance`, `reach`, `themes`,
   `audience`, `hooks`, `timing`, `demand`, `calendar`, `recommendations`.

## When a run fails

| What you see | What it means | What to do |
|---|---|---|
| `Unable to extract secondary user ID` | Almost always audience controls, not a typo. | The driver detects this and explains it. Offer `--help-session`. |
| Driver exits 3 with a permission request | Account is signed-in-only. | Relay the request verbatim. Do not attempt a workaround. |
| `HarvestBlocked` | Private, renamed, or genuinely no public posts. | Check the handle with the user before retrying. |
| `AttributionError` | The credit line has been altered. | Restore it. This is deliberate — see LICENSE. |
| `database is locked` | Another run is in progress. | Wait for it, or run `--doctor` to check the journal mode. |

## Do not

- Do not run analyses on many accounts in a loop without asking. Each one makes
  real requests to someone else's servers.
- Do not present "not enough data yet" as a failure of the tool.
- Do not offer to remove the attribution line. See LICENSE.
- Do not claim the report contains watch time, retention, traffic sources or
  demographics. It cannot, and no tool can for an account it does not own.
