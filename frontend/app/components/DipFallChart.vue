<script setup lang="ts">
import { linePath, linearScale, type Point } from '~/utils/chart'

const props = defineProps<{
  values: number[]
  offsets: readonly string[]
  tone: 'mint' | 'crimson'
  /** The other series, drawn behind as a hairline so the divergence is visible. */
  ghost: number[]
}>()

const scales = computed(() => ({
  x: linearScale([0, props.values.length - 1], [6, 94]),
  y: linearScale([-10, 7], [88, 12]),
}))

const toPath = (values: number[]) =>
  linePath(
    values.map(
      (value, index) =>
        [scales.value.x(index) * 10, scales.value.y(value) * 10] as Point,
    ),
  )

const path = computed(() => toPath(props.values))
const ghostPath = computed(() => toPath(props.ghost))
const zeroY = computed(() => scales.value.y(0) * 10)
const dropX = computed(() => scales.value.x(2))
</script>

<template>
  <figure class="dip" :class="`dip--${tone}`">
    <svg viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-hidden="true">
      <line
        x1="40"
        :y1="zeroY"
        x2="960"
        :y2="zeroY"
        stroke="var(--grid-line)"
        stroke-width="1"
        vector-effect="non-scaling-stroke"
      />
      <line
        :x1="dropX * 10"
        y1="80"
        :x2="dropX * 10"
        y2="900"
        stroke="var(--line-strong)"
        stroke-width="1"
        stroke-dasharray="3 5"
        vector-effect="non-scaling-stroke"
      />
      <path
        :d="ghostPath"
        fill="none"
        stroke="var(--text-dim)"
        stroke-width="1.25"
        stroke-dasharray="2 4"
        opacity=".55"
        vector-effect="non-scaling-stroke"
      />
      <path
        :d="path"
        fill="none"
        stroke="currentColor"
        stroke-width="2.5"
        stroke-linejoin="round"
        vector-effect="non-scaling-stroke"
      />
    </svg>
    <div class="dip__axis" aria-hidden="true">
      <span v-for="offset in offsets" :key="offset">{{ offset }}</span>
    </div>
  </figure>
</template>
