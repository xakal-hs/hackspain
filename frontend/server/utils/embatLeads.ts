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

/** Lo único que pide la empresa desde el panel de flujo: un puente hasta que entra el cobro. */
const REASON = 'Préstamo puente'

function money(value: number, currency: string) {
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(value)
}

function day(iso: string) {
  return new Intl.DateTimeFormat('es-ES', { day: 'numeric', month: 'long', timeZone: 'UTC' }).format(
    new Date(`${iso}T00:00:00Z`),
  )
}

/* El comercial no llama con una etiqueta: llama con el importe y la fecha. El motivo se calcula
 * sobre la misma previsión que la empresa tenía delante al pulsar el botón. */
async function reasonsFor(companyIds: string[]): Promise<Map<string, { amount: string; detail: string }>> {
  const reasons = new Map<string, { amount: string; detail: string }>()
  const prevision = await loadPrevision().catch(() => null)
  if (!prevision) return reasons
  for (const id of companyIds) {
    const company = prevision.companies[id]
    const rotura = company?.forecast?.rotura
    if (!rotura) continue
    const amount = money(Math.abs(rotura.low), company!.currency || 'EUR')
    const rescue = rotura.rescue
      ? `, y el cobro que la tapa no entra hasta el ${day(rotura.rescue.date)}`
      : ''
    reasons.set(id, {
      amount,
      detail: `Necesita ${amount}: la caja toca fondo el ${day(rotura.low_date)}${rescue}.`,
    })
  }
  return reasons
}

export async function hydrateLeads(
  rows: LeadRow[],
  knownEmployees?: Employee[],
): Promise<EmbatLead[]> {
  if (!rows.length) return []
  const read = companyDataReader()
  const ids = [...new Set(rows.map((row) => row.assigned_to))]
  const companyIds = [...new Set(rows.map((row) => row.company_id))]
  const [employees, featured, reasons] = await Promise.all([
    knownEmployees ? Promise.resolve(knownEmployees) : employeesById(ids),
    read<FeaturedName>('featured_companies', {
      select: 'company_id,display_name',
      company_id: `in.(${companyIds.join(',')})`,
      limit: 50,
    }).catch(() => [] as FeaturedName[]),
    reasonsFor(companyIds),
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
      reason: REASON,
      reason_amount: reasons.get(row.company_id)?.amount ?? null,
      reason_detail: reasons.get(row.company_id)?.detail ?? null,
      email_draft: row.email_draft,
      created_at: row.created_at,
    }
  })
}
