"""Guided setup: do the machine's half, hand over the human's half cleanly.

Setting this up involves two genuinely different kinds of work, and the usual
README mashes them together into one numbered list that the reader has to sort
out for themselves.

**The machine's half** is installing packages, creating a directory and
starting a server. An agent can do all of it, and should — after asking, since
it is the user's machine.

**The human's half** is everything behind a login or a browser UI: creating an
email, creating a TikTok account, clicking "Add to Chrome", typing a password.
Some of that an agent merely *cannot* do; the rest it **must not**. Creating
accounts and entering passwords on somebody's behalf is off the table however
convenient it would be, so those steps come with instructions and a URL, and
then the agent waits.

Sorting the work by who can do it, rather than by the order it appears in, is
the whole point of this module.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import paths

CAMOFOX_DIR = Path.home() / ".camofox-browser"
CAMOFOX_PKG = "@askjo/camofox-browser"

COOKIE_EXTENSION_URL = (
    "https://chromewebstore.google.com/search/get%20cookies.txt%20locally")
NODE_URL = "https://nodejs.org/en/download"
PYTHON_URL = "https://www.python.org/downloads/"


def _run(cmd: list[str], timeout: int = 900) -> tuple[bool, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout, text=True)
    except FileNotFoundError:
        return False, f"{cmd[0]} not found"
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    out = (p.stdout or "") + (p.stderr or "")
    tail = [ln for ln in out.strip().splitlines() if ln.strip()]
    return p.returncode == 0, (tail[-1][:160] if tail else "")


# ------------------------------------------------------------------ the checks

def python_ok() -> bool:
    return sys.version_info >= (3, 10)


def deps_missing() -> list[str]:
    missing = []
    for mod, pkg in (("yt_dlp", "yt-dlp"), ("openpyxl", "openpyxl")):
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    return missing


def node_ok() -> tuple[bool, str]:
    found = shutil.which("node")
    if not found:
        return False, "not installed"
    ok, out = _run([found, "-v"], timeout=30)
    if not ok:
        return False, "not runnable"
    version = out.strip().lstrip("v")
    major = int(version.split(".")[0]) if version.split(".")[0].isdigit() else 0
    return major >= 18, f"v{version}"


def camofox_installed() -> bool:
    return (CAMOFOX_DIR / "node_modules" / "@askjo" /
            "camofox-browser" / "server.js").exists()


# --------------------------------------------------------- the machine's half

def install_deps(log=print) -> bool:
    missing = deps_missing()
    if not missing:
        log("  Python packages already installed.")
        return True
    log(f"  Installing {', '.join(missing)}...")
    ok, msg = _run([sys.executable, "-m", "pip", "install", *missing])
    log("  Installed." if ok else f"  Failed: {msg}")
    return ok


def install_camofox(log=print) -> bool:
    """npm install into ~/.camofox-browser.

    The skill ships a setup.sh, but it is POSIX bash and hardcodes /tmp paths,
    so on Windows it needs Git Bash to run at all. The install underneath it is
    a plain npm install, which works the same everywhere.
    """
    ok, detail = node_ok()
    if not ok:
        log(f"  Node.js is {detail}. This one needs a human — see below.")
        return False
    if camofox_installed():
        log("  camofox already installed.")
        return True

    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        log("  npm not found alongside node.")
        return False

    CAMOFOX_DIR.mkdir(parents=True, exist_ok=True)
    log(f"  Installing {CAMOFOX_PKG} into {CAMOFOX_DIR} (~300MB, a few minutes)...")
    _run([npm, "init", "-y"], timeout=120)
    ok, msg = _run([npm, "install", CAMOFOX_PKG], timeout=1800)
    if ok and camofox_installed():
        log("  camofox installed.")
        return True
    log(f"  camofox install failed: {msg}")
    return False


def start_camofox(log=print) -> bool:
    from .harvest import camofox
    if camofox.healthy():
        log("  camofox is already running.")
        return True
    if not camofox_installed():
        return False
    log("  Starting the camofox server...")
    return camofox.start_server(log=log)


def make_home(log=print) -> bool:
    try:
        paths.ensure(paths.home())
        log(f"  Your data folder is ready: {paths.home()}")
        return True
    except OSError as exc:
        log(f"  Could not create {paths.home()}: {exc}")
        return False


# ------------------------------------------------------------ the human's half

def human_steps(*, need_python: bool, need_node: bool,
                need_session: bool) -> list[dict]:
    """What is left for the person, in the order they should do it.

    Only what genuinely requires them. A list that includes things the agent
    already did teaches people to skim it, and the one step that matters is in
    there somewhere.
    """
    steps: list[dict] = []

    if need_python:
        steps.append({
            "title": "Install Python 3.10 or newer",
            "why": "Everything here runs on it.",
            "do": [f"Download it from {PYTHON_URL}",
                   "On Windows, tick 'Add python.exe to PATH' on the first "
                   "screen — skipping it is the usual reason the next step "
                   "fails",
                   "Then run this setup again"],
        })

    if need_node:
        steps.append({
            "title": "Install Node.js 18 or newer",
            "why": "Only needed for the camofox stealth browser, which adds "
                   "follower counts, the profile audit and niche research. "
                   "Everything else works without it.",
            "do": [f"Download the LTS build from {NODE_URL}",
                   "Then run this setup again and it will install camofox "
                   "for you"],
        })

    if need_session:
        steps.extend([
            {
                "title": "Make a new browser profile",
                "why": "A cookie export carries every cookie that profile "
                       "holds. From your everyday browser that is your email, "
                       "your bank, everything. A profile that has only seen "
                       "tiktok.com can only export tiktok.com.",
                "do": ["Chrome: your avatar, top right -> Add -> continue "
                       "without an account",
                       "Do not sign it into Google",
                       "Do everything below inside that profile"],
            },
            {
                "title": "Make a throwaway TikTok account",
                "why": "Automated reading can get an account rate-limited. "
                       "This is the one you can afford to lose.",
                "do": ["A spare email address, then sign up at tiktok.com",
                       "No posts, no picture, no followers needed — it only "
                       "ever reads",
                       "A separate profile separates cookies, not identity: "
                       "TikTok can still link accounts by device and network"],
                "agent_must_not": "Creating accounts and entering passwords is "
                                  "for the account holder to do, not an agent.",
            },
            {
                "title": "Install a cookies.txt extension in that profile",
                "why": "It is what exports the session. It belongs in the "
                       "throwaway profile because it can read cookies for "
                       "every site by design.",
                "do": [f"Open {COOKIE_EXTENSION_URL}",
                       "Pick one that is open-source and works offline — "
                       "'Get cookies.txt LOCALLY' is the usual choice",
                       "Check its reviews and permissions before adding it",
                       "Click 'Add to Chrome'"],
                "agent_must_not": "Installing a browser extension needs a click "
                                  "in the browser's own UI.",
            },
            {
                "title": "Sign in and export",
                "why": "This produces the file the tool reads.",
                "do": ["Sign into the throwaway account at tiktok.com",
                       "Stay on a tiktok.com page",
                       "Click the extension's icon and export for this site",
                       f"Save it as {paths.home() / 'tiktok-cookies.txt'}",
                       "Do not leave it in Downloads"],
                "agent_must_not": "Signing in means typing a password.",
            },
        ])

    return steps


def render_human_steps(steps: list[dict]) -> str:
    if not steps:
        return "  Nothing left for you to do."
    out = []
    for i, s in enumerate(steps, start=1):
        out.append(f"  {i}. {s['title']}")
        out.append(f"     Why: {s['why']}")
        for line in s["do"]:
            out.append(f"       - {line}")
        if s.get("agent_must_not"):
            out.append(f"     (Not something to hand to an agent: "
                       f"{s['agent_must_not']})")
        out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------- driver

def run(*, assume_yes: bool = False, want_session: bool = False,
        log=print) -> int:
    """Do the machine's half, then print the human's half."""
    from . import voice
    log("")
    log(voice.mark())
    log("")
    log("What I can do for you")
    log("-" * 21)

    if not python_ok():
        log(f"  Python {sys.version_info.major}.{sys.version_info.minor} is too "
            f"old — 3.10+ is needed, and I cannot upgrade it for you.")
    else:
        log(f"  Python {sys.version_info.major}.{sys.version_info.minor} is fine.")

    if deps_missing() and not assume_yes:
        log(f"  Needs: pip install {' '.join(deps_missing())}")
        log("  (re-run with --yes to let me install it)")
    elif python_ok():
        install_deps(log=log)

    node_fine, node_detail = node_ok()
    if not node_fine:
        log(f"  Node.js: {node_detail} — camofox needs it, see below.")
    elif not camofox_installed() and not assume_yes:
        log("  camofox is not installed. It is ~300MB and adds roughly half "
            "the report.")
        log("  (re-run with --yes to let me install it)")
    elif node_fine:
        if install_camofox(log=log):
            start_camofox(log=log)

    make_home(log=log)

    steps = human_steps(need_python=not python_ok(),
                        need_node=not node_fine,
                        need_session=want_session)
    log("")
    log("What only you can do")
    log("-" * 20)
    log(render_human_steps(steps))
    log("Then check everything with:  python driver.py --doctor")
    log("")
    return 0
