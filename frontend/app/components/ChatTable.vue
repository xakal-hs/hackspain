<script setup lang="ts">
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronRight, Filter, ListRestart, Minus, X } from '@lucide/vue'
import type { ChartTone, ChatChart, TableColumn } from '~/utils/chatCharts'
import { PILLAR_ASKS, PILLAR_FEATURES, PILLAR_LABEL, type Pillar } from '~/utils/pillars'

/* `flush` = a sangre: sin tarjeta, llenando el panel. Es como se lee una tabla larga. */
const props = defineProps<{ chart: ChatChart, flush?: boolean, /** Sin cabecera ni recuento de columnas: el título lo pone quien la usa, fuera del marco. */ plain?: boolean }>()

const TONE: Record<ChartTone, string> = { live: 'var(--live-ink)', mint: 'var(--mint-ink)', crimson: 'var(--crimson-ink)', amber: 'var(--amber-ink)' }
const BAND: Record<string, ChartTone> = { sano: 'mint', vigilar: 'amber', riesgo: 'crimson' }
/* El cuadrito de la nota va con el verde vivo de la tabla de referencia, no con el menta del tema. */
const SQUARE: Record<string, string> = { sano: 'rgb(10, 180, 10)', vigilar: 'var(--amber)', riesgo: 'var(--crimson)' }

const cols = computed(() => props.chart.columns ?? [])
const grid = computed(() => `44px ${cols.value.map(c => `minmax(0, ${c.grow ?? 1}fr)`).join(' ')}`)

/* Ordenar es parte del análisis: sin esto la tabla es una lista y no se puede comparar. */
const sortKey = ref<string>('')
const asc = ref(false)
function sortBy(c: TableColumn) {
  if (sortKey.value === c.key) asc.value = !asc.value
  else { sortKey.value = c.key; asc.value = c.kind === 'text' }
}
const rows = computed(() => {
  const list = [...(props.chart.rows ?? [])]
  if (!sortKey.value) return list
  const k = sortKey.value
  return list.sort((a, b) => {
    const x = a[k], y = b[k]
    if (x == null) return 1
    if (y == null) return -1
    const cmp = typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y), 'es')
    return asc.value ? cmp : -cmp
  })
})

const fmt = (v: unknown, c: TableColumn, r?: Record<string, unknown>) => {
  if (v == null) return '—'
  if (c.kind !== 'num') return String(v)
  const n = Number(v)
  return (c.signed && n > 0 ? '+' : '') + n.toLocaleString('es-ES', { maximumFractionDigits: 1 }) + String(r?.[`${c.key}_unit`] ?? c.unit ?? '')
}
const numTone = (v: unknown, c: TableColumn): string =>
  c.signed && typeof v === 'number' ? TONE[v < 0 ? 'crimson' : 'mint'] : 'inherit'
const TREND = { mejora: ArrowUp, deterioro: ArrowDown, estable: Minus } as const
const trendOf = (v: unknown) => TREND[String(v) as keyof typeof TREND] ?? Minus
/* Descomponer un pilar: qué señales lo forman. El valor del pilar viene del backend;
   las señales son el catálogo del modelo, así que no se inventa ninguna cifra. */
const open = ref('')
watch(() => props.chart.id, () => { open.value = ''; sortKey.value = '' })
function onEsc(e: KeyboardEvent) { if (e.key === 'Escape' && open.value) { open.value = ''; e.stopPropagation() } }
onMounted(() => window.addEventListener('keydown', onEsc))
onBeforeUnmount(() => window.removeEventListener('keydown', onEsc))
function toggle(rowKey: string, c: TableColumn) {
  if (c.kind !== 'pillar' && c.kind !== 'score') return
  open.value = open.value === `${rowKey}|${c.key}` ? '' : `${rowKey}|${c.key}`
}
const openRow = computed(() => open.value.split('|')[0])
const openCol = computed(() => open.value.split('|')[1])
const openPillar = computed(() => (openCol.value && openCol.value !== 'nota' ? openCol.value : undefined) as Pillar | undefined)
const openScore = computed(() => openCol.value === 'nota'
  ? rows.value.find(r => String(r.company_id) === openRow.value)
  : undefined)

