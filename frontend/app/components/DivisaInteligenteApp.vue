<script setup lang="ts">
import type { AlertDirection } from './TreasuryAlert.vue'
import type { LogEntry } from './TreasuryLog.vue'
import type { TreasuryState } from './TreasuryHead.vue'

const selected = ref<TreasuryState>('bien')

interface Payment {
  amount: string
  date: string
  counterparty: string
  status: string
  urgent?: boolean
}

// TODO: sustituir por fetch a /api/... cuando el endpoint esté listo
const states: Record<
  TreasuryState,
  {
    chartColor: string
    direction: AlertDirection
    headline: string
    subhead: string
    ctaLabel: string
    ctaFilled: boolean
    exposure: string
    coverage: string
    coverageDelta: string
    coverageBar: string
    savingsLabel: string
    savings: string
    savingsDelta: string
    savingsHint: string
    spotHistory: string
    spotForecast: string
    payments: [number, number][]
    upcomingPayments: Payment[]
    history: LogEntry[]
  }
> = {
  bien: {
    // El semáforo solo sobrevive en los puntos de pago de la gráfica; el resto
    // de la vista va en el color primario.
    chartColor: 'var(--ok)',
    direction: 'down',
    headline: 'Cubre 45k USD ahora y ahorra 900 € frente al tipo esperado',
    subhead:
      'El tipo de hoy mejora el previsto en un 2 % o más · volatilidad alta · pago previsto el 15 de noviembre, confirmado en el ERP.',
    ctaLabel: 'Ejecutar cobertura',
    ctaFilled: true,
    exposure: '340k €',
    coverage: '68 %',
    coverageDelta: '+3 pp esta semana',
    coverageBar: '68%',
    savingsLabel: 'Ahorro estimado',
    savings: '+900 €',
    savingsDelta: 'sobre este pago',
    savingsHint: 'Ahorro acumulado del trimestre: 12.400 € frente a los tipos de mercado en la fecha real.',
    spotHistory:
      '20,110 60,118 100,112 140,108 180,102 220,100 260,105 300,110 340,115 380,120 420,125 460,130',
    spotForecast: '460,130 490,135 520,145 550,150',
    payments: [
      [260, 105],
      [380, 120],
      [490, 135],
    ],
    upcomingPayments: [
      { amount: '45.000 USD', date: '15 nov', counterparty: 'Global Supplies Inc.', status: 'Cubrir hoy · ahorra 900 €', urgent: true },
      { amount: '18.500 GBP', date: '22 nov', counterparty: 'London Freight Ltd.', status: 'Cubrir esta semana' },
      { amount: '620.000 JPY', date: '01 dic', counterparty: 'Sakura Materials', status: 'Sin urgencia' },
    ],
    history: [
      { date: '05 sep', title: 'Cobertura 32k USD · ahorro 640 €', desc: 'Ejecutada 8 días antes del pago · tipo 0,915', badge: 'Cerrada' },
      { date: '22 ago', title: 'Cobertura 15k GBP · ahorro 320 €', desc: 'Modo automático, por ser menor de 20k €', badge: 'Cerrada' },
      { date: '10 ago', title: 'Cobertura 60k USD · ahorro 1.240 €', desc: 'Trimestre anterior · efecto acumulado', badge: 'Cerrada' },
    ],
  },
  normal: {
    chartColor: 'var(--warn)',
    direction: 'flat',
    headline: 'Tus exposiciones están bien: sin cobertura sugerida esta semana',
    subhead:
      'Los pagos previstos son pequeños o la volatilidad esperada no justifica el coste de la cobertura.',
    ctaLabel: 'Ajustar sensibilidad',
    ctaFilled: false,
    exposure: '48k €',
    coverage: '92 %',
    coverageDelta: 'estable',
    coverageBar: '92%',
    savingsLabel: 'Ahorro previsto',
    savings: '+120 €',
    savingsDelta: 'trimestre en curso',
    savingsHint: 'No hay operaciones grandes previstas. Se pagará al tipo de contado en la fecha.',
    spotHistory:
      '20,110 60,108 100,112 140,110 180,108 220,111 260,110 300,109 340,111 380,110 420,109 460,110',
    spotForecast: '460,110 490,112 520,110 550,111',
    payments: [
      [300, 109],
      [490, 112],
    ],
    upcomingPayments: [
      { amount: '4.200 USD', date: '18 nov', counterparty: 'US Design Studio', status: 'Sin urgencia' },
      { amount: '3.800 GBP', date: '01 dic', counterparty: 'Small Vendor UK', status: 'Sin urgencia' },
      { amount: '1.100 USD', date: '05 dic', counterparty: 'SaaS License', status: 'Sin urgencia' },
    ],
    history: [
      { date: '02 sep', title: 'Pago al contado · 3.400 USD', desc: 'Sin cobertura · por debajo del umbral', badge: 'Sin acción' },
      { date: '25 ago', title: 'Pago al contado · 5.100 USD', desc: 'Sin cobertura · por debajo del umbral', badge: 'Sin acción' },
      { date: '10 ago', title: 'Cobertura 22k USD · ahorro 380 €', desc: 'Última cobertura del ciclo', badge: 'Cerrada' },
    ],
  },
  mal: {
    chartColor: 'var(--bad)',
    direction: 'alert',
    headline: 'Tienes 45k USD cubiertos sin pago que los use',
    subhead:
      'El ERP canceló el pago de Global Supplies el 12 de noviembre. Tu posición abierta en divisa pierde 240 €/día al ritmo actual.',
    ctaLabel: 'Revertir posición',
    ctaFilled: true,
    exposure: '340k €',
    coverage: '73 %',
    coverageDelta: '−5 pp por posición abierta',
    coverageBar: '73%',
    savingsLabel: 'Coste diario abierto',
    savings: '−240 €',
    savingsDelta: '2 días abierta',
    savingsHint: 'Deshacer al tipo actual limita la pérdida a 480 €. Cada día abierta añade riesgo.',
    spotHistory:
      '20,90 60,100 100,110 140,120 180,115 220,105 260,115 300,120 340,125 380,140 420,155 460,170',
    spotForecast: '460,170 490,180 520,190 550,195',
    payments: [[380, 140]],
    upcomingPayments: [
      { amount: '45.000 USD', date: '12 nov · cancelado en el ERP', counterparty: 'Global Supplies Inc.', status: 'Posición abierta', urgent: true },
      { amount: '18.500 GBP', date: '22 nov', counterparty: 'London Freight Ltd.', status: 'Verificando' },
      { amount: '620.000 JPY', date: '01 dic', counterparty: 'Sakura Materials', status: 'Sin urgencia' },
    ],
    history: [
      { date: '13 nov', title: 'Posición huérfana detectada', desc: 'Pago cancelado en el ERP tras la cobertura · aviso al CFO', badge: 'Activa', open: true },
      { date: '10 nov', title: 'Cobertura 45k USD ejecutada', desc: 'Ahorro esperado de 900 €, antes de la cancelación', badge: 'Sin uso' },
      { date: '02 nov', title: 'Cobertura 22k USD · ahorro 360 €', desc: 'Ejecutada y utilizada correctamente', badge: 'Cerrada' },
    ],
  },
}

