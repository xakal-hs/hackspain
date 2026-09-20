<script setup lang="ts">
import { areaPath, linePath, linearScale, paddedDomain, type Point } from '~/utils/chart'
import type { ChartTone, ChatChart } from '~/utils/chatCharts'

const props = defineProps<{ chart: ChatChart }>()

const TONE: Record<ChartTone, string> = { live: 'var(--live)', mint: 'var(--mint)', crimson: 'var(--crimson)', amber: 'var(--amber)' }
const INK: Record<ChartTone, string> = { live: 'var(--live-ink)', mint: 'var(--mint-ink)', crimson: 'var(--crimson-ink)', amber: 'var(--amber-ink)' }
const uid = useId()
const fmt = (v: number, sign = props.chart.signed) =>
  (sign && v > 0 ? '+' : '') + v.toLocaleString('es-ES', { maximumFractionDigits: 1 })

/* ── Línea: nota mes a mes ── */
const W = 560, H = 210, L = 30, R = 14, T = 16, B = 26
const hover = ref<number | null>(null)
const plot = ref<HTMLElement | null>(null)

const line = computed(() => {
  const items = props.chart.items
  const values = items.map(i => i.value)
  const x = linearScale([0, Math.max(values.length - 1, 1)], [L, W - R])
  const y = linearScale(props.chart.domain ?? paddedDomain(values, 0.18), [H - B, T])
  const points = values.map((v, i) => [x(i), y(v)] as Point)
  const step = Math.max(1, Math.ceil(values.length / 6))
  const total = values.at(-1)! - values[0]!
  return {
    points, path: linePath(points), area: areaPath(points, H - B),
    grid: (props.chart.domain ? [0, 25, 50, 75, 100] : []).map(t => ({ t, y: y(t) })),
    labels: items.map((it, i) => ({ text: it.label, x: x(i), show: i % step === 0 || i === items.length - 1 })).filter(l => l.show),
    total,
    hi: values.indexOf(Math.max(...values)), lo: values.indexOf(Math.min(...values)),
  }
})
const at = computed(() => (hover.value ?? props.chart.items.length - 1))
const tip = computed(() => {
  const i = hover.value
  if (i == null) return null
  const p = line.value.points[i]!
  return { left: `${(p[0] / W) * 100}%`, top: `${(p[1] / H) * 100}%`, item: props.chart.items[i]!, align: p[0] / W > 0.7 ? 'end' : p[0] / W < 0.3 ? 'start' : 'mid' }
})
function move(e: PointerEvent) {
  const box = plot.value?.getBoundingClientRect()
  if (!box?.width) return
  const px = ((e.clientX - box.left) / box.width) * W
  let best = 0, gap = Infinity
  line.value.points.forEach((p, i) => { const d = Math.abs(p[0] - px); if (d < gap) { gap = d; best = i } })
  hover.value = best
}
function keys(e: KeyboardEvent) {
  const n = props.chart.items.length
  const from = hover.value ?? n
  if (e.key === 'ArrowLeft') hover.value = Math.max(0, from - 1)
  else if (e.key === 'ArrowRight') hover.value = Math.min(n - 1, (hover.value ?? -1) + 1)
  else if (e.key === 'Escape') hover.value = null
  else return
  e.preventDefault()
}

/* ── Barras ── */
const bars = computed(() => {
  const vals = props.chart.items.map(i => i.value)
  const [lo, hi] = props.chart.domain ?? [Math.min(0, ...vals), Math.max(0, ...vals)]
  const span = hi - lo || 1
  const zero = ((0 - lo) / span) * 100
  return props.chart.items.map((it) => {
    const a = ((Math.min(it.value, 0) - lo) / span) * 100
    const b = ((Math.max(it.value, 0) - lo) / span) * 100
    return { ...it, left: `${it.value < 0 ? a : zero}%`, width: `${Math.max(Math.abs(b - a), 0.8)}%`, zero: `${zero}%` }
  })
})

/* ── Radar: pilares ── */
const radar = computed(() => {
  const items = props.chart.items
  const [lo, hi] = props.chart.domain ?? [0, 100]
  const C = 110, Rr = 74, n = items.length
  const ang = (i: number) => -Math.PI / 2 + (i * 2 * Math.PI) / n
  const at = (i: number, f: number) => [C + Math.cos(ang(i)) * Rr * f, C + Math.sin(ang(i)) * Rr * f] as Point
  const shape = items.map((it, i) => at(i, Math.min(1, Math.max(0, (it.value - lo) / (hi - lo)))))
  return {
    C, rings: [0.25, 0.5, 0.75, 1].map(f => linePath(items.map((_, i) => at(i, f))) + ' Z'),
    spokes: items.map((_, i) => at(i, 1)),
    shape: linePath(shape) + ' Z', dots: shape,
    labels: items.map((it, i) => {
      const [x, y] = at(i, 1.3)
      return { text: it.label, value: Math.round(it.value), x, y, anchor: x < C - 4 ? 'end' : x > C + 4 ? 'start' : 'middle' }
    }),
  }
})
</script>

