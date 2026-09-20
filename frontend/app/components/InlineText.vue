<script setup lang="ts">
import type { Inline } from '~/utils/chatText'

defineProps<{ parts: Inline[] }>()
</script>

<template>
  <!-- Cada trozo se pinta como texto: nunca se interpreta como HTML. -->
  <template v-for="(s, i) in parts" :key="i">
    <code v-if="s.code">{{ s.text }}</code>
    <s v-else-if="s.strike"><strong v-if="s.bold"><em v-if="s.italic">{{ s.text }}</em><template v-else>{{ s.text }}</template></strong><em v-else-if="s.italic">{{ s.text }}</em><template v-else>{{ s.text }}</template></s>
    <strong v-else-if="s.bold"><em v-if="s.italic">{{ s.text }}</em><template v-else>{{ s.text }}</template></strong>
    <em v-else-if="s.italic">{{ s.text }}</em>
    <template v-else>{{ s.text }}</template>
  </template>
</template>

<style scoped>
code {
  padding: 1px 5px; border-radius: 5px; background: var(--neutral-wash);
  font: 0.92em var(--font-num); color: var(--live-ink);
}
s { color: var(--text-muted); }
em { font-style: italic; }
</style>
