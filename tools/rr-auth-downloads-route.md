# Rutas `/dl/*` para el worker `rr-auth`

Mueve el contador mensual de descargas (módulo Oportunidad, etc.) del
localStorage del cliente al worker. Sin esto, un usuario Pro puede
"regenerar" descargas vaciando `localStorage` y subir efectivamente a
ilimitadas.

## Requisitos

- Un namespace **KV** llamado `RR_DL` bindeado al worker (nombre del
  binding en `wrangler.toml` o en la pestaña Settings → Variables del
  worker en el dashboard Cloudflare).
- La función `verifyJwt(token, env)` que el worker ya usa para
  `/auth/me` (debe devolver `{ id, email, plan }` o similar; el
  contador necesita un `user.id` estable).

### Crear el KV namespace

```bash
# Vía wrangler CLI (recomendado):
wrangler kv:namespace create RR_DL
# → copia el id en wrangler.toml:
# [[kv_namespaces]]
# binding = "RR_DL"
# id = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

O por dashboard: Workers & Pages → KV → Create namespace `RR_DL` →
bindearlo al worker `rr-auth` con binding name `RR_DL`.

## Snippet a pegar en el worker

Va dentro del `fetch(request, env, ctx)`, **antes** del 404 final.

```js
// ─── /dl ─────────────────────────────────────────────────────────────
// Contador mensual de descargas por usuario. Persiste en KV con TTL de
// 45 días (suficiente para cubrir el mes en curso + holgura).
const DL_QUOTA = { free:0, pro:3, premium:10, full:9999 };

function _dlMonthKey(userId) {
  const d = new Date();
  const ym = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
  return `dl:${userId}:${ym}`;
}

function _dlCorsHeaders(extra = {}) {
  return {
    'Content-Type':                  'application/json; charset=utf-8',
    'Cache-Control':                 'no-store',
    'Access-Control-Allow-Origin':   '*',
    'Access-Control-Allow-Methods':  'GET,POST,OPTIONS',
    'Access-Control-Allow-Headers':  'content-type, authorization',
    ...extra,
  };
}

if (url.pathname === '/dl/status' || url.pathname === '/dl/consume') {
  // Preflight CORS
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: _dlCorsHeaders() });
  }
  // Verifica token (usa la función verifyJwt que ya tiene el worker
  // para /auth/me). Devuelve { id, email, plan, ... }.
  const auth = request.headers.get('Authorization') || '';
  const tok  = auth.startsWith('Bearer ') ? auth.slice(7) : null;
  let user = null;
  try { if (tok) user = await verifyJwt(tok, env); } catch(_) {}
  if (!user || !user.id) {
    return new Response(JSON.stringify({ ok:false, reason:'unauthorized' }),
      { status:401, headers:_dlCorsHeaders() });
  }
  const quota = DL_QUOTA[user.plan] || 0;
  const key   = _dlMonthKey(user.id);
  const used  = parseInt((await env.RR_DL.get(key)) || '0', 10) || 0;

  // GET /dl/status → estado actual sin mutación
  if (url.pathname === '/dl/status' && request.method === 'GET') {
    return new Response(JSON.stringify({ ok:true, used, quota, plan:user.plan }),
      { status:200, headers:_dlCorsHeaders() });
  }
  // POST /dl/consume → incrementa si hay quota disponible
  if (url.pathname === '/dl/consume' && request.method === 'POST') {
    if (quota === 0) {
      return new Response(JSON.stringify({ ok:false, reason:'plan', used, quota }),
        { status:403, headers:_dlCorsHeaders() });
    }
    if (used >= quota) {
      return new Response(JSON.stringify({ ok:false, reason:'quota', used, quota }),
        { status:403, headers:_dlCorsHeaders() });
    }
    const next = used + 1;
    await env.RR_DL.put(key, String(next), { expirationTtl: 60*60*24*45 });
    return new Response(JSON.stringify({ ok:true, used:next, quota }),
      { status:200, headers:_dlCorsHeaders() });
  }
  return new Response('Method Not Allowed', { status:405, headers:_dlCorsHeaders() });
}
```

## Verificación

```bash
# Status (requiere token válido):
curl -H "Authorization: Bearer <jwt>" https://rr-auth.reruizc.workers.dev/dl/status
# → {"ok":true,"used":0,"quota":3,"plan":"pro"}

# Consume:
curl -X POST -H "Authorization: Bearer <jwt>" https://rr-auth.reruizc.workers.dev/dl/consume
# → {"ok":true,"used":1,"quota":3}
```

## Notas

- **TTL 45 días**: KV borra automáticamente la entrada después del mes,
  así no acumula basura indefinidamente.
- **Frontend con fallback**: `oportunidad.html` ya usa estos endpoints
  con fallback a localStorage si el worker responde 404 o 5xx. Mientras
  no despliegues el snippet, el contador sigue siendo local (v1).
- **Quota por plan**: si cambias los números, sincronízalos en el
  frontend (`DL_QUOTA` dentro de `<script>` en `oportunidad.html`).
