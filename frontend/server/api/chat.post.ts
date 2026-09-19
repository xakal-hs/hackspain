import { convertToModelMessages, isStepCount, streamText, type UIMessage } from 'ai'
import { agentTools, apiFetcher } from '../agent/tools'
import { systemPrompt, type AgentContext } from '../agent/prompt'

interface ChatBody extends AgentContext {
  messages: UIMessage[]
}

const MAX_MESSAGES = 30

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  // Vercel AI Gateway: clave propia en local y en servidores externos, OIDC en un despliegue de Vercel.
  if (!process.env.AI_GATEWAY_API_KEY && !process.env.VERCEL_OIDC_TOKEN)
    throw createError({ statusCode: 503, statusMessage: 'Assistant unavailable', message: 'El asistente no está configurado (falta AI_GATEWAY_API_KEY)' })
  if (!config.xrayApiBase)
    throw createError({ statusCode: 503, statusMessage: 'Assistant unavailable', message: 'El asistente necesita el backend de X-Ray (XRAY_API_BASE)' })

  const body = await readBody<ChatBody>(event)
  if (!Array.isArray(body?.messages) || !body.messages.length)
    throw createError({ statusCode: 400, statusMessage: 'Bad request', message: 'Faltan mensajes' })

  const result = streamText({
    // Un id `proveedor/modelo` a secas se enruta por el AI Gateway.
    model: config.agentModel || 'anthropic/claude-opus-5',
    system: systemPrompt({ role: body.role, companyId: body.companyId }),
    messages: await convertToModelMessages(body.messages.slice(-MAX_MESSAGES)),
    tools: agentTools(apiFetcher(config.xrayApiBase)),
    stopWhen: isStepCount(8),
  })
  return result.toUIMessageStreamResponse()
})
