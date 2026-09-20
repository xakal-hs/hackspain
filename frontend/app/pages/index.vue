<script setup lang="ts">
import { Activity, ArrowUpRight, ChartNoAxesCombined, Pause, Play, Wallet, Waves } from '@lucide/vue'
import { companyById, leadCompany, leadMonths, shapeLabel, signed } from '~/data/demo'

useSeoMeta({
  title: 'X-Ray · Ve lo que viene. Decide con ventaja.',
  description: 'Entiende la salud financiera de tu empresa, anticipa tensiones de caja y descubre oportunidades en tu tesorería con X-Ray de Embat.',
})

const motionPaused = ref(false)

/* Six companies read at one shared scale: a recovery and a collapse have to be
 * comparable by eye, not by caption. */
const strip = computed(() =>
  ['atlas-frio', 'solis', 'vidal', 'nortex', 'iberica', 'sureste']
    .map((id) => companyById(id)!)
    .map((company) => ({ ...company, window: company.history.slice(12) })),
)
const stripDomain: [number, number] = [34, 96]

const benefits = [
  {
    icon: Activity,
    name: 'Entiende dónde estás.',
    description: 'Un score que explica qué ha cambiado, desde cuándo y si es un bache o una caída de fondo.',
    product: 'X-Ray Score',
  },
  {
    icon: Wallet,
    name: 'Llega antes a la falta de caja.',
    description: 'Pon los próximos cobros y pagos en perspectiva. Decide con margen, no cuando la cuenta llegue a cero.',
    product: 'Colchón Dinámico',
  },
  {
    icon: ChartNoAxesCombined,
    name: 'Mira lo que no estás viendo.',
    description: 'Dinero parado y exposición a otras monedas. Haz visibles los costes que hoy pasan desapercibidos.',
    product: 'Divisa Inteligente',
  },
]
</script>

<template>
  <div class="landing" :class="{ 'is-paused': motionPaused }">
    <a class="skip-link" href="#main-content">Saltar al contenido</a>
    <div class="landing__atmosphere" aria-hidden="true">
      <div class="landing__aurora landing__aurora--blue" />
      <div class="landing__aurora landing__aurora--violet" />
      <div class="landing__aurora landing__aurora--teal" />
    </div>

    <header class="landing__header landing__width">
      <NuxtLink to="/" class="landing__brand" aria-label="X-Ray de Embat, inicio">
        <BrandMark />
        <span>X-Ray <small>de Embat</small></span>
      </NuxtLink>
      <nav class="landing__nav" aria-label="Navegación principal">
        <a class="landing__product-link" href="#producto">El producto</a>
        <NuxtLink class="landing__login" to="/login">Entrar <ArrowUpRight :size="16" aria-hidden="true" /></NuxtLink>
      </nav>
    </header>

    <main id="main-content" tabindex="-1">
      <section class="landing__hero landing__width" aria-labelledby="hero-title">
        <p class="landing__intro"><BrandMark /> Tu tesorería, con perspectiva.</p>
        <h1 id="hero-title">Ve lo que viene.<br />Decide con ventaja.</h1>
        <p class="landing__lead">
          Tu caja cuenta más de lo que parece. X-Ray traduce tus datos de tesorería
          en señales claras para anticipar riesgos y descubrir oportunidades.
        </p>
        <NuxtLink class="landing__cta" to="/login">Explorar la demo <ArrowUpRight :size="19" aria-hidden="true" /></NuxtLink>
        <p class="landing__reassurance">Sin registro. Sin operaciones reales.</p>
      </section>

      <section id="producto" class="landing__product landing__width" aria-labelledby="product-title">
        <div class="landing__preview-label">
          <h2 id="product-title">Menos ruido. Más perspectiva.</h2>
          <span>Vista ilustrativa del producto</span>
        </div>
        <div class="landing__preview">
          <header class="landing__preview-bar">
            <span class="landing__preview-brand"><BrandMark /> X-Ray Score</span>
            <span class="landing__demo-label">Datos de demo</span>
          </header>
          <div class="landing__company">
            <div>
              <p>{{ leadCompany.sector }}</p>
              <h3>{{ leadCompany.name }}</h3>
            </div>
            <div class="landing__score">
              <strong>{{ leadCompany.score }}<small>/100</small></strong>
              <span>{{ signed(leadCompany.delta3) }} puntos en 3 meses</span>
            </div>
          </div>
          <div class="landing__chart"><DetectionChart :company="leadCompany" /></div>
          <div class="landing__insight">
            <span class="landing__insight-icon"><Waves :size="22" aria-hidden="true" /></span>
            <p><strong>La señal aparece antes que la caída.</strong> En este ejemplo, X-Ray detecta el deterioro {{ leadMonths(leadCompany) }} meses antes de que el score baje de 70.</p>
          </div>
          <ul class="landing__companies" aria-label="Ejemplos de evolución del score, a la misma escala">
            <li v-for="company in strip" :key="company.id">
              <span>{{ company.name }}</span>
              <Sparkline
                :values="company.window"
                :domain="stripDomain"
                :tone="company.delta3 > 2 ? 'mint' : company.delta3 < -5 ? 'crimson' : 'muted'"
                :label="`${company.name}, últimos doce meses: ${company.window.join(', ')}. ${shapeLabel[company.shape]}.`"
              />
              <div><b>{{ company.score }}</b><span>{{ signed(company.delta3) }} / 3 m</span></div>
            </li>
          </ul>
        </div>
      </section>

      <section class="landing__benefits landing__width" aria-label="Qué puedes hacer con X-Ray">
        <article v-for="benefit in benefits" :key="benefit.product">
          <component :is="benefit.icon" :size="24" :stroke-width="1.5" aria-hidden="true" />
          <h2>{{ benefit.name }}</h2>
          <p>{{ benefit.description }}</p>
          <span>{{ benefit.product }}</span>
        </article>
      </section>

      <section class="landing__closing landing__width" aria-labelledby="closing-title">
        <div>
          <h2 id="closing-title">Los datos ya están.<br />La ventaja está en verlos antes.</h2>
          <p>Para quien cuida la caja. Para quien decide financiar.</p>
        </div>
        <NuxtLink class="landing__cta" to="/login">Explorar la demo <ArrowUpRight :size="19" aria-hidden="true" /></NuxtLink>
      </section>
    </main>

    <footer class="landing__footer landing__width">
      <span>X-Ray de Embat <span class="landing__footer-divider">/</span> HackSpain 2026</span>
      <button class="landing__motion" type="button" :aria-pressed="motionPaused" @click="motionPaused = !motionPaused">
        <component :is="motionPaused ? Play : Pause" :size="14" aria-hidden="true" />
        {{ motionPaused ? 'Reanudar animación' : 'Pausar animación' }}
      </button>
    </footer>
  </div>