<template>
  <figure class="cc" :class="`cc--${chart.kind}`">
    <figcaption>
      <strong>{{ chart.title }}</strong>
      <span v-if="chart.subtitle">{{ chart.subtitle }}</span>
    </figcaption>

    <!-- Cifras clave -->
    <dl v-if="chart.kind === 'stats'" class="cc__stats">
      <div v-for="it in chart.items" :key="it.label" class="cc__stat">
        <dt>{{ it.label }}</dt>
        <dd :style="{ color: INK[it.tone ?? 'live'] }">{{ it.text ?? fmt(it.value) }}</dd>
        <small v-if="it.note"><i :style="{ background: TONE[it.tone ?? 'live'] }" />{{ it.note }}</small>
      </div>
    </dl>

    <!-- Serie mensual -->
    <template v-else-if="chart.kind === 'line'">
      <p class="cc__lead">
        <b :style="{ color: INK[chart.items[at]!.tone ?? 'live'] }">{{ fmt(chart.items[at]!.value, false) }}</b>
        <span>{{ chart.items[at]!.label }}</span>
        <em v-if="hover == null" :class="line.total < 0 ? 'is-down' : 'is-up'">{{ fmt(line.total, true) }} pts en {{ chart.items.length }} meses</em>
      </p>
      <div
        ref="plot" class="cc__plot" tabindex="0" role="img"
        :aria-label="`${chart.title}: ${chart.items.map(i => `${i.label} ${fmt(i.value, false)}`).join(', ')}`"
        @pointermove="move" @pointerleave="hover = null" @keydown="keys" @blur="hover = null"
      >
        <svg :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none" aria-hidden="true">
          <defs>
            <linearGradient :id="`${uid}-a`" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stop-color="var(--live)" stop-opacity="0.28" />
              <stop offset="1" stop-color="var(--live)" stop-opacity="0" />
            </linearGradient>
          </defs>
          <g v-for="g in line.grid" :key="g.t">
            <line :x1="L" :x2="W - R" :y1="g.y" :y2="g.y" stroke="var(--grid-line)" stroke-dasharray="2 4" vector-effect="non-scaling-stroke" />
          </g>
          <path :d="line.area" :fill="`url(#${uid}-a)`" />
          <path :d="line.path" fill="none" stroke="var(--live)" stroke-width="2.25" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke" />
          <line v-if="hover != null" :x1="line.points[hover]![0]" :x2="line.points[hover]![0]" :y1="T" :y2="H - B" stroke="var(--line-strong)" vector-effect="non-scaling-stroke" />
        </svg>
        <span v-for="g in line.grid" :key="g.t" class="cc__ytick" :style="{ top: `${(g.y / H) * 100}%` }">{{ g.t }}</span>
        <span v-for="(l, i) in line.labels" :key="i" class="cc__xtick" :style="{ left: `${(l.x / W) * 100}%` }">{{ l.text }}</span>
        <i
          v-for="(p, i) in line.points" :key="i" class="cc__dot" :class="{ 'is-on': i === at }"
          :style="{ left: `${(p[0] / W) * 100}%`, top: `${(p[1] / H) * 100}%`, background: TONE[chart.items[i]!.tone ?? 'live'] }"
        />
        <div v-if="tip" class="cc__tip" :class="`is-${tip.align}`" :style="{ left: tip.left, top: tip.top }">
          <b>{{ tip.item.label }}</b>{{ fmt(tip.item.value, false) }}
        </div>
      </div>
    </template>

    <!-- Radar -->
    <div v-else-if="chart.kind === 'radar'" class="cc__radar">
      <svg viewBox="-30 -6 280 232" role="img" :aria-label="`${chart.title}: ${chart.items.map(i => `${i.label} ${Math.round(i.value)}`).join(', ')}`">
        <path v-for="(r, i) in radar.rings" :key="i" :d="r" fill="none" stroke="var(--grid-line)" />
        <line v-for="(s, i) in radar.spokes" :key="i" :x1="radar.C" :y1="radar.C" :x2="s[0]" :y2="s[1]" stroke="var(--grid-line)" />
        <path :d="radar.shape" fill="var(--live)" fill-opacity="0.2" stroke="var(--live)" stroke-width="2" stroke-linejoin="round" />
        <circle v-for="(d, i) in radar.dots" :key="i" :cx="d[0]" :cy="d[1]" r="3" fill="var(--live)" />
        <text v-for="(l, i) in radar.labels" :key="i" :x="l.x" :y="l.y" :text-anchor="l.anchor" class="cc__rl">
          <tspan :x="l.x">{{ l.text }}</tspan><tspan :x="l.x" dy="12" class="cc__rv">{{ l.value }}</tspan>
        </text>
      </svg>
    </div>

    <!-- Barras -->
    <ul v-else class="cc__bars">
      <li v-for="(b, i) in bars" :key="i" :title="b.note ? `${b.label} · ${b.note}` : b.label">
        <span class="cc__label">{{ b.label }}</span>
        <span class="cc__track">
          <i v-if="chart.signed" class="cc__zero" :style="{ left: b.zero }" />
          <i class="cc__fill" :style="{ left: b.left, width: b.width, background: TONE[b.tone ?? 'live'] }" />
        </span>
        <span class="cc__val" :style="{ color: chart.signed ? INK[b.tone ?? 'live'] : undefined }">{{ fmt(b.value) }}{{ chart.unit && chart.unit !== 'pts' ? chart.unit : '' }}</span>
      </li>
    </ul>
  </figure>
