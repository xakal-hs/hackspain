import type { EmbatLead, LeadStatus } from '../../shared/types/embat'
import { employeesById, type Employee } from './embatEmployees'

export interface LeadRow {
  id: string
  company_id: string
  status: LeadStatus
  assigned_to: string
  signal: 'financiar'
  email_draft: string
  created_at: string
}

interface FeaturedName {
  company_id: string
  display_name: string
}

function label(employee: Employee | undefined) {
  if (!employee) return { name: 'Sin asignar', title: '' }
  return {
    name: employee.ai_full_name || employee.full_name,
    title: employee.ai_job_title || employee.job_title,
  }
}

export async function hydrateLeads(
  rows: LeadRow[],
  knownEmployees?: Employee[],
): Promise<EmbatLead[]> {
  if (!rows.length) return []
  const read = companyDataReader()
  const ids = [...new Set(rows.map((row) => row.assigned_to))]
  const companyIds = [...new Set(rows.map((row) => row.company_id))]
  const [employees, featured] = await Promise.all([
    knownEmployees ? Promise.resolve(knownEmployees) : employeesById(ids),
    read<FeaturedName>('featured_companies', {
      select: 'company_id,display_name',
      company_id: `in.(${companyIds.join(',')})`,
      limit: 50,
    }).catch(() => [] as FeaturedName[]),
  ])
  const byEmployee = new Map(employees.map((row) => [row.id, row]))
  const byCompany = new Map(featured.map((row) => [row.company_id, row.display_name]))
  return rows.map((row) => {
    const assignee = label(byEmployee.get(row.assigned_to))
    return {
      id: row.id,
      company_id: row.company_id,
      company_name: byCompany.get(row.company_id) || row.company_id,
      status: row.status,
      assigned_to: row.assigned_to,
      assignee_name: assignee.name,
      assignee_title: assignee.title,
      signal: row.signal,
      email_draft: row.email_draft,
      created_at: row.created_at,
    }
  })
}
