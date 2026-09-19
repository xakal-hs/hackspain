<script setup lang="ts">
import {
  LayoutDashboard,
  Store,
  Activity,
  ChevronsUpDown,
  LogOut,
  Check,
} from "@lucide/vue";
import { perspectives, type Perspective } from "~/data/demo";
const props = defineProps<{ role: Perspective; section: string }>();
const profile = computed(() => perspectives.find((p) => p.id === props.role)!);
const open = ref(false);
const session = useCookie<Perspective | null>("xray-demo-role", {
  sameSite: "lax",
});
async function switchRole(role: Perspective) {
  session.value = role;
  open.value = false;
  await navigateTo(`/dashboard/${role}`);
}
async function logout() {
  session.value = null;
  await navigateTo("/");
}
</script>
<template>
  <aside class="workspace-sidebar">
    <NuxtLink to="/" class="brand"
      ><BrandMark /> X-Ray <small>by Embat</small></NuxtLink
    >
    <div class="sidebar-workspace">
      <span class="workspace-dot" />{{ profile.name
      }}<small>Espacio de trabajo</small>
    </div>
    <nav aria-label="Navegación del dashboard">
      <NuxtLink
        :to="`/dashboard/${role}`"
        :class="{ active: section === 'overview' }"
        ><LayoutDashboard :size="18" />Resumen</NuxtLink
      ><NuxtLink
        :to="`/dashboard/${role}?section=marketplace`"
        :class="{ active: section === 'marketplace' }"
        ><Store :size="18" />{{
          role === "empresa" ? "Mi financiación" : "Marketplace"
        }}</NuxtLink
      ><NuxtLink
        :to="`/dashboard/${role}?section=signals`"
        :class="{ active: section === 'signals' }"
        ><Activity :size="18" />{{
          role === "empresa" ? "Mis señales" : "Monitor de señales"
        }}</NuxtLink
      >
    </nav>
    <div class="sidebar-bottom">
      <div class="demo-caption">
        <span class="workspace-dot" />Entorno de demostración<small
          >Datos ficticios · Septiembre 2026</small
        >
      </div>
      <div class="profile-container" @keydown.esc="open = false">
        <div v-if="open" id="perspective-picker" class="profile-picker">
          <p>Cambiar perspectiva</p>
          <button
            v-for="p in perspectives"
            :key="p.id"
            type="button"
            :aria-pressed="p.id === role"
            @click="switchRole(p.id)"
          >
            <span class="role-avatar">{{ p.initials }}</span
            ><span
              >{{ p.name }}<small>{{ p.person }}</small></span
            ><Check v-if="p.id === role" :size="16" /></button
          ><button class="logout-button" type="button" @click="logout">
            <LogOut :size="16" />Salir de la demo
          </button>
        </div>
        <button
          class="profile-button"
          type="button"
          :aria-expanded="open"
          aria-controls="perspective-picker"
          @click="open = !open"
        >
          <span class="role-avatar">{{ profile.initials }}</span
          ><span
            ><strong>{{ profile.person }}</strong
            ><small>Cambiar perspectiva</small></span
          ><ChevronsUpDown :size="16" />
        </button>
      </div>
    </div>
  </aside>
</template>
