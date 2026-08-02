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

from .. import attribution
from ..stats import plain
from . import charts
from .charts import esc

CSS = """
:root {
  --ink: #0B0B0B; --soft: #52514E; --muted: #7A7973;
  --rule: #E5E4E0; --surface: #FCFCFB; --band: #F4F6F9;
  --pos: #2A78D6; --neg: #D03B3B; --good: #0CA30C; --warn: #B07800;
}
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  margin: 0; background: var(--surface); color: var(--ink);
  font: 400 13px/1.55 "Segoe UI", -apple-system, "Helvetica Neue", Arial, sans-serif;
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

h1 { font-size: 30px; line-height: 1.15; margin: 0 0 6px; letter-spacing: -0.4px; }
h2 { font-size: 17px; margin: 0 0 3px; letter-spacing: -0.2px; }
h3 { font-size: 13px; margin: 18px 0 6px; text-transform: uppercase;
     letter-spacing: 0.6px; color: var(--soft); }
p  { margin: 0 0 9px; max-width: 68ch; }
.sub { color: var(--soft); margin: 0 0 16px; font-size: 13px; }
.lede { font-size: 14.5px; line-height: 1.6; }

.rule { height: 1px; background: var(--rule); margin: 14px 0 16px; border: 0; }

/* cover ------------------------------------------------------------------ */
.cover { padding-top: 8mm; }
.cover h1 { font-size: 38px; }
.provenance { border: 1px solid var(--rule); border-radius: 6px; padding: 14px 16px;
  margin: 20px 0; background: var(--band); }
.provenance dl { display: grid; grid-template-columns: max-content 1fr;
  gap: 5px 18px; margin: 0; font-size: 12.5px; }
.provenance dt { color: var(--soft); }
.provenance dd { margin: 0; font-weight: 600; }
.notice { border-left: 3px solid var(--warn); padding: 10px 0 10px 13px;
  margin: 18px 0; font-size: 12.5px; color: var(--soft); }
.notice strong { color: var(--ink); }

/* KPI row ---------------------------------------------------------------- */
.tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;
  margin: 14px 0 18px; }
.tile { border: 1px solid var(--rule); border-radius: 6px; padding: 11px 12px; }
.tile .k { font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.6px;
  color: var(--muted); margin-bottom: 3px; }
.tile .v { font-size: 21px; font-weight: 700; line-height: 1.1;
  font-variant-numeric: tabular-nums; }
.tile .n { font-size: 11px; color: var(--soft); margin-top: 2px; }

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

.checks li { margin-bottom: 7px; }
.check-pass::marker { content: "PASS  "; }
.check-fix::marker  { content: "FIX  "; }
.hooklist { margin: 0; padding-left: 18px; }
.hooklist li { margin-bottom: 5px; }
.hooklist .m { color: var(--muted); font-size: 11px; }

footer { margin-top: 10mm; padding-top: 8px; border-top: 1px solid var(--rule);
  font-size: 10.5px; color: var(--muted); display: flex;
  justify-content: space-between; gap: 12px; }
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

    return f"""
<section class="page cover">
  <h1>TikTok content analysis</h1>
  <p class="sub">A read of what this account has actually published, and a
     30-day plan built from it.</p>

  <div class="provenance">
    <dl>
      <dt>Account analysed</dt><dd>@{esc(meta['handle'])}</dd>
      <dt>Posts examined</dt><dd>{_num(k.get('n', 0))}{f" &nbsp;·&nbsp; {esc(span)}" if span else ""}</dd>
      <dt>Followers</dt><dd>{_num(followers) if followers else "not captured"}</dd>
      <dt>Accessed via</dt><dd>{esc(meta['accessed_via'])}</dd>
      <dt>Data source</dt><dd>{esc(meta['harvest_tier'])}</dd>
      <dt>Generated</dt><dd>{esc(meta['generated'])}</dd>
      <dt>Tool version</dt><dd>{esc(meta['version'])}</dd>
    </dl>
  </div>

  <div class="notice">
    <strong>What this is for.</strong> This was built to help people grow their
    accounts meaningfully — by understanding what they have already published and
    deciding what to make next. It reads public data only, takes nothing that
    TikTok does not show any logged-out visitor, and automates no engagement of
    any kind. Please do not use it to harass, impersonate, or target anyone.
  </div>

  <hr class="rule">
  {_prose(ctx.get('narrative'), 'summary',
          "The pages that follow move from what this account is, to what has "
          "worked, to what to post next. Every finding carries a note on how "
          "much evidence sits behind it — read those as carefully as the numbers.")}

  <footer><span>{esc(attribution.stamp_footer())}</span>
          <span>@{esc(meta['handle'])} &nbsp;·&nbsp; {esc(meta['generated'])}</span></footer>
