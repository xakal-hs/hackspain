<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { ChevronDown, ChevronRight, ChevronsUpDown, TrendingUp, TriangleAlert } from '@lucide/vue'
import type { Cashflow, CashflowMonth, ForecastMonth } from '../../shared/types/company'

const { selectedId, company, sector } = useSelectedCompany()

const flujo = useQuery({
  queryKey: computed(() => ['flujo', selectedId.value]),
  queryFn: () => $fetch<Cashflow>(`/api/flujo/${encodeURIComponent(selectedId.value)}`),
  staleTime: 60 * 1000,
})

type Period = '3M' | '6M' | '12M' | 'YTD'
const periods: Period[] = ['3M', '6M', '12M', 'YTD']
const period = ref<Period>('3M')
const projection = ref<'none' | '3m'>('3m')

/* Una columna es un mes real del panel o un mes previsto; las dos saben de qué saldo parten. */
type Column =
  | { key: string; month: string; ahead: false; start: number | null; m: CashflowMonth }
  | { key: string; month: string; ahead: true; start: number; f: ForecastMonth }

const n = (v: number | null | undefined) => Number(v ?? 0)

const columns = computed<Column[]>(() => {
  const panel = flujo.data.value?.panel ?? []
  const take = { '3M': 3, '6M': 6, '12M': 12, YTD: panel.filter((m) => m.month.startsWith(panel.at(-1)?.month.slice(0, 4) ?? '')).length }[period.value]
  const real: Column[] = panel.map((m, i) => ({
    key: m.month,
    month: m.month,
    ahead: false as const,
    start: i > 0 ? panel[i - 1]!.cash_end : m.cash_end == null ? null : m.cash_end - n(m.net_bank),
    m,
  })).slice(-take)
  const forecast = flujo.data.value?.forecast
  if (projection.value === 'none' || !forecast) return real
  let start = forecast.cash
  const ahead: Column[] = forecast.months.map((f) => {
    const col = { key: `p-${f.month}`, month: f.month, ahead: true as const, start, f }
    start += f.cobros + f.proveedores + f.nominas + f.seguridad_social + f.deuda
    return col
  })
  return [...real, ...ahead]
})

/* Las filas copian el esqueleto del flujo de caja de Embat. Lo que la previsión no modela
 * (impuestos, comisiones, inversión, transferencias) queda en blanco, no a cero. */
interface Row {
  id: string
  label: string
  level: number
  parent?: string
  strong?: boolean
  value: (c: Column) => number | null
}

const operating = (c: Column) =>
  c.ahead ? c.f.cobros + c.f.proveedores + c.f.nominas + c.f.seguridad_social : n(c.m.inflow_op) - n(c.m.outflow_op)
const payments = (c: Column) =>
  c.ahead ? c.f.proveedores + c.f.nominas + c.f.seguridad_social : -n(c.m.outflow_op)
const real = (c: Column, pick: (m: CashflowMonth) => number | null) => (c.ahead ? null : pick(c.m))

