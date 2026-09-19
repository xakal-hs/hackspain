export type HealthBand = 'sano' | 'vigilar' | 'riesgo'
export type HealthTrend = 'mejora' | 'estable' | 'deterioro'

export interface CompanySummary {
  company_id: string
  group_id: string
  currency: string
  has_erp: boolean
  n_months: number
  last_month: string
  score: number
  band: HealthBand
  delta3_q10: number
  delta3_q50: number
  delta3_q90: number
  trend: HealthTrend
  alert: string | null
  dormant: boolean
  confidence: number
}

export interface PortfolioResponse {
  companies: CompanySummary[]
  source?: 'demo' | 'api'
}
