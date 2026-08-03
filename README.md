# Raven

**Raven reads a TikTok account and tells you what she actually found.**

Point her at any public account. She goes through every post it has ever made,
works out what travelled and what only looked like it did, and writes you a
report plus a 30-day content calendar.

Her defining habit is that **she will not overclaim.** On a young account most
findings come back "not enough data yet" — and she says so, plainly, rather
than dressing up a hunch as a finding. That is deliberate: a confident report
built on six posts is how people talk themselves out of the thing that was
working.

**Free. Local. No API key, no account, no subscription.** Two Python packages
and a browser you already have. Nothing is uploaded anywhere.

**→ [See a sample report](examples/sample-report/sample-report.pdf)** before
installing anything. It is built from invented data for a made-up account, so
you can see exactly what you get.
([HTML version](examples/sample-report/sample-report.html) ·
[the calendar it produces](examples/sample-report/sample-calendar.xlsx))

---

```
Raven is reading @someone.

3/6  Working out what actually travelled, and what only looked like it
  4 themes. The feed reads as about 2.8 distinct styles.
  Nothing here is settled yet. I would rather tell you that than guess at it.
```

Prefer a tool to a character? `--plain` turns the voice off everywhere.

## Contents

- [What you get](#what-you-get)
- [Install it](#install-it) — step by step, nothing assumed
- [Use it](#use-it)
- [Optional extras](#optional-extras)
- [Accounts that need a login](#accounts-that-need-a-login) — throwaway account and cookies, in full
- [What it cannot tell you](#what-it-cannot-tell-you)
- [Limits and roadmap](LIMITATIONS.md)
- [Please use this well](#please-use-this-well)
- [Credits](#credits) · [Contact](#contact) · [Licence](#licence)

---

## What you get

Every run writes five files to
`~/.raven/reports/<handle>/<timestamp>/`:

| File | What it is |
|---|---|
| **`report.pdf`** | The report. A4, charted, ready to print or send. |
| `report.html` | The same document, opens in any browser. |
| **`calendar.xlsx`** | 30 dated rows on a five-day rotation. Six tabs including a hook library and a progress tracker. Columns left blank for your caption, platform, and a tick when it goes out. |
| `analysis.json` | Every computed figure. Nothing is hidden in the PDF. |
| `videos.csv` | The raw catalogue. |

### What is in the report

| Section | What it answers |
|---|---|
| Cover | Which account, read through which session, when, by what version. |
| At a glance | The shape of the account — and what this report *cannot* tell you. |
| **What to make next** | A numbered list of specific things to film, ordered by evidence. |
| Reach and trajectory | Where it is heading, month by month. |
| What this account is about | Themes discovered from the captions, with a **Keep / Ditch / Test more / Try** call on each. |
| Who you are talking to | Profile audit, and how accounts around you position themselves. |
| Hooks and captions | Which caption features travel, and whether your openings have gone templated. |
| Timing and consistency | Best day and hour, and whether posting more has actually helped *you*. |
| What the niche is talking about | Demand signal, and questions people are asking right now. |
| **The next 30 days** | The calendar. |
| The frameworks behind this | The creator playbook, stated so you can use it without the report. |
| Method, limits and credits | How every number was produced. |

### The part most tools skip

Almost every finding on a young account comes back **"not enough data yet"**,
and this report says so — loudly, in the chart marks themselves. A theme drawn
from nine posts is drawn as an outline, not a solid bar. Where possible it also
tells you **how many more posts would settle it**.

That is deliberate. A confident-looking report built on six posts sends people
off to change the thing that was working. Groups under eight posts are never
called significant here, however large the gap looks.

---

## Install it

### Step 1 — Check Python

```bash
python --version
```

Needs **3.10 or newer**. If it says 3.9, "command not found", or nothing at
all, install it from [python.org/downloads](https://www.python.org/downloads/).

> **Windows:** tick **"Add python.exe to PATH"** on the first screen of the
> installer. Skipping it is the single most common reason step 3 fails.

### Step 2 — Download it

The location matters if you want the Claude skill trigger — it must go inside
`~/.claude/skills/`.

**macOS / Linux:**

```bash
git clone https://github.com/mfmp112-karl/raven ~/.claude/skills/raven
```

**Windows (PowerShell):**

```powershell
git clone https://github.com/mfmp112-karl/raven $HOME\.claude\skills\raven
```

No git? Use the green **Code** button at the top of this page → **Download
ZIP**, unzip it, and put the folder in that same place.

### Step 3 — Install the two dependencies

```bash
pip install yt-dlp openpyxl
```

That is the entire dependency list. If `pip` is not found, use
`python -m pip install yt-dlp openpyxl`.

### Step 4 — Check everything

```bash
python driver.py --doctor
```

```
[  OK  ] Python 3.10+                     3.12.10
[  OK  ] yt-dlp                           installed
[  OK  ] openpyxl                         installed
[  OK  ] Chrome / Edge (for the PDF)      chrome.exe
[  OK  ] Folder for your data             C:\Users\you\.raven
[  --  ] camofox stealth browser          not running
[  --  ] Signed-in TikTok session         no cookie file configured
[  --  ] last30days skill                 not installed
[  --  ] sentence-transformers            not installed
```

**`[  --  ]` means optional — the tool works without every one of them.** Only
`MISSING` blocks you, and each missing line prints the exact command that fixes
it.

---

## Use it

### From the command line

```bash
python driver.py @someone
```

That is the whole thing. It prints progress at each of six steps and opens the
report when it finishes.

| How big | Roughly how long |
|---|---|
| ~100 videos, no research | 40 seconds |
| ~100 videos, full research | 3–4 minutes |
| ~1,800 videos | 6 minutes |

### From Claude

If you cloned into `~/.claude/skills/`, just say:

> analyse this tiktok account for me and generate a content calendar — @someone

Claude reads [INSTALL.md](INSTALL.md), which tells it to run the doctor first,
show you the result, and ask before doing anything that needs your permission.

### Useful flags

```bash
python driver.py @handle --no-research
python driver.py @handle --no-cluster
python driver.py @handle --cap 2000 --attempts 4
python driver.py @handle --since 2026-01-01
python driver.py @handle --cookies path/to/cookies.txt
python driver.py @handle --plain
python driver.py --help
```

Re-running an account is **incremental** — it only fetches what is new.

---

## Optional extras

Each of these adds something. None are required.

| Extra | What it adds | Worth installing? |
|---|---|---|
| **Chrome / Edge / Chromium / Brave** | A proper vector PDF. | You almost certainly have one already. Edge ships with Windows. Without any of them you still get the full HTML report. |
| **[camofox-browser](https://github.com/yelban/camofox-browser)** (Node 18+) | Follower count, the profile audit, and the niche research pages. | **The biggest single upgrade** — roughly half the report. |
| **[last30days](https://github.com/mvanhorn/last30days-skill)** | What people are *asking* about your niche on Reddit, Hacker News and the web. | Strong for tech and business niches, thinner for beauty, fitness and lifestyle. |
| **`sentence-transformers`** | Marginally better theme grouping. | Skip it. ~2GB download, and the built-in method works fine. |

Starting camofox once installed:

```bash
node ~/.camofox-browser/node_modules/@askjo/camofox-browser/server.js
```

Leave that running in its own terminal. On Windows, the camofox skill's own
`camofox.sh` needs Git Bash or WSL — the command above skips the wrapper.

---

## Accounts that need a login

Some creators switch on **audience controls**. TikTok then serves their profile
only to signed-in visitors: follower counts render as `-`, the video grid is
empty, and `yt-dlp` fails with `Unable to extract secondary user ID`.

**This is a permission, not a bot block.** No tool gets past it signed out. The
tool detects it and tells you, rather than reporting the account as private.

The fix is to give it a signed-in session. Here is the whole process.

### 1. Make a throwaway TikTok account

**Do not use your main account.** Two reasons, both real:

- The file you are about to export is a **credential**. Anyone who gets hold of
  it is signed in as that account.
- Automated reading can get an account **rate-limited or restricted** by
  TikTok. Risk that on an account you do not care about.

Sign up at [tiktok.com](https://www.tiktok.com) with a spare email. It needs no
posts, no profile picture and no followers — it only ever reads.

### 2. Install a cookie export extension

Any "cookies.txt" extension will do.

- **Chrome / Edge / Brave** — search the
  [Chrome Web Store](https://chromewebstore.google.com/) for
  **"Get cookies.txt LOCALLY"**.
- **Firefox** — search [addons.mozilla.org](https://addons.mozilla.org/) for
  **"cookies.txt"**.

> Read the reviews and the requested permissions before installing. These
> extensions can read your cookies for **every** site by design, which is
> exactly why you want one that is open-source and works offline. A cookie
> exporter that phones home is the last thing you want.

### 3. Sign in and export

1. Sign into **the throwaway account** at [tiktok.com](https://www.tiktok.com).
2. Stay on a tiktok.com page.
3. Click the extension's icon.
4. Choose **Export** / **Save as cookies.txt** for the current site.
5. Save the file somewhere private — **not** inside this repo.

The file is plain text and starts with `# Netscape HTTP Cookie File`.

### 4. Point the tool at it

Pass it each time:

```bash
python driver.py @handle --cookies /path/to/cookies.txt
```

Or save it once at `~/.raven/tiktok-cookies.txt` and it is
picked up automatically.

### 5. Check it worked

```bash
python driver.py --doctor
```

```
[  OK  ] Signed-in TikTok session    41 TikTok cookies, signed in, 21.0 days left
```

You will see one of three things: it is working, **the session has expired**
(sign in again and re-export), or **no sessionid found** (you exported while
signed out).

### What the tool does and does not do with it

- It **never asks for a password** and **never logs anybody in**. You
  authenticate in your own browser; the tool only reads a file that already
  exists.
- It **never prints a cookie value.** The doctor reports names, counts and days
  remaining, nothing more.
- It **never copies or uploads the file.** The path is read at run time, and
  that is all.
- Sessions expire. When one does the doctor says so — which matters, because an
  expired session and a private account look identical otherwise.

`*cookies*.txt` is in `.gitignore` as a backstop, but keep the file outside the
repo anyway.

---

## What it cannot tell you

**Watch time, retention curves, average view duration, traffic sources,
follower growth over time and audience demographics** are served by TikTok
**only to the account owner**, inside their own analytics.

No tool can get them for an account it does not own. Anything claiming
otherwise is guessing.

A great deal of creator advice is *about* watch time. Where that is true, this
tests what it can actually measure and says which is which, rather than
substituting a proxy and hoping you do not notice.

There is a fuller accounting in **[LIMITATIONS.md](LIMITATIONS.md)** —
including what is simply not built yet, and what it would take to fix each one.

---

## Please use this well

This exists to help people grow their accounts meaningfully — by understanding
what they have already made, and deciding what to make next.

It reads **public data only**. It takes nothing TikTok does not show any
logged-out visitor. It automates **no engagement whatsoever**: no posting,
following, liking, commenting or messaging.

Please do not use it to harass, impersonate or target anyone, to scrape private
accounts, or to build profiles of private individuals. If you are analysing
somebody else's account, treat it as competitive research — the way you would
read a competitor's public website — not as surveillance of a person.

---

## Credits

- **The 30-day content calendar method** — the five post types and the five-day
  rotation this tool is built around — is
  **[themarketingfmpodcast](https://www.instagram.com/marketingfmpodcastke)**'s
  work. Every file the tool writes carries
  `themarketingfmpodcast - Free Tool, Share it.`
- **The creator growth playbook** behind the profile audit and the
  content-style analysis is
  **[@teezytheturtle](https://www.instagram.com/teezytheturtle)**'s.
- **[camofox-browser](https://github.com/yelban/camofox-browser)** (MIT,
  © yelban) — stealth browsing.
- **[last30days](https://github.com/mvanhorn/last30days-skill)** (MIT,
  mvanhorn) — cross-platform research.

Neither camofox nor last30days is bundled here. The tool talks to them if they
are installed, so they stay yours to update.

## Contact

- **Bugs, questions, feature requests** —
  [open an issue](https://github.com/mfmp112-karl/raven/issues).
- **Anything else** — <themarketingfmpod317@gmail.com>

Pull requests welcome. [LIMITATIONS.md](LIMITATIONS.md) doubles as the roadmap
and names the three changes worth making first.

## Licence

[MIT](LICENSE) — free to use, modify and redistribute, including commercially.
© 2026 themarketingfmpodcast, whose 30-day calendar method Raven is built
around.

The credit line in the output is a courtesy the tool keeps for itself, not a
condition of the licence. Keeping it costs you one line and is simply the
decent thing to do.
