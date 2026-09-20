export type CashStatus = 'alerta' | 'oportunidad' | 'vigilancia'

/** Punto de nota mensual para el gráfico de Caja. */
export interface ScorePoint {
  month: string
  score: number
}

export interface CajaCompany {
  company_id: string
  name: string
  sector: string
  currency: string
  month: string | null
  status: CashStatus
  why: string
  operativa: {
    cash_end: number | null
    net_op: number | null
    inflow_op: number | null
    outflow_op: number | null
    runway_m: number | null
  }
  financiera: {
    debt_service: number | null
    debt_service_ratio_3m: number | null
    debt_outstanding: number | null
    debt_util: number | null
  }
  health_score: number | null
  health_band: string | null
  health_trend: string | null
  score_delta_3m: number | null
  /** Nota mes a mes para filtrar el gráfico por sector o comparar dos empresas. */
  score_series: ScorePoint[]
  action: 'prestar' | 'financiar' | null
  /** low − monthly_spend: negativo = € que faltan, positivo = € colocables. Null sin previsión. */
  impacto: number | null
  /** Días entre la foto de la previsión y el punto más bajo de caja. */
  urgencia_dias: number | null
  sugerencia: 'financiar' | 'colocar' | 'seguir'
}

export interface CajaResponse {
  companies: CajaCompany[]
  counts: Record<CashStatus, number>
  /** Nota de la cartera mes a mes: media y mediana de las empresas que tienen nota ese mes. */
  score_history: { month: string; mean: number; median: number; n: number }[]
}

export type LeadStatus = 'nuevo' | 'contactado' | 'reunion' | 'cerrado'

export interface EmbatLead {
  id: string
  company_id: string
  company_name: string
  status: LeadStatus
  assigned_to: string
  assignee_name: string
  assignee_title: string
  signal: 'financiar'
  /** Por qué escribe la empresa, tal como se lo contamos al comercial. */
  reason: string
  /** El puente que pide, ya formateado, cuando la previsión tiene la rotura. */
  reason_amount: string | null
  /** El importe y la fecha del agujero, si la previsión los tiene. */
  reason_detail: string | null
  email_draft: string
  created_at: string
}

export type EmployeeTeam = 'account_management' | 'customer_success'

export interface EmbatEmployee {
  id: string
  name: string
  job_title: string
  team: EmployeeTeam
  standardized_role: string
}

export interface EmployeesResponse {
  employees: EmbatEmployee[]
  counts: Record<EmployeeTeam, number>
}

export interface LeadsResponse {
  leads: EmbatLead[]
  /** De dónde sale el pipeline: Supabase o el fichero de respaldo del demo. */
  source: 'supabase' | 'local'
}

export interface LeadMutationResponse {
  lead: EmbatLead
  alreadyOpen?: boolean
}