</section>"""


def _at_a_glance(ctx: dict) -> str:
    k = ctx["analysis"]["kpi"]
    cad = ctx["cadence"]
    limits = ctx.get("limits", [])
    tiles = [
        ("Posts", _num(k.get("n", 0)), f"{k.get('per_week', 0)} per week"),
        ("Total views", _num(k.get("total_views", 0)), f"best post {_num(k.get('best', 0))}"),
        ("Average views", _num(k.get("avg", 0)), f"median {_num(k.get('median', 0))}"),
        ("Like rate", f"{k.get('like_rate', 0)}%",
         f"comments {k.get('comment_rate', 0)}%"),
    ]
    tile_html = "".join(
        f'<div class="tile"><div class="k">{esc(a)}</div>'
        f'<div class="v">{b}</div><div class="n">{esc(c)}</div></div>'
        for a, b, c in tiles)

    limit_items = "".join(f"<li>{esc(x)}</li>" for x in limits)
    return f"""
<section class="page">
  <h2>At a glance</h2>
  <p class="sub">The shape of the account before any interpretation.</p>
  <div class="tiles">{tile_html}</div>
  {_prose(ctx.get('narrative'), 'glance')}

  <h3>Posting rhythm</h3>
  <p>Currently posting about <strong>{cad['rhythm']['recent_per_week']} times a week</strong>
     ({esc(cad['rhythm']['trend'])} against a lifetime rate of
     {cad['rhythm']['per_week']}). Longest run of consecutive days:
     <strong>{cad['gaps']['longest_streak']}</strong>. Longest silence:
     <strong>{cad['gaps']['longest_gap']} days</strong>.</p>

  <h3>What this report cannot tell you</h3>
  <ul>{limit_items}</ul>

  <footer><span>{esc(attribution.stamp_footer())}</span><span>At a glance</span></footer>
</section>"""


def _reach(ctx: dict) -> str:
    a = ctx["analysis"]
    monthly = a["monthly"]
    rows = [[esc(r["month"]), _num(r["posts"]), _num(r["avg"]),
             _num(r["median"]), _num(r["best"])] for r in monthly]
    return f"""
<section class="page">
  <h2>Reach and trajectory</h2>
  <p class="sub">Where the account is heading, month by month.</p>
  {charts.trend_line(monthly, title="Average views per post, by month")}
  {charts.volume_bars(monthly, title="Posts published per month",
                      label_key="month", value_key="posts")}
  {_prose(ctx.get('narrative'), 'reach')}
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
        table_rows.append([
            esc(r["name"]), _num(r["n"]), f'{r["share"]}%', _num(r["avg"]),
            _delta(r["delta"]), _v(r["verdict"]),
            f'<span class="pill {pill}">{esc(call.get("label", "Test more"))}</span>',
        ])

    method_note = (f'Themes were found by {esc(t["method"])}.'
                   + (f' The feed reads as about <strong>{t["effective_themes"]} '
                      f'distinct styles</strong>.' if t.get("effective_themes") else ""))

    return f"""
<section class="page">
  <h2>What this account is about</h2>
  <p class="sub">Themes discovered from the captions themselves, not chosen in advance.</p>
  {charts.donut(rows, title="Share of posts by theme")}
  {charts.legend_note()}
  {charts.index_bars(rows, title="Reach by theme, against this account's own average")}
  {_prose(ctx.get('narrative'), 'themes')}
  <p class="sub">{method_note}</p>
  {_table(["Theme", "Posts", "Share", "Avg views", "vs average", "Evidence", "Call"],
          table_rows)}
  <h3>How to read the call</h3>
  <p><span class="pill keep">Keep</span> beats the account average with evidence behind it.
     <span class="pill ditch">Ditch</span> trails the average with evidence behind it.
     <span class="pill test">Test more</span> looks promising or poor but rests on too
     few posts to judge — the honest answer for most themes on most accounts.
     <span class="pill replace">Try</span> is a theme with outside demand that this
     account has not covered yet.</p>
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
                            "Evidence"], rep_rows)
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
        f'{w["index"]}% of average{" · " + esc(w["theme"]) if w["theme"] else ""}</span></li>'
        for w in h["winning_hooks"])

    return f"""
