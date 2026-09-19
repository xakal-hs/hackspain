<script setup lang="ts">
import { ArrowDown, ArrowRight, ArrowUp, ChevronDown } from '@lucide/vue'
import type { AlertDirection } from './TreasuryAlert.vue'
import type { TreasuryState } from './TreasuryHead.vue'
import type { CompanyDriver } from '../../shared/types/company'
import { groupScoreDrivers, formatContribution, type ScorePillarId } from '~/utils/scorePillars'

const selected = ref<TreasuryState>('mal')

const { name: companyName, sector: companySector, detail: companyDetail, latest: companyLatest, health: companyHealth, company: selectedCompany } = useSelectedCompany()

// TODO: sustituir por fetch a /api/... cuando el endpoint esté listo
const states = {
  bien: {
    scoreColor: 'var(--ok)',
    direction: 'up' as AlertDirection,
    headline: 'Tu score subió 20 puntos en 4 meses',
    subhead:
      'La mejora es sostenible: viene de mejor gestión de cobro con facturación estable. Hay una ventana para pedir mejores condiciones.',
    ctaLabel: 'Ver 3 oportunidades',
    ctaFilled: true,
    score: '65',
    band: 'Sano',
    bandTitle: 'Trayectoria ascendente confirmada',
    bandDesc:
      'Salta al tramo preferente del marketplace. Score consolidado por 3 meses seguidos.',
    delta3: '+20 pts',
    deltaHint: 'Mejora sostenida en 4 meses. Sin señales de reversión.',
    forecast: '68 · +3',
    forecastHint: 'sigue mejorando',
    drivers: [
      { label: 'Cobros tardíos de clientes', contribution: '+4,8', value: '38 días vs. 60' },
      { label: 'Tendencia de cobros', contribution: '+3,2', value: '+18 % en 12 meses' },
      { label: 'Amplitud de clientes', contribution: '+2,4', value: '+0,3 clientes/mes' },
      { label: 'Meses de caja', contribution: '+2,0', value: '4,2 meses' },
    ],
  },
  normal: {
    scoreColor: 'var(--warn)',
    direction: 'flat' as AlertDirection,
    headline: 'Sin novedades desde tu última revisión',
    subhead:
      'El score se mantiene en su banda. Sin cambios significativos en las señales que lo componen. No pasa nada, y eso también es una señal.',
    ctaLabel: 'Explorar detalle',
    ctaFilled: false,
    score: '62',
    band: 'Vigilancia',
    bandTitle: 'Estable en zona intermedia',
    bandDesc:
      'El cambio a tres meses está dentro de ±5 puntos. Ni oportunidad clara, ni riesgo activo. Seguimos observando.',
    delta3: '±2 pts',
    deltaHint: 'Dentro del margen de ruido esperado.',
    forecast: '62 · 0',
    forecastHint: 'trayectoria plana',
    drivers: [
      { label: 'Meses de caja', contribution: '±0', value: '3,4 meses · estable' },
      { label: 'Pagos tardíos a proveedores', contribution: '+0,2', value: 'sin cambio' },
      { label: 'Tendencia de actividad', contribution: '−0,1', value: 'ruido de mes' },
      { label: 'Facturación de clientes perdidos', contribution: '±0', value: '4 % base' },
    ],
  },
  mal: {
    scoreColor: 'var(--bad)',
    direction: 'down' as AlertDirection,
    headline: 'Tu score bajó 14 puntos en 3 meses',
    subhead:
      'Detectado 3 meses antes de que se note en caja. Coste de circulante +15 % y 3 proveedores concentran el 60 % del retraso en los pagos.',
    ctaLabel: 'Abrir chat del agente',
    ctaFilled: true,
    score: '68',
    band: 'Vigilancia',
    bandTitle: 'Trayectoria descendente detectada',
    bandDesc:
      'Bajaste desde la banda sana (≥ 65) en 3 meses. La previsión a tres meses apunta a más caída si no actúas.',
    delta3: '−14 pts',
    deltaHint: 'Caída sostenida, no un mes suelto.',
    forecast: '64 · −4',
    forecastHint: 'sigue bajando',
    drivers: [
      { label: 'Meses de caja', contribution: '−4,2', value: '3,1 vs. 4,2 meses' },
      { label: 'Facturación de clientes perdidos', contribution: '−5,2', value: '22 % vs. 8 %' },
      { label: 'Pagos tardíos a proveedores', contribution: '−1,9', value: '18 % vs. 5 %' },
      { label: 'Varias señales a la vez', contribution: '−4,0', value: '3 señales activas' },
    ],
  },
}

