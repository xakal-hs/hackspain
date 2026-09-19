import type { CompanyHealth, SectorHealth } from '../../shared/types/company'

export type SectorStatistic = 'score_mean' | 'score_median'

/** Join by calendar month, never by row position; missing values are not zero. */
export function alignSectorHealth(company: CompanyHealth[], sector: SectorHealth[], statistic: SectorStatistic) {
  const byMonth = new Map(sector.map(row => [row.month.slice(0, 7), row]))
  return company.flatMap(row => {
    const month = row.month.slice(0, 7)
    const benchmark = byMonth.get(month)
    const value = benchmark?.[statistic]
    if (!benchmark || value == null || !Number.isFinite(value) || !Number.isFinite(row.health_score)) return []
    return [{ month, company: row.health_score, sector: value, n: benchmark.n }]
  }).sort((a, b) => a.month.localeCompare(b.month))
}
