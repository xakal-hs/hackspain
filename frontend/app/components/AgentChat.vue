<script setup lang="ts">
import { Chat } from '@ai-sdk/vue'
import { DefaultChatTransport, getToolName, isToolUIPart, type UIMessage } from 'ai'
import { ArrowUp, BarChart3, Check, Copy, Maximize2, Mic, Minimize2, Plus, Sparkles, Square, X } from '@lucide/vue'
import raybot from '~/assets/images/raybot.png'
import { blocks } from '~/utils/chatText'
import { chartSections, chartsFromParts } from '~/utils/chatCharts'

const props = defineProps<{ role: string }>()

const { selectedId } = useSelectedCompany()
const open = ref(false)
const draft = ref('')
const log = ref<HTMLElement | null>(null)
const wide = ref(false)
const field = ref<HTMLTextAreaElement | null>(null)
const listening = ref(false)
function toggle() {
  open.value = !open.value
}

const chat = new Chat<UIMessage>({
  transport: new DefaultChatTransport({
    api: '/api/chat',
  }),
})

const busy = computed(() => chat.status === 'submitted' || chat.status === 'streaming')
const suggestions = computed(() => props.role === 'embat'
  ? ['¿Qué empresas empeoran más este trimestre?', '¿Cómo se construye la nota?']
  : ['¿Por qué ha cambiado su nota este mes?', '¿Qué prevé su caja?', '¿Por qué esta decisión?'])

/* Lo que hace el asistente antes de contestar: enseñarlo es lo que permite comprobar de dónde sale cada cifra. */
const TOOL_LABEL: Record<string, string> = {
  ficha_empresa: 'Leyendo la ficha',
  explicar_mes: 'Descomponiendo el cambio de nota',
  decision_prestamista: 'Consultando la decisión',
  prevision_tesoreria: 'Leyendo la previsión',
  buscar_cartera: 'Buscando en la cartera',
  como_funciona_el_score: 'Leyendo cómo se calcula la nota',
  catalogo_de_vetos: 'Consultando los vetos',
}

/* El botón dice lo que se abre: con tabla no hay «gráficos» que ver, hay una tabla. */
function vizLabel(message: UIMessage) {
  const charts = chartsFromParts(message.parts)
  if (charts[0]?.kind === 'table') return 'Ver la tabla'
  return charts.length === 1 ? 'Ver el gráfico' : `Ver ${charts.length} gráficos`
}

function toolChips(message: UIMessage) {
  return message.parts.filter(isToolUIPart).map(part => ({
    key: part.toolCallId,
    label: TOOL_LABEL[getToolName(part)] ?? getToolName(part),
    done: part.state === 'output-available' || part.state === 'output-error',
  }))
}

/* Los gráficos se sacan de lo que devolvieron las herramientas; el más reciente arriba. */
const sections = computed(() => chartSections(chat.messages))
/* En compacto el panel crece con la conversación, pero toca techo pronto:
   un panel que sigue creciendo acaba tapando la pantalla que se está explicando. */
const compactHeight = computed(() => {
  // el arranque tiene que caber entero: cabecera, la frase, las tres sugerencias y la caja
  const turns = chat.messages.length
  return `min(${Math.min(540, 420 + turns * 40)}px, calc(100vh - 100px))`
})

const chartCount = computed(() => sections.value.reduce((n, sec) => n + sec.charts.length, 0))
/* Mientras el asistente consulta datos y aún no hay gráfico de esta pregunta, se enseñan esqueletos. */
const pending = computed(() => busy.value && !chartsFromParts(chat.messages.at(-1)?.role === 'assistant' ? chat.messages.at(-1)!.parts : []).length)
watch(chartCount, (n, before) => { if (n > before) wide.value = true })
/* El chat ocupa todo; la derecha solo aparece cuando hay algo que enseñar. */
const showViz = computed(() => wide.value && (sections.value.length > 0 || pending.value))
/* Solo la pregunta en curso: apilar las anteriores convertía el panel en un cajón de sastre. */
const latest = computed(() => sections.value[0])
/* Una tabla sola se pinta a sangre y ocupa el panel; lo demás va en tarjetas. */
const soleTable = computed(() =>
  latest.value?.charts.length === 1 && latest.value.charts[0]!.kind === 'table' ? latest.value.charts[0] : null)

