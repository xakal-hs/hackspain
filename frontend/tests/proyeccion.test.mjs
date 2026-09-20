import { test } from 'node:test'
import assert from 'node:assert/strict'
import { HORIZON, MIN_HISTORY, PHI, holtDamped, projectScore, trailingRun } from '../shared/proyeccion.ts'

const monthly = (values, from = 1) => values.map((value, i) => ({ month: `2026-${String(from + i).padStart(2, '0')}`, value }))

test('a flat series stays flat: no trend, nothing to extrapolate', () => {
  assert.deepEqual(holtDamped([50, 50, 50, 50, 50]), [50, 50, 50])
})

test('a rising series keeps rising, but the slope is damped, never multiplied by the horizon', () => {
  const ahead = holtDamped([50, 52, 54, 56, 58])
  assert.equal(ahead.length, HORIZON)
  assert.ok(ahead[0] > 58, 'el primer mes previsto sigue subiendo')
  assert.ok(ahead[0] < ahead[1] && ahead[1] < ahead[2], 'la línea sigue subiendo')
  // Con pendiente 2 y phi 0,8 el techo a 3 meses es 2·(0,8+0,64+0,512) ≈ 3,9, no 6.
  assert.ok(ahead[2] - ahead[0] < 2 * (PHI + PHI ** 2), 'los pasos se van acortando')
  assert.ok(ahead[2] < 58 + 2 * HORIZON, 'no extrapola como una recta sin amortiguar')
})

test('a falling series is projected downwards, symmetrically', () => {
  const up = holtDamped([50, 52, 54, 56, 58])
  const down = holtDamped([58, 56, 54, 52, 50])
  assert.deepEqual(down.map(v => Math.round((108 - v) * 1e6) / 1e6), up.map(v => Math.round(v * 1e6) / 1e6))
})

test('the level is anchored to the last published score, so a drop is never projected upwards', () => {
  // La forma real de COMP_0790: meses planos y altos y una caída seca en el último.
  const ahead = holtDamped([93.9, 93.0, 92.6, 89.4])
  assert.ok(ahead[0] < 89.4, `la previsión arranca por debajo del último mes, no en ${ahead[0]}`)
  assert.ok(ahead.every((value, i) => i === 0 || value <= ahead[i - 1]), 'sigue bajando')
})

test('the projection is clamped to the 0-100 range of the score', () => {
  assert.ok(holtDamped([70, 80, 90, 97, 100]).every(v => v <= 100))
  assert.ok(holtDamped([30, 20, 10, 3, 0]).every(v => v >= 0))
})

test('short history yields no projection instead of a guess', () => {
  assert.deepEqual(holtDamped(Array(MIN_HISTORY - 1).fill(50)), [])
  assert.deepEqual(projectScore(monthly([50, 50, 50])), [])
  assert.deepEqual(projectScore([]), [])
})

test('projected months follow the last real month and roll over the year', () => {
  const ahead = projectScore(monthly([50, 51, 52, 53], 9))
  assert.deepEqual(ahead.map(point => point.month), ['2027-01', '2027-02', '2027-03'])
})

test('a calendar gap truncates the series: only the final consecutive run is smoothed', () => {
  const run = trailingRun([
    { month: '2025-01-01', value: 10 },
    { month: '2025-02-01', value: 11 },
    { month: '2025-09-01', value: 40 },
    { month: '2025-10-01', value: 41 },
  ])
  assert.deepEqual(run.map(row => row.value), [40, 41])
})

test('unordered months and null values never shift or zero the series', () => {
  const ahead = projectScore([
    { month: '2026-03', value: 54 },
    { month: '2026-01', value: 50 },
    { month: '2026-05', value: null },
    { month: '2026-04', value: 56 },
    { month: '2026-02', value: 52 },
  ])
  assert.deepEqual(ahead.map(point => point.month), ['2026-05', '2026-06', '2026-07'])
  assert.ok(ahead.every(point => point.value > 56))
})
