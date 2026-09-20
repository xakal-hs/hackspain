<script setup lang="ts">
import { alignSectorHealth, type SectorStatistic } from '~/utils/sectorHealth'

const { name, sector, company, detail } = useSelectedCompany()
/* La referencia del sector es siempre la media: una sola cifra que comparar
 * evita que el lector tenga que decidir qué estadístico mira. */
const statistic: SectorStatistic = 'score_mean'
const label = 'Media'
const rows = computed(() => alignSectorHealth(detail.data.value?.health ?? [], detail.data.value?.sectorHealth ?? [], statistic))
const latest = computed(() => rows.value.at(-1))
const omitted = computed(() => (detail.data.value?.health.length ?? 0) - rows.value.length)

/* Los dos trazos previstos comparten eje: el del sector sólo se dibuja en los meses en que
 * coincide con los de la empresa —y se corta en el primero que falte— para que la distancia
 * entre líneas siga leyéndose en el mes que dice la etiqueta. */
const ahead = computed(() => {
  const projection = detail.data.value?.projection
  const last = latest.value?.month
  const empty = { months: [] as string[], company: [] as number[], sector: [] as number[] }
  if (!projection || !last) return empty
  const mine = projection.company.filter(point => point.month > last)
  if (!mine.length) return empty
  const peer = new Map(projection.sector[statistic].map(point => [point.month, point.value]))
  const sectorAhead: number[] = []
  for (const point of mine) {
    const value = peer.get(point.month)
    if (value == null) break
    sectorAhead.push(value)
  }
  return { months: mine.map(point => point.month), company: mine.map(point => point.value), sector: sectorAhead }
})
const aheadNote = computed(() => ahead.value.months.length ? `previsión ${ahead.value.months.length} m` : undefined)
const traces = computed(() => [
  { key: 'company', label: name.value, note: aheadNote.value, history: rows.value.map(row => row.company), forecast: ahead.value.company },
  { key: 'sector', label: `${label} · ${sector.value}`, tone: 'muted' as const, history: rows.value.map(row => row.sector), forecast: ahead.value.sector },
])
const emptyMessage = computed(() => !company.value?.top_sector
  ? 'Esta empresa aún no tiene un sector asignado.'
  : !detail.data.value?.health.length
    ? 'La empresa aún no tiene un score real para comparar.'
    : `No hay datos de ${label.toLowerCase()} del sector para los meses de esta empresa.`)
const format = (value: number) => value.toLocaleString('es-ES', { maximumFractionDigits: 1 })
const difference = computed(() => latest.value ? latest.value.company - latest.value.sector : 0)
const signed = (value: number) => `${value > 0 ? '+' : value < 0 ? '−' : ''}${format(Math.abs(value))}`
</script>

<template>
  <section class="sector" aria-label="Frente al sector" data-tour="xray-sector">
    <header class="sector__bar">
      <b>Frente al sector</b>
      <span>{{ sector }}</span>
    </header>
    <div aria-live="polite">
      <p v-if="!latest" class="sector__note">{{ emptyMessage }}</p>
      <p v-else class="sector__note">
        {{ latest.month }} · Tu score <b>{{ format(latest.company) }}</b> · {{ label }} del sector
        <b>{{ format(latest.sector) }}</b> en {{ latest.n }} empresas · Diferencia <b>{{ signed(difference) }}</b>.
      </p>
    </div>
    <ScoreBandChart v-if="latest" :traces="traces" :month-labels="[...rows.map(row => row.month), ...ahead.months]"
      :note="ahead.months.length ? 'Datos reales hasta la línea · previsión en discontinuo' : 'Datos reales · meses coincidentes'"
      :caption="`Score de ${name} frente a la media de ${sector}, comparado mes a mes. Último mes común: ${latest.month}.`" />
    <p v-if="omitted && latest" class="sector__note sector__note--foot">{{ omitted }} meses sin comparación: solo se dibujan los que tienen ambos datos.</p>
  </section>
</template>

<style scoped>
.sector { padding-bottom: 20px; border-bottom: 1px solid var(--ea-line); }
.sector__bar { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 12px; min-height: 52px; padding-block: 14px; }
.sector__bar b { font-size: 14px; font-weight: 600; }
.sector__bar span { color: var(--ea-muted); }
.sector__bar .embat-app__seg { margin-left: auto; }
.sector__note { margin: 0 0 14px; color: var(--ea-muted); }
.sector__note b { font-weight: 600; color: var(--ea-text); }
.sector__note--foot { margin: 12px 0 0; }
</style>
