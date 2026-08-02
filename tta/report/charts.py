"""Inline SVG charts, sized for print.

Two deliberate departures from how these would normally be built:

* **No hover layer, no dark mode.** The primary artefact is a PDF. Interaction
  cannot survive printing, and a dark surface wastes toner. The HTML twin is a
  convenience, not the target.

* **The mark carries confidence.** Almost every finding on a young account comes
  back "too early to tell", and a solid bar reads as a fact whatever the caption
  next to it says. So proven marks are filled solid and unproven ones are drawn
  as a pale tint with a full-strength outline. Confidence lives in the mark
  itself, which is the only place a skimming reader will actually see it.

Colour rules followed here: categorical hues assigned in fixed slot order and
never cycled, above/below-average shown with a diverging pair around a neutral,
one axis per chart, every mark directly labelled, and a table beside every chart
so identity never rests on colour alone.
"""
from __future__ import annotations

import html
import math

# Fixed slot order. An entity keeps its hue across every chart in the report.
SERIES = ["#2A78D6", "#008300", "#E87BA4", "#EDA100", "#1BAF7A",
          "#EB6834", "#4A3AA7", "#E34948"]
POS, NEG, NEUTRAL = "#2A78D6", "#D03B3B", "#B8B7B2"
INK, INK_SOFT, GRID = "#0B0B0B", "#52514E", "#E5E4E0"
SURFACE = "#FCFCFB"

MAX_SLICES = 6          # past this the tail folds into "Other"
LABEL_MAX = 34          # longest row label before it is elided
PROVEN = ("strong", "moderate")


def esc(text) -> str:
    return html.escape(str(text if text is not None else ""), quote=True)


def series_color(i: int) -> str:
    return SERIES[i % len(SERIES)]


def _defs() -> str:
    """No pattern definitions are needed — see `_mark`."""
    return ""


def _mark(colour: str, proven: bool) -> str:
    """SVG paint attributes encoding confidence into the mark itself.

    Proven findings are solid. Unproven ones are a pale tint of the same hue
    with a full-strength outline: the shape and its direction stay completely
    legible, but the mark visibly lacks substance.

    This started out as a 45-degree hatch, which is the textbook answer. It was
    replaced because at print scale the hatch simply did not render — a chart
    of entirely unproven bars, which is the *normal* case for a young account,
    came out looking like an empty frame. An encoding that disappears at the
    size it is actually viewed is not an encoding.
    """
    if proven:
        return f' fill="{colour}"'
    return (f' fill="{colour}" fill-opacity="0.16"'
            f' stroke="{colour}" stroke-width="1.25"')


def _fmt(n) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return str(n)
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"{n / 1_000:.1f}K"
    return f"{n:,.0f}"


# ------------------------------------------------------------------------- donut

