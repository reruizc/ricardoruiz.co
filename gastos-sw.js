// Service worker de la app de Gastos.
//
// Regla única y deliberada: se cachea SOLO el cascarón (HTML, fuentes, íconos).
// Los datos NUNCA — viven en otro origen (el worker rr-auth) y mostrar un saldo
// viejo como si fuera el de hoy es peor que no mostrar nada.
// ⚠️ SUBIR ESTE NÚMERO en cada cambio del cascarón. Una app añadida a la
// pantalla de inicio se queda con la versión vieja hasta que el caché cambie de
// nombre — a Ricardo le pasó: siguió viendo la pregunta del sueldo que ya no
// existía, y le respondió con su ingreso a un campo que pedía su saldo.
const CACHE = 'gastos-v2';
const SHELL = [
  '/gastos.html',
  '/gastos-manifest.json',
  '/imagenes/gastos-icon-192.png',
  '/imagenes/gastos-icon-512.png',
  '/fonts/helveticaneue.woff2',
  '/fonts/helveticaneue-light.woff2',
  '/fonts/helveticaneue-medium.woff2',
  '/fonts/helveticaneue-bold.woff2',
];

self.addEventListener('install', e => {
  // addAll falla entero si un archivo falta; se piden sueltos para que un
  // 404 en una fuente no deje la app sin cascarón.
  e.waitUntil(caches.open(CACHE).then(c =>
    Promise.all(SHELL.map(u => c.add(u).catch(() => {})))
  ).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;   // la API se deja pasar directo

  // El HTML va por red primero: si hay señal, siempre la versión nueva.
  if (req.mode === 'navigate' || url.pathname.endsWith('.html')) {
    e.respondWith(
      fetch(req)
        .then(r => { const c = r.clone(); caches.open(CACHE).then(k => k.put(req, c)); return r; })
        .catch(() => caches.match(req).then(r => r || caches.match('/gastos.html')))
    );
    return;
  }

  // Estáticos: del caché si están, si no de la red.
  e.respondWith(caches.match(req).then(r => r || fetch(req).then(res => {
    if (res.ok) { const c = res.clone(); caches.open(CACHE).then(k => k.put(req, c)); }
    return res;
  }).catch(() => r)));
});
