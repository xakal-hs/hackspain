import type { CompanySummary, MonthFlow, PortfolioResponse, Veto } from '~/types/portfolio'

/**
 * La cartera: el último mes de cada empresa, lo peor arriba.
 *
 * Una sola consulta a `company_portfolio_latest`, que ya agrega en PostgreSQL la salud,
 * la decisión, el panel y los doce meses de flujos y notas. Paginar aquí 22.000 filas de
 * panel en cada petición costaba más que la consulta entera.
 */
interface PortfolioRow {
  company_id: string
  group_id: string | null
  currency: string | null
  has_erp: boolean | null
  n_months: number
  last_month: string
  score: number
  band: string
  delta3: number | null
  health_trend: string
  coverage: number | null
  confidence: number | null
  accion: string | null
  accion_label: string | null
  razon: string | null
  vetos: Veto[] | null
  avisos: Veto[] | null
  importe_max_meses: number | null
  cash_end: number | null
  runway_now: number | null
  runway_prev: number | null
  dso_now: number | null
  dso_prev: number | null
  overdue_share: number | null
  margin_3m: number | null
  debt_service_ratio_3m: number | null
  n_tx: number | null
  debt_outstanding: number | null
  debt_util: number | null
  flows: MonthFlow[] | null
  history: number[] | null
  liquidez_score: number | null
  rentabilidad_score: number | null
  solvencia_score: number | null
  disciplina_score: number | null
  estabilidad_score: number | null
}

const BANDS = new Set(['sano', 'vigilar', 'riesgo'])

/* La cartera solo cambia cuando corre el job de publicación, no entre peticiones. Se cachea
 * la lectura y no el manejador, para que el respaldo de demostración nunca entre en caché. */
const readPortfolio = defineCachedFunction(
  (band: string | null) => companyDataPages<PortfolioRow>(
    'company_portfolio_latest',
    '*',
    'score.asc,company_id.asc',
    band ? { band: `eq.${band}` } : {},
  ),
  { maxAge: 300, name: 'portfolio', getKey: (band: string | null) => band ?? 'todas' },
)

/* Sin Supabase configurado el proyecto sigue arrancando: `pnpm dev` a secas enseña esta
 * cartera de muestra en vez de una pantalla de error. No es un respaldo de producción. */
const demoCompanies: CompanySummary[] = [
  {
    company_id: 'COMP_0864', group_id: 'GROUP_0198', currency: 'EUR', has_erp: true,
    n_months: 24, last_month: '2026-09', score: 68, band: 'vigilar',
    delta3_q50: -8.4, trend: 'deterioro',
    alert: 'La caja cae durante tres meses consecutivos.', dormant: false, confidence: 0.91,
  },
  {
    company_id: 'COMP_0412', group_id: 'GROUP_0084', currency: 'EUR', has_erp: true,
    n_months: 22, last_month: '2026-09', score: 81, band: 'sano',
    delta3_q50: 5.7, trend: 'mejora', alert: null, dormant: false, confidence: 0.88,
  },
  {
    company_id: 'COMP_1107', group_id: 'GROUP_0231', currency: 'GBP', has_erp: false,
    n_months: 24, last_month: '2026-09', score: 74, band: 'sano',
    delta3_q50: 0.6, trend: 'estable', alert: null, dormant: false, confidence: 0.73,
  },
  {
    company_id: 'COMP_0239', group_id: 'GROUP_0056', currency: 'EUR', has_erp: true,
    n_months: 18, last_month: '2026-09', score: 43, band: 'riesgo',
    delta3_q50: -6.2, trend: 'deterioro',
    alert: 'Los pagos superan los cobros y la deuda consume la caja.', dormant: false, confidence: 0.86,
  },
  {
    company_id: 'COMP_0721', group_id: 'GROUP_0142', currency: 'USD', has_erp: true,
    n_months: 21, last_month: '2026-09', score: 62, band: 'vigilar',
    delta3_q50: 2.3, trend: 'mejora',
    alert: 'Recuperación temprana tras un bache de tesorería.', dormant: false, confidence: 0.79,
  },
]

function toSummary(row: PortfolioRow): CompanySummary {
  const delta3 = round(row.delta3)
  const confidence = round(row.confidence, 2)
  const band = bandOf(row.band)
  return {
    company_id: row.company_id,
    group_id: row.group_id ?? '',
    currency: row.currency ?? 'EUR',
    has_erp: Boolean(row.has_erp),
    n_months: row.n_months,
    last_month: monthLabel(row.last_month),
    score: round(row.score) ?? 0,
    band,
    delta3_q50: delta3 ?? 0,
    trend: trendOf(row.health_trend),
    alert: alertOf({ band, delta3, confidence }),
    // sin un solo movimiento en el mes no hay empresa que observar, solo un saldo parado
    dormant: (row.n_tx ?? 0) === 0,
    confidence: confidence ?? 0,
    pillars: pillarsOf(row as unknown as Record<string, unknown>),
    history: row.history ?? undefined,
    flows: row.flows ?? undefined,
    accion: (row.accion ?? undefined) as CompanySummary['accion'],
    accion_label: row.accion_label ?? undefined,
    razon: row.razon ?? undefined,
    vetos: row.vetos ?? [],
    avisos: row.avisos ?? [],
    importe_max_meses: row.importe_max_meses,
    cash_end: row.cash_end,
    runway_now: round(row.runway_now),
    runway_prev: round(row.runway_prev),
    dso_now: round(row.dso_now, 0),
    dso_prev: round(row.dso_prev, 0),
    overdue_share: round(row.overdue_share),
    margin_3m: round(row.margin_3m, 4),
    debt_service_ratio_3m: round(row.debt_service_ratio_3m, 4),
    debt_outstanding: row.debt_outstanding,
    debt_util: round(row.debt_util, 4),
  }
}

export default defineEventHandler(async (event): Promise<PortfolioResponse> => {
  const band = getQuery(event).band ? String(getQuery(event).band) : null
  if (band && !BANDS.has(band))
    throw createError({ statusCode: 400, statusMessage: 'Banda inválida' })

  const config = useRuntimeConfig()
  if (!config.public.supabaseUrl || !config.supabaseSecretKey)
    return { companies: demoCompanies, source: 'demo' }

  try {
    const rows = await readPortfolio(band)
    return { companies: rows.map(toSummary), source: 'supabase' }
  } catch (error) {
    console.error('Supabase portfolio read failed', error instanceof Error ? error.message : error)
    return {
      companies: demoCompanies,
      source: 'demo',
      warning: 'No se pudo leer Supabase; se muestran los datos de demostración.',
    }
  }
})
