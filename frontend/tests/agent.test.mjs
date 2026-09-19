import { test } from 'node:test'
import assert from 'node:assert/strict'
import { blocks } from '../app/utils/chatText.ts'
import { agentTools } from '../server/agent/tools.ts'
import { systemPrompt } from '../server/agent/prompt.ts'

const run = (t, input) => t.execute(input, { toolCallId: 't', messages: [] })

test('blocks separa párrafos, listas y negritas sin generar HTML', () => {
  const out = blocks('La nota es **61**.\n- caja: baja\n\n- cobros: lentos')
  assert.deepEqual(out.map(b => b.kind), ['p', 'li', 'li'])
  assert.deepEqual(out[0].inline, [
    { text: 'La nota es ', bold: false }, { text: '61', bold: true }, { text: '.', bold: false },
  ])
})

test('blocks no interpreta etiquetas: el texto del modelo queda como texto', () => {
  const [b] = blocks('<img src=x onerror=alert(1)>')
  assert.equal(b.inline[0].text, '<img src=x onerror=alert(1)>')
})

const company = {
  group_id: 'GROUP_0198', score: 68, band: 'vigilar', trend: 'deterioro', delta3: -8.4, confidence: 0.9, coverage: 1,
  ood_features: [], pillars: { liquidez: 40 },
  decision: { accion: 'vigilar', accion_label: 'Vigilar', vetos: [], avisos: ['x'], razones: [{ etiqueta: 'a', texto: 'b', codigo: 'c' }], importe_max_meses: null },
  series: Array.from({ length: 20 }, (_, i) => ({ month: `2025-${String((i % 12) + 1).padStart(2, '0')}`, score: 50 + i, band: 'vigilar' })),
  signals: Array.from({ length: 10 }, (_, i) => ({ label: `s${i}`, pillar: 'p', weight: 0.1, points: i - 5, value_text: `${i}` })),
}

test('ficha_empresa recorta la ficha: 12 meses y 4+4 señales, de las que más restan a las que más suman', async () => {
  const seen = []
  const tools = agentTools(async (path) => { seen.push(path); return company })
  const r = await run(tools.ficha_empresa, { company_id: 'COMP_0864' })
  assert.deepEqual(seen, ['/api/companies/COMP_0864'])
  assert.equal(r.serie_nota_12_meses.length, 12)
  assert.deepEqual(r.senales_que_mas_restan.map(s => s.senal), ['s0', 's1', 's2', 's3'])
  assert.deepEqual(r.senales_que_mas_suman.map(s => s.senal), ['s9', 's8', 's7', 's6'])
  assert.equal(r.decision.accion, 'Vigilar')
})

test('una empresa inexistente vuelve como error legible, no como excepción', async () => {
  const tools = agentTools(async () => { throw { statusCode: 404 } })
  const r = await run(tools.explicar_mes, { company_id: 'COMP_9999' })
  assert.match(r.error, /No hay datos/)
})

test('un backend caído se dice como tal', async () => {
  const tools = agentTools(async () => { throw new Error('ECONNREFUSED') })
  const r = await run(tools.buscar_cartera, { orden: 'peor_nota', limite: 3 })
  assert.match(r.error, /no ha respondido/)
})

test('buscar_cartera ordena por mayor caída y respeta el límite', async () => {
  const rows = [
    { company_id: 'A', score: 80, delta3_q50: 2 }, { company_id: 'B', score: 60, delta3_q50: -9 },
    { company_id: 'C', score: 40, delta3_q50: -3 },
  ]
  const tools = agentTools(async () => ({ companies: rows }))
  const r = await run(tools.buscar_cartera, { orden: 'mayor_caida', limite: 2 })
  assert.deepEqual(r.empresas.map(e => e.company_id), ['B', 'C'])
  assert.equal(r.total_en_cartera, 3)
})

test('los identificadores se validan antes de tocar el backend', () => {
  const tools = agentTools(async () => ({}))
  assert.equal(tools.ficha_empresa.inputSchema.safeParse({ company_id: '../etc/passwd' }).success, false)
  assert.equal(tools.ficha_empresa.inputSchema.safeParse({ company_id: 'COMP_0864' }).success, true)
})

test('el prompt lleva la empresa abierta y la regla de no inventar cifras', () => {
  const p = systemPrompt({ role: 'banco', companyId: 'COMP_0864' })
  assert.match(p, /COMP_0864/)
  assert.match(p, /sale de una herramienta/)
  assert.match(p, /No decides préstamos/)
})
