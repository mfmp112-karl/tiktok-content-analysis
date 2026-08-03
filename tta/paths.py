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
#: TTA_HOME is the old name and still works — it predates the tool being called
#: Raven, and silently ignoring it would strand anyone who had scripted it.
ENV_HOME = "RAVEN_HOME"
ENV_HOME_LEGACY = "TTA_HOME"

DIR_NAME = ".raven"
DIR_NAME_LEGACY = ".tiktok-content-analysis"


def home() -> Path:
    """Where the data lives.

    The directory was called `.tiktok-content-analysis` before the tool was
    named. New installs get `.raven`, but an existing directory keeps being
    used rather than being abandoned with someone's analysis history inside
    it — a rename that silently orphans data is not a rename, it is a loss.
    """
    for var in (ENV_HOME, ENV_HOME_LEGACY):
        override = os.getenv(var)
        if override:
            return Path(override).expanduser()

    new = Path.home() / DIR_NAME
    legacy = Path.home() / DIR_NAME_LEGACY
    if not new.exists() and legacy.exists():
        return legacy
    return new


def using_legacy_home() -> bool:
    return home().name == DIR_NAME_LEGACY


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
