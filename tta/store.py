"""Local SQLite store — one file, no server, no signup.

Two rules are inherited from the analyser this replaces, and both were learned
the hard way:

* **Metric refreshes touch metric columns only.** Re-pulling an account must
  never blank the theme assigned by a previous run's clustering.
* **Writes go in chunks.** Row-at-a-time updates hung a job at 1,829 videos.
  Everything here batches through `executemany`.

The schema is intentionally flat. A creator has videos; a run records what was
reachable at the time. That is the whole model.
"""
from __future__ import annotations

import csv
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from . import paths

CHUNK = 400

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    handle      TEXT NOT NULL,
    video_id    TEXT NOT NULL,
    url         TEXT,
    title       TEXT,
    views       INTEGER DEFAULT 0,
    likes       INTEGER DEFAULT 0,
    comments    INTEGER DEFAULT 0,
    shares      INTEGER DEFAULT 0,
    reposts     INTEGER DEFAULT 0,
    duration    INTEGER,
    uploaded    TEXT,
    theme       TEXT,
    theme_id    INTEGER,
    fetched_at  TEXT,
    PRIMARY KEY (handle, video_id)
);
CREATE INDEX IF NOT EXISTS idx_videos_handle   ON videos(handle);
CREATE INDEX IF NOT EXISTS idx_videos_uploaded ON videos(handle, uploaded);