const rows: Row[] = [
  { id: 'inicio', label: 'Tesorería al inicio del mes', level: 0, strong: true, value: (c) => c.start },
  { id: 'operativas', label: 'Actividades operativas', level: 0, value: operating },
  { id: 'cobros', label: 'Cobros', level: 1, parent: 'operativas', value: (c) => (c.ahead ? c.f.cobros : n(c.m.inflow_op)) },
  { id: 'pagos', label: 'Pagos', level: 1, parent: 'operativas', value: payments },
  {
    id: 'proveedores', label: 'Proveedores y otros pagos', level: 2, parent: 'pagos',
    value: (c) => c.ahead ? c.f.proveedores
      : -(n(c.m.outflow_op) - n(c.m.out_salary) - n(c.m.out_social_security) - n(c.m.out_tax) - n(c.m.out_fin_cost)),
  },
  { id: 'nominas', label: 'Nóminas', level: 2, parent: 'pagos', value: (c) => (c.ahead ? c.f.nominas : -n(c.m.out_salary)) },
  { id: 'ss', label: 'Seguridad social', level: 2, parent: 'pagos', value: (c) => (c.ahead ? c.f.seguridad_social : -n(c.m.out_social_security)) },
  { id: 'impuestos', label: 'Impuestos', level: 2, parent: 'pagos', value: (c) => real(c, (m) => -n(m.out_tax)) },
  { id: 'comisiones', label: 'Comisiones e intereses', level: 2, parent: 'pagos', value: (c) => real(c, (m) => -n(m.out_fin_cost)) },
  { id: 'financiacion', label: 'Actividades de financiación', level: 0, value: (c) => (c.ahead ? c.f.deuda : -n(c.m.debt_service)) },
  {
    id: 'inversion', label: 'Actividades de inversión', level: 0,
    value: (c) => real(c, (m) => n(m.net_bank) - (n(m.inflow_op) - n(m.outflow_op) - n(m.debt_service) + n(m.transfer_net))),
  },
  { id: 'transferencias', label: 'Transferencias', level: 0, value: (c) => real(c, (m) => n(m.transfer_net)) },
  {
    id: 'final', label: 'Tesorería al final del mes', level: 0, strong: true,
    value: (c) => c.ahead ? c.start + c.f.cobros + c.f.proveedores + c.f.nominas + c.f.seguridad_social + c.f.deuda : c.m.cash_end,
  },
]

const parents = new Set(rows.flatMap((r) => (r.parent ? [r.parent] : [])))
const open = ref(new Set(['operativas']))
const allOpen = computed(() => [...parents].every((id) => open.value.has(id)))

