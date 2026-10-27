/* ═══════════════════════════════════════════════════════════════════════════
   CANDIDATO 360 · ¿su voto sigue a las iglesias cristianas? (oct-19-2026)
   ───────────────────────────────────────────────────────────────────────────
   Bloque plegable («toggle estratégico») de la pestaña Territorio del módulo
   11. Lee candidato-360-data/iglesias-concejo-bogota-2023.json, que arma
   tools/candidato-360/iglesias/analisis.py: para cada candidato comparado, si
   su participación en el puesto sube con los templos cristianos no católicos
   cercanos, con el estrato controlado, contra candidatos de control.

   Solo aparece si la candidatura (o una de su historial) está en el análisis.
   ⚠ Es una correlación ecológica del territorio: que haya iglesias cerca de un
   puesto no dice que quien vota ahí sea creyente, ni por quién votó.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';

  const URL_DATOS = 'candidato-360-data/iglesias-concejo-bogota-2023.json?v=20261027';
  const esc = s => String(s ?? '').replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
  const dec = (x, n = 2) => x == null || Number.isNaN(x) ? '—' : Number(x).toFixed(n).replace('.', ',');
  const titulo = s => String(s || '').toLowerCase().replace(/(^|[\s(\-])([a-záéíóúñü])/g, (m, a, b) => a + b.toUpperCase()).replace(/\b(De|Del|La|Las|Los|Y|El|En)\b/g, w => w.toLowerCase()).replace(/^(\w)/, c => c.toUpperCase());

  let DATOS = null;
  const cargar = () => DATOS || (DATOS = fetch(URL_DATOS).then(r => r.ok ? r.json() : null).catch(() => null));

  /* Qué dice el número, en una frase. Manda la razón de cuartiles con su IC
     (es la que se entiende sin estadística); la regresión con estrato dice si
     sobrevive al control de clase. */
  function veredicto(c) {
    const [lo, hi] = c.ratio_ic95 || [], [rlo, rhi] = c.ic95_reg || [];
    const sube = lo > 1, baja = hi < 1, regSi = rlo > 0, regNeg = rhi < 0;
    if (sube && regSi) return { tono: 'si', txt: `Sí. En los puestos con más iglesias cristianas cerca su votación es ${dec(c.ratio_cuartil)} veces la de los puestos con menos, y la relación se mantiene con el estrato controlado.` };
    if (sube) return { tono: 'medio', txt: `En bruto sí (${dec(c.ratio_cuartil)} veces), pero con el estrato controlado la relación se diluye: las iglesias están donde también está su clase social de votantes.` };
    if (baja && regNeg) return { tono: 'no', txt: `Al revés: rinde menos donde hay más iglesias cristianas cerca (${dec(c.ratio_cuartil)} veces), también con el estrato controlado.` };
    if (baja) return { tono: 'no', txt: `En bruto rinde menos donde hay más iglesias cerca (${dec(c.ratio_cuartil)} veces); con el estrato controlado la diferencia no se sostiene.` };
    const matiz = regNeg ? ' Con el estrato controlado incluso rinde un poco menos donde hay más templos.' : regSi ? ' Con el estrato controlado aparece una relación leve a favor.' : '';
    return { tono: 'neutro', txt: `No: su votación no se concentra donde hay más iglesias cristianas cerca (${dec(c.ratio_cuartil)} veces, sin diferencia clara).${matiz}` };
  }

  /* Lo que sale de comparar: quién de los cristianos medidos sí sigue el mapa
     de templos, y qué significa para esta candidatura. Descriptivo: no dice
     quién vota por quién. */
  function comparada(D, propio) {
    const sigue = c => (c.ratio_ic95?.[0] > 1) && (c.ic95_reg?.[0] > 0);
    const cr = (D.candidatos || []).filter(c => c.grupo === 'cristiano' && c.slug !== propio.slug);
    const si = cr.filter(sigue).map(c => `${titulo(c.nombre)}, de ${c.nota || c.partido} (${dec(c.ratio_cuartil)}×),`);
    const ctl = (D.candidatos || []).filter(c => c.grupo !== 'cristiano' && sigue(c)).map(c => titulo(c.nombre));
    const yo = sigue(propio);
    const p1 = si.length ? `Entre los otros candidatos cristianos medidos, ${si.length === 1 ? 'solo' : ''} ${esc(si.join(' y '))} ${si.length === 1 ? 'sigue' : 'siguen'} el mapa de templos; los demás no.` : 'Ninguno de los otros candidatos cristianos medidos sigue el mapa de templos.';
    const p2 = ctl.length ? ` Ojo: también lo sigue ${esc(ctl.join(' y '))}, que no es candidatura cristiana, así que una parte de la relación es geografía de barrio, no religión.` : '';
    const p3 = yo ? ' Para usted, los barrios con más templos son terreno propio: es donde conviene sostener presencia.' : ' Para usted, la conclusión práctica es que su votación no llega por el mapa de templos: recorrer iglesias barrio por barrio no es lo que explica sus votos hoy, y su voto cristiano, si lo tiene, está repartido por la ciudad como su voto de opinión.';
    return `<p class="ig-comp">${(p1 + p2 + p3).replace(/ {2,}/g, ' ')}</p>`;
  }
  function html(D, propio) {
    const m = D.meta || {}, pu = m.puestos || {}, nc = pu.no_catolicas_1k || {};
    const v = veredicto(propio);
    const fila = c => {
      const sig = c.ic95_reg && (c.ic95_reg[0] > 0 || c.ic95_reg[1] < 0);
      return `<tr${c.slug === propio.slug ? ' class="ig-yo"' : ''}><td>${esc(titulo(c.nombre))}<small>${esc(c.nota || c.partido || '')}</small></td>
        <td>${c.grupo === 'cristiano' ? 'cristiano' : 'control'}</td>
        <td><b>${dec(c.ratio_cuartil)}×</b><small>${dec(c.ratio_ic95?.[0])} a ${dec(c.ratio_ic95?.[1])}</small></td>
        <td>${dec(c.spearman_1k)}</td>
        <td>${c.coef_reg_rel_pct == null ? '—' : `${c.coef_reg_rel_pct > 0 ? '+' : ''}${dec(c.coef_reg_rel_pct, 1)} %`}${sig ? ' <span class="ig-sig">✓</span>' : ''}</td></tr>`;
    };
    const orden = (D.candidatos || []).slice().sort((a, b) => (a.grupo === b.grupo ? 0 : a.grupo === 'cristiano' ? -1 : 1) || b.ratio_cuartil - a.ratio_cuartil);
    return `<details class="panel estr-bloque ig-toggle"><summary><span class="panel-num">Estratégico · interno</span><b>¿Su voto sigue a las iglesias cristianas?</b><span class="ig-chip ig-${v.tono}">${dec(propio.ratio_cuartil)}×</span></summary>
      <p class="ig-veredicto">${esc(v.txt)}</p>${comparada(D, propio)}
      <p class="helper">Concejo de Bogotá 2023, puesto por puesto. Se miden los templos cristianos no católicos cerca de cada puesto (${pu.con_coordenada_y_votos || ''} puestos; ${pu.no_catolicas_1k?.puestos_con_cero ?? '—'} no tienen ninguno a 1 km) y se compara cuánto de la votación del puesto se llevó cada candidato. La comparación con otros cristianos y con candidatos de control dice si es un rasgo suyo o de la geografía de la ciudad.</p>
      <div class="ig-tabla"><table><thead><tr><th>Candidatura</th><th>Grupo</th><th>Más iglesias vs menos</th><th>Rangos (ρ)</th><th>Por templo, con estrato</th></tr></thead><tbody>${orden.map(fila).join('')}</tbody></table></div>
      <p class="helper"><b>Más iglesias vs menos:</b> su participación en el 25 % de puestos con más templos cerca dividida por la del 25 % con menos (sin controlar estrato), con el intervalo del 95 %. <b>Por templo:</b> cuánto cambia su participación (en % de su promedio) por cada templo no católico más a 1 km, con católicos y estrato controlados; ✓ = el intervalo no incluye cero.</p>
      <p class="helper">⚠ ${esc(m.regla || 'Describe el territorio de los puestos, nunca a los votantes.')} Templos de OpenStreetMap: contra el catastro de Bogotá aparece ${dec(m.cobertura_osm_vs_catastro?.no_catolica?.pct, 0)} % de los templos no católicos notables, y muchas iglesias evangélicas funcionan en locales que ningún mapa registra, así que la medida se queda corta justo donde más importa; ${dec(pu.pct_validos_cubiertos, 1)} % de los votos válidos quedan en puestos con coordenada.</p>
    </details>`;
  }

  /* ── Mapa: iglesias de barrio donde coincide su voto (oct-27-2026) ─────────
     Pedido de Ricardo para Emel Rojas: no la correlación de toda la ciudad sino
     el mapa de las iglesias PEQUEÑAS (las de barrio) y en cuáles su votación
     del Concejo 2023 rinde por encima de su promedio. Las redes grandes (G12 de
     los Castellanos, Iglesia de Dios Ministerial del MIRA, Manantial, El Lugar de
     su Presencia, Casa sobre la Roca, Bethesda, Universal) van en gris: son
     estructura electoral de otros. Todo se calcula aquí con `mapa` del JSON. */
  const RADIO = 500, MIN_VOTOS = 40, UMBRAL = 1.2;
  const dist = (a, b, c, d) => { const R = 6371000, r = Math.PI / 180, dp = (c - a) * r, dl = (d - b) * r; const h = Math.sin(dp / 2) ** 2 + Math.cos(a * r) * Math.cos(c * r) * Math.sin(dl / 2) ** 2; return 2 * R * Math.asin(Math.sqrt(h)); };
  const nf = n => Math.round(n).toLocaleString('es-CO');
  const TILDE_LOC = { Fontibon: 'Fontibón', Engativa: 'Engativá', Usaquen: 'Usaquén', 'Ciudad Bolivar': 'Ciudad Bolívar', 'Los Martires': 'Los Mártires', 'Antonio Narino': 'Antonio Nariño', 'San Cristobal': 'San Cristóbal' };
  const nomIg = n => !n ? 'Iglesia sin nombre en el mapa' : n === n.toLowerCase() ? titulo(n) : n;
  function cruce(D, slug) {
    const M = D.mapa; if (!M?.votos?.[slug]) return null;
    const V = M.votos[slug], P = M.puestos;
    const totV = P.reduce((s, p) => s + (V[p[0]] || 0), 0), totVal = P.reduce((s, p) => s + p[3], 0), media = totV / totVal;
    /* OSM repite templos: el mismo punto con dos nombres («Iglesia Emmanuel» e
       «Iglesia Evangélica Emmanuel»). A menos de 60 m se funden. */
    const GEN = new Set(['IGLESIA', 'CRISTIANA', 'CRISTIANO', 'EVANGELICA', 'CENTRO', 'COMUNIDAD', 'MINISTERIO', 'MINISTERIOS', 'INTERNACIONAL', 'SEDE', 'COLOMBIA', 'DIOS']);
    const propias = n => new Set(String(n || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().split(/[^A-Z]+/).filter(w => w.length > 3 && !GEN.has(w)));
    const igl = [];
    M.iglesias.forEach(([lat, lon, nombre, grande, red]) => {
      const pn = propias(nombre);
      const dup = igl.find(x => x.grande === !!grande && (dist(lat, lon, x.lat, x.lon) < 40 ||
        (dist(lat, lon, x.lat, x.lon) < 150 && [...pn].some(w => propias(x.nombre).has(w)))));
      if (dup) { if ((nombre || '').length > dup.nombre.length) dup.nombre = nombre; return; }
      igl.push({ lat, lon, nombre: nombre || '', grande: !!grande, red: red || '' });
    });
    igl.forEach(x => {
      const cerca = P.filter(p => dist(x.lat, x.lon, p[1], p[2]) <= RADIO);
      x.v = cerca.reduce((s, p) => s + (V[p[0]] || 0), 0);
      x.val = cerca.reduce((s, p) => s + p[3], 0);
      x.ratio = x.val ? (x.v / x.val) / media : null;
      const loc = {}; cerca.forEach(p => { if (p[4]) loc[p[4]] = (loc[p[4]] || 0) + p[3]; });
      x.loc = Object.entries(loc).sort((a, b) => b[1] - a[1])[0]?.[0] || '';
      x.loc = TILDE_LOC[x.loc] || x.loc;
    });
    const coinc = igl.filter(x => !x.grande && x.ratio >= UMBRAL && x.v >= MIN_VOTOS).sort((a, b) => b.ratio - a.ratio);
    coinc.forEach((x, i) => { x.n = i + 1; });
    const puestos = P.map(p => ({ p: p[0], lat: p[1], lon: p[2], val: p[3], loc: TILDE_LOC[p[4]] || p[4], v: V[p[0]] || 0, ratio: p[3] ? ((V[p[0]] || 0) / p[3]) / media : 0 }));
    return { media, igl, coinc, puestos, pequenas: igl.filter(x => !x.grande).length, grandes: igl.filter(x => x.grande) };
  }
  function htmlMapa(D, propio, C) {
    const redes = [...new Set(C.grandes.map(g => g.red))];
    const filas = C.coinc.slice(0, 12).map(x => `<tr><td class="ig-n">${x.n}</td><td>${esc(nomIg(x.nombre))}<small>${esc(x.loc)}</small></td><td><b>${dec(x.ratio)}×</b></td><td>${nf(x.v)}</td></tr>`).join('');
    return `<div class="panel estr-bloque ig-mapa-bloque"><span class="panel-num">Estratégico · iglesias de barrio</span>
      <h3>¿En qué iglesias pequeñas coincide su voto?</h3>
      <p class="ig-veredicto">De ${C.pequenas} iglesias cristianas de barrio que tiene el mapa de Bogotá, en <b>${C.coinc.length}</b> su votación al Concejo 2023 en los puestos a ${RADIO} m rinde al menos ${dec(UMBRAL, 1)} veces su promedio de la ciudad, con ${MIN_VOTOS} votos o más. Son las puertas naturales: comunidades pequeñas en barrios donde usted ya tiene votos.</p>
      <div class="ig-mapa-cols"><div><div class="ig-mapa" id="igMapa"></div>
      <div class="ig-ley"><span><i class="pu bajo"></i>puesto donde rinde menos que su promedio</span><span><i class="pu alto"></i>donde rinde más</span><span><i class="ig peq"></i>iglesia de barrio</span><span><i class="ig num">1</i>coincide con su voto</span><span><i class="ig gra"></i>red grande, de otros</span></div></div>
      <div><table class="ig-coinc"><thead><tr><th>#</th><th>Iglesia</th><th>Rinde</th><th>Sus votos</th></tr></thead><tbody>${filas || '<tr><td colspan="4">Ninguna iglesia pequeña pasa el umbral.</td></tr>'}</tbody></table></div></div>
      <p class="helper"><b>Rinde:</b> su participación en los puestos a ${RADIO} m de la iglesia dividida por su participación en toda la ciudad (${dec(C.media * 100, 2)} % de los votos válidos). <b>Sus votos:</b> los que sacó en esos puestos. En gris, las redes grandes que tienen estructura electoral propia y no son terreno a disputar: ${esc(redes.join(' · '))}.</p>
      <p class="helper">⚠ Describe el territorio, no a las personas: que haya una iglesia cerca de un puesto donde usted saca votos no dice que quienes van a esa iglesia votaron por usted. Las iglesias salen de OpenStreetMap, que registra una parte: muchas congregaciones funcionan en locales que ningún mapa tiene.</p></div>`;
  }
  function pintarMapa(C) {
    const el = document.getElementById('igMapa'); if (!el || !global.L) return;
    const L = global.L;
    const m = L.map(el, { zoomControl: true, scrollWheelZoom: false, attributionControl: true, zoomSnap: 0.25 }).setView([4.64, -74.1], 11);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18, opacity: .45, attribution: '&copy; OpenStreetMap' }).addTo(m);
    const vmax = Math.max(...C.puestos.map(p => p.v)) || 1;
    C.puestos.forEach(p => {
      if (!p.v) return;
      L.circleMarker([p.lat, p.lon], { radius: 2 + 7 * Math.sqrt(p.v / vmax), stroke: false, fillOpacity: p.ratio >= 1 ? .55 : .35,
        fillColor: p.ratio >= 1.5 ? '#0d5a51' : p.ratio >= 1 ? '#3f9d8a' : '#9fb3c4' })
        .bindTooltip(`${esc(p.loc)} · puesto ${esc(p.p)}<br>${nf(p.v)} votos · rinde ${dec(p.ratio)}×`).addTo(m);
    });
    C.igl.filter(x => x.grande).forEach(x => L.circleMarker([x.lat, x.lon], { radius: 5, color: '#fff', weight: 1.5, fillColor: '#8a8f96', fillOpacity: .9 })
      .bindTooltip(`${esc(x.nombre)}<br>Red grande: ${esc(x.red)}`).addTo(m));
    C.igl.filter(x => !x.grande && !x.n).forEach(x => L.circleMarker([x.lat, x.lon], { radius: 4.5, color: '#fff', weight: 1.2, fillColor: '#ef705d', fillOpacity: .85 })
      .bindTooltip(`${esc(nomIg(x.nombre))}${x.val ? `<br>${nf(x.v)} votos suyos a ${RADIO} m · rinde ${dec(x.ratio)}×` : ''}`).addTo(m));
    C.coinc.forEach(x => L.marker([x.lat, x.lon], { icon: L.divIcon({ className: 'ig-pin', html: `<span>${x.n}</span>`, iconSize: [24, 24], iconAnchor: [12, 12] }), zIndexOffset: 1000 })
      .bindTooltip(`<b>${esc(nomIg(x.nombre))}</b><br>${esc(x.loc)}<br>${nf(x.v)} votos suyos a ${RADIO} m · rinde ${dec(x.ratio)}×`).addTo(m));
    /* Leaflet mide su caja al crearse, y la vista de estrategia termina de
       armarse después: se reencuadra a los puestos con votos cada vez que la
       caja cambia de tamaño, y una vez más por si acaso. */
    const con = C.puestos.filter(p => p.v);
    const lats = con.map(p => p.lat).sort((a, b) => a - b), lons = con.map(p => p.lon).sort((a, b) => a - b);
    const q = (xs, f) => xs[Math.min(xs.length - 1, Math.max(0, Math.round(f * (xs.length - 1))))];
    const caja = [[q(lats, .01), q(lons, .01)], [q(lats, .99), q(lons, .99)]];
    const encuadrar = () => { if (!el.clientWidth) return; m.invalidateSize(); m.fitBounds(caja, { padding: [12, 12], animate: false }); };
    el._igMapa = m;
    setTimeout(encuadrar, 0); setTimeout(encuadrar, 400);
    if (global.ResizeObserver) { let w = 0; new ResizeObserver(() => { if (el.clientWidth !== w) { w = el.clientWidth; encuadrar(); } }).observe(el); }
  }

  function estilos() {
    if (document.getElementById('c360IglesiasCss')) return;
    const s = document.createElement('style'); s.id = 'c360IglesiasCss';
    s.textContent = `.ig-toggle summary{cursor:pointer;display:flex;gap:12px;align-items:center;flex-wrap:wrap;list-style:none}
.ig-toggle summary::-webkit-details-marker{display:none}
.ig-toggle summary::after{content:'▸';margin-left:auto;opacity:.6}.ig-toggle[open] summary::after{content:'▾'}
.ig-toggle summary b{font-family:var(--display);font-size:17px}
.ig-chip{font:600 12px var(--mono);padding:3px 8px;border-radius:999px;background:#e7e2d6}
.ig-si{background:#f0b45f}.ig-medio{background:#f3d9a4}.ig-no{background:#cfe0d4}
.ig-veredicto{font-size:15px;margin:12px 0 8px}
.ig-comp{font-size:13.5px;margin:0 0 10px}
.ig-tabla{overflow:auto;margin:8px 0}.ig-tabla table{width:100%;border-collapse:collapse;font-size:12.5px}
.ig-tabla th{text-align:left;font:500 10px var(--mono);text-transform:uppercase;letter-spacing:.06em;padding:6px;border-bottom:1px solid var(--line)}
.ig-tabla td{padding:7px 6px;border-bottom:1px solid var(--line);vertical-align:top}.ig-tabla td small{display:block;opacity:.65;font-size:11px}
.ig-yo td{background:rgba(240,180,95,.18)}.ig-sig{color:var(--green);font-weight:700}`;
    document.head.appendChild(s);
    const t = document.createElement('style'); t.id = 'c360IglesiasMapaCss';
    t.textContent = `.ig-mapa-bloque h3{margin:6px 0 8px}.ig-mapa-cols{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:18px;align-items:start;margin:10px 0}
.ig-mapa{height:440px;border:1px solid var(--line)}
.ig-ley{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:11.5px;color:var(--muted);margin-top:8px}.ig-ley span{display:inline-flex;align-items:center;gap:5px}
.ig-ley i{display:inline-block;width:11px;height:11px;border-radius:50%}.ig-ley .pu.bajo{background:#9fb3c4}.ig-ley .pu.alto{background:#3f9d8a}
.ig-ley .ig.peq{background:#ef705d;border:1.5px solid #fff;box-shadow:0 0 0 1px #ef705d}.ig-ley .ig.gra{background:#8a8f96}
.ig-ley .ig.num{width:16px;height:16px;background:#102238;color:#fff;font:700 9.5px/16px var(--sans);text-align:center;font-style:normal}
.ig-coinc{width:100%;border-collapse:collapse;font-size:13px}.ig-coinc th{text-align:left;font:500 10px var(--mono);text-transform:uppercase;letter-spacing:.06em;padding:6px;border-bottom:1px solid var(--line)}
.ig-coinc td{padding:7px 6px;border-bottom:1px solid var(--line);vertical-align:top}.ig-coinc td small{display:block;color:var(--muted);font-size:11px}
.ig-n{font-weight:800;color:#ef705d}
.ig-pin span{display:grid;place-items:center;width:24px;height:24px;border-radius:50%;background:#102238;color:#fff;font:700 11px var(--sans);border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.35)}
@media(max-width:900px){.ig-mapa-cols{grid-template-columns:1fr}.ig-mapa{height:360px}}`;
    document.head.appendChild(t);
  }

  /* `slugs`: las candidaturas de la persona (actual + historial). */
  async function montar(cont, slugs, vigente = () => true) {
    if (!cont || !slugs?.length) return;
    const D = await cargar(); if (!D?.candidatos) return;
    const propio = D.candidatos.find(c => slugs.includes(c.slug)); if (!propio) return;
    if (!cont.isConnected || !vigente() || cont.querySelector('.ig-toggle')) return;
    estilos();
    const C = cruce(D, propio.slug);
    if (C) cont.insertAdjacentHTML('beforeend', htmlMapa(D, propio, C));
    cont.insertAdjacentHTML('beforeend', html(D, propio));
    if (C) pintarMapa(C);
  }

  global.C360Iglesias = { montar, veredicto, cruce };
})(window);
