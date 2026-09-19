<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import {
  BadgeCheck,
  ChevronRight,
  ChevronsUpDown,
  CircleAlert,
  CircleCheck,
  CircleX,
  EllipsisVertical,
  Search,
  ShieldCheck,
} from '@lucide/vue'
import type { ClientBookResponse, ClientRow } from '../../shared/types/company'

/* Crédito y caución, con la lista agrupada de «Conexiones bancarias» de Embat: cada fila es un
 * cliente del ERP con lo que se sabe de cómo paga, y la acción al final. Va siempre en claro. */

const { selectedId } = useSelectedCompany()

const libro = useQuery({
  queryKey: computed(() => ['clientes', selectedId.value]),
  queryFn: () => $fetch<ClientBookResponse>(`/api/clientes/${encodeURIComponent(selectedId.value)}`),
  staleTime: 60 * 1000,
})
/* Sin esperar la consulta, el servidor pinta la pantalla vacía y el cliente llega con los datos:
 * la hidratación no cuadra y se ve un parpadeo al cargar. */
onServerPrefetch(() => libro.suspense())

const query = ref('')
const detalle = ref<ClientRow | null>(null)
const solicitados = ref(new Set<string>())

type Estado = ClientRow['estado']
const grupos: { id: Estado; label: string; icon: typeof CircleCheck; hint: string }[] = [
  { id: 'preautorizado', label: 'Preautorizados', icon: CircleCheck, hint: 'Cobertura inmediata: Embat ya tiene las pruebas de pago' },
  { id: 'estudio', label: 'En estudio', icon: CircleAlert, hint: '' },
  { id: 'denegado', label: 'Denegados', icon: CircleX, hint: '' },
]

const clientes = computed(() => libro.data.value?.clientes ?? [])
const visibles = computed(() => {
  const needle = query.value.trim().toLocaleLowerCase('es')
  return clientes.value.filter((row) => !needle || row.cliente.toLocaleLowerCase('es').includes(needle))
})
const porEstado = (estado: Estado) => visibles.value.filter((row) => row.estado === estado)

const abiertos = ref(new Set<Estado | 'caucion'>(['preautorizado', 'estudio', 'denegado', 'caucion']))
function plegar(id: Estado | 'caucion') {
  const next = new Set(abiertos.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  abiertos.value = next
}
const todoAbierto = computed(() => abiertos.value.size === 4)
const plegarTodo = () =>
  (abiertos.value = todoAbierto.value ? new Set() : new Set<Estado | 'caucion'>(['preautorizado', 'estudio', 'denegado', 'caucion']))

const preautorizados = computed(() => clientes.value.filter((row) => row.estado === 'preautorizado'))
const caucion = computed(() => libro.data.value?.caucion ?? null)
const excedente = computed(() => libro.data.value?.excedente ?? null)
/* Pignorar excedente como contragarantía: la aseguradora exige menos y la prima baja. La capacidad
 * de 4× el colateral y el ahorro del 30 % son hipótesis de producto, no precio de nadie. */
const caucionPropuesta = computed(() => (excedente.value && excedente.value > 0 ? excedente.value * 4 : null))

const cover = computed(() => libro.data.value?.cover ?? 0.9)
const nf = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 0, useGrouping: 'always' } as Intl.NumberFormatOptions)
const money = (v: number) => `${nf.format(v)} €`
const dias = (v: number | null) =>
  v == null ? '—' : v === 0 ? 'en fecha' : v < 0 ? `${nf.format(-v)} d antes` : `${nf.format(v)} d tarde`
const nClientes = (n: number) => `${n} ${n === 1 ? 'cliente' : 'clientes'}`
const meses = (v: number) => `${v} ${v === 1 ? 'mes' : 'meses'}`

function pedir(row: ClientRow) {
  solicitados.value = new Set(solicitados.value).add(row.cliente)
}
watch(selectedId, () => {
  solicitados.value = new Set()
  detalle.value = null
})
</script>

