<script setup lang="ts">
useHead({ title: 'Monitor · X-Ray' })
</script>

<template>
  <div class="app-shell">
    <AppHeader />
    <main id="main-content" class="placeholder-page" tabindex="-1">
      <span class="code-label">&lt;Monitor /&gt;</span>
      <h1>Monitor de cambios</h1>
      <p>Esta ruta está preparada para las alertas de mejora, deterioro, bache y caída estructural.</p>
      <NuxtLink to="/" class="button button--secondary">Volver a cartera</NuxtLink>
    </main>
  </div>
</template>
