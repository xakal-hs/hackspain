/**
 * Gráficos del asistente. Salen de lo que devolvieron las herramientas (nunca del texto del modelo),
 * así que cada barra y cada punto es un dato de X-Ray con su mes, no una cifra escrita por el LLM.
 */
import { PILLARS, PILLAR_LABEL } from './pillars.ts'

export type ChartTone = 'live' | 'mint' | 'crimson' | 'amber'
export interface TableColumn {
  key: string
  label: string
  /** Cómo se pinta la celda: número alineado, pastilla de banda, tendencia con flecha. */
  kind?: 'text' | 'num' | 'band' | 'trend' | 'action' | 'pillar' | 'score'
  unit?: string
  signed?: boolean
  /** Ancho relativo en la rejilla de la tabla. */
  grow?: number
}
export interface TableStat { label: string, value: string, tone?: ChartTone }
export interface TableFilter { label: string }

export interface ChartItem { label: string, value: number, tone?: ChartTone, note?: string, /** Texto ya formateado (tarjetas de cifras). */ text?: string }
export interface ChatChart {
  id: string
  kind: 'line' | 'bars' | 'stats' | 'radar' | 'table'
  title: string
  subtitle?: string
  unit?: string
  /** En barras: el cero es el centro y el signo cuenta (suma / resta). */
  signed?: boolean
  /** Fija el rango (p. ej. 0-100 para la nota). */
  domain?: [number, number]
  items: ChartItem[]
  /** Hueco lógico del gráfico (herramienta + tipo). Dos llamadas a la misma herramienta
   *  comparten hueco: se queda la última, porque la anterior ya no es lo que se preguntó. */
  slot?: string
  /** Solo en `table`: cabeceras, filas y la tira de cifras de arriba. */
  columns?: TableColumn[]
  rows?: Record<string, unknown>[]
  stats?: TableStat[]
  /** Con qué criterio se pidió la lista; se enseña para que la tabla no mienta sobre su alcance. */
  filters?: TableFilter[]
}

const num = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v)
const MONTHS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

export function monthLabel(month: string): string {
  const m = /^(\d{4})-(\d{2})/.exec(month)
  return m ? `${MONTHS[Number(m[2]) - 1] ?? m[2]} ${m[1]!.slice(2)}` : month
}

const signed = (v: number, d = 1) => `${v > 0 ? '+' : ''}${v.toLocaleString('es-ES', { maximumFractionDigits: d })}`
const pct = (v: number) => `${Math.round(v * 100)}%`
const actionTone = (a?: string): ChartTone => /^no\b/i.test(a ?? '') ? 'crimson' : /vig/i.test(a ?? '') ? 'amber' : 'mint'

const bandTone = (band?: string): ChartTone => band === 'sano' ? 'mint' : band === 'riesgo' ? 'crimson' : 'amber'

