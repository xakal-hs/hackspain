import { createOpenAICompatible } from '@ai-sdk/openai-compatible'
import type { LanguageModel } from 'ai'

export interface ModelEnv {
  agentBaseUrl?: string
  agentApiKey?: string
  agentModel?: string
  gatewayKey?: string
  oidcToken?: string
}

/**
 * Qué modelo contesta, por orden:
 *  1. AGENT_BASE_URL: cualquier servidor compatible con OpenAI (Ollama, vLLM, un proveedor de modelos abiertos).
 *     La clave es opcional, Ollama no la pide; AGENT_MODEL es obligatoria.
 *  2. Vercel AI Gateway (clave propia u OIDC), con un id `proveedor/modelo`.
 * Devuelve `null` si no hay ninguno, y el endpoint lo cuenta como «no configurado».
 */
export function resolveModel(env: ModelEnv): LanguageModel | null {
  if (env.agentBaseUrl) {
    if (!env.agentModel) return null
    return createOpenAICompatible({
      name: 'agent',
      baseURL: env.agentBaseUrl.replace(/\/$/, ''),
      apiKey: env.agentApiKey || undefined,
    })(env.agentModel)
  }
  if (env.gatewayKey || env.oidcToken) return env.agentModel || 'anthropic/claude-opus-5'
  return null
}
