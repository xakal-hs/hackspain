<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  accentColor: { type: String, default: 'var(--accent)' },
  // Suelto, el mock se renderiza entero (1720×1080 con su sidebar y su topbar).
  // Dentro del panel el shell ya lo pone el dashboard: solo va el contenido.
  chrome: { type: Boolean, default: true }
})

const accent = computed(() => props.accentColor)

const selectedState = ref('bien')

// TODO: sustituir por fetch a /api/... cuando el endpoint esté listo
const states = ref({
  bien: {
    color: 'var(--ok)', chip: 'BIEN', dotColor: 'var(--ok)', tag: 'Oportunidad de hedge',
    bannerBg: 'var(--ok-bg)', bannerBorder: 'var(--ok-border)', iconBg: 'var(--ok-chip)', icon: '↓',
    headline: 'Cubre 45k USD ahora y ahorra 900 € vs. el tipo esperado',
    subhead: 'Δ tipo hoy vs previsto ≥ 2 % · volatilidad alta · pago previsto el 15/nov confirmado en el ERP.',
    ctaLabel: 'Ejecutar cobertura',
    ctaBg: 'var(--ok)', ctaText: 'var(--on-status)', ctaBorder: 'var(--ok)',
    exposure: '340k €',
    coverage: '68 %', coverageDelta: '+3 pp esta semana', coverageBar: '68%',
    savingsLabel: 'Ahorro estimado', savings: '+900 €', savingsDelta: 'sobre este pago',
    savingsHint: 'Ahorro acumulado del trimestre: 12.400 € vs. tipos de mercado en la fecha real.',
    heroBg: 'var(--ok-bg)', heroBorder: 'var(--ok-border)',
    spotHistory: '20,110 60,118 100,112 140,108 180,102 220,100 260,105 300,110 340,115 380,120 420,125 460,130',
    spotForecast: '460,130 490,135 520,145 550,150',
    payments: [
      { x: 260, y: 105, color: 'var(--ok)' },
      { x: 380, y: 120, color: 'var(--ok)' },
      { x: 490, y: 135, color: 'var(--ok)' }
    ],
    upcomingPayments: [
      { amount: '45.000 USD', date: '15 nov', counterparty: 'Global Supplies Inc.', status: 'Cubrir hoy · ahorra 900€', bg: 'var(--ok-bg)', border: 'var(--ok-border)', statusBg: 'var(--ok-chip)', statusText: 'var(--ok-strong)' },
      { amount: '18.500 GBP', date: '22 nov', counterparty: 'London Freight Ltd.', status: 'Cubrir esta semana', bg: 'var(--card)', border: 'var(--border)', statusBg: 'var(--warn-bg)', statusText: 'var(--warn-strong)' },
      { amount: '620.000 JPY', date: '01 dic', counterparty: 'Sakura Materials', status: 'Sin urgencia', bg: 'var(--card)', border: 'var(--border)', statusBg: 'var(--wash)', statusText: 'var(--text-2)' }
    ],
    history: [
      { date: '05 sep', title: 'Cobertura 32k USD · ahorro 640 €', desc: 'Ejecutada 8 días antes del pago · tipo 0,915', badge: 'Cerrada', badgeBg: 'var(--ok-bg)', badgeText: 'var(--ok-strong)' },
      { date: '22 ago', title: 'Cobertura 15k GBP · ahorro 320 €', desc: 'Modo auto activado por < 20k€', badge: 'Cerrada', badgeBg: 'var(--ok-bg)', badgeText: 'var(--ok-strong)' },
      { date: '10 ago', title: 'Cobertura 60k USD · ahorro 1.240 €', desc: 'Trimestre anterior · efecto acumulado', badge: 'Cerrada', badgeBg: 'var(--wash)', badgeText: 'var(--text-2)' }
    ]
  },
  normal: {
    color: 'var(--warn)', chip: 'NORMAL', dotColor: 'var(--warn)', tag: 'Sin recomendación',
    bannerBg: 'var(--warn-bg)', bannerBorder: 'var(--warn-border)', iconBg: 'var(--warn-chip)', icon: '→',
    headline: 'Tus exposiciones están bien · sin cobertura sugerida esta semana',
    subhead: 'Los pagos previstos son pequeños o la volatilidad esperada no justifica el spread del hedge.',
    ctaLabel: 'Ajustar sensibilidad',
    ctaBg: 'var(--card)', ctaText: 'var(--text-2)', ctaBorder: 'var(--border)',
    exposure: '48k €',
    coverage: '92 %', coverageDelta: 'estable', coverageBar: '92%',
    savingsLabel: 'Ahorro previsto', savings: '+120 €', savingsDelta: 'trimestre en curso',
    savingsHint: 'No hay operaciones grandes esperadas. Se ejecutará a tipo spot en la fecha.',
    heroBg: 'var(--warn-bg)', heroBorder: 'var(--warn-border)',
    spotHistory: '20,110 60,108 100,112 140,110 180,108 220,111 260,110 300,109 340,111 380,110 420,109 460,110',
    spotForecast: '460,110 490,112 520,110 550,111',
    payments: [
      { x: 300, y: 109, color: 'var(--warn)' },
      { x: 490, y: 112, color: 'var(--warn)' }
    ],
    upcomingPayments: [
      { amount: '4.200 USD', date: '18 nov', counterparty: 'US Design Studio', status: 'Sin urgencia', bg: 'var(--card)', border: 'var(--border)', statusBg: 'var(--wash)', statusText: 'var(--text-2)' },
      { amount: '3.800 GBP', date: '01 dic', counterparty: 'Small Vendor UK', status: 'Sin urgencia', bg: 'var(--card)', border: 'var(--border)', statusBg: 'var(--wash)', statusText: 'var(--text-2)' },
      { amount: '1.100 USD', date: '05 dic', counterparty: 'SaaS License', status: 'Sin urgencia', bg: 'var(--card)', border: 'var(--border)', statusBg: 'var(--wash)', statusText: 'var(--text-2)' }
    ],
    history: [
      { date: '02 sep', title: 'Pago a tipo spot · 3.400 USD', desc: 'Sin cobertura · por debajo del umbral', badge: 'Sin acción', badgeBg: 'var(--wash)', badgeText: 'var(--text-2)' },
      { date: '25 ago', title: 'Pago a tipo spot · 5.100 USD', desc: 'Sin cobertura · por debajo del umbral', badge: 'Sin acción', badgeBg: 'var(--wash)', badgeText: 'var(--text-2)' },
      { date: '10 ago', title: 'Cobertura 22k USD · ahorro 380 €', desc: 'Última cobertura del ciclo', badge: 'Cerrada', badgeBg: 'var(--wash)', badgeText: 'var(--text-2)' }
    ]
  },
  mal: {
    color: 'var(--bad)', chip: 'MAL', dotColor: 'var(--bad)', tag: 'Posición huérfana',
    bannerBg: 'var(--bad-bg)', bannerBorder: 'var(--bad-border)', iconBg: 'var(--bad-chip)', icon: '!',
    headline: 'Tienes 45k USD cubiertos sin pago que los use',
    subhead: 'El ERP canceló el pago de Global Supplies el 12/nov. Tu posición FX abierta pierde 240 €/día al ritmo actual.',
    ctaLabel: 'Revertir posición',
    ctaBg: 'var(--bad)', ctaText: 'var(--on-status)', ctaBorder: 'var(--bad)',
    exposure: '340k €',
    coverage: '73 %', coverageDelta: '−5 pp por posición abierta', coverageBar: '73%',
    savingsLabel: 'Coste diario abierto', savings: '−240 €', savingsDelta: '2 días abierta',
    savingsHint: 'Deshacer al tipo actual limita la pérdida a 480 €. Cada día abierta añade riesgo.',
    heroBg: 'var(--bad-bg)', heroBorder: 'var(--bad-border)',
    spotHistory: '20,90 60,100 100,110 140,120 180,115 220,105 260,115 300,120 340,125 380,140 420,155 460,170',
    spotForecast: '460,170 490,180 520,190 550,195',
    payments: [
      { x: 380, y: 140, color: 'var(--bad)' }
    ],
    upcomingPayments: [
      { amount: '45.000 USD', date: '12 nov · cancelado en ERP', counterparty: 'Global Supplies Inc.', status: 'Posición abierta', bg: 'var(--bad-bg)', border: 'var(--bad-border)', statusBg: 'var(--bad-chip)', statusText: 'var(--bad-strong)' },
      { amount: '18.500 GBP', date: '22 nov', counterparty: 'London Freight Ltd.', status: 'Verificando', bg: 'var(--warn-bg)', border: 'var(--warn-border)', statusBg: 'var(--warn-chip)', statusText: 'var(--warn-strong)' },
      { amount: '620.000 JPY', date: '01 dic', counterparty: 'Sakura Materials', status: 'Sin urgencia', bg: 'var(--card)', border: 'var(--border)', statusBg: 'var(--wash)', statusText: 'var(--text-2)' }
    ],
    history: [
      { date: '13 nov', title: '🔴 Posición huérfana detectada', desc: 'Pago cancelado en ERP tras hedge · aviso al CFO', badge: 'Activa', badgeBg: 'var(--bad-bg)', badgeText: 'var(--bad-strong)' },
      { date: '10 nov', title: 'Cobertura 45k USD ejecutada', desc: 'Ahorro esperado 900 € · antes de la cancelación', badge: 'Sin uso', badgeBg: 'var(--warn-bg)', badgeText: 'var(--warn-strong)' },
      { date: '02 nov', title: 'Cobertura 22k USD · ahorro 360 €', desc: 'Ejecutada y utilizada correctamente', badge: 'Cerrada', badgeBg: 'var(--wash)', badgeText: 'var(--text-2)' }
    ]
  }
})

