<script setup lang="ts">
import { X } from '@lucide/vue'
import type { ClientRow } from '../../shared/types/company'

/* Panel lateral de Crédito y caución, con la misma forma que el de Flujo de caja.
 * Preautorizado: condiciones y activar, sin pedir un solo dato.
 * En estudio: lo que sale del ERP y lo que la aseguradora todavía necesita. */

const props = defineProps<{
  open: boolean
  row: ClientRow | null
  snapshot: string
  hecho: boolean
}>()
const emit = defineEmits<{ close: []; confirm: [ClientRow] }>()

const { selectedId } = useSelectedCompany()
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

const nf = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 0, useGrouping: 'always' } as Intl.NumberFormatOptions)
const money = (v: number) => `${nf.format(v)} €`
const dias = (v: number | null) =>
  v == null ? 'sin dato' : v === 0 ? 'en fecha' : v < 0 ? `${nf.format(-v)} días antes` : `${nf.format(v)} días tarde`

const preautorizado = computed(() => props.row?.estado === 'preautorizado')
/* Con el expediente completo se cotiza sin pasar por la aseguradora. */
const cotizable = computed(() => props.row?.estado === 'estudio' && props.row.expediente === 'completo')
const conQuote = computed(() => preautorizado.value || cotizable.value)

/* La cotización entra sola: un instante de cálculo y aparece. */
const quote = ref(false)
let timer: ReturnType<typeof setTimeout> | undefined
watch(
  () => [props.open, props.row?.cliente] as const,
  ([open]) => {
    clearTimeout(timer)
    quote.value = false
    if (open && conQuote.value) timer = setTimeout(() => (quote.value = true), 520)
  },
  { immediate: true },
)
onUnmounted(() => clearTimeout(timer))

/* Lo que Embat ya ha leído del ERP y conciliado con el banco. */
const delErp = computed(() => {
  const r = props.row
  if (!r) return []
  return [
    { label: 'Facturas emitidas y cobradas', value: `${r.n_pagadas} de ${r.n_facturas}` },
    { label: 'Relación comercial', value: `${r.meses_relacion} meses` },
    { label: 'Cómo paga', value: dias(r.retraso_medio) },
    { label: 'Mayor deuda que ya devolvió', value: money(r.pico) },
    { label: 'Lo que te debe hoy', value: money(r.expuesto) },
    { label: 'Vencido a más de 90 días', value: money(r.vencido_90) },
  ]
})

/* Lo que falta: primero lo que le falta a este cliente según la regla, y después lo que
 * la aseguradora mira siempre y Embat no puede ver desde el ERP de su cliente. */
const loQueFalta = computed(() => {
  const r = props.row
  if (!r) return []
  const faltan: { label: string; value: string }[] = []
  if (r.n_pagadas < 8)
    faltan.push({ label: 'Historial de cobros', value: `${r.n_pagadas} facturas cobradas; hacen falta 8` })
  if (r.meses_relacion < 6)
    faltan.push({ label: 'Antigüedad de la relación', value: `${r.meses_relacion} meses; hacen falta 6` })
  if (r.retraso_medio != null && r.retraso_medio > 45)
    faltan.push({ label: 'Puntualidad', value: `paga a ${nf.format(r.retraso_medio)} días; el límite son 45` })
  if (!r.pico)
    faltan.push({ label: 'Deuda previa de referencia', value: 'nunca ha tenido saldo pendiente que sirva de tope' })
  faltan.push({ label: 'Cuentas anuales del cliente', value: 'las consulta la aseguradora en el registro' })
  faltan.push({ label: 'Incidencias judiciales y de impago', value: 'bases de datos de la aseguradora' })
  return faltan
})

