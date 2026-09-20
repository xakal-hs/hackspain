<script setup lang="ts">
import { Check, Copy, Landmark } from '@lucide/vue'
import type { EmbatLead, LeadStatus, LeadsResponse } from '../../shared/types/embat'

const COLUMNS: { id: LeadStatus; label: string }[] = [
  { id: 'nuevo', label: 'Nuevo' },
  { id: 'contactado', label: 'Contactado' },
  { id: 'reunion', label: 'Reunión' },
  { id: 'cerrado', label: 'Cerrado' },
]

const { data, refresh, error, pending } = await useAsyncData('embat-leads', () =>
  $fetch<LeadsResponse>('/api/embat/leads'),
)
const { patch } = useEmbatLeads()
const openId = ref<string | null>(null)
const copied = ref(false)

/* El aviso que la empresa acaba de pedir entra marcado: se anuncia una vez, en la primera
 * apertura de la pestaña, y la cookie se consume ahí mismo para no repetir la entrada. */
const fresh = useCookie<string | null>('xray-crm-fresh', { sameSite: 'lax' })
const landed = ref<string | null>(null)
onMounted(() => {
  const id = fresh.value
  if (!id || !data.value?.leads.some((lead) => lead.id === id)) return
  landed.value = id
  openId.value = id
  fresh.value = null
  window.setTimeout(() => {
    landed.value = null
  }, 4000)
})

const grouped = computed(() => {
  const leads = data.value?.leads || []
  return Object.fromEntries(
    COLUMNS.map((column) => [column.id, leads.filter((lead) => lead.status === column.id)]),
  ) as Record<LeadStatus, EmbatLead[]>
})

const landedLead = computed(() => data.value?.leads.find((lead) => lead.id === landed.value) || null)
const openLead = computed(() => data.value?.leads.find((lead) => lead.id === openId.value) || null)

function when(iso: string) {
  return new Intl.DateTimeFormat('es-ES', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(iso))
}

/* El importe llega ya escrito en es-ES («62.231 €»). Para sumar la etapa hay que deshacer el
 * formato: fuera el símbolo, el punto es el millar y la coma el decimal. */
function importe(lead: EmbatLead) {
  if (!lead.reason_amount) return 0
  const n = Number(lead.reason_amount.replace(/[^\d.,]/g, '').replace(/\./g, '').replace(',', '.'))
  return Number.isFinite(n) ? n : 0
}

function suma(id: LeadStatus) {
  const total = (grouped.value[id] || []).reduce((acc, lead) => acc + importe(lead), 0)
  if (!total) return null
  return `${new Intl.NumberFormat('es-ES', { maximumFractionDigits: 0 }).format(total)} €`
}

async function copyDraft(text: string) {
  await navigator.clipboard.writeText(text)
  copied.value = true
  window.setTimeout(() => {
    copied.value = false
  }, 1600)
}

async function move(lead: EmbatLead, status: LeadStatus) {
  if (status === lead.status) return
  const previo = lead.status
  /* La tarjeta cambia de columna en el momento del gesto; si el PATCH falla, vuelve a su sitio. */
  lead.status = status
  try {
    await patch({ id: lead.id, status })
    await refresh()
  } catch {
    lead.status = previo
  }
}

/* Arrastrar y soltar entre etapas: el estado vive aquí para pintar la columna de destino
 * mientras la tarjeta está en el aire. */
const dragId = ref<string | null>(null)
const overCol = ref<LeadStatus | null>(null)

function onDragStart(lead: EmbatLead, event: DragEvent) {
  dragId.value = lead.id
  if (!event.dataTransfer) return
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', lead.id)
}

function onDragEnd() {
  dragId.value = null
  overCol.value = null
}

function onDragOver(id: LeadStatus, event: DragEvent) {
  if (!dragId.value) return
  if (event.dataTransfer) event.dataTransfer.dropEffect = 'move'
  overCol.value = id
}

function onDragLeave(id: LeadStatus, event: DragEvent) {
  /* dragleave también salta al pasar de la columna a una tarjeta suya: si el puntero sigue
   * dentro, la columna no se apaga. */
  const from = event.currentTarget as Node | null
  const to = event.relatedTarget as Node | null
  if (from && to && from.contains(to)) return
  if (overCol.value === id) overCol.value = null
}

async function onDrop(status: LeadStatus) {
  const lead = data.value?.leads.find((item) => item.id === dragId.value) || null
  onDragEnd()
  if (lead) await move(lead, status)
}
</script>

