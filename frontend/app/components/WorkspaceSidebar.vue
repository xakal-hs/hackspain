<script setup lang="ts">
import {
  Activity,
  ChevronsUpDown,
  Gauge,
  Handshake,
  LogOut,
  Rows3,
  Check,
} from '@lucide/vue'
import {
  perspectives,
  perspectiveById,
  currentMonth,
  type PerspectiveId,
} from '~/data/demo'

const props = defineProps<{ role: PerspectiveId; section: string }>()

const profile = computed(() => perspectiveById(props.role)!)

const items = computed(() => {
  const all = [
    { id: 'resumen', label: 'Resumen', icon: Gauge },
    { id: 'cartera', label: 'Cartera', icon: Rows3 },
    { id: 'senales', label: props.role === 'empresa' ? 'Mis señales' : 'Señales', icon: Activity },
    {
      id: 'ofertas',
      label:
        props.role === 'empresa'
          ? 'Mis ofertas'
          : props.role === 'banco'
            ? 'Ofertas enviadas'
            : 'Mercado',
      icon: Handshake,
    },
  ]
  return props.role === 'empresa' ? all.filter((i) => i.id !== 'cartera') : all
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

function href(id: string) {
  return id === 'resumen'
    ? `/dashboard/${props.role}`
    : `/dashboard/${props.role}?section=${id}`
}
</script>

<template>
  <aside class="rail">
    <NuxtLink to="/" class="lp__brand rail__brand">
      <BrandMark />
      <span>X-Ray<small>de Embat</small></span>
    </NuxtLink>

    <div class="rail__space">
      <b>{{ profile.name }}</b>
      <span>{{ profile.person }}</span>
    </div>

    <nav class="rail__nav" aria-label="Secciones del panel">
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
      <ThemeSwitch />

      <p class="rail__env">
        Entorno de demostración<span>Datos ficticios · {{ currentMonth }}</span>
      </p>

      <div class="rail__profile" @keydown.esc="open = false">
        <div v-if="open" id="rail-switcher" class="rail__switcher">
          <p>Cambiar de vista</p>
          <button
            v-for="perspective in perspectives"
            :key="perspective.id"
            type="button"
            :aria-pressed="perspective.id === role"
            @click="switchTo(perspective.id)"
          >
            <i aria-hidden="true">{{ perspective.initials }}</i>
            <span
              >{{ perspective.name }}<small>{{ perspective.person }}</small></span
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
          <i aria-hidden="true">{{ profile.initials }}</i>
          <span
            ><b>{{ profile.person }}</b
            ><small>Cambiar de vista</small></span
          >
          <ChevronsUpDown :size="15" aria-hidden="true" />
        </button>
      </div>
    </div>
  </aside>
</template>
