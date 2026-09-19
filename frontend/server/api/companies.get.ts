import type { CompanySummary, MonthFlow } from '~/types/portfolio'

const mockSignals = {
  COMP_0864: { score: 68, delta3: -8.4, trend: 'deterioro' },
  COMP_0412: { score: 81, delta3: 5.7, trend: 'mejora' },
  COMP_1107: { score: 74, delta3: 0.6, trend: 'estable' },
  COMP_0239: { score: 43, delta3: -6.2, trend: 'deterioro' },
  COMP_0721: { score: 62, delta3: 2.3, trend: 'mejora' },
} as const

const featuredIds = Object.keys(mockSignals)

interface CompanyStaticRow {
  company_id: string
  group_id: string
  currency: string
  tiene_erp: boolean
  meses_historia: number
  saldo_inconsistente: boolean
  debt_outstanding: number | null
  debt_util: number | null
}

interface PanelRow {
  company_id: string
  month: string
  inflow_op: number | null
  outflow_op: number | null
  cash_end: number | null
  runway_m: number | null
  dso: number | null
  pct_vencido: number | null
  margin_3m: number | null
  debt_service_ratio_3m: number | null
  n_tx: number
}

const demoCompanies: CompanySummary[] = [
  {
    company_id: 'COMP_0864', group_id: 'GROUP_0198', currency: 'EUR', has_erp: true,
    n_months: 24, last_month: '2026-09', score: 68, band: 'vigilar',
    delta3_q10: -13.2, delta3_q50: -8.4, delta3_q90: -2.1, trend: 'deterioro',
    alert: 'La caja cae durante tres meses consecutivos.', dormant: false, confidence: 0.91,
  },
  {
    company_id: 'COMP_0412', group_id: 'GROUP_0084', currency: 'EUR', has_erp: true,
    n_months: 22, last_month: '2026-09', score: 81, band: 'sano',
    delta3_q10: 1.8, delta3_q50: 5.7, delta3_q90: 9.4, trend: 'mejora',
    alert: null, dormant: false, confidence: 0.88,
  },
  {
    company_id: 'COMP_1107', group_id: 'GROUP_0231', currency: 'GBP', has_erp: false,
    n_months: 24, last_month: '2026-09', score: 74, band: 'sano',
    delta3_q10: -3.1, delta3_q50: 0.6, delta3_q90: 4.2, trend: 'estable',
    alert: null, dormant: false, confidence: 0.73,
  },
  {
    company_id: 'COMP_0239', group_id: 'GROUP_0056', currency: 'EUR', has_erp: true,
    n_months: 18, last_month: '2026-09', score: 43, band: 'riesgo',
    delta3_q10: -12.8, delta3_q50: -6.2, delta3_q90: 1.4, trend: 'deterioro',
    alert: 'Los pagos superan los cobros y la deuda consume la caja.', dormant: false, confidence: 0.86,
  },
  {
    company_id: 'COMP_0721', group_id: 'GROUP_0142', currency: 'USD', has_erp: true,
    n_months: 21, last_month: '2026-09', score: 62, band: 'vigilar',
    delta3_q10: -4.9, delta3_q50: 2.3, delta3_q90: 8.1, trend: 'mejora',
    alert: 'Recuperación temprana tras un bache de tesorería.', dormant: false, confidence: 0.79,
  },
]

function numberOrNull(value: number | null | undefined) {
  return Number.isFinite(value) ? Number(value) : null
}

function alertFor(row: PanelRow) {
  if (row.runway_m != null && row.runway_m < 1)
    return 'El dinero en la cuenta no cubre un mes de pagos.'
  if (row.margin_3m != null && row.margin_3m < 0)
    return 'En los últimos tres meses ha salido más dinero del que ha entrado.'
  // `pct_vencido` no es un porcentaje: es vencido acumulado / facturación de 3 meses,
  // una fracción recortada a [0, 5]. El umbral 10 nunca se alcanzaba (0 filas de 10.054).
  if (row.pct_vencido != null && row.pct_vencido >= 0.25)
    return 'Una parte relevante de las facturas sigue pendiente de cobro.'
  return null
}

