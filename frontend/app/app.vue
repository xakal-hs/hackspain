<script setup lang="ts">
const { theme } = useTheme()

useHead({
  htmlAttrs: { 'data-theme': () => theme.value },
  meta: [
    {
      name: 'theme-color',
      content: () => (theme.value === 'light' ? '#ffffff' : '#050b2c'),
    },
  ],
})
</script>

<template>
  <NuxtRouteAnnouncer />
  <NuxtPage />
</template>