<section class="page">
  <h2>Hooks and captions</h2>
  <p class="sub">What the opening line does, and whether it shows up in the numbers.</p>
  {_prose(ctx.get('narrative'), 'hooks')}
  <h3>Caption features against reach</h3>
  {_table(["Feature", "Posts with it", "Avg with", "Avg without", "Difference",
           "Evidence"], feat_rows)}
  <p class="sub">These features overlap with each other and with the mood the
     creator was in. A result here says the gap is real, not that the feature
     caused it.</p>

  <h3>Are the openers templated?</h3>
  {rep_note}
  {rep_block}

  <h3>Openings that worked on this account</h3>
  <p class="sub">Taken from posts that beat the account average, so the voice is
     already the creator's own.</p>
  <ul class="hooklist">{hook_items or "<li>No standout posts yet.</li>"}</ul>
  <footer><span>{esc(attribution.stamp_footer())}</span><span>Hooks</span></footer>
</section>"""


def _timing(ctx: dict) -> str:
    a = ctx["analysis"]
    cad = ctx["cadence"]
    slot = cad["best_slot"]
    cons = cad["consistency"]

    caveat = ("" if slot["day_proven"] else
              " Neither is proven yet — treat them as the best available guess "
              "rather than a rule.")
    return f"""
<section class="page">
  <h2>Timing and consistency</h2>
  <p class="sub">When this account posts, and whether it matters.</p>
  {charts.index_bars(a["weekday"], title="Reach by day of week, against the account average")}
  {charts.index_bars(a["duration"], title="Reach by video length")}
  {_prose(ctx.get('narrative'), 'timing')}

  <h3>Best slot</h3>
  <p>The strongest day is <strong>{esc(slot['day'] or 'unclear')}</strong>
     (index {slot['day_index'] or '—'}) and the strongest hour is
     <strong>{esc(slot['hour'] or 'unclear')}</strong>
     (index {slot['hour_index'] or '—'}).{esc(caveat)}
     Hours are in this machine's local timezone.</p>

  <h3>Does posting more often help?</h3>
  <p>In months where this account posted more than its median of
     {cons.get('median_posts', 0):.0f} posts, videos averaged
     <strong>{_num(cons.get('busy_avg', 0))}</strong> views, against
     <strong>{_num(cons.get('quiet_avg', 0))}</strong> in quieter months.
     Evidence: {_v(cons['verdict'])}.
     {esc(cons.get('note') or '')}</p>
  <p class="sub">"Post daily" is good advice in general. This is whether it has
     shown up in this account's own numbers so far.</p>
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
                      f'<br><span class="m">Your picture at profile size, at comment size, '
                      f'and at the size it appears in a busy feed.</span></p>')
        checks = f"<h3>Profile audit</h3>{avatar}<ul class='checks'>{items}</ul>"

    peer_block = ""
    if peers:
        rows = [[esc("@" + p["handle"]), _num(p.get("followers")),
                 esc((p.get("bio") or "")[:110])] for p in peers]
        peer_block = ("<h3>How others in this niche describe their audience</h3>"
                      "<p class='sub'>Read these as competitive intelligence on "
                      "positioning: who they say they are for, and what they promise.</p>"
                      + _table(["Account", "Followers", "Bio"], rows,
                               left_cols={2}))

    return f"""
<section class="page">
  <h2>Who you are talking to</h2>
  <p class="sub">The profile a visitor lands on, and how peers in this niche
     position themselves.</p>
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
    return f"""
