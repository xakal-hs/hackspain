<script setup lang="ts">
import { ChevronRight, ChevronsUpDown } from '@lucide/vue'
import type { EmployeeTeam, EmployeesResponse } from '../../shared/types/embat'

const TEAM: { id: EmployeeTeam; label: string; hint: string }[] = [
  {
    id: 'account_management',
    label: 'Comercial',
    hint: 'Coge las peticiones de financiación',
  },
  {
    id: 'customer_success',
    label: 'Customer success',
    hint: 'Sigue al cliente cuando ya está dentro',
  },
]

const { data, error, pending, refresh } = await useAsyncData('embat-employees', () =>
  $fetch<EmployeesResponse>('/api/embat/employees'),
)

const grouped = computed(() => {
  const rows = data.value?.employees || []
  return {
    account_management: rows.filter((row) => row.team === 'account_management'),
    customer_success: rows.filter((row) => row.team === 'customer_success'),
  }
})

const abiertos = ref(new Set<EmployeeTeam>(['account_management', 'customer_success']))
const todoAbierto = computed(() => TEAM.every((team) => abiertos.value.has(team.id)))

function plegar(id: EmployeeTeam) {
  const next = new Set(abiertos.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  abiertos.value = next
}

function plegarTodo() {
  abiertos.value = todoAbierto.value
    ? new Set()
    : new Set<EmployeeTeam>(['account_management', 'customer_success'])
}

function nPersonas(n: number) {
  return `${n} ${n === 1 ? 'persona' : 'personas'}`
}
</script>

<template>
  <div class="embat-app">
    <header class="embat-app__title">
      <h1>Equipo</h1>
      <div class="embat-app__tools">
        <button
          type="button"
          class="embat-app__icon"
          :aria-label="todoAbierto ? 'Plegar todo' : 'Desplegar todo'"
          @click="plegarTodo"
        >
          <ChevronsUpDown :size="16" aria-hidden="true" />
        </button>
      </div>
    </header>

    <section class="embat-app__sheet" :aria-busy="pending">
      <p v-if="pending" class="embat-app__state">Leyendo el equipo.</p>
      <p v-else-if="error" class="embat-app__state" role="alert">
        No se pudo leer el equipo.
        <button type="button" @click="refresh()">Reintentar</button>
      </p>
      <p v-else-if="!data?.employees.length" class="embat-app__state">
        No hay personas en el equipo.
      </p>

      <template v-else>
        <article v-for="team in TEAM" :key="team.id" class="embat-app__group">
          <header>
            <button type="button" :aria-expanded="abiertos.has(team.id)" @click="plegar(team.id)">
              <ChevronRight :size="16" aria-hidden="true" />
            </button>
            <b>{{ team.label }}</b>
            <span>{{ team.hint }}</span>
            <em>{{ nPersonas(grouped[team.id].length) }}</em>
          </header>
          <table v-if="abiertos.has(team.id) && grouped[team.id].length" :aria-label="team.label">
            <tbody>
              <tr v-for="person in grouped[team.id]" :key="person.id" class="is-static">
                <th scope="row">{{ person.name }}</th>
                <td class="embat-app__meta">{{ person.job_title }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else-if="abiertos.has(team.id)" class="embat-app__empty">Nadie en este equipo.</p>
        </article>
      </template>
    </section>
  </div>
</template>
