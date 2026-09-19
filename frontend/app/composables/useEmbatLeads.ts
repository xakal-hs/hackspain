import type { LeadMutationResponse, LeadStatus } from '../../shared/types/embat'

export function useEmbatLeads() {
  async function patch(input: { id: string; status: LeadStatus }) {
    return $fetch<LeadMutationResponse>(`/api/embat/leads/${input.id}`, {
      method: 'PATCH',
      body: { status: input.status },
    })
  }
  return { patch }
}
