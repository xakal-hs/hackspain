<script setup>
import { computed, ref } from 'vue'
import { leadCompany } from '~/data/demo'

const props = defineProps({
  accentColor: { type: String, default: 'var(--accent)' },
  // Suelto, el mock se renderiza entero (1720×1080 con su sidebar y su topbar).
  // Dentro del panel el shell ya lo pone el dashboard: solo va el contenido.
  chrome: { type: Boolean, default: true }
})

const accent = computed(() => props.accentColor)

const selectedState = ref('mal')

// TODO: sustituir por fetch a /api/... cuando el endpoint esté listo
const states = ref({
  bien: {
    color: 'var(--ok)', chip: 'BIEN', dotColor: 'var(--ok)', tag: 'Mejora sostenida',
    bannerBg: 'var(--ok-bg)', bannerBorder: 'var(--ok-border)', iconBg: 'var(--ok-chip)', icon: '↑',
    headline: 'Tu score subió 20 puntos en 4 meses',
    subhead: 'La mejora es sostenible: viene de mejor gestión de cobro con facturación estable. Hay una ventana para pedir mejores condiciones.',
    ctaLabel: 'Ver 3 oportunidades',
    ctaBg: 'var(--ok)', ctaText: 'var(--on-status)', ctaBorder: 'var(--ok)',
    score: '65', bandText: 'Banda: SANO', bandTitle: 'Trayectoria ascendente confirmada',
    bandDesc: 'Salta al tramo preferente del marketplace. Score consolidado por 3 meses seguidos.',
    heroBg: 'var(--ok-bg)',
    delta3: '+20 pts', deltaHint: 'Mejora sostenida en 4 meses. Sin señales de reversión.',
    forecast: '68 · +3', forecastHint: 'sigue mejorando en h3',
    chartTag: 'Consolidada 3 meses', chartTagBg: 'var(--ok-bg)',
    chartHistory: '20,160 60,158 100,155 140,153 180,150 220,148 260,140 300,132 340,120 380,110 420,100 460,88',
    chartForecast: '460,88 490,80 520,72 550,68',
    chartLastX: '460', chartLastY: '88', chartMarkerX: '260', chartMarkerY: '140',
    agentStatus: 'Modo oportunidades', agentMessage: 'Vuestra trayectoria está limpia. Aquí van 3 movimientos para capitalizarla antes de que el mercado lo vea.',
    recommendations: [
      { n: '1', title: 'Ampliar línea de crédito', impact: 'Hasta 40k € · tipo preferente' },
      { n: '2', title: 'Cerrar precios a 12m', impact: 'Con proveedores clave · protege margen' },
      { n: '3', title: 'Entrar al marketplace', impact: 'Con score 65 accedes al mejor tramo' }
    ],
    drivers: [
      { label: 'ar_late_share (cobros)', contribution: '+4,8', value: '38 días vs. 60d', color: 'var(--ok)', bg: 'var(--ok-bg)', border: 'var(--ok-border)' },
      { label: 'growth_vs_12m', contribution: '+3,2', value: '+18 % vs. 12m', color: 'var(--ok)', bg: 'var(--ok-bg)', border: 'var(--ok-border)' },
      { label: 'cust_trend', contribution: '+2,4', value: '+0,3 clientes/m', color: 'var(--ok)', bg: 'var(--ok-bg)', border: 'var(--ok-border)' },
      { label: 'runway', contribution: '+2,0', value: '4,2 meses', color: 'var(--ok)', bg: 'var(--ok-bg)', border: 'var(--ok-border)' }
    ]
  },
  normal: {
    color: 'var(--warn)', chip: 'NORMAL', dotColor: 'var(--warn)', tag: 'Score estable',
    bannerBg: 'var(--warn-bg)', bannerBorder: 'var(--warn-border)', iconBg: 'var(--warn-chip)', icon: '→',
    headline: 'Sin novedades desde tu última revisión',
    subhead: 'El score se mantiene en su banda. Sin cambios significativos en las señales que lo componen. No pasa nada, y eso también es una señal.',
    ctaLabel: 'Explorar detalle',
    ctaBg: 'var(--card)', ctaText: 'var(--text-2)', ctaBorder: 'var(--border)',
    score: '62', bandText: 'Banda: VIGILANCIA', bandTitle: 'Estable en zona intermedia',
    bandDesc: 'Δ3m dentro de ±5 pts. Ni oportunidad clara, ni riesgo activo. Seguimos observando.',
    heroBg: 'var(--warn-bg)',
    delta3: '±2 pts', deltaHint: 'Dentro del margen de ruido esperado.',
    forecast: '62 · 0', forecastHint: 'trayectoria plana en h3',
    chartTag: 'Sin cambios significativos', chartTagBg: 'var(--warn-bg)',
    chartHistory: '20,110 60,108 100,112 140,110 180,108 220,112 260,110 300,109 340,111 380,110 420,109 460,110',
    chartForecast: '460,110 490,112 520,110 550,111',
    chartLastX: '460', chartLastY: '110', chartMarkerX: '260', chartMarkerY: '110',
    agentStatus: 'Modo silencio activo', agentMessage: 'Sin recomendaciones esta semana. El silencio también es una feature: te aviso cuando algo cambie de verdad.',
    recommendations: [
      { n: '1', title: 'Sin acciones sugeridas', impact: 'Vigilamos por ti · siguiente revisión: 26 sep' }
    ],
    drivers: [
      { label: 'runway', contribution: '±0', value: '3,4 meses · estable', color: 'var(--text)', bg: 'var(--card)', border: 'var(--border)' },
      { label: 'ap_late_share', contribution: '+0,2', value: 'sin cambio', color: 'var(--text)', bg: 'var(--card)', border: 'var(--border)' },
      { label: 'activity_trend', contribution: '−0,1', value: 'ruido de mes', color: 'var(--text)', bg: 'var(--card)', border: 'var(--border)' },
      { label: 'lost_share', contribution: '±0', value: '4 % base', color: 'var(--text)', bg: 'var(--card)', border: 'var(--border)' }
    ]
  },
  mal: {
    color: 'var(--bad)', chip: 'MAL', dotColor: 'var(--bad)', tag: 'Deterioro sostenido',
    bannerBg: 'var(--bad-bg)', bannerBorder: 'var(--bad-border)', iconBg: 'var(--bad-chip)', icon: '↓',
    headline: 'Vuestro score bajó 14 puntos en 3 meses',
    subhead: 'Detectado 3 meses antes de que se note en caja. Coste de circulante +15 % y 3 proveedores concentran el 60 % del retraso en los pagos.',
    ctaLabel: 'Abrir chat del agente',
    ctaBg: 'var(--bad)', ctaText: 'var(--on-status)', ctaBorder: 'var(--bad)',
    score: '68', bandText: 'Banda: VIGILANCIA', bandTitle: 'Trayectoria descendente detectada',
    bandDesc: 'Bajaste desde banda SANA (≥ 65) en 3 meses. El forecaster h3 predice más caída si no actúas.',
    heroBg: 'var(--bad-bg)',
    delta3: '−14 pts', deltaHint: 'Caída sostenida, no un mes suelto.',
    forecast: '64 · −4', forecastHint: 'sigue bajando en h3',
    chartTag: 'Detectado 3 meses antes', chartTagBg: 'var(--wash)',
    chartHistory: '20,60 60,62 100,58 140,65 180,68 220,72 260,80 300,88 340,95 380,105 420,112 460,120',
    chartForecast: '460,120 490,132 520,142 550,150',
    chartLastX: '460', chartLastY: '120', chartMarkerX: '260', chartMarkerY: '80',
    agentStatus: 'Alerta activa · esperando acción', agentMessage: 'Te escribí sin que preguntes. La caja aún no lo nota, pero el ritmo dice que llegará. Te propongo tres movimientos para pararlo.',
    recommendations: [
      { n: '1', title: 'Refinanciar la línea de circulante', impact: 'Ahorro est. 2.400 €/mes' },
      { n: '2', title: 'Renegociar plazos con 3 proveedores', impact: 'Alivia tensión de caja' },
      { n: '3', title: 'Apretar el cobro a 2 clientes', impact: 'Libera ~18.000 €' }
    ],
    drivers: [
      { label: 'runway', contribution: '−4,2', value: '3,1 vs. 4,2 meses', color: 'var(--bad)', bg: 'var(--bad-bg)', border: 'var(--bad-border)' },
      { label: 'lost_share', contribution: '−5,2', value: '22 % vs. 8 %', color: 'var(--bad)', bg: 'var(--bad-bg)', border: 'var(--bad-border)' },
      { label: 'ap_late_share', contribution: '−1,9', value: '18 % vs. 5 %', color: 'var(--bad)', bg: 'var(--bad-bg)', border: 'var(--bad-border)' },
      { label: 'multi_signal_stress', contribution: '−4,0', value: '3 señales activas', color: 'var(--bad)', bg: 'var(--bad-bg)', border: 'var(--bad-border)' }
    ]
  }
})

