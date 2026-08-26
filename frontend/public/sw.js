// Minimal service worker — exists only so the browser considers this app
// installable (a fetch handler is part of that check on several browsers).
// Deliberately does no caching: this app's data changes constantly (live
// attendance, QR rotation), so a cache-first strategy would serve stale
// data. Every request just passes straight through to the network.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});
