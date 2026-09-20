import { tool } from 'ai'
import { z } from 'zod'

/**
 * Herramientas de solo lectura del agente. Cada una es un envoltorio fino de una ruta de este
 * mismo servidor, que a su vez sirve lo publicado en Supabase: el agente nunca calcula, solo
 * lee lo que el modelo ya calculó. Los errores vuelven como `{ error }` y no como excepción,
 * para que el modelo pueda decirlo en vez de romper la conversación.
 */
export type Fetcher = <T>(path: string, query?: Record<string, string | number | undefined>) => Promise<T>

/** Llamada interna a las rutas de Nitro: no sale a la red ni necesita saber la URL pública. */
export function localFetcher(): Fetcher {
  // Nitro tipa `$fetch` por ruta literal; estas se construyen con el id de la empresa.
  const call = $fetch as unknown as (url: string, opts: object) => Promise<any>
  return (path, query) => call(path, { query, timeout: 20000 })
}

const round = (n: number | null | undefined, d = 1) =>
  n == null || !Number.isFinite(n) ? null : Number(n.toFixed(d))

const companyId = z.string().regex(/^COMP_\d{4}$/, 'formato COMP_0000').describe('Identificador de empresa, p. ej. COMP_0864')
const month = z.string().regex(/^\d{4}-\d{2}(-\d{2})?$/).optional().describe('Mes en formato AAAA-MM. Si se omite, el último mes con datos')

async function safe<T>(run: () => Promise<T>) {
  try {
    return await run()
  } catch (error: any) {
    const status = error?.statusCode ?? error?.status
    if (status === 404) return { error: 'No hay datos para esa empresa o ese mes.' }
    return { error: 'El servicio de datos de X-Ray no ha respondido.' }
  }
}

interface Signal { label: string; pillar: string; weight: number; points: number; value_text: string }
interface SeriesPoint { month: string; score: number; band: string }

