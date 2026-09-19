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
    // El semáforo solo sobrevive en la gráfica; el resto de la vista va en el
    // color primario.
    chartColor: 'var(--ok)', chip: 'BIEN', tag: 'Oportunidad detectada', icon: '↑',
    headline: 'Puedes colocar 300k€ sin comprometer tu colchón',
    subhead: 'Excedente sostenido 2 meses · score 78 · runway h3 > 3 meses. Rendimiento estimado: +1.240 €/mes.',
    ctaLabel: 'Colocar 300k€', ctaFilled: true,
    cash: '620k €',
    excedenteLabel: 'Excedente colocable', excedente: '380k €', excedenteDelta: '+120k vs. mes ant.',
    excedenteHint: 'Al ritmo del forecast h3, puedes colocar sin devolver antes de tiempo.',
    chartHistory: '20,175 60,168 100,165 140,155 180,140 220,130 260,125 300,115 340,100 380,90 420,80 460,70',
    chartForecast: '460,70 490,60 520,55 550,52',
    chartLastX: '460', chartLastY: '70',
    drivers: [
      { label: 'Excedente sostenido', value: '2 meses', dot: 'var(--accent)' },
      { label: 'Score X-Ray', value: '78 · sano', dot: 'var(--accent)' },
      { label: 'Runway h3', value: '4,8 meses', dot: 'var(--accent)' },
      { label: 'Tipo depósito preferente', value: '3,2 %', dot: null }
    ],
    autoMode: 'Colocación automática', autoOn: true,
    autoHint: 'Activa: excedentes > 100k€ sostenidos 2m se colocan sin confirmación.',
    history: [
      { date: '11 sep', title: 'Colocación automática 220k€', desc: 'Depósito 30 días · tipo 3,1%', badge: 'Activa', badgeTone: 'var(--accent)' },
      { date: '28 ago', title: 'Devolución al vencimiento', desc: 'Depósito de 180k€ recuperado en tiempo · sin ruptura', badge: 'Cerrada', badgeTone: null },
      { date: '14 ago', title: 'Colocación manual 150k€', desc: 'CFO ejecutó desde el chat del agente', badge: 'Cerrada', badgeTone: null }
    ]
  },
  normal: {
    chartColor: 'var(--warn)', chip: 'NORMAL', tag: 'Sin acción esta semana', icon: '→',
    headline: 'Excedente en observación · esperamos confirmación',
    subhead: 'El excedente es volátil este mes (±80k€). Volvemos a evaluar el 12/dic. No sugerimos colocar aún.',
    ctaLabel: 'Ajustar umbrales', ctaFilled: false,
    cash: '340k €',
    excedenteLabel: 'Excedente colocable', excedente: '80k €', excedenteDelta: '±30k volatilidad',
    excedenteHint: 'Por debajo del umbral de 100k€. Podría ser un pico puntual.',
    chartHistory: '20,120 60,135 100,110 140,145 180,120 220,150 260,110 300,140 340,120 380,145 420,115 460,140',
    chartForecast: '460,140 490,135 520,140 550,138',
    chartLastX: '460', chartLastY: '140',
    drivers: [
      { label: 'Excedente sostenido', value: '< 1 mes', dot: 'var(--accent)' },
      { label: 'Score X-Ray', value: '62 · vigilancia', dot: 'var(--accent)' },
      { label: 'Volatilidad de caja', value: 'Alta', dot: 'var(--accent)' },
      { label: 'Próxima evaluación', value: '12 dic', dot: null }
    ],
    autoMode: 'Colocación automática', autoOn: false,
    autoHint: 'Desactivada por volatilidad. Requiere confirmación manual del CFO.',
    history: [
      { date: '11 sep', title: 'Excedente vuelto por bajo runway h3', desc: 'Sistema esperó y no colocó — evitó rotura de caja', badge: 'Silencio', badgeTone: 'var(--accent)' },
      { date: '04 sep', title: 'Umbral no alcanzado', desc: 'Excedente 65k€ · por debajo del mínimo de 100k€', badge: 'Sin acción', badgeTone: null },
      { date: '20 ago', title: 'Colocación anterior devuelta', desc: 'Cierre normal, sin nuevas colocaciones esperadas 2 semanas', badge: 'Cerrada', badgeTone: null }
    ]
  },
  mal: {
    chartColor: 'var(--bad)', chip: 'MAL', tag: 'Alerta anticipada', icon: '↓',
    headline: 'Prepara la devolución del depósito antes del 30/nov',
    subhead: 'Forecaster h3 predice runway 1,8 meses. Devuelve 120k€ del depósito activo o quedas por debajo del colchón.',
    ctaLabel: 'Devolver 120k€ ahora', ctaFilled: true,
    cash: '285k €',
    excedenteLabel: 'Excedente colocable', excedente: '−45k €', excedenteDelta: '−165k vs. mes ant.',
    excedenteHint: 'Estás por debajo del colchón necesario. Necesitas devolver parte del depósito.',
    chartHistory: '20,60 60,70 100,80 140,90 180,100 220,110 260,120 300,135 340,150 380,165 420,175 460,180',
    chartForecast: '460,180 490,190 520,195 550,200',
    chartLastX: '460', chartLastY: '180',
    drivers: [
      { label: 'Runway h3 previsto', value: '1,8 meses', dot: 'var(--accent)' },
      { label: 'Score X-Ray', value: '68 · vigilancia', dot: 'var(--accent)' },
      { label: 'ap_late_share ↑', value: '+0,10 (3m)', dot: 'var(--accent)' },
      { label: 'Depósito activo', value: '220k € · vence 15 dic', dot: null }
    ],
    autoMode: 'Colocación automática', autoOn: false,
    autoHint: 'Pausada · el sistema no colocará hasta que la trayectoria se estabilice.',
    history: [
      { date: '18 sep', title: 'Alerta anticipada emitida', desc: '3 meses antes del cash-crunch previsto · chat del agente activo', badge: 'Activa', badgeTone: 'var(--accent)' },
      { date: '05 sep', title: 'Primera señal detectada', desc: 'runway h3 baja del umbral · sistema empieza vigilancia intensiva', badge: 'Detectada', badgeTone: null },
      { date: '20 ago', title: 'Última colocación exitosa', desc: '220k€ colocados · en momento aún saludable', badge: 'Cerrada', badgeTone: null }
    ]
  }
})

