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

export const loadPrevision = () =>
  (loaded ??= useStorage('assets:server').getItem<Prevision>('prevision.json'))

export function actionFor(
  forecast: CashForecast | null,
  health: CompanyHealth | undefined,
): CashflowAction {
  if (forecast?.rotura) return 'financiar'
  if (forecast?.excedente && health?.health_band === 'sano') return 'prestar'
  return null
}
