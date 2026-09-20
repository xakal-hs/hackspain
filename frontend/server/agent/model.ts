import { createOpenAICompatible } from '@ai-sdk/openai-compatible'
import type { LanguageModel } from 'ai'

export interface ModelEnv {
  agentBaseUrl?: string
  agentApiKey?: string
  agentModel?: string
}

export function resolveModel(env: ModelEnv): LanguageModel | null {
  const baseUrl = env.agentBaseUrl?.trim()
  const apiKey = env.agentApiKey?.trim()
  const model = env.agentModel?.trim()
  if (!baseUrl || !apiKey || !model) return null

  try {
    const url = new URL(baseUrl)
    if (!['http:', 'https:'].includes(url.protocol)) return null
  } catch {
    return null
  }

  return createOpenAICompatible({
    name: 'helmcode',
    baseURL: baseUrl.replace(/\/$/, ''),
    apiKey,
  })(model)
}