export function chartsFromTool(name: string, out: any, key = name): ChatChart[] {
  if (!out || typeof out !== 'object' || out.error) return []
  const charts: ChatChart[] = []

  if (name === 'ficha_empresa') {
    const stats: ChartItem[] = []
    if (num(out.nota)) stats.push({ label: 'Nota', value: out.nota, text: String(Math.round(out.nota)), tone: bandTone(out.banda), note: out.banda ? `Banda ${out.banda}` : undefined })
    if (num(out.cambio_3_meses)) stats.push({ label: 'Últimos 3 meses', value: out.cambio_3_meses, text: `${signed(out.cambio_3_meses)} pts`, tone: out.cambio_3_meses < 0 ? 'crimson' : 'mint', note: out.tendencia })
    if (out.decision?.accion) stats.push({ label: 'Decisión', value: 0, text: String(out.decision.accion), tone: actionTone(out.decision.accion), note: monthLabel(out.mes ?? '') })
    if (num(out.confianza)) stats.push({ label: 'Confianza', value: out.confianza, text: pct(out.confianza), tone: 'live', note: num(out.cobertura_datos) ? `Cobertura ${pct(out.cobertura_datos)}` : undefined })
    if (stats.length) charts.push({ id: `${key}-resumen`, kind: 'stats', title: out.company_id, subtitle: monthLabel(out.mes ?? ''), items: stats })
    const serie = (out.serie_nota_12_meses ?? []).filter((p: any) => num(p.nota))
    if (serie.length > 1) {
      charts.push({
        id: `${key}-serie`, kind: 'line', title: 'Nota mes a mes', subtitle: `${out.company_id} · últimos ${serie.length} meses`,
        domain: [0, 100], items: serie.map((p: any) => ({ label: monthLabel(p.mes), value: p.nota, tone: bandTone(p.banda) })),
      })
    }
  }

  if (name === 'explicar_mes') {
    if (num(out.cambio_total_puntos)) {
      charts.push({
        id: `${key}-total`, kind: 'stats', title: out.company_id, subtitle: `${monthLabel(out.mes_anterior ?? '')} → ${monthLabel(out.mes ?? '')}`,
        items: [{ label: 'Cambio de nota', value: out.cambio_total_puntos, text: `${signed(out.cambio_total_puntos)} pts`, tone: out.cambio_total_puntos < 0 ? 'crimson' : 'mint' }],
      })
    }
    const a = (out.aportaciones ?? []).filter((c: any) => num(c.puntos))
    if (a.length) {
      charts.push({
        id: `${key}-mes`, kind: 'bars', signed: true, unit: 'pts', title: `Por qué cambió la nota en ${monthLabel(out.mes ?? '')}`,
        subtitle: `Cambio total ${num(out.cambio_total_puntos) ? (out.cambio_total_puntos > 0 ? '+' : '') + out.cambio_total_puntos : '—'} pts frente a ${monthLabel(out.mes_anterior ?? '')}`,
        items: [...a].sort((x: any, y: any) => Math.abs(y.puntos) - Math.abs(x.puntos)).map((c: any) => ({ label: c.senal, value: c.puntos, tone: c.puntos < 0 ? 'crimson' : 'mint' })),
      })
    }
  }

  if (name === 'buscar_cartera') {
    const e = (out.empresas ?? []).filter((c: any) => num(c.nota))
    if (e.length) {
      const riesgo = e.filter((c: any) => c.banda === 'riesgo').length
      const bajan = e.filter((c: any) => num(c.cambio_3_meses) && c.cambio_3_meses < 0).length
      const media = e.reduce((a: number, c: any) => a + c.nota, 0) / e.length
      charts.push({
        id: `${key}-tabla`, kind: 'table', title: 'Empresas de la cartera',
        subtitle: `${e.length} de ${out.total_en_cartera ?? e.length} · ${monthLabel(e[0]?.mes ?? '')}`,
        stats: [
          { label: 'Empresas', value: String(e.length) },
          { label: 'Nota media', value: media.toFixed(1), tone: bandTone(media >= 65 ? 'sano' : media >= 35 ? 'vigilar' : 'riesgo') },
          { label: 'En riesgo', value: `${riesgo} (${Math.round((riesgo / e.length) * 100)}%)`, tone: riesgo ? 'crimson' : 'mint' },
          { label: 'Empeorando', value: `${bajan} (${Math.round((bajan / e.length) * 100)}%)`, tone: bajan ? 'amber' : 'mint' },
        ],
        filters: [
          { label: out.criterio?.banda ? `Banda ${out.criterio.banda}` : 'Todas las bandas' },
          { label: { peor_nota: 'Peor nota primero', mayor_caida: 'Mayor caída primero', mayor_mejora: 'Mayor mejora primero' }[out.criterio?.orden as string] ?? 'Peor nota primero' },
          { label: `Máximo ${out.criterio?.limite ?? e.length}` },
        ],
        columns: [
          { key: 'company_id', label: 'Empresa', kind: 'text', grow: 1.6 },
          { key: 'nota', label: 'Nota', kind: 'score', grow: 1 },
          // las cinco columnas del score: cada una se puede desplegar en sus señales
          ...PILLARS.map(p => ({ key: p, label: PILLAR_LABEL[p], kind: 'pillar' as const, grow: 1 })),
        ],
        rows: e.map((c: any) => ({
          company_id: c.company_id, nota: c.nota, banda: c.banda, tendencia: c.tendencia,
          cambio_3_meses: c.cambio_3_meses, accion: c.accion,
          confianza: num(c.confianza) ? Math.round(c.confianza * 100) : null,
          alerta: c.alerta,
          ...Object.fromEntries(PILLARS.map(p => [p, num(c.pilares?.[p]) ? c.pilares[p] : null])),
        })),
        items: [],
      })
    }
  }

  if (name === 'como_funciona_el_score') {
    const w = Object.entries(out.pesos_por_senal ?? {}).filter(([, v]) => num(v)) as [string, number][]
    if (w.length) {
      const names = out.significado_de_las_senales ?? {}
      charts.push({
        id: `${key}-pesos`, kind: 'bars', unit: '%', title: 'Cuánto pesa cada señal',
        subtitle: 'Peso calibrado en la nota; la caja pesa mucho más que un retraso de cobro',
        items: w.sort((a, b) => b[1] - a[1]).slice(0, 10)
          .map(([k, v]) => ({ label: names[k]?.etiqueta ?? k, value: Math.round(v * 1000) / 10, tone: 'live' as const })),
      })
    }
  }
  // el hueco no lleva el id de llamada: es lo que permite quedarse solo con la última
  return charts.map(c => ({ ...c, slot: `${name}${c.id.slice(key.length)}` }))
}

/** Todos los gráficos de un mensaje del asistente, sin repetir (un id por herramienta y llamada). */
export function chartsFromParts(parts: readonly any[]): ChatChart[] {
  const all = parts.flatMap((p) => {
    if (typeof p?.type !== 'string' || !p.type.startsWith('tool-') || p.state !== 'output-available') return []
    return chartsFromTool(p.type.slice(5), p.output, p.toolCallId)
  })
  // si el agente busca dos veces, la segunda manda: dos tablas casi iguales no se comparan, se confunden
  const last = new Map<string, ChatChart>()
  for (const c of all) last.set(c.slot ?? c.id, c)
  return [...last.values()]
}

export interface ChartSection { id: string, question: string, charts: ChatChart[] }

/** Los gráficos agrupados por la pregunta que los provocó, el más reciente arriba. */
export function chartSections(messages: readonly { id: string, role: string, parts: readonly any[] }[]): ChartSection[] {
  let question = ''
  const out: ChartSection[] = []
  for (const m of messages) {
    if (m.role === 'user') question = m.parts.map(p => (p.type === 'text' ? p.text : '')).join('').trim()
    else {
      const charts = chartsFromParts(m.parts)
      if (charts.length) out.push({ id: m.id, question, charts })
    }
  }
  return out.reverse()
}
