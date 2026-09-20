<script setup lang="ts">
import { Search, X } from '@lucide/vue'
import type { CajaCompany, CajaResponse, ScorePoint } from '../../shared/types/embat'
import type { ChatChart } from '~/utils/chatCharts'
import type { Trace } from './ScoreBandChart.vue'

const { data: caja, pending, error, refresh } = await useAsyncData('embat-caja', () =>
  $fetch<CajaResponse>('/api/embat/caja'),
)

const SUGERENCIA = {
  financiar: { label: 'Financiar', tone: 'crimson' },
  colocar: { label: 'Colocar excedente', tone: 'mint' },
  seguir: { label: 'Seguir', tone: 'neutral' },
} as const

const money = (value: number, currency: string) =>
  `${Math.abs(value).toLocaleString('es-ES', { maximumFractionDigits: 0 })} ${currency === 'EUR' ? '€' : currency}`

/* Financiar y colocar salen del mismo número: impacto = punto más bajo de la caja − gasto de un mes. */
function accion(company: CajaCompany) {
  const { label } = SUGERENCIA[company.sugerencia]
  return company.sugerencia === 'seguir' || company.impacto == null ? label : `${label} · ${money(company.impacto, company.currency)}`
}

const companies = computed(() => caja.value?.companies ?? [])

const sectors = computed(() =>
  [...new Set(companies.value.map((row) => row.sector).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, 'es'),
  ),
)

type Slot = 'a' | 'b'

const COMPARE_SLOTS = [
  { id: 'a' as const, placeholder: 'Empresa A', aria: 'empresa A' },
  { id: 'b' as const, placeholder: 'Empresa B', aria: 'empresa B' },
]

const sectorFilter = ref<string | null>(null)
const compareId = reactive<{ a: string | null; b: string | null }>({ a: null, b: null })
const query = reactive({ a: '', b: '' })
const openPicker = ref<Slot | null>(null)

const scopedCompanies = computed(() => {
  const rows = companies.value
  if (!sectorFilter.value) return rows
  return rows.filter((row) => row.sector === sectorFilter.value)
})

const meanTraceLabel = computed(() =>
  sectorFilter.value ? `Media · ${sectorFilter.value}` : 'Media de la cartera',
)

const monthNames = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
const monthLabel = (month: string) =>
  `${monthNames[Number(month.slice(5, 7)) - 1]} ${month.slice(2, 4)}`

function meanMedian(scores: number[]) {
  const sorted = [...scores].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return {
    mean: scores.reduce((sum, v) => sum + v, 0) / scores.length,
    median: sorted.length % 2 ? sorted[mid]! : (sorted[mid - 1]! + sorted[mid]!) / 2,
    n: scores.length,
  }
}

function scoresByMonth(series: ScorePoint[]) {
  return new Map(series.map((point) => [point.month, point.score]))
}

/** Meses presentes en todos los mapas (ordenados). */
function sharedMonths(...maps: Map<string, number>[]) {
  const [first, ...rest] = maps
  if (!first) return []
  return [...first.keys()].filter((month) => rest.every((map) => map.has(month))).sort()
}

function companyTrace(
  company: CajaCompany,
  months: string[],
  scores: Map<string, number>,
  tone?: Trace['tone'],
): Trace {
  return {
    key: company.company_id,
    label: company.name,
    note: company.sector,
    ...(tone ? { tone } : {}),
    history: months.map((month) => scores.get(month)!),
    forecast: [],
  }
}

/** Meses con nota en el subconjunto activo (sector o cartera). */
const portfolioHistory = computed(() => {
  const byMonth = new Map<string, number[]>()
  for (const company of scopedCompanies.value) {
    for (const point of company.score_series) {
      const bucket = byMonth.get(point.month)
      if (bucket) bucket.push(point.score)
      else byMonth.set(point.month, [point.score])
    }
  }
  return [...byMonth.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, scores]) => ({ month, ...meanMedian(scores) }))
})

function companyById(id: string | null) {
  return id ? scopedCompanies.value.find((row) => row.company_id === id) ?? null : null
}

const pickA = computed(() => companyById(compareId.a))
const pickB = computed(() => companyById(compareId.b))

