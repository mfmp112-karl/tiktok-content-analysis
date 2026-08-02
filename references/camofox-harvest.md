# Driving camofox against TikTok

Notes from getting this working. The camofox skill's own documentation is
incomplete in one important way, and TikTok is inconsistent in several.

## The API is bigger than its documentation

camofox's `SKILL.md` and `references/api-reference.md` document seven tab
operations: navigate, click, type, scroll, back/forward/refresh, snapshot,
links and screenshot. Reading `server.js` turns up several more that are not
mentioned anywhere:

| Endpoint | What it does |
|---|---|
| `POST /tabs/:id/evaluate` | **Runs arbitrary JavaScript, returns JSON.** |
| `POST /tabs/:id/extract` | Structured extraction; requires a `schema` in the body. |
| `POST /tabs/:id/viewport` | Sets viewport size. |
| `POST /tabs/:id/wait` | Waits on a condition. |
| `POST /tabs/:id/press` | Key presses. |
| `GET /tabs/:id/images` | Images on the page. |
| `GET /tabs/:id/stats` | Per-tab stats. |
| `POST /act` | Higher-level action endpoint. |

`evaluate` is the one that matters. Everything in this tool that reads TikTok
goes through it. Without it you are regexing numbers out of an accessibility
tree, which is exactly as fragile as it sounds.

Response shape is `{"ok": true, "result": <your value>}`.

## TikTok will not give you the same page twice

**`__UNIVERSAL_DATA_FOR_REHYDRATION__` is frequently absent.** The same profile
URL serves it on one load and omits it the next, with no pattern this project
could find. When it is there it is the best source available — exact follower
counts, the bio, `avatarLarger`, `videoCount`. When it is not, the page is still
perfectly rendered; it just has no hydration payload to read.

So `camofox.PROFILE_JS` tries three sources in order:

1. the hydration JSON,
2. labelled DOM nodes (`[data-e2e="followers-count"]` and friends), which give
   display strings like `9.9M` that need parsing,
3. the visible text, matched against `N Following N Followers N Likes`.

It reports which one answered in `source`. A reader that only knows about (1)
will report "login wall" for pages that loaded fine — this cost an hour.

## Timing

**A TikTok profile needs roughly twelve seconds.** At six, `document.title` is
empty and `document.body.innerText` is the six characters `Log in`. Do not
sleep a constant — poll for the data and stop when it arrives, because the
right delay varies with load.

## The browser restarts underneath you

Requests start failing with:

```json
{"error": "Tab no longer exists (browser was restarted). Create a new tab.",
 "code": "browser_restarted"}
```

Every existing `tabId` is void at that point. The fix is to open a new tab, not
to retry the old one. This happened mid-session during ordinary use, not under
any unusual load.

## Do not retry a 4xx

A concatenated theme phrase is not a hashtag. `#workoutandglutes` returns
**HTTP 410 Gone** and will return it every time. Retrying four times with a
five-second gap turns one wasted request into four.

`open_url` raises `PageUnavailable` immediately on 4xx (except 429) and only
retries 5xx and transport errors, which are the ones that are actually about
warm-up.

For hashtags specifically: try the individual words of a theme label first
(`#workout`, `#glutes`), then the concatenation, then fall back to search.

## Reading video cards

Two details make the difference:

- **Views come from `[data-e2e*="video-views"]`**, not from grepping the nearest
  number out of `innerText`. The naive version returns comment counts,
  durations, and once, memorably, `7`.
- **Captions come from the thumbnail's `alt` attribute.** Grid cards do not
  display the caption anywhere, but the image alt text carries it in full,
  hashtags included.

## Cold start

The first page launch after the server starts routinely exceeds the server's own
timeout and comes back as HTTP 500. Retry. Subsequent loads are fast.

## Windows

`scripts/camofox.sh` is POSIX bash and hardcodes `/tmp` paths, so it needs Git
Bash or WSL. Starting the server directly avoids the wrapper entirely:

```bash
node ~/.camofox-browser/node_modules/@askjo/camofox-browser/server.js
```
