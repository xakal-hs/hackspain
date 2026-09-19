<script setup lang="ts">
import { Chat } from '@ai-sdk/vue'
import { DefaultChatTransport, getToolName, isToolUIPart, type UIMessage } from 'ai'
import { MessageCircleQuestion, Send, Square, X } from '@lucide/vue'
import { blocks } from '~/utils/chatText'

const props = defineProps<{ role: string }>()

const { selectedId } = useSelectedCompany()
const open = ref(false)
const draft = ref('')
const log = ref<HTMLElement | null>(null)

const chat = new Chat<UIMessage>({
  transport: new DefaultChatTransport({
    api: '/api/chat',
    body: () => ({ role: props.role, companyId: selectedId.value }),
  }),
})

const busy = computed(() => chat.status === 'submitted' || chat.status === 'streaming')
const suggestions = computed(() => props.role === 'embat'
  ? ['¿Qué empresas empeoran más este trimestre?', '¿Cómo se construye la nota?']
  : ['¿Por qué ha cambiado su nota este mes?', '¿Es un bache o un cambio de fondo?', '¿Por qué esta decisión?'])

/* Lo que hace el asistente antes de contestar: enseñarlo es lo que permite comprobar de dónde sale cada cifra. */
const TOOL_LABEL: Record<string, string> = {
  ficha_empresa: 'Leyendo la ficha',
  explicar_mes: 'Descomponiendo el cambio de nota',
  decision_prestamista: 'Consultando la decisión',
  buscar_cartera: 'Buscando en la cartera',
  como_funciona_el_score: 'Leyendo cómo se calcula la nota',
  catalogo_de_vetos: 'Consultando los vetos',
}

function toolChips(message: UIMessage) {
  return message.parts.filter(isToolUIPart).map(part => ({
    key: part.toolCallId,
    label: TOOL_LABEL[getToolName(part)] ?? getToolName(part),
    done: part.state === 'output-available' || part.state === 'output-error',
  }))
}

const textOf = (message: UIMessage) =>
  message.parts.map(part => (part.type === 'text' ? part.text : '')).join('')

function send(text: string) {
  const value = text.trim()
  if (!value || busy.value) return
  draft.value = ''
  chat.sendMessage({ text: value })
}

const errorText = computed(() => {
  if (!chat.error) return ''
  return /503|configurado|XRAY_API_BASE/.test(chat.error.message)
    ? 'El asistente no está disponible en este entorno.'
    : 'No he podido contestar. Inténtalo de nuevo.'
})

watch(() => chat.messages.map(m => textOf(m).length).join(','), async () => {
  await nextTick()
  log.value?.scrollTo({ top: log.value.scrollHeight })
})
</script>

<template>
  <div class="agent">
    <button v-if="!open" class="agent__fab" type="button" @click="open = true">
      <MessageCircleQuestion :size="18" aria-hidden="true" />
      Pregunta a X-Ray
    </button>

    <section v-else class="agent__panel" role="dialog" aria-label="Asistente de X-Ray">
      <header class="agent__head">
        <div>
          <h2>Pregunta a X-Ray</h2>
          <p>Explica lo que la pantalla no puede enseñar{{ role !== 'embat' ? ` de ${selectedId}` : '' }}.</p>
        </div>
        <button type="button" class="agent__icon" aria-label="Cerrar" @click="open = false">
          <X :size="16" aria-hidden="true" />
        </button>
      </header>

      <div ref="log" class="agent__log" aria-live="polite">
        <div v-if="!chat.messages.length" class="agent__empty">
          <p>Cada cifra que te dé sale de los datos de X-Ray y va con su mes.</p>
          <button v-for="s in suggestions" :key="s" type="button" class="agent__chip" @click="send(s)">{{ s }}</button>
        </div>

        <article v-for="m in chat.messages" :key="m.id" class="agent__msg" :class="`agent__msg--${m.role}`">
          <ul v-if="m.role === 'assistant' && toolChips(m).length" class="agent__tools">
            <li v-for="t in toolChips(m)" :key="t.key" :class="{ 'is-done': t.done }">{{ t.label }}</li>
          </ul>
          <template v-for="(b, i) in blocks(textOf(m))" :key="i">
            <p v-if="b.kind === 'p'"><template v-for="(s, j) in b.inline" :key="j"><strong v-if="s.bold">{{ s.text }}</strong><template v-else>{{ s.text }}</template></template></p>
            <p v-else class="agent__li"><template v-for="(s, j) in b.inline" :key="j"><strong v-if="s.bold">{{ s.text }}</strong><template v-else>{{ s.text }}</template></template></p>
          </template>
        </article>

        <p v-if="errorText" class="agent__error" role="alert">{{ errorText }}</p>
      </div>

      <form class="agent__form" @submit.prevent="send(draft)">
        <input v-model="draft" type="text" placeholder="Pregunta por una nota, un cambio o una decisión" aria-label="Tu pregunta" :disabled="busy">
        <button v-if="busy" type="button" class="agent__send" aria-label="Parar" @click="chat.stop()">
          <Square :size="16" aria-hidden="true" />
        </button>
        <button v-else type="submit" class="agent__send" aria-label="Enviar" :disabled="!draft.trim()">
          <Send :size="16" aria-hidden="true" />
        </button>
      </form>
    </section>
  </div>
