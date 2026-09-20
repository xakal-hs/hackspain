<script setup lang="ts">
import { ArrowDown, ArrowRight, ArrowUp, ChevronDown } from '@lucide/vue'
import type { CompanyDriver } from '../../shared/types/company'
import { groupScoreDrivers, formatContribution, type ScorePillarId } from '~/utils/scorePillars'

/* Misma piel que Flujo de caja y Crédito: el chrome claro de Embat, sin
 * tarjetas ni bloques teñidos. El color queda para el arco, las bandas de la
 * gráfica y el signo de las contribuciones. */

const { name: companyName, sector: companySector, detail: companyDetail, health: companyHealth, company: selectedCompany } = useSelectedCompany()

type Trend = 'up' | 'flat' | 'down'

/* Caso de demostración: solo se pinta cuando la empresa no tiene score publicado. */
const demo = {
  score: '68,0',
  band: 'vigilancia',
  tone: 'var(--warn)',
  direction: 'down' as Trend,
  delta3: '−14,0 pts',
  drivers: [
    { label: 'Meses de caja', contribution: -4.2, display_value: '3,1 vs. 4,2 meses' },
    { label: 'Facturación de clientes perdidos', contribution: -5.2, display_value: '22 % vs. 8 %' },
    { label: 'Pagos tardíos a proveedores', contribution: -1.9, display_value: '18 % vs. 5 %' },
  ] satisfies CompanyDriver[],
}

