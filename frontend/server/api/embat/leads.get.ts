import type { LeadsResponse } from '../../../shared/types/embat'
import { listLeads } from '../../utils/embatStore'

export default defineEventHandler(async (): Promise<LeadsResponse> => {
  return { leads: await listLeads() }
})