/* El campo crece con lo que escribes (hasta 200 px), como el de un chat moderno. */
function grow() {
  const el = field.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  el.style.overflowY = el.scrollHeight > 200 ? 'auto' : 'hidden'
}
watch(draft, () => nextTick(grow))
watch(open, (isOpen) => nextTick(() => { if (isOpen) field.value?.focus() }))
function onEnter(e: KeyboardEvent) {
  if (e.isComposing || e.shiftKey) return
  e.preventDefault()
  send(draft.value)
}
function newChat() {
  chat.stop()
  chat.messages = []
  nextTick(() => field.value?.focus())
}

/* Dictado por voz con el reconocimiento del navegador; si no lo hay, el botón no aparece. */
const Recognition = import.meta.client ? ((window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition) : null
let recognizer: any = null
function toggleVoice() {
  if (listening.value) { recognizer?.stop(); return }
  recognizer = new Recognition()
  recognizer.lang = 'es-ES'
  recognizer.interimResults = false
  recognizer.onresult = (e: any) => { draft.value = `${draft.value} ${e.results[0][0].transcript}`.trim() }
  recognizer.onend = () => { listening.value = false }
  recognizer.onerror = () => { listening.value = false }
  listening.value = true
  recognizer.start()
}

const close = () => { open.value = false }
function onKey(e: KeyboardEvent) { if (e.key === 'Escape' && open.value) close() }
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => { window.removeEventListener('keydown', onKey); recognizer?.abort?.() })

const textOf = (message: UIMessage) =>
  message.parts.map(part => (part.type === 'text' ? part.text : '')).join('')

/* «X-Ray trabajó 12 s»: el tiempo real de la respuesta y, plegados, los pasos que dio. */
const took = reactive<Record<string, number>>({})
const openWork = reactive<Record<string, boolean>>({})
const copied = ref('')
let startedAt = 0
watch(() => chat.status, (status) => {
  const last = chat.messages.at(-1)
  if (status === 'ready' && last?.role === 'assistant' && startedAt) took[last.id] = Math.max(1, Math.round((Date.now() - startedAt) / 1000))
})
const isWorking = (m: UIMessage) => busy.value && m.id === chat.messages.at(-1)?.id
const workLabel = (m: UIMessage) => isWorking(m) ? 'X-Ray está trabajando…' : took[m.id] ? `X-Ray trabajó ${took[m.id]} s` : 'Pasos de X-Ray'
async function copy(m: UIMessage) {
  try { await navigator.clipboard.writeText(textOf(m)); copied.value = m.id; setTimeout(() => { copied.value = '' }, 1500) } catch { /* sin portapapeles: no pasa nada */ }
}

function send(text: string) {
  const value = text.trim()
  if (!value || busy.value) return
  draft.value = ''
  open.value = true
  startedAt = Date.now()
  chat.sendMessage({ text: value }, {
    body: { role: props.role, companyId: selectedId.value },
  })
}

