<script setup lang="ts">
import { demoCases } from '../../shared/demoCases'
const { selectedId, directory, companies } = useSelectedCompany()
const id = useId()
/* Los casos reales de la demo van arriba: se cambia de uno a otro sin buscar entre 1.286. */
const demo = computed(() => companies.value.filter(company => company.company_id in demoCases))
</script>
<template>
  <label class="company-selector" :for="id">
    <span>Empresa</span>
    <select :id="id" v-model="selectedId" :disabled="!companies.length" aria-label="Seleccionar empresa">
      <option v-if="!companies.length" :value="selectedId">{{ directory.isPending.value ? 'Cargando empresas…' : 'Empresas no disponibles' }}</option>
      <optgroup v-if="demo.length" label="Casos de la demo">
        <option v-for="company in demo" :key="`demo-${company.company_id}`" :value="company.company_id">
          {{ company.company_id }} · {{ demoCases[company.company_id]!.label }}
        </option>
      </optgroup>
      <optgroup :label="demo.length ? 'Todas las empresas' : undefined">
        <option v-for="company in companies" :key="company.company_id" :value="company.company_id">
          {{ company.company_id }} · {{ company.top_sector || 'Sin sector' }}
        </option>
      </optgroup>
    </select>
  </label>
  <p v-if="directory.isError.value" role="alert" class="company-selector-error">
    No se pudieron cargar las empresas. <button type="button" @click="directory.refetch()">Reintentar</button>
  </p>
</template>
<style scoped>
.company-selector { display: grid; gap: 8px; min-width: 0; }
.company-selector > span { font-weight: 600; }
select { width: 100%; min-height: 44px; padding: 8px; color: var(--text); background: var(--panel-raised); border: 1px solid var(--line); border-radius: 8px; font: inherit; font-size: 13px; text-overflow: ellipsis; }
select:focus-visible { outline: 2px solid var(--live); outline-offset: 3px; }
.company-selector-error { font-size: 12px; }
</style>
