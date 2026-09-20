import { convertToModelMessages, isStepCount, streamText, type UIMessage } from 'ai'
import { agentTools, localFetcher } from '../agent/tools'
import { resolveModel } from '../agent/model'
import { systemPrompt, type AgentContext } from '../agent/prompt'

interface ChatBody extends AgentContext {
  messages: UIMessage[]
}

const MAX_MESSAGES = 30

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const model = resolveModel({
    agentBaseUrl: config.agentBaseUrl, agentApiKey: config.agentApiKey, agentModel: config.agentModel,
    gatewayKey: process.env.AI_GATEWAY_API_KEY, oidcToken: process.env.VERCEL_OIDC_TOKEN,
  })
  if (!model)
    throw createError({ statusCode: 503, statusMessage: 'Assistant unavailable', message: 'El asistente no está configurado (falta AGENT_BASE_URL con AGENT_MODEL, o AI_GATEWAY_API_KEY)' })
  /* Ocultar el botón no cierra la puerta: la ruta se puede llamar a mano desde la vista de
     empresa, y las herramientas leen cualquier empresa de la cartera. Manda la sesión. */
  if (getCookie(event, 'xray-demo-role') !== 'embat')
    throw createError({ statusCode: 403, statusMessage: 'Forbidden', message: 'El asistente solo está disponible en la vista de Embat' })

  const body = await readBody<ChatBody>(event)
  if (!Array.isArray(body?.messages) || !body.messages.length)
    throw createError({ statusCode: 400, statusMessage: 'Bad request', message: 'Faltan mensajes' })

  const result = streamText({
    model,
    system: systemPrompt({ role: body.role, companyId: body.companyId }),
    messages: await convertToModelMessages(body.messages.slice(-MAX_MESSAGES)),
    tools: agentTools(localFetcher()),
    stopWhen: isStepCount(8),
  })
  return result.toUIMessageStreamResponse()
})
