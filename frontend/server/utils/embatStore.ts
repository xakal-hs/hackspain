import { randomUUID } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { FINANCING_EMAIL_DRAFT } from './embatDraft'
import { hydrateLeads, type LeadRow } from './embatLeads'
import type { EmbatLead, LeadStatus } from '../../shared/types/embat'

interface Manager {
  id: string
  name: string
}

interface FileState {
  managers: Manager[]
  leads: LeadRow[]
}

const FILE = join(process.cwd(), '.data', 'embat-crm.json')
const SEED_MANAGERS: Manager[] = [
  { id: '11111111-1111-4111-8111-111111111111', name: 'Marta Gil' },
  { id: '22222222-2222-4222-8222-222222222222', name: 'Luis Navarro' },
  { id: '33333333-3333-4333-8333-333333333333', name: 'Elena Ortiz' },
]

const SEED_LEADS: Array<Pick<LeadRow, 'company_id' | 'status' | 'assigned_to'>> = [
  { company_id: 'COMP_0779', status: 'nuevo', assigned_to: SEED_MANAGERS[0]!.id },
  { company_id: 'COMP_0130', status: 'contactado', assigned_to: SEED_MANAGERS[1]!.id },
  { company_id: 'COMP_1155', status: 'reunion', assigned_to: SEED_MANAGERS[2]!.id },
]

function isMissingTable(error: unknown) {
  const payload = error as { statusCode?: number; status?: number; data?: { code?: string }; message?: string }
  const code = payload?.data?.code || ''
  const message = String(payload?.message || '')
  return code === 'PGRST205' || message.includes("Could not find the table") || payload?.statusCode === 404 || payload?.status === 404
}

async function readFileState(): Promise<FileState> {
  try {
    return JSON.parse(await readFile(FILE, 'utf8')) as FileState
  } catch {
    const leads: LeadRow[] = SEED_LEADS.map((row) => ({
      id: randomUUID(),
      company_id: row.company_id,
      status: row.status,
      assigned_to: row.assigned_to,
      signal: 'financiar',
      email_draft: FINANCING_EMAIL_DRAFT,
      created_at: new Date().toISOString(),
    }))
    const state = { managers: SEED_MANAGERS, leads }
    await mkdir(dirname(FILE), { recursive: true })
    await writeFile(FILE, JSON.stringify(state, null, 2))
    return state
  }
}

async function writeFileState(state: FileState) {
  await mkdir(dirname(FILE), { recursive: true })
  await writeFile(FILE, JSON.stringify(state, null, 2))
}

let supabaseReady: Promise<boolean> | undefined

async function hasSupabaseTables() {
  return (supabaseReady ??= (async () => {
    try {
      const read = companyDataReader()
      await read<{ id: string }>('embat_account_managers', { select: 'id', limit: 1 })
      return true
    } catch (error) {
      if (isMissingTable(error)) return false
      throw error
    }
  })())
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
  return hydrateLeads(state.leads, state.managers)
}

function pickAssignee(managers: Manager[], open: LeadRow[]) {
  const load = managers.map((manager) => ({
    id: manager.id,
    open: open.filter((row) => row.assigned_to === manager.id && row.status !== 'cerrado').length,
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
    const managers = await read<Manager>('embat_account_managers', { select: 'id,name', order: 'name.asc', limit: 20 })
    const open = await read<LeadRow>('embat_leads', {
      select: 'id,company_id,status,assigned_to,signal,email_draft,created_at',
      status: 'in.(nuevo,contactado,reunion)',
      limit: 500,
    })
    const created = await companyDataWrite<LeadRow>('POST', 'embat_leads', {}, {
      company_id: companyId,
      status: 'nuevo',
      assigned_to: pickAssignee(managers, open),
      signal: 'financiar',
      email_draft: FINANCING_EMAIL_DRAFT,
    })
    const [lead] = await hydrateLeads(created)
    return { lead: lead!, alreadyOpen: false }
  }

  const state = await readFileState()
  const existing = state.leads.find((row) => row.company_id === companyId && openStatuses.includes(row.status))
  if (existing) {
    const [lead] = await hydrateLeads([existing], state.managers)
    return { lead: lead!, alreadyOpen: true }
  }
  const row: LeadRow = {
    id: randomUUID(),
    company_id: companyId,
    status: 'nuevo',
    assigned_to: pickAssignee(state.managers, state.leads),
    signal: 'financiar',
    email_draft: FINANCING_EMAIL_DRAFT,
    created_at: new Date().toISOString(),
  }
  state.leads.unshift(row)
  await writeFileState(state)
  const [lead] = await hydrateLeads([row], state.managers)
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
  const [lead] = await hydrateLeads([row], state.managers)
  return lead!
}
