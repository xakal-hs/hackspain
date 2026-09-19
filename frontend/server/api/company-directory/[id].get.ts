import type { CompanyDetail, CompanyDriver, CompanyHealth, CompanyMonth } from '../../../shared/types/company'

export default defineEventHandler(async (event): Promise<CompanyDetail> => {
  const id = getRouterParam(event, 'id') || ''
  if (!/^COMP_\d{4}$/.test(id)) throw createError({ statusCode: 400, statusMessage: 'Empresa inválida' })
  const read = companyDataReader()
  const filter = { company_id: `eq.${id}` }
  const warnings: string[] = []
  async function optional<T>(table: string, select: string, order: string) {
    try { return await read<T>(table, { ...filter, select, order, limit: 500 }) }
    catch { warnings.push(`No se pudo cargar ${table}.`); return [] }
  }
  const [panel, health, products] = await Promise.all([
    optional<CompanyMonth>('panel_monthly', 'month,cash_end,runway_m,dso,inflow_op,outflow_op,saldo_inconsistente', 'month.asc'),
    optional<CompanyHealth>('company_health_monthly', 'month,health_score,health_band,health_trend,score_delta_3m', 'month.asc'),
    optional<{ currency: string | null }>('banking_products', 'currency', 'product_id.asc'),
  ])
  let drivers: CompanyDriver[] = []
  const latestHealth = health.at(-1)
  if (latestHealth) {
    try {
      drivers = await read<CompanyDriver>('company_health_driver_monthly', {
        ...filter, month: `eq.${latestHealth.month}`, select: 'label,display_value,contribution', order: 'feature.asc', limit: 100,
      })
    } catch { warnings.push('No se pudieron cargar las explicaciones del score.') }
  }
  return { panel, health, drivers, currencies: [...new Set(products.flatMap(row => row.currency ? [row.currency] : []))].sort(), warnings }
})
