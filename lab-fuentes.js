// ════════════════════════════════════════════════════════════════════════
// Lab de Políticas Públicas · fuentes sugeridas según el tema del problema
// ════════════════════════════════════════════════════════════════════════
// Cuando alguien escribe su problema, detecta el tema (educación, salud,
// seguridad…) y le muestra dos cosas:
//   1. Las cifras oficiales de SU municipio que ya tenemos precargadas
//      (lab-indicadores.js · Policía Nacional + MEN, 2018-2024).
//   2. Las bases donde está el resto del dato (lab-recursos.js, campo `temas`).
// Cada cosa trae «+ Añadir como evidencia», que la deja en la evidencia del
// módulo que lo monta.
//
// La detección es por diccionario, sin modelo: palabras que casan al inicio
// de una palabra del texto. Si no detecta nada, el usuario elige el tema.
//
// Uso:
//   LabFuentes.montar(elemento, {
//     modulo: 'problema',
//     texto: () => ['enunciado', 'afectados…'],   // o un solo string
//     escuchar: ['id-del-textarea', …],      // re-detecta al escribir
//     anadir: fila => {…},                    // fila {fuente,anyo,dato,link,nota}
//     yaEsta: fila => bool,                   // para pintar «✓ Añadida»
//     onTerritorio: (divipola, mun) => {…}    // opcional
//   });
//   LabFuentes.paraTextarea('id')  → { anadir, yaEsta } para evidencia en texto libre.
//   LabFuentes.refrescarTodos()    → repinta (p. ej. al borrar una evidencia).
//
// El municipio elegido se recuerda entre módulos en localStorage
// 'lab-territorio-v1' = { dep, mun }.
// ════════════════════════════════════════════════════════════════════════
(function () {
  'use strict';

  // ── Temas ─────────────────────────────────────────────────────────────
  // kw: inicios de palabra (sin tildes, minúscula). Una frase de varias
  // palabras pesa el doble que una palabra suelta.
  // ind: indicadores municipales de lab-indicadores.js para ese tema.
  // q: búsqueda sugerida en datos.gov.co.
  const TEMAS = [
    { id:'educacion', nombre:'Educación', q:'educacion',
      ind:['desercion','cobertura_neta','matricula_5_16'],
      kw:['educac','escuela','escolar','colegio','desercion','matricula','estudiant','docente','maestr','aprendizaje','saber 11','icfes','alfabetiz','universidad','bachiller','pae ','alimentacion escolar','repitencia','reprobacion','aula'] },
    { id:'salud', nombre:'Salud', q:'salud',
      ind:[],
      kw:['salud','hospital','eps ','ips ','mortalidad','morbilidad','enfermedad','vacun','dengue','desnutric','suicid','salud mental','consumo de sustancias','drogas','discapacidad','embarazo adolescente','medico','urgencias','cancer','diabetes'] },
    { id:'seguridad', nombre:'Seguridad y convivencia', q:'seguridad',
      ind:['homicidios','hurto_personas','hurto_vehiculos'],
      kw:['insegur','seguridad','homicid','asesinat','hurto','robo','delito','delincuen','crimen','criminal','extorsion','pandilla','microtrafico','convivencia','rinas','policia','sicariato','violencia armada','grupos armados'] },
    { id:'genero', nombre:'Violencias contra mujeres y familia', q:'violencia intrafamiliar',
      ind:['violencia_intrafamiliar','delitos_sexuales'],
      kw:['violencia intrafamiliar','violencia de genero','violencia contra la mujer','violencia sexual','abuso sexual','feminicid','mujeres','maltrato','violencia domestica','violencia de pareja','cuidado','cuidadoras','brecha de genero','acoso'] },
    { id:'infancia', nombre:'Niñez, adolescencia y juventud', q:'primera infancia',
      ind:['matricula_5_16'],
      kw:['primera infancia','ninez','ninos','ninas','infancia','adolescen','jovenes','juventud','menores de edad','trabajo infantil','embarazo adolescente'] },
    { id:'empleo', nombre:'Empleo e ingresos', q:'mercado laboral',
      ind:[],
      kw:['empleo','desempleo','desocupa','informalidad','trabajo','ingresos','emprend','mipyme','microempres','economia local','productividad','salario','comercio'] },
    { id:'pobreza', nombre:'Pobreza y hambre', q:'pobreza',
      ind:[],
      kw:['pobreza','pobres','ipm ','nbi ','necesidades basicas','hambre','inseguridad alimentaria','vulnerab','subsidio','transferencias','habitante de calle','desigualdad'] },
    { id:'vivienda', nombre:'Vivienda y hábitat', q:'vivienda',
      ind:[],
      kw:['vivienda','deficit habitacional','asentamiento','invasion','arriendo','mejoramiento de vivienda','urbanizac','barrios informales','titulacion','espacio publico','hacinamiento'] },
    { id:'agua', nombre:'Agua y saneamiento', q:'acueducto',
      ind:[],
      kw:['agua potable','agua','acueducto','alcantarillado','saneamiento','residuos','basura','relleno sanitario','aseo','servicios publicos','vertimiento'] },
    { id:'ambiente', nombre:'Ambiente y riesgo', q:'ambiental',
      ind:[],
      kw:['ambient','clima','cambio climatico','deforest','contaminac','calidad del aire','rio ','cuenca','inundac','deslizamiento','riesgo de desastre','desastre','sequia','mineria ilegal','incendio forestal','biodivers','paramo'] },
    { id:'movilidad', nombre:'Movilidad y vías', q:'siniestros viales',
      ind:[],
      kw:['movilidad','transporte','transito','siniestr','accidentes de transito','vias','malla vial','trancon','congestion','bicicleta','peaton','motociclist','terminal'] },
    { id:'conectividad', nombre:'Conectividad digital', q:'internet',
      ind:[],
      kw:['internet','conectividad','digital','brecha digital','wifi','tic ','telecomunicac'] },
    { id:'rural', nombre:'Desarrollo rural y agro', q:'agropecuario',
      ind:[],
      kw:['rural','campesin','agro','agricol','agropecuar','tierra','catastro','cultivo','vereda','ganader','cafe ','produccion agricola','vias terciarias','coca'] },
    { id:'victimas', nombre:'Víctimas, paz y conflicto', q:'victimas conflicto armado',
      ind:['homicidios'],
      kw:['victima','conflicto armado','paz ','desplazamiento','desplazad','reincorporac','pdet','minas antipersonal','reparacion','retorno','lideres sociales'] },
    { id:'migracion', nombre:'Migración', q:'migrantes',
      ind:[],
      kw:['migrant','migracion','venezolan','refugiad','retornad'] },
    { id:'fiscal', nombre:'Finanzas públicas y gestión', q:'ejecucion presupuestal',
      ind:[],
      kw:['presupuest','recaudo','finanzas','impuesto','predial','regalias','endeudamiento','contratacion','corrupc','transparencia','gestion publica','eficiencia del gasto','inversion publica'] },
    { id:'energia', nombre:'Energía', q:'energia electrica',
      ind:[],
      kw:['energia','electric','gas natural','tarifas de energia','zonas no interconectadas','alumbrado'] },
    { id:'poblacion', nombre:'Población y envejecimiento', q:'poblacion',
      ind:[],
      kw:['poblacion','envejecimiento','adulto mayor','adultos mayores','demograf','natalidad','censo'] }
  ];
  const TEMA = Object.fromEntries(TEMAS.map(t => [t.id, t]));
  const LS_TERR = 'lab-territorio-v1';

  function norm(s) {
    return ' ' + String(s == null ? '' : s).toLowerCase()
      .normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9ñ ]+/g, ' ').replace(/\s+/g, ' ').trim() + ' ';
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c =>
      ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
  }

  // Devuelve los temas detectados, del más al menos presente.
  function detectar(texto) {
    const t = norm(texto);
    if (t.trim().length < 4) return [];
    const out = [];
    for (const tema of TEMAS) {
      let score = 0;
      for (const kw of tema.kw) {
        // Un espacio final en la palabra clave exige palabra completa ('pae ', 'rio ').
        if (t.includes(' ' + kw)) score += kw.trim().includes(' ') ? 2 : 1;
      }
      if (score > 0) out.push({ id: tema.id, score });
    }
    out.sort((a, b) => b.score - a.score);
    return out;
  }

  function recursosDe(temaId) {
    const items = (window.LAB_RECURSOS && window.LAB_RECURSOS.items) || [];
    const propios = items.filter(i => (i.temas || []).includes(temaId));
    // Las bases del sector (co-sector) van antes que los portales generales.
    propios.sort((a, b) => (a.categoria === 'co-sector' ? 0 : 1) - (b.categoria === 'co-sector' ? 0 : 1));
    const generales = items.filter(i => (i.temas || []).includes('general') && !propios.includes(i));
    // Primero las del sector; las generales (DANE, TerriData) cierran la lista.
    return propios.concat(generales.slice(0, Math.max(0, 4 - propios.length))).slice(0, 4);
  }

  function leerTerr() {
    try { return JSON.parse(localStorage.getItem(LS_TERR) || 'null') || {}; } catch { return {}; }
  }
  function guardarTerr(t) {
    try { localStorage.setItem(LS_TERR, JSON.stringify(t)); } catch {}
  }

  // ── Estilos (una sola vez) ────────────────────────────────────────────
  function inyectarCSS() {
    if (document.getElementById('lab-fuentes-css')) return;
    const css = `
.lf{margin:1.1rem 0 1.4rem;padding:1.05rem 1.15rem 1rem;background:var(--paper-2,#fbf9f3);border:1px solid var(--rule,#d9d4c4);border-left:6px solid var(--post-it-verde,#5cb37f);border-radius:var(--r,12px);font-family:var(--sans,system-ui)}
.lf-eyebrow{font-family:var(--mono,monospace);font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--green,#2f7d4a);font-weight:700}
.lf-titulo{font-family:var(--display,var(--sans));font-weight:700;font-size:1.08rem;color:var(--ink,#1f1b3a);margin:.2rem 0 .55rem;line-height:1.25}
.lf-temas{display:flex;flex-wrap:wrap;gap:.4rem;align-items:center;margin-bottom:.4rem}
.lf-chip{font-family:var(--sans);font-size:.82rem;padding:.3rem .7rem;border-radius:999px;border:1px solid var(--rule-strong,#bdb6a3);background:var(--paper,#f2efe6);color:var(--ink-2,#4b4766);cursor:pointer;transition:background .15s,border-color .15s,transform .15s}
.lf-chip:hover{border-color:var(--ink,#1f1b3a);transform:translateY(-1px)}
.lf-chip.on{background:var(--post-it-verde,#5cb37f);border-color:var(--post-it-verde,#5cb37f);color:#10261a;font-weight:600}
.lf-otro{font-family:var(--sans);font-size:.82rem;padding:.28rem .5rem;border:1px dashed var(--rule-strong,#bdb6a3);background:transparent;color:var(--ink-3,#767290);border-radius:999px;max-width:13rem}
.lf-vacio{font-size:.9rem;line-height:1.5;color:var(--ink-2,#4b4766);margin:.2rem 0 0}
.lf-grid{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,1fr);gap:1rem;margin-top:.75rem}
@media (max-width:820px){.lf-grid{grid-template-columns:1fr}}
.lf-sub{font-family:var(--mono,monospace);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3,#767290);font-weight:700;margin-bottom:.5rem}
.lf-terr{display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:.6rem}
.lf-terr select{font-family:var(--sans);font-size:.86rem;padding:.38rem .55rem;background:var(--paper,#f2efe6);color:var(--ink,#1f1b3a);border:1px solid var(--rule-strong,#bdb6a3);border-radius:var(--r-s,8px);min-width:0;flex:1 1 9rem}
.lf-ind{display:grid;grid-template-columns:1fr auto;gap:.15rem .7rem;align-items:center;padding:.6rem .7rem;background:var(--paper,#f2efe6);border:1px solid var(--rule,#d9d4c4);border-radius:var(--r-s,8px);margin-bottom:.45rem}
.lf-ind-nom{font-size:.86rem;color:var(--ink-2,#4b4766);line-height:1.3}
.lf-ind-val{font-family:var(--display,var(--sans));font-weight:700;font-size:1.15rem;color:var(--ink,#1f1b3a);line-height:1.1}
.lf-ind-val small{font-family:var(--mono,monospace);font-size:.7rem;font-weight:400;color:var(--ink-3,#767290);margin-left:.3rem}
.lf-ind svg{grid-row:1/3;grid-column:2;display:block}
.lf-ind-pie{grid-column:1/-1;display:flex;justify-content:space-between;align-items:center;gap:.5rem;margin-top:.3rem;font-size:.74rem;color:var(--ink-3,#767290)}
.lf-base{padding:.55rem .7rem;border:1px solid var(--rule,#d9d4c4);border-radius:var(--r-s,8px);background:var(--paper,#f2efe6);margin-bottom:.45rem}
.lf-base-nom{font-weight:600;font-size:.88rem;color:var(--ink,#1f1b3a);line-height:1.3}
.lf-base-desc{font-size:.8rem;line-height:1.4;color:var(--ink-2,#4b4766);margin:.15rem 0 .35rem;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.lf-acc{display:flex;gap:.45rem;align-items:center;flex-wrap:wrap}
.lf-acc a{font-size:.78rem;color:var(--ink-2,#4b4766);text-decoration:underline;text-underline-offset:2px}
.lf-add{white-space:nowrap;flex-shrink:0;font-family:var(--sans);font-size:.78rem;font-weight:600;padding:.26rem .6rem;border-radius:999px;border:1px solid var(--ink,#1f1b3a);background:var(--ink,#1f1b3a);color:var(--paper,#f2efe6);cursor:pointer;transition:transform .15s,background .15s}
.lf-add:hover{transform:translateY(-1px)}
.lf-add.ok{background:transparent;color:var(--green,#2f7d4a);border-color:var(--green,#2f7d4a);cursor:default;transform:none}
.lf-nota{font-size:.84rem;line-height:1.45;color:var(--ink-2,#4b4766);padding:.55rem .7rem;border:1px dashed var(--rule-strong,#bdb6a3);border-radius:var(--r-s,8px)}
.lf-buscar{display:inline-block;margin-top:.15rem;font-size:.8rem;color:var(--ink-2,#4b4766)}
.lf-pie{font-size:.74rem;line-height:1.45;color:var(--ink-3,#767290);margin:.7rem 0 0}
.lf-cargando{font-size:.84rem;color:var(--ink-3,#767290);font-style:italic}
@media (prefers-reduced-motion:reduce){.lf-chip,.lf-add{transition:none}}
`;
    const st = document.createElement('style');
    st.id = 'lab-fuentes-css';
    st.textContent = css;
    document.head.appendChild(st);
  }

  function sparkline(values) {
    const ys = Object.keys(values || {}).sort();
    const pts = ys.map(y => Number(values[y])).filter(v => Number.isFinite(v));
    if (pts.length < 2) return '';
    const w = 74, h = 30, p = 3;
    const mn = Math.min(...pts), mx = Math.max(...pts), rg = (mx - mn) || 1;
    const xy = pts.map((v, i) => [p + i * (w - 2 * p) / (pts.length - 1), h - p - (v - mn) / rg * (h - 2 * p)]);
    const d = xy.map((q, i) => (i ? 'L' : 'M') + q[0].toFixed(1) + ' ' + q[1].toFixed(1)).join(' ');
    const u = xy[xy.length - 1];
    return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true"><path d="${d}" fill="none" stroke="var(--ink-2,#4b4766)" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${u[0].toFixed(1)}" cy="${u[1].toFixed(1)}" r="2.6" fill="var(--post-it-verde,#5cb37f)"/></svg>`;
  }

  // ── Instancias ────────────────────────────────────────────────────────
  const INSTANCIAS = [];

  function montar(el, opts) {
    if (!el || el._labFuentes) return el && el._labFuentes;
    inyectarCSS();
    const inst = { el, opts: Object.assign({ modulo: 'lab' }, opts), activo: null, manual: null, deptos: null };
    try { inst.manual = localStorage.getItem('lab-fuentes-tema-' + inst.opts.modulo) || null; } catch {}
    el._labFuentes = inst;
    INSTANCIAS.push(inst);

    let tmr = null;
    const programar = () => { clearTimeout(tmr); tmr = setTimeout(() => pintar(inst), 450); };
    (inst.opts.escuchar || []).forEach(id => {
      const inp = document.getElementById(id);
      if (inp) inp.addEventListener('input', programar);
    });

    el.addEventListener('click', ev => {
      const chip = ev.target.closest('[data-lf-tema]');
      if (chip) {
        inst.activo = chip.dataset.lfTema;
        inst.elegido = true;
        pintar(inst);
        return;
      }
      const add = ev.target.closest('[data-lf-add]');
      if (add && !add.classList.contains('ok')) {
        const fila = inst._filas && inst._filas[add.dataset.lfAdd];
        if (!fila) return;
        try { inst.opts.anadir && inst.opts.anadir(fila); } catch (e) { console.error(e); }
        refrescarTodos();
      }
    });
    el.addEventListener('change', ev => {
      if (ev.target.matches('[data-lf-otro]')) {
        const v = ev.target.value;
        inst.manual = v || null;
        inst.activo = v || null;
        inst.elegido = !!v;
        try { v ? localStorage.setItem('lab-fuentes-tema-' + inst.opts.modulo, v) : localStorage.removeItem('lab-fuentes-tema-' + inst.opts.modulo); } catch {}
        pintar(inst);
      }
      if (ev.target.matches('[data-lf-dep]')) {
        guardarTerr({ dep: ev.target.value, mun: '' });
        pintar(inst);
      }
      if (ev.target.matches('[data-lf-mun]')) {
        const t = leerTerr();
        t.mun = ev.target.value;
        guardarTerr(t);
        if (t.mun && inst.opts.onTerritorio && window.LabIndicadores && window.LabIndicadores.isLoaded()) {
          try { inst.opts.onTerritorio(t.mun, window.LabIndicadores.getMun(t.mun)); } catch (e) { console.error(e); }
        }
        refrescarTodos();
      }
    });

    // Si el módulo trae su propio municipio y aún no hay uno global, adoptarlo.
    if (!leerTerr().mun && inst.opts.territorioInicial) {
      try {
        const m = inst.opts.territorioInicial();
        if (m) guardarTerr({ dep: String(m).padStart(5, '0').slice(0, 2), mun: String(m).padStart(5, '0') });
      } catch {}
    }
    pintar(inst);
    return inst;
  }

  function pintar(inst) {
    const { el, opts } = inst;
    // texto() puede devolver un string o [principal, ...contexto]: el
    // enunciado pesa el triple que los afectados o el síntoma, así el tema
    // sigue a lo que la persona está escribiendo ahora.
    const crudo = typeof opts.texto === 'function' ? opts.texto() : '';
    const partes = Array.isArray(crudo) ? crudo : [crudo];
    const texto = partes.filter(Boolean).join(' ');
    const puntaje = {};
    partes.forEach((p, i) => detectar(p).forEach(d => { puntaje[d.id] = (puntaje[d.id] || 0) + d.score * (i === 0 ? 3 : 1); }));
    const ids = Object.keys(puntaje).sort((a, b) => puntaje[b] - puntaje[a]).slice(0, 3);
    if (inst.manual && !ids.includes(inst.manual)) ids.push(inst.manual);
    // El tema activo solo se queda fijo si la persona lo eligió con un clic.
    if (!inst.elegido || !ids.includes(inst.activo)) { inst.activo = ids[0] || null; inst.elegido = false; }
    const tema = inst.activo ? TEMA[inst.activo] : null;
    inst._filas = {};

    const opcionesOtro = TEMAS.filter(t => !ids.includes(t.id) || t.id === inst.manual)
      .map(t => `<option value="${t.id}"${t.id === inst.manual ? ' selected' : ''}>${esc(t.nombre)}</option>`).join('');
    const selectOtro = `<select class="lf-otro" data-lf-otro aria-label="Elegir otro tema"><option value="">${ids.length ? 'Otro tema…' : 'Elige el tema…'}</option>${opcionesOtro}</select>`;

    if (!tema) {
      inst._ultHtml = null; inst._ultTema = null;
      el.innerHTML = `<div class="lf">
        <div class="lf-eyebrow">Datos para tu problema</div>
        <div class="lf-titulo">¿De dónde sacas las cifras?</div>
        <p class="lf-vacio">${texto.trim().length < 12
          ? 'Cuando describas el problema te mostramos las cifras oficiales de tu municipio y las bases donde está el resto del dato.'
          : 'No reconocimos el tema en lo que escribiste. Elígelo y te mostramos dónde están los datos.'}</p>
        <div class="lf-temas" style="margin-top:.6rem">${selectOtro}</div>
      </div>`;
      return;
    }

    const chips = ids.map(id => `<button type="button" class="lf-chip${id === inst.activo ? ' on' : ''}" data-lf-tema="${id}">${esc(TEMA[id].nombre)}</button>`).join('');

    // Bases sugeridas
    const bases = recursosDe(tema.id);
    const basesHtml = bases.map((r, i) => {
      const k = 'b' + i;
      const fila = { fuente: r.nombre, anyo: '', dato: '', link: r.url,
        nota: `Fuente sugerida para «${tema.nombre}». Falta anotar la cifra que vas a usar.` };
      inst._filas[k] = fila;
      const esta = opts.yaEsta ? !!opts.yaEsta(fila) : false;
      return `<div class="lf-base">
        <div class="lf-base-nom">${esc(r.nombre)}</div>
        <div class="lf-base-desc">${esc(r.desc || '')}</div>
        <div class="lf-acc">
          <button type="button" class="lf-add${esta ? ' ok' : ''}" data-lf-add="${k}">${esta ? '✓ En tu evidencia' : '+ Añadir como evidencia'}</button>
          <a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">Abrir ↗</a>
        </div>
      </div>`;
    }).join('');
    const buscar = `<a class="lf-buscar" href="https://www.datos.gov.co/browse?q=${encodeURIComponent(tema.q)}" target="_blank" rel="noopener noreferrer">Buscar «${esc(tema.q)}» en datos.gov.co ↗</a>`;

    const html = `<div class="lf${inst._ultTema !== tema.id ? ' lf-anim' : ''}">
      <div class="lf-eyebrow">Datos para tu problema</div>
      <div class="lf-titulo">Para «${esc(tema.nombre)}» hay datos aquí</div>
      <div class="lf-temas">${chips}${selectOtro}</div>
      <div class="lf-grid">
        <div><div class="lf-sub">Cifras oficiales de tu municipio</div><div data-lf-ind>${indicadoresHtml(inst, tema)}</div></div>
        <div><div class="lf-sub">Dónde buscar el resto</div>${basesHtml}${buscar}</div>
      </div>
      <p class="lf-pie">Las cifras municipales salen de datos.gov.co (Policía Nacional y Ministerio de Educación), 2018-2024. Revisa la ficha técnica de cada fuente antes de citarla.</p>
    </div>`;
    // Repintar solo si algo cambió: mientras se escribe, el panel se recalcula
    // cada pausa y no debe parpadear ni volver a animarse con el mismo tema.
    const sinAnim = html.replace(' lf-anim', '');
    if (sinAnim !== inst._ultHtml) { el.innerHTML = html; inst._ultHtml = sinAnim; }
    inst._ultTema = tema.id;
    if (tema.ind.length) asegurarDatos(inst, tema);
  }

  function indicadoresHtml(inst, tema) {
    if (!tema.ind.length) {
      return `<div class="lf-nota">Para este tema todavía no tenemos cifras municipales precargadas. Las bases de la derecha sí las tienen: abre la que corresponda y anota la cifra en tu evidencia.</div>`;
    }
    const LI = window.LabIndicadores;
    if (!LI) return `<div class="lf-nota">No se pudieron cargar las cifras municipales.</div>`;
    if (!LI.isLoaded()) return `<div class="lf-cargando">Cargando cifras de 1.108 municipios…</div>`;

    const terr = leerTerr();
    const deptos = LI.getDeptosCatalog();
    const optsDep = deptos.map(d => `<option value="${d.cod}"${d.cod === terr.dep ? ' selected' : ''}>${esc(d.nombre)}</option>`).join('');
    const muns = terr.dep ? LI.getMunsByDepto(terr.dep) : [];
    const optsMun = muns.map(m => `<option value="${m.divipola}"${m.divipola === terr.mun ? ' selected' : ''}>${esc(m.nombre)}</option>`).join('');
    const selects = `<div class="lf-terr">
      <select data-lf-dep aria-label="Departamento"><option value="">Departamento…</option>${optsDep}</select>
      <select data-lf-mun aria-label="Municipio"${terr.dep ? '' : ' disabled'}><option value="">Municipio…</option>${optsMun}</select>
    </div>`;
    if (!terr.mun) return selects + `<div class="lf-nota">Elige tu municipio y te mostramos sus cifras de ${tema.ind.length === 1 ? 'este indicador' : 'estos ' + tema.ind.length + ' indicadores'}.</div>`;

    const mun = LI.getMun(terr.mun);
    if (!mun) return selects;
    const cat = LI.getCatalog();
    let html = '';
    tema.ind.forEach((indId, i) => {
      const meta = cat.find(c => c.id === indId);
      const ult = LI.getLatestValue(terr.mun, indId);
      if (!meta || !ult || ult.value == null) return;
      // Bogotá es su propia entidad certificada en educación: el JSON la marca
      // como «ETC departamental (aprox)» por un cruce de nombres del builder,
      // pero la cifra es la del Distrito. No se rotula como aproximada.
      const proxy = ult.isProxy && terr.mun !== '11001';
      const serie = LI.getSerie(terr.mun, indId);
      const val = LI.formatValue(ult.value, indId);
      const unidad = meta.unidad === '%' ? '' : ' ' + meta.unidad;
      const k = 'i' + i;
      const fila = {
        fuente: meta.fuente,
        anyo: String(ult.year),
        dato: `${meta.nombre} · ${mun.nombre}: ${val}${unidad}` + (proxy ? ' (aprox)' : ''),
        link: meta.fuente_url,
        nota: (meta.nota || '') + (proxy ? ' Nota: es la cifra de la entidad certificada del departamento, no del municipio.' : '')
      };
      inst._filas[k] = fila;
      const esta = inst.opts.yaEsta ? !!inst.opts.yaEsta(fila) : false;
      html += `<div class="lf-ind">
        <div class="lf-ind-nom">${esc(meta.nombre)}${proxy ? ' · <em title="El municipio no es entidad certificada en educación: la cifra es la del departamento.">cifra departamental</em>' : ''}</div>
        ${serie ? sparkline(serie.values) : ''}
        <div class="lf-ind-val">${esc(val)}<small>${esc(unidad.trim())} · ${ult.year}</small></div>
        <div class="lf-ind-pie"><span>${esc(meta.fuente)}</span>
          <button type="button" class="lf-add${esta ? ' ok' : ''}" data-lf-add="${k}">${esta ? '✓ En tu evidencia' : '+ Añadir'}</button></div>
      </div>`;
    });
    if (!html) html = `<div class="lf-nota">No hay cifras de este tema para ${esc(mun.nombre)}.</div>`;
    return selects + html;
  }

  function asegurarDatos(inst) {
    const LI = window.LabIndicadores;
    if (!LI || LI.isLoaded()) return;
    if (inst._cargando) return;
    inst._cargando = true;
    LI.load().then(() => { inst._cargando = false; refrescarTodos(); })
      .catch(() => {
        inst._cargando = false;
        const box = inst.el.querySelector('[data-lf-ind]');
        if (box) box.innerHTML = '<div class="lf-nota">No se pudieron cargar las cifras municipales. Las bases de la derecha siguen sirviendo.</div>';
      });
  }

  function refrescarTodos() {
    INSTANCIAS.forEach(inst => { if (inst.el.isConnected) pintar(inst); });
  }

  // Evidencia en texto libre (AIN, Comunicar): cada fuente es una línea.
  function paraTextarea(id) {
    const linea = f => f.dato
      ? `${f.dato} (${f.fuente}, ${f.anyo}) ${f.link}`
      : `Por consultar: ${f.fuente} ${f.link}`;
    return {
      anadir(f) {
        const ta = document.getElementById(id);
        if (!ta) return;
        const v = ta.value.trim();
        ta.value = (v ? v + '\n' : '') + linea(f);
        ta.dispatchEvent(new Event('input', { bubbles: true }));
      },
      yaEsta(f) {
        const ta = document.getElementById(id);
        if (!ta) return false;
        return f.dato ? ta.value.includes(f.dato) : ta.value.includes(f.link);
      }
    };
  }

  window.LabFuentes = { montar, detectar, recursosDe, paraTextarea, refrescarTodos, TEMAS };
})();
