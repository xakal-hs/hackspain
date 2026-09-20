<script setup lang="ts">
import { X } from '@lucide/vue'
import type { Cashflow, CashflowAction } from '../../shared/types/company'

/* Mismo panel para los dos casos de tesorería: colocar el excedente (yield) o
 * pedir un puente cuando la caja se rompe. Los números salen de la previsión
 * que ya carga Flujo de caja; el tipo de depósito y el 1,5 % neto son la
 * hipótesis de producto de context/oportunidades.md. */

const props = defineProps<{
  open: boolean
  mode: Exclude<CashflowAction, null>
  flujo: Cashflow | undefined
}>()
const emit = defineEmits<{ close: [] }>()

const { selectedId, health, sector } = useSelectedCompany()
const dialog = ref<HTMLDialogElement | null>(null)
const titleId = useId()
const leadId = useId()

watch(
  () => props.open,
  async (open) => {
    await nextTick()
    const el = dialog.value
    if (!el) return
    if (open && !el.open) el.showModal()
    else if (!open && el.open) el.close()
  },
)

const onNativeClose = () => {
  if (props.open) emit('close')
}

const currency = computed(() => props.flujo?.currency || 'EUR')
const money = (v: number) =>
  new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: currency.value,
    maximumFractionDigits: 0,
    useGrouping: 'always',
  } as Intl.NumberFormatOptions)
    .format(v)
    .replace('-', '−')

const monthLong = (iso: string) =>
  new Intl.DateTimeFormat('es-ES', { day: 'numeric', month: 'long', timeZone: 'UTC' }).format(
    new Date(`${iso}T00:00:00Z`),
  )

const excedente = computed(() => props.flujo?.forecast?.excedente ?? null)
const rotura = computed(() => props.flujo?.forecast?.rotura ?? null)

/* 1,5 % neto al CFO tras 100 pb. El primer número del panel es lo que cuesta
 * no hacer nada, no el take de Embat. */
const NET_YIELD = 0.015
const yearlyYield = computed(() => (excedente.value ? excedente.value.amount * NET_YIELD : 0))
const monthlyYield = computed(() => yearlyYield.value / 12)
const hole = computed(() => (rotura.value ? Math.abs(rotura.value.low) : 0))
const gapDays = computed(() => {
  const r = rotura.value
  if (!r) return 0
  const from = Date.parse(`${r.from}T00:00:00Z`)
  const to = Date.parse(`${(r.to ?? r.low_date)}T00:00:00Z`)
  return Math.max(1, Math.round((to - from) / 86_400_000) + 1)
})

const band = computed(() => health.value?.health_band ?? null)
const bandLabel = computed(() => {
  if (band.value === 'sano') return 'sano'
  if (band.value === 'riesgo') return 'en riesgo'
  if (band.value === 'vigilar') return 'en vigilancia'
  return null
})

const asking = ref(false)
const asked = ref<'new' | 'open' | 'error' | null>(null)

watch(
  () => [props.open, props.mode, selectedId.value] as const,
  () => {
    asked.value = null
  },
)

