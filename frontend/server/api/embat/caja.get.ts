import type { CashForecast, CompanyHealth } from '../../../shared/types/company'
import type { CajaCompany, CajaResponse, CashStatus } from '../../../shared/types/embat'
import { actionFor, loadPrevision } from '../../utils/prevision'

interface FeaturedRow {
  company_id: string
  display_name: string
  sector: string
  display_order: number
}

interface PanelRow {
  company_id: string
  month: string
  cash_end: number | null
  net_op: number | null
  inflow_op: number | null
  outflow_op: number | null
  runway_m: number | null
  debt_service: number | null
  debt_service_ratio_3m: number | null
}

interface StaticRow {
  company_id: string
  currency: string
  debt_outstanding: number | null
  debt_util: number | null
}

function finite(value: number | null | undefined) {
  return value != null && Number.isFinite(value) ? value : null
}

/** Sentinel cash and runaway months are generator artifacts, not SME cash. */
function cashOf(value: number | null | undefined) {
  const n = finite(value)
  return n == null || Math.abs(n) > 1e8 ? null : n
}

function runwayOf(value: number | null | undefined) {
  const n = finite(value)
  return n == null || n < 0 || n > 36 ? null : n
}

function latestByCompany<T extends { company_id: string; month: string }>(rows: T[]) {
  const map = new Map<string, T>()
  for (const row of rows) {
    const prev = map.get(row.company_id)
    if (!prev || row.month > prev.month) map.set(row.company_id, row)
  }
  return map
}

function statusOf(opts: {
  rotura: boolean
  excedente: boolean
  band: string | null
  runway: number | null
  netOp: number | null
}): { status: CashStatus; why: string } {
  if (opts.rotura) {
    return {
      status: 'alerta',
      why: 'La previsión de caja se pone en negativo. Sin un puente, la cuenta no cubre los pagos.',
    }
  }
  if (opts.runway != null && opts.runway < 1) {
    return {
      status: 'alerta',
      why: 'El dinero de la cuenta no cubre un mes de pagos.',
    }
  }
  if (opts.netOp != null && opts.netOp < 0 && (opts.runway == null || opts.runway < 3)) {
    return {
      status: 'alerta',
      why: 'Sale más de lo que entra y la cuenta no da margen. Es una mala situación de caja.',
    }
  }
  if (opts.excedente && opts.band === 'sano') {
    return {
      status: 'oportunidad',
      why: 'Hay excedente sobre el colchón y la nota está sana. Caja en buena situación: se puede colocar.',
    }
  }
  return {
    status: 'vigilancia',
    why: 'Ni rotura ni excedente claro. Se sigue, no se dispara.',
  }
}

export default defineEventHandler(async (): Promise<CajaResponse> => {
  const read = companyDataReader()
  const featured = await read<FeaturedRow>('featured_companies', {
    select: 'company_id,display_name,sector,display_order',
    order: 'display_order.asc',
    limit: 20,
  })
  if (!featured.length) {
    throw createError({ statusCode: 503, statusMessage: 'No hay empresas curadas en Supabase' })
  }

  const filter = `in.(${featured.map((row) => row.company_id).join(',')})`
  const [panel, health, staticRows, forecasts] = await Promise.all([
    read<PanelRow>('panel_monthly', {
      select: 'company_id,month,cash_end,net_op,inflow_op,outflow_op,runway_m,debt_service,debt_service_ratio_3m',
      company_id: filter,
      order: 'company_id.asc,month.asc',
      limit: 1000,
    }).catch(() => [] as PanelRow[]),
    read<CompanyHealth & { company_id: string }>('company_health_monthly', {
      select: 'company_id,month,health_score,health_band,health_trend,score_delta_3m',
      company_id: filter,
      order: 'company_id.asc,month.asc',
      limit: 1000,
    }).catch(() => [] as Array<CompanyHealth & { company_id: string }>),
    read<StaticRow>('company_static', {
      select: 'company_id,currency,debt_outstanding,debt_util',
      company_id: filter,
      order: 'company_id.asc',
      limit: 20,
    }).catch(() => [] as StaticRow[]),
    loadPrevision(),
  ])

  const ids = new Set(featured.map((row) => row.company_id))
  const latestPanel = latestByCompany(panel.filter((row) => ids.has(row.company_id)))
  const latestHealth = latestByCompany(health.filter((row) => ids.has(row.company_id)))
  const staticById = new Map(staticRows.map((row) => [row.company_id, row]))

  const companies: CajaCompany[] = featured.map((row) => {
    const month = latestPanel.get(row.company_id)
    const note = latestHealth.get(row.company_id)
    const facts = staticById.get(row.company_id)
    const forecast: CashForecast | null = forecasts?.companies[row.company_id]?.forecast ?? null
    const action = actionFor(forecast, note)
    const runway = runwayOf(month?.runway_m)
    const netOp = finite(month?.net_op)
    const { status, why } = statusOf({
      rotura: Boolean(forecast?.rotura),
      excedente: Boolean(forecast?.excedente),
      band: note?.health_band ?? null,
      runway,
      netOp,
    })
    return {
      company_id: row.company_id,
      name: row.display_name,
      sector: row.sector,
      currency: facts?.currency || forecasts?.companies[row.company_id]?.currency || 'EUR',
      month: month?.month ?? null,
      status,
      why,
      operativa: {
        cash_end: cashOf(month?.cash_end),
        net_op: netOp,
        inflow_op: finite(month?.inflow_op),
        outflow_op: finite(month?.outflow_op),
        runway_m: runway,
      },
      financiera: {
        debt_service: finite(month?.debt_service),
        debt_service_ratio_3m: finite(month?.debt_service_ratio_3m),
        debt_outstanding: cashOf(facts?.debt_outstanding),
        debt_util: finite(facts?.debt_util),
      },
      health_band: note?.health_band ?? null,
      action,
    }
  })

  const counts: CajaResponse['counts'] = { alerta: 0, oportunidad: 0, vigilancia: 0 }
  for (const company of companies) counts[company.status] += 1

  return { companies, counts }
})
