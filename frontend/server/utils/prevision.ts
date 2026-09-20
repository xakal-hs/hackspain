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
  if (forecast?.excedente && health?.health_band === 'sano') return 'prestar'
  return null
}
