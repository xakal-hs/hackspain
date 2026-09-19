<script setup lang="ts">
import { ArrowDownRight, ArrowUpRight, Minus, MoveRight } from '@lucide/vue'
import type { CompanySummary } from '~/types/portfolio'

defineProps<{
  companies: CompanySummary[]
  compact?: boolean
}>()

function trendLabel(trend: CompanySummary['trend']) {
  return trend === 'mejora' ? 'Mejora' : trend === 'deterioro' ? 'Deterioro' : 'Estable'
}
</script>

<template>
  <div class="table-shell" :class="{ 'is-compact': compact }">
    <table>
      <thead>
        <tr>
          <th>Empresa</th>
          <th>Score</th>
          <th>Trayectoria</th>
          <th>Previsión 3 meses</th>
          <th>Decisión</th>
          <th><span class="sr-only">Abrir empresa</span></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="company in companies" :key="company.company_id">
          <td>
            <div class="company-cell">
              <span class="company-monogram">{{ company.company_id.slice(-2) }}</span>
              <span>
                <strong>{{ company.company_id }}</strong>
                <small>{{ company.group_id }} · {{ company.currency }}</small>
              </span>
            </div>
          </td>
          <td>
            <strong class="score-number">{{ company.score.toFixed(0) }}</strong>
            <span class="score-denominator">/100</span>
          </td>
          <td>
            <span class="trend" :class="`trend--${company.trend}`">
              <ArrowUpRight v-if="company.trend === 'mejora'" :size="16" aria-hidden="true" />
              <ArrowDownRight v-else-if="company.trend === 'deterioro'" :size="16" aria-hidden="true" />
              <Minus v-else :size="16" aria-hidden="true" />
              {{ trendLabel(company.trend) }}
            </span>
          </td>
          <td>
            <strong :class="company.delta3_q50 >= 0 ? 'delta-positive' : 'delta-negative'">
              {{ company.delta3_q50 > 0 ? '+' : '' }}{{ company.delta3_q50.toFixed(1) }} pts
            </strong>
            <small class="forecast-range">
              {{ company.delta3_q10.toFixed(1) }} a {{ company.delta3_q90.toFixed(1) }}
            </small>
          </td>
          <td><StatusPill :band="company.band" /></td>
          <td>
            <NuxtLink :to="`/empresas/${company.company_id}`" class="row-link" :aria-label="`Abrir ${company.company_id}`">
              <MoveRight :size="18" aria-hidden="true" />
            </NuxtLink>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
