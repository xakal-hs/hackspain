export default defineNuxtConfig({
  compatibilityDate: '2026-09-01',
  devtools: { enabled: true },
  modules: ['@pinia/nuxt'],
  css: ['~/assets/css/main.css'],
  app: {
    head: {
      htmlAttrs: { lang: 'es' },
      meta: [
        { name: 'theme-color', content: '#f7f7f8' },
        {
          name: 'description',
          content: 'X-Ray convierte la tesorería en una decisión de crédito explicable y anticipada.',
        },
      ],
      link: [
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Geist:wght@400;450;500;600;700&family=Geist+Mono:wght@400;500;600&display=swap',
        },
      ],
    },
  },
  runtimeConfig: {
    xrayApiBase: process.env.XRAY_API_BASE || '',
    public: {
      appName: 'X-Ray',
    },
  },
  nitro: {
    routeRules: {
      '/api/**': { cors: true },
    },
  },
  typescript: {
    typeCheck: true,
    strict: true,
  },
})
