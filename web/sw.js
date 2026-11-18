/* Font QA service worker: the page starts without the network after the first visit.

   - Pyodide and HarfBuzz (versioned, immutable CDN URLs): cache first, kept across releases.
   - Our own files (page, worker, core bundle, wheels): network first, so a release shows at once;
     the cache answers when the network is slow or gone. Its name carries the bundle hash.
   Never cached: anything that is not a GET, fonts the visitor drops (they never leave the page),
   and anything outside these two groups. build_site.py copies this file to the site root and fills in VERSION. */

const VERSION = "__VERSION__";
const SITE = "fontqa-site-" + VERSION;
const CDN = "fontqa-cdn-1";
const CDN_PREFIXES = ["https://cdn.jsdelivr.net/pyodide/", "https://cdn.jsdelivr.net/npm/harfbuzzjs@"];
const SLOW_MS = 6000;

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) {
      if (key.startsWith("fontqa-site-") && key !== SITE) await caches.delete(key);
    }
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  if (CDN_PREFIXES.some((p) => req.url.startsWith(p))) event.respondWith(cacheFirst(req));
  else if (req.url.startsWith(self.registration.scope)) event.respondWith(networkFirst(req));
});

async function cacheFirst(req) {
  const cache = await caches.open(CDN);
  const hit = await cache.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok) cache.put(req, res.clone());
  return res;
}

async function networkFirst(req) {
  const cache = await caches.open(SITE);
  try {
    const res = await Promise.race([fetch(req), new Promise((_, no) => setTimeout(() => no(new Error("slow")), SLOW_MS))]);
    if (res.ok) cache.put(req.url.split("?")[0], res.clone());
    return res;
  } catch (err) {
    const hit = await cache.match(req, { ignoreSearch: true });
    if (hit) return hit;
    return fetch(req);  // nothing cached: wait for the network after all
  }
}
