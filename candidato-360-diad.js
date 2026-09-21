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
  function csv(seleccion, etiqueta = 'Votos suyos') {
    const cab = ['#', 'Testigo', 'Codigo', 'Puesto', 'Direccion', 'Barrio', 'Municipio',
      'Mesas', 'Censo', etiqueta, '% del total', '% acumulado',
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

  /* ── De dónde sale el plan ────────────────────────────────────────────
     Los testigos cuidan los votos de la candidatura QUE VIENE, no los de la
     anterior. Quien fue a la JAL de Teusaquillo y ahora va al Concejo de
     Bogotá compite en las 20 localidades: armarle el plan con sus 24 puestos
     de la JAL era planear la elección equivocada.
     · «propio»: su votación, solo de candidaturas a ESA MISMA corporación y
       dentro del territorio al que va. Es lo mejor que hay cuando existe.
     · «territorio»: si no la hay, los puestos de toda la circunscripción,
       ordenados por los votos que sacó SU FAMILIA POLÍTICA en 2023. En una
       corporación de lista, el testigo cuida los votos de la lista entera;
       dónde vota la familia es el mejor mapa público de dónde van a estar.
       Sus votos de antes se marcan en el puesto, sin mezclarlos en la cifra.
     Fuente por destino: Concejo y JAL de las ciudades con detalle por comuna
     (concejo-2023 / jal-2023); Alcaldía, con el Concejo de su ciudad; el
     resto de municipios y las corporaciones departamentales, con la
     Asamblea 2023, la única que baja a todos los puestos del país. */
  const CORP_DE_SLUG = [[/^JAL\d{4}/, 'jal'], [/^CONC\d{4}/, 'concejo'], [/^ALC\d{4}/, 'alcaldia'],
    [/^ASAM\d{4}/, 'asamblea'], [/^GOB\d{4}/, 'gobernacion']];
  const corpDeSlug = sl => (CORP_DE_SLUG.find(([re]) => re.test(String(sl || ''))) || [])[1] || '';
  const DEPARTAMENTAL = ['asamblea', 'gobernacion'];
  const pad2 = x => pad(x, 2), pad3 = x => pad(x, 3);
  const normTexto = x => String(x || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase()
    .replace(/^\s*(LOC(ALIDAD)?\.?|COMUNA)?\s*\d+\s*/, '').replace(/[^A-Z0-9]+/g, ' ').trim();
  const NOMBRE_CORP = { concejo: 'el Concejo', alcaldia: 'la Alcaldía', jal: 'la JAL', asamblea: 'la Asamblea', gobernacion: 'la Gobernación' };
  const CON_ARTICULO = { izq: 'la izquierda', ci: 'el centro-izquierda', c: 'el centro', cd: 'el centro-derecha', d: 'la derecha' };

  function familiaDe(campana) {
    const PB = global.PartidosBloques; if (!PB) return '';
    const f = campana.avales === 'firmas' || campana.avales === 'indeciso' ? (campana.espectro || '')
      : (campana.partido ? PB.bloqueDeOrganizacion(campana.partido) : '');
    return f === 'sc' ? '' : f;
  }
  async function enTandas(tareas, n = 6) {
    const out = []; let i = 0;
    await Promise.all(Array.from({ length: n }, async () => { while (i < tareas.length) { const k = i++; out[k] = await tareas[k]().catch(() => null); } }));
    return out;
  }

  /* Los puestos de la circunscripción, con los votos de 2023 por partido. */
  async function puestosDestino(campana) {
    const E = global.C360Electorado, dep = pad2(campana.departamento), corp = campana.corp;
    if (!dep || dep === '00') return null;
    if (DEPARTAMENTAL.includes(corp)) {
      const r = await json(`${S3}/asamblea-2023/dep/${dep}.json`);
      const muns = Object.keys(r.comunas || {}).map(pad3);
      const partes = await enTandas(muns.map(m => () => json(`${S3}/asamblea-2023/mun/${dep}-${m}.json`)));
      return { fuente: 'asamblea', lugar: r.name || campana.departamentoNombre || '',
        archivos: partes.filter(Boolean).map(d => ({ d, mun: pad3(d.mme) })) , faltan: partes.filter(x => !x).length };
    }
    const mun3 = pad3(await E.codigoMunicipio(dep, campana.municipio).catch(() => ''));
    if (!mun3 || mun3 === '000') return null;
    const key = `${dep}-${mun3}`;
    const porComuna = corp === 'jal' ? 'jal' : 'concejo';     /* alcaldía: el Concejo de su ciudad */
    const res = await json(`${S3}/${porComuna}-2023/resultados-${porComuna}-2023.json`).catch(() => null);
    const ciudad = res?.data?.[key];
    if (ciudad) {
      let comunas = Object.entries(ciudad.comunas || {}).filter(([c]) => !['90', '98', 'NULL', ''].includes(c));
      if (corp === 'jal') {
        const q = normTexto(campana.localidad);
        const una = comunas.filter(([, d]) => normTexto(d.name) === q);
        if (una.length) comunas = una;
      }
      const partes = await enTandas(comunas.map(([c]) => () => json(`${S3}/${porComuna}-2023/comuna/${key}-${c}.json`)));
      /* El nombre de la unidad (Usaquén, Comuna 14…) sale del agregado: el
         archivo por comuna trae un rótulo genérico («COMUNA 1»). */
      const ciudadNom = (res.cities || []).find(x => x.key === key)?.name || campana.municipio || '';
      return { fuente: porComuna, lugar: corp === 'jal' && comunas.length === 1 ? comunas[0][1].name : ciudadNom,
        archivos: partes.map((d, i) => d && { d, mun: mun3, nombre: comunas[i][1].name }).filter(Boolean), faltan: partes.filter(x => !x).length };
    }
    const d = await json(`${S3}/asamblea-2023/mun/${key}.json`).catch(() => null);
    return d ? { fuente: 'asamblea', lugar: d.name || campana.municipio || '', archivos: [{ d, mun: mun3 }], faltan: 0 } : null;
  }

  /* Votos por puesto de la familia (o de todos, si no hay familia), como
     «mesas» sintéticas para reusar plan(). Si la familia no tuvo lista ahí
     en 2023, se mide con sus vecinas del espectro y se declara. */
  function mesasDeFamilia(destino, dep, famSet) {
    const E = global.C360Electorado, mesas = [];
    let propios = 0, total = 0;
    destino.archivos.forEach(({ d, mun, nombre }) => (d.puestos || []).forEach(pu => {
      const [zon, pue] = String(pu.code || '').split('-');
      if (!zon || !pue || ['90', '98'].includes(zon)) return;
      const f = E.votosFamilia(pu.v, d.cands, d.partidos, famSet || new Set(), pu.l);
      const v = famSet ? f.propios : f.total;
      propios += f.propios; total += f.total;
      if (v > 0) mesas.push({ dep, mun, zon, pue, v, munNom: nombre || d.name || '' });
    }));
    return { mesas, peso: total ? propios / total : 0 };
  }

  async function fuente({ slugs = [], campana = {} } = {}) {
    const E = global.C360Electorado;
    const corp = campana.corp || '';
    const suyas = await E.mesasDe(slugs);
    const aqui = { dep: pad2(campana.departamento), mun: '' };
    if (campana.municipio && !DEPARTAMENTAL.includes(corp)) aqui.mun = pad3(await E.codigoMunicipio(aqui.dep, campana.municipio).catch(() => ''));
    const dentro = m => !campana.departamento || (pad2(m.dep) === aqui.dep && (!aqui.mun || pad3(m.mun) === aqui.mun));

    /* «La misma corporación» o una candidatura previa a la misma corporación
       en el mismo territorio: su votación manda. */
    const mismas = slugs.filter(sl => corpDeSlug(sl) === corp);
    if (campana.ruta === 'same' || (mismas.length && corp !== 'jal')) {
      const mesas = campana.ruta === 'same' ? suyas : (await E.mesasDe(mismas)).filter(dentro);
      if (mesas.length) return { modo: 'propio', mesas, etiqueta: 'Votos suyos', suyas: null };
    }

    const destino = await puestosDestino(campana);
    if (!destino || !destino.archivos.length) return { modo: 'sin-dato', mesas: [] };
    const dep = pad2(campana.departamento);
    let familia = familiaDe(campana), famSet = familia ? new Set([familia]) : null, ampliada = false;
    let r = mesasDeFamilia(destino, dep, famSet);
    if (famSet && r.peso < .01 && E.VECINAS?.[familia]) {
      famSet = new Set(E.VECINAS[familia]); ampliada = true;
      r = mesasDeFamilia(destino, dep, famSet);
    }
    /* Sus votos de antes, por puesto, para marcarlos en la tabla. */
    const suyosPorPuesto = new Map();
    suyas.forEach(m => { const c = codigoPuesto(m), v = Number(m.v || 0); if (v) suyosPorPuesto.set(c, (suyosPorPuesto.get(c) || 0) + v); });
    const PB = global.PartidosBloques;
    const famTexto = !famSet ? 'todas las listas'
      : ampliada ? [...famSet].map(f => (PB?.BLOQUE_LABEL?.[f] || f).toLowerCase()).join(' + ')
      : (CON_ARTICULO[familia] || 'su familia política');
    const corpFuente = destino.fuente === 'jal' ? 'la JAL' : destino.fuente === 'concejo' ? 'el Concejo' : 'la Asamblea';
    return {
      modo: 'territorio', mesas: r.mesas, suyosPorPuesto, familia, ampliada, famTexto,
      corp, corpTexto: NOMBRE_CORP[corp] || 'su corporación', fuenteTexto: `${corpFuente} de 2023`,
      proxy: (corp === 'alcaldia' && destino.fuente === 'concejo') || (destino.fuente === 'asamblea' && !DEPARTAMENTAL.includes(corp)),
      lugar: destino.lugar, faltan: destino.faltan,
      etiqueta: famSet ? 'Votos de su familia 2023' : 'Votos válidos 2023',
    };
  }

  global.C360DiaD = { hvpDe, plan, cobertura, testigosPara, alertas, csv, codigoPuesto, AVISOS, json, S3, fuente, corpDeSlug };
})(window);
