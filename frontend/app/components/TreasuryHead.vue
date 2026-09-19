<script setup lang="ts">
export type TreasuryState = 'bien' | 'normal' | 'mal'

defineProps<{ title: string; lead?: string; sync: string }>()
const state = defineModel<TreasuryState>({ required: true })

const options: { id: TreasuryState; label: string }[] = [
  { id: 'bien', label: 'Bien' },
  { id: 'normal', label: 'Normal' },
  { id: 'mal', label: 'Mal' },
]
</script>

<template>
  <header class="tz__head">
    <div>
      <h1>{{ title }}</h1>
      <p v-if="lead">{{ lead }}</p>
    </div>
    <div class="tz__meta">
      <!-- El simulador es una herramienta de demo, no parte del producto. -->
      <div class="tz-sim" role="group" aria-label="Simular estado">
        <button
          v-for="option in options"
          :key="option.id"
          type="button"
          :aria-pressed="state === option.id"
          @click="state = option.id"
        >
          {{ option.label }}
        </button>
      </div>
      <p class="tz__sync">{{ sync }}</p>
    </div>
  </header>
</template>
