<script setup lang="ts">
import { Check, Search } from '@lucide/vue'
import {
  companies as demoCompanies,
  currentMonth,
  decisionLabel,
  euros,
  initialOffers,
  leadCompany,
  leadMonths,
  months,
  perspectiveById,
  shapeLabel,
  signed,
  sizeFilterLabel,
  sizeFilters,
  sizeLabel,
  compactEuros,
  type Offer,
  type PerspectiveId,
  type SizeBand,
} from '~/data/demo'
import { portfolioCompanies } from '~/data/portfolio'

definePageMeta({
  middleware: [
    function (to) {
      if (!perspectiveById(String(to.params.role))) return navigateTo('/login')
      const session = useCookie<string | null>('xray-demo-role')
      if (!session.value) return navigateTo(`/login?role=${to.params.role}`)
    },
  ],
})

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

/* Las pantallas de tesorería propia traen su propio encabezado y solo
 * existen para la perspectiva empresa. */
const treasurySections = ['score', 'colchon', 'divisa']
const allowed = ['resumen', 'cartera', 'senales', 'ofertas', ...treasurySections]
const section = computed(() => {
  const requested = String(route.query.section || 'resumen')
  if (!allowed.includes(requested)) return 'resumen'
  if (requested === 'cartera' && role.value === 'empresa') return 'resumen'
  if (treasurySections.includes(requested) && role.value !== 'empresa')
    return 'resumen'
  return requested
})

const isTreasury = computed(() => treasurySections.includes(section.value))

const sectionLabel = computed(
  () =>
    ({
      resumen: 'Resumen',
      cartera: 'Cartera',
      senales: role.value === 'empresa' ? 'Mis señales' : 'Señales',
      ofertas: role.value === 'empresa' ? 'Mis ofertas' : 'Mercado',
      score: 'X-Ray Score',
      colchon: 'Colchón Dinámico',
      divisa: 'Divisa Inteligente',
    })[section.value]!,
)

useHead(() => ({ title: `${sectionLabel.value} · ${profile.value.name} · X-Ray` }))

/* The pane only settles after a tab change, never on the first paint. */
const paneLive = ref(false)
watch(section, () => {
  paneLive.value = true
})

/* A company view always has a subject. For the company perspective it is fixed;
 * Embat picks it from the portfolio. */