const plazo = 90
const franquicia = 10
const avisoImpago = 60
const carencia = 90
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
      <aside v-if="row" class="sheet__panel">
        <header class="sheet__head">
          <div>
            <h2 :id="titleId">
              {{
                preautorizado
                  ? 'Cobertura de este cliente'
                  : cotizable
                    ? 'Cotización de este cliente'
                    : 'Enviar este cliente a estudio'
              }}
            </h2>
            <p class="sheet__who">{{ row.cliente }} · {{ selectedId }}</p>
          </div>
          <button type="button" class="sheet__close" aria-label="Cerrar" @click="dialog?.close()">
            <X :size="18" aria-hidden="true" />
          </button>
        </header>

        <div class="sheet__body">
          <template v-if="conQuote">
            <p :id="leadId" class="sheet__lead">
              <template v-if="preautorizado">
                No hay que rellenar nada: Embat ya tiene las pruebas de pago conciliadas con el banco
                hasta el {{ snapshot }}. Solo tienes que aceptar las condiciones.
              </template>
              <template v-else>
                El expediente de este cliente está completo en tu ERP, así que la cotización sale
                ahora mismo, sin pasar por la aseguradora ni pedirte un dato.
              </template>
            </p>

            <p v-if="!quote" class="sheet__calc" role="status">Calculando la cotización…</p>
            <dl v-else class="sheet__read is-in">
              <div>
                <dt>Límite asegurado</dt>
                <dd>{{ money(row.limite) }}</dd>
              </div>
              <div>
                <dt>Cobertura</dt>
                <dd>{{ Math.round(row.cover * 100) }} %</dd>
              </div>
              <div>
                <dt>Prima estimada</dt>
                <dd>{{ money(row.prima) }}/año</dd>
              </div>
            </dl>

            <h3 v-if="quote">Condiciones</h3>
            <ul v-if="quote" class="sheet__terms">
              <li>
                <b>Qué cubre</b>
                <span>
                  El {{ Math.round(row.cover * 100) }} % del impago de este cliente, hasta
                  {{ money(row.limite) }} de saldo vivo. El {{ franquicia }} % restante queda a tu cargo.
                </span>
              </li>
              <li>
                <b>Plazo máximo de crédito</b>
                <span>Facturas a {{ plazo }} días como mucho. Más allá, esa factura no está cubierta.</span>
              </li>
              <li>
                <b>Si no te paga</b>
                <span>
                  Lo comunicas dentro de los {{ avisoImpago }} días siguientes al vencimiento y cedes el
                  recobro. La indemnización llega {{ carencia }} días después del aviso.
                </span>
              </li>
              <li>
                <b>Declaración de ventas</b>
                <span>Automática desde tu ERP cada mes. No tienes que enviar nada.</span>
              </li>
              <li>
                <b>Revisión del límite</b>
                <span>
                  La aseguradora puede reducirlo o retirarlo avisando con 30 días. Embat te avisa antes
                  si ve que este cliente empieza a pagar peor.
                </span>
              </li>
              <li>
                <b>Vigencia</b>
                <span>12 meses, renovable. La prima se ajusta a las ventas declaradas.</span>
              </li>
            </ul>
          </template>

          <template v-else>
            <p :id="leadId" class="sheet__lead">
              Este cliente no se puede preautorizar, pero casi todo el expediente ya está hecho:
              esto es lo que Embat ha sacado de tu ERP y lo que le falta a la aseguradora.
            </p>

            <h3>Lo que hemos sacado de tu ERP</h3>
            <dl class="sheet__facts">
              <div v-for="fact in delErp" :key="fact.label">
                <dt>{{ fact.label }}</dt>
                <dd>{{ fact.value }}</dd>
              </div>
            </dl>

            <h3>Lo que no hemos encontrado</h3>
            <dl class="sheet__facts is-missing">
              <div v-for="fact in loQueFalta" :key="fact.label">
                <dt>{{ fact.label }}</dt>
                <dd>{{ fact.value }}</dd>
              </div>
            </dl>

            <p class="sheet__note">
              Con el expediente del ERP, la aseguradora responde en 24-72 h en vez de pedirte la lista
              de clientes, las ventas y el historial de impagos.
            </p>
          </template>
        </div>

        <footer class="sheet__foot">
          <p v-if="conQuote">
            {{
              hecho
                ? 'Cobertura activada. La póliza recoge este límite en la próxima declaración.'
                : quote
                  ? `Al activar, este cliente queda cubierto hasta ${money(row.limite)}.`
                  : 'Cotización en curso.'
            }}
          </p>
          <p v-else>
            {{ hecho ? 'Expediente enviado. La aseguradora responde en 24-72 h.' : 'No te pedimos ningún dato más.' }}
          </p>
          <button
            class="sheet__ask"
            type="button"
            :disabled="hecho || (conQuote && !quote)"
            @click="emit('confirm', row)"
          >
            {{
              hecho
                ? conQuote
                  ? 'Cobertura activada'
                  : 'Enviado a estudio'
                : conQuote
                  ? 'Aceptar condiciones y activar'
                  : 'Enviar a estudio'
            }}
          </button>
        </footer>
      </aside>
    </dialog>
  </Teleport>