<template>
  <div class="embat-app">
    <header class="embat-app__title">
      <h1>Financiación</h1>
    </header>

    <p v-if="landedLead" class="crm__landed" role="status">
      <Landmark :size="15" aria-hidden="true" />
      <span
        ><b>{{ landedLead.company_name }}</b> acaba de pedir un préstamo puente. Lo lleva
        {{ landedLead.assignee_name }}.</span
      >
    </p>

    <section class="embat-app__sheet crm__sheet" :aria-busy="pending">
      <p v-if="pending" class="embat-app__state">Cargando la cola.</p>
      <p v-else-if="error" class="embat-app__state" role="alert">
        No se pudo leer la cola de avisos.
        <button type="button" @click="refresh()">Reintentar</button>
      </p>
      <p v-else-if="!data?.leads.length" class="embat-app__state">
        Nadie ha pedido financiación todavía. El aviso entra aquí cuando una empresa pulsa «Quiero
        pedir financiación».
      </p>

      <!-- Tablero: las cuatro etapas del proceso de venta, en orden, y la tarjeta se arrastra
       * de una a la siguiente. -->
      <div v-else class="crm__board">
        <section
          v-for="column in COLUMNS"
          :key="column.id"
          class="crm__col"
          :class="{ 'is-over': overCol === column.id }"
          :aria-label="column.label"
          @dragover.prevent="onDragOver(column.id, $event)"
          @dragleave="onDragLeave(column.id, $event)"
          @drop.prevent="onDrop(column.id)"
        >
          <header class="crm__col-head">
            <b>{{ column.label }} <em>({{ grouped[column.id]?.length || 0 }})</em></b>
            <span v-if="suma(column.id)" class="crm__col-sum">{{ suma(column.id) }}</span>
          </header>

          <ol class="crm__stack">
            <li v-for="lead in grouped[column.id]" :key="lead.id">
              <button
                type="button"
                class="crm__card"
                draggable="true"
                :class="{ 'is-on': openId === lead.id, 'is-landing': landed === lead.id, 'is-dragging': dragId === lead.id }"
                :aria-pressed="openId === lead.id"
                @click="openId = lead.id"
                @dragstart="onDragStart(lead, $event)"
                @dragend="onDragEnd"
              >
                <b>{{ lead.company_name }}</b>
                <em class="crm__why"
                  >{{ lead.reason }}<i v-if="lead.reason_amount"> · {{ lead.reason_amount }}</i></em
                >
                <span class="crm__card-quien">
                  {{ lead.assignee_name }}
                  <small v-if="lead.assignee_title">{{ lead.assignee_title }}</small>
                </span>
                <time :datetime="lead.created_at">{{ when(lead.created_at) }}</time>
              </button>
            </li>
          </ol>

          <p v-if="!grouped[column.id]?.length" class="crm__col-empty">
            {{ overCol === column.id ? 'Suelta aquí' : 'Ningún aviso' }}
          </p>
        </section>
      </div>
    </section>

    <aside
      v-if="openLead"
      class="embat-app__dialog embat-app__dialog--wide"
      role="dialog"
      aria-modal="true"
      aria-labelledby="crm-ficha-title"
    >
      <header>
        <div>
          <h2 id="crm-ficha-title">{{ openLead.company_name }}</h2>
          <p>
            Asignada a {{ openLead.assignee_name
            }}<template v-if="openLead.assignee_title">, {{ openLead.assignee_title }}</template>. El
            correo no nombra a la empresa.
          </p>
        </div>
        <button type="button" @click="openId = null">Cerrar</button>
      </header>
      <p class="crm__motivo">
        <b>Llama por el préstamo.</b>
        {{ openLead.reason_detail || 'Pidió financiación desde su panel de flujo de caja.' }}
        El correo de abajo no nombra a la empresa: solo la señal y la llamada.
      </p>
      <div class="embat-app__chips" role="group" aria-label="Cambiar estado">
        <button
          v-for="column in COLUMNS"
          :key="column.id"
          type="button"
          class="embat-app__chip"
          :class="{ 'is-on': openLead.status === column.id }"
          @click="move(openLead, column.id)"
        >
          {{ column.label }}
        </button>
      </div>
      <pre class="embat-app__draft">{{ openLead.email_draft }}</pre>
      <div class="embat-app__chips">
        <button type="button" class="embat-app__chip" @click="copyDraft(openLead.email_draft)">
          <Check v-if="copied" :size="14" aria-hidden="true" />
          <Copy v-else :size="14" aria-hidden="true" />
          {{ copied ? 'Copiado' : 'Copiar el draft' }}
        </button>
      </div>
    </aside>
  </div>
</template>

<style scoped>
/* ── Tablero ─────────────────────────────────────────────────────────────── */

/* El tablero ocupa el alto que queda: las columnas llegan abajo y hay sitio de sobra
 * donde soltar la tarjeta. */
.crm__sheet {
  display: flex;
  min-height: 0;
  padding-bottom: 0;
}
.crm__board {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  flex: 1;
  min-width: 0;
}
.crm__col {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 0 14px 18px;
  border-left: 1px solid var(--ea-line);
  transition: background 0.14s ease;
}
.crm__col:first-child {
  padding-left: 0;
  border-left: 0;
}
.crm__col:last-child {
  padding-right: 0;
}
/* Mientras la tarjeta está en el aire, la columna de destino se enciende. */
.crm__col.is-over {
  background: color-mix(in srgb, var(--ea-blue) 5%, transparent);
}

