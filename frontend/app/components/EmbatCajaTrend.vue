<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { areaPath, linePath, linearScale, paddedDomain, type Point } from '~/utils/chart'
import type { Cashflow } from '../../shared/types/company'

/* El gráfico de la ficha: de dónde sale la lectura de caja que ya se ve en la fila.
 * Vive en su propio componente porque solo hace falta pedir el histórico mensual
 * cuando el panel está abierto, no al cargar el tablero entero. */

const props = defineProps<{ companyId: string; currency: string }>()

const { data, isPending, isError } = useQuery({
  queryKey: computed(() => ['caja-trend', props.companyId]),
  queryFn: () => $fetch<Cashflow>(`/api/flujo/${encodeURIComponent(props.companyId)}`),
  staleTime: 60 * 1000,
})

const months = computed(() => (data.value?.panel ?? []).slice(-12).filter((m) => m.cash_end != null))

const money = (value: number) =>
  new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: props.currency,
    maximumFractionDigits: 0,
  }).format(value)

const MONTH = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
const short = (ym: string) => MONTH[Number(ym.slice(5, 7)) - 1] ?? ym

const W = 400
const H = 120
const PAD = 8
const hover = ref<number | null>(null)
const plot = ref<HTMLElement | null>(null)

const trend = computed(() => {
  const values = months.value.map((m) => m.cash_end as number)
  if (values.length < 2) return null
  const x = linearScale([0, values.length - 1], [PAD, W - PAD])
  const y = linearScale(paddedDomain(values, 0.22), [H - PAD, PAD])
  const points = values.map((value, index) => [x(index), y(value)] as Point)
  return { points, path: linePath(points), area: areaPath(points, H - PAD) }
})

const at = computed(() => hover.value ?? months.value.length - 1)
const current = computed(() => months.value[at.value] ?? null)
const delta = computed(() => {
  const prev = months.value[at.value - 1]
  if (!prev || prev.cash_end == null || current.value?.cash_end == null) return null
  return current.value.cash_end - prev.cash_end
})

function move(event: PointerEvent) {
  const box = plot.value?.getBoundingClientRect()
  if (!box?.width || !trend.value) return
  const px = ((event.clientX - box.left) / box.width) * W
  let best = 0
  let gap = Infinity
  trend.value.points.forEach((point, index) => {
    const d = Math.abs(point[0] - px)
    if (d < gap) {
      gap = d
      best = index
    }
  })
  hover.value = best
}

function onKeydown(event: KeyboardEvent) {
  const n = months.value.length
  if (!n) return
  if (event.key === 'ArrowLeft') {
    hover.value = Math.max(0, at.value - 1)
    event.preventDefault()
  } else if (event.key === 'ArrowRight') {
    hover.value = Math.min(n - 1, at.value + 1)
    event.preventDefault()
  } else if (event.key === 'Escape') {
    hover.value = null
  }
}

const spoken = computed(() =>
  months.value.map((m) => `${short(m.month)}: ${m.cash_end != null ? money(m.cash_end) : 'sin dato'}`).join('. '),
)

const netBars = computed(() => {
  const rows = months.value.filter((m) => m.inflow_op != null || m.outflow_op != null)
  const nets = rows.map((m) => (m.inflow_op ?? 0) - (m.outflow_op ?? 0))
  const span = Math.max(1, ...nets.map((v) => Math.abs(v)))
  return rows.map((m, index) => {
    const net = nets[index]!
    return {
      month: short(m.month),
      net,
      label: `${net >= 0 ? '+' : '−'}${money(Math.abs(net))}`,
      pct: Math.max(4, (Math.abs(net) / span) * 100),
      tone: net >= 0 ? 'in' : 'out',
    }
  })
})
</script>

