import type { CompanyDriver } from '../../shared/types/company'

export const scorePillars = [
  {
    id: 'liquidez',
    name: 'Liquidez',
    question: '¿Qué margen tienes para pagar?',
    description: 'El dinero que queda en las cuentas y el margen disponible en las líneas de crédito. Muestra el colchón para afrontar los próximos pagos.',
    reading: 'Más meses de caja y menos crédito dispuesto suelen dar más margen. Una contribución positiva no equivale por sí sola a tener caja suficiente.',
    features: [
      { key: 'runway', label: 'Meses de caja' },
      { key: 'lc_util', label: 'Uso de líneas de crédito' },
    ],
  },
  {
    id: 'rentabilidad',
    name: 'Rentabilidad',
    question: '¿El negocio está cobrando más?',
    description: 'En este modelo, este pilar se aproxima mediante la tendencia de cobros operativos: compara los últimos tres meses con la referencia de doce meses.',
    reading: 'Más cobros recientes favorecen esta señal. No es un margen de beneficio contable ni demuestra por sí solo que la empresa sea rentable.',
    features: [
      { key: 'oper_growth_12m', label: 'Tendencia de cobros' },
    ],
  },
  {
    id: 'solvencia',
    name: 'Solvencia',
    question: '¿Puedes sostener tus compromisos?',
    description: 'La parte de las entradas dedicada a deuda y la regularidad y continuidad de las nóminas. Son señales de la capacidad de sostener pagos recurrentes.',
    reading: 'Una menor carga de deuda deja más dinero para otros pagos. Las nóminas se evalúan solo cuando se observan: sin nóminas, la señal puede no aplicar.',
    features: [
      { key: 'debt_burden', label: 'Carga de deuda' },
      { key: 'payroll_cv', label: 'Regularidad de nóminas' },
      { key: 'payroll_continuity_6m', label: 'Continuidad de nóminas' },
    ],
  },
  {
    id: 'disciplina',
    name: 'Disciplina',
    question: '¿Se cobra y se paga a tiempo?',
    description: 'Los retrasos de clientes y proveedores, los importes vencidos y las devoluciones. Distingue el retraso por número de facturas del dinero que sigue pendiente.',
    reading: 'Menos retrasos, deuda vencida y devoluciones favorecen estas señales. La morosidad de clientes describe también a quienes deben pagarte, no solo tu conducta de pago.',
    features: [
      { key: 'ap_late_share', label: 'Pagos tardíos a proveedores' },
      { key: 'ar_late_share', label: 'Cobros tardíos de clientes' },
      { key: 'ap_overdue_ratio', label: 'Deuda vencida con proveedores' },
      { key: 'ar_overdue_90_ratio', label: 'Clientes morosos >60 días' },
      { key: 'refund_rate', label: 'Devoluciones de cobros' },
    ],
  },
  {
    id: 'estabilidad',
    name: 'Estabilidad',
    question: '¿Qué sostiene la continuidad del negocio?',
    description: 'La actividad bancaria, la continuidad de cobros, los meses con déficit y la base de clientes. También recoge la dependencia de transferencias ajenas a los cobros del negocio.',
    reading: 'Cobros sostenidos, clientes diversificados y menos déficits suelen dar una base más estable. Más movimientos no significan necesariamente más beneficio.',
    features: [
      { key: 'activity_trend', label: 'Tendencia de actividad' },
      { key: 'transfer_dep', label: 'Dependencia de transferencias' },
      { key: 'hhi_ar_6m', label: 'Concentración de clientes' },
      { key: 'net_vol_6m', label: 'Volatilidad a la baja' },
      { key: 'cust_trend', label: 'Amplitud de clientes' },
      { key: 'lost_share', label: 'Facturación de clientes perdidos' },
      { key: 'oper_persistence_6m', label: 'Persistencia de cobros' },
    ],
  },
] as const

export type ScorePillarId = typeof scorePillars[number]['id']

const featurePillar = new Map<string, ScorePillarId>(scorePillars.flatMap(p => p.features.map(f => [f.key, p.id] as const)))
const labelPillar = new Map<string, ScorePillarId>(scorePillars.flatMap(p => p.features.map(f => [f.label, p.id] as const)))
const magnitude = (row: CompanyDriver) => Number.isFinite(row.contribution) ? Math.abs(row.contribution) : 0

export function groupScoreDrivers(drivers: CompanyDriver[]) {
  const peak = Math.max(...drivers.map(magnitude), 1)
  const rows = drivers.map(row => ({
    ...row,
    pillar: row.feature ? featurePillar.get(row.feature) : labelPillar.get(row.label),
    weight: `${magnitude(row) / peak * 100}%`,
  })).sort((a, b) => magnitude(b) - magnitude(a))
  const contribution = (items: CompanyDriver[]) => items.length && items.every(row => Number.isFinite(row.contribution))
    ? items.reduce((sum, row) => sum + row.contribution, 0)
    : null
  const additional = rows.filter(row => !row.pillar)
  return {
    pillars: scorePillars.map(pillar => {
      const items = rows.filter(row => row.pillar === pillar.id)
      return { ...pillar, drivers: items, contribution: contribution(items) }
    }),
    additional: { drivers: additional, contribution: contribution(additional) },
  }
}

export function formatContribution(value: number | null): string {
  if (value == null || !Number.isFinite(value)) return 'Sin contribución'
  if (Math.abs(value) < 0.05) return '0,0'
  return value.toLocaleString('es-ES', { minimumFractionDigits: 1, maximumFractionDigits: 1, signDisplay: 'exceptZero' })
}
