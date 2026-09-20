<script setup lang="ts">
import { ChevronLeft, ChevronRight, ChevronsUpDown, X } from '@lucide/vue'
import type { CajaResponse, CajaCompany, CashStatus } from '../../shared/types/embat'

const STATUS: Record<CashStatus, string> = {
  alerta: 'Alerta',
  oportunidad: 'Oportunidad',
  vigilancia: 'En vigilancia',
}

const GROUPS: { id: CashStatus; label: string; hint: string }[] = [
  { id: 'alerta', label: 'Alerta', hint: 'La caja operativa no cubre lo que sale' },
  { id: 'oportunidad', label: 'Oportunidad', hint: 'Hay excedente que se puede colocar' },
  { id: 'vigilancia', label: 'En vigilancia', hint: 'Ni rotura ni excedente claro' },
]

const HEALTH: Record<string, string> = {
  sano: 'Sana',
  vigilar: 'En vigilancia',
  riesgo: 'En riesgo',
}

const ACTION: Record<'prestar' | 'financiar', string> = {
  prestar: 'Hay excedente sano: se le puede ofrecer rendimiento por su caja.',
  financiar: 'Va a romper caja: se le puede ofrecer un puente de financiación.',
}

const { data: caja, pending, error, refresh } = await useAsyncData('embat-caja', () =>
  $fetch<CajaResponse>('/api/embat/caja'),
)
const filter = ref<CashStatus | 'todas'>('todas')
const detalle = ref<CajaCompany | null>(null)
const abiertos = ref(new Set<CashStatus>(['alerta', 'oportunidad', 'vigilancia']))

const visible = computed(() => {
  const rows = caja.value?.companies || []
  return filter.value === 'todas' ? rows : rows.filter((row) => row.status === filter.value)
})
const gruposVisibles = computed(() =>
  filter.value === 'todas' ? GROUPS : GROUPS.filter((grupo) => grupo.id === filter.value),
)
const todoAbierto = computed(() => gruposVisibles.value.every((grupo) => abiertos.value.has(grupo.id)))
watch(filter, (id) => {
  if (id === 'todas') return
  const next = new Set(abiertos.value)
  next.add(id)
  abiertos.value = next
})

