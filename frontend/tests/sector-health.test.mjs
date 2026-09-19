import { test } from 'node:test'
import assert from 'node:assert/strict'
import { alignSectorHealth } from '../app/utils/sectorHealth.ts'

const company = [
  { month: '2026-03-01', health_score: 60 },
  { month: '2026-01-01', health_score: 0 },
  { month: '2026-02-01', health_score: 40 },
]
const sector = [
  { month: '2026-02', n: 12, score_mean: null, score_median: 39 },
  { month: '2026-03', n: 14, score_mean: 50, score_median: 55 },
  { month: '2026-01', n: 10, score_mean: 0, score_median: 5 },
  { month: '2025-12', n: 9, score_mean: 30, score_median: 31 },
]
test('joins calendar months despite different ordering, lengths and date formats; retains zero', () => {
  assert.deepEqual(alignSectorHealth(company, sector, 'score_mean'), [
    { month: '2026-01', company: 0, sector: 0, n: 10 },
    { month: '2026-03', company: 60, sector: 50, n: 14 },
  ])
})
test('median selects its own monthly values and coverage without shifting company scores', () => {
  assert.deepEqual(alignSectorHealth(company, sector, 'score_median'), [
    { month: '2026-01', company: 0, sector: 5, n: 10 },
    { month: '2026-02', company: 40, sector: 39, n: 12 },
    { month: '2026-03', company: 60, sector: 55, n: 14 },
  ])
})
test('missing or invalid series never produce a fake comparison', () => {
  assert.deepEqual(alignSectorHealth([], sector, 'score_mean'), [])
  assert.deepEqual(alignSectorHealth(company, [], 'score_mean'), [])
  assert.deepEqual(alignSectorHealth([{ month: '2026-01', health_score: NaN }], sector, 'score_mean'), [])
})
