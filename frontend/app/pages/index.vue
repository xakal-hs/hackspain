<script setup lang="ts">
import {
  ArrowRight,
  Activity,
  Building2,
  Landmark,
  ScanLine,
} from "@lucide/vue";
useHead({ title: "X-Ray · La salud financiera, a la vista" });
</script>
<template>
  <div class="landing">
    <header class="landing-nav">
      <NuxtLink to="/" class="brand"><BrandMark /> X-Ray</NuxtLink
      ><span class="landing-by">Inteligencia de tesorería de Embat</span
      ><NuxtLink class="button button--primary" to="/login"
        >Entrar a la demo <ArrowRight :size="16"
      /></NuxtLink>
    </header>
    <main id="main-content" class="landing-main">
      <section class="landing-hero">
        <div>
          <span class="landing-tag"
            ><ScanLine :size="16" /> Una nueva mirada al riesgo</span
          >
          <h1>La salud financiera.<br />Con perspectiva.</h1>
          <p>
            Lo que una foto no cuenta, la tesorería lo revela. Entiende cómo
            cambia una empresa y conecta cada señal con una mejor decisión.
          </p>
          <NuxtLink class="button button--primary" to="/login"
            >Explorar X-Ray <ArrowRight :size="18" /></NuxtLink
          ><small
            >Acceso demo sin contraseña. Tres perspectivas, un mismo
            ecosistema.</small
          >
        </div>
        <div class="landing-evidence">
          <div class="evidence-top">
            <span><BrandMark /> Radiografía de empresa</span
            ><span class="live-label">Demo</span>
          </div>
          <p>Distribuciones Ibérica</p>
          <div class="evidence-score">
            68 <span>/ 100 <small>↓ 14 puntos en 3 meses</small></span>
          </div>
          <svg
            viewBox="0 0 440 120"
            role="img"
            aria-label="Score de 85 a 68 entre abril y septiembre"
          >
            <path
              d="M0 20 L88 25 L176 36 L264 55 L352 81 L440 106"
              fill="none"
              stroke="#bdaaff"
              stroke-width="3"
            />
            <path
              d="M0 20 L88 25 L176 36 L264 55 L352 81 L440 106 L440 120 L0 120Z"
              fill="#6c47ff"
              opacity=".12"
            />
          </svg>
          <div class="evidence-months">
            <span>Abril</span><span>Septiembre 2026</span>
          </div>
          <div class="evidence-reason">
            <Activity :size="20" /><span
              ><strong>Una señal para actuar a tiempo</strong>Sube el coste de
              la deuda. Se retrasa el pago a proveedores.</span
            >
          </div>
        </div>
      </section>
      <section class="landing-perspectives">
        <h2>La misma información. Tu decisión.</h2>
        <div class="perspective-grid">
          <NuxtLink to="/login?role=embat"
            ><ScanLine />
            <h3>Para Embat</h3>
            <p>
              Una visión del ecosistema: actividad, señales y oportunidades de
              financiación.
            </p>
            <span>Ver el conjunto <ArrowRight :size="16" /></span></NuxtLink
          ><NuxtLink to="/login?role=empresa"
            ><Building2 />
            <h3>Para tu empresa</h3>
            <p>
              Entiende qué cambia en tu salud financiera y compara ofertas en un
              solo lugar.
            </p>
            <span
              >Encontrar financiación <ArrowRight :size="16" /></span></NuxtLink
          ><NuxtLink to="/login?role=banco"
            ><Landmark />
            <h3>Para tu banco</h3>
            <p>
              Evalúa empresas con contexto, trayectoria y motivos claros para
              cada decisión.
            </p>
            <span>Explorar oportunidades <ArrowRight :size="16" /></span
          ></NuxtLink>
        </div>
      </section>
    </main>
    <footer class="landing-footer">
      X-Ray by Embat
      <span>HackSpain 2026 · Demostración con datos ficticios</span>
    </footer>
  </div>
</template>
