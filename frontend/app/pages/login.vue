<script setup lang="ts">
import { ArrowRight, Check } from "@lucide/vue";
import { perspectives, type Perspective } from "~/data/demo";
useHead({ title: "Acceso demo · X-Ray" });
const route = useRoute();
const selected = ref<Perspective>(
  perspectives.find((p) => p.id === route.query.role)?.id ?? "embat",
);
const session = useCookie<Perspective | null>("xray-demo-role", {
  sameSite: "lax",
});
function enter() {
  session.value = selected.value;
  navigateTo(`/dashboard/${selected.value}`);
}
</script>
<template>
  <div class="demo-login">
    <NuxtLink to="/" class="brand"><BrandMark /> X-Ray</NuxtLink>
    <main id="main-content" class="login-panel">
      <span class="landing-tag">Acceso demo</span>
      <h1>¿Desde dónde quieres mirar?</h1>
      <p>
        Elige un perfil para empezar. Podrás cambiarlo desde el panel de usuario
        en cualquier momento.
      </p>
      <form @submit.prevent="enter">
        <fieldset>
          <legend class="sr-only">Selecciona tu perspectiva</legend>
          <label
            v-for="p in perspectives"
            :key="p.id"
            class="login-role"
            :class="{ selected: selected === p.id }"
            ><input
              v-model="selected"
              type="radio"
              name="perspective"
              :value="p.id" /><span class="role-avatar">{{ p.initials }}</span
            ><span
              ><strong>{{ p.name }}</strong
              ><small>{{ p.description }}</small></span
            ><Check v-if="selected === p.id" :size="20" aria-hidden="true"
          /></label>
        </fieldset>
        <button class="button button--primary" type="submit">
          Entrar como {{ perspectives.find((p) => p.id === selected)?.name }}
          <ArrowRight :size="17" />
        </button>
      </form>
      <small>Sesión simulada, sin credenciales ni operaciones reales.</small>
    </main>
    <NuxtLink to="/" class="back-link">Volver a la landing</NuxtLink>
  </div>
</template>