/* Todo lo que enseña el panel sale de la fila: ni una cifra nueva. */
const detail = computed(() => {
  const row = rows.value.find(r => String(r.company_id) === openRow.value)
  if (!row) return null
  const crumb = `${row.company_id} · ${props.chart.subtitle ?? ''}`.trim()
  if (openScore.value) {
    const d3 = row.cambio_3_meses
    return {
      title: 'Nota', crumb, value: typeof row.nota === 'number' ? Math.round(Number(row.nota)) : '—',
      facts: [
        { label: 'Banda', value: String(row.banda ?? '—'), tone: BAND[String(row.banda)] },
        { label: 'Tendencia', value: String(row.tendencia ?? '—'), tone: TREND_TONE[String(row.tendencia)] },
        { label: 'Últimos 3 meses', value: typeof d3 === 'number' ? `${d3 > 0 ? '+' : ''}${d3} pts` : '—', tone: typeof d3 === 'number' ? (d3 < 0 ? 'crimson' : 'mint') as ChartTone : undefined },
        { label: 'Decisión del prestamista', value: String(row.accion ?? '—'), tone: actionTone(row.accion) },
        { label: 'Confianza', value: row.confianza == null ? '—' : `${row.confianza}%` },
        ...(row.alerta ? [{ label: 'Alerta', value: String(row.alerta), tone: 'crimson' as ChartTone }] : []),
      ],
    }
  }
  const p = openPillar.value
  if (!p || !PILLAR_FEATURES[p]) return null
  return {
    title: PILLAR_LABEL[p], crumb, ask: PILLAR_ASKS[p],
    value: typeof row[p] === 'number' ? Number(row[p]) : 'sin dato',
    signals: PILLAR_FEATURES[p],
  }
})
const pillarTone = (v: unknown): ChartTone =>
  typeof v !== 'number' ? 'live' : v >= 65 ? 'mint' : v >= 35 ? 'amber' : 'crimson'

const TREND_TONE: Record<string, ChartTone> = { mejora: 'mint', deterioro: 'crimson' }

const actionTone = (v: unknown): ChartTone =>
  /^no/i.test(String(v)) ? 'crimson' : /vig/i.test(String(v)) ? 'amber' : 'mint'
</script>

