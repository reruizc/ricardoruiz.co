/* ═══════════════════════════════════════════════════════════════════════════
   CANDIDATO 360 · registro de arquetipos
   ───────────────────────────────────────────────────────────────────────────
   Las cinco familias psicopolíticas del modelo de Nury Astrid (cartografía
   emocional 2015-2027, módulo 05 de Proyecto DC). Es la MISMA taxonomía que usa
   la capa táctica de saliencia de Proyecto DC
   (tools/agenda-medios-recomienda/arquetipos.json): si allá cambia una
   sensibilidad, hay que cambiarla acá.

   Dos capas, y la separación es el punto:

   1. `FAMILIAS` — el perfil de cada familia: qué temas de agenda la mueven
      (sensibilidad 1-5), qué la activa, qué la desmoviliza y en qué tono se le
      habla. Esto sirve en CUALQUIER territorio.

   2. `TERRITORIOS` — cuánto pesa cada familia en un electorado concreto. Hoy
      solo existe Medellín (proyección 2027 por barrio). **Para sumar un
      territorio nuevo basta una entrada acá**: el panel de escucha la toma
      sola y pasa de «perfil de referencia» a «agenda ponderada por su
      electorado». Sin entrada, el panel lo dice en vez de suponer un reparto.

   ⚠️ Nada de esto es encuesta: es un modelo ecológico sobre voto barrial. La
   página lo declara.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';

  /* Las llaves de `sens` son los temas de agenda que clasifica
     candidato-360-saliencia.js (TEMAS). Los temas sin llave acá (política,
     ambiente, vivienda y obras) no mueven la sintonía de ninguna familia. */
  const FAMILIAS = [
    { slug: 'proteccion', color: '#2563eb', nombre: 'Protección con resultados', largo: 'Protección con resultados y orden competente',
      tagline: 'Orden que se ve · resultados verificables',
      sens: { seguridad: 5, corrupcion: 3, empleo: 4, servicios: 4, movilidad: 4, salud_educacion: 3, participacion: 2, cultura: 2 },
      activa: 'Resultados visibles, seguridad barrial y autoridad eficaz',
      desmoviliza: 'Promesa vacía, burocracia y deterioro urbano',
      fuga: 'Si la seguridad o la gestión no se sienten en el barrio, migra a castigo o supervivencia económica',
      tono: 'Firme, serio, ejecutivo, verificable y territorial',
      canales: 'WhatsApp, Facebook, radio y TV local, líderes de seguridad y comercio' },
    { slug: 'castigo', color: '#dc2626', nombre: 'Castigo y alternancia', largo: 'Castigo a la restauración y demanda de alternancia',
      tagline: 'Desencanto activo · vigilancia ciudadana',
      sens: { seguridad: 4, corrupcion: 5, empleo: 4, servicios: 3, movilidad: 3, salud_educacion: 3, participacion: 4, cultura: 3 },
      activa: 'Denuncia sustentada, control ciudadano y alternativa confiable',
      desmoviliza: 'Rabia vacía, opacidad y excusas',
      fuga: 'Puede migrar a continuidad si hay beneficios visibles o a pertenencia si emerge un liderazgo local fuerte',
      tono: 'Crítico, documentado, vigilante, cívico y argumentativo',
      canales: 'WhatsApp, YouTube, Facebook, medios digitales, debates, vocerías ciudadanas' },
    { slug: 'continuidad', color: '#16a34a', nombre: 'Continuidad pragmática', largo: 'Continuidad pragmática y gestión barrial',
      tagline: 'Vínculo que funciona · gestión semanal',
      sens: { seguridad: 3, corrupcion: 2, empleo: 3, servicios: 5, movilidad: 4, salud_educacion: 4, participacion: 5, cultura: 3 },
      activa: 'Respuesta cercana, trámites, programas y gestión semanal',
      desmoviliza: 'Ruptura del vínculo o abandono del territorio',
      fuga: 'Si la continuidad no resuelve, migra a supervivencia económica o a castigo',
      tono: 'Cercano, funcional, barrial, concreto y continuista con mejoras',
      canales: 'WhatsApp, reuniones pequeñas, llamadas, líderes comunitarios, casa a casa, JAL' },
    { slug: 'supervivencia', color: '#b45309', nombre: 'Supervivencia económica', largo: 'Supervivencia económica y servicios cotidianos',
      tagline: 'Bolsillo apretado · soluciones inmediatas',
      sens: { seguridad: 3, corrupcion: 2, empleo: 5, servicios: 5, movilidad: 4, salud_educacion: 4, participacion: 2, cultura: 2 },
      activa: 'Empleo, alivios, subsidios, transporte y servicios',
      desmoviliza: 'Lenguaje abstracto, tecnocracia y promesa lejana',
      fuga: 'Puede ser capturado por maquinarias locales o por propuestas con beneficios muy tangibles',
      tono: 'Directo, sencillo, útil, empático y resolvedor',
      canales: 'WhatsApp, TikTok, radio popular, activaciones territoriales, voz a voz' },
    { slug: 'pertenencia', color: '#a21caf', nombre: 'Pertenencia comunitaria', largo: 'Pertenencia comunitaria y autonomía territorial',
      tagline: 'Voz del barrio · identidad y arraigo',
      sens: { seguridad: 4, corrupcion: 3, empleo: 3, servicios: 4, movilidad: 3, salud_educacion: 3, participacion: 5, cultura: 5 },
      activa: 'Reconocimiento, participación, cultura y liderazgo local',
      desmoviliza: 'Invisibilización, centralismo y falta de escucha',
      fuga: 'Si no hay liderazgo confiable, puede migrar a protección o a castigo',
      tono: 'Comunitario, reconocedor, participativo, identitario y esperanzador',
      canales: 'WhatsApp comunitario, Facebook, Instagram, encuentros barriales, colectivos culturales' },
  ];

  const S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/bases+de+datos/Proyecto+DC/arquetipos';

  /* Cada territorio: cómo reconocerlo desde el territorio de la candidatura
     (`calza`) y de dónde sale el peso de cada familia (`cargar`, que devuelve
     `{ slug: fracción }` sumando ~1). */
  const TERRITORIOS = [
    {
      id: 'medellin', nombre: 'Medellín',
      fuente: 'Proyección 2027 por barrio · cartografía emocional de Medellín 2015-2027',
      calza: t => !t.departamental && norm(t.munLimpio || t.base) === 'MEDELLIN',
      cargar: async () => {
        const r = await fetch(`${S3}/proyeccion-2027-resumen.json`);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const d = await r.json(), pesos = {};
        for (const a of d?.ciudad_2027?.arquetipos || []) pesos[a.familia] = Number(a.pct_ciudad) || 0;
        return pesos;
      },
    },
  ];

  const norm = s => String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^A-Za-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim().toUpperCase();

  /* Devuelve `{ territorio, pesos }` o null si el territorio todavía no tiene
     arquetipos construidos. Se cachea por sesión. */
  const cache = new Map();
  async function deTerritorio(t) {
    const def = TERRITORIOS.find(x => { try { return x.calza(t); } catch { return false; } });
    if (!def) return null;
    if (!cache.has(def.id)) cache.set(def.id, def.cargar().then(pesos => ({ territorio: def, pesos })).catch(() => null));
    return cache.get(def.id);
  }

  global.C360Arquetipos = { FAMILIAS, TERRITORIOS, deTerritorio };
})(window);