async function requestFinancing() {
  if (!selectedId.value || asking.value) return
  asking.value = true
  asked.value = null
  try {
    const result = await $fetch<{ alreadyOpen?: boolean }>('/api/embat/leads', {
      method: 'POST',
      body: { company_id: selectedId.value },
    })
    asked.value = result.alreadyOpen ? 'open' : 'new'
    await refreshNuxtData('embat-leads')
  } catch {
    asked.value = 'error'
  } finally {
    asking.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <dialog
      ref="dialog"
      class="sheet"
      :aria-labelledby="titleId"
      :aria-describedby="leadId"
      @close="onNativeClose"
      @click.self="dialog?.close()"
    >
      <div class="sheet__scrim" @click="dialog?.close()" />
      <aside class="sheet__panel" :data-mode="mode">
        <header class="sheet__head">
          <div>
            <h2 :id="titleId">
              {{ mode === 'prestar' ? 'Coloca el excedente y captura el yield' : 'Si no pides un plan' }}
            </h2>
            <p class="sheet__who">{{ selectedId }} · {{ sector }}</p>
          </div>
          <button type="button" class="sheet__close" aria-label="Cerrar" @click="dialog?.close()">
            <X :size="18" aria-hidden="true" />
          </button>
        </header>

        <div class="sheet__body">
          <template v-if="mode === 'prestar' && excedente">
            <p :id="leadId" class="sheet__lead">
              Dejar {{ money(excedente.amount) }} en corriente te cuesta
              <strong>{{ money(yearlyYield) }} al año</strong>. Colocarlos no toca el colchón
              y convierte ese coste en yield.
            </p>

            <dl class="sheet__read">
              <div>
                <dt>Colocables</dt>
                <dd>{{ money(excedente.amount) }}</dd>
              </div>
              <div>
                <dt>Colchón que se queda</dt>
                <dd>{{ money(excedente.cushion) }}</dd>
              </div>
              <div>
                <dt>Yield neto a 1,5 %</dt>
                <dd>{{ money(monthlyYield) }}/mes</dd>
              </div>
            </dl>

            <ol class="sheet__steps">
              <li>
                <b>Barre solo lo que sobra</b>
                <span>
                  {{ money(excedente.amount) }} sobran por encima de un mes de gasto
                  ({{ money(excedente.monthly_spend) }}/mes) en el peor día del trimestre.
                  Eso es lo que puede trabajar.
                </span>
              </li>
              <li>
                <b>El colchón no se toca</b>
                <span>
                  {{ money(excedente.cushion) }} se quedan en cuenta. El score no se
                  resiente porque la caja de operar no baja.
                </span>
              </li>
              <li>
                <b>El yield es la acción, no el descubrimiento</b>
                <span>
                  Un depósito a 30–90 días a ~1,5 % neto da {{ money(yearlyYield) }} al año.
                  El dinero parado no se siente como problema; este número sí.
                </span>
              </li>
              <li>
                <b>Aparcarlo abaratará el crédito</b>
                <span>
                  Si más adelante pides financiación, el depósito es colateral: baja el
                  interés y no tienes que deshacer el colchón.
                </span>
              </li>
            </ol>
          </template>

          <template v-else-if="mode === 'financiar' && rotura">
            <p :id="leadId" class="sheet__lead">
              Sin un préstamo puente de {{ money(hole) }}, la cuenta se pone en
              <strong>{{ money(rotura.low) }} el {{ monthLong(rotura.low_date) }}</strong>.
              Es un hueco de {{ gapDays }} {{ gapDays === 1 ? 'día' : 'días' }}, no un
              agujero que se arregla solo.
            </p>

            <dl class="sheet__read">
              <div>
                <dt>Mínimo previsto</dt>
                <dd>{{ money(rotura.low) }}</dd>
              </div>
              <div>
                <dt>Puente que cubre</dt>
                <dd>{{ money(hole) }}</dd>
              </div>
              <div>
                <dt>Pagos antes del hueco</dt>
                <dd>{{ money(rotura.paid_before) }}</dd>
              </div>
            </dl>

            <ol class="sheet__steps">
              <li>
                <b>La cuenta se pone en negativo</b>
                <span>
                  Del {{ monthLong(rotura.from) }}{{ rotura.to ? ` al ${monthLong(rotura.to)}` : '' }}
                  no hay saldo para operar. El peor día es el {{ monthLong(rotura.low_date) }}.
                </span>
              </li>
              <li>
                <b>Los pagos de ese tramo no salen</b>
                <span>
                  {{ rotura.n_paid_before }} pagos por {{ money(rotura.paid_before) }} vencen
                  antes de romper caja. Nóminas, proveedores o cuotas se quedan sin cubrir.
                </span>
              </li>
              <li v-if="rotura.rescue">
                <b>El cobro que tapa el hueco llega tarde</b>
                <span>
                  El {{ monthLong(rotura.rescue.date) }} entra {{ money(rotura.rescue.amount) }}.
                  Un día después del agujero. El puente dura hasta ese cobro; no hace falta
                  deuda a un año.
                </span>
              </li>
              <li v-else>
                <b>En el horizonte la caja no vuelve sola</b>
                <span>
                  No hay un cobro previsto que cierre el hueco. Sin un plan, el bache se
                  queda y un prestamista lo leerá como deterioro, no como un mal mes.
                </span>
              </li>
              <li>
                <b>El score deja de ser un bache</b>
                <span>
                  {{ bandLabel ? `Hoy estás ${bandLabel}. ` : '' }}Una rotura de caja es la señal que más mueve
                  la nota. Si esperas a ver el negativo, el siguiente préstamo ya no llega.
                </span>
              </li>
            </ol>
          </template>
        </div>

        <footer class="sheet__foot">
          <p v-if="mode === 'prestar' && excedente">
            Recomendación: colocar {{ money(excedente.amount) }} y dejar
            {{ money(excedente.cushion) }} de colchón.
          </p>
          <template v-else-if="mode === 'financiar' && rotura">
            <p>
              Recomendación: un puente de {{ money(hole) }}{{ rotura.rescue ? ` hasta el ${monthLong(rotura.rescue.date)}` : '' }}.
            </p>
            <button
              class="sheet__ask"
              type="button"
              :disabled="asking || asked === 'new' || asked === 'open'"
              @click="requestFinancing"
            >
              {{
                asked === 'new'
                  ? 'Tu asesor ya tiene el aviso'
                  : asked === 'open'
                    ? 'Este aviso ya estaba en la cola'
                    : asking
                      ? 'Avisando al asesor…'
                      : 'Quiero pedir financiación'
              }}
            </button>
            <p v-if="asked === 'error'" class="sheet__ask-error">No se pudo avisar. Inténtalo de nuevo.</p>
          </template>
        </footer>
      </aside>
    </dialog>
  </Teleport>
</template>

<style scoped>
.sheet {
  --sheet-bg: #ffffff;
  --sheet-line: #e8eaee;
  --sheet-text: #1b1f2a;
  --sheet-body: #3a4050;
  --sheet-muted: #737a8a;
  --sheet-navy: #131736;
  --sheet-fill: #f4f5f8;
  --sheet-good: #0f7a4a;
  --sheet-bad: #b42318;

  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
  max-width: none;
  max-height: none;
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--sheet-text);
  font-family: Inter, ui-sans-serif, system-ui, sans-serif;
  font-size: 14px;
  color-scheme: light;
}

.sheet:not([open]) {
  display: none;
}

.sheet::backdrop {
  background: transparent;
}

.sheet__scrim {
  position: absolute;
  inset: 0;
  background: rgb(16 20 40 / 0.38);
}

.sheet__panel {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  width: min(32rem, 100%);
  background: var(--sheet-bg);
  border-left: 1px solid var(--sheet-line);
  overflow: hidden;
}

.sheet[open] .sheet__scrim {
  animation: sheet-fade 0.2s ease-out;
}

.sheet[open] .sheet__panel {
  animation: sheet-in 0.32s cubic-bezier(0.16, 1, 0.3, 1);
}

.sheet__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 22px 22px 16px;
  border-bottom: 1px solid var(--sheet-line);
}

