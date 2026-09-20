import { convertToModelMessages, isStepCount, streamText, type UIMessage } from 'ai'
import { agentTools, localFetcher } from '../agent/tools'
import { resolveModel } from '../agent/model'
import { systemPrompt, type AgentContext } from '../agent/prompt'

interface ChatBody extends AgentContext {
  messages: UIMessage[]
}

const MAX_MESSAGES = 30

export default defineEventHandler(async (event) => {
  /* Ocultar el botón no cierra la puerta: la ruta se puede llamar a mano desde la vista de
     empresa, y las herramientas leen cualquier empresa de la cartera. Manda la sesión. */
  if (getCookie(event, 'xray-demo-role') !== 'embat')
    throw createError({ statusCode: 403, statusMessage: 'Forbidden', message: 'El asistente solo está disponible en la vista de Embat' })

  const body = await readBody<ChatBody>(event)
  if (!Array.isArray(body?.messages) || !body.messages.length)
    throw createError({ statusCode: 400, statusMessage: 'Faltan mensajes' })
  if (!['empresa', 'embat'].includes(body.role ?? ''))
    throw createError({ statusCode: 400, statusMessage: 'Rol inválido' })
  if (body.companyId && !/^COMP_\d{4}$/.test(body.companyId))
    throw createError({ statusCode: 400, statusMessage: 'Empresa inválida' })
  if (body.role === 'empresa' && !body.companyId)
    throw createError({ statusCode: 400, statusMessage: 'Falta la empresa seleccionada' })

  const config = useRuntimeConfig()
  const model = resolveModel({
    agentBaseUrl: process.env.AGENT_BASE_URL || config.agentBaseUrl,
    agentApiKey: process.env.AGENT_API_KEY || config.agentApiKey,
    agentModel: process.env.AGENT_MODEL || config.agentModel,
  })
  if (!model)
    throw createError({ statusCode: 503, statusMessage: 'Asistente no disponible', message: 'El proveedor del asistente no está configurado.' })

  const result = streamText({
    model,
    system: systemPrompt({ role: body.role, companyId: body.companyId }),
    messages: await convertToModelMessages(body.messages.slice(-MAX_MESSAGES)),
    tools: agentTools(localFetcher()),
    stopWhen: isStepCount(8),
    timeout: { totalMs: 120_000 },
  })
  return result.toUIMessageStreamResponse()
})
