<script setup lang="ts">
import type { AlertDirection } from './TreasuryAlert.vue'
import type { LogEntry } from './TreasuryLog.vue'
import type { TreasuryState } from './TreasuryHead.vue'

const selected = ref<TreasuryState>('bien')

interface Fact {
  label: string
  value: string
  flagged?: boolean
}

const { name: companyName, sector: companySector, detail: companyDetail, latest: companyLatest, health: companyHealth, company: selectedCompany } = useSelectedCompany()

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
    cash: string
    excedente: string
    excedenteDelta: string
    excedenteHint: string
    chartHistory: string
    chartForecast: string
    chartLast: [number, number]
    drivers: Fact[]
    autoOn: boolean
    autoHint: string
    history: LogEntry[]
  }
> = {
  bien: {
    // El semáforo solo sobrevive en la gráfica; el resto de la vista va en el
    // color primario.
    chartColor: 'var(--ok)',
    direction: 'up',
    headline: 'Puedes colocar 300k € sin comprometer tu colchón',
    subhead:
      'Excedente sostenido 2 meses · score 78 · caja prevista a 3 meses por encima de 3 meses de gasto. Rendimiento estimado: +1.240 €/mes.',
    ctaLabel: 'Colocar 300k €',
    ctaFilled: true,
    cash: '620k €',
    excedente: '380k €',
    excedenteDelta: '+120k vs. mes anterior',
    excedenteHint: 'Al ritmo previsto, puedes colocar sin devolver antes de tiempo.',
    chartHistory:
      '20,175 60,168 100,165 140,155 180,140 220,130 260,125 300,115 340,100 380,90 420,80 460,70',
    chartForecast: '460,70 490,60 520,55 550,52',
    chartLast: [460, 70],
    drivers: [
      { label: 'Excedente sostenido', value: '2 meses', flagged: true },
      { label: 'Score X-Ray', value: '78 · sano', flagged: true },
      { label: 'Caja prevista a 3 meses', value: '4,8 meses', flagged: true },
      { label: 'Tipo depósito preferente', value: '3,2 %' },
    ],
    autoOn: true,
    autoHint: 'Activa: los excedentes de más de 100k € sostenidos 2 meses se colocan sin confirmación.',
    history: [
      { date: '11 sep', title: 'Colocación automática 220k €', desc: 'Depósito 30 días · tipo 3,1 %', badge: 'Activa', open: true },
      { date: '28 ago', title: 'Devolución al vencimiento', desc: 'Depósito de 180k € recuperado en tiempo · sin ruptura', badge: 'Cerrada' },
      { date: '14 ago', title: 'Colocación manual 150k €', desc: 'El CFO la ejecutó desde el chat del agente', badge: 'Cerrada' },
    ],
  },
  normal: {
    chartColor: 'var(--warn)',
    direction: 'flat',
    headline: 'Excedente en observación: esperamos confirmación',
    subhead:
      'El excedente es volátil este mes (±80k €). Volvemos a evaluar el 12 de diciembre. No sugerimos colocar aún.',
    ctaLabel: 'Ajustar umbrales',
    ctaFilled: false,
    cash: '340k €',
    excedente: '80k €',
    excedenteDelta: '±30k de volatilidad',
    excedenteHint: 'Por debajo del umbral de 100k €. Podría ser un pico puntual.',
    chartHistory:
      '20,120 60,135 100,110 140,145 180,120 220,150 260,110 300,140 340,120 380,145 420,115 460,140',
    chartForecast: '460,140 490,135 520,140 550,138',
    chartLast: [460, 140],
    drivers: [
      { label: 'Excedente sostenido', value: '< 1 mes', flagged: true },
      { label: 'Score X-Ray', value: '62 · vigilancia', flagged: true },
      { label: 'Volatilidad de caja', value: 'Alta', flagged: true },
      { label: 'Próxima evaluación', value: '12 dic' },
    ],
    autoOn: false,
    autoHint: 'Desactivada por volatilidad. Requiere confirmación manual del CFO.',
    history: [
      { date: '11 sep', title: 'Excedente retenido por poca caja prevista', desc: 'El sistema esperó y no colocó: evitó una rotura de caja', badge: 'Silencio', open: true },
      { date: '04 sep', title: 'Umbral no alcanzado', desc: 'Excedente de 65k €, por debajo del mínimo de 100k €', badge: 'Sin acción' },
      { date: '20 ago', title: 'Colocación anterior devuelta', desc: 'Cierre normal, sin nuevas colocaciones esperadas en 2 semanas', badge: 'Cerrada' },
    ],
  },
  mal: {
    chartColor: 'var(--bad)',
    direction: 'down',
    headline: 'Prepara la devolución del depósito antes del 30 de noviembre',
    subhead:
      'La previsión a tres meses deja la caja en 1,8 meses de gasto. Devuelve 120k € del depósito activo o quedarás por debajo del colchón.',
    ctaLabel: 'Devolver 120k € ahora',
    ctaFilled: true,
    cash: '285k €',
    excedente: '−45k €',
    excedenteDelta: '−165k vs. mes anterior',
    excedenteHint: 'Estás por debajo del colchón necesario. Necesitas devolver parte del depósito.',
    chartHistory:
      '20,60 60,70 100,80 140,90 180,100 220,110 260,120 300,135 340,150 380,165 420,175 460,180',
    chartForecast: '460,180 490,190 520,195 550,200',
    chartLast: [460, 180],
    drivers: [
      { label: 'Caja prevista a 3 meses', value: '1,8 meses', flagged: true },
      { label: 'Score X-Ray', value: '68 · vigilancia', flagged: true },
      { label: 'Pagos tardíos a proveedores', value: '+10 pp en 3 meses', flagged: true },
      { label: 'Depósito activo', value: '220k € · vence 15 dic' },
    ],
    autoOn: false,
    autoHint: 'Pausada: el sistema no colocará hasta que la trayectoria se estabilice.',
    history: [
      { date: '18 sep', title: 'Alerta anticipada emitida', desc: '3 meses antes de la falta de caja prevista · chat del agente activo', badge: 'Activa', open: true },
      { date: '05 sep', title: 'Primera señal detectada', desc: 'La caja prevista baja del umbral · empieza la vigilancia intensiva', badge: 'Detectada' },
      { date: '20 ago', title: 'Última colocación', desc: '220k € colocados, en un momento aún saludable', badge: 'Cerrada' },
    ],
  },
}

