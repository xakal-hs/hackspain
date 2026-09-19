<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import {
  Atom,
  Calendar,
  ChartLine,
  ChevronDown,
  ChevronRight,
  ChevronsUpDown,
  Ellipsis,
  Eye,
  ListChecks,
  RotateCcwClock,
  ScanLine,
  TrendingUp,
  TriangleAlert,
} from '@lucide/vue'
import type { Cashflow, CashflowMonth, ForecastMonth } from '../../shared/types/company'

/* Clon de la pantalla «Flujo de caja» de Embat: mismas filas, mismos controles y la misma barra
 * flotante abajo. Va siempre en claro, como el original. */

const { selectedId, company, sector } = useSelectedCompany()

const flujo = useQuery({
  queryKey: computed(() => ['flujo', selectedId.value]),
  queryFn: () => $fetch<Cashflow>(`/api/flujo/${encodeURIComponent(selectedId.value)}`),
  staleTime: 60 * 1000,
})

type Period = 'custom' | '3M' | '6M' | 'AA' | 'YTD'
const period = ref<Period>('3M')
const projection = ref<'none' | '3m'>('none')

type RealColumn = { key: string; month: string; ahead: false; start: number | null; m: CashflowMonth; cats: Record<string, number> }
type AheadColumn = { key: string; month: string; ahead: true; start: number; f: ForecastMonth }
type Column = RealColumn | AheadColumn

const n = (v: number | null | undefined) => Number(v ?? 0)

const columns = computed<Column[]>(() => {
  const data = flujo.data.value
  if (!data) return []
  // Solo los meses con desglose por categoría: los doce últimos.
  const panel = data.panel.filter((m) => data.categories[m.month])
  const year = Number((panel.at(-1)?.month ?? '').slice(0, 4))
  const picked = {
    custom: panel,
    '3M': panel.slice(-3),
    '6M': panel.slice(-6),
    AA: panel.filter((m) => m.month.startsWith(String(year - 1))),
    YTD: panel.filter((m) => m.month.startsWith(String(year))),
  }[period.value]
  const all = data.panel
  const real: Column[] = picked.map((m) => {
    const i = all.indexOf(m)
    return {
      key: m.month,
      month: m.month,
      ahead: false as const,
      start: i > 0 ? all[i - 1]!.cash_end : m.cash_end == null ? null : m.cash_end - n(m.net_bank),
      m,
      cats: data.categories[m.month] ?? {},
    }
  })
  if (projection.value === 'none' || !data.forecast) return real
  let start = data.forecast.cash
  return [
    ...real,
    ...data.forecast.months.map((f) => {
      const col = { key: `p-${f.month}`, month: f.month, ahead: true as const, start, f }
      start += f.cobros + f.proveedores + f.nominas + f.seguridad_social + f.deuda
      return col
    }),
  ]
})

/* Categorías bancarias → filas de Embat. Lo que no aparece aquí va a «Por categorizar». */
const groups: Record<string, [string, string][]> = {
  cobros: [
    ['collection', 'Cobros de clientes'],
    ['bulk_collection', 'Remesas de cobro'],
    ['pos_settlement', 'Liquidaciones TPV'],
    ['cash_settlement', 'Ingresos en efectivo'],
    ['cash_settlements', 'Ingresos en efectivo'],
    ['payment_refund', 'Devoluciones de pagos'],
    ['tax_refund', 'Devoluciones de impuestos'],
  ],
  pagos: [
    ['payment', 'Proveedores'],
    ['bulk_payment', 'Remesas de pago'],
    ['salary', 'Nóminas'],
    ['social_security', 'Seguridad social'],
    ['tax', 'Impuestos'],
    ['utility', 'Suministros'],
    ['fee', 'Comisiones bancarias'],
    ['cash_withdrawal', 'Retiradas de efectivo'],
    ['pos_withdrawal', 'Cargos TPV'],
    ['collection_refund', 'Devoluciones de cobros'],
  ],
  financing: [
    ['debt_repayment', 'Amortización de deuda'],
    ['interest_charge', 'Intereses'],
  ],
  investment: [
    ['investment_deployment', 'Inversiones'],
    ['investment_return', 'Retornos de inversión'],
  ],
  intercompany: [['transfer', 'Transferencias']],
}
const known = new Set(Object.values(groups).flat().map(([cat]) => cat))

