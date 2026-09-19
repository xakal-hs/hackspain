export type CashStatus = 'alerta' | 'oportunidad' | 'vigilancia'

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
  health_band: string | null
  action: 'prestar' | 'financiar' | null
}

export interface CajaResponse {
  companies: CajaCompany[]
  counts: Record<CashStatus, number>
}

export type LeadStatus = 'nuevo' | 'contactado' | 'reunion' | 'cerrado'

export interface EmbatLead {
  id: string
  company_id: string
  company_name: string
  status: LeadStatus
  assigned_to: string
  assignee_name: string
  signal: 'financiar'
  email_draft: string
  created_at: string
}

export interface LeadsResponse {
  leads: EmbatLead[]
}

export interface LeadMutationResponse {
  lead: EmbatLead
  alreadyOpen?: boolean
}