CREATE TABLE IF NOT EXISTS creators (
    handle      TEXT PRIMARY KEY,
    nickname    TEXT,
    followers   INTEGER,
    following   INTEGER,
    hearts      INTEGER,
    bio         TEXT,
    link        TEXT,
    avatar_url  TEXT,
    video_count INTEGER,
    updated_at  TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    handle       TEXT NOT NULL,
    started_at   TEXT,
    finished_at  TEXT,
    accessed_via TEXT,
    harvest_tier TEXT,
    sources      TEXT,
    n_videos     INTEGER,
    report_dir   TEXT
);
"""

#: Columns a metric refresh is allowed to overwrite. `theme` and `theme_id` are
#: absent on purpose — they are analysis output, not harvested data.
METRIC_COLUMNS = ("url", "title", "views", "likes", "comments", "shares",
                  "reposts", "duration", "uploaded", "fetched_at")


#: How long a second run will wait for the first to release the database.
#: A run holds its connection open across minutes of network work, so the
#: sqlite3 default of 5 seconds is nowhere near enough — analysing two accounts
#: at once failed outright with "database is locked", which is a thing people
#: will do constantly.
BUSY_TIMEOUT_S = 60


@contextmanager
def connect(path: Path | None = None):
    path = path or paths.db_path()
    paths.ensure(path.parent)
    conn = sqlite3.connect(path, timeout=BUSY_TIMEOUT_S)
    conn.row_factory = sqlite3.Row
    try:
        # Order matters. busy_timeout goes first so that everything after it
        # *waits* for a competing connection instead of failing immediately —
        # including the WAL switch below, which itself needs a brief exclusive
        # lock and will otherwise blow up when two runs start together.
        conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_S * 1000}")
        try:
            # WAL lets readers carry on while a writer works, which is what
            # makes concurrent runs viable. The setting is persistent, so this
            # only does anything the very first time.
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            pass          # another connection is mid-switch; it will win, fine
        conn.execute("PRAGMA synchronous=NORMAL")

        # Only take a write lock when the schema is genuinely absent. Running
        # executescript on every connect commits and locks for no reason.
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='videos'"
        ).fetchone()
        if not exists:
            conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def norm_handle(raw: str) -> str:
    """Accept anything a user might paste and return the bare handle.

    '@Foo', 'foo', 'https://www.tiktok.com/@foo?lang=en' and a full video
    permalink all become 'foo'. The '@' segment is picked out by name rather
    than by position, because taking the last path segment turns a video URL
    into its numeric id.
    """
    s = (raw or "").strip()
    if "tiktok.com" in s:
        s = s.split("tiktok.com", 1)[1]
    s = s.split("?", 1)[0].split("#", 1)[0]
    for segment in s.strip("/").split("/"):
        if segment.startswith("@"):
            return segment.lstrip("@").strip().lower()
    return s.strip("/").split("/")[0].lstrip("@").strip().lower()


# ------------------------------------------------------------------------- writes

def upsert_videos(conn, handle: str, rows: list[dict]) -> int:
    """Insert or refresh video metrics in chunks, preserving stored analysis."""
    if not rows:
        return 0
    handle = norm_handle(handle)
    now = datetime.now().isoformat(timespec="seconds")
    cols = ("handle", "video_id") + METRIC_COLUMNS
    placeholders = ",".join("?" * len(cols))
    # Every metric column is overwritten; theme/theme_id are never named here,
    # so a re-pull leaves a previous run's clustering intact.
    updates = ",".join(f"{c}=excluded.{c}" for c in METRIC_COLUMNS)
    sql = (f"INSERT INTO videos ({','.join(cols)}) VALUES ({placeholders}) "
           f"ON CONFLICT(handle, video_id) DO UPDATE SET {updates}")

    payload = []
    for r in rows:
        payload.append((
            handle, str(r.get("video_id") or ""), r.get("url"), r.get("title"),
            int(r.get("views") or 0), int(r.get("likes") or 0),
            int(r.get("comments") or 0), int(r.get("shares") or 0),
            int(r.get("reposts") or 0),
            r.get("duration"), r.get("uploaded"), now,
        ))
    written = 0
    for i in range(0, len(payload), CHUNK):
        batch = payload[i:i + CHUNK]
        conn.executemany(sql, batch)
        written += len(batch)
    return written


def set_themes(conn, handle: str, assignments: dict[str, tuple[int, str]]) -> int:
    """Write clustering results back. `assignments` maps video_id -> (id, name)."""
    if not assignments:
        return 0
    handle = norm_handle(handle)
    rows = [(tid, name, handle, vid) for vid, (tid, name) in assignments.items()]
    sql = "UPDATE videos SET theme_id=?, theme=? WHERE handle=? AND video_id=?"
    for i in range(0, len(rows), CHUNK):
        conn.executemany(sql, rows[i:i + CHUNK])
    return len(rows)


def upsert_creator(conn, handle: str, **fields) -> None:
    handle = norm_handle(handle)
    fields = {k: v for k, v in fields.items() if v is not None}
    fields["updated_at"] = datetime.now().isoformat(timespec="seconds")
    cols = ["handle"] + list(fields)
    sql = (f"INSERT INTO creators ({','.join(cols)}) "
           f"VALUES ({','.join('?' * len(cols))}) "
           f"ON CONFLICT(handle) DO UPDATE SET "
           f"{','.join(f'{c}=excluded.{c}' for c in fields)}")
    conn.execute(sql, [handle] + list(fields.values()))


def start_run(conn, handle: str, accessed_via: str) -> int:
    cur = conn.execute(
        "INSERT INTO runs (handle, started_at, accessed_via) VALUES (?,?,?)",
        (norm_handle(handle), datetime.now().isoformat(timespec="seconds"), accessed_via))
    return cur.lastrowid


def finish_run(conn, run_id: int, *, harvest_tier: str, sources: str,
               n_videos: int, report_dir: str) -> None:
    conn.execute(
        "UPDATE runs SET finished_at=?, harvest_tier=?, sources=?, n_videos=?, "
        "report_dir=? WHERE id=?",
        (datetime.now().isoformat(timespec="seconds"), harvest_tier, sources,
         n_videos, report_dir, run_id))


# -------------------------------------------------------------------------- reads

def load_videos(conn, handle: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM videos WHERE handle=? ORDER BY uploaded", (norm_handle(handle),)
    ).fetchall()
    return [dict(r) for r in rows]


def creator(conn, handle: str) -> dict | None:
    row = conn.execute("SELECT * FROM creators WHERE handle=?",
                       (norm_handle(handle),)).fetchone()
    return dict(row) if row else None


def known_video_ids(conn, handle: str) -> set[str]:
    """Drives the incremental re-run: what we already hold for this account."""
    return {r[0] for r in conn.execute(
        "SELECT video_id FROM videos WHERE handle=?", (norm_handle(handle),))}


def counts(conn) -> dict:
    return {
        "accounts": conn.execute("SELECT COUNT(*) FROM creators").fetchone()[0],
        "videos": conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0],
        "runs": conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0],
    }


# ------------------------------------------------------------------------- export

def export_csv(videos: list[dict], path: Path) -> Path:
    """Nothing should be trapped in the database — every run writes this too."""
    fields = ["video_id", "url", "title", "views", "likes", "comments", "shares",
              "reposts", "duration", "uploaded", "theme"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(videos)
    return path