const num = (value: number) =>
  value.toLocaleString('es-ES', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const signed = (value: number) =>
  value.toLocaleString('es-ES', { minimumFractionDigits: 1, maximumFractionDigits: 1, signDisplay: 'exceptZero' })

const state = computed(() => {
  const health = companyHealth.value
  if (!health) return demo
  const delta = health.score_delta_3m
  return {
    score: num(health.health_score),
    band: health.health_band,
    tone: health.health_band === 'sano' ? 'var(--ok)' : health.health_band === 'riesgo' ? 'var(--bad)' : 'var(--warn)',
    direction: (health.health_trend === 'improving' ? 'up' : health.health_trend === 'deteriorating' ? 'down' : 'flat') as Trend,
    delta3: delta == null ? 'Sin dato' : `${signed(delta)} pts`,
  }
})

const arrow = computed(() => ({ up: ArrowUp, flat: ArrowRight, down: ArrowDown })[state.value.direction])

/* La previsión es la misma serie que prolonga la gráfica del sector: su último
 * mes, con la distancia al mes cerrado. No es un mes cerrado. */
const forecast = computed(() => {
  const health = companyHealth.value
  const ahead = (companyDetail.data.value?.projection.company ?? []).filter(point => point.month > (health?.month ?? ''))
  const end = ahead.at(-1)
  if (!health || !end) return null
  return { value: end.value, delta: end.value - health.health_score, month: end.month }
})

/* El arco del medidor es medio círculo de radio 126 en el viewBox del SVG: la
 * nota se dibuja tapando con el desfase el tramo que le sobra. El llenado es
 * una animación CSS que parte del arco vacío, y el `key` del trazo la vuelve a
 * lanzar cuando cambia la nota —al cambiar de empresa o de mes. */
const ARC_LENGTH = Number((Math.PI * 126).toFixed(1))
const arcOffset = computed(() => {
  const score = Math.min(100, Math.max(0, Number.parseFloat(state.value.score.replace(',', '.')) || 0))
  return Number((ARC_LENGTH * (1 - score / 100)).toFixed(1))
})

const drivers = computed<CompanyDriver[]>(() =>
  companyHealth.value ? companyDetail.data.value?.drivers ?? [] : demo.drivers)
const explanation = computed(() => groupScoreDrivers(drivers.value))
const activePillar = ref<ScorePillarId | null>(null)
const activeDetail = computed(() => explanation.value.pillars.find(p => p.id === activePillar.value))
const explanationId = useId()
watch(() => [selectedCompany.value?.company_id, companyHealth.value?.month], () => {
  activePillar.value = null
})
</script>

<template>
  <div v-if="!companyDetail.isPending.value" class="embat-app xs">
    <header class="embat-app__title">
      <h1>X-Ray Score</h1>
      <p class="xs-sector">{{ companyName }} · {{ companySector }}</p>
    </header>

    <!-- El arco y la banda conservan el verde/ámbar/rojo: es el único sitio de
         la pantalla, junto a las bandas de la gráfica, donde el semáforo dice
         algo. -->
    <section class="xs-top" aria-label="Lectura del score">
      <div class="xs-gauge" data-tour="xray-gauge">
        <svg viewBox="0 0 300 168" :aria-label="`Score ${state.score} sobre 100 · banda ${state.band}`" role="img">
          <path class="xs-gauge__track" d="M24 152 A126 126 0 0 1 276 152" />
          <path :key="arcOffset" class="xs-gauge__value" d="M24 152 A126 126 0 0 1 276 152"
            :stroke="state.tone" :stroke-dasharray="ARC_LENGTH" :stroke-dashoffset="arcOffset" />
        </svg>
        <p class="xs-gauge__figure" aria-hidden="true">
          <b>{{ state.score }}</b>
          <span :style="{ color: state.tone }">{{ state.band }}</span>
        </p>
        <p class="xs-gauge__scale" aria-hidden="true"><span>0</span><span>100</span></p>
      </div>
      <dl class="xs-reads">
        <div data-tour="xray-change">
          <dt>Cambio en 3 meses <component :is="arrow" :size="13" aria-hidden="true" /></dt>
          <dd>{{ state.delta3 }}</dd>
        </div>
        <div>
          <dt>Previsión a 3 meses</dt>
          <dd v-if="forecast">{{ num(forecast.value) }} <small>{{ signed(forecast.delta) }} · {{ forecast.month }}</small></dd>
          <dd v-else class="is-empty">Sin previsión</dd>
        </div>
        <div>
          <dt>Señales medidas</dt>
          <dd>{{ drivers.length }} <small>{{ companyHealth ? 'del score publicado' : 'de demostración' }}</small></dd>
        </div>
      </dl>
    </section>

    <div class="embat-app__sheet">
      <SectorHealthCompare />

      <section class="xs-explanation" aria-label="Qué explica el score">
        <header class="xs-explanation__bar">
          <b>Qué explica el score</b>
        </header>
        <p v-if="!drivers.length" class="xs-explanation__empty">Sin explicaciones disponibles para este mes. Puedes consultar qué mide cada pilar.</p>
        <ul class="xs-pillars" aria-label="Los cinco pilares del score" data-tour="xray-pillars">
          <li v-for="pillar in explanation.pillars" :key="pillar.id">
            <button type="button" :id="`${explanationId}-${pillar.id}`"
              :aria-expanded="activePillar === pillar.id" :aria-controls="`${explanationId}-detail`"
              @click="activePillar = activePillar === pillar.id ? null : pillar.id">
              <span class="xs-pillars__name">{{ pillar.name }} <ChevronDown :size="16" aria-hidden="true" /></span>
              <span class="xs-pillars__question">{{ pillar.question }}</span>
              <span class="xs-pillars__value" :class="{ 'xs-pillars__value--empty': pillar.contribution === null }">
                {{ formatContribution(pillar.contribution) }}<small v-if="pillar.contribution !== null"> pts</small>
              </span>
              <span class="xs-pillars__count">{{ pillar.drivers.length }} {{ pillar.drivers.length === 1 ? 'señal registrada' : 'señales registradas' }}</span>
              <span class="xs-pillars__action">{{ activePillar === pillar.id ? 'Ocultar detalle' : 'Ver detalle' }}</span>
            </button>
          </li>
        </ul>
        <div :id="`${explanationId}-detail`" :hidden="!activeDetail" class="xs-pillar-detail"
          data-tour="xray-pillar-detail" role="region" :aria-labelledby="activePillar ? `${explanationId}-${activePillar}` : undefined">
          <template v-if="activeDetail">
            <div class="xs-pillar-detail__heading">
              <h2>{{ activeDetail.name }}</h2>
              <span>{{ formatContribution(activeDetail.contribution) }}{{ activeDetail.contribution !== null ? ' pts en total' : '' }}</span>
            </div>
            <p class="xs-pillar-detail__description">{{ activeDetail.description }}</p>
            <p class="xs-pillar-detail__reading">{{ activeDetail.reading }}</p>
            <p v-if="!activeDetail.drivers.length" class="xs-explanation__empty">No hay contribuciones registradas para este pilar en este mes. No significa que valga cero.</p>
            <ul v-else class="xs-drivers" :aria-label="`Señales de ${activeDetail.name}`">
              <li v-for="d in activeDetail.drivers" :key="d.feature || d.label">
                <ScoreFieldHelp :label="d.label" :value="d.display_value">
                  <p><b>{{ formatContribution(d.contribution) }} pts</b><small>{{ d.display_value }}</small></p>
                  <i aria-hidden="true"><span :style="{ width: d.weight }"></span></i>
                </ScoreFieldHelp>
              </li>
            </ul>
            <p v-if="activeDetail.drivers.length" class="xs-pillar-detail__foot">Las barras comparan la magnitud de las contribuciones; el signo indica si suman o restan. «Sin dato» no es cero: el modelo puede aportar puntos usando un valor neutral.</p>
          </template>
        </div>
        <details v-if="explanation.additional.drivers.length" :key="selectedCompany?.company_id" class="xs-adjustments">
          <summary>Reglas y otras contribuciones <span>{{ formatContribution(explanation.additional.contribution) }} pts</span><ChevronDown :size="16" aria-hidden="true" /></summary>
          <p class="xs-pillar-detail__reading">Estos términos se conservan fuera de los cinco pilares: pueden ser ajustes del modelo o señales sin una asignación en el catálogo.</p>
          <ul class="xs-drivers">
            <li v-for="d in explanation.additional.drivers" :key="d.feature || d.label">
              <ScoreFieldHelp :label="d.label" :value="d.display_value">
                <p><b>{{ formatContribution(d.contribution) }} pts</b><small>{{ d.display_value }}</small></p>
                <i aria-hidden="true"><span :style="{ width: d.weight }"></span></i>
              </ScoreFieldHelp>
            </li>
          </ul>
        </details>
      </section>
    </div>
  </div>
</template>

<style scoped>
.xs {
  container-type: inline-size;
}

.xs-sector {
  margin: 0;
  color: var(--ea-muted);
}

/* Medidor y lecturas comparten una tira con filetes, como el pulso de las
   pantallas de Embat: ni tarjetas ni pozos de color. */
.xs-top {
  display: grid;
  grid-template-columns: 248px minmax(0, 1fr);
  align-items: center;
  gap: 8px 32px;
  padding: 14px 24px 18px;
  border-bottom: 1px solid var(--ea-line);
}

.xs-gauge {
  position: relative;
  width: 248px;
  max-width: 100%;
}

.xs-gauge svg {
  display: block;
  width: 100%;
}

.xs-gauge__track,
.xs-gauge__value {
  fill: none;
  stroke-width: 16;
  stroke-linecap: round;
}

.xs-gauge__track {
  stroke: var(--ea-soft);
}

/* El arco se llena al entrar. Va como animación y no como transición porque el
   valor final ya viene del servidor: el fotograma de partida es el vacío. */
.xs-gauge__value {
  animation: xs-gauge-fill 1.1s cubic-bezier(0.22, 0.61, 0.36, 1) both;
}

@keyframes xs-gauge-fill {
  from {
    stroke-dashoffset: 395.8px;
  }
}

.xs-gauge__figure {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  margin: 0;
  padding-bottom: 12px;
}

.xs-gauge__figure b {
  font-size: 44px;
  font-weight: 500;
  line-height: 1;
  letter-spacing: -0.03em;
}

.xs-gauge__figure span {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.xs-gauge__scale {
  display: flex;
  justify-content: space-between;
  margin: -6px 0 0;
  color: var(--ea-muted);
}

.xs-reads {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  margin: 0;
  min-width: 0;
}

.xs-reads > div {
  min-width: 0;
  padding: 0 18px;
  border-left: 1px solid var(--ea-line);
}

.xs-reads > div:first-child {
  padding-left: 0;
  border-left: 0;
}

.xs-reads dt {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--ea-muted);
}

.xs-reads dt svg {
  flex: none;
}

.xs-reads dd {
  margin: 4px 0 0;
  font-size: 22px;
  font-weight: 500;
  letter-spacing: -0.02em;
}

.xs-reads dd.is-empty {
  font-size: 13px;
  font-weight: 400;
  color: var(--ea-muted);
}

.xs-reads dd small {
  display: block;
  margin-top: 2px;
  font-size: 12px;
  font-weight: 400;
  letter-spacing: 0;
  color: var(--ea-muted);
}

/* «Qué explica el score» conserva su composición: cinco pilares en columnas
   separadas por filetes, con el detalle debajo. Solo cambia la piel. */
.xs-explanation__bar {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 10px;
  min-height: 52px;
  padding-block: 14px;
}

.xs-explanation__bar b {
  font-size: 14px;
  font-weight: 600;
}

.xs-explanation__bar span {
  color: var(--ea-muted);
}

.xs-explanation__note,
.xs-explanation__empty {
  margin: 0 0 18px;
  max-width: 88ch;
  line-height: 1.55;
  color: var(--ea-muted);
}

.xs-explanation__empty {
  padding: 12px 14px;
  border-radius: 6px;
  background: var(--ea-hover);
}

.xs-pillars {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  margin: 0;
  border-top: 1px solid var(--ea-line);
}

.xs-pillars li {
  min-width: 0;
}

.xs-pillars li + li {
  border-left: 1px solid var(--ea-line);
}

.xs-pillars button {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  padding: 16px 14px;
  border-bottom: 2px solid transparent;
  text-align: left;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.xs-pillars button:hover {
  background: var(--ea-hover);
}

.xs-pillars button[aria-expanded='true'] {
  background: var(--ea-hover);
  border-bottom-color: var(--ea-blue);
}

.xs-pillars__name {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
}

.xs-pillars__name svg {
  flex: none;
  color: var(--ea-muted);
  transition: transform 0.15s ease;
}

.xs-pillars button[aria-expanded='true'] svg {
  transform: rotate(180deg);
}

.xs-pillars__question {
  display: block;
  margin-top: 8px;
  margin-bottom: auto;
  color: var(--ea-muted);
  line-height: 1.5;
}

.xs-pillars__value {
  display: block;
  margin-top: 22px;
  font-size: 26px;
  font-weight: 500;
  line-height: 1.25;
  letter-spacing: -0.02em;
}

.xs-pillars__value small {
  font-size: 12px;
  font-weight: 400;
  letter-spacing: 0;
  color: var(--ea-muted);
}

.xs-pillars__value--empty {
  font-size: 13px;
  font-weight: 400;
  line-height: 2.5;
  letter-spacing: 0;
  color: var(--ea-muted);
}

.xs-pillars__count {
  display: block;
  margin-top: 4px;
  color: var(--ea-muted);
}

.xs-pillars__action {
  display: block;
  margin-top: 16px;
  color: var(--ea-blue);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.xs-pillar-detail {
  margin-top: 22px;
  padding-top: 22px;
  border-top: 1px solid var(--ea-line);
}

.xs-pillar-detail__heading {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 4px 12px;
}

.xs-pillar-detail__heading h2 {
  font-size: 15px;
  font-weight: 600;
}

.xs-pillar-detail__heading > span {
  color: var(--ea-muted);
}

.xs-pillar-detail__description {
  max-width: 88ch;
  margin-top: 12px;
  line-height: 1.6;
  color: var(--ea-body);
}

.xs-pillar-detail__reading {
  max-width: 92ch;
  margin: 8px 0 20px;
  line-height: 1.6;
  color: var(--ea-muted);
}

.xs-pillar-detail__foot {
  margin: 18px 0 0;
  line-height: 1.55;
  color: var(--ea-muted);
}

/* Tira con filetes: las señales del pilar, ordenadas por lo que pesan. */
.xs-drivers {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: 0;
}

.xs-drivers li {
  min-width: 0;
  padding: 0 18px;
}

.xs-drivers li:first-child {
  padding-left: 0;
}

.xs-drivers li + li {
  border-left: 1px solid var(--ea-line);
}

.xs-drivers p {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 2px 10px;
  margin: 4px 0 0;
}

.xs-drivers b {
  font-size: 18px;
  font-weight: 500;
  letter-spacing: -0.02em;
}

.xs-drivers small {
  font-size: 12px;
  color: var(--ea-muted);
}

.xs-drivers i {
  display: block;
  height: 3px;
  margin-top: 10px;
  border-radius: 2px;
  background: var(--ea-soft);
  overflow: hidden;
}

.xs-drivers i span {
  display: block;
  height: 100%;
  background: var(--ea-blue);
}

.xs-adjustments {
  margin-top: 22px;
  border-top: 1px solid var(--ea-line);
}

.xs-adjustments summary {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 52px;
  padding-block: 12px;
  list-style: none;
  cursor: pointer;
}

.xs-adjustments summary::-webkit-details-marker {
  display: none;
}

.xs-adjustments summary span {
  margin-left: auto;
  color: var(--ea-muted);
  white-space: nowrap;
}

.xs-adjustments summary svg {
  flex: none;
  color: var(--ea-muted);
  transition: transform 0.15s ease;
}

.xs-adjustments[open] summary svg {
  transform: rotate(180deg);
}

@container (max-width: 960px) {
  .xs-drivers {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    row-gap: 16px;
  }

  .xs-drivers li:nth-child(odd) {
    padding-left: 0;
    border-left: 0;
  }
}

@container (max-width: 860px) {
  .xs-pillars {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .xs-pillars li:nth-child(odd) {
    border-left: 0;
  }

  .xs-pillars li:nth-child(n + 3) {
    border-top: 1px solid var(--ea-line);
  }

  .xs-pillars li:last-child {
    grid-column: 1 / -1;
  }
}

@container (max-width: 700px) {
  .xs-top {
    grid-template-columns: minmax(0, 1fr);
    justify-items: center;
  }

  .xs-reads {
    width: 100%;
  }
}

@container (max-width: 480px) {
  .xs-pillars {
    grid-template-columns: minmax(0, 1fr);
  }

  .xs-pillars li + li {
    border-left: 0;
    border-top: 1px solid var(--ea-line);
  }

  .xs-drivers {
    grid-template-columns: minmax(0, 1fr);
  }

  .xs-drivers li {
    padding: 0;
    border-left: 0;
  }

  .xs-drivers li + li {
    padding-top: 12px;
    border-left: 0;
    border-top: 1px solid var(--ea-line);
  }
}

@media (prefers-reduced-motion: reduce) {
  .xs-pillars button,
  .xs-pillars svg,
  .xs-adjustments summary svg {
    transition: none;
  }

  .xs-gauge__value {
    animation: none;
  }
}
</style>
