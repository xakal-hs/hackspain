# X-Ray design system

X-Ray reads a company's treasury month by month and says whether to lend, watch
or not lend, with the reason and with how many months of notice. The interface is
an instrument for that reading, not a dashboard of metrics.

The visual language is Embat's own. Everything below — the navy, the action blue,
the four semantic ramps, the radii, the three shadow levels, the header height,
the grid and the type scale — is taken from the tokens published on embat.io and
from the design-taste engine's read of that page, not invented here. What is
X-Ray's is the semantics: which colour means money in, which means the product
knows something early, and which surfaces are chrome. What it deliberately does
not take from the reference is the grid of identical rounded cards.

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

Six base values per theme, in `app/assets/css/tokens.css`. The base is Embat's
deep navy, not a tinted near-black, and light is the default because that is how
their product is read.

| Role | Token | Light | Dark |
|---|---|---|---|
| Canvas | `--canvas` | `#ffffff` | `#050b2c` |
| Panel | `--panel` | `#ffffff` | `#0e1431` |
| Raised panel, active nav | `--panel-raised` | `#f3f4f6` | `#232845` |
| Text | `--text` | `#050b2c` | `#ffffff` |
| Secondary text | `--text-muted` | `#6e707c` | `#afafbb` |
| Hairline | `--line` | `#e8e8ed` | `#373c56` |

Those are Embat's content-primary, background-primary/secondary and
border-primary values, and their inverse ramp for the dark theme. Two of them
move one step for contrast and nothing else: the metadata grey and the warning
ink.

Six accents, each with a single job, plus one held apart. Five of them are
Embat's semantic ramps, used as published:

- `--mint` money in, improvement, lend — their `success`
- `--coral` money out — direction, not risk — their `highlight-info-2`
- `--amber` watch — their `warning`
- `--crimson` risk, do not lend — their `danger`
- `--live` actions, focus, the product's own voice — their `highlight-info`. The
  filled button steps in to `#1a56da`, their inverse highlight-info-medium,
  because white on the brand blue is 4.05:1 and a 16px label has to clear 4.5:1.
- `--ahead` **reserved for what the product knows before it happens**: the
  forecast trace, the anticipation span, the "N months earlier" chip. It is the
  purple from Embat's brand gradient, it appears nowhere else, and anticipation
  always carries a dashed line and hollow node as well as the colour, so the
  meaning survives without it.

Each accent has an `-ink` variant that clears 4.5:1 on that theme's panels and a
`-wash` variant for chip and well fills, taken from the same Embat ramp
(`-light` for the wash, `-dark` for the ink).

The brand gradient — `275deg, #c357ec → #9d4bdd → #415de6` — appears exactly
once in the product, as a 3px rule on the model-metrics panel, which is the one
surface where the subject is X-Ray itself rather than a company. The soft
gradient is used once, as the ground of the access screen. Nothing else wears
them.

## Typography

Embat sets every word in **HafferSQXH**, which is licensed and self-hosted, so
**Inter Tight** stands in at the same weights and rhythm — the closest free
grotesque at that x-height and tightness — and the licensed face is documented
here rather than shipped. It carries navigation, headings, prose, table cells,
chips and the product mocks. **Chivo Mono** is restricted to large numeric
readings — score, cash, days, months of anticipation — set at 32–68px with
`tabular-nums` and tracking at −0.04 to −0.06em, so the figure reads as an
instrument display. The mono is never used for small labels, and no fourth
family is loaded.

The scale is Embat's, mapped onto X-Ray's names: 12 / 14 / 16 / 18px for
`--t-micro` through `--t-lead`, and their three headline clamps (20–28, 24–40,
32–52px) for `--t-h3` through `--t-h1`. `--t-display` sits one step below
headline-1 because the landing headline splits into two clauses that each have
to hold one line beside the rail. Display leading 1.06, prose 1.55, measure
capped at 62 characters.

The landing headline's two clauses are divided by a hairline rule, the same
device as the threshold line in the chart below it: something is crossed.

## Structure

Both the landing page and the cockpit hang off a fixed 232px rail, and **the rail
keeps the navy under both themes**. It is chrome, not content — the same navy as
Embat's own header and footer — so a navy edge frames a white canvas without
competing with it. The landing hero is navy too: Embat opens on navy with the
product screen sitting on it, and that is the one place our page raises its
voice. The dark surface values therefore live in their own `--ink-*` set in
`tokens.css`; the dark theme *is* those values and both the rail and the hero
borrow them, so they cannot drift. Those surfaces re-point the theme tokens
rather than restating colours, so every descendant follows — charts, popovers,
buttons and the focus ring included.