function plegar(id: CashStatus) {
  const next = new Set(abiertos.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  abiertos.value = next
}

function plegarTodo() {
  abiertos.value = todoAbierto.value
    ? new Set()
    : new Set<CashStatus>(gruposVisibles.value.map((grupo) => grupo.id))
}

function porEstado(estado: CashStatus) {
  return visible.value.filter((row) => row.status === estado)
}

/* El orden real de la ficha: todas las empresas del filtro activo, en el orden en que
 * caen las tres tablas. Así ‹ / › y j/k recorren exactamente lo que se ve en pantalla. */
const flatOrder = computed(() => gruposVisibles.value.flatMap((grupo) => porEstado(grupo.id)))
const detalleIndex = computed(() =>
  detalle.value ? flatOrder.value.findIndex((row) => row.company_id === detalle.value!.company_id) : -1,
)
const canPrev = computed(() => detalleIndex.value > 0)
const canNext = computed(() => detalleIndex.value >= 0 && detalleIndex.value < flatOrder.value.length - 1)

function money(value: number | null | undefined, currency: string) {
  if (value == null) return '—'
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(value)
}

function months(value: number | null | undefined) {
  if (value == null) return '—'
  return `${value.toLocaleString('es-ES', { maximumFractionDigits: 1 })} meses`
}

function ratio(value: number | null | undefined) {
  if (value == null) return '—'
  return `${(value * 100).toLocaleString('es-ES', { maximumFractionDigits: 0 })} %`
}

function nEmpresas(n: number) {
  return `${n} ${n === 1 ? 'empresa' : 'empresas'}`
}

function whenMonth(value: string | null) {
  if (!value) return null
  return new Intl.DateTimeFormat('es-ES', { month: 'long', year: 'numeric', timeZone: 'UTC' }).format(
    new Date(`${value}-01T00:00:00Z`),
  )
}

/* Abrir y cerrar es el mismo gesto: pulsar la fila que ya está abierta la cierra,
 * igual que el panel de revisión de noticias. */
function toggle(company: CajaCompany) {
  detalle.value = detalle.value?.company_id === company.company_id ? null : company
}

function close() {
  detalle.value = null
}

/* Un enlace, botón o casilla dentro de la fila resuelve su propio gesto: la fila no
 * debe abrir el panel por encima de lo que el usuario ya ha pulsado. */
function onRowClick(company: CajaCompany, event: MouseEvent) {
  if ((event.target as HTMLElement | null)?.closest('a, button, input')) return
  toggle(company)
}

function step(delta: 1 | -1) {
  if (!flatOrder.value.length) return
  const from = detalleIndex.value
  const next = from < 0 ? 0 : Math.min(flatOrder.value.length - 1, Math.max(0, from + delta))
  detalle.value = flatOrder.value[next] ?? null
}

function onKeydown(event: KeyboardEvent) {
  if (!detalle.value) return
  if (event.key === 'Escape') {
    close()
  } else if (event.key === 'j' || event.key === 'ArrowDown') {
    event.preventDefault()
    step(1)
  } else if (event.key === 'k' || event.key === 'ArrowUp') {
    event.preventDefault()
    step(-1)
  }
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="embat-app" :class="{ 'embat-app--panel-open': !!detalle }">
    <header class="embat-app__title">
      <h1>Caja</h1>
      <div class="embat-app__tools">
        <button
          type="button"
          class="embat-app__icon"
          :aria-label="todoAbierto ? 'Plegar todo' : 'Desplegar todo'"
          @click="plegarTodo"
        >
          <ChevronsUpDown :size="16" aria-hidden="true" />
        </button>
        <div class="embat-app__seg" role="radiogroup" aria-label="Filtrar por estado de caja">
          <button
            v-for="option in (['todas', 'alerta', 'oportunidad', 'vigilancia'] as const)"
            :key="option"
            type="button"
            role="radio"
            :aria-checked="filter === option"
            @click="filter = option"
          >
            {{ option === 'todas' ? 'Todas' : STATUS[option] }}
          </button>
        </div>
      </div>
    </header>

    <dl v-if="caja" class="embat-app__pulse">
      <div data-tone="alerta">
        <dt>En alerta</dt>
        <dd>{{ caja.counts.alerta }}</dd>
      </div>
      <div data-tone="oportunidad">
        <dt>Oportunidad</dt>
        <dd>{{ caja.counts.oportunidad }}</dd>
      </div>
      <div data-tone="vigilancia">
        <dt>En vigilancia</dt>
        <dd>{{ caja.counts.vigilancia }}</dd>
      </div>
    </dl>

    <section class="embat-app__sheet" :aria-busy="pending">
      <p v-if="pending" class="embat-app__state">Leyendo la tesorería.</p>
      <p v-else-if="error" class="embat-app__state" role="alert">
        No se pudo leer la tesorería.
        <button type="button" @click="refresh()">Reintentar</button>
      </p>
      <p v-else-if="!caja?.companies.length" class="embat-app__state">
        No hay empresas en el portfolio de caja.
      </p>

      <template v-else>
        <article v-for="grupo in gruposVisibles" :key="grupo.id" class="embat-app__group">
          <header>
            <button type="button" :aria-expanded="abiertos.has(grupo.id)" @click="plegar(grupo.id)">
              <ChevronRight :size="16" aria-hidden="true" />
            </button>
            <b>{{ grupo.label }}</b>
            <span>{{ grupo.hint }}</span>
            <em>{{ nEmpresas(porEstado(grupo.id).length) }}</em>
          </header>
          <table
            v-if="abiertos.has(grupo.id) && porEstado(grupo.id).length"
            class="caja__rows"
            :aria-label="`${grupo.label}: caja operativa y financiera`"
          >
            <!-- Cada estado es su propia tabla: sin estas medidas el importe de caja y el de
             * deuda caen en una vertical distinta en cada grupo y la columna queda en zigzag. -->
            <colgroup>
              <col />
              <col class="caja__rows-caja" />
              <col class="caja__rows-deuda" />
              <col class="caja__rows-estado" />
            </colgroup>
            <tbody>
              <tr
                v-for="company in porEstado(grupo.id)"
                :key="company.company_id"
                :class="{ 'is-on': detalle?.company_id === company.company_id }"
                @click="onRowClick(company, $event)"
              >
                <th scope="row">
                  <button
                    type="button"
                    class="caja__rowtitle"
                    :aria-expanded="detalle?.company_id === company.company_id"
                    @click="toggle(company)"
                  >
                    {{ company.name }}
                  </button>
                  <small>{{ company.sector }}</small>
                </th>
                <td class="embat-app__amount">
                  {{ money(company.operativa.cash_end, company.currency) }}
                  <small>{{ months(company.operativa.runway_m) }}</small>
                </td>
                <td>
                  {{ money(company.financiera.debt_outstanding, company.currency) }}
                  <small>cuota {{ money(company.financiera.debt_service, company.currency) }}</small>
                </td>
                <td class="embat-app__meta">{{ STATUS[company.status] }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else-if="abiertos.has(grupo.id)" class="embat-app__empty">Ninguna empresa en este estado.</p>
        </article>
      </template>
    </section>

    <Transition name="caja-panel">
      <aside
        v-if="detalle"
        class="caja__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="caja-ficha-title"
      >
        <header class="caja__panel-head">
          <div class="caja__panel-nav">
            <button type="button" :disabled="!canPrev" aria-label="Empresa anterior" @click="step(-1)">
              <ChevronLeft :size="16" aria-hidden="true" />
            </button>
            <button type="button" :disabled="!canNext" aria-label="Empresa siguiente" @click="step(1)">
              <ChevronRight :size="16" aria-hidden="true" />
            </button>
          </div>
          <button type="button" class="caja__panel-close" aria-label="Cerrar" @click="close">
            <X :size="16" aria-hidden="true" />
          </button>
        </header>

        <div class="caja__panel-body">
          <p class="caja__panel-eyebrow">
            {{ detalle.sector }}
            <span v-if="whenMonth(detalle.month)"> · datos de {{ whenMonth(detalle.month) }}</span>
          </p>
          <h2 id="caja-ficha-title">{{ detalle.name }}</h2>
          <div class="caja__panel-badges">
            <span class="caja__badge" :data-tone="detalle.status">{{ STATUS[detalle.status] }}</span>
            <span v-if="detalle.health_band" class="caja__badge caja__badge--outline">
              Nota {{ HEALTH[detalle.health_band] ?? detalle.health_band }}
            </span>
          </div>
          <p class="caja__panel-why">{{ detalle.why }}</p>
          <p v-if="detalle.action" class="caja__panel-action">{{ ACTION[detalle.action] }}</p>

          <dl class="caja__panel-metrics">
            <div>
              <dt>Dinero en la cuenta</dt>
              <dd>{{ money(detalle.operativa.cash_end, detalle.currency) }}</dd>
            </div>
            <div>
              <dt>Meses cubiertos</dt>
              <dd>{{ months(detalle.operativa.runway_m) }}</dd>
            </div>
            <div>
              <dt>Entra frente a sale</dt>
              <dd>{{ money(detalle.operativa.net_op, detalle.currency) }}</dd>
            </div>
            <div>
              <dt>Deuda viva</dt>
              <dd>{{ money(detalle.financiera.debt_outstanding, detalle.currency) }}</dd>
            </div>
            <div>
              <dt>Cuota del mes</dt>
              <dd>{{ money(detalle.financiera.debt_service, detalle.currency) }}</dd>
            </div>
            <div>
              <dt>Póliza dispuesta</dt>
              <dd>{{ ratio(detalle.financiera.debt_util) }}</dd>
            </div>
          </dl>

          <section class="caja__panel-section">
            <h3>Cómo se ha evaluado</h3>
            <EmbatCajaTrend :company-id="detalle.company_id" :currency="detalle.currency" />
          </section>

          <p class="embat-app__note">
            Operativa es el dinero que deja el negocio. Financiera es lo que se debe y lo que se paga de
            deuda. Alerta y oportunidad salen de la caja, no del score.
          </p>
        </div>
      </aside>
    </Transition>
  </div>
</template>

<style scoped>
/* Las tres tablas comparten rejilla para que caja, deuda y estado caigan en la misma
 * vertical al saltar de un grupo a otro. Con reparto libre cada tabla se medía sola y el
 * ancho de la tabla más larga se salía del panel, comiéndose el margen derecho. */
.caja__rows {
  table-layout: fixed;
}
.caja__rows-caja {
  width: 21%;
}
.caja__rows-deuda {
  width: 23%;
}
.caja__rows-estado {
  width: 16%;
}

/* Con la rejilla fija un nombre largo ya no puede empujar los importes: se recorta. */
.caja__rows th[scope='row'],
.caja__rows th[scope='row'] small,
.caja__rows td,
.caja__rows td small {
  overflow: hidden;
  text-overflow: ellipsis;
}

/* El nombre es un botón sin verse como uno: lleva el foco de teclado y el
 * aria-expanded de la ficha, pero se lee igual que el resto de la fila. */
.caja__rowtitle {
  display: block;
  width: 100%;
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  font-weight: inherit;
  text-align: inherit;
  cursor: pointer;
}
.caja__rowtitle:focus-visible {
  outline: 2px solid var(--ea-blue);
  outline-offset: 2px;
  border-radius: 3px;
}

/* ── Panel: ficha acoplada al borde derecho, no una tarjeta flotante ────────── */
.embat-app {
  --caja-panel-w: min(440px, 92vw);
}

/* Con el panel abierto la tabla cede el ancho que ocupa la ficha, igual que hace
 * el body de la cola de revisión: así ninguna columna queda tapada detrás. */
@media (min-width: 1041px) {
  .embat-app--panel-open .embat-app__sheet {
    padding-right: calc(var(--caja-panel-w) + 40px);
    transition: padding-right 0.22s cubic-bezier(0.22, 1, 0.36, 1);
  }
}

.caja__panel {
  position: fixed;
  inset: 0 0 0 auto;
  z-index: 20;
  display: flex;
  flex-direction: column;
  width: var(--caja-panel-w);
  border-left: 1px solid var(--ea-line);
  background: #fff;
  color: var(--ea-text);
  box-shadow: -18px 0 44px -28px rgb(16 20 40 / 0.35);
}

.caja-panel-enter-active,
.caja-panel-leave-active {
  transition: transform 0.22s cubic-bezier(0.22, 1, 0.36, 1);
}
.caja-panel-enter-from,
.caja-panel-leave-to {
  transform: translateX(100%);
}

.caja__panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: none;
  height: 52px;
  padding: 0 14px;
  border-bottom: 1px solid var(--ea-line);
}

.caja__panel-nav {
  display: flex;
  gap: 4px;
}

.caja__panel-nav button,
.caja__panel-close {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 6px;
  background: none;
  color: var(--ea-body);
  cursor: pointer;
}
.caja__panel-nav button:hover:not(:disabled),
.caja__panel-close:hover {
  background: var(--ea-hover);
}
.caja__panel-nav button:disabled {
  color: var(--ea-line);
  cursor: default;
}

.caja__panel-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 20px 22px 26px;
}

.caja__panel-eyebrow {
  margin: 0 0 4px;
  color: var(--ea-muted);
  font-size: 11.5px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.caja__panel-body h2 {
  margin: 0 0 10px;
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.caja__panel-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.caja__badge {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 9px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 600;
}
.caja__badge[data-tone='alerta'] {
  background: color-mix(in srgb, var(--ea-red) 12%, transparent);
  color: var(--ea-red);
}
.caja__badge[data-tone='oportunidad'] {
  background: color-mix(in srgb, var(--ea-green) 12%, transparent);
  color: var(--ea-green);
}
.caja__badge[data-tone='vigilancia'] {
  background: color-mix(in srgb, var(--ea-amber) 14%, transparent);
  color: var(--ea-amber);
}
.caja__badge--outline {
  background: none;
  border: 1px solid var(--ea-line);
  color: var(--ea-muted);
  font-weight: 500;
}

.caja__panel-why {
  margin: 0;
  color: var(--ea-body);
  line-height: 1.5;
}

.caja__panel-action {
  margin: 10px 0 0;
  padding: 9px 11px;
  border-radius: 8px;
  background: var(--ea-hover);
  color: var(--ea-text);
  font-size: 12.5px;
  line-height: 1.45;
}

.caja__panel-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 18px;
  margin: 18px 0 0;
}
.caja__panel-metrics dt {
  color: var(--ea-muted);
}
.caja__panel-metrics dd {
  margin: 2px 0 0;
  font-weight: 600;
}

.caja__panel-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--ea-soft);
}
.caja__panel-section h3 {
  margin: 0 0 6px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--ea-text);
}

.embat-app__note {
  margin: 18px 0 0;
  padding-top: 12px;
  border-top: 1px solid var(--ea-soft);
  color: var(--ea-muted);
  line-height: 1.5;
}

/* Bajo 1041px la ficha deja de acoplarse al lateral: se convierte en una hoja
 * que sube desde abajo, como en la cola de revisión. */
@media (max-width: 1040px) {
  .caja__panel {
    inset: auto 0 0 0;
    max-height: 82vh;
    width: auto;
    border-left: 0;
    border-top: 1px solid var(--ea-line);
    border-radius: 14px 14px 0 0;
    box-shadow: 0 -18px 44px -28px rgb(16 20 40 / 0.4);
  }
  .caja-panel-enter-from,
  .caja-panel-leave-to {
    transform: translateY(100%);
  }
}

@media (prefers-reduced-motion: reduce) {
  .caja-panel-enter-active,
  .caja-panel-leave-active {
    transition: none;
  }
}
</style>
