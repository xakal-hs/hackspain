import type { LeadMutationResponse, LeadStatus } from '../../../../shared/types/embat'
import { patchLead } from '../../../utils/embatStore'

const STATUSES: LeadStatus[] = ['nuevo', 'contactado', 'reunion', 'cerrado']

export default defineEventHandler(async (event): Promise<LeadMutationResponse> => {
  const id = getRouterParam(event, 'id') || ''
  if (!/^[0-9a-f-]{36}$/i.test(id)) {
    throw createError({ statusCode: 400, statusMessage: 'Aviso inválido' })
  }
  const body = await readBody<{ status?: string }>(event)
  const status = body?.status as LeadStatus | undefined
  if (!status || !STATUSES.includes(status)) {
    throw createError({ statusCode: 400, statusMessage: 'Estado inválido' })
  }
  return { lead: await patchLead(id, status) }
})
