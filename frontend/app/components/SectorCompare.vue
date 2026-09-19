<script setup lang="ts">
import {
  formatDays,
  formatMonths,
  sectorBenchmarks,
  sectorMedianSeries,
  sectorPeers,
  signed,
  sizeFilterLabel,
  sizeFilters,
  sizeLabel,
  vsMedian,
  type Company,
  type SizeBand,
} from '~/data/demo'

const props = withDefaults(
  defineProps<{
    company: Company
    /** Overlay the simulated score in the X-Ray Score mock. */
    score?: number
    selectable?: boolean
    /** El sector se resume en su mediana; nadie ve la cifra de una competidora. */
    anonymous?: boolean
  }>(),
  { selectable: false, anonymous: true },
)

const emit = defineEmits<{ select: [id: string] }>()

const sizeFilter = ref<SizeBand | 'todas'>(props.company.size)

watch(
  () => props.company.id,
  (id, previous) => {
    if (id !== previous) sizeFilter.value = props.company.size
  },
)

const scoreOf = (row: Company) =>
  row.id === props.company.id && props.score != null ? props.score : row.score

const cut = computed(() => sectorPeers(props.company, sizeFilter.value))

const rows = computed(() => {
  if (cut.value.some((peer: Company) => peer.id === props.company.id)) return cut.value
  return [props.company, ...cut.value]
})

const bench = computed(() => sectorBenchmarks(cut.value))

const trend = computed(() => sectorMedianSeries(cut.value))

const rank = computed(() => {
  const index = cut.value.findIndex((peer: Company) => peer.id === props.company.id)
  return index === -1 ? null : index + 1
})

/** Con dos empresas la "mediana" es la cifra de una de ellas con otro nombre.
 *  Por debajo de este corte no se publica nada del sector. */
const MIN_PEERS = 3

const publishable = computed(
  () => !props.anonymous || cut.value.length >= MIN_PEERS,
)

interface Metric {
  key: 'score' | 'delta3' | 'runway' | 'dso' | 'dpo'
  label: string
  of: (peer: Company) => number
  format: (value: number) => string
  /** Cuanto más bajo, mejor: plazos de cobro y de pago. */
  invert?: boolean
  /** Se juzga contra cero, no contra el sector. */
  absolute?: boolean
}

const metrics: Metric[] = [
  {
    key: 'score',
    label: 'Score',
    of: (peer) => scoreOf(peer),
    format: (value) => value.toLocaleString('es-ES'),
  },
  {
    key: 'delta3',
    label: '3 m',
    of: (peer) => peer.delta3,
    format: (value) => signed(Math.round(value)),
    absolute: true,
  },
  {
    key: 'runway',
    label: 'Meses de caja',
    of: (peer) => peer.runway.now,
    format: formatMonths,
  },
  {
    key: 'dso',
    label: 'Días de cobro',
    of: (peer) => peer.dso.now,
    format: formatDays,
    invert: true,
  },
  {
    key: 'dpo',
    label: 'Días de pago',
    of: (peer) => peer.dpo.now,
    format: formatDays,
    invert: true,
  },
]

/** Los plazos llegan a 0 cuando no hay dato, y un 0 no es un plazo mejor. */
const missing = (metric: Metric, value: number) => Boolean(metric.invert) && !value

const dirOf = (metric: Metric, value: number) => {
  if (metric.absolute) return value > 0 ? 'up' : value < 0 ? 'down' : 'flat'
  if (missing(metric, value) || !publishable.value) return undefined
  const direction = vsMedian(value, bench.value[metric.key], metric.invert)
  return direction === 'flat' ? undefined : direction
}

/** Fila de diferencia: lo que separa a esta empresa de la mediana del corte. */
const gap = (metric: Metric) => {
  const value = metric.of(props.company)
  const median = bench.value[metric.key]
  if (median == null || missing(metric, value)) return { text: '—', dir: undefined }
  const delta = value - median
  const text = signed(
    metric.key === 'runway' ? Math.round(delta * 10) / 10 : Math.round(delta),
  )
  const direction = vsMedian(value, median, metric.invert)
  return { text, dir: direction === 'flat' ? undefined : direction }
}

const sectorName = computed(() => props.company.sector.toLocaleLowerCase('es'))

const cutLabel = computed(() =>
  sizeFilter.value === 'todas'
    ? `todo el sector de ${sectorName.value}`
    : `${sizeFilterLabel[sizeFilter.value].toLocaleLowerCase('es')} de ${sectorName.value}`,
)

