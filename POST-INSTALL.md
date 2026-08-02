# You have just installed this. Here is what is left.

Run this first — it checks every item below and tells you exactly what to do:

```bash
python driver.py --doctor
```

## Required

- [ ] **Python 3.10 or newer.** Check with `python --version`.
- [ ] **Two packages.** `pip install yt-dlp openpyxl` — that is the whole list.
- [ ] **Permission to create a folder.** This tool writes to
      `~/.tiktok-content-analysis/` and nowhere else: one SQLite file for the
      accounts you analyse, and one folder per report. Deleting that directory
      removes every trace of it. Nothing is written next to your other work,
      and nothing is uploaded anywhere.

## Optional — each one makes the report fuller, none of them are required

- [ ] **Chrome, Edge, Chromium or Brave** for a proper vector PDF. Edge ships
      with Windows and Chrome is nearly everywhere, so you probably have one
      already. Without any of them you still get the full HTML report, and
      camofox can produce a raster PDF.

- [ ] **The camofox-browser skill** (needs Node 18+). This is what reads
      follower counts, the bio and avatar for the profile audit, and TikTok's
      hashtag and search pages for the niche research. Start it with:

      ```bash
      node ~/.camofox-browser/node_modules/@askjo/camofox-browser/server.js
      ```

      On Windows the skill's own `camofox.sh` wrapper needs Git Bash or WSL —
      it will not run in PowerShell or cmd.

- [ ] **The last30days skill** for Reddit, Hacker News, GitHub and web signal.
      Those sources need no API key.

- [ ] **Allow Claude to use your own Chrome** — only relevant if TikTok blocks
      both the public path and camofox. The tool will stop and ask before ever
      touching your logged-in session, and it only ever reads.

- [ ] **`sentence-transformers`** for marginally better theme clustering. It is
      a large download and the built-in pure-Python method works well. Skip it
      unless you are analysing very large accounts.

## Then

```bash
python driver.py @someone
```

A first run on a small account takes about 40 seconds without research, or
around three minutes with it. Large accounts take longer — the tool tells you
what it is doing at each step rather than leaving you watching a spinner.

---

themarketingfmpodcast - Free Tool, Share it.
