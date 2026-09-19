<script setup lang="ts">
const { theme, setTheme } = useTheme()
</script>

<template>
  <div class="theme-switch" role="group" aria-label="Tema de la interfaz">
    <button
      type="button"
      class="theme-switch__opt"
      data-value="light"
      :aria-pressed="theme === 'light'"
      @click="setTheme('light')"
    >
      Claro
    </button>
    <button
      type="button"
      class="theme-switch__opt"
      data-value="dark"
      :aria-pressed="theme === 'dark'"
      @click="setTheme('dark')"
    >
      Oscuro
    </button>
  </div>
</template>
