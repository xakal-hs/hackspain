import type { LeadMutationResponse } from '../../../shared/types/embat'
import { openLeadFor } from '../../utils/embatStore'

export default defineEventHandler(async (event): Promise<LeadMutationResponse> => {
  const body = await readBody<{ company_id?: string }>(event)
  const companyId = String(body?.company_id || '')
  if (!/^COMP_\d{4}$/.test(companyId)) {
    throw createError({ statusCode: 400, statusMessage: 'Empresa inválida' })
  }
  const result = await openLeadFor(companyId)
  return { lead: result.lead, alreadyOpen: result.alreadyOpen || undefined }
})
