<script setup lang="ts">
import type { OpsAlert } from '~/data/internal'

defineProps<{ alerts: OpsAlert[] }>()

/* El tono ya va como color en el filo de la tarjeta; la palabra lo repite para
 * quien no distinga el verde del rojo. */
const word: Record<OpsAlert['tone'], string> = {
  mint: 'Oportunidad',
  coral: 'Seguimiento',
  amber: 'Vigilar',
  crimson: 'Deterioro',
  live: 'Aviso',
}
</script>

<template>
  <ol class="afeed">
    <li v-for="alert in alerts" :key="alert.id" :data-tone="alert.tone">
      <div class="afeed__head">
        <b>{{ alert.company }}</b>
        <time>{{ alert.when }}</time>
      </div>
      <p>{{ alert.text }}</p>
      <span class="afeed__tag">{{ word[alert.tone] }}</span>
    </li>
  </ol>
</template>
