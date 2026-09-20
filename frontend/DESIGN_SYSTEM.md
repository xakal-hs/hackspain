# X-Ray design system

X-Ray reads a company's treasury month by month and says whether to lend, watch
or not lend, with the reason and with how many months of notice. The interface is
an instrument for that reading, not a dashboard of metrics.

The visual language comes from Embat's own product: a deep indigo canvas with
nested panels bordered by a single hairline and no drop shadows, status chips
carrying a coloured dot, and a mint/coral pair for money in and money out. What
it deliberately does not take from that reference is the grid of identical
rounded cards.

## Principles

1. **The decision before the diagnosis.** Every company view answers lend, watch
   or don't lend before it shows a single feature.
2. **Trajectory beside level.** A score without its direction and the month it
   turned is incomplete, so anticipation is a first-class number.
3. **Criticality is not uniform, and it is drawn that way.** In *Qué ha
   cambiado*, bar length is the signal's share of the score move, so a
   collapsing cash runway draws five times the bar of a one-day wobble in
   collection days.
4. **Coverage is not health.** ERP connection, history length and reconciliation
   are neutral observability, labelled as "what we can see".
5. **Plain language always.** "The money left in the account" before liquidity
   runway; "how long they take to get paid" before DSO.
6. **Series are not beautified.** Traces are straight segments between months. A
   smoothed curve would invent months that never happened, and axis labels sit at
   the month they name rather than at even intervals.

## Colour

Six base values per theme, in `app/assets/css/tokens.css`. The base is indigo
with real chroma, not a tinted near-black.

| Role | Token | Dark | Light |
|---|---|---|---|
| Canvas | `--canvas` | `#090c22` | `#f4f5fb` |
| Panel | `--panel` | `#10142f` | `#ffffff` |
| Raised panel, active nav | `--panel-raised` | `#1a1f42` | `#ebeef9` |
| Text | `--text` | `#eef0fb` | `#151833` |
| Secondary text | `--text-muted` | `#9aa0c4` | `#5a6088` |
| Hairline | `--line` | `rgba(190,200,255,.10)` | `#dcdfef` |

Five accents, each with a single job, plus one held apart:

- `--mint` money in, improvement, lend
- `--coral` money out — direction, not risk
- `--amber` watch
- `--crimson` risk, do not lend
- `--live` actions, focus, the product's own voice (`--live-solid` for filled
  buttons, a touch deeper so white labels clear AA)
- `--ahead` **reserved for what the product knows before it happens**: the
  forecast trace, the anticipation span, the "N months earlier" chip. It appears
  nowhere else, and anticipation always carries a dashed line and hollow node as
  well as the colour, so the meaning survives without it.

Each accent has an `-ink` variant that clears 4.5:1 on that theme's panels and a
`-wash` variant for chip and well fills.

## Typography

**Schibsted Grotesk** carries every word: navigation, headings, prose, table
cells, chips. **Chivo Mono** is restricted to large numeric readings — score,
cash, days, months of anticipation — set at 32–68px with `tabular-nums` and
tracking at −0.04 to −0.06em, so the figure reads as an instrument display. The
mono is never used for small labels.

Scale on a 16px base, roughly 1.25 per step: 12.5 / 14 / 16 / 18 / 22 / 28 / 38 /
`--t-h1` / `--t-display`. Display leading 1.06, prose 1.55, measure capped at 62
characters.

The landing headline splits into two clauses divided by a hairline rule, the same
device as the threshold line in the chart below it: something is crossed.
`--t-display` is tuned so each clause holds one line beside the rail.

## Structure

Both the landing page and the cockpit hang off a fixed 232px rail, and **the rail
keeps the dark palette under both themes**. It is chrome, not content: the reader's
eye should fall on the panels that carry the numbers, and a dark edge frames a
light canvas without competing with it. The dark surface values therefore live in
their own `--ink-*` set in `tokens.css`; the dark theme *is* those values and the
rail borrows them, so the two cannot drift. The rail re-points the theme tokens
rather than restating colours, so every descendant follows — popovers, buttons and
the focus ring included.

The landing's
sections each use a different structural device, because the shape is part of the
argument: ruled rows for the three readings, a ruled grid of small multiples at
one shared scale, one panel split in two for bump-versus-fall, and a
definition list for what the product is worth.

The cockpit is a 12-column grid with deliberately unequal spans (5/4/3 · 12 ·
7/5 · 12; 8/4 in the portfolio view), so it never reads as a tile kit. Radii are
tied to nesting depth rather than applied uniformly: 18px for panels, 10px for
rows and controls, full pill for status. No drop shadows anywhere — a 1px border
plus an inset sheen, as in the reference.

Chips are data keys and status, in tracked small capitals with a dot. They are
never hung above a heading as an eyebrow.

Embat's own perspective has three views — caja of the featured portfolio, the
financing CRM and the team — where the subject is the book, not one company
looking at itself. They use the same always-light Embat product chrome as Flujo
and Crédito: a 17px title bar, grouped hairline tables, no cockpit crumb. Caja
opens with a **ruled strip** of three readings (alerta, oportunidad, vigilancia),
divided by a hairline rather than boxed into cards, collapsing to ruled rows when
the column narrows.

## Theme

`data-theme="dark|light"` on `<html>`, both token sets complete. The choice is
kept in the `xray-theme` cookie and read during SSR, so the first byte is already
the right palette and there is no flash. Dark is the default. The control is a
two-position switch — one button, not two options — so a click anywhere flips the
theme. Sun and moon mark the sides; a sliding thumb says which is current, and the
active half is decided by a CSS attribute selector on the root, so it is correct
before any script runs. The thumb does not slide on first paint, only when the
theme actually changes, and it overshoots a little, like the score crossing a
threshold. The glyphs replace labels because the control sits in a rail where
every other line is a destination; the accessible name still says which is which.
It rides on the brand row, at the far end from the mark and flush with the right
edge of the panels below it, in all three shells — rail, landing index and access
screen — because it is the one header element that does not navigate. Page colour
transitions at 120ms. Under `prefers-reduced-motion` both the thumb and the page
cut the motion.

The three Centinela product mocks carry their own palette under `.centinela`,
because they are a different product's interface and `--text` already means
something else at the root. They follow the theme too: their status accents are
derived from X-Ray's, so a "bien" in the mock is the same green as a "lend" in the
score. Their navy panels are the one surface that does not theme — a deliberate
accent that works on either canvas — so the ink on them lives in a fixed
`--on-navy` ramp rather than borrowing `--card`, which would go dark and vanish.

## Motion

One orchestrated sequence, on the landing hero, once: the trace draws, the
detection marker lands, the forecast extends, the level marker lands, and the
span between them is measured. Nothing else moves on its own — no scroll-triggered
entrances. Everything else responds to a click: selecting a row, opening the
view switcher, flipping the theme, changing cockpit tabs. The tab thumb
slides with the same overshoot as the theme switch, and the pane settles
from 10px below; neither runs on first paint, only on the change. Under
`prefers-reduced-motion` the hero renders its finished state immediately.

## Accessibility floor

- Every text colour clears 4.5:1 on the surfaces it is used on, in both themes.
- Status combines colour with a word and, for anticipation, with a dash pattern.
- Charts carry a full sentence description in `aria-label` listing the monthly
  values; annotations layered over them are `aria-hidden`.
- Focus is a visible 2px ring on every interactive element; the portfolio row
  selector is a real button with `aria-pressed`.
- Prose is at least 16px; table metadata may drop to 12.5px.
- Responsive to 390px: the rail becomes a top bar and the grid collapses to one
  column.