const readout = computed(() => {
  const { runway, dso } = bench.value
  const n = cut.value.length

  if (!n) return `No hay ninguna empresa en ${cutLabel.value}.`

  if (!publishable.value) {
    return (
      `En ${cutLabel.value} solo hay ${n === 1 ? 'una empresa' : `${n} empresas`}. ` +
      `Con menos de ${MIN_PEERS} la mediana sería el dato de una empresa concreta, ` +
      'así que no la publicamos: amplía el tamaño para ver la comparativa.'
    )
  }

  const place = rank.value
    ? `${props.company.name} queda ${rank.value}.ª de ${n} en ${cutLabel.value}.`
    : `${props.company.name} queda fuera de este corte.`
  const cash =
    runway == null
      ? ''
      : ` El dinero en la cuenta cubre ${formatMonths(props.company.runway.now)} meses; la mediana, ${formatMonths(runway)}.`
  const collect =
    dso == null || !props.company.dso.now
      ? ''
      : ` Cobra a ${props.company.dso.now} días; el sector, a ${formatDays(dso)}.`
  return `${place}${cash}${collect}`
})

const pick = (id: string) => {
  if (props.selectable && id !== props.company.id) emit('select', id)
}
</script>

<template>
  <div class="compare">
    <div class="filters compare__filters">
      <div class="filters__field">
        <span id="compare-size">Tamaño</span>
        <div class="seg" role="radiogroup" aria-labelledby="compare-size">
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
      <p v-if="rank && publishable" class="compare__place">
        {{ rank }} de {{ cut.length }}
      </p>
    </div>

    <p class="compare__read">{{ readout }}</p>

    <SectorTrendChart
      v-if="cut.length && publishable"
      :company="company"
      :sector="trend"
      :peers="cut.length"
      :score="score"
    />

    <div class="ctable compare__table">
      <table>
        <caption class="sr-only">
          Comparativa de {{ company.name }} con la mediana de
          {{ cutLabel }}, score y plazos.
        </caption>
        <thead>
          <tr>
            <th scope="col">Empresa</th>
            <th v-for="metric in metrics" :key="metric.key" scope="col" class="num">
              {{ metric.label }}
            </th>
          </tr>
        </thead>

        <tbody v-if="anonymous">
          <tr class="is-you">
            <th scope="row">
              <span>
                <b>{{ company.name }}</b>
                <small>{{ sizeLabel[company.size] }} · esta empresa</small>
              </span>
            </th>
            <td
              v-for="metric in metrics"
              :key="metric.key"
              class="num"
              :data-dir="dirOf(metric, metric.of(company))"
            >
              {{ metric.format(metric.of(company)) }}
            </td>
          </tr>
          <tr v-if="publishable" class="is-median">
            <th scope="row">
              <span>
                <b>Mediana del sector</b>
                <small>{{ cut.length }} empresas · {{ cutLabel }}</small>
              </span>
            </th>
            <td v-for="metric in metrics" :key="metric.key" class="num">
              {{
                bench[metric.key] == null ? '—' : metric.format(bench[metric.key]!)
              }}
            </td>
          </tr>
          <tr v-if="publishable" class="is-gap">
            <th scope="row">
              <span>
                <b>Diferencia</b>
                <small>esta empresa frente a la mediana</small>
              </span>
            </th>
            <td
              v-for="metric in metrics"
              :key="metric.key"
              class="num"
              :data-dir="gap(metric).dir"
            >
              {{ gap(metric).text }}
            </td>
          </tr>
        </tbody>

        <tbody v-else>
          <tr
            v-for="peer in rows"
            :key="peer.id"
            :class="{
              'is-you': peer.id === company.id,
              'is-out': peer.id === company.id && rank === null,
            }"
          >
            <th scope="row">
              <button
                v-if="selectable"
                type="button"
                :aria-pressed="peer.id === company.id"
                :aria-current="peer.id === company.id ? 'true' : undefined"
                @click="pick(peer.id)"
              >
                <b>{{ peer.name }}</b>
                <small
                  >{{ sizeLabel[peer.size]
                  }}<template v-if="peer.id === company.id">
                    · esta empresa</template
                  ></small
                >
              </button>
              <span v-else>
                <b>{{ peer.name }}</b>
                <small
                  >{{ sizeLabel[peer.size]
                  }}<template v-if="peer.id === company.id">
                    · esta empresa</template
                  ></small
                >
              </span>
            </th>
            <td
              v-for="metric in metrics"
              :key="metric.key"
              class="num"
              :data-dir="dirOf(metric, metric.of(peer))"
            >
              {{ metric.format(metric.of(peer)) }}
            </td>
          </tr>
        </tbody>

        <tfoot v-if="!anonymous && cut.length">
          <tr>
            <th scope="row">Mediana del corte</th>
            <td v-for="metric in metrics" :key="metric.key" class="num">
              {{
                bench[metric.key] == null ? '—' : metric.format(bench[metric.key]!)
              }}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>

    <p v-if="anonymous" class="compare__note">
      El sector solo se publica como mediana, y solo a partir de
      {{ MIN_PEERS }} empresas en el corte. Nunca mostramos el dato de una
      empresa concreta, ni el tuyo a las demás.
    </p>
  </div>
</template>