const state = computed(() => states[selected.value])
</script>

<template>
  <div class="centinela tz">
    <TreasuryHead
      v-model="selected"
      title="Divisa Inteligente"
      lead="Prevé tus pagos en divisa y cubre al mejor tipo antes de la fecha del cobro o del pago."
      sync="Conectado con Business Central"
    />

    <TreasuryAlert
      :direction="state.direction"
      :headline="state.headline"
      :text="state.subhead"
      :cta="state.ctaLabel"
      :cta-filled="state.ctaFilled"
    />

    <section class="tz-card tz-strip" aria-label="Exposición, cobertura y ahorro">
      <div>
        <p class="tz-read__label">Exposición en divisa · próximo trimestre <b>USD · GBP · JPY</b></p>
        <p class="tz-read__figure">{{ state.exposure }}</p>
        <p class="tz-read__hint">Previsión a tres meses</p>
      </div>
      <div>
        <p class="tz-read__label">Cobertura actual <b class="is-accent">{{ state.coverageDelta }}</b></p>
        <p class="tz-read__figure">{{ state.coverage }}</p>
        <div class="tz-meter" aria-hidden="true"><span :style="{ width: state.coverageBar }"></span></div>
      </div>
      <div>
        <p class="tz-read__label">
          {{ state.savingsLabel }} <b class="is-accent">{{ state.savingsDelta }}</b>
        </p>
        <p class="tz-read__figure is-accent">{{ state.savings }}</p>
        <p class="tz-read__hint">{{ state.savingsHint }}</p>
      </div>
    </section>

    <div class="tz-split">
      <section class="tz-card tz-chart">
        <header class="tz-card__bar">
          <div>
            <h2>Evolución EUR/USD · pagos previstos</h2>
            <p>Tipo actual y previsión a tres meses</p>
          </div>
          <span class="tz-tag">EUR / USD</span>
        </header>
        <svg
          viewBox="0 0 700 220"
          preserveAspectRatio="none"
          role="img"
          aria-label="Tipo EUR/USD de los últimos 12 meses con previsión a tres meses y los pagos en divisa previstos."
        >
          <line
            v-for="y in [30, 80, 130, 180]"
            :key="y"
            x1="10"
            :y1="y"
            x2="690"
            :y2="y"
            stroke="var(--grid)"
            vector-effect="non-scaling-stroke"
          />
          <polyline
            :points="state.spotHistory"
            fill="none"
            stroke="var(--text)"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            vector-effect="non-scaling-stroke"
          />
          <polyline
            :points="state.spotForecast"
            fill="none"
            stroke="var(--text)"
            stroke-width="2"
            stroke-linecap="round"
            stroke-dasharray="5 5"
            opacity="0.5"
            vector-effect="non-scaling-stroke"
          />
          <!-- Trazos de longitud cero con remate redondo: círculos que no se
               deforman aunque el SVG se estire. -->
          <g v-for="([x, y], i) in state.payments" :key="i">
            <path
              :d="`M${x} ${y}h0`"
              stroke="var(--card)"
              stroke-width="18"
              stroke-linecap="round"
              vector-effect="non-scaling-stroke"
            />
            <path
              :d="`M${x} ${y}h0`"
              :stroke="state.chartColor"
              stroke-width="14"
              stroke-linecap="round"
              vector-effect="non-scaling-stroke"
            />
          </g>
        </svg>
        <p class="tz-chart__axis" aria-hidden="true">
          <span>oct '25</span><span>ene '26</span><span>hoy</span><span>+3 meses</span>
        </p>
        <ul class="tz-legend">
          <li><i style="color: var(--text)"></i>Tipo real</li>
          <li><i class="is-dashed" style="color: var(--text)"></i>Previsión</li>
          <li><i class="is-dot" :style="{ background: state.chartColor }"></i>Pago en divisa previsto</li>
        </ul>
      </section>

      <!-- La cola de pagos es casi toda rutina: solo el pago que pide una
           decisión hoy lleva el chip con color. -->
      <section class="tz-card">
        <header class="tz-card__bar"><h2>Próximos pagos en divisa</h2></header>
        <ul class="dv-queue">
          <li v-for="pay in state.upcomingPayments" :key="pay.amount">
            <p>
              <b>{{ pay.amount }}</b><time>{{ pay.date }}</time>
            </p>
            <p>
              <span>{{ pay.counterparty }}</span>
              <em class="tz-badge" :class="{ 'is-open': pay.urgent }">{{ pay.status }}</em>
            </p>
          </li>
        </ul>
      </section>
    </div>

    <TreasuryLog title="Coberturas recientes" :entries="state.history" />
  </div>
</template>

<style scoped>
.dv-queue {
  margin: 0;
  padding: 0;
  list-style: none;
}

.dv-queue li {
  display: grid;
  gap: 6px;
  padding: 12px 0;
  border-top: 1px solid var(--grid);
}

.dv-queue li:first-child {
  padding-top: 0;
  border-top: 0;
}

.dv-queue p {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 4px 8px;
  margin: 0;
}

.dv-queue b {
  font-size: 13.5px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.dv-queue time,
.dv-queue span {
  font-size: 12.5px;
  color: var(--meta);
}
</style>