/* La previsión solo conoce facturas, nóminas y cuotas: el resto va en blanco, no a cero. */
const forecastPart: Record<string, (f: ForecastMonth) => number> = {
  collection: (f) => f.cobros,
  payment: (f) => f.proveedores,
  salary: (f) => f.nominas,
  social_security: (f) => f.seguridad_social,
  debt_repayment: (f) => f.deuda,
}

const sumCats = (c: RealColumn, cats: string[]) => cats.reduce((acc, cat) => acc + n(c.cats[cat]), 0)
const groupValue = (c: Column, id: string): number | null => {
  const cats = groups[id]!.map(([cat]) => cat)
  if (!c.ahead) return sumCats(c, cats)
  const parts = cats.filter((cat) => forecastPart[cat])
  return parts.length ? parts.reduce((acc, cat) => acc + forecastPart[cat]!(c.f), 0) : null
}
const operating = (c: Column) => n(groupValue(c, 'cobros')) + n(groupValue(c, 'pagos'))

interface Row {
  id: string
  label: string
  level: number
  parent?: string
  tone?: 'strong' | 'muted'
  value: (c: Column) => number | null
}

function groupRows(id: string, label: string, level: number, parent?: string): Row[] {
  const names = [...new Set(groups[id]!.map(([, name]) => name))]
  return [
    { id, label, level, parent, value: (c) => groupValue(c, id) },
    ...names.map((name): Row => {
      const cats = groups[id]!.filter(([, other]) => other === name).map(([cat]) => cat)
      const part = cats.map((cat) => forecastPart[cat]).find(Boolean)
      return {
        id: `${id}:${name}`,
        label: name,
        level: level + 1,
        parent: id,
        value: (c) => (c.ahead ? (part ? part(c.f) : null) : sumCats(c, cats)),
      }
    }),
  ]
}

const allRows: Row[] = [
  { id: 'inicio', label: 'Tesorería al inicio del mes', level: 0, tone: 'strong', value: (c) => c.start },
  { id: 'op', label: 'Cashflow from operating activities', level: 0, value: operating },
  { id: 'flujo', label: 'Flujo de caja operativo', level: 1, parent: 'op', value: operating },
  ...groupRows('cobros', 'Cobros', 2, 'flujo'),
  ...groupRows('pagos', 'Pagos', 2, 'flujo'),
  ...groupRows('financing', 'Cashflow from financing activities', 0),
  ...groupRows('investment', 'Cashflow from investment activities', 0),
  ...groupRows('intercompany', 'Cashflow Intercompany operations', 0),
  {
    id: 'uncat', label: 'Por categorizar', level: 0, tone: 'muted',
    value: (c) => (c.ahead ? null : Object.entries(c.cats).reduce((acc, [cat, v]) => acc + (known.has(cat) ? 0 : v), 0)),
  },
  // Los importes ya llegan convertidos a la moneda de la empresa, movimiento a movimiento.
  { id: 'fx', label: 'Variación de divisa', level: 0, tone: 'muted', value: (c) => (c.ahead ? null : 0) },
  {
    id: 'ajustes', label: 'Ajustes de balance', level: 0, tone: 'muted',
    value: (c) => (c.ahead || c.start == null || c.m.cash_end == null ? null
      : c.m.cash_end - c.start - Object.values(c.cats).reduce((acc, v) => acc + v, 0)),
  },
  {
    id: 'final', label: 'Tesorería al final del mes', level: 0, tone: 'strong',
    value: (c) => (c.ahead ? c.start + c.f.cobros + c.f.proveedores + c.f.nominas + c.f.seguridad_social + c.f.deuda : c.m.cash_end),
  },
]

