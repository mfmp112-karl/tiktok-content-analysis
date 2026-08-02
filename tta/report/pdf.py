"""Turning the report page into a PDF, by whatever route this machine allows.

Three tiers, in descending order of output quality:

1. **A Chromium-family browser** — Chrome, Edge, Brave, Chromium. Prints real
   vector PDF with selectable text, and is present on the overwhelming majority
   of machines: Edge ships with Windows, and Chrome is near-ubiquitous elsewhere.
2. **camofox** — the stealth browser, if the user has it. Camoufox is a Firefox
   fork, and Firefox has no print-to-PDF, so this route screenshots the page and
   wraps the images with `minipdf`. Raster, larger, no text selection.
3. **The HTML alone**, always written regardless of which tier ran. It opens in
   any browser and for many readers it is the nicer artefact anyway.

A failure at one tier is never fatal — it falls through and the caller is told
which route produced the file.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .. import attribution
from . import minipdf

#: Probed in order. The env var wins so anyone with an unusual install can point at it.
ENV_BROWSER = "TTA_BROWSER"

WINDOWS_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
]
MAC_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
]
POSIX_NAMES = ["google-chrome", "google-chrome-stable", "chromium",
               "chromium-browser", "microsoft-edge", "brave-browser"]


def find_browser() -> str | None:
    """Locate a Chromium-family binary, or None."""
    override = os.getenv(ENV_BROWSER)
    if override and Path(override).exists():
        return override

    for name in POSIX_NAMES + ["chrome", "msedge"]:
        found = shutil.which(name)
        if found:
            return found

    candidates = (WINDOWS_CANDIDATES if sys.platform == "win32"
                  else MAC_CANDIDATES if sys.platform == "darwin" else [])
    for path in candidates:
        if Path(path).exists():
            return path
    return None


def describe_browser() -> str:
    found = find_browser()
    return found if found else "none found"


# ------------------------------------------------------------------ tier 1: chromium

def via_chromium(html_path: Path, pdf_path: Path, *, browser: str | None = None,
                 timeout: int = 120, log=print) -> bool:
    browser = browser or find_browser()
    if not browser:
        return False
    profile = tempfile.mkdtemp(prefix="tta-chrome-")
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-first-run",
        "--no-pdf-header-footer",
        f"--user-data-dir={profile}",
        f"--print-to-pdf={pdf_path}",
        html_path.resolve().as_uri(),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError) as exc:
        log(f"    chromium print failed: {exc}")
        return False
    finally:
        shutil.rmtree(profile, ignore_errors=True)

    if pdf_path.exists() and pdf_path.stat().st_size > 1000:
        return True
    err = (proc.stderr or b"").decode("utf-8", "replace").strip().splitlines()
    log(f"    chromium produced no PDF (exit {proc.returncode})"
        + (f": {err[-1]}" if err else ""))
    return False


# ------------------------------------------------------------------- tier 2: camofox

def via_camofox(html_path: Path, pdf_path: Path, *, log=print) -> bool:
    """Screenshot the page in the stealth browser, then wrap the images.

    Firefox cannot print to PDF, so this is a raster capture. The page is
    rendered at a fixed width and captured full-height, then sliced into A4-ish
    pages by `minipdf`.
    """
    from ..harvest import camofox
    if not camofox.healthy():
        log("    camofox is not running")
        return False

    tmpdir = Path(tempfile.mkdtemp(prefix="tta-shots-"))
    try:
        tab = camofox.open_url(html_path.resolve().as_uri(), settle=2.0, log=log)
        camofox.set_viewport(tab, 900, 1400)
        time.sleep(1.0)
        shot = tmpdir / "report.png"
        if not camofox.screenshot(tab, shot, full_page=True):
            log("    camofox screenshot failed")
            return False
        camofox.close_tab(tab)
        minipdf.images_to_pdf([shot], pdf_path)
        return pdf_path.exists() and pdf_path.stat().st_size > 1000
    except Exception as exc:
        log(f"    camofox PDF route failed: {type(exc).__name__}: {exc}")
        return False
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ------------------------------------------------------------------------- entry

def write(html_text: str, out_dir: Path, *, stem: str = "report", log=print) -> dict:
    """Write the HTML, then get a PDF out of it however this machine can."""
    attribution.assert_stamped(html_text, "report HTML")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    html_path = out_dir / f"{stem}.html"
    html_path.write_text(html_text, encoding="utf-8")

    pdf_path = out_dir / f"{stem}.pdf"
    browser = find_browser()
    if browser:
        log(f"    printing via {Path(browser).name}")
        if via_chromium(html_path, pdf_path, browser=browser, log=log):
            return {"pdf": pdf_path, "html": html_path, "route": Path(browser).name,
                    "quality": "vector"}

    log("    no Chromium browser available - trying camofox")
    if via_camofox(html_path, pdf_path, log=log):
        return {"pdf": pdf_path, "html": html_path, "route": "camofox (raster)",
                "quality": "raster"}

    log("    no PDF route available - the HTML report is still complete")
    return {"pdf": None, "html": html_path, "route": "none", "quality": "html only"}
