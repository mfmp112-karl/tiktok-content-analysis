#!/usr/bin/env python3
"""Make the record agree with the live renderer. Run from the repo root.

Three checks, all mechanical, all against `tta.report.html.SECTIONS` — the
list `render()` itself builds the document from (see html.py). The docs
don't get a second, hand-maintained list to drift from the real one; they
get checked against the same structure the renderer uses.

1. README.md's and SKILL.md's "what is in the report" tables list exactly
   the sections SECTIONS lists, in the same order — no more, no fewer.
2. Every key in `voice._REPORT` is read by at least one `voice.report(...)`
   call somewhere in `tta/` — an unread key is dead prose nobody will notice
   going stale (this is exactly how `frameworks.sub` went unnoticed).
3. `SKILL.md`'s three example commands under "Useful variations" all parse
   as real driver.py flags — a stale flag combination fails loudly here
   instead of silently misleading whoever tries it next.

Exit non-zero on any drift. Prints the same pass/fail row style as
`driver.py --doctor` / `--selftest`, on purpose — one house style for "is
this actually true" checks across the project.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tta.report import html as rhtml   # noqa: E402
from tta import voice                  # noqa: E402


def _table_titles(md_path: Path, heading: str) -> list[str] | None:
    """Pull the first column out of the markdown table under `heading`.

    Returns None if the heading isn't found at all, so a caller can tell
    "no table" apart from "empty table" — different failures.
    """
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == heading)
    except StopIteration:
        return None

    titles = []
    in_table = False
    for ln in lines[start + 1:]:
        if ln.startswith("##"):          # next heading — table's over
            break
        if not ln.startswith("|"):
            if in_table:
                break
            continue
        in_table = True
        if set(ln.replace("|", "").strip()) <= {"-", " ", ":"}:
            continue                      # the |---|---| separator row
        cell = ln.split("|")[1].strip()
        if cell.lower() == "section":
            continue                      # header row
        cell = re.sub(r"^\*+|\*+$", "", cell)       # **bold** / *italic* wrapper
        titles.append(cell)
    return titles


def _read_report_keys() -> set[str]:
    """Every string literal passed to voice.report(...) anywhere in tta/."""
    pattern = re.compile(r'voice\.report\(\s*["\']([\w.]+)["\']')
    found: set[str] = set()
    for py in ROOT.joinpath("tta").rglob("*.py"):
        found |= set(pattern.findall(py.read_text(encoding="utf-8")))
    return found


def _flag_names() -> set[str]:
    """Every --flag driver.py's parser actually defines, read from its own
    argparse calls rather than hand-copied, so this can't itself go stale."""
    src = ROOT.joinpath("driver.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    flags = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument" and node.args):
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                if first.value.startswith("--"):
                    flags.add(first.value)
    return flags


def _example_commands(md_path: Path) -> list[str]:
    text = md_path.read_text(encoding="utf-8")
    m = re.search(r"Useful variations:\s*```bash\n(.*?)```", text, re.S)
    return [ln.strip() for ln in m.group(1).splitlines() if ln.strip()] if m else []


def main() -> int:
    rows: list[tuple[str, bool, str]] = []   # label, ok, detail
    section_titles = [s["title"] for s in rhtml.SECTIONS]

    for label, path, heading in (
        ("README.md section table", ROOT / "README.md", "### What is in the report"),
        ("SKILL.md section table", ROOT / "SKILL.md", "## What the report contains"),
    ):
        titles = _table_titles(path, heading)
        if titles is None:
            rows.append((label, False, f'heading "{heading}" not found'))
        elif titles == section_titles:
            rows.append((label, True, f"{len(titles)} sections, matches render()"))
        else:
            missing = [t for t in section_titles if t not in titles]
            extra = [t for t in titles if t not in section_titles]
            detail = f"{len(titles)} rows vs {len(section_titles)} in render()"
            if missing:
                detail += f"; missing: {missing}"
            if extra:
                detail += f"; not in render(): {extra}"
            rows.append((label, False, detail))

    read_keys = _read_report_keys()
    defined_keys = set(voice._REPORT.keys())
    orphaned = sorted(defined_keys - read_keys)
    rows.append(("voice._REPORT keys all read", not orphaned,
                 "every key has a voice.report(...) call site" if not orphaned
                 else f"orphaned: {orphaned}"))

    flags = _flag_names()
    bad_examples = []
    for cmd in _example_commands(ROOT / "SKILL.md"):
        used = set(re.findall(r"--[\w-]+", cmd))
        unknown = used - flags
        if unknown:
            bad_examples.append((cmd, unknown))
    rows.append(("SKILL.md example commands", not bad_examples,
                 "all flags exist in driver.py" if not bad_examples
                 else f"unknown flags: {bad_examples}"))

    print()
    failed = 0
    for label, ok, detail in rows:
        print(f"[{'  OK  ' if ok else ' FAIL '}] {label:<32} {detail}")
        if not ok:
            failed += 1
    print()
    if failed:
        print(f"{failed} check(s) failed — the docs and the code disagree.")
    else:
        print("Docs agree with the live renderer.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