</template>

<style scoped>
/* Mismas medidas y paleta que el panel de Flujo de caja. */
.sheet {
  --sheet-bg: #ffffff;
  --sheet-line: #e8eaee;
  --sheet-text: #1b1f2a;
  --sheet-body: #3a4050;
  --sheet-muted: #737a8a;
  --sheet-navy: #131736;
  --sheet-fill: #f4f5f8;

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
  border-left: 1px solid var(--sheet-line);
  background: var(--sheet-bg);
  overflow: hidden;
}

.sheet[open] .sheet__scrim {
  animation: sheet-fade 0.2s ease-out;
}

.sheet[open] .sheet__panel {
  animation: sheet-in 0.32s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes sheet-fade {
  from {
    opacity: 0;
  }
}

@keyframes sheet-in {
  from {
    transform: translateX(16px);
    opacity: 0;
  }
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
  line-height: 1.25;
  letter-spacing: -0.02em;
}

.sheet__who {
  margin: 6px 0 0;
  color: var(--sheet-muted);
  font-size: 13px;
}

.sheet__close {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 8px;
  background: none;
  color: var(--sheet-muted);
  cursor: pointer;
}

.sheet__close:hover {
  background: var(--sheet-fill);
  color: var(--sheet-text);
}

.sheet__body {
  flex: 1;
  padding: 20px 22px 24px;
  overflow-y: auto;
}

.sheet__lead {
  margin: 0;
  color: var(--sheet-body);
  line-height: 1.55;
}

.sheet__body h3 {
  margin: 22px 0 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--sheet-muted);
}

.sheet__calc {
  margin: 18px 0 0;
  padding: 22px 16px;
  border-radius: 10px;
  background: var(--sheet-fill);
  color: var(--sheet-muted);
  text-align: center;
}

.sheet__read.is-in {
  animation: quote-in 0.42s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes quote-in {
  from {
    transform: translateY(6px);
    opacity: 0;
  }
}

.sheet__read {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin: 18px 0 0;
  padding: 14px 16px;
  border-radius: 10px;
  background: var(--sheet-fill);
}

.sheet__read dt {
  color: var(--sheet-muted);
  font-size: 12.5px;
}

.sheet__read dd {
  margin: 4px 0 0;
  font-size: 16px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.sheet__facts {
  display: grid;
  gap: 0;
  margin: 0;
}

.sheet__facts div {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  padding: 9px 0;
  border-bottom: 1px solid var(--sheet-line);
}

.sheet__facts div:last-child {
  border-bottom: 0;
}

.sheet__facts dt {
  color: var(--sheet-body);
}

.sheet__facts dd {
  margin: 0;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  text-align: right;
}

/* Lo que falta se lee como pendiente, no como dato. */
.sheet__facts.is-missing dd {
  font-weight: 400;
  color: var(--sheet-muted);
}

.sheet__terms {
  display: grid;
  gap: 14px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.sheet__terms li {
  display: grid;
  gap: 3px;
}

.sheet__terms b {
  font-size: 13.5px;
  font-weight: 600;
}

.sheet__terms span {
  color: var(--sheet-body);
  font-size: 13.5px;
  line-height: 1.5;
}

.sheet__note {
  margin: 20px 0 0;
  padding-top: 14px;
  border-top: 1px solid var(--sheet-line);
  color: var(--sheet-muted);
  font-size: 13px;
  line-height: 1.55;
}

.sheet__foot {
  display: grid;
  gap: 10px;
  padding: 16px 22px 20px;
  border-top: 1px solid var(--sheet-line);
  background: var(--sheet-bg);
}

.sheet__foot p {
  margin: 0;
  color: var(--sheet-muted);
  font-size: 13px;
  line-height: 1.5;
}

.sheet__ask {
  height: 42px;
  border: 0;
  border-radius: 8px;
  background: var(--sheet-navy);
  color: #fff;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}

.sheet__ask:hover:not(:disabled) {
  background: #1f2452;
}

.sheet__ask:disabled {
  background: var(--sheet-fill);
  color: var(--sheet-muted);
  cursor: default;
}

.sheet button:focus-visible {
  outline: 2px solid #3b77f6;
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .sheet[open] .sheet__scrim,
  .sheet[open] .sheet__panel,
  .sheet__read.is-in {
    animation: none;
  }
}
</style>
