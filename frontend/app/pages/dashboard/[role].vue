<script setup lang="ts">
import { Search } from '@lucide/vue'
import {
  companies as demoCompanies,
  currentMonth,
  decisionLabel,
  euros,
  leadMonths,
  months,
  perspectiveById,
  shapeLabel,
  signed,
  sizeFilterLabel,
  sizeFilters,
  sizeLabel,
  compactEuros,
  type PerspectiveId,
  type SizeBand,
} from '~/data/demo'
import type { Company } from '~/data/demo'
import { portfolioCompanies } from '~/data/portfolio'
import {
  activeCompanies,
  millions,
  modelAllClear,
  modelMetrics,
  modelVersion,
  opsAlerts,
  opsPulse,
  revenueAnnualised,
  revenueGrowth,
  revenueMonth,
  revenueProducts,
  share,
  thousands,
} from '~/data/internal'

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
const portfolioQuery = usePortfolioQuery()
const companies = computed(() => {
  if (role.value !== 'embat') return demoCompanies
  const rows = portfolioQuery.data.value?.companies || []
  return rows.length ? portfolioCompanies(rows) : demoCompanies
})
const portfolioSource = computed(() => portfolioQuery.data.value?.source || 'demo')

/* Vetos primero y avisos después: lo que bloquea se lee antes que lo que solo advierte. */
const overrides = (company: Company) => [...(company.vetos || []), ...(company.avisos || [])]

/* La empresa solo ve su tesorería propia: tres pantallas que traen su propio
 * encabezado. Embat ve la cartera y, además, las vistas internas, que miran a
 * Embat y no a una empresa: revenue propio, alertas del ecosistema y salud del
 * modelo. Cada perspectiva entra por su primera sección. */
const treasurySections = ['flujo', 'score', 'colchon', 'divisa']
const sectionsByRole: Record<PerspectiveId, string[]> = {
  empresa: [...treasurySections, 'ajustes'],
  embat: ['resumen', 'cartera', 'senales', 'ofertas', 'monitor', 'revenue', 'modelo'],
}

const section = computed(() => {
  const allowed = sectionsByRole[role.value]
  const requested = String(route.query.section || '')
  return allowed.includes(requested) ? requested : allowed[0]!
})

const isTreasury = computed(() => treasurySections.includes(section.value))

/* En la demo, `?empresa=COMP_0829` deja preparada cada pestaña del navegador con su caso. */
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
      resumen: 'Resumen',
      cartera: 'Cartera',
      senales: 'Señales',
      ofertas: 'Mercado',
      score: 'X-Ray Score',
      flujo: 'Flujo de caja',
      colchon: 'Colchón Dinámico',
      divisa: 'Divisa Inteligente',
      monitor: 'Monitor operativo',
      revenue: 'Revenue por producto',
      modelo: 'Métricas del modelo',
      ajustes: 'Ajustes',
    })[section.value]!,
)

useHead(() => ({ title: `${sectionLabel.value} · ${profile.value.name} · X-Ray` }))

/* The pane only settles after a tab change, never on the first paint. */
const paneLive = ref(false)
watch(section, () => {
  paneLive.value = true
})

/* A company view always has a subject, picked from the portfolio. */
const pickedId = useState('wk-picked', () => 'iberica')
const subject = computed(
  () => companies.value.find((company) => company.id === pickedId.value) || companies.value[0]!,
)

watch(
  companies,
  (rows) => {
    if (role.value === 'embat' && !rows.some((company) => company.id === pickedId.value))
      pickedId.value = rows[0]?.id || 'iberica'
  },
  { immediate: true },
)

const query = ref('')
const sizeFilter = ref<SizeBand | 'todas'>('todas')
const groupFilter = ref('')
const sectorFilter = ref('')

const groupOptions = computed(() => {
  const names = companies.value
    .filter((company) => sizeFilter.value === 'todas' || company.size === sizeFilter.value)
    .filter((company) => !sectorFilter.value || company.sector === sectorFilter.value)
    .map((company) => company.group)
  return [...new Set(names)].sort((a, b) => a.localeCompare(b, 'es'))
})

