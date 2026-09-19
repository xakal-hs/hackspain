export default defineNuxtConfig({
  compatibilityDate: '2026-09-01',
  devtools: { enabled: true },
  modules: ['@pinia/nuxt'],
  // Order matters: tokens and shared primitives first, cockpit layer second.
  css: ['~/assets/css/main.css', '~/assets/css/workspace.css'],
  app: {
    head: {
      htmlAttrs: { lang: 'es', 'data-theme': 'dark' },
      meta: [
        {
          name: 'description',
          content:
            'X-Ray lee la tesorería mes a mes y dice si prestar, vigilar o no prestar, con el motivo y con cuántos meses de antelación.',
        },
      ],
      link: [
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@400;500;600;700&family=Chivo+Mono:wght@300;400&display=swap',
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
      // Routes from the earlier structure now live as sections of the cockpit.
      '/cartera': { redirect: '/dashboard/banco?section=cartera' },
      '/monitor': { redirect: '/dashboard/banco?section=senales' },
      '/escenarios': { redirect: '/dashboard/banco' },
      '/empresas/**': { redirect: '/dashboard/banco?section=cartera' },
    },
  },
  typescript: {
    typeCheck: true,
    strict: true,
  },
})
