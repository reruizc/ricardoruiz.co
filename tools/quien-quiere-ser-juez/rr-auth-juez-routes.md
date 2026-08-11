# Rutas `/juez/*` del worker rr-auth · ¿Quién quiere ser juez?

**✅ DESPLEGADAS en producción (ago-2026)** en `/Users/ricardoruiz/rr-auth/src/index.js`
(buscar "QUIÉN QUIERE SER JUEZ"). Este doc queda como referencia del contrato.
Verificado en vivo: ranking vacío OK, honeypot OK, validaciones de consent/cel OK.

Diferencia clave vs el sketch original: rate limit propio `_juezRateLimit` (40/h por IP)
en vez de reusar `_pronRateLimit` (8/h) — el frontend guarda al final de cada partida
y una sesión de estudio son 10-20 partidas.

## Storage KV (`RR_STORE`)

```
juez:reg:<correo>        registro + mejores puntajes del jugador (JSON)
```

Una sola llave por jugador: el registro (nombre, apellido, correo, cel,
universidad, grado, cargo, consent, ts) + `best` = `{civil, penal, administrativo}`.
Reenvíos actualizan `best` con `max()` por sala y conservan `createdAt`.

## Endpoints

### `POST /juez/save` — sin auth
Body: `{nombre, apellido, correo, cel, universidad, grado, cargo, consent, best:{sala:pts}, ts}`

Validación:
- `consent === true` obligatorio (Ley 1581 — sin autorización no se guarda).
- correo con regex simple; cel `^3\d{9}$`; nombre/apellido/universidad no vacíos, ≤120 chars.
- `best`: solo llaves en `{civil, penal, administrativo}`, valores enteros 0..1000.
- Merge: `best[sala] = Math.max(prev, nuevo)`; conservar `createdAt` del primer envío.

### `GET /juez/ranking?tab=global|civil|penal|administrativo|uni` — sin auth, público
Lista hasta 25 filas `{nombre, universidad, pts}`:
- `global`: max de `best` por jugador, desc.
- por sala: `best[sala]` desc.
- `uni`: agrupa por universidad normalizada (sin tildes, MAYÚS), muestra
  `{nombre: universidad, universidad: 'N jugadores', pts: promedio de los mejores}`.
- **PII**: solo `nombre + inicial del apellido` y universidad. Nunca correo ni celular.
- Cache: recomputar máx. cada 5 min (guardar en `juez:ranking-cache` con TTL 300).

### `GET /juez/admin/all` — adminGuard (sesión de reruizc@gmail.com)
Dump completo para el negocio (leads): lista paginada de `juez:reg:*`.
Es el equivalente de `/pron/admin/all`. La base NUNCA se expone sin adminGuard
(lección de la ruta `/pron/me` retirada por exponer PII).

## Sketch del código

```js
// ── ¿Quién quiere ser juez? ──
if (url.pathname === '/juez/save' && request.method === 'POST') {
  const b = await request.json().catch(() => null);
  if (!b || b.consent !== true) return json({ error: 'consent_required' }, 400);
  const correo = String(b.correo || '').trim().toLowerCase();
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(correo)) return json({ error: 'bad_email' }, 400);
  if (!/^3\d{9}$/.test(String(b.cel || ''))) return json({ error: 'bad_cel' }, 400);
  const clean = s => String(s || '').slice(0, 120).trim();
  if (!clean(b.nombre) || !clean(b.apellido) || !clean(b.universidad)) return json({ error: 'missing' }, 400);
  const SALAS = ['civil', 'penal', 'administrativo'];
  const key = 'juez:reg:' + correo;
  const prev = await env.RR_STORE.get(key, 'json');
  const best = {};
  for (const s of SALAS) {
    const n = Math.max(prev?.best?.[s] || 0, Math.min(1000, Math.max(0, parseInt(b.best?.[s] || 0, 10) || 0)));
    if (n) best[s] = n;
  }
  await env.RR_STORE.put(key, JSON.stringify({
    nombre: clean(b.nombre), apellido: clean(b.apellido), correo,
    cel: String(b.cel), universidad: clean(b.universidad),
    grado: clean(b.grado), cargo: clean(b.cargo), consent: true, best,
    createdAt: prev?.createdAt || Date.now(), updatedAt: Date.now()
  }));
  return json({ ok: true });
}

if (url.pathname === '/juez/ranking' && request.method === 'GET') {
  const tab = url.searchParams.get('tab') || 'global';
  const cacheKey = 'juez:ranking-cache:' + tab;
  const cached = await env.RR_STORE.get(cacheKey, 'json');
  if (cached) return json({ rows: cached });
  const rows = [];
  let cursor;
  do {
    const l = await env.RR_STORE.list({ prefix: 'juez:reg:', cursor, limit: 1000 });
    for (const k of l.keys) {
      const r = await env.RR_STORE.get(k.name, 'json');
      if (!r) continue;
      const pts = tab === 'global' || tab === 'uni'
        ? Math.max(0, ...Object.values(r.best || {}), 0)
        : (r.best?.[tab] || 0);
      if (pts) rows.push({ nombre: r.nombre + ' ' + (r.apellido || '').charAt(0) + '.', universidad: r.universidad, pts });
    }
    cursor = l.list_complete ? null : l.cursor;
  } while (cursor);
  let out;
  if (tab === 'uni') {
    const g = {};
    for (const r of rows) {
      const u = r.universidad.normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase();
      (g[u] = g[u] || { nombre: r.universidad, tot: 0, n: 0 }).tot += r.pts; g[u].n++;
    }
    out = Object.values(g).map(x => ({ nombre: x.nombre, universidad: x.n + ' jugador' + (x.n > 1 ? 'es' : ''), pts: Math.round(x.tot / x.n) }));
  } else out = rows;
  out.sort((a, b2) => b2.pts - a.pts);
  out = out.slice(0, 25);
  await env.RR_STORE.put(cacheKey, JSON.stringify(out), { expirationTtl: 300 });
  return json({ rows: out });
}
```

`/juez/admin/all`: clonar `/pron/admin/all` cambiando el prefijo a `juez:reg:`.

## CORS
El error visto en localhost (`Access-Control-Allow-Origin: https://ricardoruiz.co`)
es el comportamiento correcto en producción. Para probar local, agregar
temporalmente el origen o probar desde el dominio.

## Deploy
```bash
cd /Users/ricardoruiz/rr-auth && npx wrangler deploy
```

## Panel admin (siguiente paso)
Clonar `admin-pronosticos.html` → `admin-juez.html`: KPIs (registros, partidas,
por universidad, por cargo objetivo) + tabla + export CSV de leads. Card en
`PRIVATE_TOOLS` de dashboard.html.
