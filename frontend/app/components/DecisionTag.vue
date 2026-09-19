<script setup lang="ts">
import { decisionLabel, type Decision } from '~/data/demo'

/* Status always carries a word as well as a colour. */
defineProps<{ decision: Decision; size?: 'sm' | 'md' }>()
</script>

<template>
  <span class="dtag" :class="[`dtag--${decision}`, size === 'sm' && 'dtag--sm']">
    <i aria-hidden="true" />{{ decisionLabel[decision] }}
  </span>
</template>
