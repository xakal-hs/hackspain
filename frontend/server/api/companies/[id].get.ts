import type { Veto } from '~/types/portfolio'

/**
 * Ficha de una empresa: la serie de la nota, los pilares del último mes, la decisión del
 * prestamista y las señales ordenadas por cuánto aportan a la nota.
 *
 * Las señales salen de `company_health_driver_monthly`, donde cada fila es la contribución
 * exacta de una señal al número publicado: no es una aproximación tipo SHAP, es la
 * descomposición del score. El peso lo pone el catálogo del modelo.
 */
interface HealthRow {
  month: string
  health_score: number
  health_band: string
  health_trend: string
  score_delta_3m: number | null
  coverage: number | null
  confidence: number | null
  ood_share: number | null
  risk_flags: string[] | null
  liquidez_score: number | null
  rentabilidad_score: number | null
  solvencia_score: number | null
  disciplina_score: number | null
  estabilidad_score: number | null
}

interface DriverRow {
  feature: string
  pillar: string
  label: string
  raw_value: number | null
  display_value: string
  contribution: number
}

interface DecisionRow {
  month: string
  accion: string
  accion_label: string
  razon: string
  vetos: Veto[]
  avisos: Veto[]
  razones: { codigo: string, etiqueta: string, texto: string }[]
  importe_max_meses: number | null
}

export default defineEventHandler(async (event) => {
  const id = companyIdOf(event)
  const read = companyDataReader()
  const filter = { company_id: `eq.${id}` }

  const health = await read<HealthRow>('company_health_monthly', {
    ...filter,
    select: 'month,health_score,health_band,health_trend,score_delta_3m,coverage,confidence,ood_share,'
      + 'risk_flags,liquidez_score,rentabilidad_score,solvencia_score,disciplina_score,estabilidad_score',
    order: 'month.asc',
    limit: 500,
  })
  if (!health.length)
    throw createError({ statusCode: 404, statusMessage: `Empresa sin nota publicada: ${id}` })

  const current = health.at(-1)!
  const version = await publishedVersion()
  const [drivers, decisions, catalog] = await Promise.all([
    read<DriverRow>('company_health_driver_monthly', {
      ...filter, month: `eq.${current.month}`, score_version: `eq.${version}`,
      select: 'feature,pillar,label,raw_value,display_value,contribution',
      order: 'contribution.asc', limit: 100,
    }),
    read<DecisionRow>('company_decision_monthly', {
      ...filter, month: `eq.${current.month}`,
      select: 'month,accion,accion_label,razon,vetos,avisos,razones,importe_max_meses', limit: 1,
    }),
    scoreCatalog(),
  ])

  const decision = decisions[0]
  return {
    company_id: id,
    month: monthLabel(current.month),
    score: round(current.health_score) ?? 0,
    band: bandOf(current.health_band),
    trend: trendOf(current.health_trend),
    delta3: round(current.score_delta_3m),
    confidence: round(current.confidence, 2),
    coverage: round(current.coverage, 2),
    ood_share: round(current.ood_share, 3),
    risk_flags: current.risk_flags ?? [],
    pillars: pillarsOf(current as unknown as Record<string, unknown>),
    decision: decision
      ? {
          accion: decision.accion, accion_label: decision.accion_label, razon: decision.razon,
          vetos: decision.vetos, avisos: decision.avisos, razones: decision.razones,
          importe_max_meses: decision.importe_max_meses,
        }
      : null,
    series: health.map(row => ({
      month: monthLabel(row.month),
      score: round(row.health_score) ?? 0,
      band: bandOf(row.health_band),
    })),
    // de la que menos aporta a la que más: arriba queda lo que está lastrando la nota
    signals: drivers.map(row => ({
      feature: row.feature,
      label: row.label,
      pillar: row.pillar,
      formula: catalog.features[row.feature]?.formula ?? null,
      weight: catalog.weights[row.feature] ?? null,
      points: round(row.contribution, 2),
      value: row.raw_value,
      value_text: row.display_value,
    })),
  }
})