const state = computed(() => states.value[selectedState.value] || states.value.bien)

const stateOptions = computed(() =>
  [
    { id: 'bien', label: '🟢 BIEN' },
    { id: 'normal', label: '🟡 NORMAL' },
    { id: 'mal', label: '🔴 MAL' }
  ].map((s) => ({
    id: s.id,
    label: s.label,
    bg: s.id === selectedState.value ? 'var(--card)' : 'transparent',
    text: s.id === selectedState.value ? 'var(--text)' : 'var(--text-3)',
    pick: () => { selectedState.value = s.id }
  }))
)
</script>

<template>
  <div
    class="centinela"
    style="box-sizing: border-box; background: var(--bg); color: var(--text); display: flex; overflow: hidden;"
    :style="chrome
      ? { width: '1720px', height: '1080px' }
      : { width: '100%', overflow: 'visible', borderRadius: 'var(--r-panel)' }"
  >

    <!-- SIDEBAR (navy) -->
    <div v-if="chrome" style="width: 250px; flex-shrink: 0; background: linear-gradient(180deg, var(--navy-1) 0%, var(--navy-2) 100%); padding: 22px 16px; display: flex; flex-direction: column; gap: 4px;">
      <div style="display: flex; align-items: center; gap: 10px; padding: 4px 8px 20px; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 12px;">
        <div style="width: 30px; height: 30px; border-radius: var(--r-sm); display: flex; align-items: center; justify-content: center;" :style="{ background: accent }">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 2L4 6V12C4 17 7.5 20.5 12 22C16.5 20.5 20 17 20 12V6L12 2Z" stroke="var(--card)" stroke-width="1.8" stroke-linejoin="round"></path></svg>
        </div>
        <span style="font-family: var(--font-display); font-size: 17px; font-weight: 600; color: var(--on-navy);">Centinela</span>
      </div>

      <a href="WebAppScore.dc.html" class="nav-link"><span style="width: 16px;">◈</span> Inicio</a>
      <a href="WebAppScore.dc.html" class="nav-link"><span style="width: 16px;">☰</span> X-Ray Score</a>
      <a href="WebApp.dc.html" class="nav-link"><span style="width: 16px;">◇</span> Colchón Dinámico</a>

      <!-- Active -->
      <div style="display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: var(--r-sm); background: rgba(255,255,255,0.12); color: var(--on-navy); font-size: 13.5px; font-weight: 600;" :style="{ borderLeft: `3px solid ${accent}` }">
        <span style="width: 16px;">$</span> Divisa Inteligente
        <span style="margin-left: auto; padding: 2px 7px; color: var(--on-status); border-radius: 999px; font-size: 10px; font-weight: 700;" :style="{ background: state.dotColor }">{{ state.chip }}</span>
      </div>

      <a href="Marketplace.dc.html" class="nav-link"><span style="width: 16px;">⚏</span> Contrapartes</a>
      <a href="Marketplace.dc.html" class="nav-link"><span style="width: 16px;">◉</span> Marketplace</a>

      <div style="height: 1px; background: rgba(255,255,255,0.08); margin: 10px 8px;"></div>
      <span style="font-size: 10.5px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--on-navy-4); padding: 0 12px 4px;">Embat</span>
      <div class="nav-sub"><span style="width: 16px;">⇄</span> Conectividad</div>
      <div class="nav-sub"><span style="width: 16px;">▤</span> Pagos</div>
      <div class="nav-sub"><span style="width: 16px;">⧉</span> Conciliación</div>

      <div style="margin-top: auto; padding: 12px; background: rgba(255,255,255,0.06); border-radius: var(--r-lg); display: flex; align-items: center; gap: 10px;">
        <div style="width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: var(--on-navy); font-size: 12px; font-weight: 700; font-family: var(--font-display);" :style="{ background: accent }">CA</div>
        <div style="flex-grow: 1; min-width: 0;">
          <div style="font-size: 12.5px; font-weight: 600; color: var(--on-navy);">César Álvarez</div>
          <div style="font-size: 11px; color: var(--on-navy-3);">Distribuciones Ibérica</div>
        </div>
      </div>
    </div>

    <!-- MAIN -->
    <div style="flex: 1; display: flex; flex-direction: column; min-width: 0; overflow: hidden;" :style="chrome ? null : { overflow: 'visible' }">

      <!-- TOP BAR -->
      <div
        style="display: flex; align-items: center; flex-shrink: 0;"
        :style="chrome
          ? { padding: '16px 32px', background: 'var(--card)', borderBottom: '1px solid var(--border)', justifyContent: 'space-between' }
          : { padding: '22px 24px 0', justifyContent: 'flex-end' }"
      >
        <div v-if="chrome" style="display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--meta);">
          <span>Tesorería</span><span>›</span>
          <span style="color: var(--text); font-weight: 600;">Divisa Inteligente</span>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
          <span style="font-size: 11.5px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; color: var(--text-3);">Simular estado</span>
          <div style="display: flex; background: var(--bg); border-radius: 999px; padding: 3px;">
            <button
              v-for="s in stateOptions"
              :key="s.id"
              type="button"
              style="padding: 6px 14px; border-radius: 999px; font-size: 12.5px; font-weight: 600; cursor: pointer; font-family: var(--font-body); border: none;"
              :style="{ background: s.bg, color: s.text }"
              @click="s.pick"
            >{{ s.label }}</button>
          </div>
        </div>
      </div>

      <!-- CONTENT -->
      <div style="flex: 1; display: flex; flex-direction: column; gap: 18px;" :style="chrome ? { overflowY: 'auto', padding: '26px 32px' } : { padding: '16px 24px 22px' }">

        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
          <div>
            <h1 style="margin: 0 0 6px; font-family: var(--font-display); font-size: 26px; font-weight: 600;">Divisa Inteligente</h1>
            <p style="margin: 0; font-size: 13.5px; color: var(--meta);">Predice tus pagos en divisa y cubre al mejor tipo antes de la fecha del cobro o pago.</p>
          </div>
          <div style="display: flex; align-items: center; gap: 10px; padding: 8px 14px; background: var(--card); border: 1px solid var(--border); border-radius: 999px; font-size: 12.5px; color: var(--text-2);">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--ok);"></span>
            Conectado con Business Central
          </div>
        </div>

        <!-- BANNER -->
        <div
          style="border-radius: var(--r-lg); padding: 16px 20px; display: flex; align-items: center; gap: 16px;"
          :style="{ background: state.bannerBg, border: `1px solid ${state.bannerBorder}`, borderLeft: `4px solid ${state.color}` }"
        >
          <div style="width: 40px; height: 40px; border-radius: var(--r-lg); display: flex; align-items: center; justify-content: center; font-size: 18px;" :style="{ background: state.iconBg }">{{ state.icon }}</div>
          <div style="flex-grow: 1;">
            <div style="font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 2px;" :style="{ color: state.color }">{{ state.tag }}</div>
            <div style="font-family: var(--font-display); font-size: 16.5px; font-weight: 600; margin-bottom: 3px;">{{ state.headline }}</div>
            <div style="font-size: 13px; color: var(--body); line-height: 1.5;">{{ state.subhead }}</div>
          </div>
          <button
            type="button"
            style="padding: 12px 22px; border-radius: var(--r-md); font-size: 13.5px; font-weight: 600; cursor: pointer; font-family: var(--font-body); white-space: nowrap;"
            :style="{ background: state.ctaBg, color: state.ctaText, border: `1px solid ${state.ctaBorder}` }"
          >{{ state.ctaLabel }}</button>
        </div>

        <!-- HERO -->
        <div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px;">

          <div class="card" style="padding: 20px 22px;">
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
              <span style="font-size: 12.5px; color: var(--meta);">Exposición FX · próximo trimestre</span>
              <span style="font-size: 11px; color: var(--text-3); font-weight: 600;">USD · GBP · JPY</span>
            </div>
            <div style="font-family: var(--font-display); font-size: 30px; font-weight: 700; margin-top: 8px;">{{ state.exposure }}</div>
            <div style="font-size: 12px; color: var(--text-2); margin-top: 6px;">Previsto por el forecaster h1-h3</div>
          </div>

          <div class="card" style="padding: 20px 22px;">
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
              <span style="font-size: 12.5px; color: var(--meta);">Cobertura actual</span>
              <span style="font-size: 11px; font-weight: 600;" :style="{ color: state.color }">{{ state.coverageDelta }}</span>
            </div>
            <div style="font-family: var(--font-display); font-size: 30px; font-weight: 700; margin-top: 8px;">{{ state.coverage }}</div>
            <div style="margin-top: 10px;">
              <div style="height: 6px; background: var(--wash); border-radius: 3px; overflow: hidden;">
                <div style="height: 100%; border-radius: 3px;" :style="{ width: state.coverageBar, background: state.color }"></div>
              </div>
            </div>
          </div>

          <div style="border-radius: var(--r-lg); padding: 20px 22px;" :style="{ background: state.heroBg, border: `1px solid ${state.heroBorder}` }">
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
              <span style="font-size: 12.5px; color: var(--meta);">{{ state.savingsLabel }}</span>
              <span style="font-size: 11px; font-weight: 600;" :style="{ color: state.color }">{{ state.savingsDelta }}</span>
            </div>
            <div style="font-family: var(--font-display); font-size: 32px; font-weight: 700; margin-top: 8px;" :style="{ color: state.color }">{{ state.savings }}</div>
            <div style="font-size: 12px; color: var(--text-2); margin-top: 8px; line-height: 1.4;">{{ state.savingsHint }}</div>
          </div>

        </div>

        <!-- FX CHART + PANEL -->
        <div style="display: grid; grid-template-columns: 1.6fr 1fr; gap: 16px;">

          <div class="card" style="padding: 20px 22px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <div>
                <div style="font-size: 13.5px; font-weight: 600;">Evolución EUR/USD · pagos previstos</div>
                <div style="font-size: 11.5px; color: var(--text-3); margin-top: 2px;">Tipo actual + predicción del forecaster h1-h3</div>
              </div>
              <span style="padding: 4px 10px; background: var(--wash); color: var(--text-2); border-radius: 6px; font-size: 11.5px; font-weight: 600;">EUR / USD</span>
            </div>
            <svg width="100%" height="220" viewBox="0 0 700 220" preserveAspectRatio="none">
              <line x1="10" y1="180" x2="690" y2="180" stroke="var(--grid)" stroke-width="1"></line>
              <line x1="10" y1="130" x2="690" y2="130" stroke="var(--grid)" stroke-width="1"></line>
              <line x1="10" y1="80" x2="690" y2="80" stroke="var(--grid)" stroke-width="1"></line>
              <line x1="10" y1="30" x2="690" y2="30" stroke="var(--grid)" stroke-width="1"></line>

              <polyline :points="state.spotHistory" fill="none" stroke="var(--text)" stroke-width="2" stroke-linecap="round"></polyline>
              <polyline :points="state.spotForecast" fill="none" stroke="var(--text)" stroke-width="2" stroke-linecap="round" stroke-dasharray="5,5" opacity="0.5"></polyline>

              <circle v-for="(p, i) in state.payments" :key="i" :cx="p.x" :cy="p.y" r="7" :fill="p.color" stroke="var(--card)" stroke-width="2"></circle>
            </svg>
            <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-3);">
              <span>oct '25</span><span>ene '26</span><span>hoy</span><span>h3 →</span>
            </div>
            <div style="display: flex; gap: 14px; margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--grid);">
              <div class="legend-item"><span style="width: 12px; height: 2px; background: var(--text);"></span> Tipo real</div>
              <div class="legend-item"><span style="width: 12px; height: 2px; background: var(--text); opacity: 0.5;"></span> Predicción h3</div>
              <div class="legend-item"><span style="width: 10px; height: 10px; border-radius: 50%;" :style="{ background: state.color }"></span> Pago FX previsto</div>
            </div>
          </div>

          <!-- Payments queue -->
          <div class="card" style="padding: 18px 20px;">
            <div style="font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-3); margin-bottom: 12px;">Próximos pagos en divisa</div>
            <div style="display: flex; flex-direction: column; gap: 10px;">
              <div
                v-for="pay in state.upcomingPayments"
                :key="pay.amount"
                style="border-radius: var(--r-md); padding: 12px 14px; display: flex; flex-direction: column; gap: 6px;"
                :style="{ border: `1px solid ${pay.border}`, background: pay.bg }"
              >
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                  <span style="font-size: 13px; font-weight: 600;">{{ pay.amount }}</span>
                  <span style="font-size: 11.5px; color: var(--meta);">{{ pay.date }}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <span style="font-size: 11.5px; color: var(--meta);">{{ pay.counterparty }}</span>
                  <span style="padding: 3px 8px; border-radius: 999px; font-size: 10.5px; font-weight: 600;" :style="{ background: pay.statusBg, color: pay.statusText }">{{ pay.status }}</span>
                </div>
              </div>
            </div>
          </div>

        </div>

        <!-- HISTORY -->
        <div class="card" style="padding: 18px 22px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <div style="font-size: 13.5px; font-weight: 600;">Coberturas recientes</div>
            <span style="font-size: 12px; font-weight: 600;" :style="{ color: accent }">Ver todo →</span>
          </div>
          <div>
            <div
              v-for="h in state.history"
              :key="h.date"
              style="display: grid; grid-template-columns: 90px 1fr auto; gap: 14px; align-items: center; padding: 10px 0; border-top: 1px solid var(--grid);"
            >
              <span style="font-size: 11.5px; color: var(--text-3);">{{ h.date }}</span>
              <div>
                <div style="font-size: 13px; font-weight: 600;">{{ h.title }}</div>
                <div style="font-size: 11.5px; color: var(--meta); margin-top: 2px;">{{ h.desc }}</div>
              </div>
              <span style="padding: 4px 10px; border-radius: 999px; font-size: 11.5px; font-weight: 600;" :style="{ background: h.badgeBg, color: h.badgeText }">{{ h.badge }}</span>
            </div>
          </div>
        </div>

      </div>
    </div>

  </div>
</template>

<style scoped>
/* Se repiten idénticos varias veces en el markup del mock. */
.nav-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--r-sm);
  color: var(--on-navy-3);
  font-size: 13.5px;
  text-decoration: none;
}

.nav-sub {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: var(--r-sm);
  color: var(--on-navy-3);
  font-size: 13px;
}

.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: var(--text-2);
}
</style>
