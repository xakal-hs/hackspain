export type HealthBand = 'sano' | 'vigilar' | 'riesgo'
export type HealthTrend = 'mejora' | 'estable' | 'deterioro'

export interface MonthFlow {
  month: string
  in: number
  out: number
  cash: number
}

export interface CompanySummary {
  company_id: string
  group_id: string
  currency: string
  has_erp: boolean
  n_months: number
  last_month: string
  score: number
  band: HealthBand
  /** Variación observada de la nota en los últimos 3 meses. No es un pronóstico. */
  delta3_q50: number
  /** Intervalo de la variación PREVISTA. Solo llega si hay un modelo de trayectoria detrás. */
  delta3_q10?: number
  delta3_q90?: number
  trend: HealthTrend
  alert: string | null
  dormant: boolean
  confidence: number
  /** Serie real de la nota, un valor por mes. Si falta, se dibuja sobre la plantilla. */
  history?: number[]
  /** Decisión del prestamista. Los vetos mandan sobre la nota, así que no se deduce del score. */
  accion?: 'prestar' | 'vigilar' | 'no_prestar' | 'sin_nota'
  /** La razón que manda, ya redactada por el backend. */
  razon?: string
  vetos?: string[]
  avisos?: string[]
  score_expansion?: number
  cash_end?: number | null
  runway_now?: number | null
  runway_prev?: number | null
  dso_now?: number | null
  dso_prev?: number | null
  overdue_share?: number | null
  margin_3m?: number | null
  debt_service_ratio_3m?: number | null
  debt_outstanding?: number | null
  debt_util?: number | null
  flows?: MonthFlow[]
}

export interface PortfolioResponse {
  companies: CompanySummary[]
  source?: 'demo' | 'api' | 'supabase'
  warning?: string
}
