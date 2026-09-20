/**
 * Por qué se movió la nota: el cambio del mes repartido entre las señales.
 *
 * Cada fila de `company_health_driver_monthly` es la contribución de una señal al número
 * publicado, así que la diferencia entre dos meses es, señal a señal, de dónde salió el
 * movimiento. Lo que no explican las señales (el tope por inactividad, el recorte a 0-100)
 * viaja como una fila propia en vez de desaparecer: la suma tiene que cerrar el delta.
 */
const MIN_POINTS = 0.05          // por debajo de esto es ruido de redondeo, no una explicación
const RESIDUAL_LABEL = 'Reglas y límites de escala'

interface DriverRow {
  month: string
  feature: string
  pillar: string
  label: string
  raw_value: number | null
  display_value: string
  contribution: number
}

export default defineEventHandler(async (event) => {
  const id = companyIdOf(event)
  const asked = getQuery(event).month ? String(getQuery(event).month) : null
  if (asked && !/^\d{4}-\d{2}(-\d{2})?$/.test(asked))
    throw createError({ statusCode: 400, statusMessage: 'Mes inválido' })

  const read = companyDataReader()
  const filter = { company_id: `eq.${id}` }
  const health = await read<{ month: string, health_score: number }>('company_health_monthly', {
    ...filter, select: 'month,health_score', order: 'month.asc', limit: 500,
  })
  if (!health.length)
    throw createError({ statusCode: 404, statusMessage: `Empresa sin nota publicada: ${id}` })

  const index = asked
    ? health.findIndex(row => monthLabel(row.month) === monthLabel(asked))
    : health.length - 1
  if (index < 0)
    throw createError({ statusCode: 404, statusMessage: `Mes sin datos para ${id}: ${asked}` })

  const current = health[index]!
  if (index === 0) {
    return {
      company_id: id, month: monthLabel(current.month), prev_month: null, delta: 0,
      contributions: [], summary_text: 'Primer mes con datos: sin referencia anterior.',
    }
  }

  const previous = health[index - 1]!
  const drivers = await read<DriverRow>('company_health_driver_monthly', {
    ...filter,
    score_version: `eq.${await publishedVersion()}`,
    month: `in.(${previous.month},${current.month})`,
    select: 'month,feature,pillar,label,raw_value,display_value,contribution',
    order: 'feature.asc', limit: 200,
  })

  const before = new Map(drivers.filter(d => d.month === previous.month).map(d => [d.feature, d]))
  const after = new Map(drivers.filter(d => d.month === current.month).map(d => [d.feature, d]))
  const delta = Number((current.health_score - previous.health_score).toFixed(2))

  const rows = [...new Set([...before.keys(), ...after.keys()])].map((feature) => {
    const now = after.get(feature)
    const prev = before.get(feature)
    const points = Number(((now?.contribution ?? 0) - (prev?.contribution ?? 0)).toFixed(2))
    const label = now?.label ?? prev?.label ?? feature
    return {
      feature, label,
      pillar: now?.pillar ?? prev?.pillar ?? 'regla',
      delta_points: points,
      value_prev: prev?.raw_value ?? null,
      value_now: now?.raw_value ?? null,
      text: `${label}: ${prev?.display_value ?? 'sin dato'} → ${now?.display_value ?? 'sin dato'} (${es(points, 1, true)} pts)`,
    }
  })

  // lo que las señales no explican son las reglas que van encima de la suma
  const explained = rows.reduce((sum, row) => sum + row.delta_points, 0)
  const residual = Number((delta - explained).toFixed(2))
  if (Math.abs(residual) >= MIN_POINTS) {
    rows.push({
      feature: 'reglas', label: RESIDUAL_LABEL, pillar: 'regla', delta_points: residual,
      value_prev: null, value_now: null,
      text: `${RESIDUAL_LABEL}: ${es(residual, 1, true)} pts`,
    })
  }

  const contributions = rows
    .filter(row => Math.abs(row.delta_points) >= MIN_POINTS)
    .sort((a, b) => Math.abs(b.delta_points) - Math.abs(a.delta_points))

  const leading = contributions.filter(row => Math.sign(row.delta_points) === Math.sign(delta)).slice(0, 2)
  const why = leading.length ? leading.map(row => row.label.toLowerCase()).join(' y ') : 'cambios menores'

  return {
    company_id: id,
    month: monthLabel(current.month),
    prev_month: monthLabel(previous.month),
    delta,
    contributions,
    summary_text: `El score ${delta > 0 ? 'sube' : 'baja'} ${es(Math.abs(delta))} puntos `
      + `(${es(previous.health_score)} → ${es(current.health_score)}), sobre todo por ${why}.`,
  }
})
