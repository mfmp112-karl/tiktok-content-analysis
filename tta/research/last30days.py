"""Bridge to the `last30days` skill — what people are saying off TikTok.

camofox tells you what is being *posted* in a niche. This tells you what is
being *asked and argued about* in it: Reddit threads, Hacker News, the wider
web. Those are where the questions live, and a question someone actually typed
out is the best content prompt there is.

Optional. If the skill is not installed this returns nothing and says so.

Getting the invocation right matters more than it looks. The first version of
this called `--emit=compact --save-dir=...` and then globbed the save directory
for JSON, which silently produced nothing on every single run while still
exiting zero — so the report kept saying "ran but returned nothing usable" and
that read like the skill's fault. The correct form is `--emit json --output
FILE`, which writes a documented schema: `clusters` (grouped topics with
summaries), `results` (individual posts with engagement), and `source_status`
(per-source ok / no-results).

`--register creator` is used because the skill ships an audience preset for
exactly this use case.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TIMEOUT = 420

def _candidates() -> list[Path]:
    home = Path.home()
    here = Path(__file__).resolve().parents[2]
    out = [
        home / ".claude" / "skills" / "last30days",
        home / ".claude" / "skills" / "last30days-skill" / "skills" / "last30days",
    ]
    # Sibling installs, and the copy some projects vendor next to their own work.
    out += sorted(here.parent.glob("*/skills/last30days"))
    out += sorted(here.parent.glob("*/.claude/skills/last30days"))
    out += sorted(here.parent.glob("last30days"))
    return out


def _version_of(base: Path) -> tuple:
    """Parse `version:` out of the skill's frontmatter, for ordering."""
    skill_md = base / "SKILL.md"
    if not skill_md.exists():
        return (0,)
    try:
        for line in skill_md.read_text(encoding="utf-8", errors="replace").splitlines()[:40]:
            if line.lower().startswith("version:"):
                raw = line.split(":", 1)[1].strip().strip('"\'')
                return tuple(int(p) for p in raw.split(".") if p.isdigit())
    except OSError:
        pass
    return (0,)


def find_skill() -> Path | None:
    """Pick the most capable installed copy.

    More than one is common — a global one and a project-local one — and they
    drift apart by many minor versions. Older builds lack `--register` and
    `--output`, so taking whichever appears first in the path list silently
    gets you the weaker one. Newest version wins.
    """
    override = os.getenv("LAST30DAYS_DIR")
    if override and (Path(override) / "scripts" / "last30days.py").exists():
        return Path(override)

    found = {}
    for base in _candidates():
        if (base / "scripts" / "last30days.py").exists():
            found[base.resolve()] = _version_of(base)
    if not found:
        return None
    return max(found.items(), key=lambda kv: kv[1])[0]


def available() -> bool:
    return find_skill() is not None


def _python() -> str:
    return os.getenv("LAST30DAYS_PYTHON") or shutil.which("python3") or sys.executable


def run(topics: list[str], *, quick: bool = True, log=print) -> dict:
    """Research these topics. Always returns items, clusters and coverage."""
    skill = find_skill()
    if not skill:
        return {"items": [], "clusters": [], "coverage": [{
            "source": "last30days (Reddit, Hacker News, web)", "ok": False,
            "note": "skill not installed - these sources were not consulted",
        }]}

    # One topic, not a concatenation. Joining two mechanical theme labels
    # produced queries like "workout and glutes cardio and work", which reads
    # as noise to a search backend and came back as eight software launches.
    query = (topics[0] if topics else "").strip() or "content strategy"
    out_file = Path(tempfile.mkdtemp(prefix="tta-l30d-")) / "out.json"
    cmd = [_python(), str(skill / "scripts" / "last30days.py"), query,
           "--emit", "json", "--register", "creator", "--output", str(out_file)]
    if quick:
        cmd.append("--quick")

    log(f"  last30days: {query}")
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT,
                              cwd=str(skill))
    except subprocess.TimeoutExpired:
        return _failed(f"timed out after {TIMEOUT}s")
    except OSError as exc:
        return _failed(str(exc)[:120])

    # Older builds do not honour --output but still print the JSON, so fall
    # back to stdout rather than reporting a failure that did not happen.
    raw = ""
    if out_file.exists():
        raw = out_file.read_text(encoding="utf-8", errors="replace")
    if not raw.strip():
        raw = (proc.stdout or b"").decode("utf-8", "replace")
        start = raw.find("{")
        raw = raw[start:] if start >= 0 else ""

    if not raw.strip():
        tail = (proc.stderr or b"").decode("utf-8", "replace").strip().splitlines()
        return _failed(tail[-1][:120] if tail else f"exited {proc.returncode}")

    try:
        data = json.loads(raw)
    except Exception as exc:
        return _failed(f"unreadable output: {exc}"[:120])

    items = []
    for r in (data.get("results") or [])[:30]:
        if not isinstance(r, dict):
            continue
        items.append({
            "source": r.get("source") or "web",
            "title": (r.get("title") or "")[:180],
            "summary": (r.get("summary") or "")[:300],
            "url": r.get("url") or "",
            "engagement": r.get("engagement"),
            "cluster": r.get("cluster"),
            "published_at": r.get("published_at"),
        })

    clusters = []
    for c in (data.get("clusters") or [])[:8]:
        if not isinstance(c, dict):
            continue
        clusters.append({
            "title": (c.get("title") or "").strip(),
            "summary": (c.get("summary") or "").strip(),
            "engagement": c.get("engagement_total"),
            "sources": c.get("sources") or [],
        })

    # The skill reports per-source status, so say which actually answered
    # rather than collapsing everything into one line.
    status = data.get("source_status") or {}
    ok_sources = [k for k, v in status.items() if str(v).lower() == "ok"]
    coverage = [{
        "source": "last30days (" + ", ".join(sorted(status)) + ")"
                  if status else "last30days",
        "ok": bool(items),
        "note": (f"{len(items)} posts, {len(clusters)} topic clusters"
                 + (f"; answered: {', '.join(ok_sources)}" if ok_sources else "")
                 if items else "ran but found nothing in the last 30 days"),
    }]
    log(f"    {len(items)} posts across {len(clusters)} clusters"
        + (f" (from {', '.join(ok_sources)})" if ok_sources else ""))
    return {"items": items, "clusters": clusters, "coverage": coverage,
            "window_days": data.get("window_days"), "query": query}


def _failed(note: str) -> dict:
    return {"items": [], "clusters": [], "coverage": [{
        "source": "last30days (Reddit, Hacker News, web)", "ok": False,
        "note": note}]}
