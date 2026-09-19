import { companies as fixtures, type Company, type Decision } from '~/data/demo'
import type { CompanySummary } from '~/types/portfolio'

// `sin_nota` no es «presta»: es «no veo la empresa lo suficiente», y ante la duda se vigila.
const decisionByAccion: Record<NonNullable<CompanySummary['accion']>, Decision> = {
  prestar: 'prestar',
  vigilar: 'vigilar',
  no_prestar: 'no-prestar',
  sin_nota: 'vigilar',
}

const templateByCompany: Record<string, Company> = {
  COMP_0864: fixtures.find((company) => company.id === 'iberica')!,
  COMP_0412: fixtures.find((company) => company.id === 'solis')!,
  COMP_1107: fixtures.find((company) => company.id === 'nortex')!,
  COMP_0239: fixtures.find((company) => company.id === 'sureste')!,
  COMP_0721: fixtures.find((company) => company.id === 'vidal')!,
}

const round = (value: number | null | undefined, fallback: number) =>
  value == null ? fallback : Math.round(value * 10) / 10

const clampScore = (value: number) => Math.max(0, Math.min(100, Math.round(value)))

function alignedHistory(template: Company, summary: CompanySummary) {
  // Si el backend manda la serie real de la nota, se usa tal cual: la plantilla solo
  // existe para rellenar la forma cuando la fuente no tiene historia propia.
  if (summary.history?.length) {
    const real = summary.history.map(clampScore)
    const pad = template.history.length - real.length
    return pad > 0 ? [...Array.from({ length: pad }, () => real[0]!), ...real] : real.slice(-template.history.length)
  }
  const shifted = template.history.map((value) =>
    clampScore(value + summary.score - template.score),
  )
  const change = Math.round(summary.delta3_q50)
  const anchor = shifted.length - 4

  if (anchor >= 0) {
    for (let step = 0; step <= 3; step += 1)
      shifted[anchor + step] = clampScore(summary.score - change + (change * step) / 3)
  }
  return shifted
}

function currency(value: number | null | undefined, code: string) {
  if (value == null) return 'sin dato de caja'
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: code,
    maximumFractionDigits: 0,
  }).format(value)
}

function realSignals(summary: CompanySummary, template: Company): Company['signals'] {
  const runwayNow = round(summary.runway_now, template.runway.now)
  const runwayPrev = round(summary.runway_prev, template.runway.prev)
  const dsoNow = round(summary.dso_now, template.dso.now)
  const dsoPrev = round(summary.dso_prev, template.dso.prev)
  const margin = summary.margin_3m
  const overdue = summary.overdue_share

  return [
    {
      label: 'El dinero que queda en la cuenta',
      detail: `${currency(summary.cash_end, summary.currency)} · ${runwayNow.toLocaleString('es-ES')} meses de pagos`,
      weight: 0.42,
      direction: runwayNow > runwayPrev ? 'up' : runwayNow < runwayPrev ? 'down' : 'flat',
    },
    {
      label: 'Lo que entra frente a lo que sale',
      detail: margin == null ? 'Sin margen comparable' : `${(margin * 100).toLocaleString('es-ES', { maximumFractionDigits: 1 })} % en tres meses`,
      weight: 0.28,
      direction: margin == null ? 'flat' : margin >= 0 ? 'up' : 'down',
    },
    {
      label: 'Cuánto tardan los clientes en pagar',
      detail: summary.dso_now == null ? 'No hay facturas suficientes' : `${dsoNow.toLocaleString('es-ES')} días · antes ${dsoPrev.toLocaleString('es-ES')}`,
      weight: 0.2,
      direction: summary.dso_now == null ? 'flat' : dsoNow < dsoPrev ? 'up' : dsoNow > dsoPrev ? 'down' : 'flat',
    },
    {
      label: 'Facturas pendientes de cobro',
      detail: overdue == null ? 'Sin cobertura de facturas' : `${overdue.toLocaleString('es-ES', { maximumFractionDigits: 1 })} % con más de 60 días de retraso`,
      weight: 0.1,
      direction: overdue == null ? 'flat' : overdue >= 10 ? 'down' : 'flat',
    },
  ]
}

/**
 * Joins Supabase treasury facts to the product-only fixture fields. Scores,
 * names, sectors, decisions, trajectories and offer terms remain mocked until
 * their corresponding tables are available.
 */
export function portfolioCompany(summary: CompanySummary): Company {
  const template = templateByCompany[summary.company_id] || fixtures[0]!
  const history = alignedHistory(template, summary)
  const forecast = template.forecast.map((value) =>
    clampScore(summary.score + value - template.score),
  )
  const runway = round(summary.runway_now, template.runway.now)
  const dso = round(summary.dso_now, template.dso.now)
  const facts = [
    `La cuenta cierra con ${currency(summary.cash_end, summary.currency)}`,
    `cubre ${runway.toLocaleString('es-ES')} meses de pagos`,
    summary.dso_now == null
      ? 'no hay facturas suficientes para medir el cobro'
      : `los clientes pagan a ${dso.toLocaleString('es-ES')} días`,
  ]

  return {
    ...template,
    id: summary.company_id,
    name: `Empresa ${summary.company_id.replace('COMP_', '')}`,
    group: summary.group_id,
    score: summary.score,
    band: summary.band,
    // La decisión y su motivo vienen del backend: un veto puede decir «no prestar» con
    // buena nota, así que deducirla del score sería enseñar otra cosa de la que se decide.
    decision: summary.accion ? decisionByAccion[summary.accion] : template.decision,
    action: summary.razon || template.action,
    delta3: Math.round(summary.delta3_q50),
    delta12: summary.score - history.at(-13)!,
    history,
    forecast,
    shape:
      summary.trend === 'mejora'
        ? 'mejora'
        : summary.trend === 'deterioro'
          ? 'deterioro'
          : 'estable',
    runway: {
      now: round(summary.runway_now, template.runway.now),
      prev: round(summary.runway_prev, template.runway.prev),
    },
    // 0 es el centinela de «sin DSO» que ya entiende la interfaz (`dso.now || '—'`).
    // Caer al valor de la plantilla enseñaría 31 días de ficción como si fueran medidos:
    // la mitad de las empresas no tiene ERP suficiente para calcularlo.
    dso: {
      now: round(summary.dso_now, 0),
      prev: round(summary.dso_prev, 0),
    },
    erp: summary.has_erp,
    monthsConnected: summary.n_months,
    coverage: summary.confidence,
    flows: summary.flows?.length ? summary.flows : template.flows,
    signals: realSignals(summary, template),
    headline: summary.alert || template.headline,
    why: `${facts.join('; ')}.`,
  }
}

export function portfolioCompanies(rows: CompanySummary[]) {
  return rows.map(portfolioCompany)
}
