<script setup lang="ts">
import { months } from '~/data/demo'
import { linePath, linearScale, type Point } from '~/utils/chart'
import type { TipRow } from './ChartTip.vue'

export interface Trace {
  key: string
  label: string
  /** Apostilla pequeña en la leyenda: "4 empresas", "previsión h3". */
  note?: string
  history: number[]
  forecast: number[]
  /** `live` es la serie protagonista; `muted`, la referencia contra la que se lee. */
  tone?: 'live' | 'muted'
}

const props = withDefaults(
  defineProps<{
    traces: Trace[]
    monthLabels?: string[]
    /** Mes en el que el producto avisó, cuando lo hubo. */
    marker?: { index: number; label: string } | null
    /** Frase de la derecha de la leyenda. */
    note?: string
    /** Descripción de la gráfica para quien no la ve. */
    caption: string
  }>(),
  { marker: null, note: 'Trazo discontinuo: previsión a 3 meses' },
)

const lead = computed(() => props.traces[0])

const valuesOf = (trace: Trace) => [...trace.history, ...trace.forecast]

const span = computed(() =>
  Math.max(1, ...props.traces.map((trace) => valuesOf(trace).length)),
)

/** Dónde acaba lo medido y empieza lo previsto. */
const measured = computed(() => lead.value?.history.length ?? 0)

/* El eje se ancla a 32 y 70 aunque nadie llegue: si no, las bandas SANO y
 * RIESGO se salen del gráfico y las tintas dejan de significar nada. */
const domain = computed<[number, number]>(() => {
  const values = [...props.traces.flatMap(valuesOf), 32, 70]
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

const drawn = computed(() =>
  props.traces.map((trace) => {
    const at = (values: number[], offset: number): Point[] =>
      values.map(
        (value, index) =>
          [scales.value.x(offset + index), scales.value.y(value)] as Point,
      )
    const history = at(trace.history, 0)
    const head = history[history.length - 1]
    const ahead = at(trace.forecast, trace.history.length)
    return {
      key: trace.key,
      tone: trace.tone ?? 'live',
      head,
      history: linePath(toBox(history)),
      forecast: linePath(toBox(head ? [head, ...ahead] : ahead)),
    }
  }),
)

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
  const today = Math.max(0, measured.value - 1)
  if (props.monthLabels?.length) {
    return [...new Set([0, Math.round(today / 2), today])].map(at => ({
      label: props.monthLabels![at]!, at, align: at === 0 ? 'start' : at === today ? 'end' : 'center',
      style: { left: `${scales.value.x(at)}%` },
    }))
  }
  return [
    { label: `hace ${measured.value} m`, at: 0, align: 'start' },
    { label: `hace ${Math.round(measured.value / 2)} m`, at: Math.round(today / 2), align: 'center' },
    { label: 'hoy', at: today, align: 'center' },
    { label: `+${span.value - measured.value} m`, at: span.value - 1, align: 'end' },
  ].map((tick) => ({ ...tick, style: { left: `${scales.value.x(tick.at)}%` } }))
})

const reading = (value: number | null | undefined) =>
  value == null ? '—' : value.toLocaleString('es-ES', { maximumFractionDigits: 1 })

const now = (trace: Trace) => trace.history[trace.history.length - 1] ?? null

const markerAt = computed(() =>
  props.marker && props.marker.index < measured.value
    ? {
        label: props.marker.label,
        x: scales.value.x(props.marker.index),
        y: scales.value.y(lead.value?.history[props.marker.index] ?? 0),
      }
    : null,
)

const { plot, active, track, clear, keys } = useChartHover(span, (index) =>
  scales.value.x(index),
)

/** El mes que nombra el índice: los reales por su nombre, los previstos por
 *  su distancia a hoy. */
const monthAt = (index: number) => {
  if (index >= measured.value) return `+${index - measured.value + 1} m · previsión`
  if (props.monthLabels?.[index]) return props.monthLabels[index]!
  const offset = months.length - measured.value
  return months[offset + index] ?? `mes ${index + 1}`
}

const cursor = computed(() => {
  const index = active.value
  if (index == null) return null

  const points = props.traces.map((trace) => {
    const value = valuesOf(trace)[index]
    return {
      key: trace.key,
      label: trace.label,
      tone: trace.tone ?? 'live',
      value: value ?? null,
      style:
        value == null
          ? null
          : {
              left: `${scales.value.x(index)}%`,
              top: `${scales.value.y(value)}%`,
            },
    }
  })

  const rows: TipRow[] = points.map((point) => ({
    key: point.key,
    label: point.label,
    value: reading(point.value),
    tone: point.tone as TipRow['tone'],
  }))

  /* Con dos líneas lo que se viene a mirar es la distancia entre ellas. */
  const [mine, other] = points
  if (mine?.value != null && other?.value != null) {
    const delta = Math.round((mine.value - other.value) * 10) / 10
    rows.push({
      key: 'gap',
      label: 'Diferencia',
      value: `${delta > 0 ? '+' : delta < 0 ? '−' : ''}${Math.abs(delta).toLocaleString('es-ES', { maximumFractionDigits: 1 })}`,
      dir: delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat',
    })
  }

  /* El globo se apoya en la mitad donde queda más aire por encima o por
   * debajo de las líneas, que con dos series no siempre es la de arriba. */
  const heights = points
    .map((point) => (point.value == null ? null : scales.value.y(point.value)))
    .filter((height): height is number => height != null)
  const above = heights.length ? Math.min(...heights) : 100
  const below = heights.length ? 100 - Math.max(...heights) : 0

  return {
    x: scales.value.x(index),
    title: monthAt(index),
    place: below > above ? ('bottom' as const) : ('top' as const),
    points,
    rows,
    ahead: index >= measured.value,
  }
})

