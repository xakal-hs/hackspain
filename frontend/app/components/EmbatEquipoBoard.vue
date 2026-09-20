<script setup lang="ts">
import type { EmployeeTeam, EmployeesResponse } from '../../shared/types/embat'

const TEAM: { id: EmployeeTeam; label: string; note: string }[] = [
  {
    id: 'account_management',
    label: 'Comercial',
    note: 'Coge las peticiones de financiación. El aviso entra en la cola y se asigna al que menos abiertos tiene.',
  },
  {
    id: 'customer_success',
    label: 'Customer success',
    note: 'Sigue al cliente cuando ya está dentro. No recibe la cola de financiación.',
  },
]

const { data, error, pending } = await useAsyncData('embat-employees', () =>
  $fetch<EmployeesResponse>('/api/embat/employees'),
)

const grouped = computed(() => {
  const rows = data.value?.employees || []
  return {
    account_management: rows.filter((row) => row.team === 'account_management'),
    customer_success: rows.filter((row) => row.team === 'customer_success'),
  }
})
</script>

<template>
  <div class="wk__grid equipo">
    <section class="panel span-12">
      <header class="panel__bar">
        <h2 class="panel__title">Equipo Embat</h2>
        <span class="chip chip--neutral">{{ data?.employees.length || 0 }} personas</span>
      </header>
      <p class="lead-line">
        Comercial y customer success, de tesorería real. Quien pide financiación en Empresa
        cae en un comercial de esta lista, no en un nombre inventado.
      </p>
      <dl v-if="data" class="caja__pulse">
        <div data-tone="mint">
          <dt>Comercial</dt>
          <dd>{{ data.counts.account_management }}</dd>
        </div>
        <div data-tone="amber">
          <dt>Customer success</dt>
          <dd>{{ data.counts.customer_success }}</dd>
        </div>
      </dl>
      <p v-if="pending" class="empty">Leyendo el equipo.</p>
      <p v-else-if="error" class="empty">No se pudo leer el equipo.</p>
    </section>

    <section v-for="team in TEAM" :key="team.id" class="panel span-6">
      <header class="panel__bar">
        <h2 class="panel__title">{{ team.label }}</h2>
        <span class="chip chip--neutral">{{ grouped[team.id].length }}</span>
      </header>
      <p class="lead-line">{{ team.note }}</p>
      <ol class="equipo__list">
        <li v-for="person in grouped[team.id]" :key="person.id">
          <b>{{ person.name }}</b>
          <span>{{ person.job_title }}</span>
        </li>
      </ol>
    </section>
  </div>
</template>

<style scoped>
.caja__pulse {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
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
.caja__pulse > div[data-tone='mint'] dd { color: var(--mint-ink); }
.caja__pulse > div[data-tone='amber'] dd { color: var(--amber-ink); }
.equipo__list {
  display: grid;
  gap: 8px;
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
}
.equipo__list li {
  display: grid;
  gap: 2px;
  padding: 12px 12px 10px;
  border: 1px solid var(--line);
  border-radius: var(--r-inner);
  background: var(--panel-raised);
}
.equipo__list b {
  font-size: 14px;
  font-weight: 500;
}
.equipo__list span {
  color: var(--text-muted);
  font-size: 12.5px;
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
