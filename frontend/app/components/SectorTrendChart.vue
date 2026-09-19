<script setup lang="ts">
import { months, type Company } from '~/data/demo'
import { linePath, linearScale, type Point } from '~/utils/chart'

const props = defineProps<{
  company: Company
  /** Mediana del corte, mes a mes. Sin nombres detrás. */
  sector: { history: number[]; forecast: number[] }
  /** Cuántas empresas sostienen esa mediana. */
  peers: number
  /** Score simulado del mock: corre la serie para que acabe donde marca el hero. */
  score?: number
}>()

/* El mock deja simular el score. Desplazamos la serie entera en vez de tocar
 * solo el último mes: así la forma sigue siendo la de la empresa. */
const shift = computed(() => {
  const last = props.company.history[props.company.history.length - 1]
  return props.score == null || last == null ? 0 : props.score - last
})

const mine = computed(() => ({
  history: props.company.history.map((value) => value + shift.value),
  forecast: props.company.forecast.map((value) => value + shift.value),
}))

const span = computed(() =>
  Math.max(
    mine.value.history.length + mine.value.forecast.length,
    props.sector.history.length + props.sector.forecast.length,
  ),
)

/* El eje se ancla a 32 y 70 aunque nadie llegue: si no, las bandas SANO y
 * RIESGO se salen del gráfico y las tintas dejan de significar nada. */
const domain = computed<[number, number]>(() => {
  const values = [
    ...mine.value.history,
    ...mine.value.forecast,
    ...props.sector.history,
    ...props.sector.forecast,
    32,
    70,
  ]
  const low = Math.min(...values)
  const high = Math.max(...values)
  const pad = (high - low) * 0.12 || 6
  return [Math.max(0, low - pad), Math.min(100, high + pad)]
})

const scales = computed(() => ({
  x: linearScale([0, Math.max(1, span.value - 1)], [2.5, 96]),
  y: linearScale(domain.value, [92, 8]),
}))

const toBox = (points: Point[]): Point[] =>
  points.map(([x, y]) => [x * 10, y * 10] as Point)

const trace = (history: number[], forecast: number[]) => {
  const at = (values: number[], offset: number): Point[] =>
    values.map(
      (value, index) =>
        [scales.value.x(offset + index), scales.value.y(value)] as Point,
    )
  const drawn = at(history, 0)
  const head = drawn[drawn.length - 1]
  const ahead = at(forecast, history.length)
  return { history: drawn, forecast: head ? [head, ...ahead] : ahead, head }
}

const you = computed(() => trace(mine.value.history, mine.value.forecast))
const median = computed(() => trace(props.sector.history, props.sector.forecast))

const paths = computed(() => ({
  you: {
    history: linePath(toBox(you.value.history)),
    forecast: linePath(toBox(you.value.forecast)),
  },
  median: {
    history: linePath(toBox(median.value.history)),
    forecast: linePath(toBox(median.value.forecast)),
  },
}))

/* Donde acaba lo medido y empieza lo previsto. */
const today = computed(() => scales.value.x(props.company.history.length - 1))

const clamp = (value: number) => Math.min(100, Math.max(0, value))

const zones = computed(() =>
  [
    { key: 'sano', label: 'SANO ≥ 65', top: 0, bottom: clamp(scales.value.y(65)) },
    {
      key: 'vigilar',
      label: 'VIGILANCIA',
      top: clamp(scales.value.y(65)),
      bottom: clamp(scales.value.y(35)),
    },
    { key: 'riesgo', label: 'RIESGO ≤ 35', top: clamp(scales.value.y(35)), bottom: 100 },
  ]
    .filter((zone) => zone.bottom - zone.top > 2)
    .map((zone) => ({
      ...zone,
      style: { top: `${zone.top}%`, height: `${zone.bottom - zone.top}%` },
    })),
)

/* Cada etiqueta se ancla al mes que nombra: "hoy" tiene que caer sobre la
 * línea que separa lo medido de lo previsto, no a un tercio del ancho. */
