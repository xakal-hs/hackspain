<script setup lang="ts">
const route = useRoute()
const companyId = computed(() => String(route.params.id))

useHead({ title: () => `${companyId.value} · X-Ray` })
</script>

<template>
  <div class="app-shell">
    <AppHeader />
    <main id="main-content" class="placeholder-page" tabindex="-1">
      <span class="code-label">&lt;CompanyView /&gt;</span>
      <h1>{{ companyId }}</h1>
      <p>Ruta preparada para el nivel, la trayectoria, las causas y la decisión de esta empresa.</p>
      <NuxtLink to="/cartera" class="button button--secondary">Volver a cartera</NuxtLink>
    </main>
  </div>
</template>
