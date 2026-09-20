import type { CashForecast, CashflowAction, CashflowCategories, CompanyHealth } from '../../shared/types/company'

interface Prevision {
  snapshot: string
  companies: Record<string, {
    currency: string
    categories?: CashflowCategories
    forecast: CashForecast | null
  }>
}

let loaded: Promise<Prevision | null> | undefined

export const loadPrevision = () => {
  const assets = useStorage('assets:server')
  // En desarrollo se lee siempre: si no, regenerar el JSON obliga a reiniciar el servidor.
  if (import.meta.dev) return assets.getItem<Prevision>('prevision.json')
  return (loaded ??= assets.getItem<Prevision>('prevision.json'))
}

export function actionFor(
  forecast: CashForecast | null,
  health: CompanyHealth | undefined,
): CashflowAction {
  if (forecast?.rotura) return 'financiar'
  // Para colocar caja basta con que sobre de verdad y la empresa no esté en riesgo: el dinero es suyo
  // y la operación es reversible, así que la banda «vigilar» no es motivo para no ofrecerlo.
  if (forecast?.excedente && health && health.health_band !== 'riesgo') return 'prestar'
  return null
}
