import type { Veto } from '~/types/portfolio'

/** Prestar / vigilar / no prestar en un mes concreto. Los vetos mandan sobre la nota. */
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
  const asked = getQuery(event).month ? String(getQuery(event).month) : null
  if (asked && !/^\d{4}-\d{2}(-\d{2})?$/.test(asked))
    throw createError({ statusCode: 400, statusMessage: 'Mes inválido' })

  const read = companyDataReader()
  const rows = await read<DecisionRow>('company_decision_monthly', {
    company_id: `eq.${id}`,
    select: 'month,accion,accion_label,razon,vetos,avisos,razones,importe_max_meses',
    // sin mes pedido, el último publicado
    ...(asked ? { month: `eq.${asked.length === 7 ? `${asked}-01` : asked}` } : {}),
    order: 'month.desc',
    limit: 1,
  })
  const decision = rows[0]
  if (!decision)
    throw createError({ statusCode: 404, statusMessage: `Mes sin decisión para ${id}: ${asked ?? 'último'}` })

  return {
    company_id: id,
    month: monthLabel(decision.month),
    accion: decision.accion,
    accion_label: decision.accion_label,
    razon: decision.razon,
    vetos: decision.vetos,
    avisos: decision.avisos,
    razones: decision.razones,
    importe_max_meses: decision.importe_max_meses,
  }
})
