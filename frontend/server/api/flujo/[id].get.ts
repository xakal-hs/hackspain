import type { CashForecast, Cashflow, CashflowCategories, CashflowMonth, CompanyHealth } from '../../../shared/types/company'
import { actionFor, loadPrevision } from '../../utils/prevision'

interface Prevision {
  snapshot: string
  companies: Record<string, { currency: string; categories: CashflowCategories; forecast: CashForecast | null }>
}

export default defineEventHandler(async (event): Promise<Cashflow> => {
  const id = getRouterParam(event, 'id') || ''
  if (!/^COMP_\d{4}$/.test(id)) throw createError({ statusCode: 400, statusMessage: 'Empresa inválida' })
  const read = companyDataReader()
  const [panel, health, forecasts] = await Promise.all([
    read<CashflowMonth>('panel_monthly', {
      company_id: `eq.${id}`,
      select: 'month,cash_end,net_bank,inflow_op,outflow_op,debt_service,transfer_net,out_salary,out_social_security,out_tax,out_fin_cost',
      order: 'month.asc',
      limit: 500,
    }),
    read<CompanyHealth>('company_health_monthly', {
      company_id: `eq.${id}`,
      select: 'month,health_score,health_band,health_trend,score_delta_3m',
      order: 'month.desc',
      limit: 1,
    }),
    loadPrevision(),
  ])
  const entry = forecasts?.companies[id]
  return {
    action: actionFor(entry?.forecast ?? null, health[0]),
    panel,
    categories: entry?.categories ?? {},
    currency: entry?.currency ?? null,
    forecast: entry?.forecast ?? null,
    snapshot: forecasts?.snapshot ?? '',
  }
})