const comparison = computed(() => {
  const a = pickA.value
  const b = pickB.value
  if (!a && !b) return null

  if (a && b) {
    const scoresA = scoresByMonth(a.score_series)
    const scoresB = scoresByMonth(b.score_series)
    const months = sharedMonths(scoresA, scoresB)
    return {
      months,
      traces: [companyTrace(a, months, scoresA), companyTrace(b, months, scoresB, 'muted')] satisfies Trace[],
    }
  }

  const lead = (a ?? b)!
  const leadScores = scoresByMonth(lead.score_series)
  const poolMean = new Map(portfolioHistory.value.map((row) => [row.month, row.mean]))
  const months = sharedMonths(leadScores, poolMean)
  return {
    months,
    traces: [
      companyTrace(lead, months, leadScores),
      {
        key: 'media',
        label: meanTraceLabel.value,
        note: `${scopedCompanies.value.length} empresas`,
        tone: 'muted',
        history: months.map((month) => poolMean.get(month)!),
        forecast: [],
      },
    ] satisfies Trace[],
  }
})

const traces = computed<Trace[]>(() => {
  if (comparison.value) return comparison.value.traces
  const history = portfolioHistory.value
  return [
    {
      key: 'media',
      label: meanTraceLabel.value,
      note: `${scopedCompanies.value.length} empresas`,
      history: history.map((m) => m.mean),
      forecast: [],
    },
    {
      key: 'mediana',
      label: 'Mediana',
      tone: 'muted',
      history: history.map((m) => m.median),
      forecast: [],
    },
  ]
})

const monthLabels = computed(() => {
  const months = comparison.value?.months ?? portfolioHistory.value.map((m) => m.month)
  return months.map(monthLabel)
})

const chartCaption = computed(() => {
  if (pickA.value && pickB.value) {
    return `Nota de ${pickA.value.name} frente a ${pickB.value.name}, mes a mes.`
  }
  if (pickA.value || pickB.value) {
    const company = (pickA.value ?? pickB.value)!
    const scope = sectorFilter.value ? `de ${sectorFilter.value}` : 'de la cartera'
    return `Nota de ${company.name} frente a la media ${scope}.`
  }
  if (sectorFilter.value) {
    return `Nota media y mediana de ${sectorFilter.value}, mes a mes.`
  }
  return 'Nota media y mediana de la cartera, mes a mes.'
})

const showChart = computed(() => monthLabels.value.length > 1)

function matchesQuery(company: CajaCompany, needle: string) {
  if (!needle) return true
  const hay = `${company.name} ${company.sector} ${company.company_id}`.toLocaleLowerCase('es')
  return hay.includes(needle)
}

function suggestions(slot: Slot) {
  const needle = query[slot].trim().toLocaleLowerCase('es')
  const taken = compareId[slot === 'a' ? 'b' : 'a']
  return scopedCompanies.value
    .filter((row) => row.company_id !== taken && matchesQuery(row, needle))
    .slice(0, 8)
}

function selectCompany(slot: Slot, company: CajaCompany) {
  compareId[slot] = company.company_id
  query[slot] = company.name
  openPicker.value = null
}

function clearCompany(slot: Slot) {
  compareId[slot] = null
  query[slot] = ''
}

function onQueryInput(slot: Slot, value: string) {
  query[slot] = value
  const picked = companyById(compareId[slot])
  if (picked && value !== picked.name) compareId[slot] = null
  openPicker.value = slot
}

function blurPicker(slot: Slot) {
  window.setTimeout(() => {
    if (openPicker.value === slot) openPicker.value = null
  }, 120)
}

watch(sectorFilter, () => {
  const pool = new Set(scopedCompanies.value.map((row) => row.company_id))
  for (const slot of COMPARE_SLOTS) {
    const id = compareId[slot.id]
    if (id && !pool.has(id)) clearCompany(slot.id)
  }
})

/* Misma tabla que enseña el agente: tres columnas, la nota con su color de banda. */
const chart = computed<ChatChart | null>(() => {
  const rows = scopedCompanies.value
  if (!rows.length && !companies.value.length) return null
  return {
    id: 'embat-caja',
    kind: 'table',
    title: 'Caja',
    subtitle: sectorFilter.value
      ? `${rows.length} empresas · ${sectorFilter.value}`
      : `${rows.length} empresas`,
    items: [],
    columns: [
      { key: 'empresa', label: 'Empresa', kind: 'text', sub: 'sector', grow: 1.6 },
      { key: 'nota', label: 'Nota', kind: 'score', grow: 0.8 },
      { key: 'impacto', label: 'Impacto potencial', kind: 'num', signed: true, unit: ' €', grow: 1.2 },
      { key: 'urgencia', label: 'Urgencia', kind: 'num', unit: ' días', grow: 0.8 },
      { key: 'sugerencia', label: 'Acción sugerida', kind: 'chip', grow: 1.6 },
    ],
    rows: [...rows]
      .sort((a, b) => (a.impacto ?? Infinity) - (b.impacto ?? Infinity))
      .map((company) => ({
        company_id: company.company_id,
        empresa: company.name,
        sector: company.sector,
        nota: company.health_score,
        banda: company.health_band,
        tendencia: company.health_trend,
        cambio_3_meses: company.score_delta_3m,
        impacto: company.impacto,
        impacto_unit: company.currency === 'EUR' ? ' €' : ` ${company.currency}`,
        urgencia: company.urgencia_dias,
        sugerencia: accion(company),
        sugerencia_tone: SUGERENCIA[company.sugerencia].tone,
      })),
  }
})
</script>

