<script setup lang="ts">
import { Bell, Menu, Search, Settings2, X } from '@lucide/vue'

const route = useRoute()
const mobileMenuOpen = ref(false)
const links = [
  { label: 'Cartera', to: '/cartera' },
  { label: 'Monitor', to: '/monitor' },
  { label: 'Escenarios', to: '/escenarios' },
]

watch(() => route.path, () => {
  mobileMenuOpen.value = false
})
</script>

<template>
  <header class="app-header">
    <a class="skip-link" href="#main-content">Saltar al contenido</a>
    <div class="app-header__inner">
      <NuxtLink to="/" class="brand" aria-label="X-Ray, inicio">
        <BrandMark />
        <span>X-Ray</span>
      </NuxtLink>

      <nav class="main-nav" aria-label="Navegación principal">
        <NuxtLink
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          :class="{ 'is-active': route.path === link.to }"
        >
          {{ link.label }}
        </NuxtLink>
      </nav>

      <div class="header-actions">
        <button
          class="icon-button mobile-menu-button"
          type="button"
          aria-label="Abrir navegación"
          aria-controls="mobile-navigation"
          :aria-expanded="mobileMenuOpen"
          @click="mobileMenuOpen = !mobileMenuOpen"
        >
          <X v-if="mobileMenuOpen" :size="19" aria-hidden="true" />
          <Menu v-else :size="19" aria-hidden="true" />
        </button>
        <button class="icon-button header-search" type="button" aria-label="Buscar empresas">
          <Search :size="18" aria-hidden="true" />
        </button>
        <button class="icon-button" type="button" aria-label="Notificaciones">
          <Bell :size="18" aria-hidden="true" />
          <span class="notification-dot" />
        </button>
        <button class="icon-button header-settings" type="button" aria-label="Configuración">
          <Settings2 :size="18" aria-hidden="true" />
        </button>
        <div class="avatar" aria-label="Perfil de CA">CA</div>
      </div>
    </div>
    <nav v-if="mobileMenuOpen" id="mobile-navigation" class="mobile-nav" aria-label="Navegación móvil">
      <NuxtLink
        v-for="link in links"
        :key="link.to"
        :to="link.to"
        :class="{ 'is-active': route.path === link.to }"
      >
        {{ link.label }}
      </NuxtLink>
    </nav>
  </header>
</template>
