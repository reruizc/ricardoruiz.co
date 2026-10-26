/* ═══════════════════════════════════════════════════════════════════════════
   CANDIDATO 360 · 12 · Su territorio, mes a mes (oct-26-2026)
   ───────────────────────────────────────────────────────────────────────────
   Las bases públicas que se actualizan cada mes, leídas para el territorio al
   que se lanza la persona:
     · JAL          → su localidad o comuna (y la ciudad alrededor)
     · Concejo/Alc. → su municipio
     · Asamblea/Gob → su departamento
   Tres fuentes:
     · Seguridad · Policía Nacional. Los JSON del hub de Policía, sin copiar
       nada: ponal/{meta,municipios,deptos,nacional,poblacion}.json y, en las
       nueve ciudades con mes a mes, ponal/ciudades-mes/{dane}.json.
     · Empleo · DANE GEIH (trimestre móvil en 23 ciudades con su área
       metropolitana, año móvil en las 32 capitales, informalidad).
     · Educación · MEN (cobertura neta y deserción, 2018-2024).
     Empleo y educación salen de candidato-360/territorio.json, que arma
     tools/candidato-360/territorio/build.py.
   Lo comparten la tarjeta 12 del CRM (resumen) y candidato-360-territorio.html.
   Todo número que no corresponde exactamente al territorio lo dice: un
   municipio sin dato de empleo lee el de la capital de su departamento,
   rotulado como referencia.
   API: C360Territorio.leer(vinculo) → informe; .resumen(informe) → tarjeta.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';
  const S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output';
  const PONAL = `${S3}/ponal`;
  const LOCAL = new URLSearchParams(location.search).has('terrlocal');
  const TERR = LOCAL ? 'Bases%20de%20datos/dane-empleo/territorio.json' : `${S3}/candidato-360/territorio.json?v=20261026`;
  /* DANE → electoral (la tabla de split_municipios.py, la misma de ponal-base.js), invertida. */
  const DANE_A_ELEC = { '05': '01', '08': '03', '11': '16', '13': '05', '15': '07', '17': '09', '18': '44', '19': '11', '20': '12', '23': '13', '25': '15', '27': '17', '41': '19', '44': '48', '47': '21', '50': '52', '52': '23', '54': '25', '63': '26', '66': '24', '68': '27', '70': '28', '73': '29', '76': '31', '81': '40', '85': '46', '86': '64', '88': '56', '91': '60', '94': '50', '95': '54', '97': '68', '99': '72' };
  const ELEC_A_DANE = Object.fromEntries(Object.entries(DANE_A_ELEC).map(([d, e]) => [e, d]));
  const MESES = 'enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre'.split(' ');
  /* Delitos que la fuente trae a medias en el año (más de 15 % sin año): su
     cambio de un año a otro no es una tendencia, es el lote. Mismo umbral del hub. */
  const UMBRAL_PARCIAL = .15;

  const cache = {};
  const j = url => cache[url] || (cache[url] = fetch(url).then(r => { if (!r.ok) throw new Error(`${r.status} ${url}`); return r.json(); }).catch(e => { delete cache[url]; throw e; }));
  const norm = s => String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().replace(/[^A-Z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim();
  const sinDC = s => norm(s).replace(/\bD C\b/g, '').replace(/\bDISTRITO( CAPITAL| TURISTICO| ESPECIAL)?\b.*$/, '').trim();
  function mismoMunicipio(a, b) {
    a = sinDC(a); b = sinDC(b); if (!a || !b) return false;
    return a === b || a.endsWith(' ' + b) || b.endsWith(' ' + a) || a.startsWith(b + ' DE ') || b.startsWith(a + ' DE ');
  }
  const suma = a => (a || []).reduce((s, x) => s + (Number(x) || 0), 0);
  const pct = (a, b) => (b > 0 ? (a - b) / b : null);

  /* ── 1. Qué territorio ─────────────────────────────────────────────── */
  function resolver(v) {
    const P = global.C360Panel; if (!P || !v) return null;
    const v2 = JSON.parse(JSON.stringify(v));
    P.completarCampana?.(v2);
    const t = P.territorioDe(v2), c = v2.campana || {};
    const depElec = t.esBogota ? '16' : String(c.departamento || '').padStart(2, '0');
    const depDane = t.esBogota ? '11' : (ELEC_A_DANE[depElec] || '');
    const nivel = t.departamental ? 'departamento' : (t.corp === 'jal' ? 'localidad' : 'municipio');
    return { t, nivel, depElec, depDane, munNombre: t.esBogota ? 'Bogotá' : P.oracion(t.munLimpio), locNombre: t.loc ? P.oracion(t.loc) : '', depNombre: t.depNombre };
  }

  /* La localidad de la campaña («COMUNA 11 LAURELES», «TEUSAQUILLO») contra
     las unidades del archivo de la Policía: por número cuando los dos lo
     traen, si no por nombre (prefijo, como en el CRM). */
  function comunaDe(cm, loc) {
    if (!cm || !loc) return null;
    const n = norm(loc), num = (n.match(/\b(\d{1,2})\b/) || [])[1];
    const pares = Object.entries(cm.com_nom || {});
    if (num && cm.com_nom?.[String(Number(num))] !== undefined && /^\d+$/.test(Object.keys(cm.com_nom)[0])) return String(Number(num));
    const limpio = x => norm(x).replace(/\b(COMUNA|LOCALIDAD|UCG|NO)\b/g, '').replace(/\b\d+\b/g, '').replace(/\s+/g, ' ').trim();
    const ln = limpio(loc); if (!ln) return null;
    const hit = pares.find(([k, nom]) => { const cn = limpio(nom) || limpio(k); return cn && (cn === ln || cn.startsWith(ln) || ln.startsWith(cn)); });
    return hit ? hit[0] : null;
  }

  /* ── 2. Cargar ─────────────────────────────────────────────────────── */
  async function cargar(r) {
    const [meta, muns, deptos, pob, nac, idx, terr] = await Promise.all([
      j(`${PONAL}/meta.json`), j(`${PONAL}/municipios.json`), j(`${PONAL}/deptos.json`), j(`${PONAL}/poblacion.json`),
      j(`${PONAL}/nacional.json`), j(`${PONAL}/ciudades-mes/index.json`), j(TERR)]);
    let munDane = null;
    if (r.nivel !== 'departamento') {
      if (r.t.esBogota) munDane = '11001';
      else {
        const cand = Object.entries(muns.muns).filter(([code, m]) => (!r.depDane || m.dp === r.depDane) && mismoMunicipio(m.n, r.munNombre));
        if (cand.length === 1) munDane = cand[0][0];
        else if (cand.length > 1) munDane = (cand.find(([, m]) => sinDC(m.n) === sinDC(r.munNombre)) || [])[0] || null;
      }
    }
    const depDane = r.depDane || (munDane ? munDane.slice(0, 2) : '');
    let cm = null, com = null;
    const ciudadMes = (r.nivel === 'departamento' ? null : idx.ciudades.find(x => x.dane === munDane));
    if (ciudadMes) { try { cm = await j(`${PONAL}/ciudades-mes/${munDane}.json?v=${idx.v}`); } catch {} }
    if (cm && r.nivel === 'localidad') com = comunaDe(cm, r.t.loc);
    return { r, meta, muns, deptos, pob, nac, cm, com, munDane, depDane, terr };
  }

  /* ── 3. Seguridad ──────────────────────────────────────────────────── */
  function seguridad(D) {
    const { r, meta, pob, nac } = D;
    const ent = r.nivel === 'departamento' ? D.deptos.deptos[D.depDane] : D.muns.muns[D.munDane];
    if (!ent) return null;
    const anios = meta.anios, ult = meta.anio_parcial?.ultimo_completo || anios[anios.length - 2];
    const iC = anios.indexOf(ult), iP = iC - 1, iN = iC + 1;
    const pa = pob.anios.indexOf(ult);
    const poblacion = r.nivel === 'departamento' ? pob.deptos?.[D.depDane]?.p?.[pa] : pob.muns?.[D.munDane]?.p?.[pa];
    const pobNac = pob.nacional?.[pa];
    const filas = meta.delitos.map(dl => {
      const y = ent.d?.[dl.id]?.y || [];
      const v = y[iC] || 0, vp = y[iP] || 0, vn = y[iN];
      const parcial = dl.total ? dl.sin_anio / dl.total > UMBRAL_PARCIAL : false;
      const nuevo = (dl.desde || 2015) > ult - 1;
      const tasa = poblacion ? v / poblacion * 1e5 : null;
      const tasaNac = pobNac ? (nac.por_anio?.[dl.id]?.[iC] || 0) / pobNac * 1e5 : null;
      return { id: dl.id, label: dl.label, serie: y, v, vp, vn, cambio: parcial || nuevo || vp < 20 ? null : pct(v, vp), parcial, tasa, tasaNac, razon: tasa && tasaNac ? tasa / tasaNac : null };
    }).filter(f => f.v > 0 || f.vp > 0).sort((a, b) => b.v - a.v);
    /* Mes a mes: la ciudad entera o, en JAL, la localidad dentro de ella. */
    let mes = null;
    if (D.cm) {
      const cm = D.cm, meses = cm.meses, unidad = D.com ? cm.comunas?.[D.com] : cm.ciudad;
      const iA = meses.indexOf(`${ult + 1}-01`), hasta = meses.length - 1, nYtd = hasta - iA + 1;
      const iB = meses.indexOf(`${ult}-01`);
      const porDelito = Object.fromEntries((cm.delitos || []).map(id => {
        const s = unidad?.[id] || [], sc = cm.ciudad?.[id] || [];
        const ytd = suma(s.slice(iA, hasta + 1)), ytdPrev = suma(s.slice(iB, iB + nYtd));
        /* La ciudad entera, aparte: la tabla del municipio no puede leer la localidad. */
        const cYtd = suma(sc.slice(iA, hasta + 1)), cPrev = suma(sc.slice(iB, iB + nYtd));
        return [id, { serie: s, ytd, ytdPrev, cambio: ytdPrev >= 20 ? pct(ytd, ytdPrev) : null, ciudad: sc, cYtd, cPrev, cCambio: cPrev >= 20 ? pct(cYtd, cPrev) : null }];
      }));
      /* El «barrio pendiente por asignar» se disparó en 2026: la comuna de esos
         hechos llega vacía, así que una localidad parece bajar aunque no baje.
         Se mide por delito y, si sube más de 5 puntos, la página compara PESOS
         (cuánto de lo ubicado en la ciudad cae en la localidad), no volúmenes. */
      let sesgo = null, peso = null;
      if (D.com) {
        const pend = id => { const p = cm.pend?.[id] || [], c = cm.ciudad?.[id] || []; return [suma(p.slice(iB, iB + nYtd)) / Math.max(1, suma(c.slice(iB, iB + nYtd))), suma(p.slice(iA, hasta + 1)) / Math.max(1, suma(c.slice(iA, hasta + 1)))]; };
        const [p25, p26] = pend('hurto_personas'); sesgo = { p25, p26, alto: p26 - p25 > .05 };
        const ubicado = (id, a, b) => Object.values(cm.comunas || {}).reduce((s, u) => s + suma((u[id] || []).slice(a, b)), 0);
        peso = Object.fromEntries((cm.delitos || []).map(id => {
          const loc = porDelito[id];
          const w25 = loc.ytdPrev / Math.max(1, ubicado(id, iB, iB + nYtd)), w26 = loc.ytd / Math.max(1, ubicado(id, iA, hasta + 1));
          return [id, { w25, w26 }];
        }));
      }
      const barrios = D.com ? (cm.barrios || []).filter(b => String(b[2]) === String(D.com)).map(b => {
        const d = b[3] || {}; const tot = a => Object.values(d).reduce((s, arr) => s + suma(arr.slice(a[0], a[1])), 0);
        return { n: b[0], y25: tot([iB, iB + 12]), ytd: tot([iA, hasta + 1]), d };
      }).sort((a, b) => b.y25 - a.y25) : [];
      const [aH, mH] = meses[hasta].split('-').map(Number);
      /* Lo que la Policía sí ubica en alguna unidad, mes a mes: el denominador del peso. */
      const ubicadoMes = D.com ? Object.fromEntries((cm.delitos || []).map(id => [id, meses.map((_, i) => Object.values(cm.comunas || {}).reduce((s, u) => s + ((u[id] || [])[i] || 0), 0))])) : null;
      mes = { meses, porDelito, sesgo, peso, barrios, ubicadoMes, hastaTxt: `${MESES[mH - 1]} de ${aH}`, rango: `enero y ${MESES[mH - 1]}`, anioYtd: aH, nombreUnidad: D.com ? (cm.com_nom?.[D.com] || r.locNombre) : cm.n, tipo: cm.tipo };
    }
    return { ult, filas, poblacion, mes, parcial: meta.anio_parcial, nombre: ent.n };
  }

  /* ── 4. Empleo ─────────────────────────────────────────────────────── */
  function empleo(D) {
    const C = D.terr.ciudades || {};
    let code = null, ref = false, area = false;
    if (D.munDane) {
      code = Object.keys(C).find(k => (C[k].area || [k]).includes(D.munDane)) || null;
      area = !!code && code !== D.munDane;
    }
    if (!code && D.depDane) { code = `${D.depDane}001`; ref = D.r.nivel !== 'departamento'; }
    const c = C[code]; if (!c) return null;
    const n = c.n.replace(/ A\.M\.$/, '').replace(/ D\.C\.$/, '');
    const out = { code, nombre: n, nombreDane: c.n, area, ref, capital: D.r.nivel === 'departamento' };
    if (c.trim) {
      const p = c.trim.p, k = p.length - 1, lab = p[k];
      const [m, a] = [lab.replace(/\s\d{4}$/, ''), Number(lab.slice(-4))];
      const kp = p.indexOf(`${m} ${a - 1}`);
      const N = D.terr.nacional, kn = N.p.indexOf(lab);
      Object.assign(out, { tipo: 'trimestre móvil', periodo: lab, td: c.trim.td[k], to: c.trim.to[k], tgp: c.trim.tgp[k], tdPrev: kp >= 0 ? c.trim.td[kp] : null, periodoPrev: kp >= 0 ? p[kp] : null,
        tdNac: kn >= 0 ? N.td[kn] : null, serie: { p, td: c.trim.td }, serieNac: { p: N.p, td: N.td } });
    } else if (c.anual) {
      const p = c.anual.p, k = p.length - 1;
      Object.assign(out, { tipo: 'año móvil', periodo: p[k], td: c.anual.td[k], to: c.anual.to[k], tgp: c.anual.tgp[k], tdPrev: k >= 12 ? c.anual.td[k - 12] : null, periodoPrev: k >= 12 ? p[k - 12] : null, serie: { p, td: c.anual.td } });
    }
    if (c.inf) { const k = c.inf.p.length - 1; out.inf = c.inf.inf[k]; out.infPeriodo = c.inf.p[k]; out.infPrev = k >= 12 ? c.inf.inf[k - 12] : null; }
    return out;
  }

  /* ── 5. Educación ──────────────────────────────────────────────────── */
  function educacion(D) {
    const E = D.terr.educacion || {};
    const code = D.r.nivel === 'departamento' ? `${D.depDane}001` : D.munDane;
    const e = E[code]; if (!e) return null;
    const serie = x => x ? { desde: Number(x[0]), v: x[1] } : null;
    const cob = serie(e.cob), des = serie(e.des);
    const ult = s => s ? s.v[s.v.length - 1] : null, ultAnio = s => s ? s.desde + s.v.length - 1 : null;
    return { code, nombre: D.muns.muns[code]?.n || '', capital: D.r.nivel === 'departamento', aprox: !!e.aprox, cob, des, cobUlt: ult(cob), desUlt: ult(des), anio: ultAnio(cob) || ultAnio(des), cobPrimero: cob?.v[0], desPrimero: des?.v[0], desde: cob?.desde || des?.desde };
  }

  /* ── 6. Frases para el discurso ────────────────────────────────────── */
  const f1 = x => (Math.round(x * 10) / 10).toLocaleString('es-CO');
  const fP = x => `${f1(Math.abs(x) * 100)} %`;
  const N = x => Math.round(x).toLocaleString('es-CO');
  /* Los nombres de pantalla salen de la Policía y el DANE («Medellín»,
     «Huila»), no de la Registraduría («MEDELLIN», «HUILA»). */
  function lugarTxt(I) { const r = I.r; return r.nivel === 'localidad' && r.locNombre ? r.locNombre : (r.nivel === 'departamento' ? I.nomDep : I.nomMun); }
  function frases(I) {
    const out = [], L = lugarTxt(I), S = I.seg, E = I.emp, Ed = I.edu, M = I.nomMun;
    if (S?.mes && I.com) {
      const p = S.mes.peso?.hurto_personas, pd = S.mes.porDelito.hurto_personas;
      if (p) out.push(`En ${L} ocurre el ${f1(p.w26 * 100)} % de los hurtos a personas que la Policía ubica en ${M} en lo que va de ${S.mes.anioYtd}${p.w25 ? ` (era el ${f1(p.w25 * 100)} % en el mismo periodo de ${S.mes.anioYtd - 1})` : ''}.`);
      if (S.mes.barrios[0]) out.push(`El barrio con más delitos denunciados de ${L} en ${S.ult} fue ${S.mes.barrios[0].n} (${N(S.mes.barrios[0].y25)} hechos).`);
      void pd;
    }
    if (S?.filas?.length) {
      const top = S.filas.find(f => f.cambio !== null && f.v >= 50);
      if (top) out.push(`${I.r.nivel === 'localidad' ? `En ${M}` : `En ${L}`} se denunciaron ${N(top.v)} casos de ${top.label.toLowerCase()} en ${S.ult}, ${fP(top.cambio)} ${top.cambio >= 0 ? 'más' : 'menos'} que en ${S.ult - 1}.`);
      const alto = S.filas.filter(f => f.razon && f.v >= 30 && !f.parcial).sort((a, b) => b.razon - a.razon)[0];
      if (alto && alto.razon >= 1.25) out.push(`La tasa de ${alto.label.toLowerCase()} ${I.r.nivel === 'localidad' ? `de ${M}` : `de ${L}`} es ${f1(alto.razon)} veces la del país: ${f1(alto.tasa)} por cada 100.000 habitantes contra ${f1(alto.tasaNac)}.`);
      if (S.mes) { const h = S.mes.porDelito.homicidios; if (h?.cCambio != null && h.cYtd >= 10) out.push(`Entre ${S.mes.rango} de ${S.mes.anioYtd} hubo ${N(h.cYtd)} homicidios en ${M}, ${fP(h.cCambio)} ${h.cCambio >= 0 ? 'más' : 'menos'} que en el mismo periodo del año anterior.`); }
    }
    if (E?.td != null) {
      const donde = E.ref ? `${E.nombre}, la capital de su departamento,` : (E.area ? `el área metropolitana de ${E.nombre}` : E.nombre);
      const comp = E.tdNac != null ? (E.td > E.tdNac + .3 ? `por encima del promedio nacional (${f1(E.tdNac)} %)` : E.td < E.tdNac - .3 ? `por debajo del promedio nacional (${f1(E.tdNac)} %)` : `cerca del promedio nacional (${f1(E.tdNac)} %)`) : '';
      out.push(`El desempleo en ${donde} está en ${f1(E.td)} %${comp ? `, ${comp}` : ''}${E.tdPrev != null ? `; hace un año era ${f1(E.tdPrev)} %` : ''}.`);
      if (E.inf != null) out.push(`${f1(E.inf)} de cada 100 personas que trabajan en ${E.area ? `el área metropolitana de ${E.nombre}` : E.nombre} lo hacen en la informalidad.`);
    }
    if (Ed?.desUlt != null && Ed.desPrimero != null && !Ed.aprox) out.push(`La deserción escolar en ${Ed.capital ? Ed.nombre : M} pasó de ${f1(Ed.desPrimero)} % en ${Ed.desde} a ${f1(Ed.desUlt)} % en ${Ed.anio}.`);
    return out;
  }

  async function leer(v) {
    const r = resolver(v); if (!r) throw new Error('sin territorio');
    const D = await cargar(r);
    const I = { r, munDane: D.munDane, depDane: D.depDane, com: D.com, meta: D.meta,
      nomMun: D.munDane === '11001' ? 'Bogotá' : (D.muns.muns[D.munDane]?.n || r.munNombre), nomDep: D.deptos.deptos[D.depDane]?.n || r.depNombre };
    I.seg = seguridad(D);
    if (I.seg?.mes) I.seg.mes.nombreCiudad = D.cm?.n;
    I.emp = empleo(D);
    I.edu = educacion(D);
    I.frases = frases(I);
    I.lugar = lugarTxt(I);
    I.fuentes = { policia: D.meta.fuente, corte: D.meta.anio_parcial, dane: D.terr.fuente, danePeriodo: I.emp?.periodo, men: D.terr.educacion_fuente };
    return I;
  }

  /* La tarjeta del CRM: un título con la frase más fuerte y una cifra. */
  function resumen(I) {
    const sinComuna = I.r.nivel === 'localidad' && !I.com;
    return {
      titulo: `Lo que pasa en ${I.lugar}, mes a mes.`,
      copy: I.frases[0] || 'Seguridad, empleo y educación de su territorio, con la fuente al lado.',
      dato: I.emp?.td != null ? `${f1(I.emp.td)} %` : (I.seg?.filas?.[0] ? N(I.seg.filas[0].v) : '—'),
      sub: I.emp?.td != null ? `desempleo · ${I.emp.nombre}` : (I.seg?.filas?.[0] ? `${I.seg.filas[0].label.toLowerCase()} · ${I.seg.ult}` : 'sin dato'),
      nota: sinComuna ? 'La Policía no publica mes a mes por comuna en esta ciudad: se lee la ciudad entera.' : '',
    };
  }

  global.C360Territorio = { leer, resumen, resolver, MESES, f1, N, fP };
})(window);