const sectorOptions = computed(() => {
  const names = companies.value
    .filter((company) => sizeFilter.value === 'todas' || company.size === sizeFilter.value)
    .filter((company) => !groupFilter.value || company.group === groupFilter.value)
    .map((company) => company.sector)
  return [...new Set(names)].sort((a, b) => a.localeCompare(b, 'es'))
})

const visible = computed(() => {
  const needle = query.value.toLocaleLowerCase('es').trim()
  return companies.value.filter((company) => {
    if (sizeFilter.value !== 'todas' && company.size !== sizeFilter.value) return false
    if (groupFilter.value && company.group !== groupFilter.value) return false
    if (sectorFilter.value && company.sector !== sectorFilter.value) return false
    if (
      needle &&
      !`${company.name} ${company.sector} ${company.group}`
        .toLocaleLowerCase('es')
        .includes(needle)
    ) {
      return false
    }
    return true
  })
})

const filtersOn = computed(
  () =>
    sizeFilter.value !== 'todas' ||
    Boolean(groupFilter.value) ||
    Boolean(sectorFilter.value) ||
    Boolean(query.value.trim()),
)

function clearFilters() {
  sizeFilter.value = 'todas'
  groupFilter.value = ''
  sectorFilter.value = ''
  query.value = ''
}

watch(groupOptions, (options) => {
  if (groupFilter.value && !options.includes(groupFilter.value)) groupFilter.value = ''
})

watch(sectorOptions, (options) => {
  if (sectorFilter.value && !options.includes(sectorFilter.value)) sectorFilter.value = ''
})

const changed = computed(() =>
  [...companies.value]
    .filter((company) => Math.abs(company.delta3) > 0)
    .sort((a, b) => Math.abs(b.delta3) - Math.abs(a.delta3)),
)

const detectedMonth = computed(() =>
  subject.value.detectedAt !== null ? months[subject.value.detectedAt] : null,
)
const levelMonth = computed(() =>
  subject.value.levelAt !== null ? months[subject.value.levelAt] : null,
)

const headline = computed(() =>
  ({
    resumen: 'Quién se mueve y desde cuándo.',
    cartera: 'Las grandes, partidas por grupo y por sector.',
    senales: 'Qué se movió, cuánto pesó y cuándo lo dijimos.',
    ofertas: 'Capital contra oportunidad.',
    monitor: 'Todo el ecosistema, en una pantalla.',
    revenue: 'De dónde sale el dinero de este mes.',
    modelo: 'Si el modelo sigue acertando, y por cuánto.',
    ajustes: 'Decide qué empresas quieres recorrer.',
  })[section.value]!,
)

const sectionDescription = computed(() =>
  section.value === 'ajustes'
    ? 'Configura el directorio que usarás al recorrer el panel de empresa.'
    : profile.value.job,
)

const leadProduct = computed(
  () => [...revenueProducts].sort((a, b) => b.amount - a.amount)[0]!,
)

const openAlerts = computed(() => opsAlerts.filter((a) => a.tone === 'crimson'))

const connected = activeCompanies.toLocaleString('es-ES')
</script>

