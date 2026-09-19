<script setup lang="ts">
import { ArrowDown, ArrowRight, ArrowUp, TriangleAlert } from '@lucide/vue'

export type AlertDirection = 'up' | 'flat' | 'down' | 'alert'

defineProps<{
  direction: AlertDirection
  headline: string
  text: string
  cta: string
  ctaFilled?: boolean
}>()

const icons = { up: ArrowUp, flat: ArrowRight, down: ArrowDown, alert: TriangleAlert }
</script>

<template>
  <section class="tz-alert">
    <span class="tz-alert__icon" aria-hidden="true">
      <component :is="icons[direction]" :size="18" />
    </span>
    <div>
      <h2>{{ headline }}</h2>
      <p>{{ text }}</p>
    </div>
    <button type="button" class="tz-btn" :class="{ 'tz-btn--filled': ctaFilled }">
      {{ cta }}
    </button>
  </section>
</template>