const state = computed(() => {
  const mock = states[selected.value]
  const health = companyHealth.value
  if (!health) return { ...mock, headline: 'Score de demostración · pendiente de datos' }
  const delta = health.score_delta_3m
  return { ...mock,
    score: health.health_score.toFixed(1), chip: health.health_band.toUpperCase(),
    scoreColor: health.health_band === 'sano' ? 'var(--ok)' : health.health_band === 'riesgo' ? 'var(--bad)' : 'var(--warn)',
    headline: `Score de ${companyName.value}: ${health.health_score.toFixed(1)}`,
    subhead: `Dato de Supabase · ${health.month.slice(0, 7)}. La previsión a tres meses sigue sin conectar.`,
    band: health.health_band, bandTitle: 'Clasificación registrada en Supabase',
    bandDesc: 'La banda y la nota proceden del mismo mes.',
    delta3: delta == null ? 'Sin dato' : `${delta > 0 ? '+' : ''}${delta.toFixed(1)} pts`,
    deltaHint: 'Variación registrada frente a tres meses antes.',
    forecast: 'Pendiente', forecastHint: 'sin previsión conectada',
    direction: (health.health_trend === 'improving' ? 'up' : health.health_trend === 'deteriorating' ? 'down' : 'flat') as AlertDirection,
  }
})
const arrow = computed(
  () => ({ up: ArrowUp, flat: ArrowRight, down: ArrowDown, alert: ArrowDown })[state.value.direction],
)

/* '−4,2' → 4.2. El guion es un signo menos tipográfico (U+2212), no un ASCII
 * '-', y el decimal va con coma: ninguno de los dos los entiende parseFloat. */
const magnitude = (raw: string) =>
  Math.abs(Number(raw.replace('−', '-').replace('±', '').replace(',', '.'))) || 0

/* Las señales que explican el score se distinguen por cuánto pesan: la barra
 * lleva la magnitud, y el color queda reducido a ese trazo. */
const drivers = computed<CompanyDriver[]>(() => companyHealth.value
  ? companyDetail.data.value?.drivers ?? []
  : state.value.drivers.map(d => ({
    label: d.label,
    display_value: d.value,
    contribution: magnitude(d.contribution) * (/^[−-]/.test(d.contribution) ? -1 : 1),
  })))
const explanation = computed(() => groupScoreDrivers(drivers.value))
const activePillar = ref<ScorePillarId | null>(null)
const activeDetail = computed(() => explanation.value.pillars.find(p => p.id === activePillar.value))
const explanationId = useId()
watch(() => [selectedCompany.value?.company_id, companyHealth.value?.month, selected.value], () => {
  activePillar.value = null
})
</script>

<template>
  <div v-if="!companyDetail.isPending.value" class="centinela tz">
    <TreasuryHead
      v-model="selected"
      :simulate="false"
      :title="`X-Ray Score · ${companyName}`"
      :sync="`Mes del score: ${companyHealth?.month.slice(0, 7) || 'demo'}`"
    />

    <TreasuryAlert
      :direction="state.direction"
      :headline="state.headline"
      :text="state.subhead"
      :cta="state.ctaLabel"
      :cta-filled="state.ctaFilled"
    />

    <!-- El número y su banda conservan el verde/ámbar/rojo: es el único sitio
         de la página, junto a las gráficas, donde el semáforo dice algo. -->
    <section class="tz-card tz-strip xs-reads" aria-label="Lectura del score">
      <div class="xs-score">
        <p class="xs-score__tile" :style="{ color: state.scoreColor }">
          <b>{{ state.score }}</b>
          <span>{{ state.band }}</span>
        </p>
        <div>
          <h2>{{ state.bandTitle }}</h2>
          <p>{{ state.bandDesc }}</p>
        </div>
      </div>
      <!-- Las dos lecturas de apoyo van en tinta normal: la dirección la lleva
           la flecha, no un número teñido. -->
      <div>
        <p class="tz-read__label">
          Cambio en 3 meses
          <component :is="arrow" :size="14" class="xs-arrow" aria-hidden="true" />
        </p>
        <p class="tz-read__figure">{{ state.delta3 }}</p>
        <p class="tz-read__hint">{{ state.deltaHint }}</p>
      </div>
      <div>
        <p class="tz-read__label">
          Previsión a 3 meses
          <component :is="arrow" :size="14" class="xs-arrow" aria-hidden="true" />
        </p>
        <p class="tz-read__figure">{{ state.forecast }}</p>
        <p class="tz-read__hint">{{ state.forecastHint }}</p>
      </div>
    </section>

    <SectorHealthCompare />

    <section class="tz-card xs-explanation" aria-label="Qué explica el score">
      <header class="tz-card__bar">
        <div>
          <h2>Qué explica el score</h2>
          <p>{{ companyHealth ? 'Cinco pilares · contribuciones del mes del score' : 'Cinco pilares · explicaciones simuladas' }}</p>
        </div>
      </header>
      <p class="xs-explanation__note">Selecciona un pilar para entender qué mide y ver sus señales. {{ companyHealth ? 'Los puntos son aportaciones al score, no notas sobre 100 ni cambios respecto al mes anterior.' : 'Los puntos de demostración ilustran el escenario; no reconstruyen una nota real.' }}</p>
      <p v-if="!drivers.length" class="xs-explanation__empty">Sin explicaciones disponibles para este mes. Puedes consultar qué mide cada pilar.</p>
      <ul class="xs-pillars" aria-label="Los cinco pilares del score">
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
        role="region" :aria-labelledby="activePillar ? `${explanationId}-${activePillar}` : undefined">
        <template v-if="activeDetail">
          <div class="xs-pillar-detail__heading">
            <h3>{{ activeDetail.name }}</h3>
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
      <details v-if="explanation.additional.drivers.length" class="xs-adjustments" :key="selectedCompany?.company_id">
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
</template>