function toFlows(rows: PanelRow[]): MonthFlow[] {
  return rows.slice(-8).map((row) => ({
    month: row.month,
    in: Number(row.inflow_op || 0),
    out: Math.abs(Number(row.outflow_op || 0)),
    cash: Number(row.cash_end || 0),
  }))
}

export default defineEventHandler(async () => {
  const config = useRuntimeConfig()

  if (config.xrayApiBase) {
    const apiBase = config.xrayApiBase.replace(/\/$/, '')
    const response = await $fetch<{ companies: CompanySummary[] }>(`${apiBase}/api/companies`)
    return { ...response, source: 'api' as const }
  }

  const supabaseUrl = String(config.public.supabaseUrl || '').replace(/\/$/, '')
  const secretKey = String(config.supabaseSecretKey || '')
  if (!supabaseUrl || !secretKey) {
    return { companies: demoCompanies, source: 'demo' as const }
  }

  const headers = {
    apikey: secretKey,
    Authorization: `Bearer ${secretKey}`,
  }
  const companyFilter = `in.(${featuredIds.join(',')})`

  try {
    const [staticRows, panelRows] = await Promise.all([
      $fetch<CompanyStaticRow[]>(`${supabaseUrl}/rest/v1/company_static`, {
        headers,
        query: { select: '*', company_id: companyFilter, order: 'company_id.asc' },
      }),
      $fetch<PanelRow[]>(`${supabaseUrl}/rest/v1/panel_monthly`, {
        headers,
        query: {
          select: 'company_id,month,inflow_op,outflow_op,cash_end,runway_m,dso,pct_vencido,margin_3m,debt_service_ratio_3m,n_tx',
          company_id: companyFilter,
          order: 'company_id.asc,month.asc',
        },
      }),
    ])

    const companies = staticRows.map((company): CompanySummary => {
      const history = panelRows.filter((row) => row.company_id === company.company_id)
      const latest = history.at(-1)
      const previous = history.at(-4) || history.at(0)
      const mock = mockSignals[company.company_id as keyof typeof mockSignals]

      if (!latest || !mock)
        throw new Error(`Missing portfolio data for ${company.company_id}`)

      return {
        company_id: company.company_id,
        group_id: company.group_id,
        currency: company.currency,
        has_erp: company.tiene_erp,
        n_months: company.meses_historia,
        last_month: latest.month,
        score: mock.score,
        band: mock.score >= 70 ? 'sano' : mock.score >= 55 ? 'vigilar' : 'riesgo',
        delta3_q10: mock.delta3 - 4,
        delta3_q50: mock.delta3,
        delta3_q90: mock.delta3 + 4,
        trend: mock.trend,
        alert: alertFor(latest),
        dormant: latest.n_tx === 0,
        confidence: company.saldo_inconsistente
          ? 0.55
          : Math.min(0.98, company.meses_historia / 24),
        cash_end: numberOrNull(latest.cash_end),
        runway_now: numberOrNull(latest.runway_m),
        runway_prev: numberOrNull(previous?.runway_m),
        dso_now: numberOrNull(latest.dso),
        dso_prev: numberOrNull(previous?.dso),
        // a porcentaje: la interfaz lo escribe con un «%» detrás, y la fracción hacía
        // que un 43 % de vencido se leyera como «0,43 %»
        overdue_share: latest.pct_vencido == null ? null : numberOrNull(latest.pct_vencido * 100),
        margin_3m: numberOrNull(latest.margin_3m),
        debt_service_ratio_3m: numberOrNull(latest.debt_service_ratio_3m),
        debt_outstanding: numberOrNull(company.debt_outstanding),
        debt_util: numberOrNull(company.debt_util),
        flows: toFlows(history),
      }
    })

    return { companies, source: 'supabase' as const }
  } catch (error) {
    console.error('Supabase portfolio read failed', error instanceof Error ? error.message : error)
    return {
      companies: demoCompanies,
      source: 'demo' as const,
      warning: 'No se pudo leer Supabase; se muestran los datos de demostración.',
    }
  }
})