function toggle(id: string) {
  const next = new Set(open.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  open.value = next
}

function toggleAll() {
  open.value = allOpen.value ? new Set() : new Set(parents)
}

const visibleRows = computed(() =>
  rows.filter((row) => {
    let parent = row.parent
    while (parent) {
      if (!open.value.has(parent)) return false
      parent = rows.find((r) => r.id === parent)?.parent
    }
    return true
  }),
)

const amount = new Intl.NumberFormat('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: 'always' } as Intl.NumberFormatOptions)
const cell = (v: number | null) => (v == null || !Number.isFinite(v) ? '—' : amount.format(Math.abs(v) < 0.005 ? 0 : v))

const monthNames = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']
const monthLabel = (ym: string) => `${monthNames[Number(ym.slice(5, 7)) - 1]} - ${ym.slice(2, 4)}`

const currency = computed(() => flujo.data.value?.forecast?.currency || company.value?.currency || 'EUR')
const money = (v: number) =>
  new Intl.NumberFormat('es-ES', { style: 'currency', currency: currency.value, maximumFractionDigits: 0, useGrouping: 'always' } as Intl.NumberFormatOptions)
    .format(v)
    .replace('-', '−')
const date = (iso: string) => new Date(`${iso}T00:00:00Z`)
const dayMonth = (iso: string) =>
  new Intl.DateTimeFormat('es-ES', { day: 'numeric', month: 'long', timeZone: 'UTC' }).format(date(iso))
/* «Del 17 al 24 de septiembre», y solo con los dos meses cuando el tramo cruza de uno a otro. */
const span = (from: string, to: string) =>
  from.slice(0, 7) === to.slice(0, 7) ? `Del ${Number(from.slice(8))} al ${dayMonth(to)}` : `Del ${dayMonth(from)} al ${dayMonth(to)}`
const sameMonth = (a: string, b: string) => a.slice(0, 7) === b.slice(0, 7)

/* Al cambiar de periodo o de empresa, la tabla se abre por el final: lo último y la previsión. */
const scroller = ref<HTMLElement | null>(null)
watch([columns, scroller], () => nextTick(() => scroller.value?.scrollTo({ left: scroller.value.scrollWidth })), { flush: 'post' })

const rotura = computed(() => flujo.data.value?.forecast?.rotura ?? null)
const excedente = computed(() => flujo.data.value?.forecast?.excedente ?? null)

/* Cada empresa lleva su propia marca, como el espacio de trabajo en Embat: al cambiar de
 * empresa en la demo cambian a la vez las iniciales, el color y la tabla. */
const initials = computed(() => {
  const words = (company.value?.top_sector || '').split(/\s+/).filter(Boolean)
  return (words.length ? words[0]!.slice(0, 2) : selectedId.value.slice(-2)).toUpperCase()
})
const hue = computed(() => (Number(selectedId.value.replace(/\D/g, '')) * 47) % 360)
const sectorLabel = computed(() => sector.value.charAt(0).toUpperCase() + sector.value.slice(1))
</script>

<template>
  <div class="centinela tz fc">
    <header class="fc__head">
      <h1>Flujo de caja</h1>
      <Transition name="fc-swap" mode="out-in">
        <p :key="selectedId" class="fc__company" :style="{ '--hue': hue }">
          <i aria-hidden="true">{{ initials }}</i>
          <span><b>{{ selectedId }}</b><small>{{ sectorLabel }} · {{ currency }}</small></span>
        </p>
      </Transition>
    </header>

    <div class="fc__bar">
      <label class="fc__select">
        <TrendingUp :size="15" aria-hidden="true" />
        <span class="sr-only">Proyección</span>
        <select v-model="projection" :disabled="!flujo.data.value?.forecast">
          <option value="none">Sin proyección</option>
          <option value="3m">{{ flujo.data.value?.forecast || flujo.isPending.value ? 'Proyección a 3 meses' : 'Sin proyección disponible' }}</option>
        </select>
        <ChevronDown :size="15" aria-hidden="true" />
      </label>
      <div class="fc__seg" role="radiogroup" aria-label="Periodo">
        <button
          v-for="p in periods"
          :key="p"
          type="button"
          role="radio"
          :aria-checked="period === p"
          @click="period = p"
        >
          {{ p }}
        </button>
      </div>
    </div>

    <Transition name="fc-swap" mode="out-in">
      <section :key="selectedId" class="fc__card" :aria-busy="flujo.isPending.value">
        <p v-if="flujo.isPending.value" class="fc__state">Cargando movimientos…</p>
        <p v-else-if="flujo.isError.value" class="fc__state" role="alert">
          No se pudo cargar el flujo de caja.
          <button type="button" @click="flujo.refetch()">Reintentar</button>
        </p>
        <p v-else-if="!columns.length" class="fc__state">Esta empresa no tiene movimientos bancarios conectados.</p>
        <div v-else ref="scroller" class="fc__scroll">
          <table>
            <thead>
              <tr>
                <th scope="col" class="fc__lead">
                  <button
                    type="button"
                    class="fc__all"
                    :aria-label="allOpen ? 'Contraer todo' : 'Desplegar todo'"
                    @click="toggleAll"
                  >
                    <ChevronsUpDown :size="15" aria-hidden="true" />
                  </button>
                </th>
                <th v-for="c in columns" :key="c.key" scope="col" :class="{ 'is-ahead': c.ahead }">
                  {{ monthLabel(c.month) }}<small v-if="c.ahead">Previsión</small>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in visibleRows" :key="row.id" :class="{ 'is-strong': row.strong }">
                <th scope="row" class="fc__lead" :style="{ '--level': row.level }">
                  <button
                    v-if="parents.has(row.id)"
                    type="button"
                    class="fc__toggle"
                    :aria-expanded="open.has(row.id)"
                    @click="toggle(row.id)"
                  >
                    <ChevronRight :size="15" aria-hidden="true" />{{ row.label }}
                  </button>
                  <span v-else>{{ row.label }}</span>
                </th>
                <td
                  v-for="c in columns"
                  :key="c.key"
                  :class="{ 'is-ahead': c.ahead, 'is-empty': row.value(c) == null }"
                >
                  {{ cell(row.value(c)) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </Transition>

    <div v-if="rotura && projection === '3m'" class="fc__act">
      <p>
        <b>Vas a romper caja.</b>{{ ' ' }}
        <template v-if="rotura.to">
          {{ span(rotura.from, rotura.to) }} llegas a {{ money(rotura.low) }}.
        </template>
        <template v-else>Desde el {{ dayMonth(rotura.from) }} llegas a {{ money(rotura.low) }}.</template>
        <template v-if="rotura.rescue">
          El cobro de {{ money(rotura.rescue.amount) }} entra el
          {{ rotura.to && sameMonth(rotura.to, rotura.rescue.date) ? Number(rotura.rescue.date.slice(8)) : dayMonth(rotura.rescue.date) }}.
        </template>
      </p>
      <button type="button" class="fc__alert" aria-label="Pedir financiación">
        <TriangleAlert :size="17" aria-hidden="true" /><span>Pedir financiación</span>
      </button>
    </div>
    <div v-else-if="excedente" class="fc__act">
      <p>{{ money(excedente.amount) }} por encima de tu colchón de tres meses de gasto.</p>
      <button type="button" class="fc__cta">Gana eficiencia prestando tu caja</button>
    </div>
  </div>
</template>

<style scoped>
.fc {
  gap: 16px;
}

.fc__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px 24px;
}

.fc__head h1 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 600;
  line-height: 1.2;
}

.fc__company {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
}

.fc__company i {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background: oklch(0.52 0.15 var(--hue));
  color: #fff;
  font: 700 12px/1 var(--font-display);
  font-style: normal;
  letter-spacing: 0.02em;
}

.fc__company span {
  display: grid;
}

.fc__company b {
  font-size: 13.5px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.fc__company small {
  font-size: 12px;
  color: var(--text-2);
}

.fc__bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.fc__select {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--card);
  color: var(--text-2);
}

.fc__select select {
  min-width: 170px;
  height: 100%;
  padding-right: 18px;
  border: 0;
  background: transparent;
  color: var(--text);
  font: 500 13px/1 var(--font-body);
  appearance: none;
  cursor: pointer;
}

.fc__select select:disabled {
  color: var(--text-3);
  cursor: default;
}

.fc__select > :last-child {
  position: absolute;
  right: 10px;
  pointer-events: none;
}

.fc__select:focus-within,
.fc__seg button:focus-visible,
.fc__all:focus-visible,
.fc__toggle:focus-visible,
.fc__cta:focus-visible,
.fc__alert:focus-visible,
.fc__state button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.fc__select select:focus {
  outline: none;
}

.fc__seg {
  display: flex;
  height: 36px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--card);
  overflow: hidden;
}

.fc__seg button {
  min-width: 46px;
  padding: 0 12px;
  border: 0;
  background: transparent;
  color: var(--text-2);
  font: 500 13px/1 var(--font-body);
  cursor: pointer;
}

.fc__seg button + button {
  border-left: 1px solid var(--border);
}

.fc__seg button[aria-checked='true'] {
  background: var(--wash);
  color: var(--text);
  font-weight: 600;
}

.fc__card {
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  background: var(--card);
  overflow: hidden;
}

.fc__state {
  margin: 0;
  padding: 28px 22px;
  font-size: 13.5px;
  color: var(--text-2);
}

.fc__state button {
  margin-left: 6px;
  padding: 0;
  border: 0;
  background: none;
  color: var(--accent);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}

.fc__scroll {
  overflow-x: auto;
  overscroll-behavior-x: contain;
}

table {
  width: 100%;
  min-width: max-content;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

th,
td {
  height: 36px;
  padding: 0 16px;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

thead th {
  height: 44px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-3);
  text-align: right;
  vertical-align: middle;
}

thead th small {
  display: block;
  margin-top: 2px;
  font-size: 10.5px;
  font-weight: 600;
  color: var(--ahead-ink);
}

td {
  min-width: 120px;
  text-align: right;
  color: var(--text-2);
}

td.is-empty {
  color: var(--text-3);
}

/* Los meses previstos llevan el color reservado a lo que el producto sabe antes de que
 * pase, y un filete discontinuo arriba, para que se lean sin depender del color. */
.is-ahead {
  background: var(--ahead-wash);
}

thead th.is-ahead {
  border-top: 2px dashed var(--ahead);
}

.fc__lead {
  position: sticky;
  left: 0;
  z-index: 1;
  min-width: 260px;
  padding-left: calc(14px + var(--level, 0) * 22px);
  background: var(--card);
  color: var(--text);
  font-weight: 400;
  text-align: left;
}

thead .fc__lead {
  padding-left: 10px;
}

tbody tr:last-child > * {
  border-bottom: 0;
}

tr.is-strong > * {
  font-weight: 600;
  color: var(--text);
}

/* Tintes opacos: la columna fija pasa por encima de los números al desplazar, y un
 * --wash translúcido (el del tema oscuro) los dejaría ver por debajo. */
tr.is-strong > td:not(.is-ahead),
tr.is-strong > .fc__lead {
  background: color-mix(in srgb, var(--text) 4%, var(--card));
}

tbody tr:hover > td:not(.is-ahead),
tbody tr:hover > .fc__lead {
  background: color-mix(in srgb, var(--text) 7%, var(--card));
}

.fc__lead > span {
  display: block;
  padding-left: 23px;
}

.fc__toggle,
.fc__all {
  display: inline-flex;
  align-items: center;
  text-align: left;
  gap: 8px;
  padding: 4px 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  cursor: pointer;
}

.fc__all {
  padding: 6px;
  border-radius: 6px;
  color: var(--text-2);
}

.fc__all:hover {
  background: var(--wash);
}

.fc__toggle svg {
  color: var(--text-3);
  transition: transform 0.18s var(--ease);
}

.fc__toggle[aria-expanded='true'] svg {
  transform: rotate(90deg);
}

/* Abajo, centrado, como la barra flotante de Embat: la única acción de la página. */
.fc__act {
  position: sticky;
  bottom: 18px;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 16px;
  justify-self: center;
  max-width: 100%;
  padding: 8px 8px 8px 18px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--card);
  box-shadow: 0 8px 24px -12px rgb(12 14 40 / 0.28);
}

.fc__act p {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.45;
  color: var(--text-2);
}

.fc__act b {
  font-weight: 600;
  color: var(--text);
}

.fc__cta {
  flex: none;
  height: 40px;
  padding: 0 18px;
  border: 0;
  border-radius: var(--r-md);
  background: var(--accent-solid);
  color: var(--accent-on);
  font: 600 13.5px/1 var(--font-body);
  cursor: pointer;
}

.fc__cta:hover {
  background: color-mix(in srgb, var(--accent-solid) 88%, #000);
}

/* El aviso es un icono negro; al pasar por encima se abre en un botón normal. */
.fc__alert {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 0;
  height: 40px;
  padding: 0 11px;
  border: 0;
  border-radius: 999px;
  background: #0b0c14;
  color: #fff;
  font: 600 13.5px/1 var(--font-body);
  cursor: pointer;
  transition:
    gap 0.3s cubic-bezier(0.16, 1, 0.3, 1),
    padding 0.3s cubic-bezier(0.16, 1, 0.3, 1),
    border-radius 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.fc__alert span {
  max-width: 0;
  overflow: hidden;
  white-space: nowrap;
  opacity: 0;
  transition:
    max-width 0.3s cubic-bezier(0.16, 1, 0.3, 1),
    opacity 0.2s ease-out;
}

.fc__alert:hover,
.fc__alert:focus-visible {
  gap: 8px;
  padding: 0 18px 0 14px;
  border-radius: var(--r-md);
}

.fc__alert:hover span,
.fc__alert:focus-visible span {
  max-width: 180px;
  opacity: 1;
}

:root[data-theme='dark'] .fc__alert {
  box-shadow: 0 0 0 1px rgb(255 255 255 / 0.16);
}

.fc-swap-enter-active,
.fc-swap-leave-active {
  transition:
    opacity 0.2s ease-out,
    transform 0.2s ease-out;
}

.fc-swap-enter-from {
  opacity: 0;
  transform: translateY(4px);
}

.fc-swap-leave-to {
  opacity: 0;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

@media (prefers-reduced-motion: reduce) {
  .fc__alert,
  .fc__alert span,
  .fc__toggle svg,
  .fc-swap-enter-active,
  .fc-swap-leave-active {
    transition: none;
  }
}

@container (max-width: 640px) {
  /* En móvil la barra deja de flotar: taparía la última fila de la tabla. */
  .fc__act {
    position: static;
    flex-direction: column;
    align-items: stretch;
    padding: 14px;
  }

  .fc__alert {
    align-self: flex-start;
  }

  .fc__lead {
    min-width: 0;
    max-width: 150px;
    white-space: normal;
    line-height: 1.25;
  }

  th,
  td {
    padding: 0 12px;
  }

  td {
    min-width: 104px;
  }
}
</style>