/* Una sola línea: la etapa con su recuento a la izquierda y lo que suma a la derecha.
 * Los dos datos pesan igual, así que comparten cuerpo de letra. */
.crm__col-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  height: 52px;
  border-bottom: 1px solid var(--ea-line);
}
.crm__col-head b {
  overflow: hidden;
  font-size: 14px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.crm__col-head em {
  color: var(--ea-muted);
  font-style: normal;
  font-weight: 500;
}
.crm__col-sum {
  flex: none;
  color: var(--ea-text);
  font-size: 14px;
  font-weight: 600;
}

.crm__stack {
  display: grid;
  align-content: start;
  gap: 8px;
  margin: 0;
  padding: 12px 0 0;
  list-style: none;
}

.crm__card {
  display: grid;
  gap: 2px;
  width: 100%;
  padding: 10px 11px;
  border: 1px solid var(--ea-line);
  border-radius: 8px;
  background: var(--ea-bg);
  color: var(--ea-body);
  font: inherit;
  text-align: left;
  cursor: grab;
  transition: border-color 0.14s ease, background 0.14s ease;
}
.crm__card:hover {
  background: var(--ea-hover);
}
.crm__card.is-on {
  border-color: color-mix(in srgb, var(--ea-blue) 45%, var(--ea-line));
  background: var(--ea-hover);
}
.crm__card:active {
  cursor: grabbing;
}
/* La tarjeta que viaja se queda en su hueco, apagada, para no perder el sitio de origen. */
.crm__card.is-dragging {
  opacity: 0.4;
}
.crm__card b {
  color: var(--ea-text);
  font-size: 13px;
  font-weight: 600;
}
.crm__card-quien {
  margin-top: 4px;
  color: var(--ea-body);
}
.crm__card-quien small,
.crm__card time {
  display: block;
  color: var(--ea-muted);
  font-size: 11px;
}
.crm__card time {
  margin-top: 3px;
}

.crm__col-empty {
  margin: 12px 0 0;
  padding: 14px 0;
  border: 1px dashed var(--ea-line);
  border-radius: 8px;
  color: var(--ea-muted);
  text-align: center;
}
.crm__col.is-over .crm__col-empty {
  border-color: color-mix(in srgb, var(--ea-blue) 40%, var(--ea-line));
  color: var(--ea-blue);
}

/* ── Común ───────────────────────────────────────────────────────────────── */

/* El chrome de Embat es siempre claro, así que estos colores salen de sus propios tokens:
 * con los del tema global el ámbar caía a 1.7:1 y el motivo quedaba blanco sobre blanco
 * en cuanto el usuario ponía X-Ray en oscuro. */

/* El motivo viaja pegado al nombre: el comercial sabe por qué llaman antes de abrir la ficha. */
.crm__why {
  /* Cuelga del nombre en su propia línea, pero el fondo sólo abraza al texto. */
  display: block;
  width: fit-content;
  margin: 3px 0 1px;
  padding: 3px 7px;
  /* Con el importe dentro la etiqueta cae a dos líneas en las columnas estrechas:
   * una esquina suave aguanta el salto mejor que la píldora. */
  border-radius: 9px;
  line-height: 1.45;
  background: color-mix(in srgb, var(--ea-amber) 11%, transparent);
  color: var(--ea-amber);
  font-size: 11px;
  font-style: normal;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.crm__why i {
  font-style: normal;
}
.crm__motivo {
  margin: 0 0 14px;
  color: var(--ea-body);
  font-size: 13.5px;
  line-height: 1.55;
}
.crm__motivo b {
  color: var(--ea-text);
}

.crm__landed {
  display: flex;
  align-items: center;
  gap: 9px;
  margin: 12px 24px 0;
  padding: 10px 14px;
  border: 1px solid color-mix(in srgb, var(--ea-blue) 30%, var(--ea-line));
  border-radius: 8px;
  background: color-mix(in srgb, var(--ea-blue) 7%, transparent);
  color: var(--ea-blue);
  font-size: 13.5px;
  animation: crm-land 0.42s ease both;
}
.crm__landed svg {
  flex: none;
}

/* El aviso recién pedido aterriza una vez: entra desde arriba y el borde late dos veces.
 * Pasados cuatro segundos vuelve a ser una fila más. */
.crm__card.is-landing {
  animation: crm-land 0.42s ease both, crm-ring 1.1s ease 0.24s 2;
}
@keyframes crm-land {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@keyframes crm-ring {
  from {
    box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--ea-blue) 55%, transparent);
  }
  to {
    box-shadow: inset 0 0 0 1px transparent;
  }
}

@media (max-width: 900px) {
  /* En pantalla estrecha el tablero se recorre de lado, con las columnas a un ancho legible. */
  .crm__board {
    grid-template-columns: repeat(4, minmax(230px, 1fr));
  }
}
</style>
