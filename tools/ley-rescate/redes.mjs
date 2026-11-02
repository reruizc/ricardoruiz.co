#!/usr/bin/env node
/* redes.mjs — la capa de redes del rastreo de la Ley de Rescate.
   ------------------------------------------------------------------
   Lee lo que se dice de la ley en X, TikTok, Instagram y Facebook por Apify y lo
   deja crudo en redes-crudo.json; rastreo.py lo clasifica. Los actores, sus
   nombres de campo y `referenciaDePost` son los de la escucha de Candidato 360:
   hay un solo sitio donde se cambian (tools/candidato-360/escucha/perfil.mjs).

     node tools/ley-rescate/redes.mjs --dry-run      plan y costo máximo, no gasta
     node tools/ley-rescate/redes.mjs --tope=1.5     tope en dólares de esta corrida

   El token SOLO se lee del entorno (APIFY_TOKEN). En GitHub Actions es un secreto. */
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { REDES, COMENTARIOS, referenciaDePost } from '../candidato-360/escucha/perfil.mjs';
import { clienteApify } from '../candidato-360/escucha/apify.mjs';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const DATOS = process.env.LR_DATOS || path.join(AQUI, '..', '..', 'Bases de datos', 'ley-rescate');
const arg = n => (process.argv.find(a => a.startsWith(`--${n}=`)) || '').split('=')[1];
const SECO = process.argv.includes('--dry-run');
const TOPE = Number(arg('tope') || process.env.LR_TOPE_USD || 1.5);
const TOPE_MES = Number(process.env.LR_TOPE_MES_USD || 45);

/* Qué se busca. Son frases, no palabras: «rescate» a secas trae rescatistas. */
const hoy = new Date();
const dias = Number(arg('dias') || process.env.LR_DIAS || 2);
const desde = new Date(hoy - dias * 864e5).toISOString().slice(0, 10);
const X_QS = ['"ley de rescate"', '"rescate económico"', '"rescate fiscal"', '#LeyDeRescate', '"reforma tributaria" (Abelardo OR "De la Espriella" OR Gómez)']
  .map(q => `${q} lang:es -filter:retweets since:${desde}`);
/* Una búsqueda por artículo, ordenada por interacción: los temas callados no salen
   entre los últimos 500 tweets, y es justo de ellos que se necesita saber si hay voz. */
const X_TEMAS = ['IVA (comida OR café OR alimentos OR tomate)', '(renta OR "clase media" OR retención)', '(prepagada OR "medicina prepagada")', '(facultades OR ministerios OR "suprimir")',
  '(amnistía OR normalización OR criptomonedas)', '(RUGE OR "grandes inversiones" OR estabilidad)', '(activos OR privatizar OR vender OR Ecopetrol)', 'patrimonio', '(contratistas OR nómina OR despidos)']
  .map(q => `"ley de rescate" ${q} lang:es -filter:retweets since:${desde}`);
const IG_TAGS = ['leyderescate', 'leyderescateeconomico', 'reformatributaria'];
const TT_TAGS = ['leyderescate', 'leyderescateeconomico', 'reformatributaria'];
/* Las páginas de los medios nacionales: en Facebook lo que se puede leer son los
   comentarios a sus notas. Es donde comenta más gente que no vive en X. */
const FB_PAGINAS = ['https://www.facebook.com/RevistaSemana', 'https://www.facebook.com/NoticiasCaracol', 'https://www.facebook.com/eltiempo', 'https://www.facebook.com/bluradioco'];
const ES_LEY = /rescate|reforma tributaria|tributaria|\biva\b|impuestos?\b|hacienda|restrepo|paro nacional/i;

const PLAN = {
  x: { items: 500, temas: 360, coment: 120 }, tiktok: { items: 45, coment: 80 }, instagram: { items: 40, coment: 60 }, facebook: { items: 60, coment: 120 },
};

const texto = it => String(it.text || it.caption || it.desc || it.description || it.message || it.content || '').replace(/\s+/g, ' ').trim();
const autor = it => String(it.author?.userName || it.author?.username || it.ownerUsername || it.authorMeta?.name || it.user?.username || it.pageName || it.username || it.profileName || '').replace(/^@/, '');
const fecha = it => it.createdAt || it.createTimeISO || it.timestamp || it.time || it.date || it.createTime || null;
const seguidores = it => Number(it.author?.followers ?? it.author?.followersCount ?? it.authorMeta?.fans ?? it.user?.followers_count ?? it.followersCount ?? 0) || 0;
const verificado = it => Boolean(it.author?.isVerified ?? it.author?.isBlueVerified ?? it.authorMeta?.verified ?? it.isVerified ?? false);
const ficha = (red, tipo, it, padre = '') => {
  const r = referenciaDePost(it) || {};
  return { red, tipo, padre, texto: Array.from(texto(it)).slice(0, 500).join(''), autor: autor(it), seguidores: seguidores(it), verificado: verificado(it),
    fecha: fecha(it), url: r.url || '', inter: Number(r.reaccion || 0) + Number(r.comentarios || 0) };
};

