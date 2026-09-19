<script setup lang="ts">
import type { CajaResponse, CajaCompany, CashStatus } from '../../shared/types/embat'

const STATUS: Record<CashStatus, string> = {
  alerta: 'Alerta',
  oportunidad: 'Oportunidad',
  vigilancia: 'En vigilancia',
}

const { data: caja, pending, error } = await useAsyncData('embat-caja', () => $fetch<CajaResponse>('/api/embat/caja'))
const filter = ref<CashStatus | 'todas'>('todas')
const pickedId = ref('')

watch(
  () => caja.value?.companies,
  (rows) => {
    if (!rows?.length) return
    if (!rows.some((row) => row.company_id === pickedId.value))
      pickedId.value = rows.find((row) => row.status === 'alerta')?.company_id || rows[0]!.company_id
  },
  { immediate: true },
)

const visible = computed(() => {
  const rows = caja.value?.companies || []
  return filter.value === 'todas' ? rows : rows.filter((row) => row.status === filter.value)
})
const subject = computed(
  () => visible.value.find((row) => row.company_id === pickedId.value) || visible.value[0] || null,
)

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

function pick(row: CajaCompany) {
  pickedId.value = row.company_id
}
</script>

<template>
  <div class="wk__grid caja">
    <section class="panel span-12">
      <header class="panel__bar">
        <h2 class="panel__title">Caja del portfolio</h2>
        <span class="chip chip--neutral">20 empresas</span>
      </header>
      <p class="lead-line">
        Operativa es el dinero que deja el negocio. Financiera es lo que se debe
        y lo que se paga de deuda. Alerta y oportunidad salen de la caja, no del score.
      </p>
      <dl v-if="caja" class="caja__pulse">
        <div data-tone="crimson">
          <dt>En alerta</dt>
          <dd>{{ caja.counts.alerta }}</dd>
        </div>
        <div data-tone="mint">
          <dt>Oportunidad</dt>
          <dd>{{ caja.counts.oportunidad }}</dd>
        </div>
        <div data-tone="amber">
          <dt>En vigilancia</dt>
          <dd>{{ caja.counts.vigilancia }}</dd>
        </div>
      </dl>
      <p v-else-if="pending" class="empty">Leyendo la tesorería.</p>
      <p v-else-if="error" class="empty">No se pudo leer Supabase.</p>
    </section>

    <section class="panel span-8 list">
      <header class="panel__bar">
        <h2 class="panel__title">Empresas</h2>
        <div class="seg" role="radiogroup" aria-label="Filtrar por estado de caja">
          <button
            v-for="option in (['todas', 'alerta', 'oportunidad', 'vigilancia'] as const)"
            :key="option"
            type="button"
            role="radio"
            :aria-checked="filter === option"
            :class="{ 'is-on': filter === option }"
            @click="filter = option"
          >
            {{ option === 'todas' ? 'Todas' : STATUS[option] }}
          </button>
        </div>
      </header>
      <div class="ctable">
        <table>
          <caption class="sr-only">Estado de caja operativa y financiera del portfolio</caption>
          <thead>
            <tr>
              <th scope="col">Empresa</th>
              <th scope="col" class="num">Operativa</th>
              <th scope="col" class="num">Financiera</th>
              <th scope="col">Estado</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="company in visible"
              :key="company.company_id"
              :class="{ 'is-selected': company.company_id === subject?.company_id }"
            >
              <th scope="row">
                <button type="button" :aria-pressed="company.company_id === subject?.company_id" @click="pick(company)">
                  <b>{{ company.name }}</b>
                  <small>{{ company.sector }}</small>
                </button>
              </th>
              <td class="num">
                {{ money(company.operativa.cash_end, company.currency) }}
                <small class="caja__sub">{{ months(company.operativa.runway_m) }}</small>
              </td>
              <td class="num">
                {{ money(company.financiera.debt_outstanding, company.currency) }}
                <small class="caja__sub">cuota {{ money(company.financiera.debt_service, company.currency) }}</small>
              </td>
              <td>
                <span class="chip" :class="`chip--${company.status === 'alerta' ? 'crimson' : company.status === 'oportunidad' ? 'mint' : 'amber'}`">
                  {{ STATUS[company.status] }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="caja && !visible.length" class="empty">Ninguna empresa en este estado.</p>
    </section>

    <section v-if="subject" class="panel span-4 sheet">
      <header class="panel__bar">
        <h2 class="panel__title">{{ subject.name }}</h2>
        <span class="chip" :class="`chip--${subject.status === 'alerta' ? 'crimson' : subject.status === 'oportunidad' ? 'mint' : 'amber'}`">
          {{ STATUS[subject.status] }}
        </span>
      </header>
      <p class="sheet__why">{{ subject.why }}</p>
      <dl class="sheet__terms">
        <div>
          <dt>Dinero en la cuenta</dt>
          <dd>{{ money(subject.operativa.cash_end, subject.currency) }}</dd>
        </div>
        <div>
          <dt>Meses cubiertos</dt>
          <dd>{{ months(subject.operativa.runway_m) }}</dd>
        </div>
        <div>
          <dt>Entra frente a sale</dt>
          <dd>{{ money(subject.operativa.net_op, subject.currency) }}</dd>
        </div>
        <div>
          <dt>Deuda viva</dt>
          <dd>{{ money(subject.financiera.debt_outstanding, subject.currency) }}</dd>
        </div>
        <div>
          <dt>Cuota del mes</dt>
          <dd>{{ money(subject.financiera.debt_service, subject.currency) }}</dd>
        </div>
        <div>
          <dt>Póliza dispuesta</dt>
          <dd>{{ ratio(subject.financiera.debt_util) }}</dd>
        </div>
      </dl>
    </section>
  </div>
</template>

<style scoped>
.caja__pulse {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0;
  margin: 0 0 4px;
}
.caja__pulse > div {
  padding: 12px 18px 4px 0;
  border-right: 1px solid var(--line);
}
.caja__pulse > div:last-child { border-right: 0; padding-right: 0; }
.caja__pulse dt {
  margin: 0 0 4px;
  color: var(--text-muted);
  font-size: 12.5px;
}
.caja__pulse dd {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 32px;
  font-weight: 400;
  letter-spacing: -0.05em;
  font-variant-numeric: tabular-nums;
}
.caja__pulse > div[data-tone='crimson'] dd { color: var(--crimson-ink); }
.caja__pulse > div[data-tone='mint'] dd { color: var(--mint-ink); }
.caja__pulse > div[data-tone='amber'] dd { color: var(--amber-ink); }
.caja__sub {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-weight: 400;
}
@media (max-width: 720px) {
  .caja__pulse { grid-template-columns: 1fr; }
  .caja__pulse > div {
    border-right: 0;
    border-top: 1px solid var(--line);
    padding: 12px 0 0;
  }
  .caja__pulse > div:first-child { border-top: 0; padding-top: 0; }
}
</style>
