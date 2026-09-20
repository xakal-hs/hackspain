import type { LeadsResponse } from '../../../shared/types/embat'
import { leadsSource, listLeads } from '../../utils/embatStore'

export default defineEventHandler(async (): Promise<LeadsResponse> => {
  const [leads, source] = await Promise.all([listLeads(), leadsSource()])
  return { leads, source }
})
