<script setup lang="ts">
import type { Signal } from '~/data/demo'

const props = defineProps<{ signals: Signal[] }>()

/* Bar length is the signal's share of the move. A collapsing cash runway draws
 * five times the bar of a one-day wobble in collection days, because it is
 * worth five times as much to whoever lends the money. */
const ranked = computed(() =>
  [...props.signals].sort((a, b) => b.weight - a.weight),
)
const max = computed(() => Math.max(...props.signals.map((s) => s.weight)))
</script>

<template>
  <ol class="sigbars">
    <li v-for="signal in ranked" :key="signal.label" :data-dir="signal.direction">
      <p class="sigbars__label">{{ signal.label }}</p>
      <p class="sigbars__detail">{{ signal.detail }}</p>
      <span class="sigbars__track">
        <span
          class="sigbars__fill"
          :style="{ width: `${(signal.weight / max) * 100}%` }"
        />
      </span>
      <span class="sigbars__weight"
        >{{ Math.round(signal.weight * 100) }}<small>%</small></span
      >
    </li>
  </ol>
</template>
