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
      Medellín y Cartagena (proyección 2027 por barrio) y Bogotá (voto 2023);
      Cartagena y Bogotá traen sus propios ocho arquetipos. **Para sumar un
      territorio nuevo basta una entrada acá**: el panel de escucha la toma
      sola y pasa de «perfil de referencia» a «agenda ponderada por su
      electorado». Sin entrada, el panel lo dice en vez de suponer un reparto.

   ⚠️ Nada de esto es encuesta: es un modelo ecológico sobre voto barrial. La
   página lo declara.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';

  /* Nombres y textos 2027 de la entrega del 1-oct-2026 (matriz actualizada:
     Resultados Primero, Ojo Abierto, Confianza Cercana, Hogar Seguro, Orgullo
     de Barrio). El slug no cambia. ⚠️ `sens` sigue siendo la matriz de mayo: la
     nueva recalibra varias celdas y mover eso cambia la escucha y la
     simulación, así que espera visto bueno (ver candidato-360.md).
     Las llaves de `sens` son los temas de agenda que clasifica
     candidato-360-saliencia.js (TEMAS). Los temas sin llave acá (política,
     ambiente, vivienda y obras) no mueven la sintonía de ninguna familia. */
  const FAMILIAS = [
    { slug: 'proteccion', color: '#2563eb', nombre: 'Resultados Primero', largo: 'Resultados Primero',
      tagline: 'Gestión visible · Resultados concretos',
      sens: { seguridad: 5, corrupcion: 3, empleo: 4, servicios: 4, movilidad: 4, salud_educacion: 3, participacion: 2, cultura: 2 },
      activa: 'Resultados verificables en seguridad, movilidad, servicios, espacio público y obras',
      desmoviliza: 'Improvisación, desorden, deterioro visible y ausencia de resultados',
      fuga: 'Pierde apoyo ante improvisación, desorden, deterioro o ausencia de resultados concretos; puede moverse hacia Ojo Abierto u Hogar Seguro',
      tono: 'Serio, técnico, claro y orientado a logros verificables',
      canales: 'WhatsApp, prensa local, redes informativas, debates y referidos' },
    { slug: 'castigo', color: '#dc2626', nombre: 'Ojo Abierto', largo: 'Ojo Abierto',
      tagline: 'Verdad comprobable · Transparencia real',
      sens: { seguridad: 4, corrupcion: 5, empleo: 4, servicios: 3, movilidad: 3, salud_educacion: 3, participacion: 4, cultura: 3 },
      activa: 'Transparencia, evidencia, rendición de cuentas, control público y coherencia',
      desmoviliza: 'Escándalo, clientelismo, mentira, opacidad o acusaciones sin prueba',
      fuga: 'Se aleja ante escándalo, clientelismo, mentira o incoherencia; puede moverse hacia Confianza Cercana u Orgullo de Barrio',
      tono: 'Claro, verificable, frontal y basado en evidencia',
      canales: 'WhatsApp, medios locales, X / Twitter, debates y veedurías barriales' },
    { slug: 'continuidad', color: '#16a34a', nombre: 'Confianza Cercana', largo: 'Confianza Cercana',
      tagline: 'Presencia real · Escucha activa',
      sens: { seguridad: 3, corrupcion: 2, empleo: 3, servicios: 5, movilidad: 4, salud_educacion: 4, participacion: 5, cultura: 3 },
      activa: 'Escucha, respuesta, servicios, liderazgo local y continuidad útil',
      desmoviliza: 'Distancia, frialdad, abandono territorial o ruptura del canal de respuesta',
      fuga: 'Si percibe distancia, frialdad o ruptura del canal de respuesta, se desconecta y busca otro referente; puede moverse hacia Hogar Seguro u Ojo Abierto',
      tono: 'Cálido, cercano, concreto y de presencia permanente',
      canales: 'WhatsApp, casa a casa, reuniones barriales, líderes locales y Facebook' },
    { slug: 'supervivencia', color: '#b45309', nombre: 'Hogar Seguro', largo: 'Hogar Seguro',
      tagline: 'Bolsillo protegido · Servicios útiles',
      sens: { seguridad: 3, corrupcion: 2, empleo: 5, servicios: 5, movilidad: 4, salud_educacion: 4, participacion: 2, cultura: 2 },
      activa: 'Empleo, ingresos, servicios útiles, seguridad, salud y costo de vida',
      desmoviliza: 'Incertidumbre económica, alzas de gastos esenciales y falta de soluciones cotidianas',
      fuga: 'Si aumenta la incertidumbre económica o empeoran los gastos esenciales, castiga o se abstiene; puede moverse hacia Resultados Primero u opciones económicas',
      tono: 'Simple, empático, útil y orientado a soluciones del día a día',
      canales: 'WhatsApp, TV / radio local, referidos, Facebook y conversación familiar' },
    { slug: 'pertenencia', color: '#a21caf', nombre: 'Orgullo de Barrio', largo: 'Orgullo de Barrio',
      tagline: 'Identidad viva · Barrio con voz',
      sens: { seguridad: 4, corrupcion: 3, empleo: 3, servicios: 4, movilidad: 3, salud_educacion: 3, participacion: 5, cultura: 5 },
      activa: 'Participación, cultura, liderazgo, seguridad, servicios y representación local',
      desmoviliza: 'Abandono, desprecio simbólico, centralización o participación sin incidencia',
      fuga: 'Si siente abandono, desprecio simbólico o participación sin incidencia, se aleja y castiga; puede moverse hacia Resultados Primero u Ojo Abierto',
      tono: 'Orgulloso, comunitario, directo y con arraigo local',
      canales: 'WhatsApp, liderazgos barriales, eventos comunitarios, Facebook y casa a casa' },
  ];

  const S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/bases+de+datos/Proyecto+DC/arquetipos';

  /* Cada territorio: cómo reconocerlo desde el territorio de la candidatura
     (`calza`) y de dónde sale el peso de cada familia (`cargar`, que devuelve
     `{ slug: fracción }` sumando ~1). */
  const S3_CTG = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/bases+de+datos/Proyecto+DC/arquetipos-cartagena';
  const S3_BOG = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/arquetipos-bogota';

  const TERRITORIOS = [
    /* Cartagena trae su PROPIA taxonomía: ocho arquetipos de Nury, no las
       cinco familias de arriba. Por eso `cargar` devuelve también `familias`,
       y el panel de escucha usa esas en vez de FAMILIAS. La sensibilidad por
       tema sale de las palancas temáticas de Nury (tools/candidato-360/
       arquetipos/build_cartagena.py, `SENS`); `sensNury` dice qué temas
       calificó ella y cuáles se completaron leyendo su ficha.
       ⚠️ «Cartagena del Chairá» (Caquetá) NO calza: el nombre es exacto. */
    {
      id: 'cartagena', nombre: 'Cartagena',
      fuente: 'Simulación 2027 por barrio · cartografía emocional de Cartagena',
      calza: t => !t.departamental && /^CARTAGENA( DE INDIAS)?$/.test(norm(t.munLimpio || t.base)) && (!t.depNombre || norm(t.depNombre) === 'BOLIVAR'),
      cargar: async () => {
        const r = await fetch(`${S3_CTG}/arquetipos-cartagena.json?v=20261020`);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const d = await r.json();
        const familias = (d.orden || Object.keys(d.familias)).map(slug => {
          const f = d.familias[slug];
          return { slug, color: f.color, nombre: f.nombre, largo: f.nombre, tagline: f.lema, sens: f.sens || {}, sensNury: f.sens_nury || [],
            emocion: f.emocion, decide: f.decide || '', sube: f.sube || '', baja: f.baja || '', perfil: f.perfil || '', palancas: f.palancas || [], tematicas: f.tematicas || [] };
        });
        return { pesos: { ...(d.ciudad_share?.['2027'] || {}) }, familias };
      },
    },
    /* Bogotá (oct-19-2026): los 8 arquetipos de comportamiento electoral de la
       corporación de la campaña (la JAL usa los del Concejo). No hay estudio
       emocional: la sensibilidad por tema es criterio del equipo
       (tools/candidato-360/arquetipos-bogota/publicar.py, `SENS`), y la tarjeta
       lo dice (`heuristica`). Los pesos son el voto 2023 de la ciudad. */
    {
      id: 'bogota', nombre: 'Bogotá', heuristica: true,
      fuente: 'Arquetipos de comportamiento electoral de Bogotá, voto 2023',
      calza: t => !t.departamental && Boolean(t.esBogota),
      clave: t => (t?.corp === 'alcaldia' ? 'alcaldia' : 'concejo'),
      cargar: async t => {
        const corp = t?.corp === 'alcaldia' ? 'alcaldia' : 'concejo';
        const r = await fetch(`${S3_BOG}/arquetipos-bogota.json?v=20261019`);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const d = await r.json();
        const familias = (d.orden?.[corp] || []).map(slug => {
          const f = d.familias[slug];
          return { slug, color: f.color, nombre: f.nombre, largo: f.nombre, tagline: f.lema, sens: f.sens || {}, heuristica: true,
            decide: f.decide || '', oficio: f.oficio || '', perfil: f.quien || '', sube: '', baja: '', palancas: [], tematicas: [] };
        });
        return { pesos: { ...(d.share?.[corp] || {}) }, familias };
      },
    },
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

  /* Devuelve `{ territorio, pesos, familias }` (familias = null si el
     territorio usa las cinco de arriba) o null si el territorio todavía no tiene
     arquetipos construidos. Se cachea por sesión. */
  const cache = new Map();
  async function deTerritorio(t) {
    const def = TERRITORIOS.find(x => { try { return x.calza(t); } catch { return false; } });
    if (!def) return null;
    /* `cargar` devuelve los pesos solos, o `{ pesos, familias }` cuando el
       territorio tiene su propia taxonomía. */
    /* Bogotá lee una tipología por corporación: la caché va por territorio y clave. */
    const id = def.clave ? `${def.id}:${def.clave(t)}` : def.id;
    if (!cache.has(id)) cache.set(id, def.cargar(t).then(r => (r && r.pesos && typeof r.pesos === 'object' && !Array.isArray(r.pesos) && r.familias)
      ? { territorio: def, pesos: r.pesos, familias: r.familias }
      : { territorio: def, pesos: r, familias: null }).catch(() => null));
    return cache.get(id);
  }

  global.C360Arquetipos = { FAMILIAS, TERRITORIOS, deTerritorio };
})(window);
