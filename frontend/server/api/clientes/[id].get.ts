import type { ClientBook, ClientBookResponse } from '../../../shared/types/company'

interface Clientes {
  snapshot: string
  cover: number
  premium_rate: number
  companies: Record<string, ClientBook>
}
interface Prevision {
  companies: Record<string, { forecast: { excedente: { amount: number } | null } | null }>
}

// server/assets/clientes.json lo genera scripts/build_cartera_clientes.py; se lee como asset de Nitro
// para que el typecheck no tenga que inferir un JSON de 3 MB.
let clientes: Promise<Clientes | null> | undefined
let prevision: Promise<Prevision | null> | undefined
const load = () => {
  clientes ??= useStorage('assets:server').getItem<Clientes>('clientes.json')
  prevision ??= useStorage('assets:server').getItem<Prevision>('prevision.json')
  return Promise.all([clientes, prevision])
}

export default defineEventHandler(async (event): Promise<ClientBookResponse> => {
  const id = getRouterParam(event, 'id') || ''
  if (!/^COMP_\d{4}$/.test(id)) throw createError({ statusCode: 400, statusMessage: 'Empresa inválida' })
  const [book, forecasts] = await load()
  const entry = book?.companies[id]
  return {
    snapshot: book?.snapshot ?? '',
    cover: book?.cover ?? 0.9,
    premiumRate: book?.premium_rate ?? 0.0035,
    ventas12m: entry?.ventas_12m ?? 0,
    clientes: entry?.clientes ?? [],
    caucion: entry?.caucion ?? null,
    excedente: forecasts?.companies[id]?.forecast?.excedente?.amount ?? null,
  }
})