The landing's sections each use a different structural device, because the shape
is part of the argument: ruled rows for the three readings, a ruled grid of small
multiples at one shared scale, one panel split in two for bump-versus-fall on the
one section that changes surface instead of rule, and a definition list for what
the product is worth.

The cockpit is a 12-column grid with deliberately unequal spans (5/4/3 · 12 ·
7/5 · 12; 8/4 in the portfolio view), so it never reads as a tile kit. Radii are
Embat's published set, tied to nesting depth rather than applied uniformly: 12px
panels, 8px cards, 6px rows and controls, 4px buttons, full pill for status. No
drop shadows of our own — their level-1 shadow on light surfaces, a hairline
border everywhere, and nothing on navy, where a 9% black shadow is invisible.

Chips are data keys and status, in sentence case with a dot. Nothing in Embat's
interface is set in tracked capitals, so nothing here is either, and a chip is
never hung above a heading as an eyebrow.

Embat's own perspective carries three internal views — monitor, revenue and
model metrics — where the subject stops being a company in the portfolio and
becomes the product itself. They reuse the cockpit language unchanged, because
the reader is the same person on the same screen; what changes is the noun. Their
recurring device is the **ruled strip**: three or five readings side by side,
divided by a hairline rather than boxed into cards, collapsing to ruled rows when
the column narrows. The model panel is the one surface that keeps the navy under
both themes outside the rail and the hero (`.panel--ink`), for the same reason
they do, and it is where the brand gradient is spent.

## Theme

`data-theme="dark|light"` on `<html>`, both token sets complete. The choice is
kept in the `xray-theme` cookie and read during SSR, so the first byte is already
the right palette and there is no flash. Light is the default, as it is in
Embat's product. The control is a two-position switch — one button, not two
options — so a click anywhere flips the theme. Sun and moon mark the sides; a
sliding thumb says which is current, and the active half is decided by a CSS
attribute selector on the root, so it is correct before any script runs. The
thumb does not slide on first paint, only when the theme actually changes, and it
overshoots a little, like the score crossing a threshold. The glyphs replace
labels because the control sits in a rail where every other line is a
destination; the accessible name still says which is which. It rides on the brand
row, at the far end from the mark and flush with the right edge of the panels
below it, in all three shells — rail, landing index and access screen — because
it is the one header element that does not navigate. Page colour transitions at
120ms. Under `prefers-reduced-motion` both the thumb and the page cut the motion.

Below 900px the rail becomes a 64px sticky top bar, Embat's own header height,
and the grid collapses to one column.

The three Centinela product mocks carry their own palette under `.centinela`,
because they are a different product's interface and `--text` already means
something else at the root. Their values are Embat's too, and they follow the
theme: their status accents are derived from X-Ray's, so a "bien" in the mock is
the same green as a "lend" in the score. Their navy panels are the one surface
that does not theme — a deliberate accent that works on either canvas — so the
ink on them lives in a fixed `--on-navy` ramp rather than borrowing `--card`,
which would go dark and vanish.

## Motion

One orchestrated sequence, on the landing hero, once: the trace draws, the
detection marker lands, the forecast extends, the level marker lands, and the
span between them is measured. Nothing else moves on its own — no scroll-triggered
entrances. Everything else responds to a click: selecting a row, opening the
view switcher, flipping the theme, changing cockpit tabs. Colour transitions on
buttons and links run at Embat's 0.3s (`--dur`); dense cockpit controls stay at
`--dur-fast`, 0.12s, because a table that answers slowly feels broken. The tab
thumb slides with the same overshoot as the theme switch, and the pane settles
from 10px below; neither runs on first paint, only on the change. Under
`prefers-reduced-motion` the hero renders its finished state immediately.

## Accessibility floor

- Every text colour clears 4.5:1 on the surfaces it is used on, in both themes.
- Status combines colour with a word and, for anticipation, with a dash pattern.
- Charts carry a full sentence description in `aria-label` listing the monthly
  values; annotations layered over them are `aria-hidden`.
- Focus is a visible 2px ring on every interactive element; the portfolio row
  selector is a real button with `aria-pressed`.
- Prose is at least 16px; table metadata may drop to 12px.
- Responsive to 390px: the rail becomes a top bar and the grid collapses to one
  column.