const ticks = computed(() => {
  const last = Math.max(0, span.value - 1)
  const today = props.company.history.length - 1
  return [
    { label: 'hace 24 m', at: 0, align: 'start' },
    { label: 'hace 12 m', at: Math.round(today / 2), align: 'center' },
    { label: 'hoy', at: today, align: 'center' },
    { label: '+3 m', at: last, align: 'end' },
  ].map((tick) => ({
    ...tick,
    style: { left: `${scales.value.x(tick.at)}%` },
  }))
})

const now = (values: number[]) => values[values.length - 1] ?? null

const reading = (value: number | null) =>
  value == null ? '—' : value.toLocaleString('es-ES', { maximumFractionDigits: 1 })

const description = computed(() => {
  const mid = now(props.sector.history)
  return (
    `Score de ${props.company.name} mes a mes, de ${months[0]} a ${months[23]}: ` +
    `${mine.value.history.map((v) => Math.round(v)).join(', ')}. ` +
    (mid == null
      ? 'No hay mediana del sector para este corte.'
      : `La mediana de ${props.peers} empresas del sector cierra en ${reading(mid)}.`)
  )
})
</script>

<template>
  <figure class="bench">
    <figcaption class="bench__key">
      <span class="bench__key-item bench__key-item--you">
        <i aria-hidden="true" />
        {{ company.name }}
        <b>{{ reading(now(mine.history)) }}</b>
      </span>
      <span class="bench__key-item bench__key-item--median">
        <i aria-hidden="true" />
        Mediana del sector
        <small>{{ peers }} empresas</small>
        <b>{{ reading(now(sector.history)) }}</b>
      </span>
      <span class="bench__key-note">Trazo discontinuo: previsión a 3 meses</span>
    </figcaption>

    <div class="bench__plot">
      <span
        v-for="zone in zones"
        :key="zone.key"
        class="bench__zone"
        :data-zone="zone.key"
        :style="zone.style"
        aria-hidden="true"
        >{{ zone.label }}</span
      >

      <svg
        class="bench__svg"
        viewBox="0 0 1000 1000"
        preserveAspectRatio="none"
        role="img"
        :aria-label="description"
      >
        <path
          :d="`M${today * 10} 40 L${today * 10} 960`"
          stroke="var(--line-strong)"
          stroke-width="1"
          stroke-dasharray="3 6"
          fill="none"
          vector-effect="non-scaling-stroke"
        />

        <path
          v-if="paths.median.history"
          :d="paths.median.history"
          fill="none"
          stroke="var(--text-dim)"
          stroke-width="2"
          stroke-linejoin="round"
          vector-effect="non-scaling-stroke"
        />
        <path
          v-if="paths.median.forecast"
          :d="paths.median.forecast"
          fill="none"
          stroke="var(--text-dim)"
          stroke-width="2"
          stroke-dasharray="6 6"
          opacity="0.75"
          vector-effect="non-scaling-stroke"
        />

        <path
          :d="paths.you.history"
          fill="none"
          stroke="var(--live)"
          stroke-width="2.6"
          stroke-linejoin="round"
          vector-effect="non-scaling-stroke"
        />
        <path
          :d="paths.you.forecast"
          fill="none"
          stroke="var(--live)"
          stroke-width="2.4"
          stroke-dasharray="6 6"
          opacity="0.6"
          vector-effect="non-scaling-stroke"
        />
      </svg>

      <span
        v-if="median.head"
        class="bench__dot bench__dot--median"
        :style="{ left: `${median.head[0]}%`, top: `${median.head[1]}%` }"
        aria-hidden="true"
      />
      <span
        v-if="you.head"
        class="bench__dot bench__dot--you"
        :style="{ left: `${you.head[0]}%`, top: `${you.head[1]}%` }"
        aria-hidden="true"
      />
    </div>

    <div class="bench__axis" aria-hidden="true">
      <span
        v-for="tick in ticks"
        :key="tick.label"
        :data-align="tick.align"
        :style="tick.style"
        >{{ tick.label }}</span
      >
    </div>
  </figure>
</template>
