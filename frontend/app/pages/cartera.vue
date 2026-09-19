<script setup lang="ts">
import { ArrowRight, LayoutList, RefreshCw, SlidersHorizontal } from '@lucide/vue'

useHead({ title: 'Cartera · X-Ray' })

const workspace = useWorkspaceStore()
const portfolioQuery = usePortfolioQuery()
await portfolioQuery.suspense()
const { data, isPending, isError, refetch, isFetching } = portfolioQuery

const companies = computed(() => data.value?.companies ?? [])
const healthyCount = computed(() => companies.value.filter((company) => company.band === 'sano').length)
const watchCount = computed(() => companies.value.filter((company) => company.band === 'vigilar').length)
const riskCount = computed(() => companies.value.filter((company) => company.band === 'riesgo').length)
</script>

<template>
  <div class="app-shell">
    <AppHeader />

    <main id="main-content" tabindex="-1">
      <section class="page-intro">
        <div>
          <p class="section-kicker">Decisión de cartera</p>
          <h1>Vea el cambio antes de que sea evidente.</h1>
          <p class="page-intro__copy">
            X-Ray convierte la tesorería de cada empresa en una señal de crédito explicable,
            con trayectoria, anticipación y una acción clara.
          </p>
        </div>
        <div class="page-intro__actions">
          <button class="button button--secondary" type="button" @click="workspace.toggleDensity">
            <LayoutList :size="17" aria-hidden="true" />
            {{ workspace.compactMode ? 'Vista cómoda' : 'Vista compacta' }}
          </button>
          <NuxtLink to="/escenarios" class="button button--primary">
            Probar escenario <ArrowRight :size="17" aria-hidden="true" />
          </NuxtLink>
        </div>
      </section>

      <DecisionPreview />

      <section class="portfolio-section" aria-labelledby="portfolio-title">
        <div class="section-heading">
          <div>
            <p class="section-kicker">Cartera</p>
            <h2 id="portfolio-title">Empresas que requieren una decisión</h2>
          </div>
          <div class="section-controls">
            <div class="period-control" aria-label="Horizonte de análisis">
              <button
                v-for="period in (['1m', '3m', '6m'] as const)"
                :key="period"
                type="button"
                :class="{ 'is-active': workspace.selectedPeriod === period }"
                @click="workspace.setPeriod(period)"
              >
                {{ period }}
              </button>
            </div>
            <button class="icon-button icon-button--bordered" type="button" aria-label="Filtrar cartera">
              <SlidersHorizontal :size="17" aria-hidden="true" />
            </button>
          </div>
        </div>

        <div class="portfolio-summary" aria-label="Resumen de cartera">
          <span><i class="summary-dot summary-dot--healthy" /> {{ healthyCount }} prestar</span>
          <span><i class="summary-dot summary-dot--watch" /> {{ watchCount }} vigilar</span>
          <span><i class="summary-dot summary-dot--risk" /> {{ riskCount }} no prestar</span>
          <small>{{ companies.length }} empresas · previsión a 3 meses</small>
        </div>

        <div v-if="isPending" class="table-state" role="status">
          <RefreshCw class="spin" :size="20" aria-hidden="true" />
          Cargando cartera…
        </div>
        <div v-else-if="isError" class="table-state table-state--error" role="alert">
          <span>No se pudo cargar la cartera.</span>
          <button class="button button--secondary" type="button" @click="refetch()">Reintentar</button>
        </div>
        <PortfolioTable v-else :companies="companies" :compact="workspace.compactMode" />

        <p v-if="data?.source === 'demo'" class="demo-note">
          Mostrando datos de desarrollo. Define <code>XRAY_API_BASE</code> para conectar el servicio real.
          <span v-if="isFetching" aria-live="polite">Actualizando…</span>
        </p>
      </section>
    </main>
  </div>
</template>
