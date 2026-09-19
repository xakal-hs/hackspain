const demoCompanies = [
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
] as const

export default defineEventHandler(async () => {
  const config = useRuntimeConfig()

  if (config.xrayApiBase) {
    const apiBase = config.xrayApiBase.replace(/\/$/, '')
    const response = await $fetch<{ companies: unknown[] }>(`${apiBase}/api/companies`)
    return { ...response, source: 'api' as const }
  }

  return { companies: demoCompanies, source: 'demo' as const }
})