</template>

<style scoped>
.agent { position: fixed; right: 20px; bottom: 20px; z-index: 40; font-family: var(--font-ui); }
.agent__fab {
  display: inline-flex; align-items: center; gap: 8px; padding: 11px 16px; border-radius: 999px;
  border: 1px solid var(--line-strong); background: var(--live-solid); color: var(--live-ink);
  font: 600 0.875rem var(--font-ui); cursor: pointer; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.28);
}
.agent__panel {
  width: min(400px, calc(100vw - 32px)); height: min(600px, calc(100vh - 40px)); display: flex; flex-direction: column;
  background: var(--panel); color: var(--text); border: 1px solid var(--line-strong); border-radius: 14px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.38); overflow: hidden;
}
.agent__head { display: flex; justify-content: space-between; gap: 12px; padding: 14px 16px; border-bottom: 1px solid var(--line); }
.agent__head h2 { margin: 0; font-size: 0.95rem; font-weight: 600; }
.agent__head p { margin: 2px 0 0; font-size: 0.78rem; color: var(--text-muted); }
.agent__icon { background: none; border: 0; color: var(--text-muted); cursor: pointer; padding: 4px; align-self: flex-start; }
.agent__log { flex: 1; overflow-y: auto; padding: 14px 16px; display: flex; flex-direction: column; gap: 12px; }
.agent__empty p { margin: 0 0 10px; font-size: 0.82rem; color: var(--text-muted); }
.agent__chip {
  display: block; width: 100%; text-align: left; margin-bottom: 6px; padding: 9px 12px; border-radius: 10px;
  border: 1px solid var(--line); background: var(--panel-sunken); color: var(--text); font: 0.84rem var(--font-ui); cursor: pointer;
}
.agent__chip:hover { border-color: var(--live); }
.agent__msg { font-size: 0.88rem; line-height: 1.55; max-width: 92%; }
.agent__msg p { margin: 0 0 6px; }
.agent__msg--user { align-self: flex-end; background: var(--panel-raised); padding: 8px 12px; border-radius: 12px 12px 2px 12px; }
.agent__msg--user p { margin: 0; }
.agent__li { padding-left: 14px; position: relative; }
.agent__li::before { content: '–'; position: absolute; left: 0; color: var(--text-muted); }
.agent__tools { list-style: none; margin: 0 0 6px; padding: 0; display: flex; flex-wrap: wrap; gap: 4px; }
.agent__tools li {
  font: 0.7rem var(--font-num); color: var(--text-muted); border: 1px solid var(--line); border-radius: 999px; padding: 2px 8px;
}
.agent__tools li.is-done { color: var(--live); border-color: var(--live); }
.agent__error { font-size: 0.82rem; color: var(--crimson); margin: 0; }
.agent__form { display: flex; gap: 8px; padding: 12px; border-top: 1px solid var(--line); }
.agent__form input {
  flex: 1; min-width: 0; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--line-strong);
  background: var(--panel-sunken); color: var(--text); font: 0.88rem var(--font-ui);
}
.agent__form input:focus-visible, .agent__fab:focus-visible, .agent__send:focus-visible, .agent__chip:focus-visible { outline: 2px solid var(--live); outline-offset: 2px; }
.agent__send {
  display: grid; place-items: center; width: 40px; border-radius: 10px; border: 0;
  background: var(--live-solid); color: var(--live-ink); cursor: pointer;
}
.agent__send:disabled { opacity: 0.4; cursor: default; }
</style>