<template>
  <div class="caja-tabla">
    <p v-if="pending" class="caja-tabla__state">Leyendo la tesorería.</p>
    <p v-else-if="error" class="caja-tabla__state" role="alert">
      No se pudo leer la tesorería.
      <button type="button" @click="refresh()">Reintentar</button>
    </p>
    <p v-else-if="!chart" class="caja-tabla__state">No hay empresas en el portfolio de caja.</p>
    <template v-else>
      <header class="caja-tabla__title">
        <h1>{{ chart.title }}</h1>
        <span>{{ chart.subtitle }}</span>
      </header>
      <section class="caja-tabla__chart tz-card" aria-label="Nota de la cartera">
        <div class="caja-tabla__filters">
          <div class="caja-tabla__compare" role="search" aria-label="Comparar dos empresas">
            <span class="caja-tabla__compare-label">Comparar</span>
            <template v-for="(slot, index) in COMPARE_SLOTS" :key="slot.id">
              <span v-if="index > 0" class="caja-tabla__vs" aria-hidden="true">vs</span>
              <div class="caja-tabla__picker">
                <label class="caja-tabla__search">
                  <Search :size="15" aria-hidden="true" />
                  <input
                    :value="query[slot.id]"
                    type="search"
                    :placeholder="slot.placeholder"
                    :aria-label="`Buscar ${slot.aria}`"
                    :aria-expanded="openPicker === slot.id"
                    aria-autocomplete="list"
                    autocomplete="off"
                    @focus="openPicker = slot.id"
                    @input="onQueryInput(slot.id, ($event.target as HTMLInputElement).value)"
                    @blur="blurPicker(slot.id)"
                  />
                  <button
                    v-if="compareId[slot.id] || query[slot.id]"
                    type="button"
                    class="caja-tabla__clear"
                    :aria-label="`Quitar ${slot.aria}`"
                    @mousedown.prevent="clearCompany(slot.id)"
                  >
                    <X :size="14" aria-hidden="true" />
                  </button>
                </label>
                <ul
                  v-if="openPicker === slot.id && suggestions(slot.id).length"
                  class="caja-tabla__suggest"
                  role="listbox"
                >
                  <li v-for="company in suggestions(slot.id)" :key="company.company_id">
                    <button type="button" @mousedown.prevent="selectCompany(slot.id, company)">
                      <b>{{ company.name }}</b>
                      <span>{{ company.sector }}</span>
                    </button>
                  </li>
                </ul>
              </div>
            </template>
          </div>

          <label class="caja-tabla__sector">
            <span>Sector</span>
            <select
              :value="sectorFilter ?? ''"
              aria-label="Filtrar por sector"
              @change="sectorFilter = ($event.target as HTMLSelectElement).value || null"
            >
              <option value="">Todos</option>
              <option v-for="sector in sectors" :key="sector" :value="sector">{{ sector }}</option>
            </select>
          </label>
        </div>

        <ScoreBandChart
          v-if="showChart"
          :traces="traces"
          :month-labels="monthLabels"
          note="Datos reales · nota mensual"
          :caption="chartCaption"
        />
        <p v-else class="caja-tabla__state">
          {{ scopedCompanies.length ? 'No hay historial de nota suficiente para este filtro.' : 'Ninguna empresa en este sector.' }}
        </p>
      </section>
      <ChatTable v-if="scopedCompanies.length" :chart="chart" plain />
      <p v-else class="caja-tabla__state">Ninguna empresa en este sector.</p>
    </template>
  </div>
</template>

<style scoped>
/* Fondo blanco a pantalla completa y la tabla flotando encima, con borde y esquinas. Las
 * pantallas Embat van siempre en claro, así que se fijan aquí los tokens que lee la tabla. */