const pickedId = useState('wk-picked', () => 'iberica')
const subject = computed(() =>
  role.value === 'empresa'
    ? leadCompany
    : companies.value.find((company) => company.id === pickedId.value) || companies.value[0]!,
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

const offers = useState<Offer[]>('wk-offers', () =>
  initialOffers.map((offer) => ({ ...offer })),
)
const notice = ref('')
const confirming = ref<string | null>(null)

function acceptOffer(id: string) {
  const offer = offers.value.find((item) => item.id === id)
  if (offer) offer.accepted = true
  confirming.value = null
  notice.value = 'Oferta aceptada en la demo. No se ha contratado nada.'
}

watch(
  () => route.fullPath,
  () => {
    notice.value = ''
    confirming.value = null
  },
)

const detectedMonth = computed(() =>
  subject.value.detectedAt !== null ? months[subject.value.detectedAt] : null,
)
const levelMonth = computed(() =>
  subject.value.levelAt !== null ? months[subject.value.levelAt] : null,
)

const cheapest = computed(() =>
  [...offers.value].sort(
    (a, b) => Number(a.rate.replace(',', '.')) - Number(b.rate.replace(',', '.')),
  )[0],
)

const headline = computed(() =>
  ({
    resumen:
      role.value === 'empresa'
        ? 'Esto es lo que ve quien te va a prestar.'
        : 'Quién se mueve y desde cuándo.',
    cartera: 'Las grandes, partidas por grupo y por sector.',
    senales: 'Qué se movió, cuánto pesó y cuándo lo dijimos.',
    ofertas:
      role.value === 'empresa'
        ? 'Tres ofertas sobre la misma empresa.'
        : 'Capital contra oportunidad.',
  })[section.value]!,
)
</script>

<template>
  <div class="wk">
    <a class="skip-link" href="#main-content">Saltar al contenido</a>
    <WorkspaceSidebar :role="role" :section="section" />

    <div class="wk__body">
      <header class="wk__top">
        <p class="wk__crumb">
          {{ profile.name }}<span aria-hidden="true">/</span>{{ sectionLabel }}
        </p>
        <div class="wk__source">
          <span v-if="role === 'embat'" class="chip chip--neutral">
            {{
              portfolioSource === 'supabase'
                ? 'Tesorería real · producto simulado'
                : 'Datos de demostración'
            }}
          </span>
          <span class="chip chip--neutral">{{ currentMonth }}</span>
        </div>
      </header>

      <main id="main-content" class="wk__main" tabindex="-1">
        <div :key="section" class="wk__pane" :class="{ 'is-live': paneLive }">
        <div v-if="!isTreasury" class="wk__head">
          <h1>{{ headline }}</h1>
          <p v-if="role === 'empresa'">
            {{ leadCompany.name }} · {{ leadCompany.sector }}
          </p>
          <p v-else>{{ profile.job }}</p>
        </div>

        <p v-if="notice" class="notice" role="status">
          <Check :size="16" aria-hidden="true" />{{ notice }}
        </p>

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
            <p class="verdict__action">{{ subject.action }}</p>
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
            <!-- La empresa solo ve la mediana del sector; Embat, que ya opera
                 la cartera entera, sigue viendo y pudiendo elegir cada peer. -->
            <SectorCompare
              :company="subject"
              :selectable="role !== 'empresa'"
              :anonymous="role === 'empresa'"
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

          <section v-if="role !== 'empresa'" class="panel span-12">
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

          <section v-else class="panel span-12">
            <header class="panel__bar">
              <h2 class="panel__title">Tus ofertas</h2>
              <NuxtLink class="btn btn--quiet" :to="`/dashboard/${role}?section=ofertas`"
                >Comparar las {{ offers.length }} ofertas</NuxtLink
              >
            </header>
            <p class="lead-line">
              La más barata está al {{ cheapest?.rate }} % a
              {{ cheapest?.months }} meses. Hace un trimestre, con 85 puntos,
              este mismo importe se ofrecía al 5,6 %.
            </p>
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
        <XRayScoreApp v-else-if="section === 'score'" :chrome="false" />
        <ColchonDinamicoApp v-else-if="section === 'colchon'" :chrome="false" />
        <DivisaInteligenteApp v-else-if="section === 'divisa'" :chrome="false" />

        <!-- Ofertas -->
        <div v-else class="wk__grid">
          <section v-if="role === 'empresa'" class="panel span-12 offers">
            <header class="panel__bar">
              <h2 class="panel__title">Ofertas recibidas</h2>
              <span class="chip chip--amber">Tu score bajó 14 puntos</span>
            </header>
            <p class="lead-line">
              Los tres tipos son más altos que en junio porque tu caja cubre
              menos tiempo. Bajar los días de pago a proveedores es lo que más
              pesa para recuperarlos.
            </p>
            <article v-for="offer in offers" :key="offer.id">
              <div class="offers__bank">
                <b>{{ offer.bank }}</b>
                <span>{{ offer.note }}</span>
              </div>
              <dl>
                <div>
                  <dt>Importe</dt>
                  <dd>{{ euros(offer.amount) }}</dd>
                </div>
                <div>
                  <dt>Tipo anual</dt>
                  <dd>{{ offer.rate }} %</dd>
                </div>
                <div>
                  <dt>Plazo</dt>
                  <dd>{{ offer.months }} meses</dd>
                </div>
                <div>
                  <dt>Intereses totales</dt>
                  <dd>
                    {{
                      euros(
                        Math.round(
                          (offer.amount *
                            Number(offer.rate.replace(',', '.')) *
                            offer.months) /
                            1200,
                        ),
                      )
                    }}
                  </dd>
                </div>
              </dl>
              <button
                class="btn"
                :class="offer.accepted ? 'btn--quiet' : 'btn--live'"
                type="button"
                :disabled="offer.accepted"
                @click="confirming = offer.id"
              >
                {{ offer.accepted ? 'Aceptada' : 'Aceptar' }}
              </button>
              <div v-if="confirming === offer.id" class="offers__confirm">
                <span
                  >Vas a aceptar {{ euros(offer.amount) }} al
                  {{ offer.rate }} % en la demo.</span
                >
                <button class="btn btn--live" type="button" @click="acceptOffer(offer.id)">
                  Aceptar la oferta
                </button>
                <button class="btn btn--quiet" type="button" @click="confirming = null">
                  Cancelar
                </button>
              </div>
            </article>
          </section>

          <section v-else class="panel span-12 offers">
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

        <footer class="wk__foot">
          <template v-if="role === 'embat' && portfolioSource === 'supabase'">
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
  </div>
</template>
