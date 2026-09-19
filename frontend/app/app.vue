<script setup lang="ts">
const { theme } = useTheme()

useHead({
  htmlAttrs: { 'data-theme': () => theme.value },
  meta: [
    {
      name: 'theme-color',
      content: () => (theme.value === 'light' ? '#f4f5fb' : '#090c22'),
    },
  ],
})
</script>

<template>
  <NuxtRouteAnnouncer />
  <NuxtPage />
</template>
