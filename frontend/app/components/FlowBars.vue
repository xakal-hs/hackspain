<script setup lang="ts">
import { compactEuros, type MonthFlow } from '~/data/demo'
import { linePath, linearScale, type Point } from '~/utils/chart'

const props = defineProps<{ flows: MonthFlow[] }>()

const max = computed(() =>
  Math.max(...props.flows.flatMap((f) => [f.in, f.out, f.cash])) * 1.08,
)

const height = (value: number) => `${Math.max((value / max.value) * 100, 1.5)}%`

/* One shared scale for collections, payments and the cash line: putting cash on
 * its own axis would let the drawing flatter the balance. */
const cashPath = computed(() => {
  const y = linearScale([0, max.value], [1000, 0])
  const slot = 1000 / props.flows.length
  return linePath(
    props.flows.map(
      (flow, index) => [slot * (index + 0.5), y(flow.cash)] as Point,
    ),
  )
})

const description = computed(
  () =>
    'Cobros, pagos y dinero en la cuenta por mes: ' +
    props.flows
      .map(
        (f) =>
          `${f.month}, cobros ${compactEuros(f.in)}, pagos ${compactEuros(f.out)}, caja ${compactEuros(f.cash)}`,
      )
      .join('; '),
)
</script>

<template>
  <figure class="flows" :aria-label="description" role="img">
    <div class="flows__bars">
      <svg
        class="flows__cash"
        viewBox="0 0 1000 1000"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <path
          :d="cashPath"
          fill="none"
          stroke="var(--live)"
          stroke-width="2"
          stroke-linejoin="round"
          vector-effect="non-scaling-stroke"
        />
      </svg>
      <span v-for="flow in flows" :key="flow.month" class="flows__pair">
        <span
          class="flows__bar flows__bar--in"
          :style="{ height: height(flow.in) }"
        />
        <span
          class="flows__bar flows__bar--out"
          :style="{ height: height(flow.out) }"
        />
      </span>
    </div>

    <div class="flows__ticks" aria-hidden="true">
      <span
        v-for="(flow, index) in flows"
        :key="flow.month"
        :class="{ 'is-current': index === flows.length - 1 }"
        >{{ flow.month }}</span
      >
    </div>
    <figcaption class="flows__legend">
      <span class="chip chip--live">Dinero en la cuenta</span>
      <span class="chip chip--mint">Cobros</span>
      <span class="chip chip--coral">Pagos</span>
    </figcaption>
  </figure>
</template>