def donut(rows: list[dict], *, title: str, value_key: str = "n",
          label_key: str = "name", width: int = 640, height: int = 300) -> str:
    """Part-to-whole for the content mix.

    Capped at six slices with the tail folded into "Other" — beyond that,
    neighbouring wedges become impossible to tell apart and the reader is
    better served by the table. Every slice is directly labelled with its
    percentage, which also satisfies the contrast relief the palette needs.
    """
    rows = [r for r in rows if (r.get(value_key) or 0) > 0]
    if not rows:
        return _empty(title, width, height)
    rows = sorted(rows, key=lambda r: -(r.get(value_key) or 0))
    if len(rows) > MAX_SLICES:
        head, tail = rows[:MAX_SLICES], rows[MAX_SLICES:]
        rows = head + [{label_key: f"Other ({len(tail)} themes)",
                        value_key: sum(r.get(value_key) or 0 for r in tail),
                        "verdict": "too early to tell"}]

    total = sum(r.get(value_key) or 0 for r in rows) or 1
    cx, cy = 150, height / 2 + 6
    r_out, r_in = 96, 56
    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
             f'aria-label="{esc(title)}" xmlns="http://www.w3.org/2000/svg">', _defs()]

    angle = -math.pi / 2
    legend_y = 34
    for i, row in enumerate(rows):
        value = row.get(value_key) or 0
        frac = value / total
        sweep = frac * 2 * math.pi
        end = angle + sweep
        colour = series_color(i)
        proven = row.get("verdict") in PROVEN

        # 2px surface gap between adjacent fills
        gap = min(0.02, sweep * 0.04)
        a0, a1 = angle + gap / 2, end - gap / 2
        large = 1 if (a1 - a0) > math.pi else 0
        x0, y0 = cx + r_out * math.cos(a0), cy + r_out * math.sin(a0)
        x1, y1 = cx + r_out * math.cos(a1), cy + r_out * math.sin(a1)
        xi1, yi1 = cx + r_in * math.cos(a1), cy + r_in * math.sin(a1)
        xi0, yi0 = cx + r_in * math.cos(a0), cy + r_in * math.sin(a0)
        path = (f"M {x0:.2f} {y0:.2f} A {r_out} {r_out} 0 {large} 1 {x1:.2f} {y1:.2f} "
                f"L {xi1:.2f} {yi1:.2f} A {r_in} {r_in} 0 {large} 0 {xi0:.2f} {yi0:.2f} Z")
        parts.append(f'<path d="{path}"{_mark(colour, proven)}/>')

        # direct label on the slice when it is big enough to hold one
        if frac > 0.06:
            mid = (a0 + a1) / 2
            lx, ly = cx + 76 * math.cos(mid), cy + 76 * math.sin(mid)
            parts.append(
                f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" '
                f'dominant-baseline="middle" font-size="11" font-weight="600" '
                f'fill="{SURFACE}" style="paint-order:stroke;stroke:{colour};'
                f'stroke-width:3px">{frac * 100:.0f}%</text>')

        parts.append(
            f'<rect x="306" y="{legend_y - 9}" width="11" height="11" rx="2"'
            f'{_mark(colour, proven)}/>'
            f'<text x="325" y="{legend_y}" font-size="12" fill="{INK}">'
            f'{esc(_clip(row.get(label_key), 42))}</text>'
            f'<text x="{width - 12}" y="{legend_y}" font-size="12" text-anchor="end" '
            f'fill="{INK_SOFT}">{value} · {frac * 100:.0f}%</text>')
        legend_y += 22
        angle = end

    parts.append(f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" font-size="22" '
                 f'font-weight="700" fill="{INK}">{total}</text>'
                 f'<text x="{cx}" y="{cy + 14}" text-anchor="middle" font-size="11" '
                 f'fill="{INK_SOFT}">posts</text>')
    parts.append("</svg>")
    return _figure(title, "".join(parts))


# -------------------------------------------------------------------------- bars