</template>

<style scoped>
.cc {
  margin: 0; padding: 18px 24px 22px; background: var(--panel); border-bottom: 1px solid var(--line);
  animation: cc-in 0.45s cubic-bezier(0.22, 1, 0.36, 1) both; animation-delay: calc(var(--i, 0) * 70ms);
}
@keyframes cc-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { .cc { animation: none; } }
.cc figcaption { display: flex; flex-direction: column; gap: 3px; margin-bottom: 14px; }
.cc figcaption strong { font-size: 0.86rem; font-weight: 600; }
.cc figcaption span { font-size: 0.74rem; color: var(--text-muted); }

/* cifras */
.cc__stats { margin: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; }
.cc__stat { display: flex; flex-direction: column; gap: 4px; padding: 12px 14px; border-radius: 10px; background: var(--panel-sunken); border: 1px solid var(--line); min-width: 0; }
.cc__stat dt { font-size: 0.7rem; letter-spacing: 0.04em; text-transform: uppercase; color: var(--text-muted); }
.cc__stat dd { margin: 0; font: 600 1.55rem/1.1 var(--font-num); overflow-wrap: anywhere; }
.cc__stat small { display: inline-flex; align-items: center; gap: 6px; font-size: 0.72rem; color: var(--text-muted); text-transform: capitalize; }
.cc__stat small i { width: 6px; height: 6px; border-radius: 50%; flex: none; }

/* línea */
.cc__lead { margin: -4px 0 8px; display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.cc__lead b { font: 600 1.7rem/1 var(--font-num); }
.cc__lead span { font-size: 0.78rem; color: var(--text-muted); }
.cc__lead em { margin-left: auto; font: normal 0.74rem var(--font-num); padding: 2px 8px; border-radius: 999px; }
.cc__lead em.is-up { color: var(--mint-ink); background: var(--mint-wash); }
.cc__lead em.is-down { color: var(--crimson-ink); background: var(--crimson-wash); }
.cc__plot { position: relative; aspect-ratio: 560 / 210; cursor: crosshair; outline: none; touch-action: pan-y; }
.cc__plot:focus-visible { outline: 2px solid var(--focus-ring); outline-offset: 4px; border-radius: 6px; }
.cc__plot svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.cc__ytick { position: absolute; left: 0; transform: translateY(-50%); font: 10px var(--font-num); color: var(--text-dim); }
.cc__xtick { position: absolute; bottom: 0; transform: translateX(-50%); font: 10px var(--font-num); color: var(--text-dim); white-space: nowrap; }
.cc__dot {
  position: absolute; width: 7px; height: 7px; margin: -3.5px 0 0 -3.5px; border-radius: 50%; pointer-events: none;
  box-shadow: 0 0 0 2px var(--panel); transition: transform 0.12s ease;
}
.cc__dot.is-on { transform: scale(1.5); }
.cc__tip {
  position: absolute; pointer-events: none; transform: translate(-50%, calc(-100% - 12px)); padding: 6px 10px; border-radius: 8px;
  background: var(--panel-raised); border: 1px solid var(--line-strong); box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
  font: 600 0.82rem var(--font-num); white-space: nowrap; display: flex; gap: 8px; align-items: baseline;
}
.cc__tip b { font: 0.7rem var(--font-ui); font-weight: 500; color: var(--text-muted); }
.cc__tip.is-end { transform: translate(-100%, calc(-100% - 12px)); }
.cc__tip.is-start { transform: translate(0, calc(-100% - 12px)); }

/* radar */
.cc__radar svg { display: block; width: 100%; max-width: 380px; margin: 0 auto; height: auto; }
.cc__rl { font: 500 10px var(--font-ui); fill: var(--text-muted); }
.cc__rv { font: 600 11px var(--font-num); fill: var(--text); }

/* barras */
.cc__bars { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.cc__bars li { display: grid; grid-template-columns: minmax(96px, 36%) 1fr 52px; gap: 12px; align-items: center; padding: 5px 6px; margin: 0 -6px; border-radius: 6px; font-size: 0.78rem; transition: background 0.12s ease; }
.cc__bars li:hover { background: var(--neutral-wash); }
.cc__label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-muted); }
.cc__bars li:hover .cc__label { color: var(--text); }
.cc__track { position: relative; height: 8px; border-radius: 4px; background: var(--neutral-wash); }
.cc__fill { position: absolute; top: 0; bottom: 0; border-radius: 4px; animation: cc-grow 0.6s cubic-bezier(0.22, 1, 0.36, 1) both; transform-origin: left; }
@keyframes cc-grow { from { transform: scaleX(0); } }
.cc__zero { position: absolute; top: -3px; bottom: -3px; width: 1px; background: var(--line-strong); }
.cc__val { font: 0.78rem var(--font-num); text-align: right; }
</style>
