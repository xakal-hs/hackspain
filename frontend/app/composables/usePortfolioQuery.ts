import { useQuery } from '@tanstack/vue-query'
import type { PortfolioResponse } from '~/types/portfolio'

export function usePortfolioQuery() {
  return useQuery({
    queryKey: ['portfolio'],
    queryFn: () => $fetch<PortfolioResponse>('/api/companies'),
  })
}
