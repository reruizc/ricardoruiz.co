/* lectura.mjs — la lectura de la tarjeta 03 del CRM, corrida en Node.
   ------------------------------------------------------------------
   El briefing tiene que decir lo MISMO que la tarjeta 03: qué movió la agenda
   en estos días, a qué arquetipos le habla y en qué localidades conviene
   estar. Para no mantener dos cálculos, esto carga los mismos scripts del
   navegador (candidato-360-arq-lectura.js, -saliencia.js, -ciclo.js…) en un
   contexto `vm` con lo mínimo de `window`, `document` y `fetch`.

   Entrada (stdin, JSON): { vinculo, items: [{titulo, medio, url, fecha}],
     captura?, visitas?: {code: {fecha, nombre}}, dias? }
   Salida (stdout, JSON): { territorio, prensa, redes, arquetipos, oficio,
     unidades, ciudad, motivo? } — la forma que lee correo_ciclo.py.

     echo '{"vinculo":{…},"items":[…]}' | node tools/candidato-360/briefing/lectura.mjs

   Sin arquetipos para la ciudad (hoy: Bogotá, Medellín y Cartagena) devuelve
   prensa y redes y `motivo`; el correo sale igual, sin el bloque de zonas.   */

import vm from 'node:vm';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const SCRIPTS = ['platform-config.js', 'data-client.js', 'cand-index.js', 'partidos-bloques.js', 'candidato-360-electorado.js',
  'candidato-360-arq-lectura.js', 'candidato-360-panel.js', 'candidato-360-saliencia.js', 'candidato-360-arquetipos.js', 'candidato-360-ciclo.js'];
/* Carpeta de S3 por prefijo del código de candidatura. Se prueban en orden
   hasta que una responde: así no hay que bajar los 30 índices del buscador. */
const DIRS = { CONC: 'concejo', JAL: 'jal', ASAM: 'asamblea', ALC: 'alcaldia', GOB: 'gobernacion', CON: 'congreso', PRES: 'pres', CONSU: 'consu' };

const memoria = () => { const m = new Map(); return { getItem: k => m.has(k) ? m.get(k) : null, setItem: (k, v) => m.set(k, String(v)), removeItem: k => m.delete(k), clear: () => m.clear() }; };

async function contexto() {
  const ctx = { console: { ...console, log: (...x) => console.error(...x), warn: (...x) => console.error(...x) }, setTimeout, clearTimeout, setInterval, clearInterval,
    URL, URLSearchParams, TextDecoder, TextEncoder, Intl, structuredClone, Response, Headers, AbortController, performance };
  ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx;
  ctx.location = { search: '', hash: '', href: 'https://ricardoruiz.co/candidato-360.html', origin: 'https://ricardoruiz.co', hostname: 'ricardoruiz.co', reload() {} };
  ctx.navigator = { userAgent: 'candidato-360-briefing (node)', language: 'es-CO' };
  ctx.localStorage = memoria(); ctx.sessionStorage = memoria();
  ctx.addEventListener = () => {}; ctx.removeEventListener = () => {}; ctx.matchMedia = () => ({ matches: false, addEventListener() {} });
  const correr = async src => { const f = path.join(RAIZ, src.split('?')[0]); vm.runInContext(await readFile(f, 'utf8'), ctx, { filename: f }); };
  ctx.document = {
    head: { appendChild: el => { correr(el.src).then(() => el.onload?.(), e => el.onerror?.(e)); return el; } },
    body: { appendChild: el => el }, createElement: () => ({ style: {}, classList: { add() {}, remove() {} }, setAttribute() {} }),
    getElementById: () => null, querySelector: () => null, querySelectorAll: () => [], addEventListener: () => {}, readyState: 'complete'
  };
  /* Lo relativo es un archivo del repo; lo absoluto, la red. */
  ctx.fetch = async (url, o) => {
    const u = String(url);
    if (/^https?:/i.test(u)) return fetch(u, o);
    try { return new Response(await readFile(path.join(RAIZ, decodeURIComponent(u.split('?')[0]))), { status: 200 }); }
    catch { return new Response('', { status: 404 }); }
  };
  vm.createContext(ctx);
  for (const s of SCRIPTS) await correr(s);
  return ctx;
}

