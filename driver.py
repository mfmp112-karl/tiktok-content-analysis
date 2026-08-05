#!/usr/bin/env python3
"""Raven — one command, from a TikTok handle to a report she wrote.

    python driver.py @handle              # everything
    python driver.py                      # asks for the handle
    python driver.py --doctor             # what is installed, what is missing

Steps, in order:

  1. harvest   public catalogue via yt-dlp, falling back to the stealth browser
  2. profile   follower count, bio and avatar via camofox (optional)
  3. analyse   themes, hooks, timing, cadence — every finding significance-tested
  4. research  what the niche is posting, via camofox (optional)
  5. calendar  30 days on the five-day rotation, built from the analysis
  6. report    a print-ready PDF, an HTML twin, the workbook, JSON and CSV

Nothing here needs an API key, an account, or a paid service. Optional pieces
degrade with a warning rather than failing the run, and the report always states
which of them were actually reachable.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import webbrowser
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tta import (__version__, attribution, console, paths, setup,   # noqa: E402
                 store, voice)
from tta.analyse import (aggregates as ag, cadence, hooks, profile_audit,  # noqa: E402
                         themes)
from tta.calendar import build as calbuild, recommend, workbook                     # noqa: E402
from tta.harvest import camofox, session, ytdlp                                   # noqa: E402
from tta.report import html as rhtml, pdf                                # noqa: E402
from tta.research import last30days, tiktok_demand                       # noqa: E402


def banner(text: str) -> None:
    print(f"\n{text}\n{'-' * len(text)}", flush=True)


# ------------------------------------------------------------------------ doctor

def doctor() -> int:
    """What is here, what is missing, and the one line that fixes each."""
    print(f"\n{voice.mark()}   v{__version__}")
    print("=" * 62)

    rows: list[tuple[str, bool, bool, str, str]] = []   # label, ok, required, detail, fix

    ok_py = sys.version_info >= (3, 10)
    rows.append(("Python 3.10+", ok_py, True,
                 f"{sys.version_info.major}.{sys.version_info.minor}."
                 f"{sys.version_info.micro}",
                 "Install Python 3.10 or newer from python.org"))

    for mod, pkg in (("yt_dlp", "yt-dlp"), ("openpyxl", "openpyxl")):
        try:
            __import__(mod)
            rows.append((pkg, True, True, "installed", ""))
        except ImportError:
            rows.append((pkg, False, True, "missing", "pip install yt-dlp openpyxl"))

    browser = pdf.find_browser()
    rows.append(("Chrome / Edge (for the PDF)", bool(browser), False,
                 Path(browser).name if browser else "not found",
                 "Without one you still get the HTML report, and camofox can "
                 "produce a raster PDF."))

    home = paths.home()
    try:
        paths.ensure(home)
        writable = True
    except OSError:
        writable = False
    rows.append(("Folder for your data", writable, True,
                 paths.describe() + ("  (pre-rename folder, still in use)"
                                     if paths.using_legacy_home() else ""),
                 "This tool needs permission to create that folder. Everything "
                 "it stores lives there and nowhere else."))

    healthy = camofox.healthy()
    rows.append(("camofox stealth browser", healthy, False,
                 "running" if healthy else "not running",
                 "Optional. Needed for follower counts, the profile audit and "
                 "niche research. Install the camofox-browser skill (Node 18+), "
                 "then start it with: camofox start"))

    sess = session.status()
    rows.append(("Signed-in TikTok session", sess["usable"], False,
                 sess["note"],
                 "Optional. Only needed for accounts that have audience "
                 "controls switched on. Run with --help-session for how to "
                 "set one up."))

    rows.append(("last30days skill", last30days.available(), False,
                 "installed" if last30days.available() else "not installed",
                 "Optional. Adds Reddit, Hacker News, GitHub and web signal. "
                 "No API key needed for those sources."))

    try:
        import sentence_transformers  # noqa: F401
        st_ok = True
    except Exception:
        st_ok = False
    rows.append(("sentence-transformers", st_ok, False,
                 "installed" if st_ok else "not installed",
                 "Optional, and a large download. Without it themes are found "
                 "with a pure-Python method that works fine."))

    print()
    blocking = 0
    for label, ok, required, detail, fix in rows:
        mark = "  OK  " if ok else ("MISSING" if required else "  --  ")
        print(f"[{mark}] {label:<32} {detail}")
        if not ok and fix:
            print(f"          -> {fix}")
        if not ok and required:
            blocking += 1

    try:
        with store.connect() as conn:
            counts = store.counts(conn)
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        print(f"\nStored so far: {counts['videos']:,} videos across "
              f"{counts['accounts']} account(s), {counts['runs']} run(s).")
        if str(mode).lower() != "wal":
            # Worth surfacing: in rollback mode two runs at once collide with
            # "database is locked", and the switch to WAL can only happen when
            # nothing else has the file open.
            print(f"Note: the database is in '{mode}' mode rather than WAL. "
                  f"Run this again with no other analysis in progress and it "
                  f"will convert, which lets two runs share the file.")
    except Exception as exc:
        print(f"\nCould not open the local database: {exc}")

    print()
    if blocking:
        print(f"{blocking} required item(s) missing — fix those and run again.")
    else:
        print("Ready. Try:  python driver.py @somehandle")
    print(f"\n{attribution.TAG}\n")
    return 1 if blocking else 0


# ------------------------------------------------------------------------- steps

def harvest(conn, handle: str, args) -> dict:
    banner(f"1/6  {voice.step('harvest')}")
    stored = (store.creator(conn, handle) or {}).get("sec_uid")
    try:
        summary = ytdlp.pull(conn, handle, cap=args.cap, attempts=args.attempts,
                             since=args.since, cookies=args.cookies,
                             sec_uid=stored)
        print(voice.found(summary["stored"], summary["new"]))
        return summary
    except ytdlp.HarvestBlocked as exc:
        print(f"  {exc}")

    if camofox.healthy():
        session.import_into_camofox(args.cookies, log=lambda m: print(m))

    # Before falling back to scrolling — slower, and it returns less — try the
    # one thing yt-dlp's own error message asks for. It cannot always work out
    # an account's secondary id from the handle, but that id is sitting in the
    # page and the browser can simply read it. Fetch it once, keep it, and let
    # yt-dlp do the fast bulk pull after all.
    if not stored and camofox.healthy():
        print("  asking the browser for this account's internal id...")
        found = camofox.sec_uid(handle, log=lambda m: print(m))
        if found:
            store.upsert_creator(conn, handle, sec_uid=found)
            conn.commit()
            try:
                summary = ytdlp.pull(conn, handle, cap=args.cap,
                                     attempts=args.attempts, since=args.since,
                                     cookies=args.cookies, sec_uid=found)
                print(voice.found(summary["stored"], summary["new"]))
                return summary
            except ytdlp.HarvestBlocked as exc:
                print(f"  that did not work either: {exc}")

    print("  falling back to the stealth browser...")
    if not camofox.healthy():
        print("  camofox is not running either.")
        from tta.harvest import chrome_handoff
        print("\n" + chrome_handoff.permission_request(handle))
        raise SystemExit(2)

    # Check the profile before scrolling. If TikTok is holding the page behind
    # a login there is nothing to scroll, and "could not read any videos" sends
    # the user looking for a problem with the account rather than with their
    # access to it.
    probe = camofox.profile(handle)
    if isinstance(probe, dict) and probe.get("walled"):
        from tta.harvest import chrome_handoff
        print("\n" + voice.blocked(handle))
        print(f"  Follower counts read as '-' and the grid is empty for anyone "
              f"signed out, so neither the public path nor the stealth browser "
              f"can see it.")
        print("\n" + chrome_handoff.permission_request(handle))
        raise SystemExit(3)

    cards = camofox.scroll_harvest(f"https://www.tiktok.com/@{handle}",
                                   max_scrolls=args.scrolls)
    rows = [{"video_id": c["video_id"], "url": c["url"], "title": c["text"],
             "views": c["views"] or 0} for c in cards if c["creator"].lower() == handle]
    if not rows:
        raise SystemExit(
            f"Could not read any videos for @{handle}. The account may be "
            f"private, renamed, or have no public posts.")
    store.upsert_videos(conn, handle, rows)
    conn.commit()
    return {"tier": "camofox scroll", "stored": len(rows), "new": len(rows),
            "already_had": 0}


def read_profile(conn, handle: str, enabled: bool) -> dict | None:
    banner(f"2/6  {voice.step('profile')}")
    if not enabled:
        print("  skipped (--no-profile)")
        return None
    if not camofox.healthy():
        print("  camofox not running — follower count and profile audit "
              "will be missing from the report")
        return None
    data = camofox.profile(handle)
    if not data:
        return None
    print(f"  @{handle}: {data.get('followers')} followers, "
          f"{data.get('videos') or '?'} videos (via {data.get('source')})")
    store.upsert_creator(
        conn, handle, followers=data.get("followers"),
        following=data.get("following"), hearts=data.get("hearts"),
        bio=data.get("bio"), link=data.get("link"),
        avatar_url=data.get("avatar"), nickname=data.get("nickname"))
    conn.commit()
    return data


def analyse(videos: list[dict], conn, handle: str, args) -> tuple[dict, dict]:
    banner(f"3/6  {voice.step('analyse')}")
    if voice.is_plain():
        print(f"  {len(videos)} videos")
    if not args.no_cluster:
        info = themes.cluster(videos, log=lambda m: print(m) if voice.is_plain()
                              else None)
        store.set_themes(conn, handle, info["assignments"])
        conn.commit()
        videos = store.load_videos(conn, handle)
        print(voice.themes_found(info.get("k") or 0, info.get("effective_themes")))
    else:
        info = {"method": "reused stored themes", "k": None, "silhouette": None,
                "concentration": None, "effective_themes": None, "fallback": False}
    return ag.build(videos), info


def research(shortlisted: list[dict], args, own_tags: list[str]) -> dict:
    banner(f"4/6  {voice.step('research')}")
    if args.no_research:
        print("  skipped (--no-research)")
        return {"topics": [], "peers": [], "coverage": [
            {"source": "Niche research", "ok": False, "note": "skipped for this run"}],
            "gaps": [], "audience_words": []}

    topics = [themes.readable(t["name"]) for t in shortlisted[:args.topics]]
    print(f"  topics: {', '.join(topics) or 'none'}")

    # Research is optional by definition, so nothing inside it is allowed to
    # end the run. The report is complete without it; it is not complete
    # without the analysis that has already been paid for by this point.
    empty = {"topics": [], "peers": [], "audience_words": [], "coverage": [],
             "gaps": []}
    try:
        out = tiktok_demand.run(topics, scrolls=args.scrolls,
                                exclude=own_tags, log=lambda m: print(m))
    except Exception as exc:
        print(f"  research failed ({type(exc).__name__}: {exc}) — continuing")
        out = {**empty, "coverage": [{"source": "TikTok (via camofox)", "ok": False,
                                      "note": f"{type(exc).__name__}: {exc}"[:120]}]}
    try:
        extra = last30days.run(topics, log=lambda m: print(m))
    except Exception as exc:
        extra = {"items": [], "coverage": [{"source": "last30days", "ok": False,
                                            "note": str(exc)[:120]}]}
    out["coverage"].extend(extra["coverage"])
    out["last30days"] = extra["items"]
    out["l30_clusters"] = extra.get("clusters") or []
    for row in out["coverage"]:
        print(f"  {'reached' if row['ok'] else 'not reached'}: {row['source']}"
              f" — {row['note']}")
    return out


# -------------------------------------------------------------------------- main

def run(args) -> int:
    attribution.verify()
    handle = store.norm_handle(args.handle)
    started = time.time()
    out_dir = paths.ensure(paths.run_dir(handle))

    print()
    print(voice.greeting(handle))
    print(f"Output: {out_dir}")

    with store.connect() as conn:
        accessed_via = "logged-out / anonymous session"
        run_id = store.start_run(conn, handle, accessed_via)

        summary = harvest(conn, handle, args)
        prof = read_profile(conn, handle, not args.no_profile)
        videos = store.load_videos(conn, handle)
        if not videos:
            raise SystemExit(f"No videos stored for @{handle}.")

        analysis, theme_info = analyse(videos, conn, handle, args)
        videos = store.load_videos(conn, handle)
        hook_info = hooks.build(videos)
        cad = cadence.build(videos, analysis["weekday"], analysis["hour"])

        every = [r for dim in ("theme", "weekday", "duration", "caption_length",
                              "format", "hashtag_use")
                 for r in analysis[dim]] + hook_info["features"]
        print(voice.verdicts(
            sum(1 for r in every if r.get("verdict") == "strong"),
            sum(1 for r in every if r.get("verdict") == "moderate"),
            len(every)))

        shortlisted = themes.shortlist(analysis["theme"])
        # Every tag ever used, not just the frequently-used ones: a tag the
        # account has posted even once is not a gap in its coverage.
        own_tags = sorted(ag.all_hashtags(videos))
        demand = research(shortlisted, args, own_tags)
        calls = themes.calls(analysis["theme"], gaps=demand.get("gaps"))

        recs = recommend.build(
            analysis=analysis, theme_calls=calls, shortlist=shortlisted,
            hook_info=hook_info, cadence_info=cad, research=demand,
            profile_audit=profile_audit.audit(prof, video_count=len(videos))
            if prof else None)
        print(f"  {len(recs)} recommendations")

        banner(f"5/6  {voice.step('calendar')}")
        cal = calbuild.build(shortlist=shortlisted, theme_calls=calls,
                             winning_hooks=hook_info["winning_hooks"],
                             best_slot=cad["best_slot"], gaps=demand.get("gaps"),
                             start=date.today() + timedelta_days(1))
        xlsx = workbook.write(cal, handle=handle,
                              winning_hooks=hook_info["winning_hooks"],
                              repetition=hook_info["repetition"],
                              out_path=out_dir / "calendar.xlsx")
        print(f"  {len(cal['days'])} days across {len(cal['themes_used'])} themes "
              f"-> {xlsx.name}")

        banner(f"6/6  {voice.step('report')}")
        creator = store.creator(conn, handle)
        audit = profile_audit.audit(prof, video_count=len(videos))
        ctx = {
            "meta": {
                "handle": handle,
                "accessed_via": accessed_via,
                "harvest_tier": summary.get("tier", "yt-dlp"),
                "generated": rhtml.now_stamp(),
                "version": __version__,
            },
            "creator": creator,
            "analysis": analysis,
            "themes": theme_info,
            "hooks": hook_info,
            "cadence": cad,
            "theme_calls": calls,
            "profile_audit": audit,
            "peers": demand.get("peers"),
            "research": demand,
            "recommendations": recs,
            "calendar": cal,
            "limits": rhtml.default_limits(),
            "narrative": load_narrative(args.narrative),
        }
        result = pdf.write(rhtml.render(ctx), out_dir, log=lambda m: print(m))

        store.export_csv(videos, out_dir / "videos.csv")
        (out_dir / "analysis.json").write_text(
            json.dumps(json_safe({**ctx, **attribution.stamp_json()}),
                       indent=2, ensure_ascii=False), encoding="utf-8")
        store.finish_run(conn, run_id, harvest_tier=summary.get("tier", "yt-dlp"),
                         sources=", ".join(c["source"] for c in demand["coverage"]
                                           if c["ok"]),
                         n_videos=len(videos), report_dir=str(out_dir))

    print()
    print(voice.finished(time.time() - started, str(out_dir)))
    print(f"  report   {result['html'].name}"
          + (f" + {result['pdf'].name} ({result['route']})" if result["pdf"] else ""))
    print(f"  calendar {xlsx.name}")
    print(f"  data     videos.csv, analysis.json")
    print(f"\n  {out_dir}")
    print(f"\n{attribution.TAG}\n")

    if not args.no_open:
        target = result["pdf"] or result["html"]
        try:
            webbrowser.open(target.resolve().as_uri())
        except Exception:
            pass
    return 0


def timedelta_days(n: int):
    from datetime import timedelta
    return timedelta(days=n)


def load_narrative(path: str | None) -> dict:
    """Optional prose written by an agent from the computed aggregates.

    If the user passed ``--narrative`` and the file is missing or invalid JSON,
    raise SystemExit so the failure is not silent.
    """
    if not path:
        return {}
    p = Path(path)
    if not p.is_file():
        raise SystemExit(f"--narrative file not found: {path}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--narrative file is not valid JSON ({path}): {exc}") from exc
    except OSError as exc:
        raise SystemExit(f"--narrative file unreadable ({path}): {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"--narrative must be a JSON object, got {type(data).__name__}")
    return data


def json_safe(obj):
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()
                if k not in ("avatar_data_uri",)}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    return obj


def parse_date(text: str) -> date:
    return datetime.strptime(text, "%Y-%m-%d").date()


def main(argv: list[str]) -> int:
    console.setup()
    ap = argparse.ArgumentParser(
        prog="driver.py",
        description="Analyse a public TikTok account and build a 30-day content calendar.")
    ap.add_argument("handle", nargs="?", help="e.g. @someone, or a profile URL")
    ap.add_argument("--setup", action="store_true",
                    help="guided setup: installs what it can, tells you the rest")
    ap.add_argument("--yes", action="store_true",
                    help="with --setup, allow installing packages without asking")
    ap.add_argument("--with-session", action="store_true",
                    help="with --setup, also walk through the signed-in session")
    ap.add_argument("--help-session", action="store_true",
                    help="explain how to set up a signed-in session")
    ap.add_argument("--doctor", action="store_true",
                    help="check what is installed and what is missing")
    ap.add_argument("--cap", type=int, default=ytdlp.DEFAULT_CAP,
                    help="most videos to enumerate (default %(default)s)")
    ap.add_argument("--attempts", type=int, default=ytdlp.DEFAULT_ATTEMPTS,
                    help="enumeration retries; TikTok's pagination depth varies")
    ap.add_argument("--since", type=parse_date, metavar="YYYY-MM-DD",
                    help="ignore posts older than this")
    ap.add_argument("--scrolls", type=int, default=8,
                    help="how deep to scroll research pages (default %(default)s)")
    ap.add_argument("--topics", type=int, default=3,
                    help="how many themes to research (default %(default)s)")
    ap.add_argument("--no-cluster", action="store_true",
                    help="reuse themes already stored instead of re-clustering")
    ap.add_argument("--no-research", action="store_true",
                    help="skip the niche research step entirely")
    ap.add_argument("--no-profile", action="store_true",
                    help="skip the camofox profile read")
    ap.add_argument("--cookies", metavar="FILE",
                    help="Netscape cookies.txt for a signed-in TikTok session; "
                         "needed for accounts with audience controls on")
    ap.add_argument("--plain", action="store_true",
                    help="drop the voice; terse, parseable output")
    ap.add_argument("--no-open", action="store_true",
                    help="do not open the report when finished")
    ap.add_argument("--narrative", metavar="FILE",
                    help="JSON of written commentary to fold into the report")
    args = ap.parse_args(argv[1:])
    if args.plain:
        voice.set_plain(True)

    if args.setup:
        return setup.run(assume_yes=args.yes, want_session=args.with_session)

    if args.help_session:
        print()
        print(session.HOW_TO)
        print()
        return 0

    if args.doctor:
        return doctor()

    if not args.handle:
        try:
            args.handle = input("TikTok handle to analyse (e.g. @someone): ").strip()
        except (EOFError, KeyboardInterrupt):
            return 1
        if not args.handle:
            ap.print_help()
            return 1

    try:
        return run(args)
    except KeyboardInterrupt:
        print("\nStopped. Whatever was already fetched is saved.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
