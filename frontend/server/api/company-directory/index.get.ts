import type { CompanyIdentity } from '../../../shared/types/company'

export default defineEventHandler(async (): Promise<CompanyIdentity[]> => {
  const [companies, profiles] = await Promise.all([
    companyDataPages<Omit<CompanyIdentity, 'top_sector'>>('companies', 'company_id,group_id,country,currency,erp'),
    companyDataPages<Pick<CompanyIdentity, 'company_id' | 'top_sector'>>('company_business_profile', 'company_id,top_sector'),
  ])
  const sectors = new Map(profiles.map(row => [row.company_id, row.top_sector]))
  return companies.map(company => ({ ...company, top_sector: sectors.get(company.company_id) ?? null }))
})