<template>
  <div class="wk">
    <a class="skip-link" href="#main-content">Saltar al contenido</a>
    <WorkspaceSidebar :role="role" :section="section" />

    <!-- Flujo de caja es un clon de la pantalla de Embat: va a sangre, sin la cabecera ni el pie del panel. -->
    <div class="wk__body" :class="{ 'wk__body--bare': section === 'flujo' }">
      <header v-if="section !== 'flujo'" class="wk__top">
        <p class="wk__crumb">
          {{ profile.name }}<span aria-hidden="true">/</span>{{ sectionLabel }}
        </p>
        <div class="wk__source">
          <span v-if="role === 'embat'" class="chip chip--neutral">
            {{
              portfolioSource === 'api'
                ? 'Score real · condiciones simuladas'
                : portfolioSource === 'supabase'
                  ? 'Tesorería real · producto simulado'
                  : 'Datos de demostración'
            }}
          </span>
          <span class="chip chip--neutral">{{ currentMonth }}</span>
        </div>
      </header>

      <main id="main-content" class="wk__main" tabindex="-1">
        <CompanyDataContext v-if="role === 'empresa' && isTreasury && section !== 'flujo'" :section="section" />
        <div :key="`${section}-${role === 'empresa' ? activeCompanyId : 'portfolio'}`" class="wk__pane" :class="{ 'is-live': paneLive }">
        <div v-if="!isTreasury" class="wk__head">
          <h1>{{ headline }}</h1>
          <p>{{ sectionDescription }}</p>
        </div>

        <!-- Resumen -->
        <div v-if="section === 'resumen'" class="wk__grid">
          <section class="panel span-5 verdict">
            <h2 class="panel__title">La decisión</h2>
            <div class="verdict__read">
              <b>{{ subject.score }}</b>
              <span>
                <DecisionTag :decision="subject.decision" />
                <em
                  :data-dir="subject.delta3 > 0 ? 'up' : subject.delta3 < 0 ? 'down' : 'flat'"
                  >{{ signed(subject.delta3) }} puntos en tres meses</em
                >
              </span>
            </div>
            <p class="verdict__shape">{{ shapeLabel[subject.shape] }}</p>
            <!-- Cuando manda un veto, la acción ya es su texto: no se repite debajo. -->
            <p v-if="subject.action !== overrides(subject)[0]?.texto" class="verdict__action">
              {{ subject.action }}
            </p>

            <!-- Un veto manda sobre la nota, así que tiene que poder discutirse: va con su
                 explicación y con si se levanta enseñando un papel. -->
            <ul v-if="overrides(subject).length" class="vetos">
              <li
                v-for="veto in overrides(subject)"
                :key="veto.codigo"
                :data-blocks="veto.bloquea"
              >
                <p class="vetos__head">
                  <b>{{ veto.etiqueta }}</b>
                  <span class="chip" :class="veto.bloquea ? 'chip--crimson' : 'chip--amber'">{{
                    veto.bloquea ? 'manda sobre la nota' : 'aviso'
                  }}</span>
                </p>
                <p class="vetos__why">{{ veto.texto }}</p>
                <p v-if="veto.levantable" class="vetos__lift">
                  Se levanta con el documento que lo justifique.
                </p>
              </li>
            </ul>
          </section>

          <section class="panel span-4 ahead">
            <h2 class="panel__title">La ventaja</h2>
            <template v-if="detectedMonth && levelMonth">
              <p class="ahead__read">
                {{ leadMonths(subject) }}<small>meses</small>
              </p>
              <p class="ahead__why">
                Marcamos la trayectoria en {{ detectedMonth }}. El score no
                cambió de tramo hasta {{ levelMonth }}.
              </p>
            </template>
            <template v-else>
              <p class="ahead__read ahead__read--none">—</p>
              <p class="ahead__why">
                Nada que anticipar: {{ subject.name }} no ha cambiado de tramo
                en 24 meses.
              </p>
            </template>
          </section>

          <section class="panel span-3 cover">
            <h2 class="panel__title">Lo que podemos ver</h2>
            <dl>
              <div>
                <dt>Contabilidad</dt>
                <dd>{{ subject.erp ? 'Conectada' : 'Sin conectar' }}</dd>
              </div>
              <div>
                <dt>Historial</dt>
                <dd>{{ subject.monthsConnected }} meses</dd>
              </div>
              <div>
                <dt>Movimientos con factura</dt>
                <dd>{{ Math.round(subject.coverage * 100) }} %</dd>
              </div>
            </dl>
            <p>Esto no mide su salud. Mide cuánto podemos afirmar.</p>
          </section>

          <section class="panel span-12 traject">
            <header class="panel__bar">
              <h2 class="panel__title">Trayectoria</h2>
              <div class="panel__who">
                <strong>{{ subject.name }}</strong>
                <span>24 meses de tesorería · previsión a tres meses</span>
              </div>
              <span class="chip chip--ahead">Previsión</span>
            </header>
            <TrajectoryChart :company="subject" />
          </section>

          <section class="panel span-12">
            <header class="panel__bar">
              <h2 class="panel__title">Frente al sector</h2>
              <span class="chip chip--neutral">{{ subject.sector }}</span>
            </header>
            <!-- Embat, que ya opera la cartera entera, ve y puede elegir cada peer. -->
            <SectorCompare
              :company="subject"
              selectable
              :anonymous="false"
              @select="pickedId = $event"
            />
          </section>

          <section class="panel span-7 changed">
            <header class="panel__bar">
              <h2 class="panel__title">Qué ha cambiado</h2>
              <span class="chip chip--neutral">Peso sobre el movimiento</span>
            </header>
            <p class="changed__why">{{ subject.why }}</p>
            <SignalBars v-if="subject.signals" :signals="subject.signals" />
            <p v-else class="empty">
              Sin contabilidad conectada solo vemos los bancos, así que no
              podemos repartir el movimiento entre cobros, margen y deuda.
              Pídeles la conexión del ERP.
            </p>
          </section>

          <section class="panel span-5 cash">
            <header class="panel__bar">
              <h2 class="panel__title">El dinero de la cuenta</h2>
            </header>
            <p class="cash__read">
              {{ subject.runway.now.toLocaleString('es-ES') }}<small>meses cubiertos</small>
            </p>
            <p class="cash__was">
              Eran {{ subject.runway.prev.toLocaleString('es-ES') }} meses en
              marzo. Cobra a {{ subject.dso.now || '—' }} días y paga a
              {{ subject.dpo.now || '—' }}.
            </p>
            <FlowBars v-if="subject.flows" :flows="subject.flows" />
            <p v-else class="empty">
              Solo tenemos once meses de banco para esta empresa. No dibujamos
              lo que no podemos reconstruir.
            </p>
          </section>

          <section class="panel span-12">
            <header class="panel__bar">
              <h2 class="panel__title">Cartera</h2>
              <NuxtLink class="btn btn--quiet" :to="`/dashboard/${role}?section=cartera`"
                >Abrir la cartera completa</NuxtLink
              >
            </header>
            <div class="filters">
              <div class="filters__field">
                <span id="overview-size">Tamaño</span>
                <div class="seg" role="radiogroup" aria-labelledby="overview-size">
                  <button
                    v-for="size in sizeFilters"
                    :key="size"
                    type="button"
                    role="radio"
                    :aria-checked="sizeFilter === size"
                    :class="{ 'is-on': sizeFilter === size }"
                    @click="sizeFilter = size"
                  >
                    {{ sizeFilterLabel[size] }}
                  </button>
                </div>
              </div>
              <label class="filters__field">
                Grupo
                <select v-model="groupFilter" aria-label="Filtrar por grupo">
                  <option value="">Todos los grupos</option>
                  <option v-for="group in groupOptions" :key="group" :value="group">
                    {{ group }}
                  </option>
                </select>
              </label>
              <label class="filters__field">
                Sector
                <select v-model="sectorFilter" aria-label="Filtrar por sector">
                  <option value="">Todos los sectores</option>
                  <option v-for="sector in sectorOptions" :key="sector" :value="sector">
                    {{ sector }}
                  </option>
                </select>
              </label>
            </div>
            <CompanyTable
              compact
              :companies="visible"
              :selected-id="subject.id"
              @select="pickedId = $event"
            />
          </section>

        </div>

        <!-- Cartera -->
        <div v-else-if="section === 'cartera'" class="wk__grid">
          <section class="panel span-8 list">
            <header class="panel__bar">
              <h2 class="panel__title">Empresas</h2>
              <label class="search">
                <Search :size="15" aria-hidden="true" />
                <input
                  v-model="query"
                  type="search"
                  placeholder="Buscar empresa, sector o grupo"
                  aria-label="Buscar empresa, sector o grupo"
                />
              </label>
            </header>
            <div class="filters">
              <div class="filters__field">
                <span id="filter-size">Tamaño</span>
                <div class="seg" role="radiogroup" aria-labelledby="filter-size">
                  <button
                    v-for="size in sizeFilters"
                    :key="size"
                    type="button"
                    role="radio"
                    :aria-checked="sizeFilter === size"
                    :class="{ 'is-on': sizeFilter === size }"
                    @click="sizeFilter = size"
                  >
                    {{ sizeFilterLabel[size] }}
                  </button>
                </div>
              </div>
              <label class="filters__field">
                Grupo
                <select v-model="groupFilter" aria-label="Filtrar por grupo">
                  <option value="">Todos los grupos</option>
                  <option v-for="group in groupOptions" :key="group" :value="group">
                    {{ group }}
                  </option>
                </select>
              </label>
              <label class="filters__field">
                Sector
                <select v-model="sectorFilter" aria-label="Filtrar por sector">
                  <option value="">Todos los sectores</option>
                  <option v-for="sector in sectorOptions" :key="sector" :value="sector">
                    {{ sector }}
                  </option>
                </select>
              </label>
              <button
                v-if="filtersOn"
                class="filters__clear"
                type="button"
                @click="clearFilters"
              >
                Quitar filtros
              </button>
            </div>
            <CompanyTable
              :companies="visible"
              :selected-id="subject.id"
              @select="pickedId = $event"
            />
            <p v-if="!visible.length" class="empty">
              Ninguna empresa coincide con este corte. Prueba otro tamaño, grupo
              o sector.
            </p>
            <footer class="list__foot">
              <span>{{ visible.length }} de {{ companies.length }} empresas</span>
              <span>Las grandes se parten por grupo; el sector, aparte</span>
            </footer>
          </section>

          <section class="panel span-4 sheet">
            <header class="panel__bar">
              <h2 class="panel__title">{{ subject.name }}</h2>
              <DecisionTag :decision="subject.decision" />
            </header>
            <p class="sheet__sector">
              {{ subject.sector }} · {{ subject.group }} ·
              {{ sizeLabel[subject.size] }}
            </p>
            <div class="sheet__read">
              <b>{{ subject.score }}</b>
              <span>
                <em
                  :data-dir="subject.delta3 > 0 ? 'up' : subject.delta3 < 0 ? 'down' : 'flat'"
                  >{{ signed(subject.delta3) }} en tres meses</em
                >
                <small>{{ signed(subject.delta12) }} en doce meses</small>
              </span>
            </div>
            <h3>{{ subject.headline }}</h3>
            <p class="sheet__why">{{ subject.why }}</p>
            <TrajectoryChart :company="subject" />
            <dl class="sheet__terms">
              <div>
                <dt>Importe orientativo</dt>
                <dd>{{ euros(subject.amount) }}</dd>
              </div>
              <div>
                <dt>Tipo sugerido</dt>
                <dd>{{ subject.rate }} %</dd>
              </div>
              <div>
                <dt>Plazo</dt>
                <dd>{{ subject.term }} meses</dd>
              </div>
              <div>
                <dt>Caja cubierta</dt>
                <dd>{{ subject.runway.now.toLocaleString('es-ES') }} meses</dd>
              </div>
            </dl>
            <p class="sheet__action">{{ subject.action }}</p>
          </section>
        </div>

        <!-- Señales -->
        <section v-else-if="section === 'senales'" class="panel signals">
          <header class="panel__bar">
            <h2 class="panel__title">Monitor de cambios</h2>
            <span class="chip chip--neutral">Últimos tres meses</span>
          </header>
          <ol>
            <li v-for="company in changed" :key="company.id">
              <div class="signals__id">
                <b>{{ company.name }}</b>
                <span>{{ company.sector }}</span>
              </div>
              <span
                class="signals__delta"
                :data-dir="company.delta3 > 0 ? 'up' : 'down'"
                >{{ signed(company.delta3) }}<small>pts</small></span
              >
              <Sparkline
                :values="company.history.slice(12)"
                :domain="[34, 96]"
                :tone="company.delta3 > 2 ? 'mint' : company.delta3 < -5 ? 'crimson' : 'muted'"
                :label="`${company.name}: ${company.history.slice(12).join(', ')}`"
              />
              <div class="signals__read">
                <b>{{ shapeLabel[company.shape] }}</b>
                <span>{{ company.headline }}</span>
              </div>
              <span v-if="leadMonths(company)" class="chip chip--ahead"
                >{{ leadMonths(company) }} meses antes</span
              >
              <span v-else class="chip chip--neutral">Sin cambio de tramo</span>
              <DecisionTag :decision="company.decision" size="sm" />
            </li>
          </ol>
          <footer class="list__foot">
            <span>Ordenado por cuánto se movió el score, en las dos direcciones</span>
          </footer>
        </section>

        <!-- Tesorería propia: el mock trae su propio encabezado y su propio
             layout, así que va sin la rejilla del panel. -->
        <XRayScoreApp v-else-if="section === 'score'" />
        <FlujoCajaApp v-else-if="section === 'flujo'" />
        <ColchonDinamicoApp v-else-if="section === 'colchon'" />
        <DivisaInteligenteApp v-else-if="section === 'divisa'" />
        <CompanySettings v-else-if="section === 'ajustes'" />

        <!-- Monitor operativo: Embat mirándose a sí mismo. -->
        <div v-else-if="section === 'monitor'" class="wk__grid">
          <section class="panel span-8 pulse">
            <header class="panel__bar">
              <h2 class="panel__title">El pulso del mes</h2>
              <span class="chip chip--neutral">Mes en curso</span>
            </header>
            <dl>
              <div
                v-for="reading in opsPulse"
                :key="reading.id"
                :data-tone="reading.tone"
              >
                <dt>{{ reading.label }}</dt>
                <dd class="pulse__value">
                  {{ reading.value
                  }}<small v-if="reading.unit">{{ reading.unit }}</small>
                </dd>
                <dd class="pulse__note">{{ reading.note }}</dd>
              </div>
            </dl>
            <p class="pulse__read">
              Siete avisos sobre {{ connected }} empresas conectadas. Los tres
              que siguen sin contacto son los que cuestan dinero: el resto ya
              está en manos de éxito de cliente.
            </p>
          </section>

          <section class="panel span-4 feed">
            <header class="panel__bar">
              <h2 class="panel__title">Alertas abiertas</h2>
              <NuxtLink
                class="btn btn--quiet"
                :to="`/dashboard/${role}?section=senales`"
                >Ver las señales</NuxtLink
              >
            </header>
            <AlertFeed :alerts="opsAlerts" />
            <footer class="list__foot">
              <span
                >{{ openAlerts.length }} por deterioro,
                {{ opsAlerts.length - openAlerts.length }} por oportunidad</span
              >
            </footer>
          </section>

          <section class="panel span-8">
            <header class="panel__bar">
              <h2 class="panel__title">Revenue del mes</h2>
              <span class="chip chip--mint">{{ revenueGrowth }} sobre agosto</span>
              <NuxtLink
                class="btn btn--quiet"
                :to="`/dashboard/${role}?section=revenue`"
                >Abrir el desglose</NuxtLink
              >
            </header>
            <RevenueSplit compact :products="revenueProducts" />
          </section>

          <section class="panel span-12">
            <header class="panel__bar">
              <h2 class="panel__title">Salud del modelo</h2>
              <span v-if="modelAllClear" class="chip chip--mint"
                >Todas por encima del objetivo</span
              >
              <NuxtLink
                class="btn btn--quiet"
                :to="`/dashboard/${role}?section=modelo`"
                >Abrir las métricas</NuxtLink
              >
            </header>
            <ModelMetrics compact :metrics="modelMetrics" />
          </section>
        </div>

        <!-- Revenue por producto -->
        <div v-else-if="section === 'revenue'" class="wk__grid">
          <section class="panel span-8">
            <header class="panel__bar">
              <h2 class="panel__title">Reparto del mes</h2>
              <span class="chip chip--mint">{{ revenueGrowth }} sobre agosto</span>
            </header>
            <p class="lead-line">
              Cuatro formas de cobrar por lo mismo: ver la tesorería antes que
              nadie. La suscripción es la única que no depende de que la empresa
              mueva dinero.
            </p>
            <RevenueSplit :products="revenueProducts" />
          </section>

          <section class="panel span-4 runrate">
            <h2 class="panel__title">Si el mes se repitiera</h2>
            <p class="runrate__read">
              {{ millions(revenueAnnualised) }}<small>al año</small>
            </p>
            <p class="runrate__why">
              Es el mes en curso multiplicado por doce, no una previsión del
              modelo. Lo ponemos porque es la cifra que se cita fuera, no porque
              creamos que septiembre se repite.
            </p>
            <dl>
              <div>
                <dt>Mes en curso</dt>
                <dd>{{ thousands(revenueMonth) }}</dd>
              </div>
              <div>
                <dt>Producto que más pesa</dt>
                <dd>
                  {{ leadProduct.label }} ·
                  {{ share(leadProduct.amount) }} %
                </dd>
              </div>
              <div>
                <dt>Empresas activas</dt>
                <dd>{{ connected }}</dd>
              </div>
            </dl>
          </section>
        </div>

        <!-- Métricas del modelo -->
        <div v-else-if="section === 'modelo'" class="wk__grid">
          <section class="panel panel--ink span-12 model">
            <header class="panel__bar">
              <h2 class="panel__title">Salud del modelo</h2>
              <div class="panel__who">
                <strong>{{ modelVersion }}</strong>
                <span
                  >Medido sobre las {{ connected }} empresas conectadas,
                  ventana de 24 meses</span
                >
              </div>
              <span v-if="modelAllClear" class="chip chip--mint"
                >Todas por encima del objetivo</span
              >
              <span v-else class="chip chip--amber">Alguna por debajo</span>
            </header>
            <ModelMetrics :metrics="modelMetrics" />
          </section>

          <section class="panel span-12">
            <header class="panel__bar">
              <h2 class="panel__title">Por qué estas cinco y no otras</h2>
            </header>
            <p class="lead-line">
              Las dos primeras dicen si el orden es correcto; la tercera, si
              llega con tiempo; la cuarta, si callamos cuando toca. La quinta
              existe para poder cerrar el producto: si el modelo no bate a
              repetir el último mes, no hay nada que vender.
            </p>
          </section>
        </div>

        <!-- Ofertas -->
        <div v-else class="wk__grid">
          <section class="panel span-12 offers">
            <header class="panel__bar">
              <h2 class="panel__title">Dónde colocar los próximos 100.000 €</h2>
              <span class="chip chip--neutral">{{ companies.length }} oportunidades</span>
            </header>
            <p class="lead-line">
              Ordenado por lo que un prestamista gana descontando el riesgo que
              vemos en la caja. Las de «no prestar» aparecen para que quede
              claro por qué no.
            </p>
            <article
              v-for="company in companies"
              :key="company.id"
              :class="{ 'is-out': company.decision === 'no-prestar' }"
            >
              <div class="offers__bank">
                <b>{{ company.name }}</b>
                <span>{{ company.headline }}</span>
              </div>
              <dl>
                <div>
                  <dt>Score</dt>
                  <dd>{{ company.score }}</dd>
                </div>
                <div>
                  <dt>Tipo sugerido</dt>
                  <dd>{{ company.rate }} %</dd>
                </div>
                <div>
                  <dt>Importe</dt>
                  <dd>{{ compactEuros(company.amount) }}</dd>
                </div>
                <div>
                  <dt>Decisión</dt>
                  <dd>{{ decisionLabel[company.decision] }}</dd>
                </div>
              </dl>
            </article>
          </section>
        </div>

        </div>

        <footer v-if="section !== 'flujo'" class="wk__foot">
          <template v-if="role === 'embat' && portfolioSource === 'api'">
            Score, decisión, tesorería y flujos vienen del modelo X-Ray sobre las
            1.286 empresas. Nombres, sectores y condiciones de oferta son ficticios.
          </template>
          <template v-else-if="role === 'embat' && portfolioSource === 'supabase'">
            Tesorería desde Supabase. Score, nombres, sectores, decisiones y
            condiciones todavía son simulados.
          </template>
          <template v-else>
            Cartera y condiciones ficticias. Lo que hagas aquí solo afecta a
            esta sesión.
          </template>
        </footer>
      </main>
    </div>
    <AgentChat :role="role" />
  </div>
</template>