</template>

<style scoped>
.landing {
  --canvas: var(--ink-canvas);
  --panel: var(--ink-panel);
  --text: var(--ink-text);
  --text-muted: var(--ink-muted);
  --text-dim: var(--ink-dim);
  --line: var(--ink-line);
  --line-strong: var(--ink-line-strong);
  --live: var(--ink-live);
  --live-solid: var(--ink-live-solid);
  --on-live: #fff;
  --focus-ring: var(--ink-live-ink);
  --grid-line: var(--ink-line);
  --ahead: #c5b6ff;
  --ahead-ink: #cfc2ff;
  --mint: var(--ink-mint);
  --crimson: var(--ink-crimson);
  --landing-violet: #8648c9;
  --landing-teal: #167d9a;
  position: relative;
  isolation: isolate;
  overflow: hidden;
  background: var(--canvas);
  color: var(--text);
  color-scheme: dark;
}

.landing__width { width: min(1120px, calc(100% - 64px)); margin-inline: auto; }
.landing__atmosphere { position: absolute; inset: 0 0 auto; height: 1050px; overflow: hidden; z-index: -1; pointer-events: none; }
.landing__atmosphere::after { content: ''; position: absolute; inset: 0; background: linear-gradient(180deg, transparent 40%, var(--canvas) 100%); }
.landing__aurora { position: absolute; border-radius: 50%; filter: blur(65px); will-change: transform; animation: aurora-drift 24s ease-in-out infinite alternate; }
.landing__aurora--blue { width: 850px; height: 460px; top: -280px; left: calc(50% - 260px); background: var(--live-solid); opacity: .29; transform: rotate(-24deg); }
.landing__aurora--violet { width: 700px; height: 580px; top: -130px; left: calc(50% - 1000px); background: var(--landing-violet); opacity: .18; animation-delay: -8s; }
.landing__aurora--teal { width: 760px; height: 260px; top: 130px; left: calc(50% + 40px); background: var(--landing-teal); opacity: .19; transform: rotate(38deg); animation-delay: -16s; }
.is-paused .landing__aurora { animation-play-state: paused; }
@keyframes aurora-drift { to { transform: translate3d(65px, 90px, 0) rotate(12deg) scale(1.15); } }