export function agentTools(get: Fetcher) {
  return {
    ficha_empresa: tool({
      description:
        'Ficha de una empresa en su último mes: nota 0-100, banda, tendencia, decisión del prestamista con sus vetos, ' +
        'las señales que más suman y más restan, y la serie de notas de los últimos 12 meses. Empieza por aquí.',
      inputSchema: z.object({ company_id: companyId }),
      execute: ({ company_id }) => safe(async () => {
        const c = await get<any>(`/api/companies/${company_id}`)
        const signals: Signal[] = c.signals ?? []
        const view = (s: Signal) => ({ senal: s.label, pilar: s.pillar, peso: round(s.weight, 3), puntos: round(s.points, 2), valor: s.value_text })
        const series: SeriesPoint[] = c.series ?? []
        return {
          company_id,
          mes: c.month ?? series.at(-1)?.month,
          nota: c.score, banda: c.band, tendencia: c.trend, cambio_3_meses: c.delta3,
          confianza: c.confidence, cobertura_datos: c.coverage,
          // fracción del peso con valores fuera del rango de entrenamiento: no cambia la
          // nota, baja la confianza. Es el «esta empresa no se parece a lo que vi».
          fuera_de_rango: c.ood_share, avisos_de_riesgo: c.risk_flags,
          decision: {
            accion: c.decision?.accion_label ?? c.decision?.accion,
            vetos: c.decision?.vetos, avisos: c.decision?.avisos,
            razones: (c.decision?.razones ?? []).map((r: any) => ({ etiqueta: r.etiqueta, texto: r.texto })),
            importe_max_meses_de_gasto: c.decision?.importe_max_meses,
          },
          pilares: c.pillars,
          senales_que_mas_restan: signals.slice(0, 4).map(view),
          senales_que_mas_suman: signals.slice(-4).reverse().map(view),
          serie_nota_12_meses: series.slice(-12).map(p => ({ mes: p.month, nota: p.score, banda: p.band })),
        }
      }),
    }),

    explicar_mes: tool({
      description:
        'Por qué cambió la nota de un mes al anterior: el cambio total y cuántos puntos aportó cada señal. ' +
        'Las aportaciones suman el cambio; lo que no explican las señales aparece como «Reglas y límites de escala». ' +
        'Úsala para "¿por qué bajó en marzo?".',
      inputSchema: z.object({ company_id: companyId, month }),
      execute: ({ company_id, month }) => safe(async () => {
        const e = await get<any>(`/api/companies/${company_id}/explain`, { month })
        return {
          company_id, mes: e.month, mes_anterior: e.prev_month, cambio_total_puntos: round(e.delta, 2),
          resumen: e.summary_text,
          aportaciones: (e.contributions ?? []).slice(0, 8).map((c: any) => ({
            senal: c.label, pilar: c.pillar, puntos: round(c.delta_points, 2),
            valor_antes: c.value_prev, valor_ahora: c.value_now, texto: c.text,
          })),
        }
      }),
    }),

    prevision_tesoreria: tool({
      description:
        'Previsión de caja publicada y acción de tesorería: colocar excedente, buscar financiación o ninguna. ' +
        'No es una aprobación de crédito.',
      inputSchema: z.object({ company_id: companyId }),
      execute: ({ company_id }) => safe(async () => {
        const r = await get<any>(`/api/flujo/${company_id}`)
        return {
          company_id,
          corte_de_datos: r.snapshot || null,
          moneda: r.currency || null,
          accion_tesoreria: r.action || null,
          caja_actual: round(r.forecast?.cash, 2),
          meses_previstos: r.forecast?.months?.slice(0, 6) ?? [],
          rotura_de_caja: r.forecast?.rotura ?? null,
          excedente: r.forecast?.excedente ?? null,
          alcance: 'Acción de tesorería; no es una aprobación de crédito.',
        }
      }),
    }),

    decision_prestamista: tool({
      description: 'Decisión de prestar / vigilar / no prestar en un mes concreto, con los vetos y avisos que la motivan.',
      inputSchema: z.object({ company_id: companyId, month }),
      execute: ({ company_id, month }) => safe(async () => {
        const d = await get<any>(`/api/companies/${company_id}/decision`, { month })
        return {
          company_id, mes: d.month, accion: d.accion_label ?? d.accion, vetos: d.vetos, avisos: d.avisos,
          razones: (d.razones ?? []).map((r: any) => ({ etiqueta: r.etiqueta, texto: r.texto })),
          importe_max_meses_de_gasto: d.importe_max_meses,
        }
      }),
    }),

    buscar_cartera: tool({
      description:
        'Lista empresas de la cartera con nota, banda, tendencia y acción, para responder "cuáles están peor", "cuáles empeoran" o comparar. ' +
        'Devuelve como mucho 15.',
      inputSchema: z.object({
        banda: z.enum(['sano', 'vigilar', 'riesgo']).optional(),
        orden: z.enum(['peor_nota', 'mayor_caida', 'mayor_mejora']).default('peor_nota'),
        limite: z.number().int().min(1).max(15).default(8),
      }),
      execute: ({ banda, orden, limite }) => safe(async () => {
        const [r, curated] = await Promise.all([
          get<{ companies: any[] }>('/api/companies', { band: banda }),
          get<{ companies: any[] }>('/api/embat/caja'),
        ])
        const curatedIds = new Set(curated.companies.map(company => company.company_id))
        const companies = r.companies.filter(company => curatedIds.has(company.company_id))
        const key = {
          peor_nota: (a: any, b: any) => a.score - b.score,
          mayor_caida: (a: any, b: any) => a.delta3_q50 - b.delta3_q50,
          mayor_mejora: (a: any, b: any) => b.delta3_q50 - a.delta3_q50,
        }[orden]
        return {
          total_en_cartera: companies.length,
          criterio: { banda: banda ?? null, orden, limite },
          empresas: [...companies].sort(key).slice(0, limite).map(c => ({
            company_id: c.company_id, mes: c.last_month, nota: c.score, banda: c.band, tendencia: c.trend,
            cambio_3_meses: c.delta3_q50, accion: c.accion_label, alerta: c.alert, confianza: c.confidence,
            pilares: c.pillars,
          })),
        }
      }),
    }),

    como_funciona_el_score: tool({
      description:
        'Cómo se construye la nota: los pesos por señal, las bandas (sano / vigilar / riesgo) y las anclas de evento. ' +
        'Úsala cuando pregunten qué mide X-Ray o por qué una señal pesa más que otra.',
      inputSchema: z.object({}),
      execute: () => safe(async () => {
        const m = await get<any>('/api/model')
        return {
          version: m.score_version, pesos_por_senal: m.weights, bandas: m.bands,
          escala: m.scale, anclas_de_evento: m.anclas,
          significado_de_las_senales: Object.fromEntries(
            Object.entries(m.features ?? {}).map(([k, v]: [string, any]) => [k, { etiqueta: v.label, pilar: v.pilar, formula: v.formula }]),
          ),
        }
      }),
    }),

    catalogo_de_vetos: tool({
      description: 'Los hechos de hoy que mandan sobre la nota (vetos): cuáles bloquean el préstamo, cuáles se pueden levantar con un documento.',
      inputSchema: z.object({}),
      execute: () => safe(async () => {
        const v = await get<any>('/api/vetos')
        return { vetos: (v.vetos ?? []).map((x: any) => ({ codigo: x.codigo, etiqueta: x.etiqueta, texto: x.texto, bloquea: x.bloquea, levantable: x.levantable })) }
      }),
    }),
  }
}

export type AgentTools = ReturnType<typeof agentTools>