/* Una subcategoría sin movimientos en las columnas visibles no se pinta. */
const rows = computed(() =>
  allRows.filter((row) => !row.id.includes(':') || columns.value.some((c) => Math.abs(row.value(c) ?? 0) >= 0.005)),
)
const parents = computed(() => new Set(rows.value.flatMap((r) => (r.parent ? [r.parent] : []))))
const open = ref(new Set(['op', 'flujo']))
const selectedRow = ref('flujo')
const hoverCol = ref<string | null>(null)

function toggle(id: string) {
  const next = new Set(open.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  open.value = next
  selectedRow.value = id
}

const allOpen = computed(() => [...parents.value].every((id) => open.value.has(id)))
const toggleAll = () => (open.value = allOpen.value ? new Set() : new Set(parents.value))

const visibleRows = computed(() =>
  rows.value.filter((row) => {
    let parent = row.parent
    while (parent) {
      if (!open.value.has(parent)) return false
      parent = allRows.find((r) => r.id === parent)?.parent
    }
    return true
  }),
)

const amount = new Intl.NumberFormat('es-ES', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  useGrouping: 'always',
} as Intl.NumberFormatOptions)
const cell = (v: number | null) => (v == null || !Number.isFinite(v) ? '—' : amount.format(Math.abs(v) < 0.005 ? 0 : v))

const monthNames = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']
const monthLabel = (ym: string) => `${monthNames[Number(ym.slice(5, 7)) - 1]} - ${ym.slice(2, 4)}`
const lastReal = computed(() => [...columns.value].reverse().find((c) => !c.ahead)?.key)

const currency = computed(() => flujo.data.value?.currency || company.value?.currency || 'EUR')
const money = (v: number) =>
  new Intl.NumberFormat('es-ES', { style: 'currency', currency: currency.value, maximumFractionDigits: 0, useGrouping: 'always' } as Intl.NumberFormatOptions)
    .format(v)
    .replace('-', '−')
const monthLong = (iso: string) =>
  new Intl.DateTimeFormat('es-ES', { month: 'long', timeZone: 'UTC' }).format(new Date(`${iso}T00:00:00Z`))
/* «del 17 al 24 de septiembre», con los dos meses solo si el tramo cruza de uno a otro. */
const span = (from: string, to: string | null) => {
  const d = (iso: string) => Number(iso.slice(8))
  if (!to) return `desde el ${d(from)} de ${monthLong(from)}`
  return from.slice(0, 7) === to.slice(0, 7)
    ? `del ${d(from)} al ${d(to)} de ${monthLong(to)}`
    : `del ${d(from)} de ${monthLong(from)} al ${d(to)} de ${monthLong(to)}`
}

const rotura = computed(() => flujo.data.value?.forecast?.rotura ?? null)
const excedente = computed(() => flujo.data.value?.forecast?.excedente ?? null)

/* Al cambiar de periodo o de empresa, la tabla se abre por el final. */
const scroller = ref<HTMLElement | null>(null)
watch([columns, scroller], () => nextTick(() => scroller.value?.scrollTo({ left: scroller.value.scrollWidth })), {
  flush: 'post',
})

/* La empresa activa lleva su cuadrado de iniciales, como el «DE» de Embat. */
const initials = computed(() => {
  const words = (company.value?.top_sector || '').split(/\s+/).filter(Boolean)
  return (words.length ? words[0]!.slice(0, 2) : selectedId.value.slice(-2)).toUpperCase()
})
const hue = computed(() => (Number(selectedId.value.replace(/\D/g, '')) * 47) % 360)
const sectorLabel = computed(() => sector.value.charAt(0).toUpperCase() + sector.value.slice(1))
</script>

