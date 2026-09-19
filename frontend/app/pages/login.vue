<script setup lang="ts">
import { perspectives, perspectiveById, type PerspectiveId } from '~/data/demo'

useHead({ title: 'Entrar · X-Ray' })

const route = useRoute()
const chosen = ref<PerspectiveId>(
  perspectiveById(String(route.query.role))?.id ?? 'banco',
)

const session = useCookie<PerspectiveId | null>('xray-demo-role', {
  sameSite: 'lax',
})

function enter() {
  session.value = chosen.value
  return navigateTo(`/dashboard/${chosen.value}`)
}
</script>

<template>
  <div class="entry">
    <header class="entry__top">
      <NuxtLink to="/" class="lp__brand">
        <BrandMark />
        <span>X-Ray<small>de Embat</small></span>
      </NuxtLink>
      <ThemeSwitch />
    </header>

    <main id="main-content" class="entry__main" tabindex="-1">
      <div class="entry__intro">
        <h1>¿Desde dónde vas a mirar?</h1>
        <p>
          Los datos son los mismos para los tres. Cambia el orden de lo que
          verás primero y lo que puedes hacer con ello.
        </p>
      </div>

      <form class="panel entry__panel" @submit.prevent="enter">
        <fieldset>
          <legend class="sr-only">Elige una vista</legend>
          <label
            v-for="perspective in perspectives"
            :key="perspective.id"
            class="entry__role"
            :class="{ 'is-chosen': chosen === perspective.id }"
          >
            <input
              v-model="chosen"
              type="radio"
              name="perspective"
              :value="perspective.id"
            />
            <i aria-hidden="true">{{ perspective.initials }}</i>
            <span>
              <b>{{ perspective.name }}</b>
              <em>{{ perspective.person }}</em>
              <span>{{ perspective.reads }}</span>
            </span>
          </label>
        </fieldset>

        <button class="btn btn--live btn--lg" type="submit">
          Entrar como {{ perspectiveById(chosen)?.name }}
        </button>
        <p class="entry__note">
          No hay credenciales ni operaciones reales. Puedes cambiar de vista
          dentro del panel.
        </p>
      </form>
    </main>

    <NuxtLink to="/" class="entry__back">Volver a la portada</NuxtLink>
  </div>
</template>
