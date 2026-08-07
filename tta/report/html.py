"""The report page itself — print-first HTML.

Laid out for A4 rather than for a screen: a serif-free print register, explicit
page breaks between sections, no dark mode, and a table beside every chart so
the document still works photocopied in black and white.

Three things are load-bearing and worth not "tidying away":

* **The cover states its own provenance.** Which account was analysed, which
  session it was read through, when, and by what version. A report that travels
  without that is an assertion; with it, it is a record.

* **"What this cannot tell you" is a section, not a footnote.** Watch time,
  retention, traffic sources and demographics are owner-only on TikTok. Leaving
  that implicit invites the reader to assume the silence means zero.

* **Narration is optional.** Every section renders a sound default from the
  numbers alone. When an agent supplies prose it is inserted, but nothing here
  depends on a language model being available.
"""
from __future__ import annotations

from datetime import datetime

from .. import attribution, voice
from .. import text as texttool
from ..analyse.themes import readable
from ..stats import plain
from . import charts
from .charts import esc

CSS = """
:root {
  --ink: #17150F; --soft: #4E4A40; --muted: #7C7669;
  --rule: #E2DED2; --surface: #FBFAF6; --band: #F3F1E8;
  --accent: #B4451F; --accent-soft: #F6E7DF;
  --pos: #2A78D6; --neg: #D03B3B; --good: #0CA30C; --warn: #B07800;
  --display: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  --text: "Segoe UI", -apple-system, "Helvetica Neue", Arial, sans-serif;
}
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  margin: 0; background: var(--surface); color: var(--ink);
  font: 400 13px/1.6 var(--text);
}
@page { size: A4; margin: 14mm 13mm 16mm; }

/* On screen the document has no page margin of its own, so text and footers
   run to the window edge. Print takes its margin from @page instead, so this
   must not apply there or the two would stack. */
@media screen {
  body { padding: 28px 30px 40px; max-width: 900px; margin: 0 auto; }
}

.page { padding: 0 0 6mm; }
.page + .page { break-before: page; padding-top: 2mm; }

h1 { font-family: var(--display); font-size: 34px; font-weight: 600;
     line-height: 1.1; margin: 0 0 8px; letter-spacing: -0.01em; }
h2 { font-family: var(--display); font-size: 22px; font-weight: 600;
     margin: 0 0 4px; letter-spacing: -0.01em; }
/* Weight and size carry the hierarchy. An uppercase tracked eyebrow over
   every subsection is grammar nobody chose. */
h3 { font-size: 14px; font-weight: 700; margin: 22px 0 6px; color: var(--ink); }
p  { margin: 0 0 10px; max-width: 68ch; }
.sub { color: var(--soft); margin: 0 0 18px; font-size: 13.5px; }
.lede { font-size: 15px; line-height: 1.65; }

.rule { height: 1px; background: var(--rule); margin: 16px 0 18px; border: 0; }

/* cover ------------------------------------------------------------------ */
.cover { padding-top: 6mm; }
.cover h1 { font-size: 46px; margin-bottom: 14px; }
/* The opening figure is set as a sentence, not a stat card: this document
   often has to tell someone their work is not yet measurable, and the first
   thing it should do is count what they have already made. */
.headline { font-family: var(--display); font-size: 26px; line-height: 1.35;
  font-weight: 400; max-width: 24ch; margin: 0 0 22px; color: var(--ink); }
.headline b { font-weight: 600; font-size: 44px; color: var(--accent);
  font-variant-numeric: tabular-nums; letter-spacing: -0.02em;
  display: block; line-height: 1; margin-bottom: 2px; }

.signed { font-family: var(--display); font-style: italic; font-size: 15px;
  color: var(--soft); max-width: 46ch; margin: -8px 0 20px; }
.provenance { border-top: 1px solid var(--ink); border-bottom: 1px solid var(--rule);
  padding: 12px 0; margin: 22px 0; }
.provenance dl { display: grid; grid-template-columns: max-content 1fr;
  gap: 6px 22px; margin: 0; font-size: 12.5px; }
.provenance dt { color: var(--muted); }
.provenance dd { margin: 0; font-weight: 600; }
.notice { background: var(--accent-soft); border: 1px solid #EBD5C9;
  border-radius: 3px; padding: 13px 15px; margin: 20px 0; font-size: 12.5px;
  color: #6B3A24; }
.notice strong { color: #4A2415; }

/* figure run — inline, hairline-separated, not a grid of cards ----------- */
.figures { display: flex; gap: 0; margin: 16px 0 20px;
  border-top: 1px solid var(--ink); border-bottom: 1px solid var(--rule); }
.fig { flex: 1; padding: 12px 16px 12px 0; }
.fig + .fig { border-left: 1px solid var(--rule); padding-left: 16px; }
.fig .v { font-family: var(--display); font-size: 26px; font-weight: 600;
  line-height: 1.05; font-variant-numeric: tabular-nums; }
.fig .k { font-size: 11.5px; color: var(--muted); margin-top: 3px; }

/* tables ----------------------------------------------------------------- */
table { width: 100%; border-collapse: collapse; margin: 8px 0 14px;
  font-size: 12px; font-variant-numeric: tabular-nums; }
th { text-align: right; font-weight: 600; color: #fff; background: #1F2933;
  padding: 7px 8px; font-size: 11px; }
th:first-child, td:first-child, th.tl, td.tl { text-align: left; }
td { padding: 6px 8px; border-bottom: 1px solid var(--rule); text-align: right; }
tbody tr:nth-child(even) { background: var(--band); }
.v-strong { color: var(--good); font-weight: 600; }
.v-moderate { color: var(--warn); }
.v-weak { color: var(--muted); }
.up { color: var(--pos); font-weight: 600; }
.down { color: var(--neg); font-weight: 600; }

/* charts ----------------------------------------------------------------- */
.chart { margin: 6px 0 14px; break-inside: avoid; }
.chart figcaption { font-size: 12.5px; font-weight: 600; margin-bottom: 4px; }
.chart .empty { color: var(--muted); font-size: 12px; font-style: italic; }
.legend-note { font-size: 11px; color: var(--soft); margin: -6px 0 14px; }
.swatch { display: inline-block; width: 20px; height: 9px; border-radius: 2px;
  vertical-align: middle; margin-right: 3px; }
.swatch.solid { background: var(--pos); }
/* Matches charts.py `_mark` for the unproven case: pale tint, solid outline. */
.swatch.hatched { background: rgba(42,120,214,.16);
  border: 1.25px solid var(--pos); height: 11px; }

.two { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.avoid { break-inside: avoid; }

/* verdict pills ---------------------------------------------------------- */
.pill { display: inline-block; padding: 1px 7px; border-radius: 10px;
  font-size: 10.5px; font-weight: 600; }
.pill.keep { background: #E4F5E4; color: #0A6E0A; }
.pill.ditch { background: #FBE6E6; color: #A32020; }
.pill.test { background: #FDF3DC; color: #7A5400; }
.pill.replace { background: #E7EEFA; color: #1B4F94; }

.checks li { margin-bottom: 8px; }
.check-pass::marker { content: "PASS  "; }
.check-fix::marker  { content: "FIX  "; }
.hooklist { margin: 0; padding-left: 18px; }
.hooklist li { margin-bottom: 6px; }
.hooklist .m { color: var(--muted); font-size: 11px; }

/* links inside tables — the calendar's example-post cells ----------------- */
a { color: var(--accent); text-decoration: none; }

/* recommendations — a numbered run of things to actually make ------------ */
.recs { list-style: none; margin: 10px 0 0; padding: 0; counter-reset: rec; }
.recs li { counter-increment: rec; padding: 12px 0 12px 42px; position: relative;
  border-top: 1px solid var(--rule); break-inside: avoid; }
.recs li::before { content: counter(rec); position: absolute; left: 0; top: 12px;
  font-family: var(--display); font-size: 20px; font-weight: 600;
  color: var(--accent); line-height: 1; }
.recs .h { font-weight: 700; font-size: 14px; margin-bottom: 3px; }
.recs .w { color: var(--soft); max-width: 66ch; }
.recs .tag { display: inline-block; font-size: 10.5px; color: var(--muted);
  margin-top: 4px; }

/* the countdown — what would make an undecided finding decidable --------- */
.needs { color: var(--accent); font-weight: 600; }

footer { margin-top: 10mm; padding-top: 8px; border-top: 1px solid var(--rule);
  font-size: 10.5px; color: var(--muted); display: flex;
  justify-content: space-between; gap: 12px; }

/* appendix — method/limits/credits. Flows onto the tail of the last page
   rather than forcing a fresh one: it is reference material, not a finding,
   and does not earn a page of its own. */
.appendix { margin-top: 14mm; padding-top: 10px; border-top: 1px solid var(--ink);
  font-size: 11.5px; }
.appendix h2 { font-size: 15px; margin-bottom: 8px; }
.appendix h3 { font-size: 11.5px; margin: 12px 0 4px; color: var(--soft); }
.appendix p { margin: 0 0 6px; max-width: 74ch; }
.appendix ul { margin: 0 0 6px; padding-left: 16px; }
"""

