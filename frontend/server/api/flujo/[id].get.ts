import type { CashForecast, Cashflow, CashflowCategories, CashflowMonth } from '../../../shared/types/company'

interface Prevision {
  snapshot: string
  companies: Record<string, { currency: string; categories: CashflowCategories; forecast: CashForecast | null }>
}

// server/assets/prevision.json lo genera scripts/build_prevision.py: se lee como asset de Nitro
// para que el typecheck no tenga que inferir un JSON de 2,6 MB.
let prevision: Promise<Prevision | null> | undefined
const loadPrevision = () => (prevision ??= useStorage('assets:server').getItem<Prevision>('prevision.json'))

export default defineEventHandler(async (event): Promise<Cashflow> => {
  const id = getRouterParam(event, 'id') || ''
  if (!/^COMP_\d{4}$/.test(id)) throw createError({ statusCode: 400, statusMessage: 'Empresa inválida' })
  const [panel, forecasts] = await Promise.all([
    companyDataReader()<CashflowMonth>('panel_monthly', {
      company_id: `eq.${id}`,
      select: 'month,cash_end,net_bank,inflow_op,outflow_op,debt_service,transfer_net,out_salary,out_social_security,out_tax,out_fin_cost',
      order: 'month.asc',
      limit: 500,
    }),
    loadPrevision(),
  ])
  const entry = forecasts?.companies[id]
  return {
    panel,
    categories: entry?.categories ?? {},
    currency: entry?.currency ?? null,
    forecast: entry?.forecast ?? null,
    snapshot: forecasts?.snapshot ?? '',
  }
})
