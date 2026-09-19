<script setup lang="ts">
import { months, leadMonths, type Company } from '~/data/demo'
import {
  areaPath,
  linePath,
  linearScale,
  paddedDomain,
  type Point,
} from '~/utils/chart'

const props = defineProps<{ company: Company }>()

const series = computed(() => [
  ...props.company.history,
  ...props.company.forecast,
])

const scales = computed(() => ({
  x: linearScale([0, series.value.length - 1], [3.5, 96.5]),
  y: linearScale(paddedDomain(series.value, 0.18), [84, 16]),
}))

const history = computed<Point[]>(() =>
  props.company.history.map((value, index) => [
    scales.value.x(index),
    scales.value.y(value),
  ]),
)

const forecast = computed<Point[]>(() => {
  const start = props.company.history.length
  return [
    history.value[history.value.length - 1]!,
    ...props.company.forecast.map(
      (value, index) =>
        [scales.value.x(start + index), scales.value.y(value)] as Point,
    ),
  ]
})

/* The viewBox is a unit-free 1000×1000 square stretched over the plot, so every
 * normalised percentage below lands on the same spot as the HTML annotations. */
const toBox = (points: Point[]): Point[] =>
  points.map(([x, y]) => [x * 10, y * 10] as Point)

const historyPath = computed(() => linePath(toBox(history.value)))
const historyArea = computed(() => areaPath(toBox(history.value), 1000))
const forecastPath = computed(() => linePath(toBox(forecast.value)))
const thresholdY = computed(() => scales.value.y(70) * 10)

function marker(index: number | null) {
  if (index === null) return null
  const score = props.company.history[index]!
  return {
    month: months[index]!,
    score,
    x: scales.value.x(index),
    y: scales.value.y(score),
  }
}

const detected = computed(() => marker(props.company.detectedAt))
const level = computed(() => marker(props.company.levelAt))
const lead = computed(() => leadMonths(props.company))

const pct = (value: number) => `${value}%`

/* Axis labels sit at the month they name. Spreading them evenly would make the
   drawing lie about where "hoy" is. */
const ticks = computed(() => [
  { label: 'oct 2024', style: { left: '0' } },
  { label: 'sep 2025', style: { left: pct(scales.value.x(11)) }, center: true },
  { label: 'hoy', style: { left: pct(scales.value.x(23)) }, center: true },
])

const description = computed(() => {
  const base = `Score mensual de ${props.company.name} entre octubre de 2024 y septiembre de 2026: ${props.company.history.join(', ')}.`
  if (!detected.value || !level.value) return base
  return `${base} La trayectoria se marcó en ${detected.value.month} con ${detected.value.score} puntos y el nivel no cruzó el umbral de 70 hasta ${level.value.month} con ${level.value.score}: ${lead.value} meses de diferencia.`
})
</script>

<template>
  <figure class="dtx">
    <div class="dtx__plot">
      <svg
        class="dtx__svg"
        viewBox="0 0 1000 1000"
        preserveAspectRatio="none"
        role="img"
        :aria-label="description"
      >
        <defs>
          <linearGradient
            :id="`dtx-fill-${company.id}`"
            x1="0"
            y1="0"
            x2="0"
            y2="1"
          >
            <stop offset="0%" stop-color="var(--live)" stop-opacity=".28" />
            <stop offset="100%" stop-color="var(--live)" stop-opacity="0" />
          </linearGradient>
        </defs>

        <line
          v-for="value in [280, 500, 720]"
          :key="value"
          x1="35"
          :y1="value"
          x2="965"
          :y2="value"
          stroke="var(--grid-line)"
          stroke-width="1"
          vector-effect="non-scaling-stroke"
        />
        <line
          x1="35"
          :y1="thresholdY"
          x2="965"
          :y2="thresholdY"
          stroke="var(--line-strong)"
          stroke-width="1"
          stroke-dasharray="3 6"
          vector-effect="non-scaling-stroke"
        />

        <path
          class="dtx__area"
          :d="historyArea"
          :fill="`url(#dtx-fill-${company.id})`"
        />

        <path
          v-if="detected"
          class="dtx__stem dtx__stem--early"
          :d="`M${detected.x * 10} ${detected.y * 10} L${detected.x * 10} 930`"
          stroke="var(--ahead)"
          stroke-width="1.5"
          stroke-dasharray="4 5"
          fill="none"
          vector-effect="non-scaling-stroke"
        />
        <path
          v-if="level"
          class="dtx__stem dtx__stem--late"
          :d="`M${level.x * 10} ${level.y * 10} L${level.x * 10} 930`"
          stroke="var(--line-strong)"
          stroke-width="1.5"
          fill="none"
          vector-effect="non-scaling-stroke"
        />

        <path
          class="dtx__trace"
          :d="historyPath"
          fill="none"
          stroke="var(--live)"
          stroke-width="2.5"
          stroke-linejoin="round"
          vector-effect="non-scaling-stroke"
        />
        <path
          class="dtx__trace dtx__trace--ahead"
          :d="forecastPath"
          fill="none"
          stroke="var(--ahead)"
          stroke-width="2"
          stroke-dasharray="6 6"
          vector-effect="non-scaling-stroke"
        />
      </svg>

      <template v-if="detected">
        <div
          class="dtx__note dtx__note--early"
          :style="{ left: pct(detected.x) }"
          aria-hidden="true"
        >
          <strong>X-Ray avisó</strong>
          <span>{{ detected.month }} · {{ detected.score }} puntos</span>
        </div>
        <span
          class="dtx__ring"
          :style="{ left: pct(detected.x), top: pct(detected.y) }"
          aria-hidden="true"
        />
      </template>

      <template v-if="level">
        <div
          class="dtx__note dtx__note--late"
          :style="{ top: pct(level.y - 26) }"
          aria-hidden="true"
        >
          <strong>el nivel cruzó 70</strong>
          <span>{{ level.month }} · {{ level.score }} puntos</span>
        </div>
        <span
          class="dtx__dot"
          :style="{ left: pct(level.x), top: pct(level.y) }"
          aria-hidden="true"
        />
      </template>

      <div
        v-if="detected && level"
        class="dtx__measure"
        :style="{ left: pct(detected.x), width: pct(level.x - detected.x) }"
        aria-hidden="true"
      >
        <span class="dtx__measure-bar" />
        <b>{{ lead }} meses de ventaja</b>
      </div>
    </div>

    <div class="dtx__axis" aria-hidden="true">
      <span
        v-for="tick in ticks"
        :key="tick.label"
        :class="{ 'is-centred': tick.center }"
        :style="tick.style"
        >{{ tick.label }}</span
      >
      <span class="dtx__axis-ahead">previsión</span>
    </div>
  </figure>
</template>
