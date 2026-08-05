# Surfaces

Four external systems sit behind this tool, and none of them announce
themselves when they break. Read this before diagnosing a run that came back
thin — a report missing half its content looks the same whether TikTok
changed something or a local service just isn't running.

**Run `python driver.py --selftest`** to read all four back at once, against
a small known-stable account, and print a plain pass/fail row for each. It is
cheap on purpose (one enumeration attempt, a small cap, one research pass) so
it can run on a schedule without risking the rate limiting a full harvest can
trigger.

| Surface | The readback | Healthy looks like | Broken looks like |
|---|---|---|---|
| TikTok's public catalogue, via `yt-dlp` | `ytdlp.pull(conn, handle, cap=20, attempts=1)` | A positive video count comes back | Raises `ytdlp.HarvestBlocked` — one message covering three different causes: the account is private, renamed, or TikTok is blocking this machine |
| TikTok's DOM, via camofox | `camofox.profile(handle)` | A dict with a follower count | `None`, or a dict with no follower count — camofox answered but the page it scraped didn't have what was expected, usually because a selector moved |
| camofox's own HTTP API | `camofox.healthy()` | `True` | `False` — indistinguishable from "camofox is simply not running" from the outside; this is the one case `--doctor` already checks too |
| `last30days` | `last30days.run([handle], quick=True)` | A `coverage` list with at least one row | An empty `coverage` list, or the skill reporting `available() == False` |

**Reading `--selftest`'s output:** a row marked `--` means that surface was
never reached this run — camofox not running, or the skill not installed —
which is a configuration state, not a failure, and does not affect the exit
code. A row marked `FAIL` means the surface was reached and answered wrong,
which is the thing worth investigating. The command exits non-zero only when
at least one row fails.

**What this file is not.** It does not attempt every failure mode of every
surface — TikTok in particular can break in ways nobody has seen yet. It is
the four commands worth running first when a report looks thin, so the next
person debugging a strange run does not have to rediscover them by reading
four different modules.
