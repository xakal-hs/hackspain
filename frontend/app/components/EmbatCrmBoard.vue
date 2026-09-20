<script setup lang="ts">
import { Check, ChevronRight, ChevronsUpDown, Copy } from '@lucide/vue'
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

const grouped = computed(() => {
  const leads = data.value?.leads || []
  return Object.fromEntries(
    COLUMNS.map((column) => [column.id, leads.filter((lead) => lead.status === column.id)]),
  ) as Record<LeadStatus, EmbatLead[]>
})

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
                :class="{ 'is-on': openId === lead.id }"
                @click="openId = lead.id"
              >
                <th scope="row">{{ lead.company_name }}</th>
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