const state = computed(() => states.value[selectedState.value] || states.value.bien)

const stateOptions = computed(() =>
  [
    { id: 'bien', label: 'Bien' },
    { id: 'normal', label: 'Normal' },
    { id: 'mal', label: 'Mal' }
  ].map((s) => {
    const isSelected = s.id === selectedState.value
    return {
      id: s.id,
      label: s.label,
      bg: isSelected ? 'var(--card)' : 'transparent',
      text: isSelected ? 'var(--text)' : 'var(--text-3)',
      pick: () => { selectedState.value = s.id }
    }
  })
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

      <!-- Logo -->
      <div style="display: flex; align-items: center; gap: 10px; padding: 4px 8px 20px; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 12px;">
        <div style="width: 30px; height: 30px; border-radius: var(--r-sm); display: flex; align-items: center; justify-content: center;" :style="{ background: accent }">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 2L4 6V12C4 17 7.5 20.5 12 22C16.5 20.5 20 17 20 12V6L12 2Z" stroke="var(--card)" stroke-width="1.8" stroke-linejoin="round"></path></svg>
        </div>
        <span style="font-family: var(--font-display); font-size: 17px; font-weight: 600; color: var(--on-navy);">Centinela</span>
      </div>

      <!-- Nav items -->
      <a href="WebAppScore.dc.html" class="nav-link">
        <span style="width: 16px;">◈</span> Inicio
      </a>
      <a href="WebAppScore.dc.html" class="nav-link">
        <span style="width: 16px;">☰</span> X-Ray Score
      </a>

      <!-- Active -->
      <div style="display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: var(--r-sm); background: rgba(255,255,255,0.12); color: var(--on-navy); font-size: 13.5px; font-weight: 600;" :style="{ borderLeft: `3px solid ${accent}` }">
        <span style="width: 16px;">◇</span> Colchón Dinámico
        <span style="margin-left: auto; padding: 2px 7px; color: var(--accent-on); border-radius: 999px; font-size: 10px; font-weight: 700;" :style="{ background: accent }">{{ state.chip }}</span>
      </div>

      <a href="WebAppDivisa.dc.html" class="nav-link">
        <span style="width: 16px;">$</span> Divisa Inteligente
      </a>
      <a href="Marketplace.dc.html" class="nav-link">
        <span style="width: 16px;">⚏</span> Contrapartes
      </a>
      <a href="Marketplace.dc.html" class="nav-link">
        <span style="width: 16px;">◉</span> Marketplace
      </a>

      <div style="height: 1px; background: rgba(255,255,255,0.08); margin: 10px 8px;"></div>

      <span style="font-size: 10.5px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--on-navy-4); padding: 0 12px 4px;">Embat</span>
      <div class="nav-sub">
        <span style="width: 16px;">⇄</span> Conectividad
      </div>
      <div class="nav-sub">
        <span style="width: 16px;">▤</span> Pagos
      </div>
      <div class="nav-sub">
        <span style="width: 16px;">⧉</span> Conciliación
      </div>

      <!-- User -->
      <div style="margin-top: auto; padding: 12px; background: rgba(255,255,255,0.06); border-radius: var(--r-lg); display: flex; align-items: center; gap: 10px;">
        <div style="width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: var(--on-navy); font-size: 12px; font-weight: 700; font-family: var(--font-display);" :style="{ background: accent }">CA</div>
        <div style="flex-grow: 1; min-width: 0;">
          <div style="font-size: 12.5px; font-weight: 600; color: var(--on-navy);">César Álvarez</div>
          <div style="font-size: 11px; color: var(--on-navy-3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">Distribuciones Ibérica</div>
        </div>
      </div>

    </div>

    <!-- MAIN COLUMN -->
    <div style="flex: 1; display: flex; flex-direction: column; min-width: 0; overflow: hidden;" :style="chrome ? null : { overflow: 'visible' }">

      <!-- TOP BAR -->
      <div
        style="display: flex; align-items: center; flex-shrink: 0;"
        :style="chrome
          ? { padding: '16px 32px', background: 'var(--card)', borderBottom: '1px solid var(--border)', justifyContent: 'space-between' }
          : { padding: '22px 24px 0', justifyContent: 'flex-end' }"
      >
        <div v-if="chrome" style="display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--meta);">
          <span>Tesorería</span>
          <span>›</span>
          <span style="color: var(--text); font-weight: 600;">Colchón Dinámico</span>
        </div>

        <!-- STATE SIMULATOR -->
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

        <!-- PAGE HEADER -->
        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
          <div>
            <h1 style="margin: 0 0 6px; font-family: var(--font-display); font-size: 26px; font-weight: 600;">Colchón Dinámico</h1>
            <p style="margin: 0; font-size: 13.5px; color: var(--meta);">Divide tu caja en lo que necesitas y lo que no. Coloca el excedente, prevé las devoluciones.</p>
          </div>
          <div style="display: flex; align-items: center; gap: 10px; padding: 8px 14px; background: var(--card); border: 1px solid var(--border); border-radius: 999px; font-size: 12.5px; color: var(--text-2);">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--text-3);"></span>
            Sincronizado hace 4 min
          </div>
        </div>

        <!-- STATE BANNER. Único bloque teñido de la página, y en primario: el
             verde/ámbar/rojo se queda para la gráfica de abajo. -->
        <div
          style="border-radius: var(--r-lg); padding: 16px 20px; display: flex; align-items: center; gap: 16px;"
          :style="{
            background: `color-mix(in srgb, ${accent} 9%, transparent)`,
            border: `1px solid color-mix(in srgb, ${accent} 26%, transparent)`,
            borderLeft: `4px solid ${accent}`
          }"
        >
          <div style="width: 40px; height: 40px; border-radius: var(--r-lg); display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0;" :style="{ background: `color-mix(in srgb, ${accent} 16%, transparent)` }">{{ state.icon }}</div>
          <div style="flex-grow: 1;">
            <div style="font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 2px;" :style="{ color: accent }">{{ state.tag }}</div>
            <div style="font-family: var(--font-display); font-size: 16.5px; font-weight: 600; margin-bottom: 3px;">{{ state.headline }}</div>
            <div style="font-size: 13px; color: var(--body); line-height: 1.5;">{{ state.subhead }}</div>
          </div>
          <button
            type="button"
            style="padding: 12px 22px; border-radius: var(--r-md); font-size: 13.5px; font-weight: 600; cursor: pointer; font-family: var(--font-body); white-space: nowrap;"
            :style="state.ctaFilled
              ? { background: 'var(--accent-solid)', color: 'var(--accent-on)', border: '1px solid var(--accent-solid)' }
              : { background: 'var(--card)', color: 'var(--text-2)', border: '1px solid var(--border)' }"
          >{{ state.ctaLabel }}</button>
        </div>

        <!-- HERO KPIs -->
        <div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px;">

          <div class="card" style="padding: 20px 22px;">
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
              <span style="font-size: 12.5px; color: var(--meta);">Caja actual</span>
              <span style="font-size: 11px; color: var(--text-2); font-weight: 600;">+ 24k € esta semana</span>
            </div>
            <div style="font-family: var(--font-display); font-size: 30px; font-weight: 700; margin-top: 8px;">{{ state.cash }}</div>
            <!-- Sparkline de contexto, no la gráfica de la página: va en tinta
                 apagada para que el único trazo con color sea el de abajo. -->
            <div style="height: 32px; margin-top: 10px;">
              <svg width="100%" height="32" viewBox="0 0 200 32" preserveAspectRatio="none"><polyline points="0,26 20,24 40,22 60,18 80,16 100,14 120,14 140,12 160,10 180,8 200,6" fill="none" stroke="var(--text-3)" stroke-width="2" stroke-linecap="round"></polyline></svg>
            </div>
          </div>

          <div class="card" style="padding: 20px 22px;">
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
              <span style="font-size: 12.5px; color: var(--meta);">Colchón necesario</span>
              <span style="font-size: 11px; color: var(--text-3); font-weight: 600;">2× mediana gasto</span>
            </div>
            <div style="font-family: var(--font-display); font-size: 30px; font-weight: 700; margin-top: 8px;">240k €</div>
            <div style="margin-top: 12px;">
              <div style="height: 6px; background: var(--wash); border-radius: 3px; overflow: hidden;">
                <div style="width: 72%; height: 100%; border-radius: 3px;" :style="{ background: accent }"></div>
              </div>
              <div style="font-size: 11.5px; color: var(--text-3); margin-top: 6px;">Cubierto 72% · confianza h3 90%</div>
            </div>
          </div>

          <div class="card" style="padding: 20px 22px;">
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
              <span style="font-size: 12.5px; color: var(--meta);">{{ state.excedenteLabel }}</span>
              <span style="font-size: 11px; font-weight: 600;" :style="{ color: accent }">{{ state.excedenteDelta }}</span>
            </div>
            <div style="font-family: var(--font-display); font-size: 32px; font-weight: 700; margin-top: 8px;" :style="{ color: accent }">{{ state.excedente }}</div>
            <div style="font-size: 12px; color: var(--text-2); margin-top: 8px; line-height: 1.4;">{{ state.excedenteHint }}</div>
          </div>

        </div>

        <!-- CHART + SIDE PANEL -->
        <div style="display: grid; grid-template-columns: 1.6fr 1fr; gap: 16px;">

          <!-- Chart card -->
          <div class="card" style="padding: 20px 22px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <div>
                <div style="font-size: 13.5px; font-weight: 600;">Excedente colocable · últimos 12 meses</div>
                <div style="font-size: 11.5px; color: var(--text-3); margin-top: 2px;">Con predicción h3 · umbral de decisión en 100 k€</div>
              </div>
              <div style="display: flex; gap: 6px;">
                <span style="padding: 4px 8px; background: var(--wash); color: var(--text-2); border-radius: 6px; font-size: 11.5px; font-weight: 600;">12 M</span>
                <span style="padding: 4px 8px; color: var(--text-3); font-size: 11.5px; font-weight: 600;">24 M</span>
              </div>
            </div>
            <svg width="100%" height="220" viewBox="0 0 700 220" preserveAspectRatio="none">
              <line x1="10" y1="180" x2="690" y2="180" stroke="var(--grid)" stroke-width="1"></line>
              <line x1="10" y1="130" x2="690" y2="130" stroke="var(--grid)" stroke-width="1"></line>
              <line x1="10" y1="80" x2="690" y2="80" stroke="var(--grid)" stroke-width="1"></line>
              <line x1="10" y1="30" x2="690" y2="30" stroke="var(--grid)" stroke-width="1"></line>
              <!-- El umbral es una referencia, no una medida: va en gris para
                   que el color quede reservado al trazo del excedente. -->
              <line x1="10" y1="150" x2="690" y2="150" stroke="var(--text-3)" stroke-width="1" stroke-dasharray="4,4" opacity="0.6"></line>
              <text x="14" y="146" font-size="10" fill="var(--text-3)" style="font-family: var(--font-display);">umbral 100k€</text>

              <polyline :points="state.chartHistory" fill="none" :stroke="state.chartColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"></polyline>
              <polyline :points="state.chartForecast" fill="none" :stroke="state.chartColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="5,5" opacity="0.7"></polyline>
              <circle :cx="state.chartLastX" :cy="state.chartLastY" r="5" :fill="state.chartColor" stroke="var(--card)" stroke-width="2"></circle>
            </svg>
            <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-3);">
              <span>oct '25</span><span>abr '26</span><span>hoy</span><span>predicción h3 →</span>
            </div>
            <div style="display: flex; gap: 14px; margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--grid);">
              <div class="legend-item"><span style="width: 12px; height: 2px;" :style="{ background: state.chartColor }"></span> Excedente real</div>
              <div class="legend-item"><span style="width: 12px; height: 2px; opacity: 0.6;" :style="{ background: state.chartColor }"></span> Predicción h3 (banda 80%)</div>
            </div>
          </div>

          <!-- Side panel -->
          <div style="display: flex; flex-direction: column; gap: 14px;">

            <div class="card" style="padding: 18px 20px;">
              <div style="font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-3); margin-bottom: 10px;">Qué explica esta decisión</div>
              <div style="display: flex; flex-direction: column; gap: 10px;">
                <div
                  v-for="d in state.drivers"
                  :key="d.label"
                  style="display: flex; justify-content: space-between; align-items: center; gap: 12px; font-size: 12.5px;"
                >
                  <span style="color: var(--body);">{{ d.label }}</span>
                  <!-- El valor va en tinta normal; el punto, de 5px, es todo lo
                       que hace falta para marcar una señal fuera de rango. -->
                  <span style="display: flex; align-items: center; gap: 6px; font-weight: 600; font-family: var(--font-display); white-space: nowrap;">
                    <span v-if="d.dot" style="width: 5px; height: 5px; border-radius: 50%;" :style="{ background: d.dot }"></span>
                    {{ d.value }}
                  </span>
                </div>
              </div>
            </div>

            <div class="card" style="padding: 18px 20px;">
              <div style="font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-3); margin-bottom: 10px;">Modo de operación</div>
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                <span style="font-size: 13px; color: var(--body);">{{ state.autoMode }}</span>
                <!-- Encendido va en acento, no en verde: es un control, no un
                     veredicto sobre la salud de la caja. -->
                <div style="width: 38px; height: 22px; border-radius: 999px; padding: 3px; box-sizing: border-box;" :style="{ background: state.autoOn ? accent : 'var(--wash)' }">
                  <div style="width: 16px; height: 16px; background: var(--card); border-radius: 50%;" :style="{ marginLeft: state.autoOn ? '16px' : '0px' }"></div>
                </div>
              </div>
              <div style="font-size: 11.5px; color: var(--meta); line-height: 1.4;">{{ state.autoHint }}</div>
            </div>

          </div>

        </div>

        <!-- HISTORY -->
        <div class="card" style="padding: 18px 22px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <div style="font-size: 13.5px; font-weight: 600;">Historial reciente</div>
            <span style="font-size: 12px; font-weight: 600; cursor: pointer; color: var(--text-2);">Ver todo →</span>
          </div>
          <div style="display: flex; flex-direction: column;">
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
              <!-- Un historial son sobre todo entradas cerradas: esas van en
                   gris. Solo la que sigue abierta se lleva el color, y de
                   contorno en vez de relleno. -->
              <span
                style="padding: 4px 10px; border-radius: 999px; font-size: 11.5px; font-weight: 600;"
                :style="h.badgeTone
                  ? { background: 'transparent', border: `1px solid color-mix(in srgb, ${h.badgeTone} 45%, transparent)`, color: h.badgeTone }
                  : { background: 'var(--wash)', border: '1px solid transparent', color: 'var(--text-2)' }"
              >{{ h.badge }}</span>
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
