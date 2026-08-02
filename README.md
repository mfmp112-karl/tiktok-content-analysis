# TikTok Content Analysis

Point it at a public TikTok account. Get back a report that explains what has
actually worked on that account, and a 30-day content calendar built from it.

No API key. No account. No paid service. Nothing leaves your machine except the
requests needed to read public pages.

```bash
git clone https://github.com/YOUR-USERNAME/tiktok-content-analysis ~/.claude/skills/tiktok-content-analysis
cd ~/.claude/skills/tiktok-content-analysis
pip install yt-dlp openpyxl
python driver.py --doctor
python driver.py @someone
```

If you use Claude Code, that clone location makes it a skill — say
*"analyse this tiktok account for me and generate a content calendar"* and it
runs itself.

---

## What you get

Written to `~/.tiktok-content-analysis/reports/<handle>/<timestamp>/`:

- **`report.pdf`** — A4, charted, with the account, the session it was read
  through, and the date on the cover.
- **`report.html`** — the same document in any browser.
- **`calendar.xlsx`** — thirty dated rows on a five-day rotation, with a hook
  library and a progress tracker. Columns for your caption, platform and a tick
  when it goes out.
- **`analysis.json`** and **`videos.csv`** — everything computed, nothing locked in.

## What it actually does

1. **Reads the catalogue** with `yt-dlp`, which returns views, likes, comments,
   shares, caption, duration and upload time for every public post without
   downloading anything.
2. **Reads the profile** — follower count, bio, avatar — through the camofox
   stealth browser, if you have it.
3. **Finds the themes** by clustering the captions, rather than guessing from
   keywords. The number of themes adapts to the size of the account.
4. **Tests everything.** Every split — theme, day, hour, length, caption
   feature — is checked with Welch's t-test on log-transformed views. Findings
   are labelled *solid evidence*, *early signal*, or *not enough data yet*.
5. **Checks the niche** by reading TikTok's own hashtag and search pages through
   camofox, and peer bios to see how others position themselves.
6. **Asks what the niche is asking** through the `last30days` skill — Reddit,
   Hacker News and the web. A question somebody actually typed out is the best
   content prompt there is.
7. **Recommends what to make**, as a numbered list ordered by how much evidence
   sits behind each item: double down on what already travels, rework what
   demonstrably does not, answer the questions people are asking, and try the
   one or two things the niche is doing that this account has never touched.
8. **Builds the calendar** from the account's own strongest themes and its own
   best-performing openings.

### The part most tools skip

Almost every finding on a young account comes back **"not enough data yet"**,
and this report says so, loudly, in the chart marks themselves. A theme drawn
from nine posts is drawn as an outline, not a solid bar.

That is deliberate. A confident-looking report built on six posts will send
someone off to change the thing that was working. Groups under eight posts are
never called significant here, however large the gap looks.

## Requirements

**Required:** Python 3.10+, and `pip install yt-dlp openpyxl`. That is the
entire dependency list.

**Optional, and each one just makes the report fuller:**

| | Adds |
|---|---|
| Chrome, Edge, Chromium or Brave | A proper vector PDF. Without one you still get the HTML, and camofox can produce a raster PDF. |
| [camofox-browser](https://github.com/yelban/camofox-browser) (Node 18+) | Follower count, profile audit, niche research. |
| [last30days](https://github.com/mvanhorn/last30days-skill) | Reddit, Hacker News, GitHub and web signal. |
| `sentence-transformers` | Slightly better theme clustering. Large download; the built-in method is fine. |

`python driver.py --doctor` tells you exactly which of these you have.

## What it cannot tell you

Watch time, retention curves, traffic sources, follower growth over time and
audience demographics are served by TikTok **only to the account owner**, inside
their own analytics. No tool can get them for an account it does not own, and
any tool claiming otherwise is guessing.

Where common creator advice depends on those numbers, this tests what it *can*
measure and says which is which.

## Please use this well

I built this to help people grow their accounts meaningfully — by understanding
what they have already made, and deciding what to make next.

It reads public data only. It takes nothing TikTok does not show any logged-out
visitor. It automates no engagement of any kind: no following, no liking, no
commenting, no messaging, no posting.

Please do not use it to harass, impersonate, or target anyone, to scrape private
accounts, or to build profiles of private individuals. If you are analysing
someone else's account, do it as competitive research — the way you would read a
competitor's public website — not as surveillance of a person.

## Credits

- **The 30-day calendar method** — the five post types and the five-day
  rotation — is **themarketingfmpodcast**'s. Every file this tool writes carries
  `themarketingfmpodcast - Free Tool, Share it.`
- **The creator growth playbook** the profile audit and content-style checks are
  built on is **@teezytheturtle**'s.
- **[camofox-browser](https://github.com/yelban/camofox-browser)** (MIT, © yelban)
  for stealth browsing.
- **[last30days](https://github.com/mvanhorn/last30days-skill)** (MIT, mvanhorn)
  for cross-platform research.

Neither camofox nor last30days is vendored here — this talks to them if they are
installed, so they stay yours to update.

## Licence

MIT, with one added condition: the attribution line must stay in the output.
See [LICENSE](LICENSE).
