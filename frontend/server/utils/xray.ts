/**
 * Lectura del contrato X-Ray publicado en Supabase.
 *
 * Todo lo que sirve este servidor son resultados ya calculados: la nota la produce
 * `research/src/export_health_publication.py` y la decisión `backend/decision.py`, ambas
 * publicadas por `scripts/`. Nitro no puntúa ni decide, solo consulta y traduce.
 */
import type { H3Event } from 'h3'
import type { HealthBand, HealthTrend, Veto } from '~/types/portfolio'

/** La banda es un hecho publicado; la tendencia viaja en inglés y se enseña en español. */
const TRENDS: Record<string, HealthTrend> = {
  improving: 'mejora',
  stable: 'estable',
  deteriorating: 'deterioro',
}

export const PILLARS = ['liquidez', 'rentabilidad', 'solvencia', 'disciplina', 'estabilidad'] as const

/** Caída de 3 meses que dispara aviso, y confianza por debajo de la cual la nota es provisional. */
const ALERT_DROP = 10
const LOW_CONFIDENCE = 0.4

export function trendOf(trend: string | null | undefined): HealthTrend {
  return TRENDS[String(trend)] ?? 'estable'
}

export function numberOrNull(value: unknown): number | null {
  const n = Number(value)
  return value == null || !Number.isFinite(n) ? null : n
}

export function round(value: unknown, digits = 1): number | null {
  const n = numberOrNull(value)
  return n == null ? null : Number(n.toFixed(digits))
}

/** Mes publicado (`2026-08-01` o `2026-08`) en el `AAAA-MM` que enseña la interfaz. */
export function monthLabel(month: string | null | undefined): string {
  return String(month ?? '').slice(0, 7)
}

/** Número en formato es-ES: el producto se lee en español, con coma decimal. */
export function es(value: number, digits = 1, sign = false): string {
  const text = value.toFixed(digits)
  return (sign && value >= 0 ? `+${text}` : text).replace('.', ',')
}

/** Lo que hay que mirar hoy en esta empresa. Mismo baremo que servía el backend. */
export function alertOf(row: { band: string; delta3: number | null; confidence: number | null }): string | null {
  if (row.delta3 != null && row.delta3 <= -ALERT_DROP)
    return `Cae ${es(Math.abs(row.delta3), 0)} puntos en 3 meses`
  if (row.band === 'riesgo') return 'En banda de riesgo'
  if (row.confidence != null && row.confidence < LOW_CONFIDENCE)
    return 'Datos insuficientes: nota provisional'
  return null
}

export function bandOf(band: string): HealthBand {
  return band === 'sano' || band === 'riesgo' ? band : 'vigilar'
}

export function pillarsOf(row: Record<string, unknown>): Record<string, number | null> {
  return Object.fromEntries(PILLARS.map(p => [p, round(row[`${p}_score`])]))
}

/** Identificador de empresa. Se valida antes de construir cualquier filtro. */
export function companyIdOf(event: H3Event): string {
  const id = getRouterParam(event, 'id') || ''
  if (!/^COMP_\d{4}$/.test(id)) throw createError({ statusCode: 400, statusMessage: 'Empresa inválida' })
  return id
}

export interface ScoreCatalog {
  score_version: string
  target: string
  alpha_ewma: number
  weights: Record<string, number>
  scale: { a: number, b: number }
  bands: { desde: number, hasta: number, banda: string }[]
  dormant_cap: number
  features: Record<string, { label: string, pilar: string, formula: string, sentido: string }>
  pillars: string[]
  anclas: string[]
  probabilities: Record<string, { a: number, b: number, tasa_base: number }>
  vetos: Veto[]
  acciones: Record<string, string>
}

/* El catálogo es una fila que no cambia entre despliegues: se lee una vez por instancia
 * de la función, no una vez por petición. */
let catalogCache: Promise<ScoreCatalog> | undefined

export function scoreCatalog(): Promise<ScoreCatalog> {
  return (catalogCache ??= (async () => {
    const read = companyDataReader()
    const rows = await read<{ payload: ScoreCatalog }>('score_catalog', {
      select: 'payload', order: 'published_at.desc', limit: 1,
    })
    if (!rows.length)
      throw createError({ statusCode: 503, statusMessage: 'Falta el catálogo del score en Supabase' })
    return rows[0]!.payload
  })().catch((error) => {
    catalogCache = undefined // un fallo de red no debe dejar la instancia sin catálogo para siempre
    throw error
  }))
}
