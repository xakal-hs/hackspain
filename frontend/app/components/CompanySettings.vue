<script setup lang="ts">
import { Building2, Check, Sparkles } from '@lucide/vue'
import type { CompanyDirectorySource } from '../../shared/types/company'

const { source, companies, directory, name } = useSelectedCompany()

const options: Array<{
  id: CompanyDirectorySource
  label: string
  table: string
  description: string
  icon: typeof Building2
}> = [
  {
    id: 'featured_companies',
    label: 'Empresas destacadas',
    table: 'featured_companies',
    description: 'Una selección corta, ordenada y con alias preparada para recorrer los casos más representativos.',
    icon: Sparkles,
  },
  {
    id: 'companies',
    label: 'Todas las empresas',
    table: 'companies',
    description: 'El directorio completo de compañías conectadas, ordenado por su identificador.',
    icon: Building2,
  },
]
</script>

<template>
  <section class="panel settings-panel" aria-labelledby="company-source-title">
    <header class="settings-panel__head">
      <div>
        <h2 id="company-source-title" class="panel__title">Empresas disponibles</h2>
        <p>Elige qué conjunto aparece en el selector de empresa del panel.</p>
      </div>
      <span class="chip chip--neutral">
        {{ directory.isPending.value ? 'Actualizando' : `${companies.length} empresas` }}
      </span>
    </header>

    <fieldset class="settings-panel__choices" :disabled="directory.isFetching.value">
      <legend class="sr-only">Origen del selector de empresa</legend>
      <label v-for="option in options" :key="option.id" :class="{ 'is-selected': source === option.id }">
        <input v-model="source" type="radio" name="company-source" :value="option.id">
        <span class="settings-panel__icon"><component :is="option.icon" :size="20" aria-hidden="true" /></span>
        <span class="settings-panel__copy">
          <b>{{ option.label }}</b>
          <small><code>{{ option.table }}</code></small>
          <span>{{ option.description }}</span>
        </span>
        <span class="settings-panel__check" aria-hidden="true"><Check :size="16" /></span>
      </label>
    </fieldset>

    <p class="settings-panel__status" aria-live="polite">
      <template v-if="directory.isError.value">
        No se pudo cargar el directorio.
        <button type="button" @click="directory.refetch()">Reintentar</button>
      </template>
      <template v-else-if="directory.isFetching.value">Cambiando el selector…</template>
      <template v-else>El selector muestra {{ companies.length }} empresas. Empresa activa: {{ name }}.</template>
    </p>
  </section>
</template>

<style scoped>
.settings-panel { display: grid; gap: 24px; max-width: 860px; padding: clamp(20px, 3vw, 30px); }
.settings-panel__head { display: flex; align-items: start; justify-content: space-between; gap: 20px; }
.settings-panel__head > div { display: grid; gap: 7px; }
.settings-panel__head p, .settings-panel__status { color: var(--text-muted); font-size: var(--t-small); }
.settings-panel__choices { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; border: 0; padding: 0; }
.settings-panel__choices label { position: relative; display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: start; gap: 14px; min-height: 168px; padding: 20px; border: 1px solid var(--line); border-radius: var(--r-inner); background: var(--panel-sunken); cursor: pointer; transition: border-color .12s var(--ease), background-color .12s var(--ease); }
.settings-panel__choices label:hover { border-color: var(--line-strong); background: var(--neutral-wash); }
.settings-panel__choices label.is-selected { border-color: var(--live); background: var(--live-wash); }
.settings-panel__choices input { position: absolute; opacity: 0; pointer-events: none; }
.settings-panel__choices label:has(input:focus-visible) { outline: 2px solid var(--focus-ring); outline-offset: 3px; }
.settings-panel__icon, .settings-panel__check { display: grid; place-items: center; flex: none; }
.settings-panel__icon { width: 38px; height: 38px; border-radius: 9px; background: var(--neutral-wash); color: var(--text-muted); }
.is-selected .settings-panel__icon { background: var(--live-wash); color: var(--live-ink); }
.settings-panel__check { width: 24px; height: 24px; border: 1px solid var(--line-strong); border-radius: 50%; color: transparent; }
.is-selected .settings-panel__check { border-color: var(--live); background: var(--live-solid); color: var(--on-live); }
.settings-panel__copy { display: grid; gap: 7px; }
.settings-panel__copy b { font-size: var(--t-body); font-weight: 600; }
.settings-panel__copy small { color: var(--text-dim); font-size: var(--t-micro); }
.settings-panel__copy code { font-family: inherit; }
.settings-panel__copy > span { color: var(--text-muted); font-size: var(--t-small); line-height: 1.5; }
.settings-panel__status { min-height: 22px; padding-top: 16px; border-top: 1px solid var(--line); }
.settings-panel__status button { color: var(--live-ink); text-decoration: underline; text-underline-offset: 3px; }
@media (max-width: 700px) {
  .settings-panel__head { display: grid; }
  .settings-panel__head .chip { justify-self: start; }
  .settings-panel__choices { grid-template-columns: 1fr; }
  .settings-panel__choices label { min-height: auto; }
}
</style>
