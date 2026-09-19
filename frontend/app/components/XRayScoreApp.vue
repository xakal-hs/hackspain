<script setup lang="ts">
import { ArrowDown, ArrowRight, ArrowUp } from '@lucide/vue'
import type { AlertDirection } from './TreasuryAlert.vue'
import type { TreasuryState } from './TreasuryHead.vue'

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
    drivers: (companyDetail.data.value?.drivers || []).map(driver => ({
      label: driver.label, value: driver.display_value,
      contribution: `${driver.contribution > 0 ? '+' : ''}${driver.contribution.toFixed(1)}`,
      color: 'var(--accent)',
    })),
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
const drivers = computed(() => {
  const rows = state.value.drivers
  const peak = Math.max(...rows.map((d) => magnitude(d.contribution)), 1)
  return rows.map((d) => ({
    ...d,
    weight: `${Math.round((magnitude(d.contribution) / peak) * 100)}%`,
  }))
})
</script>

<template>
  <div v-if="!companyDetail.isPending.value" class="centinela tz">
    <TreasuryHead
      v-model="selected"
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

    <section class="tz-card">
      <header class="tz-card__bar">
        <div>
          <h2>Qué explica el score</h2>
          <p>{{ companyHealth ? 'Contribuciones registradas en Supabase' : 'Explicaciones simuladas' }}</p>
        </div>
      </header>
      <p v-if="!drivers.length">Sin explicaciones disponibles para este mes.</p>
      <ul class="xs-drivers">
        <li v-for="d in drivers" :key="d.label">
          <ScoreFieldHelp :label="d.label" :value="d.value">
            <p>
              <b>{{ d.contribution }}</b><small>{{ d.value }}</small>
            </p>
            <i aria-hidden="true"><span :style="{ width: d.weight }"></span></i>
          </ScoreFieldHelp>
        </li>
      </ul>
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
