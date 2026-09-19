export interface CompanyIdentity {
  company_id: string
  display_name?: string | null
  group_id: string | null
  country: string | null
  currency: string | null
  erp: string | null
  top_sector: string | null
}

export type CompanyDirectorySource = 'companies' | 'featured_companies'
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
  feature?: string
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

/** Un mes de `panel_monthly`: se cumple net_bank = inflow_op − outflow_op − debt_service + transfer_net + inversión. */
export interface CashflowMonth {
  month: string
  cash_end: number | null
  net_bank: number | null
  inflow_op: number | null
  outflow_op: number | null
  debt_service: number | null
  transfer_net: number | null
  out_salary: number | null
  out_social_security: number | null
  out_tax: number | null
  out_fin_cost: number | null
}
/** Mes previsto por scripts/build_prevision.py: cobros en positivo, pagos en negativo. */
export interface ForecastMonth {
  month: string
  cobros: number
  proveedores: number
  nominas: number
  seguridad_social: number
  deuda: number
}
export interface CashBreak {
  from: string
  to: string | null
  low: number
  low_date: string
  paid_before: number
  n_paid_before: number
  rescue: { date: string; amount: number; counterparty: string | null; total_day: number } | null
}
export interface CashSurplus {
  amount: number
  cushion: number
  monthly_spend: number
}
export interface CashForecast {
  cash: number
  months: ForecastMonth[]
  rotura: CashBreak | null
  excedente: CashSurplus | null
}
/** Mes → categoría bancaria → importe neto; cada mes suma el net_bank de panel_monthly. */
export type CashflowCategories = Record<string, Record<string, number>>
/** Qué sale bajo la tesorería final: prestar la caja, pedir financiación o nada. */
export type CashflowAction = 'prestar' | 'financiar' | null
export interface Cashflow {
  action: CashflowAction
  panel: CashflowMonth[]
  categories: CashflowCategories
  currency: string | null
  forecast: CashForecast | null
  snapshot: string
}

/** Un cliente del ERP con su comportamiento de pago y la decisión de cobertura. */
export interface ClientRow {
  cliente: string
  ventas_12m: number
  expuesto: number
  vencido: number
  vencido_90: number
  retraso_medio: number | null
  pct_tarde: number | null
  n_facturas: number
  n_pagadas: number
  meses_relacion: number
  pico: number
  limite: number
  prima: number
  estado: 'preautorizado' | 'estudio' | 'denegado'
  /** Si el ERP trae todo lo que hace falta para cotizar en el momento. */
  expediente: 'completo' | 'incompleto'
  motivo: string
}
export interface SuretyLine {
  linea: number
  afianzado: number
  productos: number
}
export interface ClientBook {
  ventas_12m: number
  clientes: ClientRow[]
  caucion?: SuretyLine
}
export interface ClientBookResponse {
  snapshot: string
  cover: number
  premiumRate: number
  ventas12m: number
  clientes: ClientRow[]
  caucion: SuretyLine | null
  excedente: number | null
}
