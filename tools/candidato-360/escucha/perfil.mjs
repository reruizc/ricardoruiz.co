/* perfil.mjs — el perfil de escucha SALE DEL VÍNCULO, no de un archivo.
   ------------------------------------------------------------------
   Los dos temas los escribe el candidato en el panel de escucha
   (`escucha.ideas`); el territorio y la corporación vienen de la campaña
   guardada (`campana.corp`, `localidad`, `municipio`, `departamentoNombre`);
   las cuentas, de las redes que validó (`escucha.redes.perfiles`). Nada de eso
   se escribe acá: quien se lanza a la JAL de Tunjuelito escucha Tunjuelito y
   Bogotá; si mañana se lanza al Concejo de Tunja, el mismo vínculo produce
   otro perfil sin tocar código.

   La escala la decide `territorioDe` de candidato-360-panel.js —la MISMA
   regla que usa el panel y que el briefing porta en motor.py—: JAL escucha su
   localidad y su ciudad; Concejo y Alcaldía, el municipio; Asamblea y
   Gobernación, el departamento. Dos reglas serían dos opiniones.

   Lo comparten el modelo de costos (costos.mjs) y el medidor (medir.mjs).

   ⚠️ Los nombres de campo del input VARÍAN por actor y el catálogo de Apify se
   mueve. Cada red trae su actor y su plantilla acá, y se cambian sin tocar la
   lógica.                                                                    */

import { readFileSync } from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');

/* El chasis del panel es un IIFE de navegador: se le da un `window` de mentira
   y se le saca `territorioDe`, `norm` y `oracion`. Igual que hace
   clasificar-locales.mjs con partidos-bloques.js. */
const PANEL = (() => {
  const ctx = { document: { getElementById: () => null, querySelector: () => null }, localStorage: { getItem: () => null }, location: { search: '' }, console };
  ctx.window = ctx; vm.createContext(ctx);
  vm.runInContext(readFileSync(path.join(REPO, 'candidato-360-panel.js'), 'utf8'), ctx);
  return ctx.C360Panel;
})();
export const { territorioDe, norm, oracion } = PANEL;

/* «parque de la 45» → parquedela45 */
export const hashtag = s => String(s).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]/g, '');

/* ── Páginas de Facebook, comprobadas una por una ─────────────────────────
   Facebook no busca por palabra: se siguen páginas. Y una URL inventada NO
   falla: el actor corre, no encuentra nada y cobra igual —cuatro de los seis
   handles que se pusieron de memoria la primera vez estaban mal—. Por eso acá
   solo hay páginas verificadas (sep-2026), por territorio, y donde no hay
   entrada Facebook NO se mide: se dice, en vez de adivinar.
   La clave es el nombre normalizado que produce `norm`.                      */
export const PAGINAS_FACEBOOK = {
  ciudad: {
    BOGOTA: ['https://www.facebook.com/AlcaldiaBogota', 'https://www.facebook.com/ConcejoDeBogota', 'https://www.facebook.com/CanalCapitalOficial', 'https://www.facebook.com/TransMilenio'],
  },
  localidad: {
    TUNJUELITO: ['https://www.facebook.com/AlcaldiaLocalTunjuelito', 'https://www.facebook.com/LocalidadTujuelito' /* el error de tipeo es de ellos */],
  },
};
function paginasDe(t) {
  const ciudad = PAGINAS_FACEBOOK.ciudad[norm(t.munLimpio || t.base)] || [];
  const local = t.corp === 'jal' ? (PAGINAS_FACEBOOK.localidad[norm(t.loc)] || []) : [];
  return [...local, ...ciudad];
}

/* ── El perfil, desde el vínculo ─────────────────────────────────────────── */
export function perfilDeVinculo(vinculo, overrides = {}) {
  const partes = v => String(v).split('|').map(x => x.trim()).filter(Boolean);
  const t = territorioDe(vinculo);
  const e = vinculo?.escucha || {};
  const temas = overrides.temas ? partes(overrides.temas) : (e.ideas || []).map(x => String(x).trim()).filter(Boolean);
  /* Las escalas según la corporación: la localidad y su ciudad para la JAL;
     el municipio para Concejo y Alcaldía; el departamento para las otras. */
  const escalas = t.corp === 'jal' && t.loc ? [oracion(t.loc), t.base] : [t.base];
  const cuentas = Object.fromEntries((e.redes?.perfiles || []).filter(p => p.handle && p.veredicto && !['no_encontrado', 'sin_validar'].includes(p.veredicto)).map(p => [p.red, p.handle]));
  const nombre = vinculo?.candidato?.nombre || vinculo?.nuevo?.nombre || '';
  return {
    candidato: `${t.corpLabel} · ${t.etiqueta}`, nombre, corp: t.corp, temas, escalas, cuentas,
    paginas: overrides.paginas ? partes(overrides.paginas) : paginasDe(t),
    corridasDia: Number(overrides.corridas || 2), dias: Number(overrides.dias || 30),
    territorio: t,
  };
}