def index_bars(rows: list[dict], *, title: str, label_key: str = "name",
               width: int = 640, bar_h: int = 26) -> str:
    """Horizontal diverging bars around the account's own average (index 100).

    Raw view counts are useless for comparing an account to itself across
    buckets of wildly different size, so everything is indexed. The baseline is
    drawn at 100 and bars run left or right of it — which is the whole question
    a reader has: better or worse than usual?
    """
    rows = [r for r in rows if r.get("n")]
    if not rows:
        return _empty(title, width, 120)

    height = 34 + len(rows) * bar_h + 26
    span = max(60, max(abs(r["index"] - 100) for r in rows) * 1.15)
    # Theme names are long and are right-anchored into this gutter, so the
    # gutter has to be wide enough for the longest one or the labels run off
    # the left edge of the SVG and are silently clipped.
    label_chars = max((len(_clip(r.get(label_key), LABEL_MAX)) for r in rows), default=10)
    left = min(260, max(150, int(label_chars * 6.2) + 16))
    right = width - 66
    mid = left + (right - left) / 2
    half = (right - left) / 2

    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
             f'aria-label="{esc(title)}" xmlns="http://www.w3.org/2000/svg">', _defs()]
    parts.append(f'<line x1="{mid}" y1="20" x2="{mid}" y2="{height - 24}" '
                 f'stroke="{INK_SOFT}" stroke-width="1"/>')
    parts.append(f'<text x="{mid}" y="14" text-anchor="middle" font-size="10" '
                 f'fill="{INK_SOFT}">account average</text>')

    y = 30
    for row in rows:
        delta = row["index"] - 100
        proven = row.get("verdict") in PROVEN
        colour = POS if delta >= 0 else NEG
        w = abs(delta) / span * half
        x = mid if delta >= 0 else mid - w
        parts.append(
            f'<rect x="{x:.1f}" y="{y}" width="{max(1.5, w):.1f}" height="{bar_h - 9}" '
            f'rx="3"{_mark(colour, proven)}/>')
        parts.append(
            f'<text x="{left - 10}" y="{y + bar_h - 15}" text-anchor="end" font-size="11.5" '
            f'fill="{INK}">{esc(_clip(row.get(label_key), LABEL_MAX))}</text>')
        label_x = (x + w + 7) if delta >= 0 else (x - 7)
        anchor = "start" if delta >= 0 else "end"
        parts.append(
            f'<text x="{label_x:.1f}" y="{y + bar_h - 15}" text-anchor="{anchor}" '
            f'font-size="11" font-weight="600" fill="{INK if proven else INK_SOFT}">'
            f'{delta:+.0f}%</text>')
        parts.append(
            f'<text x="{width - 8}" y="{y + bar_h - 15}" text-anchor="end" font-size="10" '
            f'fill="{INK_SOFT}">n={row["n"]}</text>')
        y += bar_h

    parts.append("</svg>")
    return _figure(title, "".join(parts))


def volume_bars(rows: list[dict], *, title: str, label_key: str, value_key: str,
                width: int = 640, bar_h: int = 24) -> str:
    """Plain magnitude bars, single hue, baseline at zero."""
    rows = [r for r in rows if (r.get(value_key) or 0) > 0]
    if not rows:
        return _empty(title, width, 120)
    height = 26 + len(rows) * bar_h + 16
    top = max(r[value_key] for r in rows) or 1
    left, right = 150, width - 70

    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
             f'aria-label="{esc(title)}" xmlns="http://www.w3.org/2000/svg">', _defs()]
    y = 22
    for row in rows:
        w = (row[value_key] / top) * (right - left)
        parts.append(f'<rect x="{left}" y="{y}" width="{max(1.5, w):.1f}" '
                     f'height="{bar_h - 8}" rx="3" fill="{SERIES[0]}"/>')
        parts.append(f'<text x="{left - 10}" y="{y + bar_h - 13}" text-anchor="end" '
                     f'font-size="11.5" fill="{INK}">{esc(_clip(row.get(label_key), 26))}</text>')
        parts.append(f'<text x="{left + w + 7:.1f}" y="{y + bar_h - 13}" font-size="11" '
                     f'fill="{INK_SOFT}">{_fmt(row[value_key])}</text>')
        y += bar_h
    parts.append("</svg>")
    return _figure(title, "".join(parts))


# -------------------------------------------------------------------------- line

