"""Where this tool keeps things on your machine.

Everything lives under one directory in your home folder, not next to whatever
you happened to `cd` into. That is deliberate: the skill gets invoked from
wherever the user is working, and runs should accumulate in one place so the
second analysis of an account is incremental rather than a cold start.

Nothing is written outside this directory, and deleting it removes every trace
of the tool's data.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

#: Override for tests, or for anyone who wants the data somewhere else.
ENV_HOME = "TTA_HOME"


def home() -> Path:
    override = os.getenv(ENV_HOME)
    return Path(override).expanduser() if override else Path.home() / ".tiktok-content-analysis"


def db_path() -> Path:
    return home() / "tta.sqlite3"


def reports_root() -> Path:
    return home() / "reports"


def run_dir(handle: str, when: datetime | None = None) -> Path:
    """reports/<handle>/<YYYY-MM-DD_HHMM>/ — timestamped, so re-running an
    account today does not overwrite this morning's report."""
    when = when or datetime.now()
    return reports_root() / handle.lstrip("@").lower() / when.strftime("%Y-%m-%d_%H%M")


def ensure(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def describe() -> str:
    """One line for the doctor output."""
    h = home()
    state = "exists" if h.exists() else "will be created on first run"
    return f"{h}  ({state})"