<template>
  <figure class="ct" :class="{ 'is-flush': flush }">
    <figcaption v-if="!plain" class="ct__head">
      <div class="ct__weave" aria-hidden="true" />
      <div class="ct__title">
        <strong>{{ chart.title }}</strong>
        <i v-if="chart.subtitle" class="ct__sep" aria-hidden="true" />
        <span v-if="chart.subtitle">{{ chart.subtitle }}</span>
      </div>
      <div v-if="chart.filters?.length" class="ct__filters">
        <b>Criterio:</b>
        <span v-for="f in chart.filters" :key="f.label"><Filter :size="10" aria-hidden="true" />{{ f.label }}</span>
      </div>

      <div class="ct__bar">
        <dl v-if="chart.stats?.length" class="ct__stats">
          <div v-for="st in chart.stats" :key="st.label">
            <dt>{{ st.label }}</dt>
            <dd :style="{ color: st.tone ? TONE[st.tone] : undefined }">{{ st.value }}</dd>
          </div>
        </dl>
        <div class="ct__tools">
          <span>{{ cols.length }} cols</span>
          <i class="ct__sep" aria-hidden="true" />
          <button type="button" :disabled="!sortKey" title="Quitar la ordenación" aria-label="Quitar la ordenación" @click="sortKey = ''">
            <ListRestart :size="15" aria-hidden="true" />
            <b v-if="sortKey">1</b>
          </button>
        </div>
      </div>
    </figcaption>

    <div class="ct__body">
    <div class="ct__scroll">
      <table :style="{ '--cols': grid }">
        <thead>
          <tr>
            <th class="ct__idx" aria-label="Fila" />
            <th v-for="c in cols" :key="c.key" :class="{ 'is-num': c.kind === 'num', 'is-on': sortKey === c.key }">
              <button type="button" @click="sortBy(c)">
                {{ c.label }}
                <ArrowUpDown v-if="sortKey !== c.key" :size="11" aria-hidden="true" />
                <ArrowUp v-else-if="asc" :size="11" aria-hidden="true" />
                <ArrowDown v-else :size="11" aria-hidden="true" />
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(r, i) in rows" :key="i">
          <tr :title="r.alerta ? String(r.alerta) : undefined">
            <td class="ct__idx">{{ i + 1 }}</td>
            <td
              v-for="c in cols" :key="c.key"
              :class="{ 'is-num': c.kind === 'num', 'is-pillar': c.kind === 'pillar', 'is-open': open === `${r.company_id}|${c.key}` }"
              @click="toggle(String(r.company_id), c)"
            >
              <button v-if="c.kind === 'score'" type="button" class="ct__score" :aria-expanded="open === `${r.company_id}|${c.key}`">
                <i :style="{ background: SQUARE[String(r.banda)] ?? 'var(--live)' }" aria-hidden="true" />
                <em>{{ typeof r[c.key] === 'number' ? Math.round(Number(r[c.key])) : '—' }}</em>
                <ChevronRight :size="12" :stroke-width="2.5" aria-hidden="true" />
              </button>
              <button v-else-if="c.kind === 'pillar'" type="button" class="ct__cell" :aria-expanded="open === `${r.company_id}|${c.key}`">
                <template v-if="typeof r[c.key] === 'number'">
                  <i class="ct__meter"><b :style="{ width: `${r[c.key]}%`, background: TONE[pillarTone(r[c.key])] }" /></i>
                  <em>{{ Math.round(Number(r[c.key])) }}</em>
                </template>
                <em v-else class="is-void">sin dato</em>
              </button>
              <span v-else-if="c.kind === 'band'" class="ct__pill" :class="`is-${BAND[String(r[c.key])] ?? 'live'}`">{{ r[c.key] ?? '—' }}</span>
              <span v-else-if="c.kind === 'trend'" class="ct__trend" :class="`is-${r[c.key]}`">
                <component :is="trendOf(r[c.key])" :size="12" aria-hidden="true" />{{ r[c.key] ?? '—' }}
              </span>
              <span v-else-if="c.kind === 'action'" class="ct__pill is-ghost" :style="{ color: TONE[actionTone(r[c.key])] }">{{ r[c.key] ?? '—' }}</span>
              <span v-else-if="c.kind === 'chip'" class="ct__pill" :class="`is-${r[`${c.key}_tone`] ?? 'neutral'}`">{{ r[c.key] ?? '—' }}</span>
              <span v-else-if="c.sub" class="ct__two"><b>{{ r[c.key] ?? '—' }}</b><small>{{ r[c.sub] ?? '' }}</small></span>
              <span v-else :style="{ color: numTone(r[c.key], c) }">{{ fmt(r[c.key], c, r) }}</span>
            </td>
          </tr>
          </template>
        </tbody>
      </table>
    </div>

    <aside v-if="detail" class="ct__side" aria-label="Detalle de la celda">
      <header>
        <div>
          <strong>{{ detail.title }}</strong>
          <p><ChevronRight :size="12" aria-hidden="true" />{{ detail.crumb }}</p>
        </div>
        <button type="button" aria-label="Cerrar (Esc)" title="Cerrar (Esc)" @click="open = ''"><X :size="15" aria-hidden="true" /></button>
      </header>

      <div class="ct__side-body">
        <p v-if="detail.ask" class="ct__ask">{{ detail.ask }}</p>

        <div v-if="detail.value != null" class="ct__field">
          <dt>{{ detail.title }}</dt>
          <dd>
            <template v-if="typeof detail.value === 'number'">
              <i class="ct__meter"><b :style="{ width: `${detail.value}%`, background: TONE[pillarTone(detail.value)] }" /></i>
              {{ Math.round(detail.value) }}<small>/ 100</small>
            </template>
            <template v-else>{{ detail.value }}</template>
          </dd>
        </div>

        <template v-if="detail.facts">
          <div v-for="f in detail.facts" :key="f.label" class="ct__field">
            <dt>{{ f.label }}</dt>
            <dd :style="{ color: f.tone ? TONE[f.tone] : undefined }">{{ f.value }}</dd>
          </div>
        </template>

        <template v-if="detail.signals">
          <div class="ct__field">
            <dt>{{ detail.signals.length }} señales del modelo</dt>
            <dd class="ct__signals"><span v-for="g in detail.signals" :key="g.key">{{ g.label }}</span></dd>
          </div>
          <small class="ct__note">El pilar es la media ponderada de estas señales. Los pesos salen de la calibración, no son iguales entre sí.</small>
        </template>
      </div>
    </aside>
    </div>

    <footer>{{ rows.length }} {{ rows.length === 1 ? 'empresa' : 'empresas' }}<template v-if="!plain"> · {{ cols.length }} columnas</template></footer>
  </figure>