<section class="page">
  <h2>What the niche is talking about</h2>
  <p class="sub">Outside demand signal, gathered at the time of this run.</p>
  {_prose(ctx.get('narrative'), 'demand')}
  {_table(["Topic", "Posts seen", "Evidence"], topic_rows) if topic_rows else ""}
  <h3>Which sources were reachable</h3>
  <p class="sub">A partial pull is not the whole picture, so this states plainly
     what was and was not consulted.</p>
  {_table(["Source", "Status", "Note"], rows)}
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
        esc(d["theme"]), esc(d["prompt"]), _v(d["confidence"]),
    ] for d in days]
    return f"""
<section class="page">
  <h2>The next 30 days</h2>
  <p class="sub">A day-by-day plan built from this account's own strongest themes
     and openings, on a five-day rotation.</p>
  {charts.donut(mix, title="Post-type mix across the 30 days", value_key="n",
                label_key="name")}
  {_prose(ctx.get('narrative'), 'calendar')}
  {_table(["Day", "Date", "Type", "Theme", "Prompt", "Evidence"], rows)}
  <p class="sub">The same calendar is in the accompanying spreadsheet, with
     columns for your caption, platform and whether you posted.</p>
  <footer><span>{esc(attribution.stamp_footer())}</span><span>30-day calendar</span></footer>
</section>"""


def _method(ctx: dict) -> str:
    meta = ctx["meta"]
    t = ctx["themes"]
    credits = "".join(f"<li>{esc(line)}</li>" for line in attribution.credit_lines())
    return f"""
<section class="page">
  <h2>Method, limits and credits</h2>

  <h3>How the numbers were produced</h3>
  <p>The catalogue was read via <strong>{esc(meta['harvest_tier'])}</strong>, which
     returns the same public metrics any visitor can see: views, likes, comments,
     shares, caption, duration and upload time. Nothing was downloaded and no
     engagement was automated.</p>
  <p>Themes were found by {esc(t['method'])}. Where a number of themes fit about
     equally well, the simpler split was taken, because a feed shattered into
     twelve themes is not something anyone can act on.</p>
  <p>Every comparison is tested with Welch's t-test on log-transformed views.
     View counts are heavily skewed, so one viral post can otherwise carry a whole
     bucket. Groups under eight posts are never called significant, however large
     the gap looks. "Solid evidence" means p &lt; 0.01; "early signal" means
     p &lt; 0.05; anything else is reported as not enough data yet.</p>
  <p>Upload times are converted in this machine's local timezone, so
     "best hour" is in your clock, not UTC.</p>

  <h3>What is genuinely unavailable</h3>
  <p>Watch time, retention curves, traffic sources, follower growth over time and
     audience demographics are served by TikTok <strong>only to the account
     owner</strong>, inside their own analytics. No tool can obtain them for an
     account it does not own. Where creator advice depends on those numbers, this
     report tests what it can measure instead and says so rather than inventing a
     proxy.</p>

  <h3>Credits</h3>
  <ul>{credits}</ul>
  <p class="sub">{esc(attribution.TAG)}</p>
  <footer><span>{esc(attribution.stamp_footer())}</span><span>Method</span></footer>
</section>"""


# ==================================================================== assembly

def render(ctx: dict) -> str:
    """Build the whole document. `ctx` is the run bundle; see driver.py."""
    attribution.verify()
    meta = ctx["meta"]
    body = "".join(part for part in [
        _cover(ctx),
        _at_a_glance(ctx),
        _reach(ctx),
        _themes(ctx),
        _audience(ctx),
        _hooks(ctx),
        _timing(ctx),
        _demand(ctx),
        _calendar(ctx),
        _method(ctx),
    ] if part)

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
