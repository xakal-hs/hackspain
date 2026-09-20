import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { scorePillars, groupScoreDrivers, formatContribution } from '../app/utils/scorePillars.ts'

const row = (feature, contribution, label = feature, display_value = '10 %') => ({ feature, contribution, label, display_value })

test('the five pillars and all feature assignments match the backend catalogue', () => {
  const source = readFileSync(new URL('../../backend/preprocessing.py', import.meta.url), 'utf8')
  const pillars = JSON.parse(source.match(/^PILLARS = (\[.*\])/m)[1])
  assert.deepEqual(scorePillars.map(p => p.id), pillars)
  const features = [...source.matchAll(/"([a-z0-9_]+)": dict\(pilar="([a-z]+)".*?label="([^"]+)"/g)]
  assert.equal(features.length, 18)
  for (const [, feature, pillar, label] of features) {
    const result = groupScoreDrivers([row(feature, 2, label)])
    assert.equal(result.pillars.find(p => p.drivers.length)?.id, pillar, feature)
    const legacy = groupScoreDrivers([{ label, contribution: 2, display_value: '1' }])
    assert.equal(legacy.pillars.find(p => p.drivers.length)?.id, pillar, label)
  }
})

test('sums signed full-precision contributions before display rounding, and sorts signals by magnitude', () => {
  const data = [row('runway', 1.26), row('lc_util', -.24), row('activity_trend', 3.23456)]
  const { pillars, additional } = groupScoreDrivers(data)
  assert.equal(pillars[0].contribution, 1.02)
  assert.equal(pillars[4].contribution, 3.23456)
  assert.equal(additional.drivers.length, 0)
  assert.deepEqual(pillars[0].drivers.map(d => d.feature), ['runway', 'lc_util'])
  assert.deepEqual(data.map(d => d.feature), ['runway', 'lc_util', 'activity_trend'])
  assert.equal(formatContribution(pillars[0].contribution), '+1,0')
})

test('zero contribution, a missing source value, and an absent pillar remain distinct', () => {
  const { pillars } = groupScoreDrivers([row('runway', 0), row('lc_util', 4.63321, 'Uso de líneas de crédito', 'sin dato')])
  assert.equal(pillars[0].contribution, 4.63321)
  assert.equal(pillars[0].drivers[1].contribution, 0)
  assert.equal(pillars[0].drivers[0].display_value, 'sin dato')
  assert.equal(pillars[1].contribution, null)
  assert.equal(groupScoreDrivers([]).pillars.length, 5)
  assert.equal(formatContribution(null), 'Sin contribución')
  assert.equal(formatContribution(0), '0,0')
  assert.equal(formatContribution(-0.001), '0,0')
})

test('rules and unrecognised features stay separate, preserving every contribution', () => {
  const data = [row('runway', 20), row('regla_liquidez', -6), row('new_feature', 2, 'Meses de caja'), row(undefined, 3, 'Varias señales a la vez')]
  const { pillars, additional } = groupScoreDrivers(data)
  assert.equal(pillars[0].contribution, 20)
  assert.equal(additional.contribution, -1)
  assert.equal(additional.drivers.length, 3)
  const total = pillars.reduce((sum, p) => sum + (p.contribution ?? 0), 0) + additional.contribution
  assert.equal(total, data.reduce((sum, d) => sum + d.contribution, 0))
})

test('an invalid contribution is not silently converted to zero or counted as a complete sum', () => {
  const { pillars } = groupScoreDrivers([row('runway', Number.NaN), row('lc_util', 3)])
  assert.equal(pillars[0].contribution, null)
  assert.equal(pillars[0].drivers.length, 2)
  assert.equal(formatContribution(Infinity), 'Sin contribución')
})
