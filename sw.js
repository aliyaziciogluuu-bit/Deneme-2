// Yazıcıoğlu Çilek Döviz (Döviz Kasası) — çevrimdışı açılabilmesi için uygulama dosyalarını önbelleğe alır.
// Fiyat servisleri (başka alan adları) önbelleğe alınmaz.
const CACHE = 'doviz-kasasi-v1';
const SHELL = [
  './doviz-kasasi.html',
  './manifest.webmanifest',
  './icon.svg',
  './icon-192.png',
  './icon-512.png',
  './apple-touch-icon.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Önce ağ (güncel sürüm gelsin), bağlantı yoksa önbellek.
self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin) return;
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() =>
        caches.match(req, { ignoreSearch: true }).then((hit) =>
          hit || (req.mode === 'navigate' ? caches.match('./doviz-kasasi.html') : Response.error())
        )
      )
  );
});
