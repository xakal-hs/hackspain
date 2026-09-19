import type { CashForecast, Cashflow, CashflowAction, CashflowCategories, CashflowMonth, CompanyHealth } from '../../../shared/types/company'

interface Prevision {
  snapshot: string
  companies: Record<string, { currency: string; categories: CashflowCategories; forecast: CashForecast | null }>
}

// server/assets/prevision.json lo genera scripts/build_prevision.py: se lee como asset de Nitro
// para que el typecheck no tenga que inferir un JSON de 2,6 MB.
let prevision: Promise<Prevision | null> | undefined
const loadPrevision = () => (prevision ??= useStorage('assets:server').getItem<Prevision>('prevision.json'))

/* Baremo de la acción bajo la tesorería final. Si va a romper caja, manda el aviso de financiación
 * sea cual sea el score. Prestar la caja se ofrece solo con excedente sobre tres meses de gasto y un
 * score de salud en la banda «sano» (≥ 65) de Supabase. Todo lo demás: nada. */
function actionFor(forecast: CashForecast | null, health: CompanyHealth | undefined): CashflowAction {
  if (forecast?.rotura) return 'financiar'
  if (forecast?.excedente && health?.health_band === 'sano') return 'prestar'
  return null
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