<template>
  <div class="caja__trend">
    <p v-if="isPending" class="caja__trend-state">Cargando el histórico.</p>
    <p v-else-if="isError || !trend" class="caja__trend-state">
      No hay histórico mensual suficiente para dibujar la tendencia.
    </p>
    <template v-else>
      <p class="caja__trend-lead">
        <b>{{ current?.cash_end != null ? money(current.cash_end) : '—' }}</b>
        <span v-if="current">{{ short(current.month) }}</span>
        <em v-if="delta != null" :class="delta >= 0 ? 'is-up' : 'is-down'">
          {{ delta >= 0 ? '+' : '−' }}{{ money(Math.abs(delta)) }} vs. mes anterior
        </em>
      </p>

      <div
        ref="plot"
        class="caja__trend-plot"
        tabindex="0"
        role="img"
        :aria-label="`Caja al cierre por mes: ${spoken}`"
        @pointermove="move"
        @pointerleave="hover = null"
        @keydown="onKeydown"
        @blur="hover = null"
      >
        <svg :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none" aria-hidden="true">
          <defs>
            <linearGradient id="caja-trend-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stop-color="var(--ea-blue)" stop-opacity="0.22" />
              <stop offset="1" stop-color="var(--ea-blue)" stop-opacity="0" />
            </linearGradient>
          </defs>
          <path :d="trend.area" fill="url(#caja-trend-fill)" />
          <path
            :d="trend.path"
            fill="none"
            stroke="var(--ea-blue)"
            stroke-width="1.75"
            stroke-linejoin="round"
            stroke-linecap="round"
            vector-effect="non-scaling-stroke"
          />
          <line
            v-if="hover != null"
            :x1="trend.points[hover]![0]"
            :x2="trend.points[hover]![0]"
            :y1="PAD"
            :y2="H - PAD"
            stroke="var(--ea-line)"
            vector-effect="non-scaling-stroke"
          />
        </svg>
        <i
          v-for="(point, index) in trend.points"
          :key="index"
          class="caja__trend-dot"
          :class="{ 'is-on': index === at }"
          :style="{ left: `${(point[0] / W) * 100}%`, top: `${(point[1] / H) * 100}%` }"
        />
      </div>

      <ul v-if="netBars.length" class="caja__trend-bars" aria-hidden="true">
        <li v-for="bar in netBars" :key="bar.month">
          <span>{{ bar.month }}</span>
          <span class="caja__trend-track"><i :class="bar.tone" :style="{ width: `${bar.pct}%` }" /></span>
        </li>
      </ul>
      <p v-if="netBars.length" class="caja__trend-note">Entradas menos salidas operativas, mes a mes.</p>
      <p class="sr-only">
        Entradas menos salidas operativas por mes: {{ netBars.map((b) => `${b.month} ${b.label}`).join('. ') }}.
      </p>
    </template>
  </div>
</template>

<style scoped>
.caja__trend-state {
  margin: 0;
  padding: 10px 0 2px;
  color: var(--ea-muted);
}

.caja__trend-lead {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px;
  margin: 0 0 8px;
}

.caja__trend-lead b {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.caja__trend-lead span {
  color: var(--ea-muted);
}

.caja__trend-lead em {
  margin-left: auto;
  font-style: normal;
  font-size: 11.5px;
}

.caja__trend-lead em.is-up {
  color: var(--ea-green);
}

.caja__trend-lead em.is-down {
  color: var(--ea-red);
}

.caja__trend-plot {
  position: relative;
  aspect-ratio: 400 / 120;
  cursor: crosshair;
  outline: none;
}

.caja__trend-plot:focus-visible {
  outline: 2px solid var(--ea-blue);
  outline-offset: 3px;
  border-radius: 4px;
}

.caja__trend-plot svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.caja__trend-dot {
  position: absolute;
  width: 5px;
  height: 5px;
  margin: -2.5px 0 0 -2.5px;
  border-radius: 50%;
  background: var(--ea-blue);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.1s ease;
}

.caja__trend-dot.is-on {
  opacity: 1;
}

.caja__trend-bars {
  display: grid;
  gap: 4px;
  margin: 14px 0 0;
  padding: 0;
  list-style: none;
}

.caja__trend-bars li {
  display: grid;
  grid-template-columns: 28px 1fr;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--ea-muted);
}

.caja__trend-track {
  position: relative;
  height: 6px;
  border-radius: 3px;
  background: var(--ea-soft);
}

.caja__trend-track i {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  border-radius: 3px;
}

.caja__trend-track i.in {
  background: var(--ea-green);
}

.caja__trend-track i.out {
  background: var(--ea-red);
}

.caja__trend-note {
  margin: 8px 0 0;
  color: var(--ea-muted);
  font-size: 11px;
}
</style>