<style scoped>
.xs-reads {
  grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr) minmax(0, 1fr);
}

.xs-score {
  display: flex;
  align-items: center;
  gap: 22px;
}

.xs-score__tile {
  display: grid;
  place-items: center;
  align-content: center;
  flex: none;
  width: 120px;
  height: 120px;
  margin: 0;
  border: 1px solid var(--border);
  border-radius: 22px;
  background: var(--wash);
}

.xs-score__tile b {
  font-family: var(--font-display);
  font-size: 50px;
  font-weight: 700;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.xs-score__tile span {
  margin-top: 6px;
  font-size: 12px;
  font-weight: 600;
}

.xs-score h2 {
  margin: 0 0 6px;
  font-family: var(--font-display);
  font-size: 19px;
  font-weight: 600;
  line-height: 1.25;
  text-wrap: balance;
}

.xs-score p {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-2);
}

.xs-arrow {
  color: var(--accent);
}

.xs-explanation__note,
.xs-explanation__empty { color: var(--text-2); font-size: 13px; line-height: 1.6; margin: 0 0 20px; max-width: 85ch; }
.xs-explanation__empty { padding: 12px 16px; background: var(--wash); border-radius: 8px; }
.xs-pillars { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); margin: 0; padding: 0; list-style: none; }
.xs-pillars li { min-width: 0; }
.xs-pillars li + li { border-left: 1px solid var(--border); }
.xs-pillars button { display: flex; flex-direction: column; width: 100%; height: 100%; padding: 18px 16px; border: 0; border-bottom: 2px solid transparent; border-radius: 4px 4px 0 0; background: transparent; color: var(--text); text-align: left; transition: background .15s, border-color .15s; }
.xs-pillars button:hover { background: var(--wash); }
.xs-pillars button[aria-expanded='true'] { background: var(--wash); border-bottom-color: var(--accent); }
.xs-pillars button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
.xs-pillars__name { display: flex; justify-content: space-between; align-items: center; width: 100%; gap: 8px; font-family: var(--font-display); font-size: 15px; font-weight: 600; }
.xs-pillars__name svg { flex: none; color: var(--text-2); transition: transform .15s; }
.xs-pillars button[aria-expanded='true'] svg { transform: rotate(180deg); }
.xs-pillars__question { display: block; margin-top: 8px; margin-bottom: auto; color: var(--text-2); font-size: 12px; line-height: 1.6; }
.xs-pillars__value { display: block; margin-top: 22px; font-family: var(--font-display); font-size: 28px; font-weight: 600; line-height: 1.3; font-variant-numeric: tabular-nums; }
.xs-pillars__value small { font-family: var(--font-body); font-size: 12px; font-weight: 400; color: var(--text-2); }
.xs-pillars__value--empty { font-family: var(--font-body); font-size: 14px; line-height: 2.6; font-weight: 400; }
.xs-pillars__count { display: block; margin-top: 4px; color: var(--text-2); font-size: 12px; }
.xs-pillars__action { display: block; margin-top: 18px; font-size: 12px; color: var(--text-2); text-decoration: underline; text-underline-offset: 3px; }
.xs-pillar-detail { margin-top: 24px; padding-top: 24px; border-top: 1px solid var(--border); }
.xs-pillar-detail__heading { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; flex-wrap: wrap; }
.xs-pillar-detail__heading h3 { font-family: var(--font-display); font-size: 19px; font-weight: 600; }
.xs-pillar-detail__heading > span { color: var(--text-2); font-size: 13px; font-variant-numeric: tabular-nums; }
.xs-pillar-detail__description { max-width: 85ch; margin-top: 12px; font-size: 14px; line-height: 1.65; color: var(--text); }
.xs-pillar-detail__reading { max-width: 90ch; margin: 8px 0 24px; color: var(--text-2); font-size: 13px; line-height: 1.65; }
.xs-pillar-detail__foot { margin: 20px 0 0; color: var(--text-2); font-size: 12px; line-height: 1.6; }
.xs-adjustments { margin-top: 24px; border-top: 1px solid var(--border); }
.xs-adjustments summary { display: flex; align-items: center; gap: 12px; min-height: 52px; padding-block: 12px; list-style: none; cursor: pointer; font-size: 13px; color: var(--text); }
.xs-adjustments summary::-webkit-details-marker { display: none; }
.xs-adjustments summary span { margin-left: auto; color: var(--text-2); white-space: nowrap; }
.xs-adjustments summary svg { flex: none; }
.xs-adjustments[open] summary svg { transform: rotate(180deg); }

