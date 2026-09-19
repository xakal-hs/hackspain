<script setup lang="ts">
useHead({ title: 'Escenarios · X-Ray' })
</script>

<template>
  <div class="app-shell">
    <AppHeader />
    <main id="main-content" class="placeholder-page" tabindex="-1">
      <span class="code-label">&lt;ScenarioLab /&gt;</span>
      <h1>Laboratorio de escenarios</h1>
      <p>Esta ruta alojará el simulador de cobros, pagos, deuda y caja contra el score actual.</p>
      <NuxtLink to="/cartera" class="button button--secondary">Volver a cartera</NuxtLink>
    </main>
  </div>
</template>
