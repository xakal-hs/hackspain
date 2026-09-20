<script setup lang="ts">
import { alignSectorHealth, type SectorStatistic } from '~/utils/sectorHealth'

const { name, sector, company, detail } = useSelectedCompany()
const statistic = useState<SectorStatistic>('sector-health-statistic', () => 'score_mean')
const options = [
  { value: 'score_mean' as const, label: 'Media' },
  { value: 'score_median' as const, label: 'Mediana' },
]
const label = computed(() => statistic.value === 'score_mean' ? 'Media' : 'Mediana')
const rows = computed(() => alignSectorHealth(detail.data.value?.health ?? [], detail.data.value?.sectorHealth ?? [], statistic.value))
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
  const peer = new Map(projection.sector[statistic.value].map(point => [point.month, point.value]))
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
  { key: 'sector', label: `${label.value} · ${sector.value}`, tone: 'muted' as const, history: rows.value.map(row => row.sector), forecast: ahead.value.sector },
])
const emptyMessage = computed(() => !company.value?.top_sector
  ? 'Esta empresa aún no tiene un sector asignado.'
  : !detail.data.value?.health.length
    ? 'La empresa aún no tiene un score real para comparar.'
    : `No hay datos de ${label.value.toLowerCase()} del sector para los meses de esta empresa.`)
const format = (value: number) => value.toLocaleString('es-ES', { maximumFractionDigits: 1 })
const difference = computed(() => latest.value ? latest.value.company - latest.value.sector : 0)
const drift = computed(() => {
  const end = ahead.value.company.at(-1)
  return end != null && latest.value ? end - latest.value.company : null
})
const signed = (value: number) => `${value > 0 ? '+' : value < 0 ? '−' : ''}${format(Math.abs(value))}`
</script>

<template>
  <section class="tz-card" aria-label="Frente al sector" data-tour="xray-sector">
    <header class="tz-card__bar sector-head">
      <div>
        <h2>Frente al sector</h2>
        <p>{{ sector }} · score de salud mensual</p>
      </div>
      <div class="sector-toggle" role="group" aria-label="Referencia del sector">
        <button v-for="option in options" :key="option.value" type="button"
          :aria-pressed="statistic === option.value" @click="statistic = option.value">
          {{ option.label }}
        </button>
      </div>
    </header>
    <p class="sector-note">{{ statistic === 'score_mean' ? 'Media: promedio de los scores del sector.' : 'Mediana: valor central de los scores del sector.' }}</p>
    <div aria-live="polite">
      <p v-if="!latest" class="sector-note">{{ emptyMessage }}</p>
      <p v-else class="sector-summary">
        {{ latest.month }} · Tu score: <b>{{ format(latest.company) }}</b> · {{ label }}: <b>{{ format(latest.sector) }}</b>
        · Diferencia: <b>{{ difference > 0 ? '+' : '' }}{{ format(difference) }} puntos</b>
        · {{ latest.n }} empresas en el sector.
      </p>
    </div>
    <ScoreBandChart v-if="latest" :traces="traces" :month-labels="[...rows.map(row => row.month), ...ahead.months]"
      :note="ahead.months.length ? 'Datos reales hasta la línea · previsión en discontinuo' : 'Datos reales · meses coincidentes'"
      :caption="`Score de ${name} frente a la ${label.toLowerCase()} de ${sector}, comparado mes a mes. Último mes común: ${latest.month}.`" />
    <p v-if="drift != null && latest" class="sector-note">
      Previsión a {{ ahead.months.length }} meses ({{ ahead.months.at(-1) }}):
      <b>{{ format(ahead.company.at(-1)!) }}</b> · <b>{{ signed(drift) }} puntos</b> sobre {{ latest.month }}.
      Prolonga la misma media que suaviza el score, con su pendiente amortiguada: no es un mes cerrado.
    </p>
    <p v-if="omitted && latest" class="sector-note">{{ omitted }} meses sin comparación disponible. Solo se muestran los meses con ambos datos.</p>
  </section>
</template>

<style scoped>
.sector-head { flex-wrap: wrap; gap: 16px; }
.sector-toggle { display: inline-flex; flex-shrink: 0; padding: 3px; border: 1px solid var(--line); border-radius: 999px; background: var(--panel-raised); }
.sector-toggle button { min-height: 44px; padding: 8px 18px; border: 0; border-radius: 999px; color: var(--text-muted); background: transparent; font: inherit; font-size: 13px; cursor: pointer; }
.sector-toggle button[aria-pressed='true'] { color: var(--text); background: var(--panel); }
.sector-toggle button:focus-visible { outline: 2px solid var(--live); outline-offset: 2px; }
.sector-note, .sector-summary { font-size: 12px; color: var(--text-muted); line-height: 1.6; margin: 0 0 16px; }
.sector-summary b { color: var(--text); }
</style>