/* Cuántos resultados se piden por consulta. ESTA es la palanca del costo:
   Apify cobra por resultado entregado, así que el gasto es
   tope × consultas × corridas, no «lo que traiga». */
export const REDES = {
  x: {
    etiqueta: 'X', modo: 'búsqueda por palabra', tope: 50, propio: 20,
    actor: 'kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest',
    /* El único que busca por palabra de verdad: cada tema por cada escala,
       más el nombre de la candidatura. */
    consultas: p => [...p.temas.flatMap(t => p.escalas.map(e => `"${t}" ${e}`)), ...(p.nombre ? [`"${p.nombre}"`] : [])],
    input: (qs, tope) => ({ searchTerms: qs, maxItems: qs.length * tope, sort: 'Latest' }),
  },
  instagram: {
    etiqueta: 'Instagram', modo: 'hashtag', tope: 20, propio: 12,
    actor: 'apify/instagram-hashtag-scraper',
    consultas: p => [...p.temas.map(hashtag), ...p.escalas.map(hashtag)],
    input: (qs, tope) => ({ hashtags: qs, resultsLimit: tope }),
  },
  tiktok: {
    etiqueta: 'TikTok', modo: 'hashtag', tope: 15, propio: 10,
    actor: 'clockworks/tiktok-scraper',
    consultas: p => [...p.temas.map(hashtag), ...p.escalas.map(hashtag)],
    input: (qs, tope) => ({ hashtags: qs, resultsPerPage: tope, proxyCountryCode: 'CO' }),
  },
  facebook: {
    etiqueta: 'Facebook', modo: 'páginas seguidas', tope: 15, propio: 10,
    actor: 'apify/facebook-posts-scraper',
    consultas: p => p.paginas,
    input: (qs, tope) => ({ startUrls: qs.map(url => ({ url })), resultsLimit: tope }),
  },
};

/* ── Capa 2 · los comentarios ─────────────────────────────────────────────
   El sentimiento no vive en los posts, vive en los comentarios: el post de la
   Alcaldía diciendo «inauguramos el parque» es neutro por definición; los 140
   comentarios debajo son la opinión de la localidad. Pero raspar comentarios
   es otro actor y otro precio —más que las cuatro redes de posts juntas—, así
   que es una CAPA APARTE: se mide aparte, se cuesta aparte y se cobra aparte.

   No se raspan todos: por corrida y por red, los comentarios de los
   `postsPorCorrida` posts con más reacción (y de los propios del candidato, si
   tiene la cuenta). En X las respuestas SON tweets y salen con el mismo actor
   buscando por conversación; en las otras tres es un actor de comentarios.

   ⚠️ Los nombres de campo del input son los usuales de cada actor y pueden
   variar: un input con otro nombre falla con un error explícito del actor,
   que medir.mjs muestra tal cual.                                            */
export const COMENTARIOS = {
  postsPorCorrida: 3, tope: 30,
  x:         { actor: 'kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest', modo: 'respuestas (son tweets)',
               input: (posts, tope) => ({ searchTerms: posts.map(p => `conversation_id:${p.id}`), maxItems: posts.length * tope, sort: 'Latest' }) },
  instagram: { actor: 'apify/instagram-comment-scraper', modo: 'comentarios del post',
               input: (posts, tope) => ({ directUrls: posts.map(p => p.url), resultsLimit: tope }) },
  tiktok:    { actor: 'clockworks/tiktok-comments-scraper', modo: 'comentarios del video',
               input: (posts, tope) => ({ postURLs: posts.map(p => p.url), commentsPerPost: tope }) },
  facebook:  { actor: 'apify/facebook-comments-scraper', modo: 'comentarios del post',
               input: (posts, tope) => ({ startUrls: posts.map(p => ({ url: p.url })), resultsLimit: tope }) },
};

/* De un ítem de posts, lo que la capa de comentarios necesita: la URL, el id y
   una medida de reacción para escoger los que más conversación tienen. Los
   nombres de campo varían por actor; se prueban los usuales y, si ninguno
   aparece, el ítem no se puede seguir y se dice. */
