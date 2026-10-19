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

  const URL_DATOS = 'candidato-360-data/iglesias-concejo-bogota-2023.json?v=20261019';
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
  }

  /* `slugs`: las candidaturas de la persona (actual + historial). */
  async function montar(cont, slugs, vigente = () => true) {
    if (!cont || !slugs?.length) return;
    const D = await cargar(); if (!D?.candidatos) return;
    const propio = D.candidatos.find(c => slugs.includes(c.slug)); if (!propio) return;
    if (!cont.isConnected || !vigente() || cont.querySelector('.ig-toggle')) return;
    estilos();
    cont.insertAdjacentHTML('beforeend', html(D, propio));
  }

  global.C360Iglesias = { montar, veredicto };
})(window);
