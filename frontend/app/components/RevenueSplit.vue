<script setup lang="ts">
import { share, thousands, type RevenueProduct } from '~/data/internal'

const props = defineProps<{
  products: RevenueProduct[]
  /** En el monitor va solo la barra con su leyenda: el desglose vive en su
   *  propia vista. */
  compact?: boolean
}>()

const total = computed(() =>
  props.products.reduce((sum, product) => sum + product.amount, 0),
)

const ranked = computed(() =>
  [...props.products].sort((a, b) => b.amount - a.amount),
)

/* El tramo se dibuja con el importe, no con el porcentaje redondeado, para que
 * la barra no pueda contradecir a las cifras que tiene debajo. */
const width = (amount: number) => `${(amount / total.value) * 100}%`

/* El nombre del producto no se mete dentro del tramo: Marketplace se queda en
 * el 2 % del mes y no cabría, y la tinta sobre un relleno de color no aguanta
 * el 4,5:1 en los dos temas. La barra es proporción; quien nombra es la
 * leyenda —el mismo reparto que en las barras de cobros y pagos. */
const description = computed(
  () =>
    `Revenue del mes por producto, ${thousands(total.value)} en total: ` +
    ranked.value
      .map(
        (product) =>
          `${product.label}, ${thousands(product.amount)}, ${share(product.amount, total.value)} %`,
      )
      .join('; '),
)
</script>

<template>
  <figure class="rsplit" role="img" :aria-label="description">
    <div class="rsplit__bar" aria-hidden="true">
      <span
        v-for="product in ranked"
        :key="product.id"
        class="rsplit__seg"
        :data-tone="product.tone"
        :style="{ width: width(product.amount) }"
      />
    </div>

    <ol v-if="!compact" class="rsplit__rows">
      <li v-for="product in ranked" :key="product.id" :data-tone="product.tone">
        <p class="rsplit__label">{{ product.label }}</p>
        <p class="rsplit__note">{{ product.note }}</p>
        <span class="rsplit__amount"
          >{{ thousands(product.amount)
          }}<small>{{ share(product.amount, total) }} % del mes</small></span
        >
      </li>
    </ol>

    <figcaption v-else class="rsplit__legend">
      <span
        v-for="product in ranked"
        :key="product.id"
        class="chip"
        :class="`chip--${product.tone}`"
        >{{ product.label }}</span
      >
    </figcaption>
  </figure>
</template>
