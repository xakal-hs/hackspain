/** Credentials stay on the server. Never copy the secret key into public config. */
export function supabaseRest() {
  const config = useRuntimeConfig()
  const url = String(config.public.supabaseUrl || '').replace(/\/$/, '')
  const key = String(config.supabaseSecretKey || '')
  if (!url || !key) throw createError({ statusCode: 503, statusMessage: 'Supabase no está configurado' })
  return {
    url,
    headers: {
      apikey: key,
      Authorization: `Bearer ${key}`,
      Prefer: 'return=representation',
    },
  }
}

/** Read-only access for the existing demo. */
export function companyDataReader() {
  const { url, headers } = supabaseRest()
  return async <T>(table: string, query: Record<string, string | number>): Promise<T[]> =>
    $fetch<T[]>(`${url}/rest/v1/${table}`, {
      headers,
      query, timeout: 15000,
    })
}

export async function companyDataWrite<T>(
  method: 'POST' | 'PATCH',
  table: string,
  query: Record<string, string | number>,
  body: Record<string, unknown>,
): Promise<T[]> {
  const { url, headers } = supabaseRest()
  return $fetch<T[]>(`${url}/rest/v1/${table}`, {
    method,
    headers,
    query,
    body,
    timeout: 15000,
  })
}

// PostgREST caps responses. Keep paging, including when the last page is full.
export async function companyDataPages<T>(table: string, select: string) {
  const read = companyDataReader()
  const rows: T[] = []
  for (let offset = 0; ; offset += 500) {
    const page = await read<T>(table, { select, order: 'company_id.asc', offset, limit: 500 })
    rows.push(...page)
    if (page.length < 500) return rows
  }
}
