import { test } from 'node:test'
import assert from 'node:assert/strict'
import { blocks, inline } from '../app/utils/chatText.ts'
import { agentTools } from '../server/agent/tools.ts'
import { systemPrompt } from '../server/agent/prompt.ts'

const run = (t, input) => t.execute(input, { toolCallId: 't', messages: [] })

test('blocks separa párrafos, listas y negritas sin generar HTML', () => {
  const out = blocks('La nota es **61**.\n- caja: baja\n\n- cobros: lentos')
  assert.deepEqual(out.map(b => b.kind), ['p', 'li', 'li'])
  assert.deepEqual(out[0].inline, [
    { text: 'La nota es ' }, { text: '61', bold: true }, { text: '.' },
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

import { resolveModel } from '../server/agent/model.ts'

test('resolveModel: sin nada configurado no hay modelo', () => {
  assert.equal(resolveModel({}), null)
})

test('resolveModel: AGENT_BASE_URL manda sobre el Gateway y no exige clave (Ollama)', () => {
  const m = resolveModel({ agentBaseUrl: 'http://localhost:11434/v1/', agentModel: 'qwen3:8b', gatewayKey: 'x' })
  assert.equal(typeof m, 'object')
  assert.equal(m.modelId, 'qwen3:8b')
})

test('resolveModel: AGENT_BASE_URL sin AGENT_MODEL cuenta como no configurado', () => {
  assert.equal(resolveModel({ agentBaseUrl: 'http://localhost:11434/v1' }), null)
})

test('resolveModel: con clave del Gateway usa un id proveedor/modelo', () => {
  assert.equal(resolveModel({ gatewayKey: 'k' }), 'anthropic/claude-opus-5')
  assert.equal(resolveModel({ oidcToken: 't', agentModel: 'zai/glm-5.3' }), 'zai/glm-5.3')
})

import { chartsFromParts } from '../app/utils/chatCharts.ts'

test('chartsFromParts dibuja solo con datos de herramientas terminadas', () => {
  const tools = agentTools(async () => company)
  return run(tools.ficha_empresa, { company_id: 'COMP_0864' }).then((output) => {
    const parts = [
      { type: 'text', text: 'hola' },
      { type: 'tool-ficha_empresa', toolCallId: 'a', state: 'output-available', output },
      { type: 'tool-ficha_empresa', toolCallId: 'b', state: 'input-available' },
      { type: 'tool-buscar_cartera', toolCallId: 'c', state: 'output-available', output: { error: 'x' } },
    ]
    const charts = chartsFromParts(parts)
    // cifras y serie: las barras de señales y el radar de pilares se quitaron del panel
    assert.deepEqual(charts.map(c => c.id), ['a-resumen', 'a-serie'])
    assert.equal(charts[1].items.length, 12)
  })
})

test('blocks reconoce listas numeradas, títulos, citas y separadores', () => {
  const out = blocks('# Título\n1. uno\n2) dos\n> cita\n---')
  assert.deepEqual(out.map(b => b.kind), ['h', 'ol', 'ol', 'quote', 'hr'])
  assert.equal(out[2].n, '2')
})

test('buscar_cartera produce una tabla ordenable con cifras, sin inventar ninguna', async () => {
  const portfolio = {
    companies: Array.from({ length: 12 }, (_, i) => ({
      company_id: `COMP_00${10 + i}`, last_month: '2026-08', score: 20 + i * 5,
      band: i < 3 ? 'riesgo' : i < 8 ? 'vigilar' : 'sano', trend: 'deterioro',
      delta3_q50: -i, accion_label: 'Vigilar', alert: null, confidence: 0.9,
      pillars: { liquidez: 40 + i, rentabilidad: null, solvencia: 60, disciplina: 70, estabilidad: 55 },
    })),
  }
  const tools = agentTools(async () => portfolio)
  const out = await run(tools.buscar_cartera, { orden: 'peor_nota', limite: 8 })
  const charts = chartsFromParts([{ type: 'tool-buscar_cartera', toolCallId: 'x', state: 'output-available', output: out }])
  // una sola tabla: las barras apiladas debajo solo repetían la columna de 3 meses
  assert.equal(charts.length, 1)
  const [tabla] = charts

  assert.equal(tabla.kind, 'table')
  assert.equal(tabla.rows.length, 8)
  // empresa, nota, banda y los cinco pilares del score
  assert.deepEqual(tabla.columns.map(c => c.key), ['company_id', 'nota', 'liquidez', 'rentabilidad', 'solvencia', 'disciplina', 'estabilidad'])
  assert.equal(tabla.rows[0].liquidez, 40)
  // un pilar sin dato viaja como null: la celda dice «sin dato», no pinta un cero
  assert.equal(tabla.rows[0].rentabilidad, null)
  // la tira de cifras se deriva de las filas, no la escribe el modelo
  assert.deepEqual(tabla.stats.map(s => s.label), ['Empresas', 'Nota media', 'En riesgo', 'Empeorando'])
  assert.equal(tabla.stats[0].value, '8')
  assert.equal(tabla.stats[2].value, '3 (38%)')
  // la confianza viaja como porcentaje entero, que es como la pinta la celda
  assert.equal(tabla.rows[0].confianza, 90)
})

test('la tabla enseña con qué criterio se pidió la lista', async () => {
  const portfolio = { companies: [{ company_id: 'COMP_0001', last_month: '2026-08', score: 30, band: 'riesgo', trend: 'deterioro', delta3_q50: -4, accion_label: 'No prestar', alert: null, confidence: 0.8 }] }
  const tools = agentTools(async () => portfolio)
  const out = await run(tools.buscar_cartera, { banda: 'riesgo', orden: 'mayor_caida', limite: 5 })
  assert.deepEqual(out.criterio, { banda: 'riesgo', orden: 'mayor_caida', limite: 5 })
  const [t] = chartsFromParts([{ type: 'tool-buscar_cartera', toolCallId: 'y', state: 'output-available', output: out }])
  assert.deepEqual(t.filters.map(f => f.label), ['Banda riesgo', 'Mayor caída primero', 'Máximo 5'])
})

test('dos búsquedas seguidas dejan una sola tabla: la última', () => {
  const row = (id, score) => ({ company_id: id, last_month: '2026-08', score, band: 'sano', trend: 'mejora', delta3_q50: 1, accion_label: 'Prestar', alert: null, confidence: 0.9, pillars: { liquidez: 50 } })
  const mk = (id, empresas, orden) => ({
    type: 'tool-buscar_cartera', toolCallId: id, state: 'output-available',
    output: { total_en_cartera: 1286, criterio: { banda: null, orden, limite: 15 }, empresas },
  })
  const charts = chartsFromParts([
    mk('a', [{ company_id: 'COMP_0001', mes: '2026-08', nota: 2, banda: 'riesgo', tendencia: 'deterioro', cambio_3_meses: -9, accion: 'No prestar', confianza: 0.9, pilares: {} }], 'peor_nota'),
    mk('b', [{ company_id: 'COMP_0364', mes: '2026-08', nota: 87, banda: 'sano', tendencia: 'mejora', cambio_3_meses: 31, accion: 'Prestar', confianza: 0.98, pilares: {} }], 'mayor_mejora'),
  ])
  assert.equal(charts.length, 1)
  assert.equal(charts[0].rows[0].company_id, 'COMP_0364')
  assert.equal(charts[0].filters[1].label, 'Mayor mejora primero')
})

test('con tabla, la tabla es la respuesta: la ficha de paso no cuelga debajo', async () => {
  const portfolio = { companies: [{ company_id: 'COMP_0001', last_month: '2026-08', score: 30, band: 'riesgo', trend: 'deterioro', delta3_q50: -4, accion_label: 'No prestar', alert: null, confidence: 0.8 }] }
  const cartera = await run(agentTools(async () => portfolio).buscar_cartera, { orden: 'peor_nota', limite: 8 })
  const ficha = await run(agentTools(async () => company).ficha_empresa, { company_id: 'COMP_0864' })
  const charts = chartsFromParts([
    { type: 'tool-buscar_cartera', toolCallId: 'a', state: 'output-available', output: cartera },
    { type: 'tool-ficha_empresa', toolCallId: 'b', state: 'output-available', output: ficha },
  ])
  assert.deepEqual(charts.map(c => c.kind), ['table'])
})

test('inline reconoce cursiva, tachado, código y marcado anidado', () => {
  assert.deepEqual(inline('un *bache*, no ~~caída~~ de `runway`'), [
    { text: 'un ' }, { text: 'bache', italic: true }, { text: ', no ' },
    { text: 'caída', strike: true }, { text: ' de ' }, { text: 'runway', code: true },
  ])
  assert.deepEqual(inline('**muy *claro* hoy**'), [{ text: 'muy ', bold: true }, { text: 'claro', bold: true, italic: true }, { text: ' hoy', bold: true }])
  // dentro del código no se busca marcado: los asteriscos son literales
  assert.deepEqual(inline('`a**b`'), [{ text: 'a**b', code: true }])
})

test('un guion bajo dentro de una palabra no es cursiva', () => {
  assert.deepEqual(inline('COMP_0364 y ar_late_share'), [{ text: 'COMP_0364 y ar_late_share' }])
})

test('el marcador a medio escribir no enseña los asteriscos mientras llega el stream', () => {
  assert.deepEqual(blocks('La nota es **6')[0].inline, [{ text: 'La nota es 6' }])
  // ya cerrado, se pinta en negrita
  assert.deepEqual(blocks('La nota es **61**')[0].inline, [{ text: 'La nota es ' }, { text: '61', bold: true }])
})

test('blocks anida las sublistas y guarda el nivel de los títulos', () => {
  const out = blocks('# Uno\n## Dos\n- padre\n  - hija\n1. uno\n   2. dos')
  assert.deepEqual(out.map(b => [b.kind, b.depth]), [['h', 0], ['h', 1], ['li', 0], ['li', 1], ['ol', 0], ['ol', 1]])
})
