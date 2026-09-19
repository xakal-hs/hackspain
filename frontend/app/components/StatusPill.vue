<script setup lang="ts">
import type { HealthBand } from '~/types/portfolio'

defineProps<{
  band: HealthBand
}>()

const labels: Record<HealthBand, string> = {
  sano: 'Prestar',
  vigilar: 'Vigilar',
  riesgo: 'No prestar',
}
</script>

<template>
  <span class="status-pill" :class="`status-pill--${band}`">
    <span class="status-pill__dot" />
    {{ labels[band] }}
  </span>
</template>
