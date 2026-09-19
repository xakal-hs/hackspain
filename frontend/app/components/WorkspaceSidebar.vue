<script setup lang="ts">
import {
  ArrowLeftRight,
  ChevronsUpDown,
  CircleDollarSign,
  Landmark,
  LogOut,
  PiggyBank,
  ScanLine,
  Wallet,
  Check,
} from '@lucide/vue'
import { perspectives, perspectiveById, type PerspectiveId } from '~/data/demo'

const props = defineProps<{ role: PerspectiveId; section: string }>()

const { name: companyName } = useSelectedCompany()
const profile = computed(() => perspectiveById(props.role)!)

const items = computed(() => {
  const treasury = [
    { id: 'flujo', label: 'Flujo de caja', icon: ArrowLeftRight },
    { id: 'score', label: 'X-Ray Score', icon: ScanLine },
    { id: 'colchon', label: 'Colchón Dinámico', icon: PiggyBank },
    { id: 'divisa', label: 'Divisa Inteligente', icon: CircleDollarSign },
  ]
  const ops = [
    { id: 'caja', label: 'Caja', icon: Wallet },
    { id: 'crm', label: 'Financiación', icon: Landmark },
  ]
  return props.role === 'empresa' ? treasury : ops
})

const open = ref(false)
const session = useCookie<PerspectiveId | null>('xray-demo-role', {
  sameSite: 'lax',
})

async function switchTo(role: PerspectiveId) {
  session.value = role
  open.value = false
  await navigateTo(`/dashboard/${role}`)
}

async function leave() {
  session.value = null
  await navigateTo('/')
}

/* La primera sección es la portada de la perspectiva: vive en la URL limpia. */
function href(id: string) {
  return id === items.value[0]?.id
    ? `/dashboard/${props.role}`
    : `/dashboard/${props.role}?section=${id}`
}

/* El pulgar de la pestaña activa se mide contra el enlace, no se estima: el
 * rail pasa de columna a fila bajo 900px y los anchos no son uniformes. */
const navEl = ref<HTMLElement | null>(null)
const placed = ref(false)
const armed = ref(false)
const thumb = reactive({ x: 0, y: 0, w: 0, h: 0 })

function placeThumb() {
  const nav = navEl.value
  const active = nav?.querySelector<HTMLElement>('a.is-here')
  if (!nav || !active) return
  thumb.x = active.offsetLeft
  thumb.y = active.offsetTop
  thumb.w = active.offsetWidth
  thumb.h = active.offsetHeight
  placed.value = true
}

onMounted(() => {
  placeThumb()
  requestAnimationFrame(() => {
    armed.value = true
  })
  const observer = new ResizeObserver(() => placeThumb())
  const el = navEl.value
  if (el) observer.observe(el as unknown as Element)
  window.addEventListener('resize', placeThumb)
  onUnmounted(() => {
    observer.disconnect()
    window.removeEventListener('resize', placeThumb)
  })
})

watch(
  () => [props.section, props.role, items.value.length] as const,
  () => placeThumb(),
  { flush: 'post' },
)
</script>

<template>
  <aside class="rail">
    <div class="rail__head">
      <NuxtLink to="/" class="lp__brand rail__brand">
        <BrandMark />
        <span>X-Ray<small>de Embat</small></span>
      </NuxtLink>
      <ThemeSwitch />
    </div>

    <div class="rail__space">
      <CompanySelector v-if="role === 'empresa'" />
      <template v-else><b>{{ profile.name }}</b><span>{{ profile.person }}</span></template>
    </div>

    <nav
      ref="navEl"
      class="rail__nav"
      :class="{ 'is-placed': placed, 'is-armed': armed }"
      aria-label="Secciones del panel"
      :style="{
        '--thumb-x': `${thumb.x}px`,
        '--thumb-y': `${thumb.y}px`,
        '--thumb-w': `${thumb.w}px`,
        '--thumb-h': `${thumb.h}px`,
      }"
    >
      <span class="rail__nav-thumb" aria-hidden="true"></span>
      <NuxtLink
        v-for="item in items"
        :key="item.id"
        :to="href(item.id)"
        :class="{ 'is-here': section === item.id }"
        :aria-current="section === item.id ? 'page' : undefined"
      >
        <component :is="item.icon" :size="17" aria-hidden="true" />{{
          item.label
        }}
      </NuxtLink>
    </nav>

    <div class="rail__foot">
      <div class="rail__profile" @keydown.esc="open = false">
        <div v-if="open" id="rail-switcher" class="rail__switcher">
          <p>Cambiar de vista</p>
          <CompanySelector v-if="role === 'empresa'" />
          <button
            v-for="perspective in perspectives"
            :key="perspective.id"
            type="button"
            :aria-pressed="perspective.id === role"
            @click="switchTo(perspective.id)"
          >
            <i aria-hidden="true">{{ perspective.id === 'empresa' ? 'CO' : perspective.initials }}</i>
            <span
              >{{ perspective.name }}<small>{{ perspective.id === 'empresa' ? companyName : perspective.person }}</small></span
            >
            <Check v-if="perspective.id === role" :size="15" aria-hidden="true" />
          </button>
          <button type="button" class="rail__leave" @click="leave">
            <LogOut :size="15" aria-hidden="true" />Salir de la demo
          </button>
        </div>

        <button
          type="button"
          class="rail__profile-btn"
          :aria-expanded="open"
          aria-controls="rail-switcher"
          @click="open = !open"
        >
          <i aria-hidden="true">{{ role === 'empresa' ? 'CO' : profile.initials }}</i>
          <span
            ><b>{{ role === 'empresa' ? companyName : profile.person }}</b
            ><small>Cambiar de vista</small></span
          >
          <ChevronsUpDown :size="15" aria-hidden="true" />
        </button>
      </div>
    </div>
  </aside>
</template>