<template>
  <div class="cc">
    <header class="cc__title">
      <h1>Crédito y caución</h1>
      <div class="cc__tools">
        <button
          type="button"
          class="cc__icon"
          :aria-label="todoAbierto ? 'Plegar todo' : 'Desplegar todo'"
          @click="plegarTodo"
        >
          <ChevronsUpDown :size="16" aria-hidden="true" />
        </button>
        <label class="cc__search">
          <Search :size="16" aria-hidden="true" />
          <input v-model="query" type="search" placeholder="Buscar cliente" aria-label="Buscar cliente" />
        </label>
      </div>
    </header>


    <section class="cc__sheet" :aria-busy="libro.isPending.value">
      <p v-if="libro.isPending.value" class="cc__state">Cargando clientes…</p>
      <p v-else-if="libro.isError.value" class="cc__state" role="alert">
        No se pudo cargar la cartera de clientes.
        <button type="button" @click="libro.refetch()">Reintentar</button>
      </p>
      <p v-else-if="!clientes.length" class="cc__state">
        Esta empresa no tiene facturas de venta en el ERP, así que no hay clientes que asegurar.
      </p>

      <template v-else>
        <article v-for="grupo in grupos" :key="grupo.id" class="cc__group">
          <header>
            <button type="button" :aria-expanded="abiertos.has(grupo.id)" @click="plegar(grupo.id)">
              <ChevronRight :size="16" aria-hidden="true" />
            </button>
            <component :is="grupo.icon" :size="17" aria-hidden="true" :class="`cc__dot is-${grupo.id}`" />
            <b>{{ grupo.label }}</b>
            <span v-if="grupo.hint">{{ grupo.hint }}</span>
            <em>{{ nClientes(porEstado(grupo.id).length) }}</em>
          </header>
          <table v-if="abiertos.has(grupo.id) && porEstado(grupo.id).length">
            <tbody>
              <tr v-for="row in porEstado(grupo.id)" :key="row.cliente" @click="detalle = row">
                <th scope="row">{{ row.cliente }}</th>
                <td class="cc__do">
                  <button
                    v-if="row.estado !== 'denegado'"
                    type="button"
                    class="cc__chip"
                    :class="{ 'is-done': solicitados.has(row.cliente) }"
                    :disabled="solicitados.has(row.cliente)"
                    @click.stop="pedir(row)"
                  >
                    <BadgeCheck v-if="solicitados.has(row.cliente)" :size="14" aria-hidden="true" />
                    {{
                      solicitados.has(row.cliente)
                        ? 'Solicitada'
                        : row.estado === 'preautorizado'
                          ? 'Pedir cobertura'
                          : 'Pedir estudio'
                    }}
                  </button>
                  <span v-else class="cc__chip is-off">Sin cobertura</span>
                </td>
                <td class="cc__meta">{{ meses(row.meses_relacion) }} · {{ row.n_pagadas }} cobradas</td>
                <td class="cc__meta">{{ dias(row.retraso_medio) }}</td>
                <td>{{ money(row.ventas_12m) }}<small>ventas 12m</small></td>
                <td>{{ money(row.expuesto) }}<small>expuesto</small></td>
                <td class="cc__amount">
                  {{ row.estado === 'denegado' || !row.limite ? '—' : money(row.limite) }}<small>límite</small>
                </td>
                <td class="cc__more">
                  <EllipsisVertical :size="16" aria-hidden="true" />
                </td>
              </tr>
            </tbody>
          </table>
          <p v-else-if="abiertos.has(grupo.id)" class="cc__empty">Ningún cliente en este estado.</p>
        </article>

        <article class="cc__group">
          <header>
            <button type="button" :aria-expanded="abiertos.has('caucion')" @click="plegar('caucion')">
              <ChevronRight :size="16" aria-hidden="true" />
            </button>
            <ShieldCheck :size="17" aria-hidden="true" class="cc__dot is-caucion" />
            <b>Caución</b>
            <em>{{ caucion ? `${caucion.productos} ${caucion.productos === 1 ? 'línea' : 'líneas'}` : 'sin línea' }}</em>
          </header>
          <table v-if="abiertos.has('caucion')">
            <tbody>
              <tr v-if="caucion">
                <th scope="row">Línea contratada</th>
                <td class="cc__do"><span class="cc__chip is-off">Vigente</span></td>
                <td class="cc__meta">{{ caucion.productos }} productos</td>
                <td class="cc__meta">Afianzado {{ money(caucion.afianzado) }}</td>
                <td>{{ money(caucion.linea - caucion.afianzado) }}<small>disponible</small></td>
                <td>{{ money(caucion.afianzado) }}<small>en riesgo</small></td>
                <td class="cc__amount">{{ money(caucion.linea) }}<small>línea</small></td>
                <td class="cc__more"><EllipsisVertical :size="16" aria-hidden="true" /></td>
              </tr>
              <tr v-if="caucionPropuesta">
                <th scope="row">{{ caucion ? 'Ampliación con tu excedente' : 'Línea con tu excedente' }}</th>
                <td class="cc__do">
                  <button type="button" class="cc__chip">Pignorar excedente</button>
                </td>
                <td class="cc__meta">Sin consumir CIRBE</td>
                <td class="cc__meta"></td>
                <td>{{ money(excedente || 0) }}<small>excedente</small></td>
                <td>4×<small>capacidad estimada</small></td>
                <td class="cc__amount">{{ money(caucionPropuesta) }}<small>línea estimada</small></td>
                <td class="cc__more"><EllipsisVertical :size="16" aria-hidden="true" /></td>
              </tr>
              <tr v-else-if="!caucion">
                <th scope="row">Sin línea de caución</th>
                <td class="cc__do"><span class="cc__chip is-off">No disponible</span></td>
                <td class="cc__meta" colspan="5">
                  Hace falta caja sobrante que pignorar o balance que la aseguradora acepte como contragarantía.
                </td>
                <td class="cc__more"><EllipsisVertical :size="16" aria-hidden="true" /></td>
              </tr>
            </tbody>
          </table>
        </article>
      </template>
    </section>


    <!-- Ficha del cliente: las pruebas que sostienen la decisión. -->
    <dialog v-if="detalle" ref="ficha" class="cc__dialog" open @close="detalle = null">
      <header>
        <div>
          <h2>{{ detalle.cliente }}</h2>
          <p>{{ detalle.motivo }}</p>
        </div>
        <button type="button" @click="detalle = null">Cerrar</button>
      </header>
      <dl>
        <div>
          <dt>Ventas 12 meses</dt>
          <dd>{{ money(detalle.ventas_12m) }}</dd>
        </div>
        <div>
          <dt>Debe hoy</dt>
          <dd>{{ money(detalle.expuesto) }}</dd>
        </div>
        <div>
          <dt>Vencido</dt>
          <dd>{{ money(detalle.vencido) }}</dd>
        </div>
        <div>
          <dt>Mayor deuda que ya devolvió</dt>
          <dd>{{ money(detalle.pico) }}</dd>
        </div>
        <div>
          <dt>Paga</dt>
          <dd>{{ dias(detalle.retraso_medio) }}</dd>
        </div>
        <div>
          <dt>Facturas cobradas</dt>
          <dd>{{ detalle.n_pagadas }} de {{ detalle.n_facturas }}</dd>
        </div>
        <div v-if="detalle.estado !== 'denegado'">
          <dt>Límite y cobertura</dt>
          <dd>{{ money(detalle.limite) }} al {{ Math.round(cover * 100) }} %</dd>
        </div>
        <div v-if="detalle.estado !== 'denegado'">
          <dt>Prima estimada</dt>
          <dd>{{ money(detalle.prima) }} al año</dd>
        </div>
      </dl>
      <p class="cc__note">
        La aseguradora clasificaría a este cliente con cuentas depositadas en el registro, a veces de
        hace año y medio. Estas cifras son facturas y cobros conciliados con el banco hasta el
        {{ libro.data.value?.snapshot }}. La prima y el porcentaje de cobertura son hipótesis de producto.
      </p>
    </dialog>
  </div>
