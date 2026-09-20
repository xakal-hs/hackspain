<script setup lang="ts">
import { Check, ChevronRight, ChevronsUpDown, Copy, Landmark } from '@lucide/vue'
import type { EmbatLead, LeadStatus, LeadsResponse } from '../../shared/types/embat'

const COLUMNS: { id: LeadStatus; label: string; hint: string }[] = [
  { id: 'nuevo', label: 'Nuevo', hint: 'Acaba de pedir financiación' },
  { id: 'contactado', label: 'Contactado', hint: 'El comercial ya ha escrito' },
  { id: 'reunion', label: 'Reunión', hint: 'Hay una llamada en el calendario' },
  { id: 'cerrado', label: 'Cerrado', hint: 'La petición ya no está abierta' },
]

const { data, refresh, error, pending } = await useAsyncData('embat-leads', () =>
  $fetch<LeadsResponse>('/api/embat/leads'),
)
const { patch } = useEmbatLeads()
const openId = ref<string | null>(null)
const copied = ref(false)
const abiertos = ref(new Set<LeadStatus>(COLUMNS.map((column) => column.id)))

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
const todoAbierto = computed(() => COLUMNS.every((column) => abiertos.value.has(column.id)))

function plegar(id: LeadStatus) {
  const next = new Set(abiertos.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  abiertos.value = next
}

function plegarTodo() {
  abiertos.value = todoAbierto.value ? new Set() : new Set<LeadStatus>(COLUMNS.map((column) => column.id))
}

function when(iso: string) {
  return new Intl.DateTimeFormat('es-ES', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(iso))
}

function nAvisos(n: number) {
  return `${n} ${n === 1 ? 'aviso' : 'avisos'}`
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
  await patch({ id: lead.id, status })
  await refresh()
}
</script>

<template>
  <div class="embat-app">
    <header class="embat-app__title">
      <h1>Financiación</h1>
      <div class="embat-app__tools">
        <button
          type="button"
          class="embat-app__icon"
          :aria-label="todoAbierto ? 'Plegar todo' : 'Desplegar todo'"
          @click="plegarTodo"
        >
          <ChevronsUpDown :size="16" aria-hidden="true" />
        </button>
      </div>
    </header>

    <p v-if="landedLead" class="crm__landed" role="status">
      <Landmark :size="15" aria-hidden="true" />
      <span
        ><b>{{ landedLead.company_name }}</b> acaba de pedir un préstamo puente. Lo lleva
        {{ landedLead.assignee_name }}.</span
      >
    </p>

    <section class="embat-app__sheet" :aria-busy="pending">
      <p v-if="pending" class="embat-app__state">Cargando la cola.</p>
      <p v-else-if="error" class="embat-app__state" role="alert">
        No se pudo leer la cola de avisos.
        <button type="button" @click="refresh()">Reintentar</button>
      </p>
      <p v-else-if="!data?.leads.length" class="embat-app__state">
        Nadie ha pedido financiación todavía. El aviso entra aquí cuando una empresa pulsa «Quiero
        pedir financiación».
      </p>

      <template v-else>
        <article v-for="column in COLUMNS" :key="column.id" class="embat-app__group">
          <header>
            <button type="button" :aria-expanded="abiertos.has(column.id)" @click="plegar(column.id)">
              <ChevronRight :size="16" aria-hidden="true" />
            </button>
            <b>{{ column.label }}</b>
            <span>{{ column.hint }}</span>
            <em>{{ nAvisos(grouped[column.id]?.length || 0) }}</em>
          </header>
          <table v-if="abiertos.has(column.id) && grouped[column.id]?.length" :aria-label="`Peticiones ${column.label.toLowerCase()}`">
            <tbody>
              <tr
                v-for="lead in grouped[column.id]"
                :key="lead.id"
                :class="{ 'is-on': openId === lead.id, 'is-landing': landed === lead.id }"
                @click="openId = lead.id"
              >
                <th scope="row">
                  {{ lead.company_name }}
                  <em class="crm__why"
                    >{{ lead.reason }}<i v-if="lead.reason_amount"> · {{ lead.reason_amount }}</i></em
                  >
                </th>
                <td class="embat-app__meta">
                  {{ lead.assignee_name }}
                  <small v-if="lead.assignee_title">{{ lead.assignee_title }}</small>
                </td>
                <td class="embat-app__meta">{{ when(lead.created_at) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else-if="abiertos.has(column.id)" class="embat-app__empty">Ningún aviso en este estado.</p>
        </article>
      </template>
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
/* El motivo viaja pegado al nombre: el comercial sabe por qué llaman antes de abrir la ficha. */
.crm__why {
  display: block;
  margin-top: 3px;
  color: var(--amber-ink);
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
  color: var(--text-muted);
  font-size: 13.5px;
  line-height: 1.55;
}
.crm__motivo b {
  color: var(--text);
}

.crm__landed {
  display: flex;
  align-items: center;
  gap: 9px;
  margin: 0 0 12px;
  padding: 10px 14px;
  border: 1px solid color-mix(in srgb, var(--live) 32%, var(--line));
  border-radius: var(--r-inner);
  background: var(--live-wash);
  color: var(--live-ink);
  font-size: 13.5px;
  animation: crm-land 0.42s var(--ease) both;
}
.crm__landed svg {
  flex: none;
}

/* El aviso recién pedido aterriza una vez: entra desde arriba y el borde late dos veces.
 * Pasados cuatro segundos vuelve a ser una fila más. */
tr.is-landing {
  animation: crm-land 0.42s var(--ease) both, crm-ring 1.1s var(--ease) 0.24s 2;
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
    box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--live) 55%, transparent);
  }
  to {
    box-shadow: inset 0 0 0 1px transparent;
  }
}
</style>
