<script setup lang="ts">
import { Info } from '@lucide/vue'
import { scoreFieldHelp } from '~/data/scoreFieldHelp'

const props = defineProps<{ label: string; value: string }>()
const help = computed(() => scoreFieldHelp[props.label])
const open = ref(false)
const root = ref<HTMLElement>()
const id = useId()
const above = ref(false)
const maxHeight = ref(360)
const left = ref(0)
function show() {
  const rect = root.value?.getBoundingClientRect()
  if (rect) {
    left.value = Math.min(0, window.innerWidth - 16 - rect.left - Math.min(360, window.innerWidth - 48))
    above.value = rect.top > window.innerHeight - rect.bottom
    maxHeight.value = Math.max(80, (above.value ? rect.top : window.innerHeight - rect.bottom) - 16)
  }
  open.value = true
}
function outside(event: Event) {
  if (!root.value?.contains(event.target as Node)) open.value = false
}
function blur(event: FocusEvent) {
  if (!root.value?.contains(event.relatedTarget as Node)) open.value = false
}
function escape(event: KeyboardEvent) {
  if (event.key === 'Escape') open.value = false
}
onMounted(() => {
  document.addEventListener('pointerdown', outside)
  document.addEventListener('keydown', escape)
})
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', outside)
  document.removeEventListener('keydown', escape)
})
watch(() => [props.label, props.value], () => { open.value = false })
</script>

<template>
  <div ref="root" class="score-help" @mouseenter="show" @mouseleave="open = false" @focusout="blur">
    <button v-if="help" type="button" class="score-help__label" :aria-describedby="open ? id : undefined"
      @focus="show" @click="show">
      {{ label }} <Info :size="14" aria-hidden="true" />
    </button>
    <span v-else class="score-help__plain">{{ label }}</span>
    <slot />
    <div v-if="help && open" :id="id" role="tooltip" class="score-help__tip" :class="{ 'score-help__tip--above': above }" :style="{ maxHeight: `${maxHeight}px`, left: `${left}px` }">
      <strong>{{ label }}</strong>
      <div>{{ help.meaning }}</div>
      <div>{{ help.reading }}</div>
      <div v-if="value.toLowerCase().includes('sin dato')" class="score-help__note">
        Sin dato no significa cero: la señal puede no aplicar o faltar información. El modelo usa un valor neutral, que puede aportar puntos.
      </div>
    </div>
  </div>
</template>

<style scoped>
.score-help { position: relative; }
.score-help__label, .score-help__plain { font: inherit; font-size: 12.5px; color: var(--meta); }
.score-help__label { display: flex; align-items: center; gap: 7px; min-height: 44px; width: 100%; padding: 0; border: 0; background: none; text-align: left; cursor: help; }
.score-help__label svg { flex: none; }
.score-help__label:hover, .score-help__label:focus-visible { color: var(--text); }
.score-help__label:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; border-radius: 4px; }
.score-help__tip { position: absolute; z-index: 20; top: 100%; left: 0; width: min(360px, calc(100vw - 48px)); box-sizing: border-box; padding: 14px; border: 1px solid var(--border); border-radius: 10px; background: var(--card); color: var(--text); box-shadow: 0 8px 24px rgb(0 0 0 / 18%); font-size: 13px; line-height: 1.55; overflow-wrap: anywhere; overflow-y: auto; }
.score-help__tip--above { top: auto; bottom: 100%; }
.score-help__tip strong { display: block; font-size: 13px; }
.score-help__tip div { margin-top: 8px; }
.score-help__note { border-top: 1px solid var(--border); padding-top: 8px; }
</style>
