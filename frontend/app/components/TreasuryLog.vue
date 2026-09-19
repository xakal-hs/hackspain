<script setup lang="ts">
export interface LogEntry {
  date: string
  title: string
  desc: string
  badge: string
  open?: boolean
}

defineProps<{ title: string; entries: LogEntry[] }>()
</script>

<template>
  <section class="tz-card">
    <header class="tz-card__bar">
      <h2>{{ title }}</h2>
    </header>
    <ol class="tz-log">
      <li v-for="entry in entries" :key="entry.date + entry.title">
        <time>{{ entry.date }}</time>
        <div>
          <b>{{ entry.title }}</b>
          <span>{{ entry.desc }}</span>
        </div>
        <em class="tz-badge" :class="{ 'is-open': entry.open }">{{ entry.badge }}</em>
      </li>
    </ol>
  </section>
</template>
