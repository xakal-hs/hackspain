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
          href: 'https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=Chivo+Mono:wght@300;400&family=Space+Grotesk:wght@500;600;700&family=Work+Sans:wght@400;500;600&display=swap',
        },
      ],
    },
  },
  runtimeConfig: {
    supabaseSecretKey: process.env.SUPABASE_SECRET_KEY || '',
    agentModel: process.env.AGENT_MODEL || '',
    agentBaseUrl: process.env.AGENT_BASE_URL || '',
    agentApiKey: process.env.AGENT_API_KEY || '',
    supabaseJwksUrl: process.env.SUPABASE_JWKS_URL || '',
    public: {
      supabaseUrl: process.env.SUPABASE_URL || '',
      supabasePublishableKey: process.env.SUPABASE_PUBLISHABLE_KEY || '',
      appName: 'X-Ray',
    },
  },
  nitro: {
    routeRules: {
      '/api/**': { cors: true },
      // Routes from the earlier structure now live as sections of the cockpit.
      '/cartera': { redirect: '/dashboard/embat?section=cartera' },
      '/monitor': { redirect: '/dashboard/embat?section=senales' },
      '/escenarios': { redirect: '/dashboard/embat' },
      '/empresas/**': { redirect: '/dashboard/embat?section=cartera' },
    },
  },
  typescript: {
    typeCheck: true,
    strict: true,
  },
})