</template>

<style scoped>
.ct { font-family: Arial, Helvetica, sans-serif; margin: 0; background: var(--panel); border: 1px solid var(--line); border-radius: 14px; overflow: hidden; box-shadow: var(--sheen); }

.ct__stats { display: flex; flex-wrap: wrap; margin: 0; padding: 0 0 10px; min-width: 0; }
.ct__stats > div { padding-right: 20px; margin-right: 20px; border-right: 1px dashed var(--line-strong); }
.ct__stats > div:last-child { border-right: 0; margin-right: 0; padding-right: 0; }
.ct__stats dt { font-size: 0.68rem; letter-spacing: 0.04em; text-transform: uppercase; color: var(--text-muted); margin-bottom: 2px; }
.ct__stats dd { margin: 0; font: 600 1.05rem var(--font-num); }

.ct__scroll { max-height: 340px; overflow: auto; border-top: 1px solid var(--line); }
.ct.is-flush .ct__scroll { border-top: 1px solid var(--line-strong); }
.ct table { width: 100%; border-collapse: collapse; }
.ct thead tr, .ct tbody tr { display: grid; grid-template-columns: var(--cols); align-items: center; }
.ct thead { position: sticky; top: 0; z-index: 1; background: var(--panel-sunken); }
.ct th { padding: 0; text-align: left; border-bottom: 1px solid var(--line); }
.ct th button {
  display: inline-flex; align-items: center; gap: 4px; width: 100%; padding: 9px 12px; border: 0; background: none;
  color: var(--text-muted); font: 500 0.7rem Arial, Helvetica, sans-serif; letter-spacing: 0.03em; text-transform: uppercase;
  cursor: pointer; text-align: left;
}
.ct th.is-num button { justify-content: flex-end; }
.ct th button:hover { color: var(--text); }
.ct th.is-on button { color: var(--live-ink); }
.ct th svg { opacity: 0.55; flex: none; }
.ct td { padding: 8px 12px; font-size: 0.79rem; border-bottom: 1px solid var(--line); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ct td.is-num { text-align: right; font-family: var(--font-num); font-variant-numeric: tabular-nums; }
.ct tbody tr:hover { background: var(--neutral-wash); }
.ct tbody tr:last-child td { border-bottom: 0; }

.ct__pill { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 0.72rem; text-transform: capitalize; }
.ct__pill.is-mint { color: var(--mint-ink); background: var(--mint-wash); }
.ct__pill.is-amber { color: var(--amber-ink); background: var(--amber-wash); }
.ct__pill.is-crimson { color: var(--crimson-ink); background: var(--crimson-wash); }
.ct__pill.is-live { color: var(--live-ink); background: var(--live-wash); }
.ct__pill.is-neutral { color: var(--text-muted); background: var(--neutral-wash); }
.ct__two { display: flex; flex-direction: column; min-width: 0; line-height: 1.25; }
.ct__two b { font-weight: 600; overflow: hidden; text-overflow: ellipsis; }
.ct__two small { color: var(--text-muted); font-size: 0.7rem; overflow: hidden; text-overflow: ellipsis; }
.ct__pill.is-ghost { background: none; padding: 0; }
.ct__trend { display: inline-flex; align-items: center; gap: 5px; text-transform: capitalize; color: var(--text-muted); }
.ct__trend.is-mejora { color: var(--mint-ink); }
.ct__trend.is-deterioro { color: var(--crimson-ink); }

.ct footer { padding: 9px 18px; font: 0.72rem var(--font-num); color: var(--text-muted); border-top: 1px solid var(--line); background: var(--panel-sunken); }

/* a sangre: la tabla es la vista, no una tarjeta dentro de ella */
.ct.is-flush { flex: 1; min-height: 0; display: flex; flex-direction: column; border: 0; border-radius: 0; background: var(--panel); }
.ct.is-flush .ct__head { padding: 18px 24px 0; }
.ct.is-flush .ct__scroll { flex: 1; max-height: none; }
.ct.is-flush footer { border-radius: 0; }
.ct__idx { color: var(--text-dim); font: 0.72rem var(--font-num); text-align: center !important; padding-left: 0 !important; padding-right: 0 !important; }
.ct td { border-right: 1px solid var(--line); }
.ct td:last-child, .ct th:last-child { border-right: 0; }

/* Cabecera al estilo Origami: rejilla de fondo, criterio y la tira de cifras. */
.ct__head { position: relative; flex: none; padding: 16px 20px 0; }
.ct__weave {
  position: absolute; inset: 0; pointer-events: none; opacity: 0.5;
  background-image: linear-gradient(to right, var(--grid-line) 1px, transparent 1px), linear-gradient(var(--grid-line) 1px, transparent 1px);
  background-size: 24px 24px;
  mask-image: linear-gradient(to right, transparent 0%, transparent 20%, black 55%, black 100%);
}
.ct__head > * { position: relative; }
.ct__title { display: flex; align-items: center; gap: 10px; min-width: 0; }
.ct__title strong { display: block; font-size: 1.05rem; font-weight: 700; letter-spacing: -0.02em; }
.ct__title span { font-size: 0.74rem; color: var(--text-muted); white-space: nowrap; }
.ct__sep { width: 1px; height: 16px; background: var(--line-strong); flex: none; }
.ct__filters { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.ct__filters b { font: 500 0.62rem var(--font-ui); letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-dim); }
.ct__filters span {
  display: inline-flex; align-items: center; gap: 5px; padding: 2px 8px; border-radius: 6px;
  background: var(--neutral-wash); color: var(--text-muted); font-size: 0.7rem;
}
.ct__filters svg { opacity: 0.6; }
.ct__bar { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin-top: 12px; }
.ct__tools { display: flex; align-items: center; gap: 10px; padding: 0 0 10px 16px; border-left: 1px dashed var(--line-strong); flex: none; }
.ct__tools > span { font: 0.72rem var(--font-num); color: var(--text-muted); }
.ct__tools button {
  position: relative; display: grid; place-items: center; width: 28px; height: 28px; border-radius: 6px;
  border: 1px solid var(--line); background: none; color: var(--text-muted); cursor: pointer;
}
.ct__tools button:hover:not(:disabled) { color: var(--text); background: var(--neutral-wash); }
.ct__tools button:disabled { opacity: 0.4; cursor: default; }
.ct__tools b {
  position: absolute; top: -5px; right: -5px; display: grid; place-items: center; min-width: 14px; height: 14px;
  padding: 0 3px; border-radius: 999px; background: var(--live-solid); color: var(--on-live); font: 600 0.58rem var(--font-num);
}

.ct td.is-pillar { padding: 0; cursor: pointer; }
.ct td.is-pillar:hover, .ct td.is-open { background: var(--neutral-wash); }
.ct__cell { display: flex; align-items: center; gap: 8px; width: 100%; padding: 8px 12px; border: 0; background: none; cursor: pointer; }
.ct__meter { flex: 1; min-width: 20px; height: 6px; border-radius: 3px; background: var(--neutral-wash); overflow: hidden; }
.ct__meter b { display: block; height: 100%; border-radius: 3px; }
.ct__cell em { font: 0.76rem var(--font-num); font-style: normal; color: var(--text); font-variant-numeric: tabular-nums; }
.ct__cell em.is-void { color: var(--text-dim); font-size: 0.7rem; }

/* Nota al estilo de la tabla de Origami: recuadro, cuadrito de color, cifra y chevron. */
.ct td.is-score { padding: 6px 12px; cursor: pointer; }
.ct td.is-score:hover, .ct td.is-score.is-open { background: var(--neutral-wash); }
.ct__score {
  display: flex; align-items: center; gap: 6px; width: 100%; padding: 5px 8px; cursor: pointer;
  border: 1px solid var(--line-strong); border-radius: 8px; background: var(--panel-raised);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08); transition: background 0.1s, border-color 0.1s, box-shadow 0.1s, transform 0.1s;
}
.ct td.is-score:hover .ct__score, .ct td.is-score.is-open .ct__score {
  background: var(--panel-sunken); border-color: var(--text-dim); box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}
