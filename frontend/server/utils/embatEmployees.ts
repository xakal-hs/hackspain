import seed from '../data/embat-employees.json'
import type { EmployeeTeam } from '../../shared/types/embat'


export interface Employee {
  id: string
  first_name: string
  last_name: string
  full_name: string
  job_title: string
  company: string
  team: EmployeeTeam
  standardized_role: string
  ai_full_name: string
  ai_job_title: string
}

export interface EmployeePublic {
  id: string
  name: string
  job_title: string
  team: EmployeeTeam
  standardized_role: string
}

function isMissingTable(error: unknown) {
  const payload = error as { statusCode?: number; status?: number; data?: { code?: string }; message?: string }
  const code = payload?.data?.code || ''
  const message = String(payload?.message || '')
  return code === 'PGRST205' || message.includes('Could not find the table') || payload?.statusCode === 404 || payload?.status === 404
}

function seedEmployees(): Employee[] {
  return (seed as Employee[]).slice()
}

export function toPublic(row: Employee): EmployeePublic {
  return {
    id: row.id,
    name: row.ai_full_name || row.full_name,
    job_title: row.ai_job_title || row.job_title,
    team: row.team,
    standardized_role: row.standardized_role,
  }
}

export function commercials(rows: Employee[]) {
  return rows.filter((row) => row.team === 'account_management')
}

export async function listEmployees(): Promise<Employee[]> {
  try {
    const read = companyDataReader()
    const rows = await read<Employee>('embat_employees', {
      select: 'id,first_name,last_name,full_name,job_title,company,team,standardized_role,ai_full_name,ai_job_title',
      order: 'ai_full_name.asc',
      limit: 100,
    })
    if (rows.length) return rows
  } catch (error) {
    if (!isMissingTable(error)) throw error
  }
  return seedEmployees().sort((a, b) => a.ai_full_name.localeCompare(b.ai_full_name, 'es'))
}

export async function employeesById(ids: string[]): Promise<Employee[]> {
  if (!ids.length) return []
  const unique = [...new Set(ids)]
  try {
    const read = companyDataReader()
    return await read<Employee>('embat_employees', {
      select: 'id,first_name,last_name,full_name,job_title,company,team,standardized_role,ai_full_name,ai_job_title',
      id: `in.(${unique.join(',')})`,
      limit: 100,
    })
  } catch (error) {
    if (!isMissingTable(error)) throw error
  }
  const wanted = new Set(unique)
  return seedEmployees().filter((row) => wanted.has(row.id))
}