async function mesasDe(ctx, slugs) {
  const S3 = ctx.CandRegistry.S3;
  for (const slug of slugs || []) {
    const m = String(slug).match(/^([A-Z]+?)(\d{4})-/); if (!m) continue;
    const base = DIRS[m[1]]; const dirs = base ? [`${base}-${m[2]}`] : [];
    dirs.push('endoso');
    for (const d of dirs) {
      const r = await fetch(`${S3}/${d}/${slug}.json`).catch(() => null);
      if (r?.ok) { const j = await r.json(); return j.mesas || []; }
    }
  }
  return [];
}

export async function lectura({ vinculo, items = [], captura = null, visitas = {}, dias = 3 }, ctx = null) {
  ctx = ctx || await contexto();
  const P = ctx.C360Panel, S = ctx.C360Saliencia, A = ctx.C360ArqLectura, C = ctx.C360Ciclo;
  P.SESION.vinculo = vinculo; P.SESION.token = 'briefing';
  const t = P.territorioDe(vinculo);
  const personas = P.terminosPersona();
  const filas0 = items.map(i => ({ titulo: i.titulo || '', medio: i.medio || '', url: i.url || '', fecha: i.fecha || '', suyo: P.mencionaPersona(i.titulo || '', personas) }));
  const a = filas0.length ? S.analizar(filas0, { locales: P.terminosLocales(t), persona: personas, ventana: dias, anclas: [t.entidad, t.cuerpo] }) : null;
  const R = captura?.redes ? C._leerRedes(captura, S) : null;
  const w = {};
  (a?.temas || []).forEach(x => { w[x.id] = (w[x.id] || 0) + x.pct * (R?.total ? 0.5 : 1); });
  if (R?.total) Object.entries(R.porTema).forEach(([id, n]) => { w[id] = (w[id] || 0) + (n / R.total) * (a?.N ? 0.5 : 1); });
  const out = {
    territorio: t.etiqueta,
    prensa: { N: a?.N || 0, temas: (a?.temas || []).slice(0, 5).map(x => ({ id: x.id, corto: x.corto, pct: x.pct, n: x.n })), filas: filas0 },
    redes: R ? { total: R.total, ideas: R.ideas, porTema: R.porTema, postura: R.postura, porRed: R.porRed, fecha: R.fecha } : null,
    arquetipos: [], unidades: [], oficio: null, ciudad: null
  };
  const mesas = vinculo.tipo === 'historial' ? await mesasDe(ctx, vinculo.candidato?.slugs) : [];
  const mun = await A.municipioDeCampana(vinculo.campana).catch(() => '');
  const ciudad = A.ciudadDe(mun, mesas);
  if (!ciudad) return { ...out, motivo: 'sin arquetipos para esta ciudad' };
  const corp = vinculo.campana?.corp;
  const [L, Lp] = await Promise.all([A.leer(ciudad, [], { corp }), mesas.length ? A.leer(ciudad, mesas, { corp }) : Promise.resolve(null)]);
  const rel = C._relevancias(L, Lp, w);
  const pr = C._prioridades(L, rel, visitas || {});
  const nt = id => { const x = S.TEMAS.find(y => y.id === id); return x ? (x.corto || x.nombre.toLowerCase()) : id; };
  const top = rel.filter(r => r.act != null);
  const f0 = top[0] ? L.ficha(top[0].id) : null;
  return {
    ...out, ciudad,
    arquetipos: rel.slice(0, 8).map(r => ({ id: r.id, nombre: r.nombre, color: r.color, act: r.act, tema: r.tema, temaNombre: r.tema ? nt(r.tema) : null, afin: r.afin, rel: r.rel })),
    oficio: f0?.oficio || null,
    unidades: pr.unidades.slice(0, 8).map(u => ({ nombre: u.nombre, share: u.share, visitados: u.visitados,
      barrios: u.barrios.slice(0, 8).map(b => ({ code: b.code, nombre: b.nombre, top: b.top, indice: b.indice, visitado: b.castigo < 1 })) }))
  };
}

/* CLI: un pedido por stdin, o una lista ({ pedidos: [...] }) con el mismo contexto. */
if (import.meta.url === `file://${process.argv[1]}`) {
  let txt = ''; for await (const t of process.stdin) txt += t;
  const pedido = JSON.parse(txt || '{}');
  const ctx = await contexto();
  const res = pedido.pedidos
    ? await Promise.all(pedido.pedidos.map(p => lectura(p, ctx).catch(e => ({ error: e.message }))))
    : await lectura(pedido, ctx).catch(e => ({ error: e.message }));
  process.stdout.write(JSON.stringify(res));
}