def trend_line(rows: list[dict], *, title: str, x_key: str = "month",
               y_key: str = "avg", width: int = 640, height: int = 260) -> str:
    """Monthly reach with the overall average as a baseline and the peak marked.

    One measure, one axis. "Average views per month" and "posts per month" are
    deliberately two charts rather than one dual-axis chart.
    """
    rows = [r for r in rows if r.get(y_key) is not None]
    if len(rows) < 2:
        return _empty(title, width, height)

    pad_l, pad_r, pad_t, pad_b = 58, 18, 26, 40
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    top = max(r[y_key] for r in rows) or 1
    avg = sum(r[y_key] for r in rows) / len(rows)
    step = plot_w / max(1, len(rows) - 1)

    def px(i):
        return pad_l + i * step

    def py(v):
        return pad_t + plot_h - (v / top) * plot_h

    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
             f'aria-label="{esc(title)}" xmlns="http://www.w3.org/2000/svg">', _defs()]

    # recessive gridlines — the data should be the loudest thing in the frame
    for frac in (0, 0.25, 0.5, 0.75, 1.0):
        gy = pad_t + plot_h * frac
        parts.append(f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{width - pad_r}" y2="{gy:.1f}" '
                     f'stroke="{GRID}" stroke-width="1"/>')
        parts.append(f'<text x="{pad_l - 8}" y="{gy + 4:.1f}" text-anchor="end" '
                     f'font-size="10" fill="{INK_SOFT}">{_fmt(top * (1 - frac))}</text>')

    parts.append(f'<line x1="{pad_l}" y1="{py(avg):.1f}" x2="{width - pad_r}" '
                 f'y2="{py(avg):.1f}" stroke="{INK_SOFT}" stroke-width="1" '
                 f'stroke-dasharray="4 3"/>')
    # Anchored left, not right: the right edge is where the final data point's
    # own label sits, and the two collide there.
    parts.append(f'<text x="{pad_l + 6}" y="{py(avg) - 5:.1f}" '
                 f'font-size="10" fill="{INK_SOFT}">average {_fmt(avg)}</text>')

    pts = " ".join(f"{px(i):.1f},{py(r[y_key]):.1f}" for i, r in enumerate(rows))
    area = (f"M {pad_l},{pad_t + plot_h} L " + pts.replace(" ", " L ") +
            f" L {px(len(rows) - 1):.1f},{pad_t + plot_h} Z")
    parts.append(f'<path d="{area}" fill="{SERIES[0]}" opacity="0.10"/>')
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{SERIES[0]}" '
                 f'stroke-width="2" stroke-linejoin="round"/>')

    peak = max(range(len(rows)), key=lambda i: rows[i][y_key])
    for i, row in enumerate(rows):
        is_peak = i == peak
        parts.append(f'<circle cx="{px(i):.1f}" cy="{py(row[y_key]):.1f}" '
                     f'r="{4.5 if is_peak else 3}" fill="{SERIES[0]}" '
                     f'stroke="{SURFACE}" stroke-width="2"/>')
        # selective labels only: first, last and peak. Never a number on every point.
        if is_peak or i in (0, len(rows) - 1):
            parts.append(f'<text x="{px(i):.1f}" y="{py(row[y_key]) - 11:.1f}" '
                         f'text-anchor="middle" font-size="10" font-weight="600" '
                         f'fill="{INK}">{_fmt(row[y_key])}</text>')

    every = max(1, len(rows) // 8)
    for i, row in enumerate(rows):
        if i % every == 0 or i == len(rows) - 1:
            parts.append(f'<text x="{px(i):.1f}" y="{height - 16}" text-anchor="middle" '
                         f'font-size="10" fill="{INK_SOFT}">{esc(row[x_key])}</text>')

    parts.append("</svg>")
    return _figure(title, "".join(parts))


# ---------------------------------------------------------------------- plumbing

def _clip(text, n: int) -> str:
    text = str(text or "").replace("\n", " ").strip()
    return text if len(text) <= n else text[:n - 1] + "…"


def _figure(title: str, svg: str) -> str:
    return (f'<figure class="chart">'
            f'<figcaption>{esc(title)}</figcaption>{svg}</figure>')


def _empty(title: str, width: int, height: int) -> str:
    return (f'<figure class="chart"><figcaption>{esc(title)}</figcaption>'
            f'<p class="empty">Not enough data to draw this yet.</p></figure>')


def legend_note() -> str:
    """Explains the hatching once, near the first chart that uses it."""
    return ('<p class="legend-note"><span class="swatch solid"></span> filled = the '
            'difference cleared a significance test &nbsp;·&nbsp; '
            '<span class="swatch hatched"></span> outlined = not enough evidence yet, '
            'treat as a hint rather than a finding</p>')
