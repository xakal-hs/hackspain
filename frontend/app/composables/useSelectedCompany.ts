import { useQuery } from '@tanstack/vue-query'
import type { CompanyDirectorySource, CompanyIdentity, CompanyDetail } from '../../shared/types/company'

export function useSelectedCompany() {
  // Sin elección previa, la demo abre en el caso del excedente de caja (shared/demoCases.ts).
  const cookie = useCookie<string>('xray-company', { default: () => 'COMP_0835', sameSite: 'lax' })
  const selectedId = useState<string>('selected-company-id', () => cookie.value)
  watch(selectedId, value => { cookie.value = value })
  const sourceCookie = useCookie<CompanyDirectorySource>('xray-company-source', {
    default: () => 'companies',
    sameSite: 'lax',
  })
  const source = computed<CompanyDirectorySource>({
    get: () => sourceCookie.value === 'featured_companies' ? 'featured_companies' : 'companies',
    set: value => { sourceCookie.value = value },
  })
  const directory = useQuery({
    queryKey: computed(() => ['company-directory', source.value]),
    queryFn: () => $fetch<CompanyIdentity[]>('/api/company-directory', { query: { source: source.value } }),
    staleTime: 5 * 60 * 1000,
  })
  const companies = computed(() => directory.data.value ?? [])
  watch(companies, rows => {
    if (rows.length && !rows.some(row => row.company_id === selectedId.value)) selectedId.value = rows[0]!.company_id
  }, { immediate: true })
  const company = computed(() => companies.value.find(row => row.company_id === selectedId.value))
  const detail = useQuery({
    queryKey: computed(() => ['company-detail', selectedId.value]),
    queryFn: () => $fetch<CompanyDetail>(`/api/company-directory/${encodeURIComponent(selectedId.value)}`),
    enabled: computed(() => !!company.value),
    staleTime: 60 * 1000,
  })
  const latest = computed(() => detail.data.value?.panel.at(-1))
  const health = computed(() => detail.data.value?.health.at(-1))
  const name = computed(() => company.value?.display_name || company.value?.company_id || selectedId.value)
  const sector = computed(() => company.value?.top_sector || 'Sector sin clasificar')
  return { selectedId, source, directory, companies, company, detail, latest, health, name, sector }
}
