<script setup lang="ts">
const { selectedId, directory, companies } = useSelectedCompany()
const id = useId()
</script>
<template>
  <label class="company-selector" :for="id">
    <span>Empresa</span>
    <select :id="id" v-model="selectedId" :disabled="!companies.length" aria-label="Seleccionar empresa">
      <option v-if="!companies.length" :value="selectedId">{{ directory.isPending.value ? 'Cargando empresas…' : 'Empresas no disponibles' }}</option>
      <option v-for="company in companies" :key="company.company_id" :value="company.company_id">
        {{ company.company_id }} · {{ company.top_sector || 'Sin sector' }}
      </option>
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