const description = computed(() => {
  const series = props.traces
    .map((trace) => `${trace.label} cierra en ${reading(now(trace))}`)
    .join('; ')
  return `${props.caption} ${series}.`
})

/* La gráfica se dibuja de izquierda a derecha al entrar, una sola vez. La clase
 * se retira cuando termina para que volver a pintar los puntos —al salir el
 * puntero del plot— no relance nada. Va por reloj y no por `animationend`
 * porque el barrido puede no llegar a correr si la pestaña está en segundo
 * plano, y entonces la clase se quedaría puesta. */
const entering = ref(true)
onMounted(() => {
  const done = setTimeout(() => { entering.value = false }, 1700)
  onScopeDispose(() => clearTimeout(done))
})

/** La misma lectura del globo, en texto, para lectores de pantalla. */
const spoken = computed(() =>
  cursor.value
    ? `${cursor.value.title}. ${cursor.value.rows
        .map((row) => `${row.label}: ${row.value}`)
        .join('. ')}`
    : '',
)
</script>

<template>
  <figure class="bench" :class="{ 'bench--entering': entering }">
    <figcaption class="bench__key">
      <span
        v-for="trace in traces"
        :key="trace.key"
        class="bench__key-item"
        :data-tone="trace.tone ?? 'live'"
      >
        <i aria-hidden="true" />
        {{ trace.label }}
        <small v-if="trace.note">{{ trace.note }}</small>
        <b>{{ reading(now(trace)) }}</b>
      </span>
      <span class="bench__key-note">{{ note }}</span>
    </figcaption>

    <div
      ref="plot"
      class="bench__plot"
      tabindex="0"
      role="img"
      :aria-label="description"
      @pointermove="track"
      @pointerdown="track"
      @pointerleave="clear"
      @pointercancel="clear"
      @blur="clear"
      @keydown="keys"
    >
      <span
        v-for="zone in zones"
        :key="zone.key"
        class="bench__zone"
        :data-zone="zone.key"
        :style="zone.style"
        aria-hidden="true"
        >{{ zone.label }}</span
      >

      <svg class="bench__svg" viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-hidden="true">
        <path
          :d="`M${scales.x(measured - 1) * 10} 40 L${scales.x(measured - 1) * 10} 960`"
          stroke="var(--line-strong)"
          stroke-width="1"
          stroke-dasharray="3 6"
          fill="none"
          vector-effect="non-scaling-stroke"
        />

        <path
          v-if="markerAt"
          :d="`M${markerAt.x * 10} ${markerAt.y * 10} L${markerAt.x * 10} 940`"
          stroke="var(--ahead)"
          stroke-width="1.5"
          stroke-dasharray="4 5"
          fill="none"
          vector-effect="non-scaling-stroke"
        />

        <!-- La referencia se dibuja primero para que la protagonista quede encima. -->
        <template v-for="line in [...drawn].reverse()" :key="line.key">
          <path
            :d="line.history"
            fill="none"
            :stroke="line.tone === 'muted' ? 'var(--text-dim)' : 'var(--live)'"
            :stroke-width="line.tone === 'muted' ? 2 : 2.6"
            stroke-linejoin="round"
            vector-effect="non-scaling-stroke"
          />
          <path
            :d="line.forecast"
            fill="none"
            :stroke="line.tone === 'muted' ? 'var(--text-dim)' : 'var(--live)'"
            :stroke-width="line.tone === 'muted' ? 2 : 2.4"
            stroke-dasharray="6 6"
            :opacity="line.tone === 'muted' ? 0.75 : 0.6"
            vector-effect="non-scaling-stroke"
          />
        </template>
      </svg>

      <p
        v-if="markerAt"
        class="bench__flag"
        :style="{ left: `${markerAt.x}%` }"
        aria-hidden="true"
      >
        {{ markerAt.label }}
      </p>

      <template v-if="!cursor">
        <span
          v-for="line in drawn"
          :key="line.key"
          class="bench__dot"
          :data-tone="line.tone"
          :style="line.head ? { left: `${line.head[0]}%`, top: `${line.head[1]}%` } : undefined"
          aria-hidden="true"
        />
      </template>

      <template v-else>
        <span
          class="bench__cursor"
          :style="{ left: `${cursor.x}%` }"
          aria-hidden="true"
        />
        <span
          v-for="point in cursor.points"
          :key="point.key"
          class="bench__dot is-live"
          :data-tone="point.tone"
          :style="point.style ?? undefined"
          aria-hidden="true"
        />
        <ChartTip
          :x="cursor.x"
          :place="cursor.place"
          :title="cursor.title"
          :rows="cursor.rows"
          :foot="cursor.ahead ? 'Predicción, no dato cerrado' : undefined"
        />
      </template>
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

    <p class="sr-only" role="status">{{ spoken }}</p>
  </figure>
</template>

<style scoped>
/* Las bandas y el eje se quedan quietos: lo que entra es el trazo, barrido de
   izquierda a derecha —del mes más viejo al último— y los puntos de cierre
   detrás, cuando la línea ya ha llegado. */
.bench--entering .bench__svg {
  animation: bench-wipe 1.15s cubic-bezier(0.22, 0.61, 0.36, 1) both;
}

.bench--entering .bench__dot {
  animation: bench-dot 0.35s ease-out 1s both;
}

@keyframes bench-wipe {
  from {
    clip-path: inset(0 100% 0 0);
  }
  to {
    clip-path: inset(0 0 0 0);
  }
}

@keyframes bench-dot {
  from {
    opacity: 0;
    transform: scale(0.4);
  }
}

@media (prefers-reduced-motion: reduce) {
  .bench--entering .bench__svg,
  .bench--entering .bench__dot {
    animation: none;
  }
}
</style>
