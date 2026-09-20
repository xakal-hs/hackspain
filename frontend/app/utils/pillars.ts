/**
 * Los cinco pilares y las señales que los forman. Es el catálogo de `research/src/xray.py`
 * (el campo `pilar` de FEATURES), copiado aquí solo para poder descomponer un pilar en pantalla
 * sin pedir nada al servidor. Los VALORES nunca salen de aquí: vienen de las herramientas.
 */
export const PILLARS = ['liquidez', 'rentabilidad', 'solvencia', 'disciplina', 'estabilidad'] as const
export type Pillar = typeof PILLARS[number]

export const PILLAR_LABEL: Record<Pillar, string> = {
  liquidez: 'Liquidez',
  rentabilidad: 'Rentabilidad',
  solvencia: 'Solvencia',
  disciplina: 'Disciplina',
  estabilidad: 'Estabilidad',
}

/** Qué pregunta responde cada pilar, en el lenguaje del producto y no en el del modelo. */
export const PILLAR_ASKS: Record<Pillar, string> = {
  liquidez: '¿Cuánto dinero le queda y cuánto le dura?',
  rentabilidad: '¿Está cobrando más que hace un año?',
  solvencia: '¿Puede con la deuda y paga las nóminas?',
  disciplina: '¿Paga y cobra a tiempo?',
  estabilidad: '¿Su actividad y sus clientes son estables?',
}

export const PILLAR_FEATURES: Record<Pillar, { key: string, label: string }[]> = {
  liquidez: [
    { key: 'runway', label: 'Meses de caja' },
    { key: 'lc_util', label: 'Uso de líneas de crédito' },
  ],
  rentabilidad: [
    { key: 'oper_growth_12m', label: 'Tendencia de cobros' },
  ],
  solvencia: [
    { key: 'debt_burden', label: 'Carga de deuda' },
    { key: 'payroll_cv', label: 'Regularidad de nóminas' },
    { key: 'payroll_continuity_6m', label: 'Continuidad de nóminas' },
  ],
  disciplina: [
    { key: 'ap_late_share', label: 'Pagos tardíos a proveedores' },
    { key: 'ar_late_share', label: 'Cobros tardíos de clientes' },
    { key: 'ap_overdue_ratio', label: 'Deuda vencida con proveedores' },
    { key: 'ar_overdue_90_ratio', label: 'Clientes morosos >60 días' },
    { key: 'refund_rate', label: 'Devoluciones de cobros' },
  ],
  estabilidad: [
    { key: 'activity_trend', label: 'Tendencia de actividad' },
    { key: 'transfer_dep', label: 'Dependencia de transferencias' },
    { key: 'hhi_ar_6m', label: 'Concentración de clientes' },
    { key: 'net_vol_6m', label: 'Volatilidad a la baja' },
    { key: 'cust_trend', label: 'Amplitud de clientes' },
    { key: 'lost_share', label: 'Facturación de clientes perdidos' },
    { key: 'oper_persistence_6m', label: 'Persistencia de cobros' },
  ],
}
