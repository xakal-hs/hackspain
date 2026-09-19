<script setup lang="ts">
import { months, type Company } from '~/data/demo'
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
  x: linearScale([0, series.value.length - 1], [7, 97.5]),
  y: linearScale(paddedDomain(series.value, 0.22), [86, 12]),
}))

const toBox = (points: Point[]): Point[] =>
  points.map(([x, y]) => [x * 10, y * 10] as Point)

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

const historyPath = computed(() => linePath(toBox(history.value)))
const historyArea = computed(() => areaPath(toBox(history.value), 1000))
const forecastPath = computed(() => linePath(toBox(forecast.value)))

/** Only the two edges a lender actually acts on. */
const bands = [70, 50]

const detected = computed(() => {
  const index = props.company.detectedAt
  if (index === null) return null
  return {
    month: months[index]!,
    x: scales.value.x(index),
    y: scales.value.y(props.company.history[index]!),
  }
})

const head = computed(() => history.value[history.value.length - 1]!)

/* Each label sits at the month it names, not at an even interval. */
const ticks = computed(() =>
  [0, 8, 16, 23].map((index, position) => ({
    label: months[index]!,
    style: { left: `${scales.value.x(index)}%` },
    center: position > 0,
  })),
)

const description = computed(
  () =>
    `Score de ${props.company.name} mes a mes, de ${months[0]} a ${months[23]}: ` +
    `${props.company.history.join(', ')}. Previsión a tres meses: ${props.company.forecast.join(', ')}.`,
)
</script>

<template>
  <figure class="traj">
    <div class="traj__plot">
      <svg
        class="traj__svg"
        viewBox="0 0 1000 1000"
        preserveAspectRatio="none"
        role="img"
        :aria-label="description"
      >
        <defs>
          <linearGradient
            :id="`traj-${company.id}`"
            x1="0"
            y1="0"
            x2="0"
            y2="1"
          >
            <stop offset="0%" stop-color="var(--live)" stop-opacity=".24" />
            <stop offset="100%" stop-color="var(--live)" stop-opacity="0" />
          </linearGradient>
        </defs>

        <line
          v-for="band in bands"
          :key="band"
          x1="40"
          :y1="scales.y(band) * 10"
          x2="985"
          :y2="scales.y(band) * 10"
          stroke="var(--line-strong)"
          stroke-width="1"
          stroke-dasharray="3 6"
          vector-effect="non-scaling-stroke"
        />

        <path :d="historyArea" :fill="`url(#traj-${company.id})`" />

        <path
          v-if="detected"
          :d="`M${detected.x * 10} ${detected.y * 10} L${detected.x * 10} 940`"
          stroke="var(--ahead)"
          stroke-width="1.5"
          stroke-dasharray="4 5"
          fill="none"
          vector-effect="non-scaling-stroke"
        />

        <path
          :d="historyPath"
          fill="none"
          stroke="var(--live)"
          stroke-width="2.25"
          stroke-linejoin="round"
          vector-effect="non-scaling-stroke"
        />
        <path
          :d="forecastPath"
          fill="none"
          stroke="var(--ahead)"
          stroke-width="2"
          stroke-dasharray="6 6"
          vector-effect="non-scaling-stroke"
        />
      </svg>

      <span
        v-for="band in bands"
        :key="band"
        class="traj__band"
        :style="{ top: `${scales.y(band)}%` }"
        aria-hidden="true"
        >{{ band }}</span
      >

      <span
        class="traj__head"
        :style="{ left: `${head[0]}%`, top: `${head[1]}%` }"
        aria-hidden="true"
      />

      <p
        v-if="detected"
        class="traj__flag"
        :style="{ left: `${detected.x}%` }"
        aria-hidden="true"
      >
        avisamos en {{ detected.month }}
      </p>
    </div>

    <div class="traj__axis" aria-hidden="true">
      <span
        v-for="tick in ticks"
        :key="tick.label"
        :class="{ 'is-centred': tick.center }"
        :style="tick.style"
        >{{ tick.label }}</span
      >
      <span class="traj__axis-ahead">+3 m</span>
    </div>
  </figure>
</template>