.caja-tabla {
  --panel: #ffffff;
  --panel-raised: #ebeef9;
  --panel-sunken: #f7f8fd;
  --line: #dcdfef;
  --line-strong: #c1c6e0;
  --text: #151833;
  --text-muted: #5a6088;
  --text-dim: #666c95;
  --amber: #e09612;
  --crimson: #e0364b;
  --live: #3552e8;
  --live-solid: #3552e8;
  --on-live: #ffffff;
  --mint-ink: #0d7d55;
  --amber-ink: #8a5a00;
  --crimson-ink: #b8253a;
  --live-ink: #2a42c9;
  --mint-wash: rgba(22, 166, 114, 0.1);
  --amber-wash: rgba(224, 150, 18, 0.13);
  --crimson-wash: rgba(224, 54, 75, 0.09);
  --live-wash: rgba(53, 82, 232, 0.09);
  --neutral-wash: rgba(21, 24, 51, 0.045);
  --grid-line: rgba(21, 24, 51, 0.08);
  --ahead-ink: #5b3fd6;
  --focus-ring: #2a42c9;
  --mint: #16a672;
  --coral: #f0714b;
  --ahead: #7a5af0;
  --sheen: none;

  display: flex;
  flex-direction: column;
  min-height: 100vh;
  padding: 20px;
  background: #ffffff;
  color: var(--text);
  color-scheme: light;
}
.caja-tabla > :deep(.ct) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--line-strong);
  border-radius: 14px;
  box-shadow: 0 6px 24px rgba(21, 24, 51, 0.08);
}
.caja-tabla > :deep(.ct .ct__body) {
  flex: 1;
  min-height: 0;
}
.caja-tabla > :deep(.ct .ct__scroll) {
  flex: 1;
  max-height: none;
  min-width: 0;
}
.caja-tabla__title {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 4px 2px 14px;
}
.caja-tabla__title h1 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.caja-tabla__title span {
  font-size: 0.78rem;
  color: var(--text-muted);
}
.caja-tabla__chart {
  margin: 0 0 16px;
  padding: 16px 18px;
  border: 1px solid var(--line-strong);
  border-radius: 14px;
  background: var(--panel);
}
.caja-tabla__filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px 16px;
  margin-bottom: 14px;
}
.caja-tabla__compare {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 10px;
  min-width: 0;
  flex: 1 1 auto;
}
.caja-tabla__sector {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
  flex: 0 0 auto;
}
.caja-tabla__sector > span {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-muted);
}
.caja-tabla__sector select {
  min-width: 160px;
  min-height: 40px;
  padding: 0 32px 0 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--panel-sunken)
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23666c95' d='M2.5 4.5L6 8l3.5-3.5'/%3E%3C/svg%3E")
    no-repeat right 12px center;
  color: var(--text);
  font: inherit;
  font-size: 0.85rem;
  appearance: none;
  cursor: pointer;
}
.caja-tabla__sector select:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}
.caja-tabla__compare-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-muted);
}
.caja-tabla__picker {
  position: relative;
  flex: 1 1 180px;
  min-width: 160px;
  max-width: 280px;
}
.caja-tabla__search {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 10px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--panel-sunken);
  color: var(--text-dim);
}
.caja-tabla__search:focus-within {
  border-color: var(--live);
  box-shadow: 0 0 0 3px var(--live-wash);
}
.caja-tabla__search input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: transparent;
  color: var(--text);
  font: inherit;
  font-size: 0.85rem;
  outline: none;
}
.caja-tabla__clear {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--text-dim);
  cursor: pointer;
}
.caja-tabla__clear:hover {
  background: var(--neutral-wash);
  color: var(--text);
}
.caja-tabla__suggest {
  position: absolute;
  z-index: 5;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  margin: 0;
  padding: 4px;
  list-style: none;
  border: 1px solid var(--line-strong);
  border-radius: 10px;
  background: var(--panel);
  box-shadow: 0 10px 28px rgba(21, 24, 51, 0.12);
  max-height: 240px;
  overflow: auto;
}
.caja-tabla__suggest button {
  display: grid;
  gap: 2px;
  width: 100%;
  padding: 8px 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.caja-tabla__suggest button:hover,
.caja-tabla__suggest button:focus-visible {
  background: var(--live-wash);
  outline: none;
}
.caja-tabla__suggest b {
  font-size: 0.85rem;
  font-weight: 600;
}
.caja-tabla__suggest span {
  font-size: 0.72rem;
  color: var(--text-muted);
}
.caja-tabla__vs {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--text-dim);
}
.caja-tabla > :deep(.ct) {
  min-height: 320px;
}
.caja-tabla__state {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.85rem;
}
</style>