const state = computed(() => {
  const mock = states[selected.value]
  const row = companyLatest.value
  const cash = row?.cash_end
  const currency = selectedCompany.value?.currency
  return { ...mock,
    cash: cash == null || !currency ? 'Sin dato' : `${new Intl.NumberFormat('es-ES', { maximumFractionDigits: 2 }).format(cash)} ${currency}`,
    drivers: [
      { label: 'Caja / pagos mensuales · dato real', value: row?.runway_m == null ? 'Sin dato' : `${row.runway_m.toFixed(1)} meses`, flagged: true },
      { label: 'Score X-Ray · dato real', value: companyHealth.value?.health_score.toFixed(1) ?? 'Sin dato', flagged: true },
      ...mock.drivers.slice(2).map(driver => ({ ...driver, label: `${driver.label} · demo` })),
    ],
  }
})


</script>

<template>
  <div v-if="!companyDetail.isPending.value" class="centinela tz">
    <TreasuryHead
      v-model="selected"
      :title="`Colchón Dinámico · ${companyName}`"
      :sync="`Mes de caja: ${companyLatest?.month || 'sin dato'}`"
    />

    <TreasuryAlert
      :direction="state.direction"
      :headline="`Ejemplo simulado · ${state.headline}`"
      :text="state.subhead"
      :cta="state.ctaLabel"
      :cta-filled="state.ctaFilled"
    />

    <section class="tz-card tz-strip" aria-label="Caja, colchón y excedente">
      <div>
        <p class="tz-read__label">Caja reconstruida <b>{{ selectedCompany?.currency || 'Sin moneda' }} · dato del panel</b></p>
        <p class="tz-read__figure">{{ state.cash }}</p>
      </div>
      <div>
        <p class="tz-read__label">Colchón necesario <b>2× la mediana de gasto</b></p>
        <p class="tz-read__figure">240k €</p>
        <div class="tz-meter" aria-hidden="true"><span style="width: 72%"></span></div>
        <p class="tz-read__hint">Cubierto al 72 % · confianza del 90 %</p>
      </div>
      <div>
        <p class="tz-read__label">
          Excedente colocable <b class="is-accent">{{ state.excedenteDelta }}</b>
        </p>
        <p class="tz-read__figure is-accent">{{ state.excedente }}</p>
        <p class="tz-read__hint">{{ state.excedenteHint }}</p>
      </div>
    </section>

    <div class="tz-split">
      <section class="tz-card tz-chart">
        <header class="tz-card__bar">
          <div>
            <h2>Excedente colocable · últimos 12 meses</h2>
            <p>Con previsión a tres meses · umbral de decisión en 100k €</p>
          </div>
        </header>
        <svg
          viewBox="0 0 700 220"
          preserveAspectRatio="none"
          role="img"
          aria-label="Excedente colocable de los últimos 12 meses frente al umbral de 100k €, con previsión a tres meses."
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
          <!-- El umbral es una referencia, no una medida: va en gris para que
               el color quede reservado al trazo del excedente. -->
          <line
            x1="10"
            y1="150"
            x2="690"
            y2="150"
            stroke="var(--text-3)"
            stroke-dasharray="4 4"
            vector-effect="non-scaling-stroke"
          />
          <polyline
            :points="state.chartHistory"
            fill="none"
            :stroke="state.chartColor"
            stroke-width="2.5"
            stroke-linecap="round"
            stroke-linejoin="round"
            vector-effect="non-scaling-stroke"
          />
          <polyline
            :points="state.chartForecast"
            fill="none"
            :stroke="state.chartColor"
            stroke-width="2.5"
            stroke-linecap="round"
            stroke-dasharray="5 5"
            opacity="0.7"
            vector-effect="non-scaling-stroke"
          />
          <!-- Un trazo de longitud cero con remate redondo es un círculo que
               no se deforma aunque el SVG se estire. -->
          <path
            :d="`M${state.chartLast[0]} ${state.chartLast[1]}h0`"
            stroke="var(--card)"
            stroke-width="14"
            stroke-linecap="round"
            vector-effect="non-scaling-stroke"
          />
          <path
            :d="`M${state.chartLast[0]} ${state.chartLast[1]}h0`"
            :stroke="state.chartColor"
            stroke-width="10"
            stroke-linecap="round"
            vector-effect="non-scaling-stroke"
          />
        </svg>
        <p class="tz-chart__axis" aria-hidden="true">
          <span>oct '25</span><span>abr '26</span><span>hoy</span><span>+3 meses</span>
        </p>
        <ul class="tz-legend">
          <li><i :style="{ color: state.chartColor }"></i>Excedente simulado</li>
          <li>
            <i class="is-dashed" :style="{ color: state.chartColor }"></i>Previsión a 3 meses
            (banda del 80 %)
          </li>
          <li><i class="is-dashed"></i>Umbral de 100k €</li>
        </ul>
      </section>

      <div class="tz-stack">
        <section class="tz-card">
          <header class="tz-card__bar"><h2>Qué explica esta decisión</h2></header>
          <dl class="tz-facts">
            <div v-for="d in state.drivers" :key="d.label">
              <dt>{{ d.label }}</dt>
              <dd :class="{ 'is-flagged': d.flagged }">{{ d.value }}</dd>
            </div>
          </dl>
        </section>

        <section class="tz-card">
          <header class="tz-card__bar"><h2>Modo de operación</h2></header>
          <p class="tz-toggle">
            Colocación automática
            <i :class="{ 'is-on': state.autoOn }" aria-hidden="true"></i>
          </p>
          <p class="tz-note">{{ state.autoHint }}</p>
        </section>
      </div>
    </div>

    <TreasuryLog title="Historial reciente" :entries="state.history" />
  </div>
</template>
