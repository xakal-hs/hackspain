<script setup lang="ts">
import {
  formatDays,
  formatMonths,
  sectorBenchmarks,
  sectorMedianSeries,
  sectorPeers,
  signed,
  sizeLabel,
  vsMedian,
  type Company,
} from '~/data/demo'

const props = withDefaults(
  defineProps<{
    company: Company
    /** Overlay the simulated score in the X-Ray Score mock. */
    score?: number
    /** Serie simulada del mock. Cuando llega manda sobre la de la empresa, para
     *  que las dos gráficas de esa pantalla cuenten lo mismo. */
    series?: { history: number[]; forecast: number[] }
    selectable?: boolean
    /** El sector se resume en su mediana; nadie ve la cifra de una competidora. */
    anonymous?: boolean
  }>(),
  { selectable: false, anonymous: true },
)

const emit = defineEmits<{ select: [id: string] }>()

const scoreOf = (row: Company) =>
  row.id === props.company.id && props.score != null ? props.score : row.score

/** Una sola comparativa, contra el sector entero. Recortar por tamaño deja
 *  cortes de una o dos empresas, que ni comparan ni se pueden anonimizar. */
const cut = computed(() => sectorPeers(props.company))

const rows = computed(() => {
  if (cut.value.some((peer: Company) => peer.id === props.company.id)) return cut.value
  return [props.company, ...cut.value]
})

const bench = computed(() => sectorBenchmarks(cut.value))

/* Sin serie simulada, el mock solo mueve el número: desplazamos la serie
 * entera en vez de tocar el último mes, para que la forma siga siendo la
 * de la empresa. */
const shift = computed(() => {
  const last = props.company.history[props.company.history.length - 1]
  return props.score == null || last == null ? 0 : props.score - last
})

const mine = computed(
  () =>
    props.series ?? {
      history: props.company.history.map((value) => value + shift.value),
      forecast: props.company.forecast.map((value) => value + shift.value),
    },
)

/** El cambio a tres meses sale de la serie que se está pintando, no del dato
 *  de cartera: si no, la tabla contradice a su propia gráfica. */
const delta3Of = (peer: Company) => {
  const history = mine.value.history
  if (peer.id !== props.company.id || !props.series || history.length < 4) {
    return peer.delta3
  }
  return Math.round(history[history.length - 1]! - history[history.length - 4]!)
}

const traces = computed(() => {
  const median = sectorMedianSeries(cut.value)
  return [
    {
      key: 'you',
      label: props.company.name,
      tone: 'live' as const,
      history: mine.value.history,
      forecast: mine.value.forecast,
    },
    {
      key: 'median',
      label: 'Mediana del sector',
      note: `${cut.value.length} empresas`,
      tone: 'muted' as const,
      history: median.history,
      forecast: median.forecast,
    },
  ]
})

const rank = computed(() => {
  const index = cut.value.findIndex((peer: Company) => peer.id === props.company.id)
  return index === -1 ? null : index + 1
})

/** Con dos empresas la "mediana" es la cifra de una de ellas con otro nombre.
 *  Por debajo de este umbral no se publica nada del sector. */
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

/** La mediana de un número par de empresas cae en medio punto, y ese medio
 *  punto tiene que sobrevivir a la resta: si no, la fila de diferencia
 *  contradice a las dos que tiene encima. */
const round1 = (value: number) => Math.round(value * 10) / 10

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
    of: (peer) => delta3Of(peer),
    format: (value) => signed(round1(value)),
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

/** Fila de diferencia: lo que separa a esta empresa de la mediana del sector. */
const gap = (metric: Metric) => {
  const value = metric.of(props.company)
  const median = bench.value[metric.key]
  if (median == null || missing(metric, value)) return { text: '—', dir: undefined }
  const text = signed(round1(value - median))
  const direction = vsMedian(value, median, metric.invert)
  return { text, dir: direction === 'flat' ? undefined : direction }
}

const sectorName = computed(() => props.company.sector.toLocaleLowerCase('es'))

const cutLabel = computed(() => `el sector de ${sectorName.value}`)

const readout = computed(() => {
  const { runway, dso } = bench.value
  const n = cut.value.length

  if (!n) return `No hay ninguna otra empresa en ${cutLabel.value}.`

  if (!publishable.value) {
    return (
      `En ${cutLabel.value} solo hay ${n === 1 ? 'una empresa' : `${n} empresas`}. ` +
      `Con menos de ${MIN_PEERS} la mediana sería el dato de una empresa concreta, ` +
      'así que no la publicamos.'
    )
  }

  const place = rank.value
    ? `${props.company.name} queda ${rank.value}.ª de ${n} en ${cutLabel.value}.`
    : `${props.company.name} queda fuera de la comparativa.`
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
    <p class="compare__read">{{ readout }}</p>

    <ScoreBandChart
      v-if="cut.length && publishable"
      :traces="traces"
      :caption="`Score de ${company.name} frente a la mediana del sector de ${sectorName}, mes a mes.`"
    />

    <div class="ctable compare__table">
      <table>
        <caption class="sr-only">
          Comparativa de {{ company.name }} con la mediana del sector de
          {{ sectorName }}, score y plazos.
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
                <small>{{ cut.length }} empresas de {{ sectorName }}</small>
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
            <th scope="row">Mediana del sector</th>
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
      {{ MIN_PEERS }} empresas en el sector. Nunca mostramos el dato de una
      empresa concreta, ni el tuyo a las demás.
    </p>
  </div>
</template>
