<script setup lang="ts">
import { shapeLabel, signed, type Company } from '~/data/demo'

const props = withDefaults(
  defineProps<{
    companies: Company[]
    selectedId?: string
    /** Drops the trajectory and coverage columns for the overview. */
    compact?: boolean
  }>(),
  { compact: false },
)

const emit = defineEmits<{ select: [id: string] }>()

const domain: [number, number] = [34, 96]

const tone = (delta: number) =>
  delta > 2 ? 'mint' : delta < -5 ? 'crimson' : 'muted'

const window12 = (company: Company) => company.history.slice(12)
</script>

<template>
  <div class="ctable" :class="{ 'ctable--compact': compact }">
    <table>
      <caption class="sr-only">
        Cartera de empresas con score, trayectoria de doce meses y decisión.
      </caption>
      <thead>
        <tr>
          <th scope="col">Empresa</th>
          <th scope="col" class="num">Score</th>
          <th scope="col">Doce meses</th>
          <th scope="col" class="num">3 m</th>
          <th v-if="!compact" scope="col">Movimiento</th>
          <th scope="col">Decisión</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="company in companies"
          :key="company.id"
          :class="{ 'is-selected': company.id === selectedId }"
        >
          <th scope="row">
            <button
              type="button"
              :aria-pressed="company.id === selectedId"
              @click="emit('select', company.id)"
            >
              <b>{{ company.name }}</b><small>{{ company.sector }}</small>
            </button>
          </th>
          <td class="num">
            <span class="ctable__score" :data-band="company.band">{{
              company.score
            }}</span>
          </td>
          <td class="ctable__spark">
            <Sparkline
              :values="window12(company)"
              :domain="domain"
              :tone="tone(company.delta3)"
              :dot="false"
            />
          </td>
          <td class="num">
            <span
              class="ctable__delta"
              :data-dir="
                company.delta3 > 0 ? 'up' : company.delta3 < 0 ? 'down' : 'flat'
              "
              >{{ signed(company.delta3) }}</span
            >
          </td>
          <td v-if="!compact" class="ctable__shape">
            {{ shapeLabel[company.shape] }}
          </td>
          <td><DecisionTag :decision="company.decision" size="sm" /></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
