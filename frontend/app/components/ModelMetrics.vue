<script setup lang="ts">
import type { ModelMetric } from '~/data/internal'

defineProps<{
  metrics: ModelMetric[]
  /** En el monitor va solo la cifra contra su objetivo; el qué significa cada
   *  una se lee en la vista del modelo. */
  compact?: boolean
}>()
</script>

<template>
  <dl class="mmetrics" :class="{ 'mmetrics--compact': compact }">
    <div v-for="metric in metrics" :key="metric.id">
      <dt>{{ metric.label }}</dt>
      <dd class="mmetrics__value">
        {{ metric.value }}<small v-if="metric.unit">{{ metric.unit }}</small>
      </dd>
      <dd class="mmetrics__target" :data-ok="metric.beatsTarget">
        {{ metric.target }}<span v-if="metric.beatsTarget"> · superado</span>
      </dd>
      <dd v-if="!compact" class="mmetrics__meaning">{{ metric.meaning }}</dd>
    </div>
  </dl>
</template>
