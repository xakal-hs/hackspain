<script setup lang="ts">
import { ArrowDownRight, Banknote, CircleGauge, ShieldCheck } from '@lucide/vue'

const points = '0,27 42,20 84,24 126,17 168,31 210,36 252,55 294,67 336,77 378,85'
</script>

<template>
  <section class="decision-preview" aria-labelledby="decision-title">
    <div class="decision-preview__topline">
      <span class="code-label">&lt;DecisionSignal /&gt;</span>
      <span class="live-indicator"><span /> Datos actualizados</span>
    </div>

    <div class="decision-preview__company">
      <div>
        <p>COMP_0864 · Septiembre 2026</p>
        <h2 id="decision-title">La caja se agota antes de que llegue el cobro.</h2>
      </div>
      <StatusPill band="vigilar" />
    </div>

    <div class="score-trajectory">
      <div class="score-block">
        <span>Salud financiera</span>
        <strong>68</strong>
        <small><ArrowDownRight :size="15" aria-hidden="true" /> −8 puntos desde junio</small>
      </div>
      <div class="chart-wrap">
        <svg viewBox="0 0 378 104" role="img" aria-labelledby="chart-title chart-desc">
          <title id="chart-title">Trayectoria del score</title>
          <desc id="chart-desc">El score cae de forma sostenida desde junio, de 82 a 68 puntos.</desc>
          <line v-for="y in [20, 50, 80]" :key="y" x1="0" :y1="y" x2="378" :y2="y" class="chart-grid" />
          <polyline :points="points" class="chart-line" />
          <circle cx="378" cy="85" r="4" class="chart-point" />
        </svg>
        <div class="chart-labels"><span>Dic 2025</span><span>Sep 2026</span></div>
      </div>
    </div>

    <div class="signal-grid">
      <article>
        <span class="signal-icon"><Banknote :size="17" aria-hidden="true" /></span>
        <div><strong>1,4 meses</strong><span>de dinero en la cuenta</span></div>
        <small class="negative">−0,8</small>
      </article>
      <article>
        <span class="signal-icon"><CircleGauge :size="17" aria-hidden="true" /></span>
        <div><strong>54 días</strong><span>para cobrar</span></div>
        <small class="negative">+11 d</small>
      </article>
      <article>
        <span class="signal-icon"><ShieldCheck :size="17" aria-hidden="true" /></span>
        <div><strong>82%</strong><span>cobertura observada</span></div>
        <small>Alta</small>
      </article>
    </div>
  </section>
</template>
