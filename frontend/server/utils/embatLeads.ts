import type { EmbatLead, LeadStatus } from '../../shared/types/embat'

export interface LeadRow {
  id: string
  company_id: string
  status: LeadStatus
  assigned_to: string
  signal: 'financiar'
  email_draft: string
  created_at: string
}

export interface ManagerRow {
  id: string
  name: string
}

interface FeaturedName {
  company_id: string
  display_name: string
}

export async function hydrateLeads(
  rows: LeadRow[],
  knownManagers?: ManagerRow[],
): Promise<EmbatLead[]> {
  if (!rows.length) return []
  const read = companyDataReader()
  const ids = [...new Set(rows.map((row) => row.assigned_to))]
  const companyIds = [...new Set(rows.map((row) => row.company_id))]
  const [managers, featured] = await Promise.all([
    knownManagers
      ? Promise.resolve(knownManagers)
      : read<ManagerRow>('embat_account_managers', {
          select: 'id,name',
          id: `in.(${ids.join(',')})`,
          limit: 50,
        }).catch(() => [] as ManagerRow[]),
    read<FeaturedName>('featured_companies', {
      select: 'company_id,display_name',
      company_id: `in.(${companyIds.join(',')})`,
      limit: 50,
    }).catch(() => [] as FeaturedName[]),
  ])
  const byManager = new Map(managers.map((row) => [row.id, row.name]))
  const byCompany = new Map(featured.map((row) => [row.company_id, row.display_name]))
  return rows.map((row) => ({
    id: row.id,
    company_id: row.company_id,
    company_name: byCompany.get(row.company_id) || row.company_id,
    status: row.status,
    assigned_to: row.assigned_to,
    assignee_name: byManager.get(row.assigned_to) || 'Sin asignar',
    signal: row.signal,
    email_draft: row.email_draft,
    created_at: row.created_at,
  }))
}
