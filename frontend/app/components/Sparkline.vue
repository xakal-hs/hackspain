<script setup lang="ts">
import { linePath, linearScale, paddedDomain, type Point } from '~/utils/chart'

const props = withDefaults(
  defineProps<{
    values: number[]
    tone?: 'mint' | 'coral' | 'crimson' | 'live' | 'muted'
    label?: string
    dot?: boolean
    /** Pass a shared domain when several sparklines must be read against each other. */
    domain?: [number, number]
  }>(),
  { tone: 'live', dot: true },
)

const geometry = computed(() => {
  const x = linearScale([0, props.values.length - 1], [1, 999])
  const y = linearScale(props.domain ?? paddedDomain(props.values, 0.16), [920, 80])
  const points = props.values.map((value, index) => [x(index), y(value)] as Point)
  const end = points[points.length - 1]!
  return {
    path: linePath(points),
    endLeft: `${end[0] / 10}%`,
    endTop: `${end[1] / 10}%`,
  }
})
</script>

<template>
  <span class="spark" :class="`spark--${tone}`">
    <svg
      viewBox="0 0 1000 1000"
      preserveAspectRatio="none"
      :role="label ? 'img' : 'presentation'"
      :aria-label="label"
      :aria-hidden="label ? undefined : 'true'"
    >
      <path
        :d="geometry.path"
        fill="none"
        stroke="currentColor"
        stroke-width="1.75"
        stroke-linejoin="round"
        vector-effect="non-scaling-stroke"
      />
    </svg>
    <i
      v-if="dot"
      :style="{ left: geometry.endLeft, top: geometry.endTop }"
      aria-hidden="true"
    />
  </span>
</template>
