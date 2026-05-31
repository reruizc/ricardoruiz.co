# Worker `registraduria-proxy` · agregar ruta `/presidente`

El worker `registraduria-proxy.reruizc.workers.dev` proxea (con CORS) los
JSON de resultados de la Registraduría. Hoy expone `/senado`, `/camara`,
`/consultas` (+ `/{ruta}/{cod}` por departamento) pero **no** `/presidente`.
`presidencial-prec-2026.html` ya está listo para consumir `/presidente`;
solo falta agregar la ruta al worker y redesplegar.

## Patrón confirmado (sondeando el worker en vivo, 2026-05-31)

El worker mapea un nombre amigable → código de corporación y arma:

```
https://resultados.registraduria.gov.co/json/ACT/{CORP}/{DEP}.json
```

| Ruta worker        | CORP | URL real que consume                       |
|--------------------|------|--------------------------------------------|
| `/senado`          | `SE` | `…/json/ACT/SE/00.json`                    |
| `/camara`          | `CA` | `…/json/ACT/CA/00.json`                    |
| `/consultas`       | `CN` | `…/json/ACT/CN/00.json`                    |
| **`/presidente`**  | **`PR`** | **`…/json/ACT/PR/00.json`**            |
| `/senado/{cod}`    | `SE` | `…/json/ACT/SE/{cod}.json`                 |

- `ACT` = resultados en vivo (actualización).
- `{DEP}` = `00` nacional, o código de depto a 2 dígitos (DANE/Registraduría).
- `PR` es el código presidencial **supuesto** (patrón 2022). El host está
  bloqueado hoy (todo da 403 antes del cierre de mesas), así que confírmalo
  al abrir el conteo: en DevTools → Network del sitio oficial, mira la URL
  exacta del JSON (`/json/ACT/XX/00.json`) y usa ese `XX` si no es `PR`.

## Cambio mínimo (ruta segura — sobre tu worker ya desplegado)

En el mapa de corporaciones del worker agrega una línea:

```js
// donde está el diccionario de rutas → corp:
const CORP = {
  senado:    'SE',
  camara:    'CA',
  consultas: 'CN',
  presidente: 'PR',   // ← AGREGAR (confirmar 'PR' con la URL real esta noche)
};
```

Si el worker valida contra una lista blanca de rutas, agrega `presidente`
(y, si aplica, `presidente/{cod}`) a esa lista también. **No toques los
headers/User-Agent existentes**: son los que esquivan el WAF de la
Registraduría y mantienen vivos senado/cámara/consultas.

## Reconstrucción de referencia (solo si perdiste la fuente)

Reproduce fielmente el comportamiento observado. Úsala **únicamente** como
fallback si no encuentras el código real; si la que tienes desplegada usa
un User-Agent específico para no ser bloqueada, consérvalo en vez de esto.

```js
const CORP = { senado:'SE', camara:'CA', consultas:'CN', presidente:'PR' };
const BASE = 'https://resultados.registraduria.gov.co/json/ACT';
const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': '*',
};

export default {
  async fetch(req) {
    const { pathname } = new URL(req.url);
    if (req.method === 'OPTIONS') return new Response(null, { headers: CORS });

    const seg = pathname.replace(/^\/+|\/+$/g, '').split('/'); // ['presidente','01']
    const corp = CORP[seg[0]];
    const dep  = /^\d{1,2}$/.test(seg[1] || '') ? seg[1].padStart(2, '0') : '00';

    if (!corp) {
      const rutas = [];
      for (const k of Object.keys(CORP)) {
        rutas.push('/' + k);
        for (const d of ['00','01','03','16','31']) rutas.push(`/${k}/${d}`); // ejemplo
      }
      return json({ error: 'Ruta no encontrada', path: pathname, rutas }, 404);
    }

    const url = `${BASE}/${corp}/${dep}.json`;
    let up;
    try {
      up = await fetch(url, {
        headers: { 'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json' },
        cf: { cacheTtl: 20, cacheEverything: true },
      });
    } catch (e) {
      return json({ error: 'No se pudo contactar a la Registraduría', message: String(e), url }, 502);
    }
    if (!up.ok) return json({ error: 'La Registraduría devolvió un error', status: up.status, message: up.statusText, url }, up.status);

    const body = await up.text();
    return new Response(body, { headers: { ...CORS, 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' } });
  },
};

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), { status, headers: { ...CORS, 'Content-Type': 'application/json; charset=utf-8' } });
}
```

## Desplegar

El worker no está en este repo (vive en Cloudflare). Desde donde tengas su
fuente:

```bash
npx wrangler deploy
```

> Es el **mismo worker** que sirve a senado/cámara/consultas y a
> `elecciones-2026.html`. Es additivo (solo agrega `/presidente`), pero
> redesplegar afecta a todas esas páginas — verifica que sigan respondiendo
> después del deploy.

## Verificación rápida tras desplegar

```bash
curl -s "https://registraduria-proxy.reruizc.workers.dev/presidente" | head -c 300
# Antes de que abran el conteo: 403 {"error":"La Registraduría devolvió un error", ...}
# Con el conteo abierto: JSON con camaras[].partotabla + totales.act
```

Luego en `presidencial-prec-2026.html`: modo **Worker propio** → «Cargar
ahora». Si sigue 404 «Ruta no encontrada», el deploy no tomó la ruta nueva.

## Alternativa sin tocar el worker (plan B de la noche)

`presidencial-prec-2026.html` tiene el modo **«URL directa Registraduría +
proxy CORS»**: pega la URL exacta capturada en DevTools y elige un proxy
público (corsproxy.io / allorigins.win). Es menos confiable bajo carga que
el worker propio, pero no requiere redesplegar nada.
