<script setup lang="ts">
import { Copy, Check } from '@lucide/vue'
import type { EmbatLead, LeadStatus, LeadsResponse } from '../../shared/types/embat'

const COLUMNS: { id: LeadStatus; label: string }[] = [
  { id: 'nuevo', label: 'Nuevo' },
  { id: 'contactado', label: 'Contactado' },
  { id: 'reunion', label: 'Reunión' },
  { id: 'cerrado', label: 'Cerrado' },
]

const { data, refresh, error, pending } = await useAsyncData('embat-leads', () => $fetch<LeadsResponse>('/api/embat/leads'))
const { patch } = useEmbatLeads()
const openId = ref<string | null>(null)
const copied = ref(false)

const grouped = computed(() => {
  const leads = data.value?.leads || []
  return Object.fromEntries(
    COLUMNS.map((column) => [column.id, leads.filter((lead) => lead.status === column.id)]),
  ) as Record<LeadStatus, EmbatLead[]>
})

const openLead = computed(
  () => data.value?.leads.find((lead) => lead.id === openId.value) || null,
)

function when(iso: string) {
  return new Intl.DateTimeFormat('es-ES', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(iso))
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
  <div class="wk__grid crm">
    <section class="panel span-12">
      <header class="panel__bar">
        <h2 class="panel__title">Peticiones de financiación</h2>
        <span class="chip chip--neutral">{{ data?.leads.length || 0 }} avisos</span>
      </header>
      <p class="lead-line">
        Cuando una empresa pulsa «Quiero pedir financiación», el aviso entra aquí y se asigna a un
        comercial de Equipo. El correo es genérico: no lleva datos de la empresa.
      </p>
      <p v-if="pending" class="empty">Cargando la cola.</p>
      <p v-else-if="error" class="empty">No se pudo leer la cola de avisos.</p>
    </section>

    <section
      v-for="column in COLUMNS"
      :key="column.id"
      class="panel span-3 crm__col"
    >
      <header class="panel__bar">
        <h2 class="panel__title">{{ column.label }}</h2>
        <span class="chip chip--neutral">{{ grouped[column.id]?.length || 0 }}</span>
      </header>
      <ol class="crm__list">
        <li v-for="lead in grouped[column.id]" :key="lead.id">
          <button type="button" class="crm__card" :aria-pressed="openId === lead.id" @click="openId = lead.id">
            <b>{{ lead.company_name }}</b>
            <span>{{ lead.assignee_name }}</span>
            <small v-if="lead.assignee_title">{{ lead.assignee_title }}</small>
            <time>{{ when(lead.created_at) }}</time>
          </button>
        </li>
      </ol>
      <p v-if="!grouped[column.id]?.length" class="empty">Vacío.</p>
    </section>

    <section v-if="openLead" class="panel span-12 sheet">
      <header class="panel__bar">
        <h2 class="panel__title">{{ openLead.company_name }}</h2>
        <span class="chip chip--neutral">{{ openLead.assignee_name }}</span>
        <span v-if="openLead.assignee_title" class="chip chip--neutral">{{ openLead.assignee_title }}</span>
      </header>
      <p class="sheet__why">
        Pidió financiación. El correo de abajo no nombra a la empresa: solo la señal y la llamada.
      </p>
      <label class="filters__field">
        Estado
        <select :value="openLead.status" aria-label="Cambiar estado" @change="move(openLead, ($event.target as HTMLSelectElement).value as LeadStatus)">
          <option v-for="column in COLUMNS" :key="column.id" :value="column.id">{{ column.label }}</option>
        </select>
      </label>
      <pre class="crm__draft">{{ openLead.email_draft }}</pre>
      <button class="btn btn--live" type="button" @click="copyDraft(openLead.email_draft)">
        <Check v-if="copied" :size="15" aria-hidden="true" />
        <Copy v-else :size="15" aria-hidden="true" />
        {{ copied ? 'Copiado' : 'Copiar el draft' }}
      </button>
    </section>
  </div>
</template>

<style scoped>
.crm__list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.crm__card {
  display: grid;
  gap: 2px;
  width: 100%;
  padding: 12px 12px 10px;
  border: 1px solid var(--line);
  border-radius: var(--r-inner);
  background: var(--panel-raised);
  text-align: left;
}
.crm__card[aria-pressed='true'] {
  border-color: var(--live);
}
.crm__card b {
  font-size: 14px;
}
.crm__card span,
.crm__card small,
.crm__card time {
  color: var(--text-muted);
  font-size: 12.5px;
}
.crm__card small {
  font-weight: 400;
}
.crm__draft {
  margin: 16px 0;
  padding: 16px 18px;
  border: 1px solid var(--line);
  border-radius: var(--r-inner);
  background: var(--panel-raised);
  white-space: pre-wrap;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.55;
}
.sheet .btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
@media (max-width: 900px) {
  .crm__col { grid-column: span 12; }
}
</style>
