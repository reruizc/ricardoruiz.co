/* perfil.mjs — el perfil de escucha, en un solo sitio.
   ------------------------------------------------------------------
   Lo comparten el modelo de costos (costos.mjs) y el medidor (medir.mjs): si
   fueran dos configuraciones, la cuenta y la medición hablarían de cosas
   distintas y la comparación no querría decir nada.

   El perfil de referencia es el que pidió el caso real: aspirante a la JAL de
   Tunjuelito, DOS temas de campaña, escucha en X, Instagram, TikTok y Facebook,
   dos lecturas al día, a escala de ciudad y de localidad.

   ⚠️ Los nombres de campo del input VARÍAN por actor y el catálogo de Apify se
   mueve. Por eso cada red trae su actor y su plantilla acá arriba, y se cambian
   sin tocar la lógica.                                                        */

export const PERFIL = {
  candidato: 'JAL · Tunjuelito · Bogotá D.C.',
  temas: ['seguridad en el comercio', 'parque de la 45'],
  ciudad: 'Bogotá',
  localidad: 'Tunjuelito',
  cuentas: { x: 'ricardoruizco', instagram: 'ricardoruizco', tiktok: 'ricardoruizco', facebook: 'ricardoruizco' },
  corridasDia: 2,
  dias: 30,
};

/* Cuántos resultados se piden por consulta. ESTA es la palanca del costo:
   Apify cobra por resultado entregado, así que el gasto es
   tope × consultas × corridas, no «lo que traiga». */
export const REDES = {
  x: {
    etiqueta: 'X', modo: 'búsqueda por palabra', tope: 50, propio: 20,
    actor: 'kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest',
    /* El único que busca por palabra de verdad: los temas entran por ciudad y
       por localidad, más el nombre de la candidatura. */
    consultas: p => [...p.temas.flatMap(t => [`"${t}" ${p.ciudad}`, `"${t}" ${p.localidad}`]), `"${p.candidatoNombre || p.localidad}"`],
    input: (qs, tope) => ({ searchTerms: qs, maxItems: qs.length * tope, sort: 'Latest' }),
    campoTexto: 'text',
  },
  instagram: {
    etiqueta: 'Instagram', modo: 'hashtag', tope: 20, propio: 12,
    actor: 'apify/instagram-hashtag-scraper',
    consultas: p => [...p.temas.map(hashtag), hashtag(p.ciudad), hashtag(p.localidad)],
    input: (qs, tope) => ({ hashtags: qs, resultsLimit: tope }),
    campoTexto: 'caption',
  },
  tiktok: {
    etiqueta: 'TikTok', modo: 'hashtag', tope: 15, propio: 10,
    actor: 'clockworks/tiktok-scraper',
    consultas: p => [...p.temas.map(hashtag), hashtag(p.ciudad), hashtag(p.localidad)],
    input: (qs, tope) => ({ hashtags: qs, resultsPerPage: tope, proxyCountryCode: 'CO' }),
    campoTexto: 'text',
  },
  facebook: {
    etiqueta: 'Facebook', modo: 'páginas seguidas', tope: 15, propio: 10,
    actor: 'apify/facebook-posts-scraper',
    /* Facebook no busca por palabra: se siguen páginas. Estas son las del
       territorio, y son las que hay que revisar antes de medir. */
    consultas: () => [
      'https://www.facebook.com/AlcaldiaTunjuelito',
      'https://www.facebook.com/Bogota',
      'https://www.facebook.com/ConcejoDeBogota',
      'https://www.facebook.com/CanalCapital',
      'https://www.facebook.com/BogotaTransMilenio',
      'https://www.facebook.com/SecretariaGobiernoBogota',
    ],
    input: (qs, tope) => ({ startUrls: qs.map(url => ({ url })), resultsLimit: tope }),
    campoTexto: 'text',
  },
};

/* «parque de la 45» → #parquedela45 */
function hashtag(s) { return String(s).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]/g, ''); }

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

/* Cuántos resultados pide UNA corrida de cada red, con el perfil dado. */
export function plan(perfil = PERFIL) {
  const p = { ...perfil, candidatoNombre: perfil.candidatoNombre || perfil.localidad };
  return Object.entries(REDES).map(([red, r]) => {
    const consultas = r.consultas(p);
    return { red, etiqueta: r.etiqueta, modo: r.modo, actor: r.actor, consultas, tope: r.tope,
      propio: r.propio, porCorrida: consultas.length * r.tope + r.propio };
  });
}
