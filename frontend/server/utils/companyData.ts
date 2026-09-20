/** Read-only access for the existing demo. Credentials stay on the server. */
export function companyDataReader() {
  const config = useRuntimeConfig()
  const url = String(config.public.supabaseUrl || '').replace(/\/$/, '')
  const key = String(config.supabaseSecretKey || '')
  if (!url || !key) throw createError({ statusCode: 503, statusMessage: 'Supabase no está configurado' })
  return async <T>(table: string, query: Record<string, string | number>): Promise<T[]> =>
    $fetch<T[]>(`${url}/rest/v1/${table}`, {
      headers: { apikey: key, Authorization: `Bearer ${key}` },
      query, timeout: 15000,
    })
}

// PostgREST caps responses. Keep paging, including when the last page is full.
// `order` debe desempatar de forma estable (p. ej. `score.asc,company_id.asc`): con un
// orden ambiguo, dos páginas consecutivas pueden repetir u omitir filas.
export async function companyDataPages<T>(
  table: string,
  select: string,
  order = 'company_id.asc',
  filters: Record<string, string | number> = {},
) {
  const read = companyDataReader()
  const rows: T[] = []
  // 1.000 es el techo de PostgREST (`db-max-rows`): pedir menos solo añade viajes.
  const size = 1000
  for (let offset = 0; ; offset += size) {
    const page = await read<T>(table, { ...filters, select, order, offset, limit: size })
    rows.push(...page)
    if (page.length < size) return rows
  }
}
