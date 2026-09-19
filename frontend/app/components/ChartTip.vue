<script setup lang="ts">
export interface TipRow {
  key: string
  label: string
  value: string
  /** Colorea el trazo de la fila igual que su línea en el gráfico. */
  tone?: 'live' | 'muted' | 'ahead'
  dir?: 'up' | 'down' | 'flat'
}

const props = defineProps<{
  /** Posición horizontal dentro del plot, en porcentaje. */
  x: number
  /** Mitad del plot donde se apoya. Quien dibuja sabe dónde le queda sitio. */
  place?: 'top' | 'bottom'
  title: string
  rows: TipRow[]
  foot?: string
}>()

/* Cerca de un borde el globo se apoya en el lado contrario: centrado se
 * saldría del panel justo en los meses que más se miran, el último y el
 * primero. */
const align = computed(() =>
  props.x > 68 ? 'end' : props.x < 32 ? 'start' : 'center',
)

</script>

<template>
  <div
    class="ctip"
    :data-align="align"
    :data-vertical="place ?? 'top'"
    :style="{ left: `${x}%` }"
    aria-hidden="true"
  >
    <p class="ctip__title">{{ title }}</p>
    <p v-for="row in rows" :key="row.key" class="ctip__row" :data-tone="row.tone">
      <i v-if="row.tone" class="ctip__mark" />
      <span>{{ row.label }}</span>
      <b :data-dir="row.dir">{{ row.value }}</b>
    </p>
    <p v-if="foot" class="ctip__foot">{{ foot }}</p>
  </div>
</template>