const errorText = computed(() => {
  if (!chat.error) return ''
  return /503|configurado/.test(chat.error.message)
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
    <nav v-show="!(open && wide)" class="agent__dock" aria-label="Asistente de X-Ray">
      <button type="button" class="agent__bot" :class="{ 'is-on': open }" aria-label="Preguntar a X-Ray" title="Pregunta a X-Ray" @click="toggle">
        <img :src="raybot" alt="" width="22" height="22">
      </button>
    </nav>

    <Teleport to="body">
      <Transition name="agent-fade">
        <div v-if="open" class="agent__scrim" aria-hidden="true" @mousedown="close" />
      </Transition>
      <Transition name="agent-up">
        <section v-if="open" class="agent__panel" :class="{ 'is-wide': wide }" :style="wide ? undefined : { height: compactHeight }" role="dialog" aria-label="Asistente de X-Ray">
          <header class="agent__head">
            <div>
              <h2>Pregunta a X-Ray</h2>
            </div>
            <div class="agent__actions">
              <button type="button" class="agent__ghost" :aria-pressed="wide" @click="wide = !wide">
                <component :is="wide ? Minimize2 : Maximize2" :size="15" aria-hidden="true" />
                {{ wide ? 'Minimizar' : 'Ampliar' }}
              </button>
              <button type="button" class="agent__icon" aria-label="Cerrar" @click="close">
                <X :size="18" aria-hidden="true" />
              </button>
            </div>
          </header>

          <div class="agent__body" :class="{ 'has-viz': showViz }">
            <div class="agent__chat">
              <div ref="log" class="agent__log" aria-live="polite">
                <div v-if="!chat.messages.length" class="agent__empty">
                  <p>Pregúntame por una nota, un cambio de mes o una decisión. Cuando haya datos que ver, los dibujo a la derecha.</p>
                  <button v-for="s in suggestions" :key="s" type="button" class="agent__chip" @click="send(s)">{{ s }}</button>
                </div>

                <article v-for="m in chat.messages" :key="m.id" class="agent__msg" :class="`agent__msg--${m.role}`">
                  <p v-if="m.role === 'user'" class="agent__ask">{{ textOf(m) }}</p>
                  <template v-else>
                    <div v-if="toolChips(m).length" class="agent__work">
                      <button type="button" :aria-expanded="!!openWork[m.id]" @click="openWork[m.id] = !openWork[m.id]">
                        <Sparkles :size="13" aria-hidden="true" />
                        <span :class="{ 'is-live': isWorking(m) }">{{ workLabel(m) }}</span>
                      </button>
                      <div v-if="isWorking(m)" class="agent__progress" role="progressbar" aria-label="El asistente está trabajando"><i /></div>
                      <ul v-if="openWork[m.id]" class="agent__steps">
                        <li v-for="t in toolChips(m)" :key="t.key"><Check v-if="t.done" :size="12" aria-hidden="true" /><i v-else class="agent__spin" aria-hidden="true" />{{ t.label }}</li>
                      </ul>
                    </div>
                    <template v-for="(b, i) in blocks(textOf(m))" :key="i">
                      <hr v-if="b.kind === 'hr'">
                      <h3 v-else-if="b.kind === 'h'" :class="`is-h${(b.depth ?? 0) + 1}`"><InlineText :parts="b.inline" /></h3>
                      <blockquote v-else-if="b.kind === 'quote'"><InlineText :parts="b.inline" /></blockquote>
                      <p v-else-if="b.kind === 'ol'" class="agent__li agent__li--n" :data-n="`${b.n}.`" :style="{ '--d': b.depth ?? 0 }"><InlineText :parts="b.inline" /></p>
                      <p v-else-if="b.kind === 'li'" class="agent__li" :style="{ '--d': b.depth ?? 0 }"><InlineText :parts="b.inline" /></p>
                      <p v-else><InlineText :parts="b.inline" /></p>
                    </template>
                    <button v-if="!wide && chartsFromParts(m.parts).length" type="button" class="agent__more" @click="wide = true">
                      <BarChart3 :size="14" aria-hidden="true" /> {{ vizLabel(m) }}
                    </button>
                    <div v-if="textOf(m) && !isWorking(m)" class="agent__acts">
                      <button type="button" :aria-label="copied === m.id ? 'Copiado' : 'Copiar respuesta'" :title="copied === m.id ? 'Copiado' : 'Copiar respuesta'" @click="copy(m)">
                        <Check v-if="copied === m.id" :size="14" aria-hidden="true" /><Copy v-else :size="14" aria-hidden="true" />
                      </button>
                    </div>
                  </template>
                </article>

                <p v-if="errorText" class="agent__error" role="alert">{{ errorText }}</p>
              </div>

              <form class="agent__form" @submit.prevent="send(draft)">
                <div class="agent__box">
                  <textarea
                    ref="field" v-model="draft" rows="1" spellcheck="false" :disabled="busy"
                    placeholder="Pregunta por una nota, un cambio o una decisión" aria-label="Tu pregunta"
                    @keydown.enter="onEnter"
                  />
                  <div class="agent__bar">
                    <button type="button" class="agent__tool" title="Nueva conversación" aria-label="Nueva conversación" :disabled="!chat.messages.length" @click="newChat">
                      <Plus :size="16" aria-hidden="true" />
                    </button>
                    <span class="agent__grow" />
                    <button v-if="Recognition" type="button" class="agent__tool" :class="{ 'is-rec': listening }" :aria-pressed="listening" aria-label="Dictar por voz" title="Dictar por voz" @click="toggleVoice">
                      <Mic :size="15" aria-hidden="true" />
                    </button>
                    <button v-if="busy" type="button" class="agent__send" aria-label="Parar" @click="chat.stop()">
                      <Square :size="13" aria-hidden="true" />
                    </button>
                    <button v-else type="submit" class="agent__send" aria-label="Enviar" :disabled="!draft.trim()">
                      <ArrowUp :size="15" aria-hidden="true" />
                    </button>
                  </div>
                </div>
              </form>
            </div>

            <aside v-if="showViz" class="agent__viz" :class="{ 'is-flush': soleTable }" aria-label="Análisis de la respuesta">
              <ChatTable v-if="soleTable" :key="soleTable.id" :chart="soleTable" flush />

              <div v-else class="agent__viz-scroll">
                <div v-if="pending" class="agent__skel" aria-hidden="true">
                  <i class="agent__skel-stats" /><i class="agent__skel-line" />
                </div>

                <template v-for="(c, i) in latest?.charts ?? []" :key="c.id">
                  <ChatTable v-if="c.kind === 'table'" :chart="c" flush :style="{ '--i': i }" />
                  <ChatChart v-else :chart="c" :style="{ '--i': i }" />
                </template>
              </div>
            </aside>
          </div>
        </section>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.agent { font-family: var(--font-ui); }
/* El dock: una pastilla oscura con el bot, siempre visible abajo. */
.agent__dock {
  position: fixed; left: 50%; bottom: 16px; z-index: 101; transform: translateX(-50%);
  display: flex; align-items: center; gap: 6px; padding: 8px 10px; border-radius: 12px;
  background: #121436; border: 1px solid rgba(190, 200, 255, 0.12); box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
}
.agent__dock button {
  display: inline-flex; align-items: center; gap: 6px; height: 34px; padding: 0 12px; border: 0; border-radius: 8px;
  background: none; color: #eef0fb; cursor: pointer;
}
.agent__bot { padding: 0 8px; }
.agent__bot img { width: 22px; height: 22px; object-fit: contain; }
/* Mientras piensa, el bot flota: es el mismo «sigo aquí» que la barra, sin robar atención. */
.agent__who { display: flex; align-items: center; gap: 11px; min-width: 0; }
.agent__who img { flex: none; object-fit: contain; }
.agent__who img.is-live { animation: agent-float 2.4s ease-in-out infinite; }
@keyframes agent-float { 50% { transform: translateY(-3px) rotate(-4deg); } }
@media (prefers-reduced-motion: reduce) { .agent__who img.is-live { animation: none; } }
.agent__dock button:hover { background: rgba(190, 200, 255, 0.08); }
.agent__dock button.is-on { background: rgba(190, 200, 255, 0.1); }
.agent__dock button:focus-visible { outline: 2px solid var(--focus-ring); outline-offset: 2px; }
/* Sobre el dock, centrado como el de Embat: sale desde abajo y no tapa la pantalla. */
.agent__panel {
  position: fixed; left: 50%; bottom: 72px; z-index: 100; transform: translateX(-50%);
  width: min(760px, calc(100vw - 32px)); display: flex; flex-direction: column;
  background: var(--panel); color: var(--text); border: 1px solid var(--line-strong);
  border-radius: 16px; font-family: var(--font-ui);
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.45), var(--sheen); overflow: hidden;
  transition: width 0.25s ease, height 0.25s ease, bottom 0.25s ease, transform 0.28s ease, opacity 0.2s ease;
}
.agent__panel.is-wide {
  bottom: 0; width: min(1660px, calc(100vw - 32px)); height: min(940px, calc(100vh - 24px));
  border-bottom: 0; border-radius: 16px 16px 0 0;
}
.agent__scrim { position: fixed; inset: 0; z-index: 99; background: rgba(4, 6, 20, 0.18); backdrop-filter: blur(2px); -webkit-backdrop-filter: blur(2px); }
.agent-fade-enter-active, .agent-fade-leave-active { transition: opacity 0.25s ease; }
.agent-fade-enter-from, .agent-fade-leave-to { opacity: 0; }
.agent-up-enter-from, .agent-up-leave-to { transform: translate(-50%, 40px); opacity: 0; }
.agent__head { display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 16px 24px; border-bottom: 1px solid var(--line); }
.agent__head h2 { margin: 0; font-size: 0.95rem; font-weight: 600; color: var(--live-ink); }
.agent__actions { display: flex; align-items: center; gap: 6px; }
.agent__ghost {
  display: inline-flex; align-items: center; gap: 6px; background: none; border: 0; color: var(--text);
  font: 500 0.82rem var(--font-ui); cursor: pointer; padding: 6px 8px; border-radius: 8px;
}
.agent__ghost:hover, .agent__icon:hover { background: var(--neutral-wash); }
.agent__icon { background: none; border: 0; color: var(--text-muted); cursor: pointer; padding: 6px; border-radius: 8px; }
.agent__body { flex: 1; min-height: 0; display: grid; grid-template-columns: 1fr; }
.agent__body.has-viz { grid-template-columns: minmax(360px, 5fr) 7fr; }
/* El chat vive en una columna centrada: a todo lo ancho el ojo pierde el renglón. */
.agent__chat { --col: 720px; display: flex; flex-direction: column; min-height: 0; min-width: 0; }
.agent__log > *, .agent__box { width: 100%; max-width: var(--col); margin-inline: auto; }
.agent__log { flex: 1; overflow-y: auto; padding: 18px 32px; display: flex; flex-direction: column; gap: 14px; }
.agent__viz { min-height: 0; display: flex; flex-direction: column; border-left: 1px solid var(--line); background: var(--panel); }
.agent__viz.is-flush { background: var(--panel); }
.agent__viz-scroll { flex: 1; min-height: 0; overflow-y: auto; scroll-behavior: smooth; background: var(--panel); }
.agent__skel { display: grid; gap: 1px; }
.agent__skel i { display: block; background: linear-gradient(100deg, var(--panel) 30%, var(--panel-raised) 50%, var(--panel) 70%); background-size: 200% 100%; animation: agent-shimmer 1.3s linear infinite; border-bottom: 1px solid var(--line); }
.agent__skel-stats { height: 92px; } .agent__skel-line { height: 250px; } .agent__skel-bars { height: 160px; }
@keyframes agent-shimmer { to { background-position: -200% 0; } }
.agent__empty p { margin: 0 0 14px; font-size: 0.82rem; line-height: 1.62; color: var(--text-muted); }
.agent__chip {
  display: block; width: 100%; text-align: left; margin-bottom: 7px; padding: 12px 15px; border-radius: 12px;
  border: 1px solid var(--line); background: var(--panel-sunken); color: var(--text); font: 0.83rem/1.5 var(--font-ui); cursor: pointer;
}
.agent__chip:hover { border-color: var(--live); }
.agent__msg { font-size: 0.82rem; line-height: 1.68; width: 100%; }
.agent__msg p { margin: 0 0 11px; }
.agent__msg--user { position: sticky; top: -16px; z-index: 2; padding-top: 16px; margin-top: -4px; background: linear-gradient(var(--panel) 80%, transparent); animation: agent-drop 0.4s cubic-bezier(0.34, 1.56, 0.64, 1); }
.agent__ask {
  margin: 0 !important; padding: 8px 12px; text-align: left; border-radius: 10px; background: var(--panel-raised);
  max-height: calc(3.5 * 1.6em + 16px); overflow: hidden; white-space: pre-wrap; overflow-wrap: anywhere;
}
@keyframes agent-drop { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: none; } }
.agent__msg h3 { margin: 18px 0 7px; font-weight: 600; }
.agent__msg h3:first-child { margin-top: 0; }
.agent__msg h3.is-h1 { font-size: 0.95rem; }
.agent__msg h3.is-h2 { font-size: 0.88rem; }
.agent__msg h3.is-h3, .agent__msg h3.is-h4 { font-size: 0.82rem; color: var(--text-muted); letter-spacing: 0.02em; text-transform: uppercase; }
.agent__msg hr { margin: 18px 0; border: 0; border-top: 1px solid var(--line); }
.agent__msg blockquote { margin: 0 0 10px; padding-left: 12px; border-left: 3px solid var(--line-strong); color: var(--text-muted); font-style: italic; }
.agent__li { padding-left: calc(16px + var(--d, 0) * 16px); position: relative; margin-bottom: 5px !important; }
.agent__li::before { content: '•'; position: absolute; left: calc(2px + var(--d, 0) * 16px); color: var(--text-dim); }
.agent__li--n { padding-left: calc(24px + var(--d, 0) * 16px); }
.agent__li--n::before { content: attr(data-n); left: calc(var(--d, 0) * 16px); color: var(--text-muted); font: 0.92em var(--font-num); font-variant-numeric: tabular-nums; }
.agent__work { margin-bottom: 8px; }
.agent__work button {
  display: inline-flex; align-items: center; gap: 8px; padding: 2px 0; border: 0; background: none;
  color: var(--text-muted); font: 0.8rem var(--font-ui); cursor: pointer;
}
.agent__work button:hover { color: var(--text); }
.agent__steps { list-style: none; margin: 6px 0 0; padding: 0 0 0 4px; display: flex; flex-direction: column; gap: 4px; font-size: 0.76rem; color: var(--text-muted); }
.agent__steps li { display: flex; align-items: center; gap: 8px; }
.agent__steps svg { color: var(--mint); }
/* La espera: el rótulo recorre un brillo y debajo corre una barra sin porcentaje.
   Nada de tres puntos: esto dice «sigo trabajando» sin fingir que sabe cuánto falta. */
