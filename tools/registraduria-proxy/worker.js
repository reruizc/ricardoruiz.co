// registraduria-proxy — proxea (con CORS) los JSON de resultados de la
// Registraduría: https://resultados.registraduria.gov.co/json/ACT/{CORP}/{DEP}.json
//
// Rutas:  /senado · /camara · /consultas · /presidente
//   + /{cod}        por depto      (ej /presidente/05)
//   + /{cod5}       por municipio  (ej /presidente/05001  → dep 05 + mun 001)
//   + /{dep}/{mun}  por municipio  (ej /presidente/05/001)
// CORP:   SE        CA         CN           PR
//
// CLAVE (verificado 2026-05-31): el WAF de la Registraduría exige un
// User-Agent de navegador COMPLETO. Un "Mozilla/5.0" mínimo o curl => 403.
// Con el UA de Chrome completo => 200. Por eso el fetch upstream lo manda.
//
// Deploy:  cd tools/registraduria-proxy && npx wrangler deploy

const CORP = { senado: 'SE', camara: 'CA', consultas: 'CN', presidente: 'PR' };
const BASE = 'https://resultados.registraduria.gov.co/json/ACT';
const UA   = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': '*',
};

export default {
  async fetch(req) {
    if (req.method === 'OPTIONS') return new Response(null, { headers: CORS });

    const { pathname } = new URL(req.url);
    const seg  = pathname.replace(/^\/+|\/+$/g, '').split('/'); // ['presidente','05'] o ['presidente','05','001']
    const corp = CORP[seg[0]];

    if (!corp) {
      const rutas = [];
      for (const k of Object.keys(CORP)) rutas.push('/' + k, `/${k}/00`);
      return json({ error: 'Ruta no encontrada', path: pathname, rutas }, 404);
    }

    // Ámbito: nacional '00' · depto (2 díg) · municipio (5 díg = dep+mun).
    // Acepta /presidente/05, /presidente/05001 y /presidente/05/001.
    const a = seg[1] || '', b = seg[2] || '';
    let amb = '00';
    if (/^\d{5}$/.test(a))                                amb = a;                                // municipio 5 díg
    else if (/^\d{1,2}$/.test(a) && /^\d{1,3}$/.test(b)) amb = a.padStart(2, '0') + b.padStart(3, '0'); // dep + mun
    else if (/^\d{1,2}$/.test(a))                        amb = a.padStart(2, '0');               // depto

    const url = `${BASE}/${corp}/${amb}.json`;
    let up;
    try {
      up = await fetch(url, {
        headers: {
          'User-Agent': UA,
          'Accept': 'application/json, text/plain, */*',
          'Accept-Language': 'es-CO,es;q=0.9',
          'Referer': 'https://resultados.registraduria.gov.co/',
        },
        cf: { cacheTtl: 15, cacheEverything: true },
      });
    } catch (e) {
      return json({ error: 'No se pudo contactar a la Registraduría', message: String(e), url }, 502);
    }
    if (!up.ok) {
      return json({ error: 'La Registraduría devolvió un error', status: up.status, message: up.statusText, url }, up.status);
    }

    const body = await up.text();
    return new Response(body, {
      headers: { ...CORS, 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'public, max-age=15' },
    });
  },
};

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { ...CORS, 'Content-Type': 'application/json; charset=utf-8' },
  });
}
