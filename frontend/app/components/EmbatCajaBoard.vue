<script setup lang="ts">
import { ChevronRight, ChevronsUpDown } from '@lucide/vue'
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

function pick(company: CajaCompany) {
  detalle.value = company
}
</script>

<template>
  <div class="embat-app">
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
          <table v-if="abiertos.has(grupo.id) && porEstado(grupo.id).length" :aria-label="`${grupo.label}: caja operativa y financiera`">
            <tbody>
              <tr
                v-for="company in porEstado(grupo.id)"
                :key="company.company_id"
                :class="{ 'is-on': detalle?.company_id === company.company_id }"
                @click="pick(company)"
              >
                <th scope="row">
                  {{ company.name }}
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

    <aside
      v-if="detalle"
      class="embat-app__dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="caja-ficha-title"
    >
      <header>
        <div>
          <h2 id="caja-ficha-title">{{ detalle.name }}</h2>
          <p>{{ detalle.why }}</p>
        </div>
        <button type="button" @click="detalle = null">Cerrar</button>
      </header>
      <dl>
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
      <p class="embat-app__note">
        Operativa es el dinero que deja el negocio. Financiera es lo que se debe y lo que se paga de
        deuda. Alerta y oportunidad salen de la caja, no del score.
      </p>
    </aside>
  </div>
</template>