VERDICT_CLASS = {"strong": "v-strong", "moderate": "v-moderate"}


def _v(verdict: str) -> str:
    cls = VERDICT_CLASS.get(verdict, "v-weak")
    return f'<span class="{cls}">{esc(plain(verdict))}</span>'


def _num(n) -> str:
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return esc(n)


def _delta(d) -> str:
    try:
        d = int(d)
    except (TypeError, ValueError):
        return esc(d)
    cls = "up" if d >= 0 else "down"
    return f'<span class="{cls}">{d:+d}%</span>'


def _table(headers: list[str], rows: list[list[str]],
           left_cols: set[int] | None = None) -> str:
    """Numbers right, prose left.

    Columns default to right-aligned because most of them are figures, but a
    right-aligned sentence — a bio, a content prompt — is genuinely hard to
    read. `left_cols` holds the 0-based indices that carry text.
    """
    if not rows:
        return '<p class="chart"><span class="empty">Nothing to show here yet.</span></p>'
    left_cols = left_cols or set()

    # Built by concatenation rather than with the class attribute inlined into
    # an f-string: escaped quotes inside an f-string expression are a syntax
    # error before Python 3.12, and this tool claims to support 3.10.
    def cls(i: int) -> str:
        return ' class="tl"' if i in left_cols else ""

    head = "".join("<th" + cls(i) + ">" + esc(h) + "</th>"
                   for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join("<td" + cls(i) + ">" + str(c) + "</td>"
                         for i, c in enumerate(r)) + "</tr>"
        for r in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _prose(narrative: dict, key: str, fallback: str = "") -> str:
    text = (narrative or {}).get(key) or fallback
    if not text:
        return ""
    paras = [p.strip() for p in str(text).split("\n\n") if p.strip()]
    return "".join(f'<p class="lede">{esc(p)}</p>' for p in paras)


# ============================================================== section builders

def _cover(ctx: dict) -> str:
    meta = ctx["meta"]
    k = ctx["analysis"]["kpi"]
    creator = ctx.get("creator") or {}
    followers = creator.get("followers")
    span = ""
    if k.get("start") and k.get("end"):
        span = f"{k['start']:%d %b %Y} to {k['end']:%d %b %Y}"

    posts = k.get("n", 0)
    views = k.get("total_views", 0)
    # Months below a year: rounding 210 days up to "1 year" overstates the
    # catalogue on exactly the accounts least able to afford an overstatement.
    days = k.get("span_days") or 30
    if days >= 400:
        n = round(days / 365 * 10) / 10
        span = f"{n:g} year{'s' if n != 1 else ''}"
    else:
        n = max(1, round(days / 30.4))
        span = f"{n} month{'s' if n != 1 else ''}"
    return f"""
<section class="page cover">
  <h1>What @{esc(meta['handle'])}<br>has already made</h1>

  <p class="headline"><b>{_num(views)}</b>
     views across {_num(posts)} posts, over {esc(span)}.
     Here is what that adds up to, and what to make next.</p>
  {f'<p class="signed">{esc(voice.cover_note(posts, span))}</p>' if voice.cover_note(posts, span) else ''}

  <div class="provenance">
    <dl>
      <dt>Account analysed</dt><dd>@{esc(meta['handle'])}</dd>
      <dt>Posts examined</dt><dd>{_num(k.get('n', 0))}{f" &nbsp;·&nbsp; {esc(span)}" if span else ""}</dd>
      <dt>Followers</dt><dd>{_num(followers) if followers else "not captured"}</dd>
      <dt>Accessed via</dt><dd>{esc(meta['accessed_via'])}</dd>
      <dt>Data source</dt><dd>{esc(meta['harvest_tier'])}</dd>
      <dt>Generated</dt><dd>{esc(meta['generated'])}</dd>
      <dt>Read by</dt><dd>{esc(voice.NAME if not voice.is_plain() else 'TikTok Content Analysis')} v{esc(meta['version'])}</dd>
    </dl>
  </div>

  <div class="notice">
    <strong>What this is for.</strong> {esc(voice.report("cover.ethics"))}
  </div>

  <hr class="rule">
  {_prose(ctx.get('narrative'), 'summary', voice.report("cover.intro"))}

  <footer><span>{esc(attribution.stamp_footer())}</span>
          <span>@{esc(meta['handle'])} &nbsp;·&nbsp; {esc(meta['generated'])}</span></footer>
</section>"""


def _at_a_glance(ctx: dict) -> str:
    k = ctx["analysis"]["kpi"]
    cad = ctx["cadence"]
    limits = ctx.get("limits", [])
    figures = [
        (_num(k.get("avg", 0)), f"average views · median {_num(k.get('median', 0))}"),
        (_num(k.get("best", 0)), "best post"),
        (f"{k.get('per_week', 0)}", "posts a week"),
        (f"{k.get('like_rate', 0)}%", f"like rate · {k.get('comment_rate', 0)}% comments"),
    ]
    fig_html = "".join(
        f'<div class="fig"><div class="v">{v}</div><div class="k">{esc(kk)}</div></div>'
        for v, kk in figures)

    limit_items = "".join(f"<li>{esc(x)}</li>" for x in limits)
    return f"""
<section class="page">
  <h2>At a glance</h2>
  <p class="sub">{esc(voice.report("glance.sub"))}</p>
  <div class="figures">{fig_html}</div>
  {_prose(ctx.get('narrative'), 'glance')}

  <h3>Posting rhythm</h3>
  <p>Currently posting about <strong>{cad['rhythm']['recent_per_week']} times a week</strong>
     ({esc(cad['rhythm']['trend'])} against a lifetime rate of
     {cad['rhythm']['per_week']}). Longest run of consecutive days:
     <strong>{cad['gaps']['longest_streak']}</strong>. Longest silence:
     <strong>{cad['gaps']['longest_gap']} days</strong>.</p>

  <h3>{esc(voice.report("glance.limits"))}</h3>
  <p class="sub">{esc(voice.cannot_measure())}</p>
  <ul>{limit_items}</ul>

  <footer><span>{esc(attribution.stamp_footer())}</span><span>At a glance</span></footer>
</section>"""


#: The month-by-month table stays useful for as long as a month is still
#: recent enough to act on. Past that it is history, not a planning input —
#: the trend charts above the table already carry the long arc, in full.
REACH_TABLE_MONTHS = 12


def _reach(ctx: dict) -> str:
    a = ctx["analysis"]
    monthly = a["monthly"]
    older, recent = monthly[:-REACH_TABLE_MONTHS], monthly[-REACH_TABLE_MONTHS:]

    older_note = ""
    if older:
        older_posts = sum(r["posts"] for r in older)
        older_avg = (round(sum(r["avg"] * r["posts"] for r in older) / older_posts)
                     if older_posts else 0)
        older_note = (f'<p class="sub">The chart above shows all '
                      f'{len(monthly)} months, back to {esc(older[0]["month"])}. '
                      f'The table below shows the last {REACH_TABLE_MONTHS}. '
                      f'Before {esc(recent[0]["month"])}: {_num(older_posts)} '
                      f'more posts, averaging {_num(older_avg)} views.</p>')

    rows = [[esc(r["month"]), _num(r["posts"]), _num(r["avg"]),
             _num(r["median"]), _num(r["best"])] for r in recent]
    return f"""
<section class="page">
  <h2>Reach and trajectory</h2>
  <p class="sub">{esc(voice.report("reach.sub"))}</p>
  {charts.trend_line(monthly, title="Average views per post, by month")}
  {charts.trend_line(monthly, title="Posts published per month", y_key="posts")}
  {_prose(ctx.get('narrative'), 'reach')}
  {older_note}
  {_table(["Month", "Posts", "Avg views", "Median", "Best"], rows)}
  <footer><span>{esc(attribution.stamp_footer())}</span><span>Reach and trajectory</span></footer>
</section>"""


def _themes(ctx: dict) -> str:
    a = ctx["analysis"]
    t = ctx["themes"]
    rows = a["theme"]
    calls = ctx["theme_calls"]

    table_rows = []
    for r in rows:
        call = calls.get(r["name"], {})
        pill = call.get("call", "test")
        evidence = _v(r["verdict"])
        if r.get("needs"):
            evidence += (f'<br><span class="needs">+{r["needs"]} posts '
                         f'to settle</span>')
        table_rows.append([
            esc(r["name"]), _num(r["n"]), f'{r["share"]}%', _num(r["avg"]),
            _delta(r["delta"]), evidence,
            f'<span class="pill {pill}">{esc(call.get("label", "Test more"))}</span>',
        ])

    method = str(t.get("method") or "")
    method_note = ("Themes are carried over from the previous analysis of this "
                   "account." if method.startswith("reused")
                   else f'Themes were found by {esc(method)}.')
    if t.get("effective_themes"):
        method_note += (f' The feed reads as about <strong>'
                        f'{t["effective_themes"]} distinct styles</strong>.')

    return f"""
<section class="page">
  <h2>What this account is about</h2>
  <p class="sub">{esc(voice.report("themes.sub"))}</p>
  {charts.donut(rows, title="Share of posts by theme")}
  {charts.legend_note()}
  {charts.index_bars(rows, title="Reach by theme, against this account's own average")}
  {_prose(ctx.get('narrative'), 'themes')}
  <p class="sub">{method_note}</p>
  {_table(["Theme", "Posts", "Share", "Avg views", "vs average", "Evidence", "Call"],
          table_rows)}
  <h3>{esc(voice.report("themes.howto"))}</h3>
  <p>{voice.report("themes.calls")
      .replace("<b>Keep</b>", '<span class="pill keep">Keep</span>')
      .replace("<b>Ditch</b>", '<span class="pill ditch">Ditch</span>')
      .replace("<b>Test more</b>", '<span class="pill test">Test more</span>')
      .replace("<b>Try</b>", '<span class="pill replace">Try</span>')}</p>
  <footer><span>{esc(attribution.stamp_footer())}</span><span>Themes</span></footer>
</section>"""


def _hooks(ctx: dict) -> str:
    h = ctx["hooks"]
    rep = h["repetition"]
    feat_rows = [[esc(r["feature"]), _num(r["n_with"]), _num(r["avg_with"]),
                  _num(r["avg_without"]), _delta(r["lift"]), _v(r["verdict"])]
                 for r in h["features"]]

    if rep["templated_posts"]:
        rep_rows = [[esc(f'"{r["opener"]}…"'), _num(r["n"]), _num(r["avg"]),
                     _delta(r["vs_rest"]), _v(r["verdict"])]
                    for r in rep["repeated_openers"]]
        rep_block = _table(["Repeated opener", "Posts", "Avg views", "vs the rest",
                            "Evidence"], rep_rows, left_cols={0})
        rep_note = (f'<p><strong>{rep["templated_posts"]} posts '
                    f'({rep["templated_share"]}%)</strong> open with a phrasing this '
                    f'account has used at least three times. Pooled against everything '
                    f'else, that group is {_v(rep["pooled_verdict"])}.</p>')
    else:
        rep_block = ""
        rep_note = (f'<p>No templated openers found: {rep["distinct_openers"]} distinct '
                    f'openings across {rep["captioned_posts"]} captioned posts. That is '
                    f'a good sign — repeated opening phrasing is one of the most common '
                    f'and least visible drags on reach.</p>')

    hook_items = "".join(
        f'<li>{esc(w["hook"])}<br><span class="m">{_num(w["views"])} views · '
        f'{w["index"]}% of average'
        f'{" · " + esc(readable(w["theme"])) if w["theme"] else ""}</span></li>'
        for w in h["winning_hooks"])

    return f"""
<section class="page">
  <h2>Hooks and captions</h2>
  <p class="sub">{esc(voice.report("hooks.sub"))}</p>
  {_prose(ctx.get('narrative'), 'hooks')}
  <h3>Caption features against reach</h3>
  {_table(["Feature", "Posts with it", "Avg with", "Avg without", "Difference",
           "Evidence"], feat_rows)}
  <p class="sub">{esc(voice.report("hooks.caveat"))}</p>

  <h3>Are the openers templated?</h3>
  {rep_note}
  {rep_block}

  <h3>{esc(voice.report("hooks.winners"))}</h3>
  <p class="sub">{esc(voice.report("hooks.winners.sub"))}</p>
  <ul class="hooklist">{hook_items or "<li>No standout posts yet.</li>"}</ul>
  <footer><span>{esc(attribution.stamp_footer())}</span><span>Hooks</span></footer>
</section>"""


def _timing(ctx: dict) -> str:
    a = ctx["analysis"]
    cad = ctx["cadence"]
    slot = cad["best_slot"]
    cons = cad["consistency"]

    caveat = ("" if slot["day_proven"] else
              " Neither is proven yet — treat them as a guess, not a rule.")
    return f"""
<section class="page">
  <h2>Timing and consistency</h2>
  <p class="sub">{esc(voice.report("timing.sub"))}</p>
  {charts.index_bars(a["weekday"], title="Reach by day of week, against the account average")}
  {charts.index_bars(a["duration"], title="Reach by video length")}
  {_prose(ctx.get('narrative'), 'timing')}

  <h3>Best slot</h3>
  <p>Your strongest day is <strong>{esc(slot['day'] or 'unclear')}</strong>
     (index {slot['day_index'] or '—'}). Your strongest hour is
     <strong>{esc(slot['hour'] or 'unclear')}</strong>
     (index {slot['hour_index'] or '—'}).{esc(caveat)}
     Hours are in this machine's local timezone.</p>

  <h3>Does posting more often help?</h3>
  <p>When this account posted more than its median of
     {cons.get('median_posts', 0):.0f} posts a month, videos averaged
     <strong>{_num(cons.get('busy_avg', 0))}</strong> views. In quieter
     months: <strong>{_num(cons.get('quiet_avg', 0))}</strong>.
     Evidence: {_v(cons['verdict'])}.
     {esc(cons.get('note') or '')}</p>
  <p class="sub">{esc(voice.report("timing.cadence"))}</p>
  <footer><span>{esc(attribution.stamp_footer())}</span><span>Timing</span></footer>
</section>"""


def _audience(ctx: dict) -> str:
    prof = ctx.get("profile_audit")
    peers = ctx.get("peers") or []
    if not prof and not peers:
        return ""

    checks = ""
    if prof and prof.get("checks"):
        items = "".join(
            f'<li class="{"check-pass" if c["pass"] else "check-fix"}">'
            f'<strong>{esc(c["name"])}</strong> — {esc(c["detail"])}'
            + (f'<br><span class="m">{esc(c["fix"])}</span>' if not c["pass"] and c.get("fix") else "")
            + "</li>"
            for c in prof["checks"])
        avatar = ""
        if prof.get("avatar_data_uri"):
            avatar = (f'<p><img src="{prof["avatar_data_uri"]}" width="96" height="96" '
                      f'style="border-radius:50%;vertical-align:middle">'
                      f'<img src="{prof["avatar_data_uri"]}" width="40" height="40" '
                      f'style="border-radius:50%;margin-left:14px;vertical-align:middle">'
                      f'<img src="{prof["avatar_data_uri"]}" width="24" height="24" '
                      f'style="border-radius:50%;margin-left:14px;vertical-align:middle">'
                      f'<br><span class="m">{esc(voice.report("audience.avatar"))}</span></p>')
        checks = f"<h3>Profile audit</h3>{avatar}<ul class='checks'>{items}</ul>"

    peer_block = ""
    if peers:
        rows = [[esc("@" + p["handle"]), _num(p.get("followers")),
                 esc((p.get("bio") or "")[:110])] for p in peers]
        peer_block = ("<h3>How others in this niche describe their audience</h3>"
                      f"<p class='sub'>{esc(voice.report('audience.peers'))}</p>"
                      + _table(["Account", "Followers", "Bio"], rows,
                               left_cols={2}))

    return f"""
<section class="page">
  <h2>Who you are talking to</h2>
  <p class="sub">{esc(voice.report("audience.sub"))}</p>
  {_prose(ctx.get('narrative'), 'audience')}
  {checks}
  {peer_block}
  <footer><span>{esc(attribution.stamp_footer())}</span><span>Audience</span></footer>
</section>"""


def _demand(ctx: dict) -> str:
    research = ctx.get("research") or {}
    coverage = research.get("coverage") or []
    if not coverage:
        return ""
    rows = [[esc(c["source"]),
             ("reached" if c["ok"] else "not reached"),
             esc(c.get("note", ""))] for c in coverage]
    topics = research.get("topics") or []
    topic_rows = [[esc(t["topic"]), _num(t.get("posts")), esc(t.get("evidence", "")[:80])]
                  for t in topics]

    # Real questions people asked in the last 30 days. These are the most
    # directly usable thing on the page - each one is a video someone wants.
    # Filtered through exactly the same test the recommendations use: the
    # research skill returns product launches and link-dumps alongside real
    # questions, and listing those here under "what people are asking" is
    # simply untrue.
    from ..calendar.recommend import is_filmable_question
    asked = [c for c in (research.get("l30_clusters") or [])
             if c.get("title") and is_filmable_question(c["title"])][:6]
    if asked:
        def _sub(c):
            s = (c.get("summary") or "").strip()
            same = s[:60].lower().strip(" .…") == c["title"][:60].lower().strip(" .…")
            return "" if (same or len(s) <= 30) else \
                f'<br><span class="m">{esc(s[:150])}</span>'
        items = "".join(f'<li>{esc(c["title"])}{_sub(c)}</li>' for c in asked)
        questions = ("<h3>What people are actually asking</h3>"
                     f"<p class='sub'>{esc(voice.report('demand.questions.sub'))}</p>"
                     f"<ul class='hooklist'>{items}</ul>")
    elif research.get("l30_clusters"):
        # Say why the list is missing. A section that silently disappears
        # looks like a broken feature; this looks like what it is.
        n = len(research["l30_clusters"])
        questions = ("<h3>What people are actually asking</h3>"
                     f"<p class='sub'>I found {n} discussions in this niche "
                     f"in the last 30 days. None were real questions to "
                     f"film — just launches, promos, and old articles. I "
                     f"didn’t invent anything to fill the gap.</p>")
    else:
        questions = ""
    return f"""
<section class="page">
  <h2>What the niche is talking about</h2>
  <p class="sub">{esc(voice.report("demand.sub"))}</p>
  {_prose(ctx.get('narrative'), 'demand')}
  {_table(["Topic", "Posts seen", "Evidence"], topic_rows,
          left_cols={2}) if topic_rows else ""}
  {questions}
  <h3>{esc(voice.report("demand.coverage"))}</h3>
  <p class="sub">{esc(voice.report("demand.coverage.sub"))}</p>
  {_table(["Source", "Status", "Note"], rows, left_cols={2})}
  <footer><span>{esc(attribution.stamp_footer())}</span><span>Demand signal</span></footer>
</section>"""


def _calendar(ctx: dict) -> str:
    cal = ctx.get("calendar") or {}
    days = cal.get("days") or []
    if not days:
        return ""
    mix = cal.get("mix") or []
    rows = [[
        _num(d["day"]), esc(d["date"]), f'<strong>{esc(d["post_type"])}</strong>',
        esc(d["theme"]), _example_post(d), _v(d["confidence"]),
    ] for d in days]
    return f"""
<section class="page">
  <h2>The next 30 days</h2>
  <p class="sub">{esc(voice.report("calendar.sub"))}</p>
  {charts.donut(mix, title="Post-type mix across the 30 days", value_key="n",
                label_key="name")}
  {_prose(ctx.get('narrative'), 'calendar')}
  {_table(["Day", "Date", "Type", "Theme", "Example post", "Evidence"], rows,
          left_cols={3, 4})}
  <p class="sub">{esc(voice.report("calendar.note"))}</p>
  <footer><span>{esc(attribution.stamp_footer())}</span><span>30-day calendar</span></footer>
</section>"""


def _example_post(d: dict) -> str:
    """A real post to build from, where the account has one on this theme.

    Honesty over invention: a theme with no matching winner falls back to the
    old instruction sentence, but labelled plainly as a fallback rather than
    presented as an equally strong example.
    """
    url, hook = d.get("hook_url"), d.get("hook")
    if url and hook:
        views = d.get("hook_views") or 0
        index = d.get("hook_index") or 100
        return (f'<a href="{esc(url)}">“{esc(texttool.truncate(hook, 90))}”</a>'
                f'<br><span class="m">{_num(views)} views · {index}% of average</span>')
    return f'<span class="m">No example yet — {esc(d["prompt"])}</span>'


def _recommendations(ctx: dict) -> str:
    from ..calendar.recommend import KIND_LABEL
    recs = ctx.get("recommendations") or []
    if not recs:
        return ""
    items = "".join(
        f'<li><div class="h">{esc(r["headline"])}</div>'
        f'<div class="w">{esc(r["why"])}</div>'
        f'<div class="tag">{esc(KIND_LABEL.get(r["kind"], r["kind"]))}'
        f' &nbsp;·&nbsp; from {esc(r["source"])}</div></li>'
        for r in recs)
    return f"""
<section class="page">
  <h2>What to make next</h2>
  <p class="sub">{esc(voice.report("recs.sub"))}</p>
  {_prose(ctx.get('narrative'), 'recommendations')}
  <ol class="recs">{items}</ol>
  <footer><span>{esc(attribution.stamp_footer())}</span><span>What to make next</span></footer>
</section>"""


def _method(ctx: dict) -> str:
    """Method, limits and credits — a compact appendix, not a section.

    Reference material a reader checks once, not a finding. It used to force
    its own page; now it flows onto the tail of whatever page precedes it, so
    it costs the space it actually needs rather than a whole page slot.
    """
    meta = ctx["meta"]
    t = ctx["themes"]
    return f"""
<div class="appendix">
  <h2>Method, limits and credits</h2>
  <p><strong>{esc(voice.report("method.how"))}:</strong>
     {"read via" if not voice.is_plain() else "Read via"}
     <strong>{esc(meta['harvest_tier'])}</strong> — the same public metrics any
     visitor can see. Nothing downloaded, no engagement automated. Themes were
     grouped by {esc(t['method'])}. {voice.report("method.significance")}
     {esc(voice.report("method.timezone"))}</p>
  <p><strong>{esc(voice.report("method.unavailable"))}:</strong>
     {voice.report("method.owner_only")}</p>
  <p class="sub">{esc(attribution.TAG)}</p>
</div>"""


# ==================================================================== assembly

#: The report's own table of contents — the single source of truth both
#: `render()` and `scripts/check_docs.py` build from, so the assembled
#: document and the docs describing it can never silently drift apart the
#: way they did when a section was deleted here but not from README.md and
#: SKILL.md (see that script for the check).
SECTIONS = [
    {"id": "cover", "fn": _cover, "title": "Cover",
     "answers": "Which account, read through which session, when, by what "
                "version — plus the ethical-use notice.", "appendix": False},
    {"id": "at_a_glance", "fn": _at_a_glance, "title": "At a glance",
     "answers": "The shape of the account, and what this report cannot tell "
                "you.", "appendix": False},
    {"id": "recommendations", "fn": _recommendations, "title": "What to make next",
     "answers": "A numbered list of specific things to film, ordered by "
                "evidence.", "appendix": False},
    {"id": "reach", "fn": _reach, "title": "Reach and trajectory",
     "answers": "Where it is heading, month by month.", "appendix": False},
    {"id": "themes", "fn": _themes, "title": "What this account is about",
     "answers": "Themes as a 3D pie, with Keep / Ditch / Test more / Try.",
     "appendix": False},
    {"id": "audience", "fn": _audience, "title": "Who you are talking to",
     "answers": "Profile audit and how peers position themselves.",
     "appendix": False},
    {"id": "hooks", "fn": _hooks, "title": "Hooks and captions",
     "answers": "Which caption features travel; whether openers are "
                "templated.", "appendix": False},
    {"id": "timing", "fn": _timing, "title": "Timing and consistency",
     "answers": "Best day and hour, and whether posting more has helped.",
     "appendix": False},
    {"id": "demand", "fn": _demand, "title": "What the niche is talking about",
     "answers": "Demand signal, and what people are actually asking.",
     "appendix": False},
    {"id": "calendar", "fn": _calendar, "title": "The next 30 days",
     "answers": "The calendar, on the five-day rotation.", "appendix": False},
    {"id": "method", "fn": _method, "title": "Method, limits and credits",
     "answers": "How every number was produced.", "appendix": True},
]


def render(ctx: dict) -> str:
    """Build the whole document. `ctx` is the run bundle; see driver.py."""
    attribution.verify()
    meta = ctx["meta"]
    body = "".join(part for part in
                   (section["fn"](ctx) for section in SECTIONS) if part)

    doc = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TikTok content analysis — @{esc(meta['handle'])}</title>
{attribution.stamp_html_meta()}
<style>{CSS}</style>
</head><body>{body}</body></html>"""

    # Post-condition: the tag must have survived into the artefact itself.
    attribution.assert_stamped(doc, "report HTML")
    return doc


def default_limits() -> list[str]:
    """Stated on every report, because their absence is not evidence of zero."""
    return [
        "Watch time and retention — TikTok shows these only to the account owner.",
        "Traffic sources and how people found each video.",
        "Follower growth over time, and who those followers are.",
        "Anything about videos that were deleted or made private before this run.",
        "Why a post did well. This measures what correlates with reach, which is "
        "not the same as what caused it.",
    ]


def now_stamp() -> str:
    now = datetime.now().astimezone()
    return now.strftime("%d %B %Y at %H:%M %Z").strip()