.sheet__head h2 {
  margin: 0;
  max-width: 22ch;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.02em;
  line-height: 1.25;
}

.sheet__who {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--sheet-muted);
}

.sheet__close {
  flex: none;
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  margin: -8px -8px 0 0;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--sheet-body);
  cursor: pointer;
}

.sheet__close:hover {
  background: var(--sheet-fill);
}

.sheet__close:focus-visible,
.sheet button:focus-visible {
  outline: 2px solid #3b77f6;
  outline-offset: 2px;
}

.sheet__body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  overscroll-behavior: contain;
  padding: 20px 22px 8px;
}

.sheet__lead {
  margin: 0 0 20px;
  max-width: 42ch;
  color: var(--sheet-body);
  line-height: 1.5;
}

.sheet__lead strong {
  color: var(--sheet-text);
  font-weight: 600;
}

.sheet__panel[data-mode='financiar'] .sheet__lead strong {
  color: var(--sheet-bad);
}

.sheet__panel[data-mode='prestar'] .sheet__lead strong {
  color: var(--sheet-good);
}

.sheet__read {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px 10px;
  margin: 0 0 22px;
  padding: 14px 0;
  border-top: 1px solid var(--sheet-line);
  border-bottom: 1px solid var(--sheet-line);
}

.sheet__read div {
  min-width: 0;
}

.sheet__read dt {
  margin: 0 0 4px;
  font-size: 12px;
  color: var(--sheet-muted);
  line-height: 1.35;
}

.sheet__read dd {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}

.sheet__steps {
  margin: 0;
  padding: 0;
  list-style: none;
  counter-reset: step;
}

.sheet__steps li {
  display: grid;
  grid-template-columns: 1.6rem minmax(0, 1fr);
  grid-template-areas:
    'n title'
    'n body';
  column-gap: 10px;
  padding: 14px 0;
  border-bottom: 1px solid var(--sheet-line);
  counter-increment: step;
}

.sheet__steps li:last-child {
  border-bottom: 0;
}

.sheet__steps li::before {
  grid-area: n;
  content: counter(step);
  color: var(--sheet-muted);
  font-size: 12px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  line-height: 1.45;
}

.sheet__steps b {
  grid-area: title;
  margin-bottom: 4px;
  font-size: 14px;
  font-weight: 600;
}

.sheet__steps span {
  grid-area: body;
  color: var(--sheet-body);
  font-size: 13.5px;
  line-height: 1.5;
}

.sheet__foot {
  padding: 16px 22px 20px;
  border-top: 1px solid var(--sheet-line);
  background: var(--sheet-fill);
}

.sheet__foot p {
  margin: 0;
  font-size: 13.5px;
  font-weight: 600;
  line-height: 1.45;
}

.sheet__ask {
  display: block;
  width: 100%;
  margin-top: 12px;
  padding: 12px 16px;
  border: 0;
  border-radius: 10px;
  background: var(--sheet-navy);
  color: #fff;
  font: inherit;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.sheet__ask:disabled {
  cursor: default;
  opacity: 0.72;
}

.sheet__ask:focus-visible {
  outline: 2px solid var(--sheet-navy);
  outline-offset: 2px;
}

.sheet__ask-error {
  margin-top: 8px !important;
  color: var(--sheet-bad);
  font-weight: 500 !important;
}

@keyframes sheet-in {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}

@keyframes sheet-fade {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .sheet[open] .sheet__scrim,
  .sheet[open] .sheet__panel {
    animation: none;
  }
}

@media (max-width: 720px) {
  .sheet__panel {
    width: 100%;
  }

  .sheet__read {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