</template>

<style scoped>
/* Misma paleta muestreada de Embat que la pantalla de Flujo de caja. */
.cc {
  --cc-bg: #ffffff;
  --cc-line: #e8eaee;
  --cc-soft: #eff1f4;
  --cc-text: #1b1f2a;
  --cc-body: #3a4050;
  --cc-muted: #737a8a;
  --cc-fill: #e8e8ed;
  --cc-hover: #f7f8fa;
  --cc-navy: #131736;
  --cc-blue: #3b77f6;
  --cc-green: #1d8a5c;
  --cc-amber: #b07a12;
  --cc-red: #c0392f;

  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 100vh;
  background: var(--cc-bg);
  color: var(--cc-text);
  font-family: 'Inter', ui-sans-serif, system-ui, sans-serif;
  font-size: 13px;
  font-feature-settings: 'tnum' 1;
  color-scheme: light;
}

.cc__title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px 16px;
  min-height: 56px;
  padding: 0 24px;
  border-bottom: 1px solid var(--cc-line);
}

.cc__title h1 {
  margin: 0;
  font-size: 17px;
  font-weight: 500;
  letter-spacing: -0.01em;
}








.cc__tools {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cc__icon {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 5px;
  background: none;
  color: var(--cc-body);
  cursor: pointer;
}

.cc__icon:hover {
  background: var(--cc-hover);
}







.cc__search {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 30px;
  padding: 0 10px;
  border: 1px solid transparent;
  border-radius: 5px;
  color: var(--cc-muted);
}

.cc__search:focus-within {
  border-color: #dfe2e7;
}

.cc__search input {
  width: 180px;
  border: 0;
  background: transparent;
  color: var(--cc-text);
  font: inherit;
}

.cc__search input:focus {
  outline: none;
}

.cc button:focus-visible,
.cc input:focus-visible {
  outline: 2px solid var(--cc-blue);
  outline-offset: 2px;
}

.cc__sheet {
  flex: 1;
  min-width: 0;
  padding: 0 24px 24px;
}

.cc__state {
  margin: 0;
  padding: 24px 0;
  color: var(--cc-muted);
}

.cc__empty {
  margin: 0;
  padding: 14px 0 14px 36px;
  border-bottom: 1px solid var(--cc-soft);
  color: var(--cc-muted);
}

.cc__state button {
  margin-left: 6px;
  border: 0;
  background: none;
  color: var(--cc-blue);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}

/* Grupo: cabecera con su cuenta y la tabla debajo, como en Conexiones bancarias. */
.cc__group header {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 52px;
  border-bottom: 1px solid var(--cc-line);
}

.cc__group header button {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border: 0;
  border-radius: 5px;
  background: none;
  color: var(--cc-body);
  cursor: pointer;
}

.cc__group header button[aria-expanded='true'] svg {
  transform: rotate(90deg);
}

.cc__group header b {
  font-size: 14px;
  font-weight: 600;
}

.cc__group header span {
  color: var(--cc-muted);
}

.cc__group header em {
  margin-left: auto;
  font-style: normal;
  color: var(--cc-muted);
}

.cc__dot.is-preautorizado {
  color: var(--cc-green);
}

.cc__dot.is-estudio {
  color: var(--cc-amber);
}

.cc__dot.is-denegado {
  color: var(--cc-red);
}

.cc__dot.is-caucion {
  color: var(--cc-blue);
}

table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}