const state = computed(() => states.value[selectedState.value] || states.value.mal)

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

      <!-- Active -->
      <div style="display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: var(--r-sm); background: rgba(255,255,255,0.12); color: var(--on-navy); font-size: 13.5px; font-weight: 600;" :style="{ borderLeft: `3px solid ${accent}` }">
        <span style="width: 16px;">☰</span> X-Ray Score
        <span style="margin-left: auto; padding: 2px 7px; color: var(--on-status); border-radius: 999px; font-size: 10px; font-weight: 700;" :style="{ background: state.dotColor }">{{ state.chip }}</span>
      </div>

      <a href="WebApp.dc.html" class="nav-link"><span style="width: 16px;">◇</span> Colchón Dinámico</a>
      <a href="WebAppDivisa.dc.html" class="nav-link"><span style="width: 16px;">$</span> Divisa Inteligente</a>
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
          <span>Análisis</span><span>›</span>
          <span style="color: var(--text); font-weight: 600;">X-Ray Score</span>
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
            <h1 style="margin: 0 0 6px; font-family: var(--font-display); font-size: 26px; font-weight: 600;">X-Ray Score · Distribuciones Ibérica</h1>
            <p style="margin: 0; font-size: 13.5px; color: var(--meta);">Tu salud financiera explicada · basado en 24 meses de rastro financiero.</p>
          </div>
          <div style="display: flex; align-items: center; gap: 10px; padding: 8px 14px; background: var(--card); border: 1px solid var(--border); border-radius: 999px; font-size: 12.5px; color: var(--text-2);">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--ok);"></span>
            Última actualización: hace 4 min
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

        <!-- HERO KPIs -->
        <div style="display: grid; grid-template-columns: 1.3fr 1fr 1fr; gap: 16px;">

          <!-- Big score card -->
          <div class="card" style="padding: 24px; display: flex; align-items: center; gap: 22px;">
            <div
              style="width: 130px; height: 130px; border-radius: 24px; display: flex; flex-direction: column; align-items: center; justify-content: center; flex-shrink: 0;"
              :style="{ background: state.heroBg, border: `3px solid ${state.color}` }"
            >
              <div style="font-family: var(--font-display); font-size: 52px; font-weight: 700; line-height: 1;" :style="{ color: state.color }">{{ state.score }}</div>
              <div style="font-size: 10.5px; color: var(--text-3); letter-spacing: 0.06em; margin-top: 4px;">SCORE X-RAY</div>
            </div>
            <div style="flex-grow: 1;">
              <div style="font-size: 12px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase;" :style="{ color: state.color }">{{ state.bandText }}</div>
              <div style="font-family: var(--font-display); font-size: 20px; font-weight: 600; margin: 6px 0;">{{ state.bandTitle }}</div>
              <div style="font-size: 13px; color: var(--text-2); line-height: 1.5;">{{ state.bandDesc }}</div>
            </div>
          </div>

          <div class="card" style="padding: 20px 22px;">
            <div style="font-size: 12.5px; color: var(--meta);">Cambio 3 meses</div>
            <div style="font-family: var(--font-display); font-size: 30px; font-weight: 700; margin-top: 8px;" :style="{ color: state.color }">{{ state.delta3 }}</div>
            <div style="font-size: 12px; color: var(--text-2); margin-top: 6px; line-height: 1.4;">{{ state.deltaHint }}</div>
          </div>

          <div class="card" style="padding: 20px 22px;">
            <div style="font-size: 12.5px; color: var(--meta);">Predicción h3</div>
            <div style="font-family: var(--font-display); font-size: 30px; font-weight: 700; margin-top: 8px;" :style="{ color: state.color }">{{ state.forecast }}</div>
            <div style="font-size: 12px; color: var(--text-2); margin-top: 6px; line-height: 1.4;">Banda 80 % · {{ state.forecastHint }}</div>
          </div>

        </div>

        <div class="card" style="padding: 18px 22px;">
          <div style="margin-bottom: 12px;">
            <div style="font-size: 13.5px; font-weight: 600;">Frente al sector</div>
            <div style="font-size: 11.5px; color: var(--text-3); margin-top: 2px;">
              Score y plazos frente a la mediana de distribución alimentaria · comparativa anónima
            </div>
          </div>
          <SectorCompare :company="leadCompany" :score="Number(state.score)" />
        </div>

        <!-- CHART + AGENT -->
        <div style="display: grid; grid-template-columns: 1.6fr 1fr; gap: 16px;">

          <!-- Trajectory -->
          <div class="card" style="padding: 20px 22px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <div>
                <div style="font-size: 13.5px; font-weight: 600;">Trayectoria del score · últimos 24 meses</div>
                <div style="font-size: 11.5px; color: var(--text-3); margin-top: 2px;">Historia + predicción h1-h3 con banda de confianza</div>
              </div>
              <span style="padding: 5px 12px; border-radius: 999px; font-size: 12px; font-weight: 600;" :style="{ background: state.chartTagBg, color: state.color }">{{ state.chartTag }}</span>
            </div>
            <svg width="100%" height="220" viewBox="0 0 700 220" preserveAspectRatio="none">
              <rect x="10" y="30" width="680" height="60" fill="var(--ok-bg)" opacity="0.4"></rect>
              <rect x="10" y="90" width="680" height="60" fill="var(--warn-bg)" opacity="0.4"></rect>
              <rect x="10" y="150" width="680" height="40" fill="var(--bad-bg)" opacity="0.4"></rect>

              <text x="14" y="46" font-size="10" fill="var(--ok-strong)" style="font-family: var(--font-display);" font-weight="600">SANO ≥ 65</text>
              <text x="14" y="106" font-size="10" fill="var(--warn-strong)" style="font-family: var(--font-display);" font-weight="600">VIGILANCIA</text>
              <text x="14" y="166" font-size="10" fill="var(--bad-strong)" style="font-family: var(--font-display);" font-weight="600">RIESGO ≤ 35</text>

              <polyline :points="state.chartHistory" fill="none" :stroke="state.color" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"></polyline>
              <polyline :points="state.chartForecast" fill="none" :stroke="state.color" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="6,6" opacity="0.6"></polyline>
              <circle :cx="state.chartLastX" :cy="state.chartLastY" r="6" :fill="state.color" stroke="var(--card)" stroke-width="2.5"></circle>
              <circle :cx="state.chartMarkerX" :cy="state.chartMarkerY" r="5" :fill="accent" stroke="var(--card)" stroke-width="2"></circle>
            </svg>
            <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-3);">
              <span>hace 24m</span><span>hace 12m</span><span>hoy</span><span>h3 →</span>
            </div>
          </div>

          <!-- Agent panel -->
          <div style="background: linear-gradient(160deg, var(--navy-1) 0%, var(--navy-2) 100%); border-radius: var(--r-lg); padding: 20px 22px; color: var(--on-navy); display: flex; flex-direction: column; gap: 12px;">
            <div style="display: flex; align-items: center; gap: 10px;">
              <div style="width: 32px; height: 32px; border-radius: var(--r-md); display: flex; align-items: center; justify-content: center; font-family: var(--font-display); font-size: 13px; font-weight: 700;" :style="{ background: accent }">A</div>
              <div style="flex-grow: 1;">
                <div style="font-family: var(--font-display); font-size: 14px; font-weight: 600;">Agente Centinela</div>
                <div style="font-size: 11.5px; color: var(--on-navy-3);">{{ state.agentStatus }}</div>
              </div>
              <span style="width: 8px; height: 8px; border-radius: 50%;" :style="{ background: state.dotColor }"></span>
            </div>

            <div style="background: rgba(255,255,255,0.06); border-radius: var(--r-lg); padding: 14px; font-size: 13px; line-height: 1.5; color: var(--on-navy);">
              "{{ state.agentMessage }}"
            </div>

            <div style="font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--on-navy-3); margin-top: 4px;">Recomendaciones esta semana</div>

            <div style="display: flex; flex-direction: column; gap: 8px;">
              <div
                v-for="r in state.recommendations"
                :key="r.n"
                style="background: rgba(255,255,255,0.06); border-radius: var(--r-md); padding: 10px 12px; display: flex; align-items: center; gap: 10px;"
              >
                <span style="width: 24px; height: 24px; border-radius: 6px; color: var(--on-navy); display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; font-family: var(--font-display);" :style="{ background: accent }">{{ r.n }}</span>
                <div style="flex-grow: 1; min-width: 0;">
                  <div style="font-size: 12.5px; font-weight: 600;">{{ r.title }}</div>
                  <div style="font-size: 11px; color: var(--on-navy-2); margin-top: 1px;">{{ r.impact }}</div>
                </div>
              </div>
            </div>
          </div>

        </div>

        <!-- DRIVERS -->
        <div class="card" style="padding: 18px 22px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <div>
              <div style="font-size: 13.5px; font-weight: 600;">Qué explica el score</div>
              <div style="font-size: 11.5px; color: var(--text-3); margin-top: 2px;">Contribución exacta de cada señal · suma al score total</div>
            </div>
            <span style="font-size: 12px; font-weight: 600;" :style="{ color: accent }">Ver todas las features →</span>
          </div>
          <div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px;">
            <div
              v-for="d in state.drivers"
              :key="d.label"
              style="border-radius: var(--r-md); padding: 12px 14px;"
              :style="{ background: d.bg, border: `1px solid ${d.border}` }"
            >
              <div style="font-size: 11.5px; color: var(--meta); margin-bottom: 4px;">{{ d.label }}</div>
              <div style="display: flex; justify-content: space-between; align-items: baseline;">
                <span style="font-family: var(--font-display); font-size: 18px; font-weight: 700;" :style="{ color: d.color }">{{ d.contribution }}</span>
                <span style="font-size: 11px; color: var(--text-2); font-weight: 600;">{{ d.value }}</span>
              </div>
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
</style>
