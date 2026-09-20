<script setup lang="ts">
import { currentMonth, perspectiveById, type PerspectiveId } from '~/data/demo'

definePageMeta({
  middleware: [
    function (to) {
      if (!perspectiveById(String(to.params.role))) return navigateTo('/login')
      const session = useCookie<string | null>('xray-demo-role')
      if (!session.value) return navigateTo(`/login?role=${to.params.role}`)
    },
  ],
})

const { selectedId: activeCompanyId } = useSelectedCompany()
const route = useRoute()
const role = computed(() => route.params.role as PerspectiveId)
const profile = computed(() => perspectiveById(role.value)!)

const treasurySections = ['flujo', 'score', 'credito', 'divisa']
const sectionsByRole: Record<PerspectiveId, string[]> = {
  empresa: [...treasurySections, 'ajustes'],
  embat: ['caja', 'crm', 'equipo'],
}

const section = computed(() => {
  const allowed = sectionsByRole[role.value]
  const requested = String(route.query.section || '')
  if (role.value === 'embat' && requested === 'ofertas') return 'crm'
  return allowed.includes(requested) ? requested : allowed[0]!
})

const isTreasury = computed(() => treasurySections.includes(section.value))

const selectedCompany = useState<string>('selected-company-id')
const companyCookie = useCookie<string>('xray-company', { sameSite: 'lax' })
watch(
  () => route.query.empresa,
  (id) => {
    if (role.value !== 'empresa' || typeof id !== 'string' || !/^COMP_\d{4}$/.test(id)) return
    selectedCompany.value = id
    companyCookie.value = id
  },
  { immediate: true },
)

const sectionLabel = computed(
  () =>
    ({
      caja: 'Caja',
      crm: 'Financiación',
      equipo: 'Equipo',
      score: 'X-Ray Score',
      flujo: 'Flujo de caja',
      credito: 'Crédito y caución',
      divisa: 'Divisa Inteligente',
      ajustes: 'Ajustes',
    })[section.value]!,
)

useHead(() => ({ title: `${sectionLabel.value} · ${profile.value.name} · X-Ray` }))

const paneLive = ref(false)
watch(section, () => {
  paneLive.value = true
})

const headline = computed(() =>
  section.value === 'ajustes' ? 'Decide qué empresas quieres recorrer.' : '',
)

const sectionDescription = computed(() =>
  section.value === 'ajustes'
    ? 'Configura el directorio que usarás al recorrer el panel de empresa.'
    : '',
)
</script>

<template>
  <div class="wk">
    <a class="skip-link" href="#main-content">Saltar al contenido</a>
    <WorkspaceSidebar :role="role" :section="section" />

    <!-- Flujo de caja y Crédito y caución son pantallas al estilo de Embat: van a sangre, sin la
         cabecera ni el pie del panel. -->
    <div class="wk__body" :class="{ 'wk__body--bare': section === 'flujo' || section === 'credito' }">
      <header v-if="section !== 'flujo' && section !== 'credito'" class="wk__top">
        <p class="wk__crumb">
          {{ profile.name }}<span aria-hidden="true">/</span>{{ sectionLabel }}
        </p>
        <div class="wk__source">
          <span v-if="role === 'embat'" class="chip chip--neutral">Tesorería real · 20 empresas</span>
          <span class="chip chip--neutral">{{ currentMonth }}</span>
        </div>
      </header>

      <main id="main-content" class="wk__main" tabindex="-1">
        <CompanyDataContext
          v-if="role === 'empresa' && isTreasury && section !== 'flujo' && section !== 'credito' && section !== 'score'"
          :section="section"
        />
        <div
          :key="`${section}-${role === 'empresa' ? activeCompanyId : 'portfolio'}`"
          class="wk__pane"
          :class="{ 'is-live': paneLive }"
        >
          <div v-if="section === 'ajustes'" class="wk__head">
            <h1>{{ headline }}</h1>
            <p>{{ sectionDescription }}</p>
          </div>

          <EmbatCajaBoard v-if="section === 'caja'" />
          <EmbatCrmBoard v-else-if="section === 'crm'" />
          <EmbatEquipoBoard v-else-if="section === 'equipo'" />
          <XRayScoreApp v-else-if="section === 'score'" />
          <FlujoCajaApp v-else-if="section === 'flujo'" />
          <CreditoCaucionApp v-else-if="section === 'credito'" />
          <DivisaInteligenteApp v-else-if="section === 'divisa'" />
          <CompanySettings v-else-if="section === 'ajustes'" />
        </div>

        <footer v-if="section !== 'flujo' && section !== 'credito'" class="wk__foot">
          <template v-if="role === 'embat'">
            Caja operativa y financiera desde Supabase. El CRM se llena cuando una empresa pide financiación y se asigna a un comercial de Equipo.
          </template>
          <template v-else>
            Tesorería de esta empresa. Lo que hagas aquí solo afecta a esta sesión.
          </template>
        </footer>
      </main>
    </div>
  </div>
</template>