.agent__work span.is-live {
  background: linear-gradient(90deg, var(--text-dim) 20%, var(--live-ink) 45%, var(--text) 55%, var(--text-dim) 80%);
  background-size: 220% 100%; -webkit-background-clip: text; background-clip: text; color: transparent;
  animation: agent-sweep 1.9s ease-in-out infinite;
}
@keyframes agent-sweep { from { background-position: 130% 0; } to { background-position: -30% 0; } }
.agent__progress { position: relative; height: 2px; margin: 7px 0 2px; border-radius: 2px; background: var(--neutral-wash); overflow: hidden; }
.agent__progress i {
  position: absolute; top: 0; bottom: 0; width: 38%; border-radius: 2px;
  background: linear-gradient(90deg, transparent, var(--live), transparent);
  animation: agent-slide 1.4s cubic-bezier(0.45, 0, 0.55, 1) infinite;
}
@keyframes agent-slide { from { left: -40%; } to { left: 102%; } }
.agent__spin {
  width: 11px; height: 11px; margin: 0 1px; border-radius: 50%; flex: none;
  border: 1.5px solid var(--line-strong); border-top-color: var(--live); animation: agent-spin 0.7s linear infinite;
}
@keyframes agent-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) {
  .agent__work span.is-live, .agent__progress i, .agent__spin { animation-duration: 0.01ms; animation-iteration-count: 1; }
  .agent__work span.is-live { color: var(--text-muted); background: none; -webkit-text-fill-color: currentColor; }
  .agent__progress i { left: 0; width: 100%; }
}
.agent__acts { display: flex; margin-top: 2px; }
.agent__acts button { display: grid; place-items: center; padding: 4px; border: 0; border-radius: 6px; background: none; color: var(--text-muted); cursor: pointer; }
.agent__acts button:hover { background: var(--neutral-wash); color: var(--text); }
.agent__more {
  display: inline-flex; align-items: center; gap: 6px; margin: 2px 0 6px; padding: 4px 10px; border-radius: 999px;
  border: 1px solid var(--line-strong); background: var(--live-wash); color: var(--live-ink); font: 0.76rem var(--font-ui); cursor: pointer;
}
.agent__error { font-size: 0.82rem; color: var(--crimson); margin: 0; }
.agent__form { padding: 8px 32px 18px; }
.agent__box {
  border: 0.5px solid var(--line-strong); border-radius: 12px; background: var(--panel-sunken);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12); transition: box-shadow 0.2s ease, border-color 0.2s ease; cursor: text;
}
.agent__box:hover { border-color: var(--text-dim); }
.agent__box:focus-within { border-color: var(--live); box-shadow: 0 2px 20px rgba(0, 0, 0, 0.2), 0 0 0 1px var(--live-wash); }
.agent__box textarea {
  display: block; width: 100%; min-height: 36px; max-height: 200px; box-sizing: border-box; padding: 10px 12px 4px;
  border: 0; background: transparent; color: var(--text); resize: none; overflow: hidden; outline: none;
  font: 0.82rem/1.55 var(--font-ui);
}
.agent__box textarea::placeholder { color: var(--text-muted); }
.agent__bar { display: flex; align-items: center; gap: 4px; padding: 4px 8px 8px; }
.agent__grow { flex: 1; }
.agent__tool {
  display: grid; place-items: center; width: 28px; height: 28px; border: 0; border-radius: 6px;
  background: none; color: var(--text-muted); cursor: pointer; transition: background 0.15s ease;
}
.agent__tool:hover:not(:disabled) { background: var(--neutral-wash); color: var(--text); }
.agent__tool:disabled { opacity: 0.35; cursor: default; }
.agent__tool.is-rec { color: var(--crimson); background: var(--crimson-wash); }
.agent__send {
  display: grid; place-items: center; width: 28px; height: 28px; border-radius: 8px; cursor: pointer;
  border: 1px solid var(--live); background: var(--live-wash); color: var(--live-ink); transition: background 0.15s ease;
}
.agent__send:hover:not(:disabled) { background: var(--live); color: var(--on-live); }
.agent__send:disabled { opacity: 0.4; cursor: default; }
.agent__send:focus-visible, .agent__chip:focus-visible, .agent__tool:focus-visible,
.agent__ghost:focus-visible, .agent__icon:focus-visible, .agent__more:focus-visible { outline: 2px solid var(--live); outline-offset: 2px; }
@media (max-width: 820px) {
  .agent__body.has-viz { grid-template-columns: 1fr; grid-template-rows: minmax(0, 1fr) minmax(0, 1fr); }
  .agent__viz { border-left: 0; border-top: 1px solid var(--line); }
}
</style>