export function referenciaDePost(item) {
  const url = item.url || item.webVideoUrl || item.postUrl || item.twitterUrl || item.link || '';
  const id = item.id || item.tweetId || item.postId || (url.match(/status\/(\d+)/) || [])[1] || '';
  const reaccion = ['likeCount', 'likesCount', 'diggCount', 'likes', 'reactionsCount', 'favorite_count'].map(k => Number(item[k])).find(n => !Number.isNaN(n)) ?? 0;
  const comentarios = ['replyCount', 'commentsCount', 'commentCount', 'comments'].map(k => Number(item[k])).find(n => !Number.isNaN(n)) ?? null;
  return url ? { url, id, reaccion, comentarios } : null;
}

/* Los precios de referencia, por si todavía no se ha medido. Son de páginas de
   terceros (sep-2026) porque apify.com no es alcanzable desde el entorno donde
   se escribió esto: sirven para dimensionar, NO para fijar tarifa. En cuanto
   medir.mjs escriba precios-medidos.json, mandan los medidos. */
export const PRECIOS_REFERENCIA = {
  x:         { bajo: 0.15, base: 0.25, alto: 0.40, fuente: 'igolaizola 0,15 · kaitoeasyapi 0,25 · apidojo 0,40' },
  instagram: { bajo: 0.30, base: 0.50, alto: 0.80, fuente: '~0,50/1K posts' },
  tiktok:    { bajo: 0.30, base: 0.50, alto: 0.80, fuente: '~0,50/1K posts' },
  facebook:  { bajo: 0.70, base: 0.89, alto: 2.00, fuente: 'dami_studio 0,70 · getanyapi 0,89 · alfalfa 2,00' },
};
/* Comentarios: los actores que vimos rondan US$1 por 1.000; en X las
   respuestas son tweets y cuestan lo que los tweets. */
export const PRECIOS_REFERENCIA_COMENTARIOS = {
  x:         { bajo: 0.15, base: 0.25, alto: 0.40, fuente: 'mismo actor que los posts' },
  instagram: { bajo: 0.50, base: 1.00, alto: 2.00, fuente: '~1,00/1K comentarios' },
  tiktok:    { bajo: 0.50, base: 1.00, alto: 2.00, fuente: '~1,00/1K comentarios' },
  facebook:  { bajo: 0.50, base: 1.00, alto: 2.00, fuente: '~1,00/1K comentarios' },
};

/* Cuántos resultados pide UNA corrida de cada red con este perfil. Una red sin
   consultas (Facebook sin páginas verificadas, o un perfil sin temas) sale con
   cero y un motivo, no con una cifra. */
export function plan(perfil) {
  return Object.entries(REDES).map(([red, r]) => {
    const consultas = r.consultas(perfil);
    const propio = perfil.cuentas?.[red] ? r.propio : 0;
    const motivo = !perfil.temas.length && red !== 'facebook' ? 'el candidato no ha escrito sus temas'
      : red === 'facebook' && !consultas.length ? `sin páginas verificadas para ${perfil.territorio.etiqueta}` : '';
    return { red, etiqueta: r.etiqueta, modo: r.modo, actor: r.actor, consultas, tope: r.tope, propio, motivo,
      porCorrida: motivo ? 0 : consultas.length * r.tope + propio };
  });
}

/* La capa 2 solo existe donde la capa 1 trajo posts: sin posts no hay de
   dónde sacar comentarios. Los posts propios entran además de los N con más
   reacción, si el candidato tiene la cuenta en esa red. */
export function planComentarios(perfil, planPosts = plan(perfil)) {
  return planPosts.map(f => {
    const c = COMENTARIOS[f.red];
    const posts = f.motivo ? 0 : COMENTARIOS.postsPorCorrida + (perfil.cuentas?.[f.red] ? 1 : 0);
    return { red: f.red, etiqueta: f.etiqueta, modo: c.modo, actor: c.actor, posts, tope: COMENTARIOS.tope,
      motivo: f.motivo ? `sin posts de ${f.etiqueta}, no hay comentarios que leer` : '', porCorrida: posts * COMENTARIOS.tope };
  });
}

/* ── De dónde sale el vínculo ────────────────────────────────────────────── */
export function cargarVinculo(args = {}) {
  const ruta = args.vinculo ? path.resolve(String(args.vinculo)) : path.join(path.dirname(fileURLToPath(import.meta.url)), 'ejemplo-vinculo.json');
  const v = JSON.parse(readFileSync(ruta, 'utf8'));
  return { vinculo: v, ruta, esEjemplo: !args.vinculo };
}
