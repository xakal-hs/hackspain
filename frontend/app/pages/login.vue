<script setup lang="ts">
import { companies, leadCompany, leadMonths, perspectives, type PerspectiveId } from '~/data/demo'

useHead({ title: 'Entrar · X-Ray' })

const session = useCookie<PerspectiveId | null>('xray-demo-role', {
  sameSite: 'lax',
})

function enterAs(id: PerspectiveId) {
  session.value = id
  return navigateTo(`/dashboard/${id}`)
}

const stats = [
  { figure: `${companies.length}`, label: 'Empresas en la demo' },
  { figure: '24', label: 'Meses de histórico por empresa' },
  { figure: `${leadMonths(leadCompany)}`, label: 'Meses de ventaja sobre la caída' },
]
</script>

<template>
  <div class="auth">
    <aside class="auth__art">
      <NuxtLink to="/" class="lp__brand">
        <BrandMark />
        <span>X-Ray<small>de Embat</small></span>
      </NuxtLink>

      <dl class="auth__stats">
        <div v-for="stat in stats" :key="stat.label">
          <dt>{{ stat.figure }}</dt>
          <dd>{{ stat.label }}</dd>
        </div>
      </dl>
    </aside>

    <main id="main-content" class="auth__form" tabindex="-1">
      <div class="auth__top">
        <NuxtLink to="/" class="auth__back">Volver a la portada</NuxtLink>
        <ThemeSwitch />
      </div>

      <div class="auth__box">
        <h1>Entrar</h1>

        <form class="auth__fake" @submit.prevent>
          <label class="field">
            <span>Email</span>
            <input type="email" placeholder="tu@empresa.com" autocomplete="off" />
          </label>

          <label class="field">
            <span>Contraseña</span>
            <input type="password" placeholder="••••••••" autocomplete="off" />
          </label>

          <span class="auth__recover">Recuperar contraseña</span>

          <button class="btn btn--quiet btn--lg" type="submit" disabled>
            Entrar
          </button>
        </form>

        <div class="auth__divider"><span>o entra directo a la demo</span></div>

        <div class="auth__demo">
          <button
            v-for="perspective in perspectives"
            :key="perspective.id"
            class="btn btn--live btn--lg"
            type="button"
            @click="enterAs(perspective.id)"
          >
            Entrar como {{ perspective.name }}
          </button>
        </div>

        <p class="auth__note">
          No hay credenciales ni operaciones reales. Datos ficticios.
        </p>
      </div>
    </main>
  </div>
</template>