<template>
  <div class="eb">
    <header class="eb__title">
      <h1>Flujo de caja</h1>
      <div class="eb__title-side">
        <Transition name="eb-swap" mode="out-in">
          <p :key="selectedId" class="eb__company" :style="{ '--hue': hue }">
            <i aria-hidden="true">{{ initials }}</i>
            <span>{{ selectedId }} · {{ sectorLabel }}</span>
          </p>
        </Transition>
        <button type="button" class="eb__ghost" disabled>
          <ChartLine :size="15" aria-hidden="true" />Análisis de variaciones
        </button>
        <button type="button" class="eb__ghost" disabled>
          <ScanLine :size="15" aria-hidden="true" />Capturas<ChevronDown :size="15" aria-hidden="true" />
        </button>
      </div>
    </header>

    <div class="eb__bar">
      <label class="eb__drop eb__drop--wide">
        <Eye :size="16" aria-hidden="true" />
        <select aria-label="Vista" class="is-placeholder">
          <option>Vista por defecto</option>
        </select>
        <ChevronDown :size="16" aria-hidden="true" />
      </label>
      <label class="eb__drop eb__drop--wide">
        <TrendingUp :size="16" aria-hidden="true" />
        <select v-model="projection" aria-label="Proyección" :class="{ 'is-placeholder': projection === 'none' }">
          <option value="none">Sin proyección</option>
          <option value="3m" :disabled="!flujo.data.value?.forecast">Proyección a 3 meses</option>
        </select>
        <ChevronDown :size="16" aria-hidden="true" />
      </label>
      <div class="eb__seg" role="radiogroup" aria-label="Periodo">
        <button type="button" role="radio" :aria-checked="period === 'custom'" @click="period = 'custom'">
          <Calendar :size="15" aria-hidden="true" />Personalizado
        </button>
        <button
          v-for="p in (['3M', '6M', 'AA', 'YTD'] as const)"
          :key="p"
          type="button"
          role="radio"
          :aria-checked="period === p"
          @click="period = p"
        >
          {{ p }}
        </button>
      </div>
      <span class="eb__grow" />
      <button type="button" class="eb__text">Añadir Filtros</button>
      <label class="eb__drop">
        <select aria-label="Visualización">
          <option>Visualización</option>
        </select>
        <ChevronDown :size="16" aria-hidden="true" />
      </label>
      <button type="button" class="eb__icon" aria-label="Más opciones"><Ellipsis :size="18" aria-hidden="true" /></button>
    </div>

    <Transition name="eb-swap" mode="out-in">
      <section :key="selectedId" class="eb__sheet" :aria-busy="flujo.isPending.value">
        <p v-if="flujo.isPending.value" class="eb__state">Cargando…</p>
        <p v-else-if="flujo.isError.value" class="eb__state" role="alert">
          No se pudo cargar el flujo de caja.
          <button type="button" @click="flujo.refetch()">Reintentar</button>
        </p>
        <p v-else-if="!columns.length" class="eb__state">Sin movimientos bancarios en este periodo.</p>
        <div v-else ref="scroller" class="eb__scroll" @mouseleave="hoverCol = null">
          <table :class="{ 'is-wide': columns.length > 4 }">
            <thead>
              <tr>
                <th scope="col" class="eb__lead">
                  <button
                    type="button"
                    class="eb__all"
                    :aria-label="allOpen ? 'Contraer todo' : 'Desplegar todo'"
                    @click="toggleAll"
                  >
                    <ChevronsUpDown :size="16" aria-hidden="true" />
                  </button>
                </th>
                <th
                  v-for="c in columns"
                  :key="c.key"
                  scope="col"
                  :class="{ 'is-hover': hoverCol === c.key, 'is-current': c.key === lastReal, 'is-ahead': c.ahead }"
                  @mouseenter="hoverCol = c.key"
                >
                  {{ monthLabel(c.month) }}<small v-if="c.ahead">Previsión</small>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in visibleRows" :key="row.id" :data-tone="row.tone">
                <th
                  scope="row"
                  class="eb__lead"
                  :class="{ 'is-selected': selectedRow === row.id }"
                  :style="{ '--level': row.level }"
                  @click="selectedRow = row.id"
                >
                  <button
                    v-if="parents.has(row.id)"
                    type="button"
                    class="eb__toggle"
                    :aria-expanded="open.has(row.id)"
                    @click.stop="toggle(row.id)"
                  >
                    <ChevronRight :size="16" aria-hidden="true" />{{ row.label }}
                  </button>
                  <span v-else>{{ row.label }}</span>
                </th>
                <td
                  v-for="c in columns"
                  :key="c.key"
                  :class="{ 'is-hover': hoverCol === c.key, 'is-ahead': c.ahead }"
                  @mouseenter="hoverCol = c.key"
                >
                  {{ cell(row.value(c)) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <!-- La acción del caso, abajo a la derecha, pegada a la tesorería final. -->
        <div v-if="columns.length && (rotura || excedente)" class="eb__action">
          <template v-if="rotura">
            <p>Vas a romper caja {{ span(rotura.from, rotura.to) }}: {{ money(rotura.low) }}</p>
            <button type="button" class="eb__alert" aria-label="Pedir financiación">
              <TriangleAlert :size="18" aria-hidden="true" /><span>Pedir financiación</span>
            </button>
          </template>
          <button v-else type="button" class="eb__cta">Gana eficiencia prestando tu caja</button>
        </div>
      </section>
    </Transition>

    <!-- La barra flotante de Embat. -->
    <div class="eb__dock">
      <nav class="eb__pill" aria-label="Herramientas">
        <button type="button" aria-label="Asistente"><Atom :size="20" aria-hidden="true" class="eb__atom" /></button>
        <button type="button" aria-label="Tareas pendientes: 1">
          <ListChecks :size="17" aria-hidden="true" /><span>1</span>
        </button>
        <button type="button" aria-label="Historial"><RotateCcwClock :size="17" aria-hidden="true" /></button>
      </nav>
    </div>
  </div>
</template>

<style scoped>
/* Paleta del original, fija: la pantalla de Embat es clara en los dos temas. */
.eb {
  --eb-bg: #ffffff;
  --eb-line: #e8eaee;
  --eb-line-soft: #eff1f4;
  --eb-text: #1b1f2a;
  --eb-body: #3a4050;
  --eb-muted: #737a8a;
  --eb-fill: #f4f5f7;
  --eb-hover: #f1f2f5;
  --eb-blue: #3b6cf5;
  --eb-ahead: #7a5af0;

  position: relative;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 100vh;
  background: var(--eb-bg);
  color: var(--eb-text);
  font-family: 'Inter', ui-sans-serif, system-ui, sans-serif;
  font-size: 13px;
  font-feature-settings: 'tnum' 1;
  color-scheme: light;
}

.eb ::selection {
  background: #dbe5ff;
}

.eb__title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px 16px;
  min-height: 56px;
  padding: 0 24px;
  border-bottom: 1px solid var(--eb-line);
}

.eb__title h1 {
  margin: 0;
  font-size: 17px;
  font-weight: 500;
  letter-spacing: -0.01em;
}

.eb__title-side {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.eb__company {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 6px 0 0;
  font-weight: 500;
  color: var(--eb-body);
}

.eb__company i {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: oklch(0.56 0.17 var(--hue));
  color: #fff;
  font-size: 11.5px;
  font-style: normal;
  font-weight: 600;
}

.eb__ghost {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 30px;
  padding: 0 12px;
  border: 0;
  border-radius: 5px;
  background: #e9ebef;
  color: #7d8391;
  font: inherit;
  font-weight: 500;
}

.eb__bar {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 10px 16px;
  padding: 12px 24px;
  border-bottom: 1px solid var(--eb-line);
}

.eb__drop {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  height: 30px;
  padding: 0 10px;
  border: 1px solid #dfe2e7;
  border-radius: 5px;
  background: #fff;
  color: var(--eb-body);
}

.eb__drop--wide {
  flex: 0 1 240px;
  min-width: 150px;
}

.eb__drop select {
  flex: 1;
  min-width: 0;
  height: 100%;
  padding-right: 22px;
  border: 0;
  background: transparent;
  color: var(--eb-text);
  font: inherit;
  appearance: none;
  cursor: pointer;
}

.eb__drop select.is-placeholder {
  color: var(--eb-muted);
}

.eb__drop select:focus {
  outline: none;
}

.eb__drop > svg:first-child {
  color: var(--eb-muted);
}

.eb__drop > svg:last-child {
  position: absolute;
  right: 10px;
  color: var(--eb-body);
  pointer-events: none;
}

.eb__drop:not(.eb__drop--wide) select {
  width: 104px;
}

.eb__seg {
  flex: none;
  display: flex;
  height: 30px;
  padding: 2px;
  border: 1px solid #dfe2e7;
  border-radius: 5px;
  background: #fff;
}

.eb__seg button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 10px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: var(--eb-text);
  font: inherit;
  font-weight: 500;
  cursor: pointer;
}

.eb__seg button[aria-checked='true'] {
  background: #e9ebef;
}

.eb__seg button:not([aria-checked='true']):hover {
  background: var(--eb-fill);
}

.eb__grow {
  flex: 1 1 0;
}

.eb__text,
.eb__icon,
.eb__drop:not(.eb__drop--wide) {
  flex: none;
}

.eb__text,
.eb__icon {
  border: 0;
  background: none;
  color: var(--eb-text);
  font: inherit;
  font-weight: 500;
  cursor: pointer;
}

.eb__icon {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 5px;
}

.eb__text:hover,
.eb__icon:hover {
  color: var(--eb-blue);
}

.eb button:focus-visible,
.eb__drop:focus-within {
  outline: 2px solid var(--eb-blue);
  outline-offset: 2px;
}

.eb__sheet {
  min-width: 0;
  padding: 16px 24px 32px;
}

.eb__state {
  margin: 0;
  padding: 24px 0;
  color: var(--eb-muted);
}

.eb__state button {
  margin-left: 6px;
  padding: 0;
  border: 0;
  background: none;
  color: var(--eb-blue);
  font: inherit;
  font-weight: 500;
  cursor: pointer;
}

.eb__scroll {
  overflow-x: auto;
  overscroll-behavior-x: contain;
}

table {
  width: 100%;
  min-width: max-content;
  border-collapse: separate;
  border-spacing: 0;
}

th,
td {
  height: 34px;
  padding: 0 14px;
  border-bottom: 1px solid var(--eb-line-soft);
  white-space: nowrap;
}

thead th {
  height: 50px;
  border-top: 2px solid transparent;
  border-bottom-color: var(--eb-line);
  font-size: 12.5px;
  font-weight: 400;
  color: var(--eb-muted);
  text-align: right;
}

thead th.is-current {
  border-top-color: var(--eb-blue);
}

thead th.is-ahead {
  border-top: 2px dashed var(--eb-ahead);
}

thead th small {
  display: block;
  font-size: 10.5px;
  color: var(--eb-ahead);
}

td {
  min-width: 170px;
  text-align: right;
  color: var(--eb-body);
}

td.is-ahead {
  background: #faf8ff;
}

/* Con más de cuatro meses (la previsión suma tres) la etiqueta cede ancho a los números. */
table.is-wide td {
  min-width: 128px;
}

table.is-wide .eb__lead {
  width: auto;
  min-width: 260px;
}

/* La columna bajo el cursor se ilumina entera, como en el original. */
th.is-hover,
td.is-hover {
  background: var(--eb-hover);
}

.eb__lead {
  position: sticky;
  left: 0;
  z-index: 1;
  width: 40%;
  min-width: 300px;
  padding-left: calc(24px + var(--level, 0) * 34px);
  background: var(--eb-bg);
  color: var(--eb-text);
  font-weight: 400;
  text-align: left;
  cursor: default;
}

thead .eb__lead {
  padding-left: 6px;
}

/* La etiqueta seleccionada lleva el recuadro azul del original. */
.eb__lead.is-selected {
  box-shadow: inset 0 0 0 1.5px var(--eb-blue);
}

.eb__lead > span {
  display: block;
  padding-left: 23px;
}

tr[data-tone='strong'] > * {
  background: #f7f8fa;
  color: var(--eb-text);
  font-weight: 600;
}

tr[data-tone='strong'] > td.is-hover {
  background: #eceef2;
}

tr[data-tone='muted'] > * {
  color: var(--eb-muted);
}

tbody tr:last-child > * {
  border-bottom: 0;
}

.eb__toggle,
.eb__all {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 3px 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.eb__all {
  padding: 6px;
  border-radius: 5px;
  color: var(--eb-body);
}

.eb__all:hover {
  background: var(--eb-fill);
}

.eb__toggle svg {
  flex: none;
  color: var(--eb-body);
  transition: transform 0.16s ease-out;
}

.eb__toggle[aria-expanded='true'] svg {
  transform: rotate(90deg);
}

/* La barra de Embat, abajo y centrada. No flota: taparía la acción del caso en pantallas bajas. */
.eb__dock {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: auto;
  padding: 0 16px 18px;
}

.eb__pill {
  display: flex;
  align-items: center;
  height: 52px;
  padding: 0 8px;
  border-radius: 10px;
  background: #1e2334;
  box-shadow: 0 10px 28px -12px rgb(16 20 40 / 0.5);
}

.eb__pill button {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 14px;
  border: 0;
  border-radius: 7px;
  background: none;
  color: #e6e8f0;
  font: inherit;
  font-weight: 500;
  cursor: pointer;
}

.eb__pill button + button::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 1px;
  background: rgb(255 255 255 / 0.14);
}

.eb__pill button:hover {
  background: rgb(255 255 255 / 0.08);
}

.eb__atom {
  color: #a58bff;
}

.eb__cta {
  height: 40px;
  padding: 0 18px;
  border: 0;
  border-radius: 8px;
  background: var(--eb-blue);
  color: #fff;
  font: inherit;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
}

.eb__cta:hover {
  background: #2f5de0;
}

.eb__action {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 14px;
}

.eb__action p {
  margin: 0;
  font-weight: 500;
  color: var(--eb-body);
}

/* El aviso es un icono negro; al pasar por encima se abre en un botón normal. */
.eb__alert {
  display: inline-flex;
  align-items: center;
  gap: 0;
  height: 40px;
  padding: 0 11px;
  border: 0;
  border-radius: 999px;
  background: #0a0a0c;
  color: #fff;
  font: inherit;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition:
    gap 0.3s cubic-bezier(0.16, 1, 0.3, 1),
    padding 0.3s cubic-bezier(0.16, 1, 0.3, 1),
    border-radius 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.eb__alert span {
  max-width: 0;
  overflow: hidden;
  white-space: nowrap;
  opacity: 0;
  transition:
    max-width 0.3s cubic-bezier(0.16, 1, 0.3, 1),
    opacity 0.2s ease-out;
}

.eb__alert:hover,
.eb__alert:focus-visible {
  gap: 8px;
  padding: 0 18px 0 14px;
  border-radius: 8px;
}

.eb__alert:hover span,
.eb__alert:focus-visible span {
  max-width: 180px;
  opacity: 1;
}

.eb-swap-enter-active,
.eb-swap-leave-active {
  transition:
    opacity 0.2s ease-out,
    transform 0.2s ease-out;
}

.eb-swap-enter-from {
  opacity: 0;
  transform: translateY(4px);
}

.eb-swap-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .eb__alert,
  .eb__alert span,
  .eb__toggle svg,
  .eb-swap-enter-active,
  .eb-swap-leave-active {
    transition: none;
  }
}

@media (max-width: 1100px) {
  .eb__bar {
    flex-wrap: wrap;
  }
}

@media (max-width: 720px) {
  .eb__title,
  .eb__bar {
    padding-inline: 16px;
  }

  .eb__sheet {
    padding: 12px 16px 24px;
  }

  .eb__drop--wide {
    width: 100%;
  }

  .eb__lead {
    width: auto;
    min-width: 0;
    max-width: 170px;
    padding-left: calc(10px + var(--level, 0) * 14px);
    white-space: normal;
    line-height: 1.25;
  }

  td {
    min-width: 116px;
  }

  .eb__dock {
    padding-bottom: 24px;
  }

  .eb__action {
    flex-wrap: wrap;
  }
}
</style>