.landing__header { display: flex; align-items: center; justify-content: space-between; min-height: 100px; gap: 24px; }
.landing__brand { display: inline-flex; align-items: center; gap: 10px; min-height: 44px; }
.landing__brand :deep(.brand-mark) { width: 30px; height: 30px; color: var(--text); }
.landing__brand > span { font-size: 24px; font-weight: 550; letter-spacing: -.04em; }
.landing__brand small { margin-left: 8px; font-size: 13px; color: var(--text-muted); font-weight: 400; letter-spacing: 0; }
.landing__nav { display: flex; gap: 30px; align-items: center; font-size: 14px; }
.landing__nav a { min-height: 44px; display: inline-flex; align-items: center; gap: 18px; transition: color .2s, background .2s, border-color .2s; }
.landing__product-link { color: var(--text-muted); }
.landing__product-link:hover { color: var(--text); }
.landing__login { padding: 0 18px; border: 1px solid var(--line-strong); border-radius: 8px; }
.landing__login:hover { background: var(--ink-raised); border-color: var(--text-muted); }

.landing__hero { text-align: center; padding-block: 72px 86px; }
.landing__intro { display: inline-flex; align-items: center; gap: 9px; padding: 7px 13px; background: var(--ink-neutral-wash); border: 1px solid var(--line); border-radius: 7px; font-size: 14px; }
.landing__intro :deep(.brand-mark) { width: 18px; height: 18px; color: var(--ahead); }
.landing h1 { margin-top: 28px; font-size: clamp(3rem, 6.8vw, 5.75rem); line-height: 1.06; letter-spacing: -.06em; font-weight: 450; }
.landing__lead { max-width: 640px; margin: 28px auto 30px; font-size: 18px; line-height: 1.7; color: #bfc4de; }
.landing__cta { display: inline-flex; justify-content: center; align-items: center; gap: 18px; min-height: 52px; padding: 0 24px; border: 1px solid rgba(255, 255, 255, .16); border-radius: 8px; background: linear-gradient(110deg, var(--live-solid), var(--landing-violet)); color: var(--on-live); font-size: 15px; font-weight: 500; transition: filter .2s, border-color .2s; }
.landing__cta:hover { filter: brightness(1.12); border-color: rgba(255, 255, 255, .4); }
.landing__cta:active { filter: brightness(.92); }
.landing__reassurance { margin-top: 14px; color: var(--text-muted); font-size: 12px; }

.landing__product { scroll-margin-top: 28px; }
.landing__preview-label { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
.landing__preview-label h2 { font-size: 16px; letter-spacing: -.01em; }
.landing__preview-label > span { color: var(--text-muted); font-size: 12px; }
.landing__preview { background: var(--panel); border: 1px solid var(--line-strong); border-radius: 16px; overflow: hidden; box-shadow: var(--ink-sheen); }
.landing__preview-bar { display: flex; justify-content: space-between; align-items: center; padding: 17px 28px; border-bottom: 1px solid var(--line); }
.landing__preview-brand { display: flex; align-items: center; gap: 9px; font-size: 14px; font-weight: 500; }
.landing__demo-label { color: var(--text-muted); font-size: 12px; border: 1px solid var(--line-strong); padding: 3px 9px; border-radius: 5px; }
.landing__company { display: flex; justify-content: space-between; align-items: center; gap: 24px; padding: 28px 32px 8px; }
.landing__company p { color: var(--text-muted); font-size: 12px; margin-bottom: 5px; }
.landing__company h3 { font-size: 22px; }
.landing__score { display: flex; align-items: center; gap: 16px; }
.landing__score strong { font-family: var(--font-num); font-size: 36px; font-weight: 450; letter-spacing: -.06em; }
.landing__score small { color: var(--text-muted); font-family: var(--font-ui); font-size: 14px; letter-spacing: 0; margin-left: 4px; }
.landing__score > span { max-width: 110px; color: var(--text-muted); font-size: 12px; }
.landing__chart { padding: 0 12px; }
.landing__chart :deep(.dtx__plot) { height: 240px; }
.landing__chart :deep(*) { animation: none; }
.landing__chart :deep(.dtx__note--early) { width: max-content; }
.landing__insight { display: flex; align-items: center; gap: 14px; margin: 20px 28px 24px; padding: 16px 20px; border: 1px solid var(--line); border-radius: 8px; background: var(--ink-neutral-wash); }
.landing__insight-icon { color: var(--ahead); flex: none; }
.landing__insight p { color: var(--text-muted); font-size: 13px; line-height: 1.6; }
.landing__insight strong { color: var(--text); font-weight: 500; }
.landing__companies { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); border-top: 1px solid var(--line); }
.landing__companies li { padding: 16px 20px; min-width: 0; }
.landing__companies li + li { border-left: 1px solid var(--line); }
.landing__companies li > span:not(.spark) { display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 12px; color: var(--text-muted); }
.landing__companies :deep(.spark) { width: 100%; height: 35px; margin-block: 10px; }
.landing__companies li > div { display: flex; align-items: center; justify-content: space-between; gap: 4px; }
.landing__companies b { font-size: 16px; font-weight: 500; }
.landing__companies li > div span { color: var(--text-muted); font-size: 12px; }

.landing__benefits { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 64px; padding-block: 80px; }
.landing__benefits article > svg { margin-bottom: 24px; color: var(--ink-live-ink); }
.landing__benefits h2 { font-size: 21px; line-height: 1.3; letter-spacing: -.03em; }
.landing__benefits p { margin-top: 14px; color: var(--text-muted); font-size: 15px; line-height: 1.7; }
.landing__benefits article > span { display: block; margin-top: 20px; font-size: 12px; color: var(--ink-live-ink); }
.landing__closing { display: flex; justify-content: space-between; align-items: center; gap: 32px; padding-block: 48px 64px; border-top: 1px solid var(--line); }
.landing__closing h2 { font-size: clamp(1.7rem, 3vw, 2.4rem); line-height: 1.2; letter-spacing: -.04em; }
.landing__closing p { margin-top: 16px; color: var(--text-muted); font-size: 14px; }
.landing__closing .landing__cta { flex: none; }
.landing__footer { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding-block: 20px; border-top: 1px solid var(--line); color: var(--text-muted); font-size: 12px; }
.landing__footer-divider { margin-inline: 12px; color: var(--text-muted); }
.landing__motion { min-height: 44px; display: flex; align-items: center; gap: 8px; padding-inline: 10px; border-radius: 6px; transition: background .2s, color .2s; }
.landing__motion:hover { background: var(--ink-neutral-wash); color: var(--text); }

@media (max-width: 900px) {
  .landing__hero { padding-block: 64px 72px; }
  .landing__benefits { gap: 28px; }
  .landing__companies { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .landing__companies li:nth-child(4) { border-left: 0; }
  .landing__companies li:nth-child(n + 4) { border-top: 1px solid var(--line); }
}

@media (max-width: 600px) {
  .landing__width { width: calc(100% - 40px); }
  .landing__header { min-height: 80px; }
  .landing__brand small, .landing__product-link { display: none !important; }
  .landing__hero { padding-block: 50px 64px; }
  .landing h1 { font-size: clamp(2.5rem, 10.8vw, 4rem); }
  .landing__lead { font-size: 16px; line-height: 1.65; margin-block: 24px 28px; }
  .landing__intro { font-size: 12px; }
  .landing__preview-label { align-items: flex-start; flex-direction: column; gap: 4px; }
  .landing__preview-bar { padding: 14px 16px; }
  .landing__company { padding: 20px 16px 8px; gap: 12px; align-items: flex-start; }
  .landing__company h3 { font-size: 18px; }
  .landing__score { flex-direction: column; align-items: flex-end; gap: 0; flex: none; }
  .landing__score strong { font-size: 30px; }
  .landing__score > span { max-width: 90px; text-align: right; }
  .landing__chart { padding: 0; }
  .landing__chart :deep(.dtx) { padding-inline: 12px; }
  .landing__chart :deep(.dtx__plot) { height: 210px; }
  .landing__chart :deep(.dtx__axis > span:nth-child(3)) { display: none; }
  .landing__insight { margin: 20px 12px 16px; padding: 12px; align-items: flex-start; gap: 10px; }
  .landing__companies li { padding: 12px; }
  .landing__companies li > div { align-items: flex-start; flex-direction: column; }
  .landing__benefits { grid-template-columns: 1fr; gap: 36px; padding-block: 56px; }
  .landing__benefits article > svg { margin-bottom: 14px; }
  .landing__benefits p { margin-top: 10px; }
  .landing__benefits article > span { margin-top: 12px; }
  .landing__closing { flex-direction: column; align-items: flex-start; padding-block: 36px 48px; gap: 24px; }
  .landing__footer { flex-direction: column; align-items: flex-start; gap: 4px; }
  .landing__motion { padding-inline: 0; }
  .landing__aurora { filter: blur(45px); }
}

@media (prefers-reduced-motion: reduce) {
  .landing__aurora { animation: none; will-change: auto; }
  .landing__motion { display: none; }
  .landing a, .landing button { transition: none; }
}
</style>