.ct__score:active { transform: scale(0.97); }
.ct__score i { width: 10px; height: 10px; border-radius: 2px; flex: none; }
.ct__score em {
  flex: 1; text-align: left; font: 600 13px/1 Arial, Helvetica, sans-serif; font-style: normal;
  font-variant-numeric: tabular-nums; color: var(--text);
}
.ct__score svg { color: var(--text-dim); opacity: 0.8; flex: none; transition: color 0.1s; }
.ct td.is-score:hover .ct__score svg { color: var(--text-muted); }

/* Panel lateral: la explicación de la celda, sin sacar al lector de la tabla. */
.ct__body { flex: 1; min-height: 0; display: flex; }
.ct.is-flush .ct__scroll { flex: 1; min-width: 0; }
.ct__side {
  width: 300px; flex: none; display: flex; flex-direction: column; min-height: 0;
  border-left: 1px solid var(--line); border-top: 1px solid var(--line-strong); background: var(--panel-sunken);
  animation: ct-slide 0.22s cubic-bezier(0.22, 1, 0.36, 1) both;
}
@keyframes ct-slide { from { opacity: 0; transform: translateX(14px); } }
.ct__side header { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; padding: 14px 16px; border-bottom: 1px solid var(--line); }
.ct__side header strong { font-size: 0.86rem; font-weight: 600; }
.ct__side header p { display: flex; align-items: center; gap: 4px; margin: 5px 0 0; font-size: 0.7rem; color: var(--text-muted); }
.ct__side header button { display: grid; place-items: center; padding: 4px; border: 0; border-radius: 5px; background: none; color: var(--text-muted); cursor: pointer; }
.ct__side header button:hover { background: var(--neutral-wash); color: var(--text); }
.ct__side-body { flex: 1; min-height: 0; overflow-y: auto; padding: 4px 16px 20px; }
.ct__ask { margin: 12px 0; font-size: 0.8rem; line-height: 1.5; color: var(--text); }
.ct__field { padding: 10px 0; border-bottom: 1px solid var(--line); }
.ct__field:last-of-type { border-bottom: 0; }
.ct__field dt { font-size: 0.64rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-muted); margin-bottom: 5px; }
.ct__field dd { margin: 0; display: flex; align-items: center; gap: 8px; font: 600 0.9rem var(--font-num); text-transform: capitalize; }
.ct__field dd small { font: 0.7rem var(--font-num); color: var(--text-dim); }
.ct__signals { display: flex; flex-wrap: wrap; gap: 5px; text-transform: none; }
.ct__signals span { padding: 3px 9px; border-radius: 999px; background: var(--neutral-wash); color: var(--text-muted); font: 0.72rem Arial, Helvetica, sans-serif; }
.ct__note { display: block; margin-top: 10px; font-size: 0.7rem; line-height: 1.5; color: var(--text-dim); }
@media (max-width: 1100px) { .ct__side { width: 240px; } }
</style>
