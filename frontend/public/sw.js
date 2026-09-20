/* Stub: some browsers still request /sw.js from an old registration.
 * Unregister so Vue Router stops logging unmatched /sw.js navigations. */
self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting())
})
self.addEventListener('activate', (event) => {
  event.waitUntil(
    self.registration.unregister().then(() => self.clients.matchAll()).then((clients) => {
      for (const client of clients) {
        if (client.url && 'navigate' in client) client.navigate(client.url)
      }
    }),
  )
})
