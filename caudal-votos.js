/* caudal-votos.js — lo que sale del voto y de las cortes
   ------------------------------------------------------------------
   Tres vistas que agregan decisiones, no trámite: disciplina de bancada
   y coaliciones (las dos leen el voto nominal y comparten la escala de
   color de los partidos) y el pilar de órganos de control y altas
   cortes.

   Se apoya en caudal.html para `esc`, `fmt`, `pcolor` y para
   `abrirCongresista` del modal. Publica los tres hooks que
   caudal-base.js llama al entrar a cada vista.

   ⚠️ Al tocar este archivo hay que bumpear el ?v= del <script> que lo
   carga en caudal.html, o el navegador sirve la copia vieja. */
(function(){
  'use strict';

  /* ---------- pilar Órganos de control y altas cortes ---------- */
  const CONTROL_EJEMPLOS=['salud','contratación','pensiones','ambiente','elecciones'];
  const CONTROL={q:'', fuente:''}; let CONTROL_STATS=null, _controlSeq=0;
  function controlCard(x){
    return `<div class="sanc"><div class="sanc-top"><a class="sanc-name" href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.titulo||x.identificador)}</a><span class="sanc-fecha">${esc(x.fecha||'s. f.')}</span></div><div class="sanc-tags"><span class="doc-badge">${esc(x.fuente_nombre)}</span><span class="doc-badge">${esc(x.tipo)}</span></div><div class="sanc-motivo"><b>${esc(x.tema)}</b>${x.resumen?` · ${esc(x.resumen)}`:''}</div></div>`;
  }
  function controlWire(){
    const chips=document.getElementById('ctrlchips'), qel=document.getElementById('ctrlq'), go=document.getElementById('ctrlgo'), back=document.getElementById('controlBack');
    if(chips&&!chips.childElementCount) CONTROL_EJEMPLOS.forEach(t=>{const c=document.createElement('span');c.className='chip';c.textContent=t;c.onclick=()=>{qel.value=t;CONTROL.q=t;controlLoad()};chips.appendChild(c)});
    if(go&&!go.dataset.ready){go.dataset.ready='1';go.onclick=()=>{CONTROL.q=(qel.value||'').trim();controlLoad()};qel.addEventListener('keydown',e=>{if(e.key==='Enter')go.click()});back.onclick=()=>showView('home')}
  }
  function controlRender(d){
    const l=document.getElementById('control-landing'), r=document.getElementById('control-results'); if(!l||!r) return;
    controlWire();
    const rows=d.resultados||d.recientes||[];
    l.innerHTML=`<div class="cli-note"><b>Fuentes oficiales.</b> ${d.total||d.n||0} providencias indexadas · ${(d.por_fuente||[]).map(x=>`${esc(x.fuente)}: ${x.n}`).join(' · ')||'cargando cobertura'}.</div>`;
    r.innerHTML=rows.length?`<div class="rad-sec">${d.mode==='search'?'Resultados':'Providencias recientes'} · ${d.n||rows.length}</div>${rows.map(controlCard).join('')}`:`<div class="err">No encontramos providencias para «${esc(CONTROL.q)}».</div>`;
  }
  async function controlLoad(){
    const l=document.getElementById('control-landing'), r=document.getElementById('control-results'); if(!l||!r) return;
    const seq=++_controlSeq; r.innerHTML='<div class="llm-load" style="padding:2rem;justify-content:center">Consultando jurisprudencia <span class="dots"><span></span><span></span><span></span></span></div>';
    try{ const d=await call({action:'control',query:CONTROL.q,fuente:CONTROL.fuente}); if(seq!==_controlSeq)return; if(!CONTROL.q&&!CONTROL.fuente)CONTROL_STATS=d; controlRender(d); }
    catch(e){if(seq===_controlSeq)r.innerHTML='<div class="err">No se pudo cargar la jurisprudencia. Reintenta.</div>';}
  }

  /* ---------- disciplina de bancada · agregado del voto nominal ----------
     Las dos cámaras NUNCA se mezclan: Cámara 2014-2026 con Sí/No/Abstención,
     Senado desde 2017 y solo Sí/No, con un orden de magnitud menos votaciones
     contestadas. El alcance de cada una se imprime arriba de sus cifras. */
  let BANC_DATA=null, BANC_CAM='camara', _bancInited=false;
  const bancPct=v=>(v==null?'—':v+'%');
  function bancBar(frac,color,alto){
    const w=Math.max(0,Math.min(100,100*frac));
    return `<span class="cx-bar" style="height:${alto||8}px"><span style="width:${w}%;background:${color};transition:none"></span></span>`;
  }
  // serie de cohesión: SVG inline (sin CSS nuevo), una línea por bancada
  function bancSerie(d){
    const s=d.serie||[];
    if(!s.length) return `<div class="panel wide"><h3>Evolución de la cohesión</h3>
      <div class="cob-note" style="margin-top:0">${esc(d.nota_serie||'Sin serie: no hay suficientes votaciones contestadas para medir evolución.')}</div></div>`;
    const bs=(d.bancadas||[]).map(b=>b.bancada);
    const W=760,H=210,P={t:14,r:12,b:26,l:34};
    const x=i=>P.l+(s.length<2?0:i*(W-P.l-P.r)/(s.length-1));
    const y=v=>P.t+(1-v)*(H-P.t-P.b);
    const grid=[0,.25,.5,.75,1].map(v=>`<line x1="${P.l}" y1="${y(v).toFixed(1)}" x2="${W-P.r}" y2="${y(v).toFixed(1)}" stroke="var(--border2)"/>`
      +`<text x="${P.l-6}" y="${(y(v)+3).toFixed(1)}" text-anchor="end" fill="#6b7b87" font-size="9">${v.toFixed(2)}</text>`).join('');
    const ejeX=s.map((p,i)=>`<text x="${x(i).toFixed(1)}" y="${H-8}" text-anchor="middle" fill="#6b7b87" font-size="9">${esc(p.periodo)}</text>`).join('');
    const lineas=bs.map(b=>{
      const pts=s.map((p,i)=>({i,v:p.rice[b]})).filter(p=>p.v!=null);
      if(pts.length<2) return '';
      const c=pcolor(b);
      const path=pts.map((p,k)=>`${k?'L':'M'}${x(p.i).toFixed(1)},${y(p.v).toFixed(1)}`).join(' ');
      return `<path d="${path}" fill="none" stroke="${c}" stroke-width="1.8" stroke-linejoin="round"/>`
        + pts.map(p=>`<circle cx="${x(p.i).toFixed(1)}" cy="${y(p.v).toFixed(1)}" r="2.4" fill="${c}"></circle>`).join('');
    }).join('');
    const leg=bs.map(b=>`<span style="display:inline-flex;align-items:center;gap:.3rem;font-size:.62rem;color:var(--ink2)"><span style="width:.55rem;height:.55rem;border-radius:50%;background:${pcolor(b)}"></span>${esc(b)}</span>`).join('');
    // ⚠️ La serie va sobre TODAS las contestadas, no solo las de fondo: medido,
    // separando por tipo se caen 2014, 2016, 2020 y 2026 bajo el umbral de 25
    // votaciones y la línea quedaría cortada en 6 de 10 años. Se conserva
    // completa y se ROTULA como global, para que no se lea como continuación
    // del panel de cohesión de arriba, que sí es de fondo.
    return `<div class="panel wide"><h3>Evolución de la cohesión · índice de Rice por ${d.serie_tipo==='era'?'era':'año'} <span style="color:var(--ink3);font-weight:400">· todas las votaciones</span></h3>
      <svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block">${grid}${lineas}${ejeX}</svg>
      <div style="display:flex;flex-wrap:wrap;gap:.5rem .9rem;margin-top:.7rem">${leg}</div>
      <div class="cob-note">Solo periodos con al menos 25 votaciones contestadas, y solo bancadas con 8 o más votaciones en ese periodo. Faltan 2012, 2018 y 2019: sus actas quedaron parseadas a medias (mediana de 2 a 12 votantes por votación) y no son plenarias completas. <b>Esta serie cuenta todas las votaciones contestadas, no solo las de fondo</b>, así que va más abajo que la cohesión del panel anterior: restringirla a las de fondo dejaría 2014, 2016, 2020 y 2026 sin suficientes votaciones y la línea quedaría cortada en 6 de 10 años.</div></div>`;
  }
  function bancRender(){
    const el=document.getElementById('banc-body'); if(!el||!BANC_DATA) return;
    const d=BANC_DATA[BANC_CAM]||{}, c=d.cobertura||{}, bs=d.bancadas||[];
    if(!bs.length){ el.innerHTML='<div class="err">Sin datos de bancada para esta cámara.</div>'; return; }
    // ⚠️ La barra mide la cohesión DE FONDO, no la global: el 33% de las
    // votaciones contestadas de Cámara son impedimentos (decidir sobre el
    // conflicto de interés de un colega), donde la bancada se suelta por rutina
    // y no por indisciplina política. Medido, promediarlo todo sub-reporta la
    // disciplina y cambia el orden. La global va al lado como referencia.
    // Senado no trae `rice_fondo` (su API no dice qué se votó) → cae a la global.
    const hayFondo=bs.some(b=>b.rice_fondo!=null);
    const riceDe=b=>b.rice_fondo!=null?b.rice_fondo:b.rice;
    const maxRice=Math.max(...bs.map(riceDe));
    const coh=bs.map(b=>{
      const r=riceDe(b), bl=b.bloque_pct_fondo!=null?b.bloque_pct_fondo:b.bloque_pct;
      return `<div class="cx-row">
        <span class="cx-lab" style="width:120px;color:${pcolor(b.bancada)}">${esc(b.bancada)}</span>
        ${bancBar(r/Math.max(.001,maxRice),pcolor(b.bancada))}
        <span class="cx-n" style="width:132px">${r.toFixed(2)} · bloque ${bl}%${b.rice_fondo!=null?`<span style="color:var(--ink3)"> · global ${b.rice.toFixed(2)}</span>`:''}</span>
      </div>`;}).join('');
    // alineación: el Pacto se mide contra sí mismo, así que se marca aparte
    const ali=bs.slice().sort((a,b)=>(b.alineacion_petro||0)-(a.alineacion_petro||0)).map(b=>{
      const v=b.alineacion_petro;
      return `<div class="cx-row">
        <span class="cx-lab" style="width:120px;color:${pcolor(b.bancada)}">${esc(b.bancada)}</span>
        ${bancBar((v||0)/100,pcolor(b.bancada))}
        <span class="cx-n" style="width:112px">${bancPct(v)}${b.es_gobierno?' · es gobierno':''}</span>
      </div>`;}).join('');
    const dm=d.disidentes_meta||{};
    // el ranking manda por la disidencia DE FONDO: quien solo se sale en
    // impedimentos no es un disidente político (medido: hay quien baja de 55,6%
    // global a 44,4% de fondo, y quien sube de 69,7% a 79,7%).
    const dis=(d.disidentes||[]).map(x=>{
      const f=x.pct_fondo!=null;
      return `<div class="tl-item banc-dis" data-k="${esc(x.key)}">
        <span style="width:52px;flex-shrink:0;font-weight:700;color:var(--amber)">${f?x.pct_fondo:x.pct}%</span>
        <span style="flex:1;min-width:0"><span style="color:var(--ink)">${esc(x.nombre)}</span>
          <span style="color:${pcolor(x.bancada)};font-size:.66rem"> · ${esc(x.bancada)}</span></span>
        <span style="flex-shrink:0;font-size:.66rem;color:var(--ink3)">${f?`${x.d_fondo} de ${x.n_fondo} de fondo · ${x.pct}% en total`:`${x.d} de ${x.n} votaciones`}</span>
      </div>`;}).join('');
    const cob=bs.map(b=>`<span style="font-size:.62rem;color:var(--ink3)">${esc(b.bancada)} <b style="color:var(--ink2)">${b.n_miembros}</b> personas · ${fmt(b.n_votos)} votos</span>`).join(' &nbsp;·&nbsp; ');
    el.innerHTML=`
      <div class="cob-note" style="margin:0 0 1rem;font-size:.72rem;color:var(--ink2);line-height:1.5">
        <b style="color:var(--ink)">${esc(d.nombre||'')}</b> · ${esc(c.desde||'')} a ${esc(c.hasta||'')}. ${esc(d.alcance||'')}</div>
      <div class="kpis">
        <div class="kpi"><div class="n">${fmt(c.n_contestadas)}</div><div class="l">Votaciones contestadas</div></div>
        ${c.n_contestadas_fondo!=null&&c.contestadas_por_tipo?`<div class="kpi"><div class="n">${fmt(c.n_contestadas_fondo)}</div><div class="l">De fondo · deciden el proyecto</div></div>`:`<div class="kpi"><div class="n">${fmt(c.n_analizadas)}</div><div class="l">Votaciones analizadas</div></div>`}
        <div class="kpi"><div class="n">${bs.length}</div><div class="l">Bancadas medidas</div></div>
        <div class="kpi"><div class="n">${(100-(c.pct_sin_partido||0)).toFixed(1)}%</div><div class="l">Votos con partido</div></div>
      </div>
      <div class="grid2">
        <div class="panel"><h3>Cohesión · qué tan en bloque vota${hayFondo?' <span style="color:var(--ink3);font-weight:400">donde se decide el proyecto</span>':''}</h3>${coh}
          <div class="cob-note">Índice de Rice: |Sí−No| dividido por (Sí+No) dentro de la bancada, promediado sobre las votaciones contestadas. <b>1,00</b> = votó en bloque perfecto; <b>0</b> = partida por la mitad. «Bloque» es el porcentaje de votaciones donde al menos el 90% votó del mismo lado.${hayFondo?` <b>La cifra grande cuenta solo las votaciones de fondo</b> —ponencia, articulado, título, conciliación, aplazamiento y archivo—, ${fmt(c.n_contestadas_fondo)} de las ${fmt(c.n_contestadas)} contestadas. Se separan porque <b>${fmt(c.n_contestadas_impedimento)}</b> (${Math.round(100*(c.n_contestadas_impedimento||0)/Math.max(1,c.n_contestadas))}%) son <b>impedimentos</b>: ahí cada quien decide sobre el conflicto de interés de un colega y la bancada se suelta por rutina, no por indisciplina política. Medirlo todo junto sub-reporta la disciplina de forma desigual y cambia el orden — Cambio Radical pasa de estar por debajo de La U a estar por encima. La cifra global va en gris al lado.`:' Esta cámara no permite separar por tipo de votación: su fuente no publica <b>qué</b> se votó, así que aquí entran también impedimentos y trámite.'}</div></div>
        <div class="panel"><h3>Alineación con el gobierno · desde ago-2022</h3>${ali}
          <div class="cob-note">Porcentaje de votos que coincidieron con la posición del Pacto (su mayoría, ≥60%), restringido al gobierno Petro. <b>El Pacto coincide consigo mismo por definición</b>: su cifra no dice nada sobre él. Solo votaciones contestadas.</div></div>
      </div>
      ${bancSerie(d)}
      <div class="panel wide" style="margin-top:1.2rem"><h3>Quién se sale de su propia bancada</h3>
        ${dis||'<div class="cob-note" style="margin-top:0">Sin nadie por encima del mínimo de votaciones evaluables.</div>'}
        <div class="cob-note">${dm.mediana_pct_fondo!=null?'Porcentaje de votaciones <b>de fondo</b> —las que deciden el proyecto— en que la persona votó contra la mayoría de su propia bancada; al lado, su cifra sobre todas las contestadas. Se ordena por la de fondo porque quien solo se sale en impedimentos no es un disidente político.':'Porcentaje de votaciones contestadas en que la persona votó contra la mayoría de su propia bancada.'} Entran quienes tengan al menos ${dm.min_votos||0} votaciones evaluables${dm.min_votos_fondo?` (y ${dm.min_votos_fondo} de fondo para publicar esa cifra)`:''}: ${fmt(dm.n_evaluables||0)} personas lo cumplen y su disidencia mediana es ${dm.mediana_pct==null?'—':dm.mediana_pct+'%'}${dm.mediana_pct_fondo!=null?` y la de fondo ${dm.mediana_pct_fondo}%`:''}. Click para ver su récord completo.${BANC_CAM==='senado'?' <b>En Senado descansa en muy pocas votaciones</b> — mira la n de cada fila antes de sacar conclusiones. Su ficha personal muestra totales más altos porque cuenta las votaciones tal como las publica la fuente, sin descartar las que republica en varias fechas.':''}</div></div>
      <div class="panel wide" style="margin-top:1.2rem"><h3>Cobertura · lo que queda por fuera</h3>
        <div style="font-size:.74rem;color:var(--ink2);line-height:1.6">
          De ${fmt(c.n_votaciones)} votaciones registradas se analizan <b>${fmt(c.n_analizadas)}</b>:
          se descartan ${fmt(c.n_descartadas_repetido)} donde alguien aparece votando dos veces${c.n_descartadas_sin_quorum?`, ${fmt(c.n_descartadas_sin_quorum)} con menos de ${c.min_votantes} votantes (actas parseadas a medias, no plenarias)`:''}${c.n_descartadas_duplicado?` y ${fmt(c.n_descartadas_duplicado)} que la fuente republica con la misma lista exacta de votos en otras fechas`:''}.
          De esas, <b>${fmt(c.n_contestadas)}</b> (${c.pct_contestadas}%) están contestadas: las unánimes se excluyen porque ahí todas las bancadas dan cohesión perfecta y el número deja de medir disciplina.
          <br><br>El <b>${c.pct_sin_partido}%</b> de los votos llega sin partido en la fuente y otro tanto pertenece a partidos que no forman bancada propia —organizaciones CITREP de un solo representante, coaliciones, movimientos pequeños—: entre unos y otros, el <b>${c.pct_no_asignado}%</b> de los votos queda fuera de estas cifras. No se les inventa una bancada ni se reparten entre las existentes.
        </div>
        <div style="margin-top:.8rem;line-height:2">${cob}</div>
        <div class="cob-note">Fuente: ${esc(d.fuente||'')}.</div></div>`;
    el.querySelectorAll('.banc-dis').forEach(x=>x.onclick=()=>abrirCongresista(x.dataset.k));
  }
  function bancSync(){ document.querySelectorAll('#banc-cam .chip').forEach(c=>c.classList.toggle('on',c.dataset.cam===BANC_CAM)); }
  // ═══ COALICIONES · quién vota con quién ═══════════════════════════════
  // Mide la coincidencia entre las MAYORÍAS de dos bancadas, solo en votaciones
  // de fondo contestadas. El orden de las filas y los bloques NO están escritos
  // a mano: los deriva el build agrupando por similitud, y van por periodo
  // porque el realineamiento de 2022 mueve pares hasta 62 pp — promediar las dos
  // eras fabrica un bloque que nunca existió.
  let COA_DATA=null, COA_PER='petro', _coaInited=false;
  // escala: rojo (discrepan) → gris (mitad y mitad) → azul (votan juntas)
  function coaColor(p){
    if(p==null) return null;
    const t=Math.max(0,Math.min(1,(p-10)/80));
    return t<.5 ? `rgba(239,68,68,${(.20+(.5-t)*1.5).toFixed(2)})`
                : `rgba(152,192,248,${(.20+(t-.5)*1.5).toFixed(2)})`;
  }
  function coaCell(m,a,b){
    const v=m[`${a}|${b}`]||m[`${b}|${a}`];
    return v?{pct:v.pct,n:v.n}:null;
  }
  function coaRender(){
    const el=document.getElementById('coa-body'); if(!el||!COA_DATA) return;
    const c=COA_DATA.camara||{}, sen=COA_DATA.senado||{};
    if(!c.medible){ el.innerHTML='<div class="err">Sin datos de coalición.</div>'; return; }
    const p=(c.periodos||{})[COA_PER]||{}, orden=p.orden||[], m=p.matriz||{};
    const cob=c.cobertura||{};
    // matriz
    const head=`<tr><th></th>${orden.map(b=>`<th class="c" style="color:${pcolor(b)}">${esc(b)}</th>`).join('')}</tr>`;
    const filas=orden.map(a=>`<tr><th class="r" style="color:${pcolor(a)}">${esc(a)}</th>${orden.map(b=>{
      if(a===b) return '<td class="coa-c self">—</td>';
      const v=coaCell(m,a,b);
      if(!v) return '<td class="coa-c na" title="Menos votaciones compartidas de las que exige la vista">·</td>';
      return `<td class="coa-c" style="background:${coaColor(v.pct)}" title="${esc(a)} y ${esc(b)} votaron igual en ${v.pct}% de ${v.n} votaciones de fondo">${v.pct}</td>`;
    }).join('')}</tr>`).join('');
    // bloques
    const blk=(p.bloques||[]).map(b=>`<div class="coa-b"><div class="h">${b.length>1?`Bloque · ${b.length} bancadas`:'Suelta'}</div>
      <div class="m">${b.map(x=>`<span style="color:${pcolor(x)}">${esc(x)}</span>`).join('')}</div></div>`).join('');
    // realineamiento: cambio entre las dos eras
    const re=(c.realineamiento||[]).filter(r=>Math.abs(r.cambio)>=10);
    const mx=Math.max(70,...re.map(r=>Math.abs(r.cambio)));
    const reH=re.map(r=>{
      const w=Math.abs(r.cambio)/mx*50, pos=r.cambio>=0;
      return `<div class="coa-r">
        <span class="coa-par"><span style="color:${pcolor(r.a)}">${esc(r.a)}</span> — <span style="color:${pcolor(r.b)}">${esc(r.b)}</span></span>
        <span class="coa-ch"><u></u><i style="${pos?'left:50%':`right:50%`};width:${w}%;background:${pos?'var(--green)':'var(--red)'}"></i></span>
        <span class="coa-d">${r.duque}% → <b style="color:${pos?'var(--green)':'var(--red)'}">${r.petro}%</b> (${r.cambio>0?'+':''}${r.cambio})</span>
      </div>`;}).join('');
    const exc=(c.excluidas||[]);
    const faltan=exc.length?[...new Set(exc.map(x=>x.par.split('|')).reduce((a,b)=>a.filter(v=>b.includes(v)),exc[0].par.split('|')))]:[];
    el.innerHTML=`
      <div class="cob-note" style="margin:0 0 1rem;font-size:.72rem;color:var(--ink2);line-height:1.5">
        <b style="color:var(--ink)">${esc(c.nombre||'')}</b> · ${esc(p.etiqueta||'')} · <b>${fmt(p.n_votaciones)}</b> votaciones de fondo contestadas.
        Dos bancadas «coinciden» cuando la mayoría de una vota lo mismo que la mayoría de la otra.</div>
      <div class="panel wide"><h3>Coincidencia entre bancadas · ${esc(p.etiqueta||'')}</h3>
        <div class="coa-wrap"><table class="coa-m">${head}${filas}</table></div>
        <div class="coa-blk">${blk}</div>
        <div class="cob-note"><b>El orden de las filas no está escrito a mano</b>: las bancadas se agrupan por parecido en su voto y el recorrido de ese árbol las deja contiguas. Que salga un eje reconocible es un hallazgo del dato, no un supuesto de entrada. Un <b>bloque</b> exige que <b>todos</b> sus pares coincidan al menos ${Math.round((cob.corte_bloque||.6)*100)}% entre sí — con el promedio en vez del mínimo, el grupo encadena y mete bancadas que discrepan en la mitad de las votaciones. Las celdas «·» son pares con menos de ${cob.min_par||25} votaciones compartidas: no se publican.</div></div>
      ${reH?`<div class="panel wide" style="margin-top:1.2rem"><h3>Qué se rompió y qué se juntó al cambiar el gobierno</h3>
        ${reH}
        <div class="cob-note">Coincidencia bajo Duque (hasta ago-2022) contra la de Petro, en los pares con al menos ${cob.min_par||25} votaciones compartidas <b>en cada era</b>. Solo se listan cambios de 10 puntos o más.${faltan.length?` <b>${faltan.map(esc).join(', ')} no aparece</b>: no era bancada propia antes de 2022 —eran Colombia Humana, Polo y MAIS, con muy pocos representantes— así que no hay periodo anterior contra el cual comparar. Su ausencia aquí no significa que no se moviera.`:''}</div></div>`:''}
      <div class="panel wide" style="margin-top:1.2rem"><h3>Cobertura · qué entra y qué no</h3>
        <div style="font-size:.74rem;color:var(--ink2);line-height:1.6">
          Entran <b>${fmt(cob.n_votaciones_fondo)}</b> votaciones: las que <b>deciden el proyecto</b> —ponencia, articulado, título, conciliación, aplazamiento y archivo— y además están <b>contestadas</b>.
          Se descartan ${fmt((cob.descartes||{}).no_fondo||0)} que no deciden el proyecto (sobre todo impedimentos, donde la bancada se suelta por rutina), ${fmt((cob.descartes||{}).unanime||0)} unánimes —si todos votan igual, dos bancadas cualesquiera coinciden sin ser aliadas—, ${fmt((cob.descartes||{}).sin_quorum||0)} sin quórum y ${fmt((cob.descartes||{}).repetido||0)} donde alguien aparece votando dos veces.
          Una bancada partida por la mitad exacta no tiene mayoría que comparar y esa votación no entra a sus pares.
          <br><br><b>El Senado no se puede medir aquí.</b> ${esc(sen.motivo||'')}
        </div>
        <div class="cob-note">Fuente: ${esc((COA_DATA.meta||{}).fuente||'')}.</div></div>`;
  }
  function coaSync(){ document.querySelectorAll('#coa-per .chip').forEach(c=>c.classList.toggle('on',c.dataset.per===COA_PER)); }
  async function coaLoad(){
    const el=document.getElementById('coa-body'); if(!el) return;
    if(!_coaInited){
      _coaInited=true;
      const cont=document.getElementById('coa-per');
      if(cont) [['petro','Gobierno Petro'],['duque','Gobierno Duque'],['todo','Todo el periodo']].forEach(([k,t])=>{
        const b=document.createElement('span'); b.className='chip'; b.dataset.per=k; b.textContent=t;
        b.onclick=()=>{ COA_PER=k; coaSync(); coaRender(); }; cont.appendChild(b);
      });
      coaSync();
    }
    if(COA_DATA) return coaRender();
    el.innerHTML='<div class="llm-load" style="padding:1.4rem">Cargando coaliciones <span class="dots"><span></span><span></span><span></span></span></div>';
    let d; try{ d=await call({action:'coaliciones'}); }catch(e){ el.innerHTML='<div class="err">No se pudo cargar. Reintenta.</div>'; return; }
    COA_DATA=d; if(d&&d.camara&&d.camara.periodo_default) { COA_PER=d.camara.periodo_default; coaSync(); }
    coaRender();
  }

  async function bancLoad(){
    const el=document.getElementById('banc-body'); if(!el) return;
    if(!_bancInited){
      _bancInited=true;
      const cont=document.getElementById('banc-cam');
      if(cont) [['camara','Cámara de Representantes'],['senado','Senado']].forEach(([k,t])=>{
        const c=document.createElement('span'); c.className='chip'; c.dataset.cam=k; c.textContent=t;
        c.onclick=()=>{ BANC_CAM=k; bancSync(); bancRender(); }; cont.appendChild(c); });
      bancSync();
    }
    if(BANC_DATA){ bancRender(); return; }
    el.innerHTML='<div class="llm-load" style="padding:2rem;justify-content:center">Cargando disciplina de bancada <span class="dots"><span></span><span></span><span></span></span></div>';
    let d; try{ d=await call({action:'bancadas'}); }catch(e){ el.innerHTML='<div class="err">No se pudo cargar. Reintenta.</div>'; return; }
    BANC_DATA=d; bancRender();
  }

  /* Los tres hooks que caudal-base.js llama al entrar a cada vista. */
  Object.assign(window, { controlLoad, bancLoad, coaLoad });
})();
