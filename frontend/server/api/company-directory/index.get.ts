import type { CompanyDirectorySource, CompanyIdentity } from '../../../shared/types/company'

interface FeaturedCompany {
  company_id: string
  display_name: string
  sector: string
}

export default defineEventHandler(async (event): Promise<CompanyIdentity[]> => {
  const requested = String(getQuery(event).source || 'companies')
  if (requested !== 'companies' && requested !== 'featured_companies')
    throw createError({ statusCode: 400, statusMessage: 'Origen de empresas inválido' })
  const source = requested as CompanyDirectorySource

  if (source === 'featured_companies') {
    const featured = await companyDataPages<FeaturedCompany>(
      'featured_companies',
      'company_id,display_name,sector',
      'display_order.asc',
    )
    if (!featured.length) return []

    const read = companyDataReader()
    const identities = await read<Omit<CompanyIdentity, 'display_name' | 'top_sector'>>(
      'companies',
      {
        select: 'company_id,group_id,country,currency,erp',
        company_id: `in.(${featured.map(row => row.company_id).join(',')})`,
        order: 'company_id.asc',
        limit: 100,
      },
    )
    const identityById = new Map(identities.map(row => [row.company_id, row]))
    return featured.map(row => ({
      company_id: row.company_id,
      display_name: row.display_name,
      top_sector: row.sector,
      group_id: identityById.get(row.company_id)?.group_id ?? null,
      country: identityById.get(row.company_id)?.country ?? null,
      currency: identityById.get(row.company_id)?.currency ?? null,
      erp: identityById.get(row.company_id)?.erp ?? null,
    }))
  }

  const [companies, profiles] = await Promise.all([
    companyDataPages<Omit<CompanyIdentity, 'top_sector'>>('companies', 'company_id,group_id,country,currency,erp'),
    companyDataPages<Pick<CompanyIdentity, 'company_id' | 'top_sector'>>('company_business_profile', 'company_id,top_sector'),
  ])
  const sectors = new Map(profiles.map(row => [row.company_id, row.top_sector]))
  return companies.map(company => ({ ...company, top_sector: sectors.get(company.company_id) ?? null }))
})