@container (max-width: 760px) {
  .xs-pillars { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .xs-pillars li:nth-child(odd) { border-left: 0; }
  .xs-pillars li:nth-child(n + 3) { border-top: 1px solid var(--border); }
  .xs-pillars li:last-child { grid-column: 1 / -1; }
}

@container (max-width: 480px) {
  .xs-pillars { grid-template-columns: minmax(0, 1fr); }
  .xs-pillars li + li { border-left: 0; border-top: 1px solid var(--border); }
  .xs-pillars button { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 4px 16px; padding: 16px 12px; }
  .xs-pillars__name { grid-column: 1 / -1; }
  .xs-pillars__question { grid-column: 1; margin: 0; }
  .xs-pillars__value { grid-column: 2; grid-row: 2 / 4; margin: 0; font-size: 24px; align-self: center; }
  .xs-pillars__value--empty { font-size: 12px; }
  .xs-pillars__count { grid-column: 1; margin: 0; }
  .xs-pillars__action { grid-column: 1 / -1; margin-top: 6px; }
}

@media (prefers-reduced-motion: reduce) {
  .xs-pillars button, .xs-pillars svg { transition: none; }
}

/* Tira con filetes: cuatro señales, ordenadas por lo que pesan. */
.xs-drivers {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: 0;
  padding: 0;
  list-style: none;
}

.xs-drivers li {
  min-width: 0;
  padding: 4px 18px;
}

.xs-drivers li:first-child {
  padding-left: 0;
}

.xs-drivers li + li {
  border-left: 1px solid var(--border);
}

.xs-drivers li > span {
  font-size: 12.5px;
  color: var(--meta);
}

.xs-drivers p {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 2px 10px;
  margin: 6px 0 0;
}

.xs-drivers b {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.xs-drivers small {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-2);
}

.xs-drivers i {
  display: block;
  height: 3px;
  margin-top: 10px;
  border-radius: 2px;
  background: var(--wash);
  overflow: hidden;
}

.xs-drivers i span {
  display: block;
  height: 100%;
  background: var(--accent);
}

@container (max-width: 960px) {
  .xs-reads {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }

  .xs-reads > .xs-score {
    grid-column: 1 / -1;
    border-bottom: 1px solid var(--border);
  }

  .xs-reads > div + div {
    border-top: 0;
    border-left: 1px solid var(--border);
  }

  .xs-reads > .xs-score + div {
    border-left: 0;
  }

  .xs-drivers {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    row-gap: 16px;
  }

  .xs-drivers li:nth-child(odd) {
    padding-left: 0;
    border-left: 0;
  }
}

@container (max-width: 480px) {
  .xs-reads {
    grid-template-columns: minmax(0, 1fr);
  }

  .xs-reads > div + div {
    border-left: 0;
    border-top: 1px solid var(--border);
  }

  .xs-reads > .xs-score {
    border-bottom: 0;
  }

  .xs-score {
    flex-direction: column;
    align-items: flex-start;
  }

  .xs-drivers {
    grid-template-columns: minmax(0, 1fr);
  }

  .xs-drivers li {
    padding: 0;
    border-left: 0;
  }

  .xs-drivers li + li {
    padding-top: 14px;
    border-left: 0;
    border-top: 1px solid var(--border);
  }
}
</style>