tbody tr {
  cursor: pointer;
}

tbody tr:hover > * {
  background: var(--cc-hover);
}

th,
td {
  height: 40px;
  padding: 0 10px;
  border-bottom: 1px solid var(--cc-soft);
  text-align: right;
  white-space: nowrap;
  color: var(--cc-body);
}

th[scope='row'] {
  padding-left: 36px;
  font-weight: 500;
  text-align: left;
  color: var(--cc-text);
}

td small {
  display: block;
  margin-top: -2px;
  font-size: 11px;
  color: var(--cc-muted);
}

.cc__meta {
  text-align: left;
  color: var(--cc-muted);
}

.cc__do {
  text-align: left;
}

.cc__amount {
  font-weight: 600;
  color: var(--cc-text);
}

.cc__more {
  width: 36px;
  color: var(--cc-muted);
}

.cc__chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 26px;
  padding: 0 10px;
  border: 0;
  border-radius: 5px;
  background: var(--cc-fill);
  color: var(--cc-body);
  font: inherit;
  font-weight: 500;
  cursor: pointer;
}

.cc__chip:hover:not(:disabled):not(.is-off) {
  background: #dbe4fb;
  color: var(--cc-blue);
}

.cc__chip.is-done {
  background: #e4f2ea;
  color: var(--cc-green);
  cursor: default;
}

.cc__chip.is-off {
  background: transparent;
  color: var(--cc-muted);
  cursor: default;
}



.cc__dialog {
  position: fixed;
  inset: auto 24px 24px auto;
  z-index: 5;
  width: min(440px, calc(100vw - 48px));
  margin: 0;
  padding: 18px 20px 20px;
  border: 1px solid var(--cc-line);
  border-radius: 12px;
  background: #fff;
  color: var(--cc-text);
  box-shadow: 0 18px 44px -20px rgb(16 20 40 / 0.45);
}

.cc__dialog header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.cc__dialog h2 {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 600;
}

.cc__dialog header p {
  margin: 0;
  color: var(--cc-muted);
  line-height: 1.45;
}

.cc__dialog header button {
  border: 0;
  background: none;
  color: var(--cc-blue);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}

.cc__dialog dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 18px;
  margin: 16px 0 0;
}

.cc__dialog dt {
  color: var(--cc-muted);
}

.cc__dialog dd {
  margin: 2px 0 0;
  font-weight: 600;
}

.cc__note {
  margin: 16px 0 0;
  padding-top: 12px;
  border-top: 1px solid var(--cc-soft);
  color: var(--cc-muted);
  line-height: 1.5;
}

@media (max-width: 900px) {
  .cc__title {
    padding-inline: 16px;
  }

  .cc__sheet {
    padding-inline: 16px;
    overflow-x: auto;
  }

  .cc__search input {
    width: 120px;
  }

  /* La pista de cada grupo aprieta la cabecera en móvil: manda el nombre y la cuenta. */
  .cc__group header span {
    display: none;
  }

  .cc__group header em {
    white-space: nowrap;
  }

  table {
    min-width: 720px;
  }

  .cc__dialog {
    inset: auto 12px 12px 12px;
    width: auto;
  }
}
</style>