async function main() {
  const salida = path.join(DATOS, 'redes-crudo.json');
  console.log(`Tope de esta corrida: US$${TOPE} · tope del mes: US$${TOPE_MES}`);
  const plan = [
    ['x', 'posts', REDES.x.actor, `${X_QS.length} búsquedas · ${PLAN.x.items} tweets`],
    ['tiktok', 'posts', REDES.tiktok.actor, `${TT_TAGS.length} hashtags · ${PLAN.tiktok.items} videos`],
    ['instagram', 'posts', REDES.instagram.actor, `${IG_TAGS.length} hashtags · ${PLAN.instagram.items} publicaciones`],
    ['facebook', 'posts', REDES.facebook.actor, `${FB_PAGINAS.length} páginas de medios · ${PLAN.facebook.items} publicaciones`],
  ];
  for (const p of plan) console.log(' ·', p[0].padEnd(10), p[3]);
  if (SECO) { console.log('Ensayo: no se gastó nada.'); return; }
  const token = process.env.APIFY_TOKEN;
  if (!token) { console.error('Sin APIFY_TOKEN en el entorno: se omite la capa de redes.'); process.exit(3); }

  const gastoRuta = path.join(DATOS, 'gasto-redes.json');
  let gasto = {}; try { gasto = JSON.parse(await readFile(gastoRuta, 'utf8')); } catch { /* primera vez */ }
  const mes = hoy.toISOString().slice(0, 7);
  if ((gasto[mes] || 0) >= TOPE_MES) { console.error(`Ya se gastó US$${gasto[mes]} este mes: se omite.`); process.exit(3); }

  const apify = clienteApify(token, { esperaMax: 240000 });
  let usd = 0;
  const items = [], informe = {};
  const puede = () => usd < TOPE;
  async function correr(red, tipo, actor, entrada) {
    if (!puede()) { (informe[red] ||= []).push(`${tipo}: omitido por el tope`); return []; }
    process.stdout.write(`▸ ${red} · ${tipo}… `);
    try {
      const r = await apify.correr(actor, entrada);
      usd += r.cobrado || 0;
      console.log(`${r.items.length} ítems · $${(r.cobrado || 0).toFixed(4)}`);
      (informe[red] ||= []).push(`${tipo}: ${r.items.length} · $${(r.cobrado || 0).toFixed(3)}`);
      return r.items;
    } catch (e) { console.log(`FALLÓ · ${e.message}`); (informe[red] ||= []).push(`${tipo}: FALLÓ · ${e.message}`); return []; }
  }
  /* Comentarios de las publicaciones con más reacción. Los comentarios son la
     parte más cara, así que van después de leer las cuatro redes. */
  const paraComentar = [];
  const x = (await correr('x', 'posts', REDES.x.actor, REDES.x.input(X_QS, Math.ceil(PLAN.x.items / X_QS.length)))).filter(i => !/KaitoEasyAPI/i.test(texto(i)));
  const xt = (await correr('x', 'posts por tema', REDES.x.actor, { ...REDES.x.input(X_TEMAS, Math.ceil(PLAN.x.temas / X_TEMAS.length)), sort: 'Top' })).filter(i => !/KaitoEasyAPI/i.test(texto(i)));
  [...x, ...xt].forEach(i => items.push(ficha('x', 'post', i)));
  paraComentar.push(['x', [...xt, ...x]]);
  const tt = await correr('tiktok', 'posts', REDES.tiktok.actor, REDES.tiktok.input(TT_TAGS, Math.ceil(PLAN.tiktok.items / TT_TAGS.length)));
  tt.forEach(i => items.push(ficha('tiktok', 'post', i)));
  paraComentar.push(['tiktok', tt]);
  const ig = await correr('instagram', 'posts', REDES.instagram.actor, REDES.instagram.input(IG_TAGS, Math.ceil(PLAN.instagram.items / IG_TAGS.length)));
  ig.forEach(i => items.push(ficha('instagram', 'post', i)));
  paraComentar.push(['instagram', ig]);
  const fbTodo = await correr('facebook', 'posts', REDES.facebook.actor, REDES.facebook.input(FB_PAGINAS, Math.ceil(PLAN.facebook.items / FB_PAGINAS.length)));
  const fb = fbTodo.filter(i => ES_LEY.test(texto(i)));
  (informe.facebook ||= []).push(`sobre la ley: ${fb.length} de ${fbTodo.length}`);
  fb.forEach(i => items.push(ficha('facebook', 'post', i)));
  paraComentar.unshift(['facebook', fb]);

  /* Un comentario suelto («qué horror») no dice de qué habla: se guarda con su publicación. */
  for (const [red, lista] of paraComentar) {
    const top = lista.map(i => ({ ...referenciaDePost(i), texto: texto(i) })).filter(r => r.url).sort((a, b) => b.reaccion - a.reaccion).slice(0, 6);
    if (!top.length || !COMENTARIOS[red]) continue;
    const cs = await correr(red, 'comentarios', COMENTARIOS[red].actor, COMENTARIOS[red].input(top, Math.ceil(PLAN[red].coment / top.length)));
    const padreDe = c => { const j = JSON.stringify(c); return (top.find(t => (t.id && j.includes(String(t.id))) || j.includes(t.url.replace(/\/$/, '').split('/').pop())) || {}).texto || ''; };
    cs.filter(i => !/KaitoEasyAPI/i.test(texto(i))).forEach(i => items.push(ficha(red, 'comentario', i, padreDe(i).slice(0, 200))));
  }
  gasto[mes] = Math.round(((gasto[mes] || 0) + usd) * 1000) / 1000;
  await mkdir(DATOS, { recursive: true });
  await writeFile(gastoRuta, JSON.stringify(gasto));
  await writeFile(salida, JSON.stringify({ generado: new Date().toISOString(), usd, informe, items }));
  console.log(`Listo: ${items.length} ítems · US$${usd.toFixed(3)} · mes: US$${gasto[mes]}`);
}
main().catch(e => { console.error(e); process.exit(1); });
