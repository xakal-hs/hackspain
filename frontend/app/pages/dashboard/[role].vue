<script setup lang="ts">
import {
  ArrowUpRight,
  ArrowDownRight,
  ArrowRight,
  Search,
  Activity,
  Check,
  Building2,
} from "@lucide/vue";
import {
  perspectives,
  demoCompanies,
  initialOffers,
  euros,
  type Perspective,
  type DemoOffer,
} from "~/data/demo";
definePageMeta({
  middleware: [
    function (to) {
      if (!perspectives.some((p) => p.id === to.params.role))
        return navigateTo("/login");
      const session = useCookie<string | null>("xray-demo-role");
      if (!session.value) return navigateTo(`/login?role=${to.params.role}`);
    },
  ],
});
const route = useRoute();
const role = computed(() => route.params.role as Perspective);
const profile = computed(() => perspectives.find((p) => p.id === role.value)!);
const section = computed(() =>
  ["marketplace", "signals"].includes(String(route.query.section))
    ? String(route.query.section)
    : "overview",
);
useHead(() => ({ title: `${profile.value.name} · X-Ray` }));
const query = ref("");
const selectedId = ref("iberica");
const selected = computed(
  () => demoCompanies.find((c) => c.id === selectedId.value)!,
);
const filtered = computed(() =>
  demoCompanies.filter((c) =>
    `${c.name} ${c.sector}`
      .toLocaleLowerCase("es")
      .includes(query.value.toLocaleLowerCase("es")),
  ),
);
const offers = useState<DemoOffer[]>("demo-offers", () =>
  initialOffers.map((o) => ({ ...o })),
);
const sent = useState<string[]>("demo-sent", () => []);
const notice = ref("");
const confirmOffer = ref<string | null>(null);
const company = demoCompanies[3]!;
const title = computed(() =>
  section.value === "signals"
    ? "Cada cambio tiene una explicación."
    : section.value === "marketplace"
      ? role.value === "empresa"
        ? "Financiación que encaja contigo."
        : "Conecta capital con oportunidades."
      : {
          embat: "Una radiografía de tu ecosistema.",
          empresa: "Tu próximo paso, con perspectiva.",
          banco: "Más contexto. Mejores decisiones.",
        }[role.value],
);
const subtitle = computed(
  () =>
    ({
      embat:
        "Supervisa empresas, señales y actividad de financiación desde un mismo lugar.",
      empresa: "Distribuciones Ibérica · Distribución alimentaria",
      banco: "Banco Meridiano · Oportunidades de financiación de circulante",
    })[role.value],
);
const stats = computed(() =>
  role.value === "empresa"
    ? [
        {
          label: "Tu score actual",
          value: "68 / 100",
          detail: "↓ 14 puntos en 3 meses",
          tone: "negative",
        },
        {
          label: "Financiación disponible",
          value: euros(offers.value.reduce((n, o) => n + o.amount, 0)),
          detail: `${offers.value.length} ofertas para comparar`,
          tone: "",
        },
        {
          label: "Tipo más bajo ofertado",
          value: "6,9 %",
          detail: "Plazo de 18 meses",
          tone: "",
        },
      ]
    : [
        {
          label:
            role.value === "embat"
              ? "Empresas en el ecosistema"
              : "Empresas disponibles",
          value: "5",
          detail: "Cartera de demostración en EUR",
          tone: "",
        },
        {
          label:
            role.value === "embat"
              ? "Ofertas en el marketplace"
              : "Tus ofertas enviadas",
          value: String(
            role.value === "embat" ? offers.value.length : sent.value.length,
          ),
          detail:
            role.value === "embat"
              ? "Conexiones entre empresa y capital"
              : "Simuladas durante esta sesión",
          tone: "",
        },
        {
          label: "Empresas que requieren atención",
          value: "3",
          detail: "2 a vigilar · 1 no prestar",
          tone: "negative",
        },
      ],
);
function tone(score: number) {
  return score >= 70 ? "positive" : score < 50 ? "negative" : "caution";
}
function trend(delta: number) {
  return `${delta > 0 ? "+" : ""}${delta}`;
}
function points(history: number[]) {
  return history.map((n, i) => `${i * 80},${125 - n}`).join(" ");
}
function sendOffer() {
  if (sent.value.includes(selected.value.id)) return;
  sent.value.push(selected.value.id);
  if (selected.value.id === "iberica")
    offers.value.push({
      id: "new-iberica",
      bank: "Banco Meridiano",
      amount: selected.value.amount,
      rate: selected.value.rate,
      months: 12,
      note: "Nueva oferta enviada desde la perspectiva Banco.",
      accepted: false,
    });
  notice.value = `Oferta simulada para ${selected.value.name}. ${selected.value.id === "iberica" ? "Ya puedes verla en la perspectiva Empresa." : "Registrada en tus ofertas de esta sesión."}`;
}
function acceptOffer(id: string) {
  const offer = offers.value.find((o) => o.id === id);
  if (offer) offer.accepted = true;
  confirmOffer.value = null;
  notice.value =
    "Oferta aceptada en la demo. No se ha contratado financiación.";
}
watch(
  () => route.fullPath,
  () => {
    notice.value = "";
    confirmOffer.value = null;
    query.value = "";
  },
);
</script>
<template>
  <div class="workspace-layout">
    <a class="skip-link" href="#main-content">Saltar al contenido</a
    ><WorkspaceSidebar :role="role" :section="section" />
    <div class="workspace-body">
      <header class="workspace-topbar">
        <span
          >{{ profile.name }} <span class="breadcrumb-slash">/</span>
          {{
            section === "overview"
              ? "Resumen"
              : section === "signals"
                ? "Señales"
                : "Marketplace"
          }}</span
        ><span class="demo-chip">Demo interactiva</span>
      </header>
      <main id="main-content" class="dashboard-main" tabindex="-1">
        <div class="dashboard-heading">
          <div>
            <h1>{{ title }}</h1>
            <p>{{ subtitle }}</p>
          </div>
          <span class="dashboard-date">Septiembre 2026</span>
        </div>
        <div v-if="notice" class="feedback-banner" role="status">
          <Check :size="18" />{{ notice }}
        </div>
        <section
          v-if="section !== 'signals'"
          class="dashboard-stats"
          aria-label="Resumen"
        >
          <article v-for="stat in stats" :key="stat.label">
            <p>{{ stat.label }}</p>
            <strong>{{ stat.value }}</strong
            ><small :class="stat.tone">{{ stat.detail }}</small>
          </article>
        </section>
        <template v-if="role === 'empresa'">
          <section v-if="section !== 'marketplace'" class="company-insight">
            <div class="dashboard-card trajectory-card">
              <div class="card-heading">
                <div>
                  <h2>Tu salud financiera</h2>
                  <p>La trayectoria importa tanto como el nivel.</p>
                </div>
                <span class="status-label caution">Vigilar</span>
              </div>
              <div class="trajectory-score">
                68<small>/ 100</small
                ><span class="negative">↓ 14 puntos / 3 meses</span>
              </div>
              <svg
                viewBox="0 0 400 120"
                role="img"
                aria-label="Score mensual: abril 85, mayo 84, junio 82, julio 78, agosto 73, septiembre 68"
              >
                <line
                  x1="0"
                  y1="80"
                  x2="400"
                  y2="80"
                  stroke="#e5e5ec"
                  stroke-dasharray="4 5"
                />
                <polyline
                  :points="points(company.history)"
                  fill="none"
                  stroke="#6c47ff"
                  stroke-width="3"
                />
                <circle
                  v-for="(value, index) in company.history"
                  :key="index"
                  :cx="index * 80"
                  :cy="125 - value"
                  r="4"
                  fill="#6c47ff"
                />
              </svg>
              <div class="chart-months">
                <span
                  v-for="month in ['Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep']"
                  :key="month"
                  >{{ month }}</span
                >
              </div>
            </div>
            <div class="dashboard-card explanation-card">
              <span class="signal-icon"><Activity :size="22" /></span>
              <h2>¿Qué ha cambiado?</h2>
              <p>{{ company.why }}</p>
              <div class="signal-callout">
                <strong>Deterioro persistente</strong
                ><span
                  >La caída se mantiene desde julio. Revisa el coste de la deuda
                  y prioriza los pagos pendientes.</span
                >
              </div>
              <small
                >Lectura ilustrativa del caso demo, no una evaluación
                real.</small
              >
            </div>
          </section>
          <section v-if="section !== 'signals'" aria-labelledby="offers-title">
            <div class="card-heading offers-heading">
              <div>
                <h2 id="offers-title">Ofertas para tu empresa</h2>
                <p>Compara importe, tipo anual y plazo antes de elegir.</p>
              </div>
              <span class="count-label">{{ offers.length }} ofertas</span>
            </div>
            <div class="warning-banner">
              Tu score bajó 14 puntos. Los tipos de este ejemplo son más altos
              que hace un trimestre. Una misma ficha permite comparar las
              propuestas.
            </div>
            <article v-for="offer in offers" :key="offer.id" class="offer-row">
              <span class="bank-avatar"><Building2 :size="23" /></span>
              <div class="offer-bank">
                <h3>{{ offer.bank }}</h3>
                <p>{{ offer.note }}</p>
              </div>
              <dl>
                <div>
                  <dt>Importe</dt>
                  <dd>{{ euros(offer.amount) }}</dd>
                </div>
                <div>
                  <dt>Tipo anual</dt>
                  <dd>{{ offer.rate }} %</dd>
                </div>
                <div>
                  <dt>Plazo</dt>
                  <dd>{{ offer.months }} meses</dd>
                </div>
              </dl>
              <button
                class="button"
                :class="
                  offer.accepted ? 'button--secondary' : 'button--primary'
                "
                :disabled="offer.accepted"
                @click="confirmOffer = offer.id"
              >
                {{ offer.accepted ? "Aceptada" : "Aceptar" }}
              </button>
              <div v-if="confirmOffer === offer.id" class="offer-confirm">
                <span>¿Aceptar esta oferta en la demo?</span
                ><button
                  class="button button--primary"
                  @click="acceptOffer(offer.id)"
                >
                  Confirmar aceptación</button
                ><button
                  class="button button--secondary"
                  @click="confirmOffer = null"
                >
                  Cancelar
                </button>
              </div>
            </article>
          </section>
        </template>
        <template v-else-if="section !== 'signals'">
          <section
            v-if="role === 'embat' && section === 'overview'"
            class="ecosystem-strip"
          >
            <div>
              <span class="signal-icon"><Activity :size="22" /></span>
              <h2>El cambio, a ambos lados del riesgo.</h2>
              <p>
                Talleres Vidal se recupera. Distribuciones Ibérica pierde
                margen. Prioriza el seguimiento con el contexto de cada empresa.
              </p>
            </div>
            <NuxtLink
              class="button button--secondary"
              to="/dashboard/embat?section=signals"
              >Revisar señales <ArrowRight :size="16"
            /></NuxtLink>
          </section>
          <div class="marketplace-layout">
            <section class="dashboard-card company-list">
              <div class="card-heading">
                <div>
                  <h2>
                    {{
                      role === "embat"
                        ? "Empresas del ecosistema"
                        : "Encuentra tu próxima oportunidad"
                    }}
                  </h2>
                  <p>Score, trayectoria y criterio para decidir.</p>
                </div>
              </div>
              <label class="company-search"
                ><Search :size="17" /><input
                  v-model="query"
                  type="search"
                  placeholder="Buscar empresa o sector"
                  aria-label="Buscar empresa o sector"
              /></label>
              <div class="market-table-wrap">
                <table class="market-table">
                  <thead>
                    <tr>
                      <th>Empresa</th>
                      <th>Score</th>
                      <th>3 meses</th>
                      <th>Tipo sugerido</th>
                      <th><span class="sr-only">Ficha</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="c in filtered"
                      :key="c.id"
                      :class="{ selected: selectedId === c.id }"
                    >
                      <td>
                        <strong>{{ c.name }}</strong
                        ><small>{{ c.sector }}</small>
                      </td>
                      <td>
                        <span class="table-score" :class="tone(c.score)">{{
                          c.score
                        }}</span>
                      </td>
                      <td>
                        <span
                          class="trend-cell"
                          :class="c.delta > 0 ? 'positive' : 'negative'"
                          ><ArrowUpRight
                            v-if="c.delta > 0"
                            :size="15"
                          /><ArrowDownRight v-else :size="15" />{{
                            trend(c.delta)
                          }}</span
                        >
                      </td>
                      <td>{{ c.rate }} %</td>
                      <td>
                        <button
                          class="row-open"
                          :aria-label="`Ver ficha de ${c.name}`"
                          :aria-pressed="selectedId === c.id"
                          @click="selectedId = c.id"
                        >
                          <ArrowRight :size="18" />
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p v-if="!filtered.length" class="empty-search">
                No hay empresas para «{{ query }}». Prueba otro nombre o sector.
              </p>
              <div class="table-footer">
                {{ filtered.length }} empresas
                <span>Datos de tesorería ilustrativos</span>
              </div>
            </section>
            <aside
              class="dashboard-card company-detail"
              aria-label="Ficha de empresa"
              aria-live="polite"
            >
              <div>
                <span class="detail-eyebrow">Ficha de empresa</span>
                <h2>{{ selected.name }}</h2>
                <p>{{ selected.sector }}</p>
              </div>
              <div class="detail-rating">
                <strong :class="tone(selected.score)">{{
                  selected.score
                }}</strong>
                <div>
                  <span class="status-label" :class="tone(selected.score)">{{
                    selected.action
                  }}</span
                  ><small :class="selected.delta > 0 ? 'positive' : 'negative'"
                    >{{ trend(selected.delta) }} puntos en 3 meses</small
                  >
                </div>
              </div>
              <h3>{{ selected.signal }}</h3>
              <p class="detail-why">{{ selected.why }}</p>
              <svg
                class="detail-chart"
                viewBox="0 0 400 110"
                role="img"
                :aria-label="`Score de abril a septiembre: ${selected.history.join(', ')}`"
              >
                <polyline
                  :points="points(selected.history)"
                  fill="none"
                  stroke="#6c47ff"
                  stroke-width="3"
                />
              </svg>
              <div class="evidence-months">
                <span>Abril</span><span>Septiembre</span>
              </div>
              <dl class="detail-terms">
                <div>
                  <dt>Importe orientativo</dt>
                  <dd>{{ euros(selected.amount) }}</dd>
                </div>
                <div>
                  <dt>Tipo anual ilustrativo</dt>
                  <dd>{{ selected.rate }} %</dd>
                </div>
                <div>
                  <dt>Plazo</dt>
                  <dd>12 meses</dd>
                </div>
              </dl>
              <button
                v-if="role === 'banco'"
                class="button button--primary"
                :disabled="
                  sent.includes(selected.id) || selected.action === 'No prestar'
                "
                @click="sendOffer"
              >
                {{
                  sent.includes(selected.id)
                    ? "Oferta enviada en demo"
                    : selected.action === "No prestar"
                      ? "Financiación no recomendada"
                      : "Enviar oferta demo"
                }}<ArrowRight :size="16" /></button
              ><NuxtLink
                v-else
                class="button button--secondary"
                to="/dashboard/embat?section=signals"
                >Ver señales del ecosistema</NuxtLink
              >
            </aside>
          </div>
        </template>
        <section
          v-if="section === 'signals' && role !== 'empresa'"
          class="dashboard-card signals-list"
        >
          <div class="card-heading">
            <div>
              <h2>Monitor de cambios</h2>
              <p>
                Mejoras y deterioros, con su explicación y la acción sugerida.
              </p>
            </div>
            <span class="count-label">Abril — septiembre</span>
          </div>
          <article v-for="c in demoCompanies" :key="c.id" class="signal-row">
            <span
              class="signal-icon"
              :class="c.delta > 0 ? 'positive' : 'negative'"
              ><ArrowUpRight v-if="c.delta > 0" /><ArrowDownRight v-else
            /></span>
            <div>
              <h3>
                {{ c.name }}
                <span :class="c.delta > 0 ? 'positive' : 'negative'"
                  >{{ trend(c.delta) }} pts / 3 meses</span
                >
              </h3>
              <strong>{{ c.signal }}</strong>
              <p>{{ c.why }}</p>
            </div>
            <span class="status-label" :class="tone(c.score)">{{
              c.action
            }}</span>
          </article>
        </section>
        <footer class="dashboard-footer">
          Datos y condiciones ficticios para explorar el producto. Las acciones
          solo afectan a esta demo.
        </footer>
      </main>
    </div>
  </div>
</template>
