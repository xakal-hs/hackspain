import { randomUUID } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { FINANCING_EMAIL_DRAFT } from './embatDraft'
import { hydrateLeads, type LeadRow } from './embatLeads'
import { commercials, listEmployees, type Employee } from './embatEmployees'
import type { EmbatLead, LeadStatus } from '../../shared/types/embat'

interface FileState {
  employees: Employee[]
  leads: LeadRow[]
}

const FILE = join(process.cwd(), '.data', 'embat-crm.json')
const SEED_LEADS: Array<Pick<LeadRow, 'company_id' | 'status'>> = [
  { company_id: 'COMP_0779', status: 'nuevo' },
  { company_id: 'COMP_0130', status: 'contactado' },
  { company_id: 'COMP_1155', status: 'reunion' },
]

function isMissingTable(error: unknown) {
  const payload = error as { statusCode?: number; status?: number; data?: { code?: string }; message?: string }
  const code = payload?.data?.code || ''
  const message = String(payload?.message || '')
  return code === 'PGRST205' || message.includes('Could not find the table') || payload?.statusCode === 404 || payload?.status === 404
}

async function readFileState(): Promise<FileState> {
  const employees = commercials(await listEmployees())
  try {
    const parsed = JSON.parse(await readFile(FILE, 'utf8')) as FileState
    const known = new Set(employees.map((row) => row.id))
    if (parsed.employees?.length && parsed.employees.every((row) => known.has(row.id))) {
      return { employees, leads: parsed.leads }
    }
  } catch {
    /* rebuild seed */
  }
  const leads: LeadRow[] = SEED_LEADS.map((row, index) => ({
    id: randomUUID(),
    company_id: row.company_id,
    status: row.status,
    assigned_to: employees[index % employees.length]!.id,
    signal: 'financiar',
    email_draft: FINANCING_EMAIL_DRAFT,
    created_at: new Date().toISOString(),
  }))
  const state = { employees, leads }
  await mkdir(dirname(FILE), { recursive: true })
  await writeFile(FILE, JSON.stringify(state, null, 2))
  return state
}

async function writeFileState(state: FileState) {
  await mkdir(dirname(FILE), { recursive: true })
  await writeFile(FILE, JSON.stringify(state, null, 2))
}

let supabaseReady: Promise<boolean> | undefined

async function probeSupabase() {
  try {
    const read = companyDataReader()
    await read<{ id: string }>('embat_employees', { select: 'id', limit: 1 })
    await read<{ id: string }>('embat_leads', { select: 'id', limit: 1 })
    return true
  } catch (error) {
    if (isMissingTable(error)) return false
    throw error
  }
}

async function hasSupabaseTables() {
  const ready = await (supabaseReady ??= probeSupabase())
  // En desarrollo se vuelve a mirar mientras falten: aplicar el esquema no debe pedir un reinicio.
  if (!ready && import.meta.dev) supabaseReady = undefined
  return ready
}

/** De dónde viene el pipeline ahora mismo, para decirlo en la pantalla sin adivinar. */
export async function leadsSource(): Promise<'supabase' | 'local'> {
  return (await hasSupabaseTables()) ? 'supabase' : 'local'
}

export async function listLeadRows(): Promise<LeadRow[]> {
  if (await hasSupabaseTables()) {
    const read = companyDataReader()
    return read<LeadRow>('embat_leads', {
      select: 'id,company_id,status,assigned_to,signal,email_draft,created_at',
      order: 'created_at.desc',
      limit: 200,
    })
  }
  const state = await readFileState()
  return [...state.leads].sort((a, b) => b.created_at.localeCompare(a.created_at))
}

export async function listLeads(): Promise<EmbatLead[]> {
  if (await hasSupabaseTables()) return hydrateLeads(await listLeadRows())
  const state = await readFileState()
  return hydrateLeads(state.leads, state.employees)
}

function pickAssignee(employees: Employee[], open: LeadRow[]) {
  const pool = commercials(employees)
  const load = pool.map((employee) => ({
    id: employee.id,
    open: open.filter((row) => row.assigned_to === employee.id && row.status !== 'cerrado').length,
  }))
  load.sort((a, b) => a.open - b.open || a.id.localeCompare(b.id))
  return load[0]!.id
}

export async function openLeadFor(companyId: string): Promise<{ lead: EmbatLead; alreadyOpen: boolean }> {
  const openStatuses: LeadStatus[] = ['nuevo', 'contactado', 'reunion']
  if (await hasSupabaseTables()) {
    const read = companyDataReader()
    const existing = await read<LeadRow>('embat_leads', {
      select: 'id,company_id,status,assigned_to,signal,email_draft,created_at',
      company_id: `eq.${companyId}`,
      status: 'in.(nuevo,contactado,reunion)',
      limit: 1,
    })
    if (existing[0]) {
      const [lead] = await hydrateLeads(existing)
      return { lead: lead!, alreadyOpen: true }
    }
    const employees = commercials(await listEmployees())
    const open = await read<LeadRow>('embat_leads', {
      select: 'id,company_id,status,assigned_to,signal,email_draft,created_at',
      status: 'in.(nuevo,contactado,reunion)',
      limit: 500,
    })
    const created = await companyDataWrite<LeadRow>('POST', 'embat_leads', {}, {
      company_id: companyId,
      status: 'nuevo',
      assigned_to: pickAssignee(employees, open),
      signal: 'financiar',
      email_draft: FINANCING_EMAIL_DRAFT,
    })
    const [lead] = await hydrateLeads(created)
    return { lead: lead!, alreadyOpen: false }
  }

  const state = await readFileState()
  const existing = state.leads.find((row) => row.company_id === companyId && openStatuses.includes(row.status))
  if (existing) {
    const [lead] = await hydrateLeads([existing], state.employees)
    return { lead: lead!, alreadyOpen: true }
  }
  const row: LeadRow = {
    id: randomUUID(),
    company_id: companyId,
    status: 'nuevo',
    assigned_to: pickAssignee(state.employees, state.leads),
    signal: 'financiar',
    email_draft: FINANCING_EMAIL_DRAFT,
    created_at: new Date().toISOString(),
  }
  state.leads.unshift(row)
  await writeFileState(state)
  const [lead] = await hydrateLeads([row], state.employees)
  return { lead: lead!, alreadyOpen: false }
}

export async function patchLead(id: string, status: LeadStatus): Promise<EmbatLead> {
  if (await hasSupabaseTables()) {
    const updated = await companyDataWrite<LeadRow>(
      'PATCH',
      'embat_leads',
      { id: `eq.${id}` },
      { status, updated_at: new Date().toISOString() },
    )
    const [lead] = await hydrateLeads(updated)
    if (!lead) throw createError({ statusCode: 404, statusMessage: 'Aviso no encontrado' })
    return lead
  }
  const state = await readFileState()
  const row = state.leads.find((item) => item.id === id)
  if (!row) throw createError({ statusCode: 404, statusMessage: 'Aviso no encontrado' })
  row.status = status
  await writeFileState(state)
  const [lead] = await hydrateLeads([row], state.employees)
  return lead!
}
