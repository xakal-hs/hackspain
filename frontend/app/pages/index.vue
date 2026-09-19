<script setup lang="ts">
import {
  companies,
  companyById,
  dipVsFall,
  leadCompany,
  leadMonths,
  perspectives,
  shapeLabel,
  signed,
  value as valueRows,
} from '~/data/demo'

useHead({
  title: 'X-Ray · La caja avisa antes que las cuentas',
})

const sections = [
  { id: 'deteccion', label: 'La detección' },
  { id: 'lectura', label: 'Tres lecturas' },
  { id: 'simetria', label: 'Mejora y caída' },
  { id: 'bache', label: 'Bache o caída' },
  { id: 'producto', label: 'Quién paga' },
]

const active = useSectionIndex(sections.map((section) => section.id))

/* Six companies read at one shared scale: a recovery and a collapse have to be
 * comparable by eye, not by caption. */
const strip = computed(() =>
  ['atlas-frio', 'solis', 'vidal', 'nortex', 'iberica', 'sureste']
    .map((id) => companyById(id)!)
    .map((company) => ({
      ...company,
      window: company.history.slice(12),
    })),
)

const stripDomain: [number, number] = [34, 96]

const readings = computed(() => {
  const company = leadCompany
  return [
    {
      perspective: perspectives.find((p) => p.id === 'banco')!,
      figure: `${company.runway.now.toLocaleString('es-ES')}`,
      unit: 'meses',
      tone: 'plain',
      reading: 'lo que dura el dinero que le queda en la cuenta',
      before: `eran ${company.runway.prev.toLocaleString('es-ES')} meses en marzo`,
    },
    {
      perspective: perspectives.find((p) => p.id === 'empresa')!,
      figure: '+1,8',
      unit: 'puntos',
      tone: 'plain',
      reading: 'lo que ha subido el interés de su deuda',
      before: 'y paga a proveedores 23 días más tarde',
    },
    {
      perspective: perspectives.find((p) => p.id === 'embat')!,
      figure: `${leadMonths(company)}`,
      unit: 'meses',
      tone: 'ahead',
      reading: 'de ventaja sobre el momento en que cayó el nivel',
      before: 'aviso enviado a las dos partes en mayo',
    },
  ]
})
</script>

