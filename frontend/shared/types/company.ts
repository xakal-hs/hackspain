export interface CompanyIdentity {
  company_id: string
  group_id: string | null
  country: string | null
  currency: string | null
  erp: string | null
  top_sector: string | null
}
export interface CompanyMonth {
  month: string
  cash_end: number | null
  runway_m: number | null
  dso: number | null
  inflow_op: number | null
  outflow_op: number | null
  saldo_inconsistente: boolean | null
}
export interface CompanyHealth {
  month: string
  health_score: number
  health_band: string
  health_trend: string
  score_delta_3m: number | null
}
export interface CompanyDriver {
  label: string
  display_value: string
  contribution: number
}
export interface SectorHealth {
  month: string
  top_sector: string
  n: number
  score_mean: number | null
  score_median: number | null
}
export interface CompanyDetail {
  sectorHealth: SectorHealth[]
  drivers: CompanyDriver[]
  panel: CompanyMonth[]
  health: CompanyHealth[]
  currencies: string[]
  warnings: string[]
}
