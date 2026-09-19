<script setup lang="ts">
import { Moon, Sun } from '@lucide/vue'

const { theme, toggle } = useTheme()

const nextLabel = computed(() =>
  theme.value === 'dark' ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro',
)
</script>

<template>
  <!-- Un solo botón: cualquier punto de la pastilla alterna. Los glifos no son
       destinos, solo marcan de qué lado está el pulgar. -->
  <button
    type="button"
    class="theme-switch"
    role="switch"
    :aria-checked="theme === 'dark'"
    :aria-label="nextLabel"
    :title="nextLabel"
    @click="toggle"
  >
    <span class="theme-switch__thumb" aria-hidden="true"></span>
    <span class="theme-switch__opt" data-value="light">
      <Sun :size="15" />
    </span>
    <span class="theme-switch__opt" data-value="dark">
      <Moon :size="15" />
    </span>
  </button>
</template>
