/* ═══════════════════════════════════════════════════════════════════════════
   EL DÍA DE LA ELECCIÓN · cálculo compartido
   ───────────────────────────────────────────────────────────────────────────
   Responde dos preguntas que un candidato resuelve hoy a ojo: en CUÁNTOS
   puestos tiene que poner testigo y en CUÁLES, y qué se va a encontrar cada
   uno cuando llegue.

   ⚠️ Este módulo NO pide ni guarda un solo dato del equipo del candidato.
   Los nombres de sus testigos son su base de datos y no tienen por qué pasar
   por acá: la plataforma calcula el plan y él lo llena en su propio archivo.
   Todo lo que se usa acá es público — su votación histórica por puesto y la
   hoja de vida del puesto de la Registraduría.

   La fuente es `hvp/dep/{cod}.json` (ver build_hvp.py). Se carga por
   departamento a propósito: el candidato que compite por una localidad de
   Bogotá no tiene por qué bajar los 4,5 MB del país.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';
  const S3 = global.RRData.publicUrl('congreso-2026/output');
  const cache = new Map();
  function json(url) {
    if (!cache.has(url)) cache.set(url, fetch(url).then(r => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status))).catch(e => { cache.delete(url); throw e; }));
    return cache.get(url);
  }

  const pad = (v, n) => String(v || '').replace(/\D/g, '').padStart(n, '0');
  /* El código de puesto lleva letra en 187 puestos del país («0100199A1»), así
     que los dos últimos caracteres NO se pueden limpiar con \D: hacerlo borra
     253.897 electores y el puesto deja de casar con su hoja de vida. */
  const codigoPuesto = m => pad(m.dep, 2) + pad(m.mun, 3) + pad(m.zon, 2) +
    String(m.pue == null ? '' : m.pue).trim().toUpperCase().padStart(2, '0');

  /* ── La hoja de vida de los puestos donde tiene votos ────────────────── */
  async function hvpDe(mesas) {
    const deps = [...new Set((mesas || []).map(m => pad(m.dep, 2)).filter(d => d !== '00'))];
    const partes = await Promise.all(deps.map(d =>
      json(`${S3}/hvp/dep/${d}.json`).then(x => x.p || {}).catch(() => ({}))));
    return Object.assign({}, ...partes);
  }

  /* ── El plan: sus puestos, de mayor a menor votación ─────────────────── */
  function plan(mesas, hvp) {
    const porPuesto = new Map();
    (mesas || []).forEach(m => {
      const code = codigoPuesto(m), v = Number(m.v || 0);
      if (!code || code.length !== 9) return;
      const p = porPuesto.get(code) || { code, votos: 0, mesasConVoto: 0, depNom: m.depNom || '', munNom: m.munNom || '' };
      p.votos += v; if (v > 0) p.mesasConVoto++;
      porPuesto.set(code, p);
    });
    const lista = [...porPuesto.values()].filter(p => p.votos > 0)
      .sort((a, b) => b.votos - a.votos || a.code.localeCompare(b.code));
    const total = lista.reduce((s, p) => s + p.votos, 0);
    let acum = 0;
    lista.forEach((p, i) => {
      const h = hvp[p.code] || null;
      acum += p.votos;
      p.rango = i + 1;
      p.acumulado = acum;
      p.share = total ? p.votos / total : 0;
      p.cobertura = total ? acum / total : 0;
      p.hvp = h;
      p.mesas = Number(h?.me || 0) || p.mesasConVoto;
      p.nombre = h?.n || '';
      p.direccion = h?.d || '';
      p.barrio = h?.b || '';
      p.comuna = h?.co || '';
      /* Sin hoja de vida no se inventa nada: los campos quedan nulos y la
         pantalla lo dice. 253 puestos del censo están en ese caso. */
      p.sinFicha = !h;
    });
    return { puestos: lista, total, conFicha: lista.filter(p => !p.sinFicha).length };
  }

  /* ── Qué cubre con N testigos ────────────────────────────────────────── */
  function cobertura(plan, n) {
    const tope = Math.max(0, Math.min(n | 0, plan.puestos.length));
    const elegidos = plan.puestos.slice(0, tope);
    return {
      testigos: tope,
      puestos: elegidos,
      votos: elegidos.reduce((s, p) => s + p.votos, 0),
      mesas: elegidos.reduce((s, p) => s + p.mesas, 0),
      share: plan.total ? elegidos.reduce((s, p) => s + p.votos, 0) / plan.total : 0,
    };
  }

  /* Cuántos testigos hacen falta para llegar a un porcentaje de su votación.
     Es la pregunta al revés y es la que de verdad hace el candidato: «quiero
     cubrir el 70 %, ¿cuánta gente consigo?». */
  function testigosPara(plan, objetivo) {
    const meta = plan.total * objetivo;
    let acum = 0;
    for (let i = 0; i < plan.puestos.length; i++) {
      acum += plan.puestos[i].votos;
      if (acum >= meta) return i + 1;
    }
    return plan.puestos.length;
  }

  /* ── Lo que el testigo se va a encontrar ─────────────────────────────── */
  /* Cada aviso dice qué mirar ANTES del día, no después. El orden es el de
     lo que más estorba en la práctica: si el testigo no puede reportar, el
     resto da igual. */
  const AVISOS = [
    { id: 'mov', mal: p => p.hvp && !p.hvp.mov,
      titulo: 'sin señal móvil permanente',
      que: 'Su testigo no va a poder reportar en tiempo real desde ahí. Acuerde con él un punto y una hora de salida para llamar, o mándelo con radio.' },
    { id: 'net', mal: p => p.hvp && !p.hvp.net,
      titulo: 'sin internet en el puesto',
      que: 'Nada de formularios en línea ni fotos por WhatsApp desde adentro: el E-14 sale en papel o en foto que se manda al salir.' },
    { id: 'e14', mal: p => p.hvp && !p.hvp.e14,
      titulo: 'sin lugar para publicar el E-14',
      que: 'El acta se publica en el puesto por ley. Donde no hay dónde fijarla, su testigo tiene que pedir copia y dejar constancia de que la pidió.' },
    { id: 'acc', mal: p => p.hvp && p.hvp.acc >= 2,
      titulo: 'de acceso difícil',
      que: 'Cuente el viaje en la planeación: no es un puesto al que se llegue el mismo domingo en la mañana.' },
    { id: 'ord', mal: p => p.hvp && p.hvp.ord,
      titulo: 'con riesgo de orden público declarado',
      que: 'Lo declaró el registrador del municipio, no nosotros. Vale la pena hablarlo con su testigo antes de mandarlo y avisar a la Registraduría si algo pasa.' },
    { id: 'dis', mal: p => p.hvp && !p.hvp.dis,
      titulo: 'no accesibles para personas con discapacidad',
      que: 'Si entre su gente hay votantes con movilidad reducida, ese puesto les cuesta. Es información que sirve para el transporte del día.' },
    { id: 'tx', mal: p => p.hvp && !p.hvp.tx,
      titulo: 'sin lugar para transmisión de datos',
      que: 'Los resultados de ese puesto van a tardar más en aparecer en el preconteo. No lo lea como que algo pasó.' },
  ];

  function alertas(seleccion) {
    const n = seleccion.puestos.length;
    return AVISOS.map(a => {
      const casos = seleccion.puestos.filter(a.mal);
      return { id: a.id, titulo: a.titulo, que: a.que, n: casos.length, de: n, casos };
    }).filter(a => a.n > 0).sort((a, b) => b.n - a.n);
  }

  /* ── El plan, en texto plano, para que se lo lleve ───────────────────── */
  /* Sale con una columna «Testigo» VACÍA a propósito: ese nombre lo pone él
     en su archivo, no acá. */
  function csv(seleccion) {
    const cab = ['#', 'Testigo', 'Codigo', 'Puesto', 'Direccion', 'Barrio', 'Municipio',
      'Mesas', 'Censo', 'Votos suyos 2023', '% de su votacion', '% acumulado',
      'Senal movil', 'Internet', 'Publica E-14', 'Transmision', 'Accesible', 'Bajo techo',
      'Banos', 'Dificultad de acceso', 'Orden publico', 'Quien abre'];
    const si = v => v == null ? '' : (v ? 'Si' : 'No');
    const ACC = ['Sin dificultad', 'Media', 'Alta', 'Extrema'];
    const filas = seleccion.puestos.map(p => {
      const h = p.hvp || {};
      return [p.rango, '', p.code, p.nombre, p.direccion, p.barrio, p.munNom,
        p.mesas, h.ce ?? '', p.votos, (p.share * 100).toFixed(2).replace('.', ','),
        (p.cobertura * 100).toFixed(2).replace('.', ','),
        si(h.mov), si(h.net), si(h.e14), si(h.tx), si(h.dis), si(h.tch),
        h.ban ?? '', p.sinFicha ? '' : (ACC[h.acc] || ''), si(h.ord), h.abr || ''];
    });
    const esc = v => { const s = String(v ?? ''); return /[";\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
    return '﻿' + [cab, ...filas].map(f => f.map(esc).join(';')).join('\r\n');
  }

  global.C360DiaD = { hvpDe, plan, cobertura, testigosPara, alertas, csv, codigoPuesto, AVISOS, json, S3 };
})(window);
