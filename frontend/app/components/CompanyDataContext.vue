<script setup lang="ts">
const props = defineProps<{ section: string }>()
const { company, name, sector, detail, latest } = useSelectedCompany()
const simulated = computed(() => props.section === 'score'
  ? 'Comparativa del sector, previsión y recomendaciones del agente: simuladas. El score y su historia usan Supabase cuando están disponibles.'
  : props.section === 'colchon'
    ? 'Excedente colocable, previsión, depósitos, rentabilidad y operaciones: simulados. La caja disponible se lee del panel mensual.'
    : props.section === 'divisa'
      ? 'Exposición, tipos de cambio, pagos previstos, coberturas y ahorro: simulados. Las monedas de las cuentas sí proceden de Supabase.'
      : 'Este resumen, sus señales y ofertas siguen siendo una demo. Los datos conectados están en X-Ray Score, Colchón Dinámico y Divisa Inteligente.')
</script>
<template>
  <section class="company-context" aria-label="Datos de la empresa seleccionada" aria-live="polite">
    <b>{{ name }} · {{ sector }}</b>
    <span>Moneda: {{ company?.currency || 'Sin dato' }} · País: {{ company?.country || 'Sin dato' }} · Grupo: {{ company?.group_id || 'Sin dato' }}</span>
    <span v-if="detail.isPending.value">Cargando información de la empresa…</span>
    <template v-else>
      <span v-if="section === 'divisa'">Monedas en cuentas: {{ detail.data.value?.currencies.join(', ') || 'Sin datos' }}</span>
      <span v-else>Último mes de tesorería: {{ latest?.month || 'Sin datos' }}</span>
      <span v-if="latest?.saldo_inconsistente">La caja reconstruida presenta inconsistencias; revisar antes de usarla.</span>
    </template>
    <span v-if="detail.isError.value" role="alert">No se pudieron cargar los datos. <button @click="detail.refetch()">Reintentar</button></span>
    <span v-for="warning in detail.data.value?.warnings" :key="warning" role="alert">{{ warning }}</span>
    <small><strong>Datos de demostración:</strong> {{ simulated }}</small>
  </section>
</template>
<style scoped>
.company-context { display: grid; gap: 6px; padding: 16px 20px; margin-bottom: 18px; border: 1px solid var(--line); border-radius: 12px; background: var(--panel); font-size: 13px; overflow-wrap: anywhere; }
.company-context span, .company-context small { color: var(--text-muted); }
.company-context small { font-size: 12px; line-height: 1.6; }
</style>
