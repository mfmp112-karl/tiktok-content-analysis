"""Optional bridge to the `last30days` skill.

If the user happens to have it installed, it adds the sources camofox cannot
sensibly reach — Reddit threads, Hacker News, GitHub, general web — all of which
work without an API key. If they do not have it, this returns nothing and says
so, and the report is a little thinner. It is never required and never installed
on anyone's behalf.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TIMEOUT = 300

SEARCH_PATHS = [
    Path.home() / ".claude" / "skills" / "last30days",
    Path.home() / ".claude" / "skills" / "last30days-skill" / "skills" / "last30days",
]


def find_skill() -> Path | None:
    override = os.getenv("LAST30DAYS_DIR")
    if override and (Path(override) / "scripts" / "last30days.py").exists():
        return Path(override)
    for base in SEARCH_PATHS:
        if (base / "scripts" / "last30days.py").exists():
            return base
    # Also look beside this repo, since both are often installed as sibling skills.
    here = Path(__file__).resolve().parents[2].parent
    for candidate in here.glob("*/skills/last30days"):
        if (candidate / "scripts" / "last30days.py").exists():
            return candidate
    return None


def available() -> bool:
    return find_skill() is not None


def _python() -> str:
    return os.getenv("LAST30DAYS_PYTHON") or shutil.which("python3") or sys.executable


def run(topics: list[str], *, log=print) -> dict:
    """Ask last30days about these topics. Always returns a coverage entry."""
    skill = find_skill()
    if not skill:
        return {"items": [], "coverage": [{
            "source": "last30days (Reddit, HN, GitHub, web)", "ok": False,
            "note": "skill not installed - these sources were not consulted",
        }]}

    script = skill / "scripts" / "last30days.py"
    out_dir = Path(tempfile.mkdtemp(prefix="tta-l30d-"))
    query = " ".join(topics[:2]) or "content strategy"
    cmd = [_python(), str(script), query, "--emit=compact", f"--save-dir={out_dir}"]

    log(f"  last30days: {query}")
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT,
                              cwd=str(skill))
    except subprocess.TimeoutExpired:
        return {"items": [], "coverage": [{
            "source": "last30days", "ok": False,
            "note": f"timed out after {TIMEOUT}s"}]}
    except OSError as exc:
        return {"items": [], "coverage": [{
            "source": "last30days", "ok": False, "note": str(exc)[:120]}]}

    if proc.returncode != 0:
        tail = (proc.stderr or b"").decode("utf-8", "replace").strip().splitlines()
        return {"items": [], "coverage": [{
            "source": "last30days", "ok": False,
            "note": (tail[-1][:120] if tail else f"exited {proc.returncode}")}]}

    items = []
    for path in sorted(out_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        entries = data.get("items") or data.get("results") or []
        for entry in entries[:20]:
            if isinstance(entry, dict):
                items.append({
                    "source": entry.get("source") or entry.get("platform") or "web",
                    "title": (entry.get("title") or entry.get("text") or "")[:160],
                    "engagement": entry.get("score") or entry.get("engagement"),
                })

    return {"items": items, "coverage": [{
        "source": "last30days (Reddit, HN, GitHub, web)", "ok": bool(items),
        "note": f"{len(items)} items" if items else "ran but returned nothing usable",
    }]}
