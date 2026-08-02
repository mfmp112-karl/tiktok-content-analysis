# The report's design brief

The brief a design pass should work against. Written down because the
constraints here are unusual enough that reasonable-looking "improvements" tend
to break them.

## What this document is

A **print** artefact. A4, black on near-white, read once, often on paper or as a
PDF on a phone. The HTML twin is a convenience.

Consequences, all of which run against normal web instincts:

- **No hover layer.** Anything that only exists on hover does not exist. Tooltips
  are not an option, so every value a reader needs is directly labelled or in
  the table beside the chart.
- **No dark mode.** A dark surface on paper is a toner bill.
- **No interactivity of any kind.** No JS, no filters, no toggles.
- **Explicit page breaks.** Each section is a `.page` with `break-before: page`,
  and charts carry `break-inside: avoid` so nothing splits across a fold.

## The single most important rule

**Confidence has to be visible in the mark, not just in the caption.**

Most findings on most accounts come back "not enough data yet". A solid bar
reads as a fact no matter what the text next to it says, and a reader skimming
a report will act on the bar.

So: proven findings are **filled solid**; unproven ones are a **pale tint of the
same hue with a full-strength outline**.

This began as a 45-degree hatch, which is the textbook answer for exactly this
job. It was replaced because at print scale the hatch did not render at all —
a chart of entirely unproven bars, which is the *normal* case, came out looking
like an empty frame. An encoding that vanishes at the size it is viewed is not
an encoding. If you revisit this, verify at actual print scale before deciding.

## Colour

Eight categorical hues in **fixed slot order, never cycled**, so an entity keeps
its colour across every chart in the document. Above/below average uses a
diverging pair around a neutral. One axis per chart — never two y-scales.

The palette passes the lightness band, chroma floor, CVD separation and
normal-vision checks. Three hues fall below 3:1 contrast against the surface,
which obliges **visible labels or a table view**. Both are present throughout,
so this is satisfied — but that is a *condition*, not a nicety. Do not remove the
direct labels or the tables.

## Charts

| Form | Used for | Rule |
|---|---|---|
| Donut | Theme mix, post-type mix | Max six slices; the tail folds into "Other". Every slice ≥6% is labelled with its percentage. |
| Diverging bars | Reach by theme, day, length | Indexed to the account's own average = 100. Raw view counts cannot compare buckets of different sizes. |
| Volume bars | Posts per month | Single hue, baseline at zero. |
| Line | Monthly reach | Overall average as a dashed baseline, peak marked, labels only on first/last/peak — never on every point. |

Label gutters are **computed from the longest label**, not fixed. Theme names run
long and a fixed gutter silently clips them off the left edge of the SVG.

## Tone

The report tells someone their work is not yet measurable. That needs care:

- Statistics live on the method page. The front pages say "solid evidence",
  "early signal", "not enough data yet".
- "What this report cannot tell you" is a **section**, not a footnote. Watch time
  and retention are owner-only, and silence about them reads as zero.
- Never call a theme a loser without evidence. Telling someone to stop making
  the thing they are still learning to do, on the strength of nine posts, is the
  worst thing this document could do.
- The cover carries provenance — account, session, timestamp, version — so the
  report is a record rather than an assertion.