<template>
  <div class="lp">
    <a class="skip-link" href="#main-content">Saltar al contenido</a>

    <aside class="lp__rail">
      <div class="lp__rail-head">
        <NuxtLink to="/" class="lp__brand">
          <BrandMark />
          <span>X-Ray<small>de Embat</small></span>
        </NuxtLink>
        <ThemeSwitch />
      </div>

      <nav class="lp__index" aria-label="Secciones de la página">
        <a
          v-for="section in sections"
          :key="section.id"
          :href="`#${section.id}`"
          :class="{ 'is-here': active === section.id }"
          :aria-current="active === section.id ? 'true' : undefined"
          >{{ section.label }}</a
        >
      </nav>

      <div class="lp__rail-foot">
        <NuxtLink class="btn btn--live" to="/login">Abrir la demo</NuxtLink>
        <p>Sin contraseña. Datos ficticios.</p>
      </div>
    </aside>

    <main id="main-content" class="lp__main" tabindex="-1">
      <section id="deteccion" class="lp__hero">
        <h1 class="lp__head">
          <span>Los problemas se ven en la caja</span>
          <span>antes de verse en las cuentas.</span>
        </h1>
        <p class="lp__lead">
          X-Ray lee mes a mes el dinero que una empresa tiene en la cuenta, lo
          que tarda en cobrar y lo que retrasa en pagar. Con eso dice si
          prestarle, vigilarla o no prestarle, por qué, y desde cuándo.
        </p>

        <div class="panel lp__evidence">
          <header class="panel__bar">
            <span class="chip chip--amber">En seguimiento</span>
            <div class="panel__who">
              <strong>{{ leadCompany.name }}</strong>
              <span>{{ leadCompany.sector }} · {{ leadCompany.group }}</span>
            </div>
            <div class="panel__reading">
              <b>{{ leadCompany.score }}</b>
              <span
                >{{ signed(leadCompany.delta3) }} en tres meses<small
                  >de 100</small
                ></span
              >
            </div>
            <DecisionTag :decision="leadCompany.decision" />
          </header>

          <DetectionChart :company="leadCompany" />

          <p class="lp__evidence-read">
            Cuatro meses antes de que el score cayera por debajo de 70, el
            dinero de la cuenta ya cubría la mitad de tiempo y el interés de la
            deuda había subido 1,8 puntos. Eso es lo que X-Ray marcó en mayo.
          </p>
        </div>
      </section>

      <section id="lectura" class="lp__section">
        <div class="lp__section-head">
          <h2>La misma caja, tres lecturas.</h2>
          <p>
            Ibérica es una sola empresa con un solo score. Lo que cambia es la
            cifra que cada uno necesita mirar primero, porque no arriesgan lo
            mismo.
          </p>
        </div>

        <ul class="reads">
          <li v-for="read in readings" :key="read.perspective.id">
            <span class="reads__who">
              <i aria-hidden="true">{{ read.perspective.initials }}</i>
              <b>{{ read.perspective.name }}</b>
              <em>{{ read.perspective.job }}</em>
            </span>
            <span class="reads__figure" :data-tone="read.tone"
              >{{ read.figure }}<small>{{ read.unit }}</small></span
            >
            <span class="reads__reading">
              <b>{{ read.reading }}</b>
              <em>{{ read.before }}</em>
            </span>
          </li>
        </ul>
      </section>

      <section id="simetria" class="lp__section">
        <div class="lp__section-head">
          <h2>Una mejora pesa igual que un deterioro.</h2>
          <p>
            Las seis empresas, a la misma escala y en la misma ventana de doce
            meses. Vidal sube veinte puntos y Sureste pierde veintitrés: el
            mismo modelo detecta las dos cosas.
          </p>
        </div>

        <ul class="multiples">
          <li v-for="company in strip" :key="company.id">
            <span class="multiples__name">{{ company.name }}</span>
            <Sparkline
              :values="company.window"
              :domain="stripDomain"
              :tone="company.delta3 > 2 ? 'mint' : company.delta3 < -5 ? 'crimson' : 'muted'"
              :label="`${company.name}, score de los últimos doce meses: ${company.window.join(', ')}`"
            />
            <span class="multiples__foot">
              <b>{{ company.score }}</b>
              <em :data-dir="company.delta3 > 0 ? 'up' : company.delta3 < 0 ? 'down' : 'flat'"
                >{{ signed(company.delta3) }} / 3 m</em
              >
              <span>{{ shapeLabel[company.shape] }}</span>
            </span>
          </li>
        </ul>
      </section>

      <section id="bache" class="lp__section">
        <div class="lp__section-head">
          <h2>Un bache no es una caída.</h2>
          <p>
            Las dos perdieron cuatro puntos en un mes y venían de dos meses
            idénticos. La línea de puntos es la otra empresa, para ver dónde se
            separan.
          </p>
        </div>

        <div class="verdicts">
          <article>
            <header>
              <span class="chip chip--mint">{{ dipVsFall.bump.verdict }}</span>
              <h3>{{ dipVsFall.bump.name }}</h3>
              <p>{{ dipVsFall.bump.month }}</p>
            </header>
            <DipFallChart
              :values="dipVsFall.bump.relative"
              :ghost="dipVsFall.fall.relative"
              :offsets="dipVsFall.offsets"
              tone="mint"
            />
            <dl>
              <div>
                <dt>Qué pasó</dt>
                <dd>{{ dipVsFall.bump.cause }}</dd>
              </div>
              <div>
                <dt>Por qué no cambia nada</dt>
                <dd>{{ dipVsFall.bump.evidence }}</dd>
              </div>
            </dl>
            <footer>
              <DecisionTag :decision="dipVsFall.bump.decision" />
              <span>{{ dipVsFall.bump.outcome }}</span>
            </footer>
          </article>

          <article>
            <header>
              <span class="chip chip--crimson">{{
                dipVsFall.fall.verdict
              }}</span>
              <h3>{{ dipVsFall.fall.name }}</h3>
              <p>{{ dipVsFall.fall.month }}</p>
            </header>
            <DipFallChart
              :values="dipVsFall.fall.relative"
              :ghost="dipVsFall.bump.relative"
              :offsets="dipVsFall.offsets"
              tone="crimson"
            />
            <dl>
              <div>
                <dt>Qué pasó</dt>
                <dd>{{ dipVsFall.fall.cause }}</dd>
              </div>
              <div>
                <dt>Por qué sí cambia todo</dt>
                <dd>{{ dipVsFall.fall.evidence }}</dd>
              </div>
            </dl>
            <footer>
              <DecisionTag :decision="dipVsFall.fall.decision" />
              <span>{{ dipVsFall.fall.outcome }}</span>
            </footer>
          </article>
        </div>
      </section>

      <section id="producto" class="lp__section lp__close">
        <div class="lp__section-head">
          <h2>Quién paga por esto.</h2>
          <p>
            Quien pierde dinero cuando se entera tarde. Un banco con una línea
            ya abierta descubre el deterioro en las cuentas del trimestre
            siguiente; aquí lo ve en la caja del mes. Embat vende ese adelanto a
            las dos partes a la vez, porque ya tiene los bancos y el ERP
            conectados.
          </p>
        </div>

        <dl class="worth">
          <div v-for="row in valueRows" :key="row.label">
            <dt>
              <b>{{ row.label }}</b>
              <span>{{ row.note }}</span>
            </dt>
            <dd>{{ row.figure }}</dd>
          </div>
        </dl>

        <div class="lp__cta">
          <NuxtLink class="btn btn--live btn--lg" to="/login"
            >Abrir la demo</NuxtLink
          >
          <p>
            {{ companies.length }} empresas, 24 meses de tesorería y las tres
            vistas del producto.
          </p>
        </div>
      </section>

      <footer class="lp__foot">
        <span>X-Ray · inteligencia de tesorería de Embat</span>
        <span>HackSpain 2026 · datos ficticios, ninguna operación real</span>
      </footer>
    </main>
  </div>
</template>
