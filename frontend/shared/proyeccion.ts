import type { ProjectedPoint } from './types/company'

/* Previsión del score a tres meses: la misma media exponencial que lo suaviza, prolongada.
 *
 * El score publicado ya es una EWMA (alpha 0,5, `adjust=False`) de las contribuciones mensuales.
 * Una EWMA sin más no predice nada: al no llegar meses nuevos su nivel se queda quieto, así que
 * prolongarla literalmente dibuja una línea horizontal. Lo que le falta es el segundo término de
 * Holt, la pendiente, y eso es lo que se añade aquí, amortiguado con phi para que su empuje se
 * agote y la previsión tienda a plano en vez de dispararse.
 *
 * El nivel NO se vuelve a suavizar: se ancla en el último score publicado. Suavizar otra vez una
 * serie ya suavizada retrasa el nivel respecto a lo publicado, y entonces la previsión arranca
 * por encima del último mes justo cuando la empresa acaba de caer —el trazo discontinuo saldría
 * hacia arriba después de una bajada—. El último valor publicado ya es el nivel; sólo hay que
 * prolongarlo con su pendiente.
 *
 * No es un modelo entrenado ni una probabilidad: es aritmética sobre la serie ya publicada, y se
 * rotula como previsión en todas partes donde se muestra. */

/** Meses hacia delante. Tres: es el horizonte con el que ya se lee el score (`score_delta_3m`). */
export const HORIZON = 3
/** Pendiente: más lenta que el nivel, para que un mes suelto no gire la línea. */
export const BETA = 0.3
/** Amortiguación: a tres meses acumula 0,8 + 0,64 + 0,512 ≈ 1,95 meses de pendiente, no 3. */
export const PHI = 0.8
/** Menos de cuatro meses seguidos no dan pendiente que merezca prolongarse. */
export const MIN_HISTORY = 4

const SCORE_FLOOR = 0
const SCORE_CEILING = 100

const clamp = (value: number) => Math.min(SCORE_CEILING, Math.max(SCORE_FLOOR, value))
const round1 = (value: number) => Math.round(value * 10) / 10

/** 'YYYY-MM' o 'YYYY-MM-DD' → número de mes absoluto, para detectar huecos de calendario. */
const monthIndex = (month: string) => {
  const [year, index] = month.slice(0, 7).split('-').map(Number)
  return year! * 12 + (index! - 1)
}

export const monthLabel = (index: number) =>
  `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, '0')}`

export interface SeriesPoint {
  month: string
  value: number | null | undefined
}

/** Sólo la racha final de meses consecutivos: un hueco en el calendario rompe el suavizado,
 *  y un mes ausente no es un cero. */
export function trailingRun(points: SeriesPoint[]) {
  const rows = points
    .flatMap(point => (Number.isFinite(point.value) ? [{ at: monthIndex(point.month), value: point.value as number }] : []))
    .sort((a, b) => a.at - b.at)
  let start = rows.length - 1
  while (start > 0 && rows[start]!.at - rows[start - 1]!.at === 1) start--
  return rows.slice(Math.max(0, start))
}

/** Tendencia amortiguada de Holt sobre una serie mensual contigua, anclada en su último valor. */
export function holtDamped(values: number[], horizon = HORIZON): number[] {
  if (values.length < MIN_HISTORY) return []
  const level = values[values.length - 1]!
  let trend = values[1]! - values[0]!
  for (let i = 2; i < values.length; i++) {
    trend = BETA * (values[i]! - values[i - 1]!) + (1 - BETA) * PHI * trend
  }
  const ahead: number[] = []
  let damped = 0
  for (let step = 1; step <= horizon; step++) {
    damped += PHI ** step
    ahead.push(clamp(level + damped * trend))
  }
  return ahead
}

/** Previsión fechada de una serie mensual de score. Vacía si no hay historia suficiente. */
export function projectScore(points: SeriesPoint[], horizon = HORIZON): ProjectedPoint[] {
  const run = trailingRun(points)
  const last = run.at(-1)
  if (!last) return []
  return holtDamped(run.map(row => row.value), horizon)
    .map((value, step) => ({ month: monthLabel(last.at + step + 1), value: round1(value) }))
}
