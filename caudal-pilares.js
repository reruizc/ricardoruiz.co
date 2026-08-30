/* caudal-pilares.js — los pilares que se consultan uno a uno
   ------------------------------------------------------------------
   Cinco vistas: Congreso (la búsqueda por tema, que es el pilar más
   viejo y por eso no lleva prefijo), Regulatorio, Ejecutivo, Medios y
   Contratación. Cada una trae su estado, su landing, su búsqueda y su
   cableado; entre ellas casi no se hablan, y lo poco que comparten
   (`empresaHint`, `_ampliarEmp`) vive acá dentro.

   Fuera de este archivo: los helpers de formato y muro (`esc`, `fmt`,
   `cortar`, `listaConMuro`, los mapas de color) y la ficha del modal
   (`abrirProyecto`, `abrirCongresista`) siguen en el <script> inline de
   caudal.html, y la búsqueda universal de allá entra acá a llamar los
   `*Buscar`/`*Card`/`*Init` de cada pilar. Todo eso resuelve contra
   `window`, así que el orden de carga no importa: nada de esto corre
   antes de que los dos scripts estén evaluados.

   ⚠️ Al tocar este archivo hay que bumpear el ?v= del <script> que lo
   carga en caudal.html, o el navegador sirve la copia vieja. */
(function(){
  'use strict';

  /* ---------- pilar Regulatorio · sanciones ---------- */

  const REG={sector:'', q:'', tipoActo:'sancion'};
  const REG_SECS=[['','Todos'],['salud','Salud'],['contratacion','Contratación'],['financiero','Financiero'],['ambiental','Ambiental'],['transporte','Transporte'],['consumo','Consumo'],['juridico','Jurídico'],['control','Control fiscal']];
  /* tipo de acto (reencuadre jul-2026). El default es 'sancion' a propósito:
     abrir el pilar en "todo" diluiría la vista que hoy usa el cliente. */
  const REG_TIPOS=[['sancion','Sanciones'],['todo','Toda la actividad regulatoria'],
    ['apertura_investigacion','Investigaciones'],['archivo','Archivos'],
    ['contribucion_especial','Contribución especial'],['resolucion','Resoluciones'],['circular','Circulares']];
  /* [singular, plural] — explícito: la pluralización del español no se infiere
     con una regla de sufijo ("apertura de investigación" → "aperturas de…"). */
  const TIPO_ACTO_TXT={
    sancion:['sanción','sanciones'],
    apertura_investigacion:['apertura de investigación','aperturas de investigación'],
    archivo:['archivo','archivos y exoneraciones'],
    contribucion_especial:['acto de contribución especial','actos de contribución especial'],
    resolucion:['resolución','resoluciones'], circular:['circular','circulares'],
    otro:['acto administrativo','actos administrativos'],
    todo:['acto regulatorio','actos regulatorios']};
  /* rótulo del contador: solo dice "sanciones" cuando lo son de verdad. */
  function regNoun(n, tipo){
    const t=TIPO_ACTO_TXT[tipo]||TIPO_ACTO_TXT.otro;
    return n===1?t[0]:t[1];
  }
  let REG_STATS=null, _regInited=false, _regSeq=0;
  function fmtCOP(n){ if(!n||n<=0) return ''; if(n>=1e12) return '$'+(n/1e12).toFixed(1).replace('.',',')+' B'; if(n>=1e6) return '$'+fmt(Math.round(n/1e6))+' M'; return '$'+fmt(Math.round(n)); }
  function sancCard(r){
    const mot=(r.motivo||'').replace(/\s+/g,' ').replace(/^[IVX]+\.\s*/,'').trim();
    const monto=r.monto?`<span class="sanc-monto">${fmtCOP(r.monto)}</span> · `:'';
    const tipo=r.tipo?`<span class="doc-badge">${esc(r.tipo)}</span>`:'';
    /* cuando el acto NO es sanción hay que decirlo en la card: si no, una
       contribución especial se lee como una multa. */
    const ta=r.tipo_acto||'sancion';
    const taBadge=ta==='sancion'?'':`<span class="doc-badge pal">${esc((TIPO_ACTO_TXT[ta]||TIPO_ACTO_TXT.otro)[0])}</span>`;
    const name=r.url
      ?`<a class="sanc-name" href="${esc(r.url)}" target="_blank" rel="noopener" style="color:inherit">${esc(r.sancionado)}</a>`
      :`<span class="sanc-name">${esc(r.sancionado)}</span>`;
    return `<div class="sanc">
      <div class="sanc-top">${name}<span class="sanc-fecha">${esc(r.fecha||'')}</span></div>
      ${mot?`<div class="sanc-motivo">${esc(mot)}</div>`:''}
      <div class="sanc-tags">${taBadge}<span class="doc-badge pal">${esc(r.fuente_nombre||r.fuente)}</span>${tipo}${monto}${r.resolucion?'Res. '+esc(r.resolucion):''}${r.url?` · <a href="${esc(r.url)}" target="_blank" rel="noopener" style="color:var(--ink3)">comunicado ↗</a>`:''}</div>
    </div>`;
  }
  function regRenderLanding(s){
    const el=document.getElementById('reg-landing'); if(!el||!s) return;
    const monto=(s.monto||{}).total_cop;
    const rango=s.rango_fechas&&s.rango_fechas[0]?`${s.rango_fechas[0].slice(0,4)}–${s.rango_fechas[1].slice(0,4)}`:'—';
    /* los KPI son de SANCIONES (lo que el pilar muestra por defecto). El
       universo de actos va como nota aparte, no mezclado en el total. */
    const otros=(s.total_actos||0)-(s.total||0);
    el.innerHTML=`
      <div class="land-h">Los actos del Estado en números · esquema común</div>
      <div class="kpis">
        <div class="kpi"><div class="n">${fmt(s.total)}</div><div class="l">Sanciones</div></div>
        <div class="kpi"><div class="n">${(s.por_fuente||[]).length}</div><div class="l">Fuentes</div></div>
        <div class="kpi"><div class="n" style="color:var(--amber)">${fmtCOP(monto)||'—'}</div><div class="l">Monto reportado</div></div>
        <div class="kpi"><div class="n">${rango}</div><div class="l">Periodo</div></div>
      </div>
      ${otros>0?`<div class="cob-note" style="margin:.2rem 0 1rem">Además de las sanciones, el pilar registra ${fmt(otros)} ${otros===1?'acto regulatorio':'actos regulatorios'} (investigaciones, archivos, contribuciones, resoluciones). <a href="#" id="reg-landing-todo" style="color:var(--teal)">Ver toda la actividad regulatoria →</a></div>`:''}
      <div class="reg-sectors-grid">
        ${(s.por_sector||[]).map(x=>`<div class="sec-card" data-sec="${esc(x.sector)}"><div class="n">${fmt(x.n)}</div><div class="l">${esc(x.sector_txt||x.sector)}</div></div>`).join('')}
      </div>
      <div class="panel wide"><h3>Sanciones más recientes</h3><div class="sanc-list">${(s.recientes||[]).map(sancCard).join('')}</div></div>`;
    el.querySelectorAll('.sec-card').forEach(c=>c.onclick=()=>{ REG.sector=c.dataset.sec; regSyncSectors(); regBuscar(); });
    const lt=document.getElementById('reg-landing-todo');
    if(lt) lt.onclick=e=>{ e.preventDefault(); REG.tipoActo='todo'; regSyncTipos(); regBuscar(); };
  }
  function regRenderResults(d){
    const el=document.getElementById('reg-results'); if(!el) return;
    el.style.display='block';
    const scope=[d.sector?esc((REG_SECS.find(s=>s[0]===d.sector)||[])[1]||d.sector):'', d.query?`«${esc(d.query)}»`:''].filter(Boolean).join(' · ');
    const ta=d.tipo_acto||'sancion';
    /* si el filtro por defecto dejó actos fuera, se dice cuántos y se ofrece
       el toggle — nunca "resultados que aparecen por magia". */
    const otros=(ta==='sancion'&&d.otros_actos>0)
      ? `<div class="cob-note" style="margin-bottom:1rem">Hay ${fmt(d.otros_actos)} ${d.otros_actos===1?'acto regulatorio más':'actos regulatorios más'} en este alcance (investigaciones, archivos, contribuciones). <a href="#" id="reg-ver-todo" style="color:var(--teal)">Ver toda la actividad regulatoria →</a></div>` : '';
    el.innerHTML=`
      <div class="r-titular" style="font-size:1.4rem">${fmt(d.n)} ${regNoun(d.n, ta)}</div>
      <div class="r-sub" style="margin-bottom:1rem">${scope||'todas las fuentes'}${d.con_monto?` · ${d.con_monto} con monto · <b>${fmtCOP(d.monto_total_cop)}</b> en total`:''}</div>
      ${otros}
      ${d.mostrados<d.n?`<div class="cob-note" style="margin-bottom:1rem">Mostrando ${d.mostrados} de ${fmt(d.n)}, los más recientes. Afina la búsqueda para ver menos.</div>`:''}
      ${listaConMuro(d.resultados, sancCard, 'acto', 'actos', `acceso · ${d.query||d.sector||'regulatorio'}`, 'Sin coincidencias. Prueba otra entidad o sector.')}`;
    const vt=document.getElementById('reg-ver-todo');
    if(vt) vt.onclick=e=>{ e.preventDefault(); REG.tipoActo='todo'; regSyncTipos(); regBuscar(); };
    el.scrollIntoView({behavior:'smooth',block:'start'});
  }
  async function regBuscar(){
    const mine=++_regSeq;
    const el=document.getElementById('reg-results'), landing=document.getElementById('reg-landing');
    if(landing) landing.style.display='none';
    if(el){ el.style.display='block'; el.innerHTML=`<div class="llm-load" style="padding:2rem;justify-content:center">Buscando ${regNoun(2, REG.tipoActo)} <span class="dots"><span></span><span></span><span></span></span></div>`; }
    let d; try{ d=await call({action:'sanciones', query:REG.q, sector:REG.sector, tipo_acto:REG.tipoActo}); }
    catch(e){ if(mine===_regSeq&&el) el.innerHTML='<div class="err">No se pudo consultar. Reintenta.</div>'; return; }
    if(mine!==_regSeq) return;
    regRenderResults(d);
  }
  async function regLoadStats(){
    if(REG_STATS){ regRenderLanding(REG_STATS); return; }
    const el=document.getElementById('reg-landing');
    if(el) el.innerHTML='<div class="llm-load" style="padding:2rem;justify-content:center">Cargando el pilar regulatorio <span class="dots"><span></span><span></span><span></span></span></div>';
    try{ REG_STATS=await call({action:'sanciones'}); }catch(e){ REG_STATS=null; }
    if(REG_STATS) regRenderLanding(REG_STATS);
    else if(el) el.innerHTML='<div class="err">No se pudieron cargar las sanciones. Reintenta.</div>';
  }
  function regShowLanding(){ const r=document.getElementById('reg-results'); if(r) r.style.display='none'; const l=document.getElementById('reg-landing'); if(l) l.style.display='block'; }
  function regSyncSectors(){ document.querySelectorAll('#rsectors .chip').forEach(c=>c.classList.toggle('on',(c.dataset.sec||'')===REG.sector)); }
  function regSyncTipos(){ document.querySelectorAll('#rtipos .chip').forEach(c=>c.classList.toggle('on',(c.dataset.ta||'')===REG.tipoActo)); }
  /* el landing solo aplica al default (sanciones): con cualquier otro tipo hay
     que consultar, porque los agregados precalculados son de sanciones. */
  function regRefrescar(){
    if(!REG.q && !REG.sector && REG.tipoActo==='sancion') regShowLanding();
    else regBuscar();
  }
  function regInit(){
    if(_regInited) return; _regInited=true;
    const rq=document.getElementById('rq'), rgo=document.getElementById('rgo');
    const go=()=>{ REG.q=(rq&&rq.value||'').trim(); regRefrescar(); };
    if(rgo) rgo.onclick=go;
    if(rq) rq.addEventListener('keydown',e=>{ if(e.key==='Enter') go(); });
    const cont=document.getElementById('rsectors');
    if(cont) REG_SECS.forEach(([sec,t])=>{ const c=document.createElement('span'); c.className='chip'+(sec===''?' on':''); c.dataset.sec=sec; c.textContent=t; c.onclick=()=>{ REG.sector=sec; regSyncSectors(); regRefrescar(); }; cont.appendChild(c); });
    const tc=document.getElementById('rtipos');
    if(tc) REG_TIPOS.forEach(([ta,t])=>{ const c=document.createElement('span'); c.className='chip'+(ta===REG.tipoActo?' on':''); c.dataset.ta=ta; c.textContent=t; c.onclick=()=>{ REG.tipoActo=ta; regSyncTipos(); regRefrescar(); }; tc.appendChild(c); });
    const rb=document.getElementById('regBack'); if(rb) rb.onclick=()=>showView('home');
  }
  /* ---------- pilar Ejecutivo Nacional · decretos y normativa ---------- */
  const EJE={tipo:'', q:''};
  const EJE_TIPOS=[['','Todas'],['DECRETOS','Decretos'],['RESOLUCIONES','Resoluciones'],['DIRECTIVAS','Directivas'],['CIRCULARES','Circulares'],['ACTOS LEGISLATIVOS','Actos legislativos'],['AGENDA REGULATORIA','Agenda regulatoria'],['LEYES','Leyes']];
  const EJE_TSING={'DECRETOS':'Decreto','LEYES':'Ley','RESOLUCIONES':'Resolución','DIRECTIVAS':'Directiva','CIRCULARES':'Circular','ACTOS LEGISLATIVOS':'Acto legislativo','AGENDA REGULATORIA':'Agenda regulatoria','RESOLUCIONES DE NOMBRAMIENTOS':'Nombramiento','CONPES':'CONPES','CONSTITUCIÓN POLÍTICA':'Constitución','DECRETO ÚNICO REGLAMENTARIO':'Decreto Único'};
  let EJE_STATS=null, _ejeInited=false, _ejeSeq=0;
  function ejeSing(t){ return EJE_TSING[t]||(t?t.charAt(0)+t.slice(1).toLowerCase():'—'); }
  function ejeTitle(t){ return t?t.charAt(0)+t.slice(1).toLowerCase():'—'; }
  function ejeCard(r){
    const nombre=ejeSing(r.tipo)+(r.numero?(' '+r.numero):'')+(r.anio?(' de '+r.anio):'');
    const desc=(r.descripcion||'').replace(/\s+/g,' ').replace(/^["“]|["”]$/g,'').trim();
    const href=r.url?encodeURI(r.url):'';
    const name=href
      ?`<a class="sanc-name" href="${esc(href)}" target="_blank" rel="noopener" style="color:inherit">${esc(nombre)}</a>`
      :`<span class="sanc-name">${esc(nombre)}</span>`;
    return `<div class="sanc">
      <div class="sanc-top">${name}<span class="sanc-fecha">${esc(r.fecha||'')}</span></div>
      ${desc?`<div class="sanc-motivo">${esc(desc)}</div>`:''}
      <div class="sanc-tags"><span class="doc-badge pal">${esc(ejeSing(r.tipo))}</span>${href?` · <a href="${esc(href)}" target="_blank" rel="noopener" style="color:var(--ink3)">texto oficial ↗</a>`:''}</div>
    </div>`;
  }
  function ejeRenderLanding(s){
    const el=document.getElementById('eje-landing'); if(!el||!s) return;
    const dec=((s.por_tipo||[]).find(x=>x.tipo==='DECRETOS')||{}).n||0;
    const rango=s.rango_fechas&&s.rango_fechas[0]?`${s.rango_fechas[0].slice(0,4)}–${s.rango_fechas[1].slice(0,4)}`:'—';
    const frec=(s.fuente||{}).frecuencia||'—';
    el.innerHTML=`
      <div class="land-h">La normativa del Ejecutivo en números · Presidencia de la República</div>
      <div class="kpis">
        <div class="kpi"><div class="n">${fmt(dec)}</div><div class="l">Decretos</div></div>
        <div class="kpi"><div class="n">${fmt(s.total)}</div><div class="l">Normas en total</div></div>
        <div class="kpi"><div class="n">${rango}</div><div class="l">Periodo</div></div>
        <div class="kpi"><div class="n" style="color:var(--teal)">${esc(frec)}</div><div class="l">Actualización</div></div>
      </div>
      <div class="reg-sectors-grid">
        ${(s.por_tipo||[]).filter(x=>x.n>=5).map(x=>`<div class="sec-card" data-tipo="${esc(x.tipo)}"><div class="n">${fmt(x.n)}</div><div class="l">${esc(ejeTitle(x.tipo))}</div></div>`).join('')}
      </div>
      <div class="panel wide"><h3>Lo último publicado</h3><div class="sanc-list">${(s.recientes||[]).map(ejeCard).join('')}</div></div>`;
    el.querySelectorAll('.sec-card').forEach(c=>c.onclick=()=>{ EJE.tipo=c.dataset.tipo; ejeSyncTipos(); ejeBuscar(); });
  }
  function ejeRenderResults(d){
    const el=document.getElementById('eje-results'); if(!el) return;
    el.style.display='block';
    const scope=[d.tipo?esc(ejeTitle(d.tipo)):'', d.query?`«${esc(d.query)}»`:''].filter(Boolean).join(' · ');
    el.innerHTML=`
      <div class="r-titular" style="font-size:1.4rem">${fmt(d.n)} ${d.n===1?'norma':'normas'}</div>
      <div class="r-sub" style="margin-bottom:1rem">${scope||'toda la normativa'}</div>
      ${d.mostrados<d.n?`<div class="cob-note" style="margin-bottom:1rem">Mostrando las ${d.mostrados} más recientes de ${fmt(d.n)}. Afina la búsqueda para ver menos.</div>`:''}
      ${listaConMuro(d.resultados, ejeCard, 'norma', 'normas', `acceso · ${d.query||d.tipo||'ejecutivo'}`, 'Sin coincidencias. Prueba otro término o tipo.')}`;
    el.scrollIntoView({behavior:'smooth',block:'start'});
  }
  async function ejeBuscar(){
    const mine=++_ejeSeq;
    const el=document.getElementById('eje-results'), landing=document.getElementById('eje-landing');
    if(landing) landing.style.display='none';
    if(el){ el.style.display='block'; el.innerHTML='<div class="llm-load" style="padding:2rem;justify-content:center">Buscando normativa <span class="dots"><span></span><span></span><span></span></span></div>'; }
    let d; try{ d=await call({action:'ejecutivo', query:EJE.q, tipo:EJE.tipo}); }
    catch(e){ if(mine===_ejeSeq&&el) el.innerHTML='<div class="err">No se pudo consultar. Reintenta.</div>'; return; }
    if(mine!==_ejeSeq) return;
    ejeRenderResults(d);
  }
  async function ejeLoadStats(){
    if(EJE_STATS){ ejeRenderLanding(EJE_STATS); return; }
    const el=document.getElementById('eje-landing');
    if(el) el.innerHTML='<div class="llm-load" style="padding:2rem;justify-content:center">Cargando el pilar ejecutivo <span class="dots"><span></span><span></span><span></span></span></div>';
    try{ EJE_STATS=await call({action:'ejecutivo'}); }catch(e){ EJE_STATS=null; }
    if(EJE_STATS) ejeRenderLanding(EJE_STATS);
    else if(el) el.innerHTML='<div class="err">No se pudo cargar la normativa. Reintenta.</div>';
  }
  function ejeShowLanding(){ const r=document.getElementById('eje-results'); if(r) r.style.display='none'; const l=document.getElementById('eje-landing'); if(l) l.style.display='block'; }
  function ejeSyncTipos(){ document.querySelectorAll('#etipos .chip').forEach(c=>c.classList.toggle('on',(c.dataset.tipo||'')===EJE.tipo)); }
  function ejeInit(){
    if(_ejeInited) return; _ejeInited=true;
    const eq=document.getElementById('eq'), ego=document.getElementById('ego');
    const go=()=>{ EJE.q=(eq&&eq.value||'').trim(); if(!EJE.q&&!EJE.tipo) ejeShowLanding(); else ejeBuscar(); };
    if(ego) ego.onclick=go;
    if(eq) eq.addEventListener('keydown',e=>{ if(e.key==='Enter') go(); });
    const cont=document.getElementById('etipos');
    if(cont) EJE_TIPOS.forEach(([tp,t])=>{ const c=document.createElement('span'); c.className='chip'+(tp===''?' on':''); c.dataset.tipo=tp; c.textContent=t; c.onclick=()=>{ EJE.tipo=tp; ejeSyncTipos(); if(!EJE.q&&!EJE.tipo) ejeShowLanding(); else ejeBuscar(); }; cont.appendChild(c); });
    const eb=document.getElementById('ejeBack'); if(eb) eb.onclick=()=>showView('home');
  }

  /* ---------- pilar Datos abiertos y contratación · SECOP II ---------- */
  const CON={q:'', filtros:{}, solo:false, orden:'reciente', tab:'contratos', _last:null};
  const CON_EJEMPLOS=['interventoría vías','dotación hospitalaria','alimentación escolar','carrotanques','comando conjunto caribe'];
  let CON_STATS=null, _conInited=false, _conSeq=0;
  function conCard(r){
    const fin=r.fecha_fin&&r.fecha_fin!==r.fecha?` · termina ${esc(r.fecha_fin)}`:'';
    const name=r.url
      ?`<a class="sanc-name" href="${esc(r.url)}" target="_blank" rel="noopener" style="color:inherit">${esc(r.entidad||'—')}</a>`
      :`<span class="sanc-name">${esc(r.entidad||'—')}</span>`;
    // el badge "matchea por" explica el ruido de $q: SECOP indexa TODAS las
    // columnas, así que un contrato puede salir por su sector o su tipo de
    // documento aunque el objeto no nombre el término buscado.
    const match=r.match&&r.match!=='Objeto'?`<span class="doc-badge">match: ${esc(r.match)}</span>`:'';
    const dond=[r.ciudad,r.departamento].filter(Boolean).join(', ');
    return `<div class="sanc">
      <div class="sanc-top">${name}<span class="sanc-fecha">${esc(r.fecha||'sin fecha')}</span></div>
      ${r.objeto?`<div class="sanc-motivo">${esc(r.objeto.slice(0,300))}${r.objeto.length>300?'…':''}</div>`:''}
      <div class="sanc-tags">
        ${r.valor?`<span class="sanc-monto">${fmtCOP(r.valor)}</span> · `:''}${esc(r.proveedor||'—')}
        ${dond?` · ${esc(dond)}`:''}${fin}
        ${r.modalidad?` · <span class="doc-badge pal">${esc(r.modalidad)}</span>`:''}${match}
        ${r.url?` · <a href="${esc(r.url)}" target="_blank" rel="noopener" style="color:var(--ink3)">proceso en SECOP ↗</a>`:''}
      </div>
    </div>`;
  }
  function conRenderLanding(s){
    const el=document.getElementById('con-landing'); if(!el||!s) return;
    const t=s.total||{};
    const anios=(s.por_anio||[]).filter(x=>/^\d{4}$/.test(x.anio)).slice(0,8);
    const frec=(s.fuente||{}).frecuencia||'—';
    el.innerHTML=`
      <div class="land-h">La contratación pública en números · SECOP II</div>
      <div class="kpis">
        <div class="kpi"><div class="n">${fmt(t.contratos||0)}</div><div class="l">Contratos</div></div>
        <div class="kpi"><div class="n" style="color:var(--amber)">${fmtCOP(s.mediana_cop)||'—'}</div><div class="l">Contrato mediano</div></div>
        <div class="kpi"><div class="n">${(s.por_departamento||[]).length}</div><div class="l">Departamentos</div></div>
        <div class="kpi"><div class="n" style="color:var(--teal)">${esc(frec)}</div><div class="l">Actualización</div></div>
      </div>
      <div class="panel wide"><h3>Contratos por año de firma</h3>
        <div class="reg-sectors-grid">${anios.map(x=>`<div class="sec-card" data-anio="${esc(x.anio)}"><div class="n">${fmt(x.n)}</div><div class="l">${esc(x.anio)}</div></div>`).join('')}</div>
      </div>
      <div class="panel wide"><h3>Por sector</h3>
        <div class="reg-sectors-grid">${(s.por_sector||[]).slice(0,10).map(x=>`<div class="sec-card" data-sector="${esc(x.sector)}"><div class="n">${fmt(x.n)}</div><div class="l">${esc(x.sector)}</div></div>`).join('')}</div>
      </div>
      <div class="panel wide"><h3>Entidades que más contratan (por número de contratos)</h3>
        <div class="cob-note" style="margin-bottom:.7rem">Se cuentan contratos, no pesos: la columna de valor de SECOP trae errores de digitación que ponían a una universidad técnica encabezando la contratación del país con una cifra mayor que el PIB mundial.</div>
        <div class="reg-sectors-grid">${(s.top_entidades_n||[]).slice(0,8).map(x=>`<div class="sec-card" data-entidad="${esc(x.entidad)}"><div class="n">${fmt(x.n)}</div><div class="l">${esc(x.entidad)}</div></div>`).join('')}</div>
      </div>
      ${s.nota?`<div class="cob-note">${esc(s.nota)}</div>`:''}`;
    el.querySelectorAll('.sec-card').forEach(c=>c.onclick=()=>{
      const d=c.dataset;
      CON.filtros={};
      if(d.anio) CON.filtros.anio=d.anio;
      if(d.sector) CON.filtros.sector=d.sector;
      if(d.entidad) CON.filtros.entidad=d.entidad;
      conBuscar();
    });
  }
  // ② y ③ · bloque de coincidencia exacta por radicado.
  // Nace del caso PAF-MENIES-O-134-2024 (ago-2026): el cliente llega con un
  // número en la mano, la búsqueda por $q mira SOLO contratos, y ese contrato
  // vive únicamente como proceso (régimen especial de patrimonio autónomo).
  // Resultado viejo: "sin coincidencias", que se lee como "no existe".
  const ADJ_TONO={adjudicado:'var(--teal)', adjudicado_sin_contrato:'#e0a33e', no_informa:'var(--ink3)'};
  function identAdj(a){
    if(!a) return '';
    // ③ NUNCA se repite el campo `adjudicado` como si fuera verdad: el estado
    // sale del cruce contra el dataset de contratos por id_del_portafolio.
    const col=ADJ_TONO[a.estado]||'var(--ink3)';
    const det=a.estado==='adjudicado'
      ? `${a.n_contratos} ${a.n_contratos===1?'contrato firmado':'contratos firmados'} en el dataset de contratos.`
      : a.estado==='adjudicado_sin_contrato'
        ? 'La fuente lo da por adjudicado pero no hay contrato electrónico publicado — en régimen especial el contrato suele ir como documento adjunto al proceso.'
        : 'El cruce contra el dataset de contratos no encontró contrato. Eso <b>no</b> quiere decir que no se adjudicó.';
    const desm=a.campo_desmentido
      ? `<div class="cob-note" style="margin:.45rem 0 0">⚠️ El campo <code>adjudicado</code> de la fuente dice <b>«${esc(a.campo_fuente||'—')}»</b> y sí hay contrato firmado. El campo está errado, no el cruce.</div>`
      : '';
    const cont=(a.contratos||[]).length
      ? `<div style="margin-top:.6rem">${a.contratos.map(conCard).join('')}</div>` : '';
    return `<div style="margin-top:.7rem;padding-left:.7rem;border-left:2px solid ${col}">
        <div style="font-weight:600;color:${col}">${esc(a.etiqueta||'')}</div>
        <div class="cob-note" style="margin:.25rem 0 0">${det}</div>
        ${desm}
        <details style="margin-top:.45rem"><summary style="cursor:pointer;color:var(--ink3);font-size:.86rem">Por qué no mostramos el campo tal cual</summary>
          <div class="cob-note" style="margin-top:.4rem">${esc(a.nota||'')}</div></details>
        ${cont}
      </div>`;
  }
  function identProcCard(p){
    const dond=[p.ciudad,p.departamento].filter(Boolean).join(', ');
    const name=p.url
      ?`<a class="sanc-name" href="${esc(p.url)}" target="_blank" rel="noopener" style="color:inherit">${esc(p.entidad||'—')}</a>`
      :`<span class="sanc-name">${esc(p.entidad||'—')}</span>`;
    return `<div class="sanc">
      <div class="sanc-top">${name}<span class="sanc-fecha">${esc(p.fecha_publicacion||'sin fecha')}</span></div>
      ${p.objeto?`<div class="sanc-motivo">${esc(p.objeto.slice(0,300))}${p.objeto.length>300?'…':''}</div>`:''}
      <div class="sanc-tags">
        ${p.valor_base?`<span class="sanc-monto">${fmtCOP(p.valor_base)}</span> <span style="color:var(--ink3)">(precio base)</span> · `:''}${esc(p.referencia||'—')}
        ${dond?` · ${esc(dond)}`:''}${p.duracion?` · ${esc(p.duracion)}`:''}
        ${p.modalidad?` · <span class="doc-badge pal">${esc(p.modalidad)}</span>`:''}
        ${p.url?` · <a href="${esc(p.url)}" target="_blank" rel="noopener" style="color:var(--ink3)">proceso en SECOP ↗</a>`:''}
      </div>
      ${identAdj(p.adjudicacion)}
    </div>`;
  }
  function identBlock(d){
    const x=d&&d.identificador; if(!x) return '';
    // el aviso que evita el falso "no existe": $q solo mira contratos.
    const solo=x.solo_proceso
      ? `<div class="cob-note" style="margin:.2rem 0 .9rem">Este radicado existe como <b>proceso</b> pero no tiene contrato electrónico publicado — es lo normal en el régimen especial de los patrimonios autónomos, donde el contrato va como documento adjunto. La búsqueda de abajo mira solo el dataset de contratos, por eso sale vacía: <b>«sin resultados» ahí significa «no está en ese dataset», no «no existe»</b>.</div>`
      : '';
    const amb=x.ambiguo
      ? `<div class="cob-note" style="margin:.2rem 0 .9rem">⚠️ Ese número no es único en SECOP: cada entidad numera por su cuenta. Se muestran las ${fmt(x.n_contratos+x.n_procesos)} coincidencias — revisa la entidad para saber cuál es la tuya.</div>`
      : '';
    return `<div class="panel wide" style="border-color:var(--teal);margin-bottom:1.4rem">
      <h3 style="margin-bottom:.3rem">Coincidencia exacta por radicado</h3>
      <div class="cob-note" style="margin-bottom:.9rem">Búsqueda por igualdad de <code>${esc(x.consulta)}</code> sobre contratos y procesos, no por texto libre.</div>
      ${solo}${amb}
      ${x.n_contratos?`<div style="font-weight:600;margin:.4rem 0 .5rem">${fmt(x.n_contratos)} ${x.n_contratos===1?'contrato':'contratos'}</div>${x.contratos.map(conCard).join('')}`:''}
      ${x.n_procesos?`<div style="font-weight:600;margin:1rem 0 .5rem">${fmt(x.n_procesos)} ${x.n_procesos===1?'proceso':'procesos'} <span style="color:var(--ink3);font-weight:400">· el proceso se publica antes que el contrato: es donde todavía se puede incidir</span></div>${x.procesos.map(identProcCard).join('')}`:''}
    </div>`;
  }
  // Procesos (p6dx-8zbt) en la lista. Van en PESTAÑA aparte, nunca fusionados
  // con los contratos: un proceso y el contrato que sale de él son la MISMA
  // contratación, así que sumarlos duplicaría, y sus campos no son comparables
  // (precio base ≠ valor firmado, fecha de publicación ≠ fecha de firma).
  function procCard(r){
    const a=r.adjudicacion||{};
    const col=ADJ_TONO[a.estado]||'var(--ink3)';
    const name=r.url
      ?`<a class="sanc-name" href="${esc(r.url)}" target="_blank" rel="noopener" style="color:inherit">${esc(r.entidad||'—')}</a>`
      :`<span class="sanc-name">${esc(r.entidad||'—')}</span>`;
    const dond=[r.ciudad,r.departamento].filter(Boolean).join(', ');
    // ③ el estado sale del cruce contra contratos, jamás del campo `adjudicado`
    const est=a.etiqueta?`<span class="doc-badge" style="border-color:${col};color:${col}">${esc(a.etiqueta)}</span>`:'';
    const desm=a.campo_desmentido?`<span class="doc-badge" style="border-color:#e0a33e;color:#e0a33e" title="El campo adjudicado de la fuente dice «${esc(a.campo_fuente||'')}» y sí hay contrato">campo errado</span>`:'';
    return `<div class="sanc">
      <div class="sanc-top">${name}<span class="sanc-fecha">${esc(r.fecha_publicacion||'sin fecha')}</span></div>
      ${r.objeto?`<div class="sanc-motivo">${esc(r.objeto.slice(0,300))}${r.objeto.length>300?'…':''}</div>`:''}
      <div class="sanc-tags">
        ${r.valor_base?`<span class="sanc-monto">${fmtCOP(r.valor_base)}</span> <span style="color:var(--ink3)">precio base</span> · `:''}${esc(r.referencia||'—')}
        ${r.proveedor?` · ${esc(r.proveedor)}`:''}${dond?` · ${esc(dond)}`:''}${r.duracion?` · ${esc(r.duracion)}`:''}
        ${r.modalidad?` · <span class="doc-badge pal">${esc(r.modalidad)}</span>`:''}
        ${est}${desm}
        ${r.url?` · <a href="${esc(r.url)}" target="_blank" rel="noopener" style="color:var(--ink3)">ver en SECOP ↗</a>`:''}
      </div>
    </div>`;
  }
  function conTabs(d){
    const p=d.procesos;
    // sin procesos no hay pestaña que ofrecer: una pestaña vacía es ruido
    if(!p&&!d.procesos_tarde) return '';
    const nC=(d.total&&d.total.contratos)!=null?d.total.contratos:(d.n||0);
    const nP=p?(p.total!=null?p.total:p.n):null;
    if(d.procesos_tarde&&!p)
      return `<div class="cob-note" style="margin-bottom:1rem">Los <b>procesos</b> de esta búsqueda no alcanzaron a cargar. Los contratos de abajo están completos; vuelve a buscar si quieres los procesos.</div>`;
    return `<div class="chips" style="margin-bottom:1rem">
      <span class="chip${CON.tab!=='procesos'?' on':''}" data-tab="contratos">Contratos <b>${fmt(nC)}</b></span>
      <span class="chip${CON.tab==='procesos'?' on':''}" data-tab="procesos">Procesos <b>${fmt(nP)}</b></span>
    </div>`;
  }
  function conProcBloque(d){
    const p=d.procesos; if(!p) return '';
    const ign=(p.filtros_ignorados||[]).length
      ? `<div class="cob-note" style="margin-bottom:1rem">⚠️ ${(p.filtros_ignorados||[]).map(x=>`<b>${esc(x)}</b>`).join(' y ')} no ${p.filtros_ignorados.length>1?'existen':'existe'} en el registro de procesos: ese filtro <b>no</b> está aplicado acá. El conteo de arriba es sin él.</div>`
      : '';
    const idn=p.por_identidad&&(p.entidades||[]).length
      ? `<div class="cob-note" style="margin-bottom:1rem">Entidades incluidas: ${p.entidades.slice(0,4).map(e=>`<b>${esc(e.nombre)}</b>`).join(' · ')}${/\.$/.test(p.entidades[0].nombre||'')?'':'.'}${p.nota_proveedor?` ${esc(p.nota_proveedor)}`:''}</div>`
      : (p.nota_proveedor?`<div class="cob-note" style="margin-bottom:1rem">${esc(p.nota_proveedor)}</div>`:'');
    return `
      <div class="cob-note" style="margin-bottom:1rem">El proceso se publica <b>antes</b> que el contrato: acá la contratación todavía se puede pelear. ${esc(p.nota_adjudicado||'')}</div>
      ${ign}${idn}
      ${(p.por_departamento||[]).length>1?`<div class="cob-note" style="margin-bottom:1rem">Dónde está: ${(p.por_departamento||[]).slice(0,6).map(x=>`${esc(x.departamento)} (${fmt(x.n)})`).join(' · ')}</div>`:''}
      ${listaConMuro(p.resultados, procCard, 'proceso', 'procesos', `acceso · ${d.query||'contratación'}`,
        'Sin procesos para esta búsqueda.')}
      ${p.total>p.n?`<div class="cob-note" style="margin-top:1rem">Mostrando ${fmt(p.n)} de ${fmt(p.total)}.</div>`:''}`;
  }
  function conRenderResults(d){
    const el=document.getElementById('con-results'); if(!el) return;
    el.style.display='block';
    CON._last=d;                       // cambiar de pestaña no repite la consulta
    if(!d.procesos) CON.tab='contratos';   // sin procesos no hay dónde estar
    const f=d.filtros||{};
    const scope=[d.query?`«${esc(d.query)}»`:'', f.entidad?esc(f.entidad):'', f.sector?esc(f.sector):'',
                 f.departamento?esc(f.departamento):'', f.anio?esc(String(f.anio)):''].filter(Boolean).join(' · ');
    const tot=d.total;
    // ② Si el radicado se encontró pero el universo $q está vacío (el caso
    // PAF-MENIES: el contrato solo existe como proceso), el titular NO puede
    // gritar «0 contratos» encima de un hallazgo real — es la misma lectura
    // equivocada que este camino existe para evitar.
    const _ix=d.identificador, _n=w=>fmt(w);
    const identSolo=_ix&&(!tot||!tot.contratos);
    const titular=identSolo
      ? [_ix.n_contratos?`${_n(_ix.n_contratos)} ${_ix.n_contratos===1?'contrato':'contratos'}`:'',
         _ix.n_procesos?`${_n(_ix.n_procesos)} ${_ix.n_procesos===1?'proceso':'procesos'}`:''].filter(Boolean).join(' · ')
      : (tot?`${fmt(tot.contratos)} ${tot.contratos===1?'contrato':'contratos'}`:`${fmt(d.n)} contratos`);
    // ⚠️ NO se publica la suma de `valor_del_contrato`. Medido ago-2026: esa
    // columna de SECOP trae errores de digitación de hasta 12 órdenes de
    // magnitud —un contrato del CNE figura con 6,86e18 pesos y él solo era el
    // 99,2% del total de su búsqueda— y no hay umbral limpio donde cortar (a 1
    // billón todavía aparece un centro de salud rural con 9,9 billones). Sumar
    // una columna rota no se arregla con un tope. El conteo sí es fiable.
    const valor='';
    const chips=(d.chips||[]).length?`<div class="cob-note" style="margin-bottom:1rem">
        ¿Buscabas el filtro exacto? ${(d.chips||[]).map(c=>`<a href="#" class="con-chip" data-campo="${esc(c.campo)}" data-valor="${esc(c.valor)}" style="color:var(--teal)">${esc(c.etiqueta)}: ${esc(c.valor)} (${fmt(c.n)})</a>`).join(' · ')}
        — filtra sin el ruido del texto libre.</div>`:'';
    const solo=d.solo_objeto?`<div class="cob-note" style="margin-bottom:1rem">Precisión activa: de los ${fmt(d.revisadas||0)} contratos más recientes de esta búsqueda, ${fmt(d.n)} nombran la frase en el <b>objeto</b>. El total de arriba es el universo completo.</div>`:'';
    // ④ con qué nombres exactos se contó: el usuario tiene que poder auditar
    // que "los contratos de Claro" son de COMCEL S.A. y no de un homónimo.
    const nomb=[...(d.proveedores||[]).map(x=>[x,'proveedor']),...(d.entidades||[]).map(x=>[x,'entidad contratante'])];
    const ident=d.identidad_empresa&&nomb.length?`<div class="cob-note" style="margin-bottom:1rem">
        Razones sociales incluidas: ${nomb.slice(0,6).map(([x,rol])=>`<b>${esc(x.nombre)}</b> <span style="color:var(--ink3)">(${fmt(x.n)} · ${rol})</span>`).join(' · ')}${nomb.length>6?` <span style="color:var(--ink3)">y ${nomb.length-6} más</span>`:''}${d.n_descartados?` — se descartaron ${fmt(d.n_descartados)} nombres que solo <i>contienen</i> la marca (${(d.descartados||[]).slice(0,2).map(x=>esc(x.nombre)).join(', ')}…).`:'.'}
        ${d.truncado?' <b>Nota:</b> hay más razones sociales de las que caben en una consulta; el total puede quedarse corto.':''}</div>`:'';
    el.innerHTML=`
      <div class="r-titular" style="font-size:1.4rem">${titular}</div>
      <div class="r-sub" style="margin-bottom:1rem">${scope||'toda la contratación'}${valor}${identSolo?' · encontrado por radicado exacto':''}</div>
      ${empresaHint(d.empresas,'con-emp-hint','contratacion')}
      ${identBlock(d)}
      ${ident}${chips}${solo}
      ${conTabs(d)}
      <div class="chips" style="margin-bottom:1rem">
        <span class="chip${CON.orden==='reciente'?' on':''}" data-orden="reciente">Más recientes</span>
        <span class="chip${CON.orden==='valor'?' on':''}" data-orden="valor">Más caros</span>
        ${d.query&&!d.identidad_empresa&&CON.tab!=='procesos'?`<span class="chip${CON.solo?' on':''}" data-solo="1">Solo en el objeto</span>`:''}
        ${Object.keys(f).length?'<span class="chip" data-clear="1">✕ Quitar filtros</span>':''}
      </div>
      ${CON.tab==='procesos'?conProcBloque(d):`
      ${(d.por_departamento||[]).length>1?`<div class="cob-note" style="margin-bottom:1rem">Dónde está: ${(d.por_departamento||[]).slice(0,6).map(x=>`${esc(x.departamento)} (${fmt(x.n)})`).join(' · ')}</div>`:''}
      ${listaConMuro(d.resultados, conCard, 'contrato', 'contratos', `acceso · ${d.query||'contratación'}`,
        d.sin_contratos
          ? `<b>${esc((d.empresas&&d.empresas[0]&&d.empresas[0].nombre)||d.query)}</b> no le vende al Estado por SECOP II: no hay ninguna razón social suya entre los proveedores.${d.n_descartados?` Sí aparecen ${fmt(d.n_descartados)} nombres que <i>contienen</i> la marca (${(d.descartados||[]).slice(0,3).map(x=>esc(x.nombre)).join(', ')}…), pero son homónimos, no la empresa.`:''} Usa el enlace de arriba si quieres verlos igual.`
          : (d.identificador
             ? `Sin coincidencias <b>en el dataset de contratos</b> — pero el radicado sí existe: lo tienes arriba.`
             : `Sin coincidencias.${Object.keys(f).length?' Hay filtros activos ('+esc(Object.values(f).join(' · '))+'): quítalos arriba y vuelve a buscar.':' Prueba otro término — recuerda que varias palabras se combinan con Y.'}`))}
      ${tot&&tot.contratos>d.n?`<div class="cob-note" style="margin-top:1rem">Mostrando ${fmt(d.n)} de ${fmt(tot.contratos)}. Afina con un filtro para ver menos.</div>`:''}`}`;
    wireEmpresaHint('con-emp-hint', conBuscar);
    el.querySelectorAll('.chip[data-tab]').forEach(c=>c.onclick=()=>{
      CON.tab=c.dataset.tab; if(CON._last) conRenderResults(CON._last); });
    el.querySelectorAll('.chip[data-orden]').forEach(c=>c.onclick=()=>{ CON.orden=c.dataset.orden; conBuscar(); });
    el.querySelectorAll('.chip[data-solo]').forEach(c=>c.onclick=()=>{ CON.solo=!CON.solo; conBuscar(); });
    el.querySelectorAll('.chip[data-clear]').forEach(c=>c.onclick=()=>{ CON.filtros={}; conBuscar(); });
    el.querySelectorAll('.con-chip').forEach(a=>a.onclick=(e)=>{
      e.preventDefault();
      const campo=a.dataset.campo, valor=a.dataset.valor;
      const MAP={departamento:'departamento', estado_contrato:'estado', modalidad_de_contratacion:'modalidad',
                 tipo_de_contrato:'tipo', sector:'sector', orden:'orden_entidad'};
      if(MAP[campo]){ CON.filtros={[MAP[campo]]:valor}; CON.q=''; const i=document.getElementById('conq'); if(i) i.value=''; conBuscar(); }
    });
    el.scrollIntoView({behavior:'smooth',block:'start'});
  }
  async function conBuscar(){
    const mine=++_conSeq;
    const el=document.getElementById('con-results'), landing=document.getElementById('con-landing');
    if(landing) landing.style.display='none';
    if(el){ el.style.display='block'; el.innerHTML='<div class="llm-load" style="padding:2rem;justify-content:center">Consultando SECOP en vivo <span class="dots"><span></span><span></span><span></span></span></div>'; }
    let d; try{ d=await call(Object.assign({action:'contratacion', query:CON.q, limit:50,
                                            orden:CON.orden, solo_objeto:CON.solo,
                                            ampliar_empresa:_ampliarEmp}, CON.filtros)); }
    catch(e){ if(mine===_conSeq&&el) el.innerHTML='<div class="err">No se pudo consultar SECOP. Reintenta.</div>'; return; }
    if(mine!==_conSeq) return;
    if(d&&d.error){ if(el) el.innerHTML=`<div class="err">${esc(d.error)}</div>`; return; }
    // si no hay contratos pero sí procesos, abrir en procesos: es el caso
    // PAF-MENIES generalizado — mandar a una lista vacía cuando el hallazgo está
    // en la otra pestaña es el mismo falso negativo que venimos corrigiendo.
    const nP=d.procesos?(d.procesos.total!=null?d.procesos.total:d.procesos.n):0;
    if(!(d.total&&d.total.contratos)&&!d.n&&nP) CON.tab='procesos';
    conRenderResults(d);
  }
  async function conLoadStats(){
    if(CON_STATS){ conRenderLanding(CON_STATS); return; }
    const el=document.getElementById('con-landing');
    if(el) el.innerHTML='<div class="llm-load" style="padding:2rem;justify-content:center">Cargando el pilar de contratación <span class="dots"><span></span><span></span><span></span></span></div>';
    try{ CON_STATS=await call({action:'contratacion'}); }catch(e){ CON_STATS=null; }
    if(CON_STATS) conRenderLanding(CON_STATS);
    else if(el) el.innerHTML='<div class="err">No se pudo cargar la contratación. Reintenta.</div>';
  }
  function conShowLanding(){ const r=document.getElementById('con-results'); if(r) r.style.display='none'; const l=document.getElementById('con-landing'); if(l) l.style.display='block'; }
  function conInit(){
    if(_conInited) return; _conInited=true;
    // ⚠️ ids propios (`conq`/`congo`): este buscador y el de congresistas usaban
    // los MISMOS `cq`/`cgo`, y como getElementById devuelve el primero del DOM,
    // este pilar leía la caja de congresistas — escribías acá y no buscaba nada.
    const cq=document.getElementById('conq'), cgo=document.getElementById('congo');
    const go=()=>{ CON.q=(cq&&cq.value||'').trim(); if(!CON.q&&!Object.keys(CON.filtros).length) conShowLanding(); else conBuscar(); };
    if(cgo) cgo.onclick=go;
    if(cq) cq.addEventListener('keydown',e=>{ if(e.key==='Enter') go(); });
    const cont=document.getElementById('cchips');
    if(cont) CON_EJEMPLOS.forEach(t=>{ const c=document.createElement('span'); c.className='chip'; c.textContent=t; c.onclick=()=>{ if(cq) cq.value=t; CON.q=t; CON.filtros={}; conBuscar(); }; cont.appendChild(c); });
    const cb=document.getElementById('conBack'); if(cb) cb.onclick=()=>showView('home');
  }
  /* ---------- pilar Medios · prensa nacional y regional ---------- */
  const MED={q:''};
  const MED_EJEMPLOS=['reforma tributaria','presupuesto general 2027','trámites empresariales','energía eléctrica','inteligencia artificial','transporte de carga'];
  let MED_STATS=null, _medInited=false, _medSeq=0;
  function medAlcanceBadge(a){ return a==='regional' ? '<span class="doc-badge pal">Regional</span>' : '<span class="doc-badge">Nacional</span>'; }
  function medHeadCard(r){
    return `<div class="sanc">
      <div class="sanc-top"><a class="sanc-name" href="${esc(r.url)}" target="_blank" rel="noopener" style="color:inherit;text-decoration:none">${esc(r.titulo)}</a><span class="sanc-fecha">${esc(r.fecha||'')}</span></div>
      <div class="sanc-tags"><span class="doc-badge">${esc(r.medio)}</span>${medAlcanceBadge(r.alcance)}</div>
    </div>`;
  }
  function medRenderLanding(s){
    const el=document.getElementById('med-landing'); if(!el||!s) return;
    const alc=Object.fromEntries((s.por_alcance||[]).map(x=>[x.alcance,x.n]));
    el.innerHTML=`
      <div class="land-h">Pulso de prensa política · últimos días</div>
      <div class="kpis">
        <div class="kpi"><div class="n">${fmt(s.n)}</div><div class="l">Titulares</div></div>
        <div class="kpi"><div class="n">${fmt(s.n_medios)}</div><div class="l">Medios distintos</div></div>
        <div class="kpi"><div class="n">${fmt(alc.nacional||0)}</div><div class="l">Nacional</div></div>
        <div class="kpi"><div class="n">${fmt(alc.regional||0)}</div><div class="l">Regional</div></div>
      </div>
      <div class="panel wide"><h3>Titulares recientes</h3><div class="sanc-list">${(s.resultados||[]).map(medHeadCard).join('')||'<div class="cob-note">Sin titulares en la ventana.</div>'}</div></div>
      <div class="cob-note" style="text-align:center;margin-top:1rem">Fuente: Google News (gl=CO) — cubre el ecosistema de prensa nacional y regional sin conectores por medio.</div>`;
  }
  function medRenderResults(d){
    const el=document.getElementById('med-results'); if(!el) return;
    el.style.display='block';
    const alc=Object.fromEntries((d.por_alcance||[]).map(x=>[x.alcance,x.n]));
    el.innerHTML=`
      <div class="r-titular" style="font-size:1.4rem">${d.n} ${d.n===1?'titular':'titulares'}</div>
      <div class="r-sub" style="margin-bottom:1rem">«${esc(d.query)}» · últimos ${d.dias} días · ${alc.nacional||0} nacional · ${alc.regional||0} regional</div>
      ${listaConMuro(d.resultados, medHeadCard, 'titular', 'titulares', `acceso · ${d.query||'prensa'}`, 'Sin cobertura de prensa reciente para este tema.')}`;
    el.scrollIntoView({behavior:'smooth',block:'start'});
  }
  async function medBuscar(){
    const mine=++_medSeq;
    const el=document.getElementById('med-results'), landing=document.getElementById('med-landing');
    if(landing) landing.style.display='none';
    if(el){ el.style.display='block'; el.innerHTML='<div class="llm-load" style="padding:2rem;justify-content:center">Rastreando prensa <span class="dots"><span></span><span></span><span></span></span></div>'; }
    let d; try{ d=await call({action:'medios', query:MED.q}); }
    catch(e){ if(mine===_medSeq&&el) el.innerHTML='<div class="err">No se pudo consultar. Reintenta.</div>'; return; }
    if(mine!==_medSeq) return;
    medRenderResults(d);
  }
  async function medLoadLanding(){
    if(MED_STATS){ medRenderLanding(MED_STATS); return; }
    const el=document.getElementById('med-landing');
    if(el) el.innerHTML='<div class="llm-load" style="padding:2rem;justify-content:center">Cargando el pulso de prensa <span class="dots"><span></span><span></span><span></span></span></div>';
    try{ MED_STATS=await call({action:'medios'}); }catch(e){ MED_STATS=null; }
    if(MED_STATS) medRenderLanding(MED_STATS);
    else if(el) el.innerHTML='<div class="err">No se pudo cargar la prensa. Reintenta.</div>';
  }
  function medShowLanding(){ const r=document.getElementById('med-results'); if(r) r.style.display='none'; const l=document.getElementById('med-landing'); if(l) l.style.display='block'; }
  function medInit(){
    if(_medInited) return; _medInited=true;
    const mq=document.getElementById('mq'), mgo=document.getElementById('mgo');
    const go=()=>{ MED.q=(mq&&mq.value||'').trim(); if(!MED.q) medShowLanding(); else medBuscar(); };
    if(mgo) mgo.onclick=go;
    if(mq) mq.addEventListener('keydown',e=>{ if(e.key==='Enter') go(); });
    const mc=document.getElementById('mchips');
    if(mc) MED_EJEMPLOS.forEach(t=>{ const ch=document.createElement('span'); ch.className='chip'; ch.textContent=t; ch.onclick=()=>{ mq.value=t; MED.q=t; medBuscar(); }; mc.appendChild(ch); });
    const mb=document.getElementById('medBack'); if(mb) mb.onclick=()=>showView('home');
  }


  /* ---------- búsqueda ---------- */
  const EJEMPLOS=['reforma tributaria','presupuesto general 2027','trámites empresariales','energía eléctrica','salud y medicamentos','inteligencia artificial','datos personales','transporte de carga'];
  // Guardas de nodo ausente: al salir de caudal.html este archivo no puede dar
  // por hecho su DOM, y un getElementById en null se llevaría por delante el
  // resto del módulo sin dejar rastro (la lección de legislativo-base.js).
  const chips=document.getElementById('chips');
  if(chips) EJEMPLOS.forEach(t=>{const c=document.createElement('span'); c.className='chip'; c.textContent=t; c.onclick=()=>{q.value=t; buscar();}; chips.appendChild(c);});
  const q=document.getElementById('q'), results=document.getElementById('results');
  const go=document.getElementById('go'); if(go) go.onclick=buscar;
  if(q) q.addEventListener('keydown',e=>{if(e.key==='Enter') buscar();});
  const cq=document.getElementById('cq');
  const cbuscar=()=>{ const v=(cq&&cq.value||'').trim(); if(v) abrirCongresista(v); };
  const cgo=document.getElementById('cgo'); if(cgo) cgo.onclick=cbuscar;
  if(cq) cq.addEventListener('keydown',e=>{if(e.key==='Enter') cbuscar();});

  let _seq=0;
  // ④ estado del tema actual (para el switch de estadísticas sin re-consultar)
  let _statMode='titulo', _temaR=null, _temaQ=''; let _lecturaData=null; const _snipCache={};
  /* ④ Traductor marca → tema. El usuario buscó «Uber» y le salen proyectos que
     dicen "plataformas tecnológicas": tiene que ver POR QUÉ. Mismo principio que
     el aviso de sinónimos y el de búsqueda flexible — nada aparece por magia.
     `ampliado` alterna núcleo (preciso, por defecto) ↔ núcleo + contexto. */
  /* Global por la misma razón que STATS: lo alterna el enlace «ampliar» de acá
     y lo lee la búsqueda universal, que vive en caudal.html. */
  window._ampliarEmp=false;
  function empresaHint(emps, id, modo){
    if(!emps||!emps.length) return '';
    const e=emps[0], esGremio=e.tipo==='gremio';
    // En CONTRATACIÓN el diccionario juega su otra cara: acá la empresa sí
    // aparece con nombre propio (es el proveedor), así que no se traduce a
    // tema — se filtra por identidad. Ampliar = ver todo lo que menciona la
    // marca, con los homónimos que eso arrastra.
    if(modo==='contratacion'){
      const mas=` <span class="bd-link" id="${id}-mas">${_ampliarEmp?'volver a solo sus contratos':'ampliar: ver todo lo que menciona «'+esc(e.nombre)+'»'} →</span>`;
      return `<div class="broaden" id="${id}"><b>${esc(e.nombre)}</b> ${esGremio?'es un gremio':'es una empresa'} del diccionario de Caudal.
        ${_ampliarEmp
          ? 'Estás viendo <b>todo lo que menciona su nombre</b> en SECOP — incluye homónimos (en Colombia hay personas que se apellidan así).'
          : 'Se filtró por <b>identidad del proveedor</b>: son los contratos que <b>son de la empresa</b>, no los que nombran la marca.'}${mas}</div>`;
    }
    const nuc=(e.nucleo||[]).map(esc).join(' · ');
    const ctx=(e.contexto||[]);
    const mas=ctx.length
      ? ` <span class="bd-link" id="${id}-mas">${_ampliarEmp?'volver a lo esencial':'ampliar a: '+ctx.map(esc).join(' · ')} →</span>`
      : '';
    return `<div class="broaden" id="${id}"><b>${esc(e.nombre)}</b> ${esGremio?'es un gremio':'es una empresa'} del diccionario de Caudal.
      El Estado no legisla marcas, legisla actividades — así que se buscó por: <b>${nuc}</b>${_ampliarEmp&&ctx.length?' · '+ctx.map(esc).join(' · '):''}.${mas}</div>`;
  }
  function wireEmpresaHint(id, rerun){
    const el=document.getElementById(id+'-mas'); if(!el) return;
    el.onclick=()=>{ _ampliarEmp=!_ampliarEmp; rerun(); };
  }

  async function buscar(){
    const query=q.value.trim(); if(!query) return;
    const mine=++_seq;
    _statMode='titulo'; _temaR=null; _lecturaData=null; Object.keys(_snipCache).forEach(k=>delete _snipCache[k]);
    const landing=document.getElementById('landing'); if(landing) landing.style.display='none';
    results.style.display='block';
    results.innerHTML='<div class="llm-load" style="padding:2rem;justify-content:center">Consultando el histórico <span class="dots"><span></span><span></span><span></span></span></div>';
    results.scrollIntoView({behavior:'smooth',block:'start'});
    let data;
    try{ data=await call({action:'tema',query,lectura:false,ampliar_empresa:_ampliarEmp}); }
    catch(e){ if(mine===_seq) results.innerHTML='<div class="err">No se pudo consultar. Reintenta.</div>'; return; }
    if(mine!==_seq) return;
    const r=data.resumen;
    if(!r||!(r.intentos||[]).length){ results.innerHTML=`<div class="err">Sin resultados para «${esc(query)}». Prueba otra palabra (tributaria, energía eléctrica, datos personales…).</div>`; return; }
    _temaR=r; _temaQ=query;
    renderResumen(query,r);
    // Sin acceso ni se pide: la Lambda la degradaría igual (devuelve
    // `lectura_bloqueada` sin llamar al modelo), pero en su lugar va el muro y no
    // tiene sentido gastar la petición.
    if(ACCESO){
      // `tema` con lectura ya NO genera: prepara y devuelve la llave. Si la
      // lectura ya estaba hecha viene en la misma respuesta y no se sondea nada.
      call({action:'tema',query,lectura:true}).then(d2=>{
        if(mine!==_seq) return;
        if(d2 && d2.lectura){ _lecturaData=d2.lectura; renderLectura(d2.lectura); return; }
        if(d2 && d2.lectura_key) pedirLecturaTema(d2.lectura_key, mine);
        else lecturaTemaFallback();
      }).catch(()=>lecturaTemaFallback());
    }
  }

  /* ---------- lectura del tema: disparo + sondeo ----------
     Generar tarda 20-51 s (la varianza es del modelo) y el API Gateway corta a
     los 30: pedirla de una devolvía 503 al primero que buscaba un tema nuevo.
     Es el mismo patrón del radar del cliente. */
  const TEMA_LECT_POLL=3500, TEMA_LECT_MAX=90000;
  let _temaLectTimer=null;
  function lecturaTemaStop(){ if(_temaLectTimer){ clearTimeout(_temaLectTimer); _temaLectTimer=null; } }
  function lecturaTemaFallback(msg){
    const el=document.getElementById('lectura-body'); if(!el) return;
    el.innerHTML='<div class="cob-note">'+esc(msg||'No se pudo generar la lectura. Los datos de arriba están completos.')+'</div>';
  }
  function pedirLecturaTema(key, mine){
    lecturaTemaStop();
    const t0=Date.now();
    const listo=d=>{
      if(mine!==_seq || !d || d.estado!=='lista' || !d.lectura || d.lectura.error) return false;
      lecturaTemaStop(); _lecturaData=d.lectura; renderLectura(d.lectura); return true;
    };
    // 1 · disparo: arranca la generación. Puede morir en el gateway a los 30 s
    //     y no pasa nada — la Lambda termina y deja la lectura en el caché.
    call({action:'tema-lectura',key}).then(d=>{
      if(mine!==_seq || listo(d)) return;
      if(d && d.estado==='sin_tema'){ lecturaTemaStop(); return lecturaTemaFallback('La lectura caducó. Vuelve a buscar el tema para regenerarla.'); }
      if(d && d.estado==='lista'){ lecturaTemaStop(); lecturaTemaFallback(); }   // respondió mal: no se cachea
    }).catch(()=>{});
    // 2 · sondeo del caché en paralelo
    const tick=()=>{
      if(mine!==_seq) return lecturaTemaStop();
      if(Date.now()-t0>TEMA_LECT_MAX){ lecturaTemaStop(); return lecturaTemaFallback(); }
      if(Date.now()-t0>12000){
        const el=document.getElementById('lectura-body');
        if(el && !el.dataset.slow){ el.dataset.slow='1'; el.innerHTML='<div class="llm-load">La primera lectura de un tema tarda un poco más <span class="dots"><span></span><span></span><span></span></span></div>'; }
      }
      call({action:'tema-lectura',key,solo_cache:true})
        .then(d=>{ if(!listo(d)) _temaLectTimer=setTimeout(tick,TEMA_LECT_POLL); })
        .catch(()=>{ if(mine===_seq) _temaLectTimer=setTimeout(tick,TEMA_LECT_POLL); });
    };
    _temaLectTimer=setTimeout(tick,TEMA_LECT_POLL);
  }

  async function profundizar(query,mine){
    const btn=document.getElementById('btn-profundizar');
    const casosEl=document.getElementById('lectura-casos');
    if(btn){ btn.disabled=true; btn.textContent='Leyendo ponencias y actas… puede tardar 20-40s'; }
    let d;
    try{ d=await call({action:'tema',query,lectura:true,profundo:true}); }
    catch(e){
      if(btn){ btn.disabled=false; btn.textContent='◈ Profundizar con evidencia de gacetas (lee ponencias/actas reales · más lento)'; }
      return;
    }
    if(mine!==_seq) return;
    // `tema` ya no genera en línea: si la lectura profunda no vino hecha, se
    // recoge con el mismo disparo+sondeo. Los casos se pintan cuando llegue.
    if(d.lectura){ _lecturaData=d.lectura; renderLectura(d.lectura); }
    else if(d.lectura_key){
      pedirLecturaTema(d.lectura_key, mine);
      if(btn) btn.remove();
      return;                     // los casos los trae la lectura al llegar
    }
    const casos=(d.lectura&&d.lectura.casos_evidencia)||[];
    if(casosEl){
      casosEl.innerHTML = casos.length
        ? `<div class="tag" style="margin-top:.8rem">◈ Casos con evidencia real de gaceta (${casos.length})</div>` +
          casos.map(c=>`<div class="blk"><div class="h">[${c.anio}] ${esc((c.titulo||'').slice(0,80))} — Gaceta ${esc(c.gaceta)}${c.tipo_doc?' · '+esc(c.tipo_doc.replace(/_/g,' ')):''}</div>
            <div class="t">${c.sentido?`Sentido: <b>${esc(c.sentido)}</b>. `:''}${esc(c.sentido_detalle||'')}${c.en_contra?` — Oposición/archivo: ${esc(c.en_contra)}`:''}</div></div>`).join('')
        : `<div class="cob-note" style="margin-top:.6rem">Ninguno de los proyectos más relevantes de este tema tiene su gaceta digitalizada todavía — la cosecha de texto prioriza lo más reciente y sigue en curso. Reintenta en un rato.</div>`;
    }
    if(btn) btn.remove();
  }

  function fillSnip(key,s){
    const el=results.querySelector(`#texto-list .snip[data-key="${key}"]`); if(!el) return;
    if(s&&s.snippet){
      let h=esc(s.snippet);
      if(s.match){ const m=esc(s.match); if(m) h=h.split(m).join('<b class="snip-hi">'+m+'</b>'); }
      el.innerHTML=h;
    } else { el.innerHTML='<span class="snip-none">fragmento no disponible (gaceta aún no cosechada)</span>'; }
  }
  // ④ trae los fragmentos del cuerpo de gaceta para los match ◈ "en el texto".
  // Cachea en _snipCache → el switch de estadísticas re-renderiza sin re-pedir.
  async function loadSnippets(query, txtInt){
    const rows=(txtInt||[]).slice(0,50);   // cap: 50 fragmentos por búsqueda
    if(!rows.length) return;
    const missing=[];
    rows.forEach(it=>{ const key=(it.tb||'pdly')+':'+it.id; if(_snipCache[key]!==undefined) fillSnip(key,_snipCache[key]); else missing.push(it); });
    if(!missing.length) return;
    const ids=missing.map(it=>({id:it.id, tb:it.tb||'pdly'}));
    let d; try{ d=await call({action:'snippets', query, ids, max:50}); }catch(e){ return; }
    (d.snippets||[]).forEach(s=>{ const key=(s.tb||'pdly')+':'+s.id; _snipCache[key]=s; fillSnip(key,s); });
    missing.forEach(it=>{ const key=(it.tb||'pdly')+':'+it.id; if(_snipCache[key]===undefined){ _snipCache[key]=null; fillSnip(key,null); } });
  }

  function renderResumen(query,r){
    const intentos=r.intentos||[];
    // ④ split: la palabra en el TÍTULO (radicado o alias) vs solo en el CUERPO de
    // la gaceta (◈). Los de texto van en su propia sección, cada uno con el fragmento.
    const titInt=intentos.filter(it=>!it.match_texto);
    const txtInt=intentos.filter(it=>it.match_texto);
    // ④ switch de estadísticas: por DEFECTO solo título (los proyectos reales del
    // tema); 'todos' incluye los que solo lo mencionan en el texto (con su ruido de
    // citas/boletines). Si no hay ninguno con la palabra en el título, cae a 'todos'.
    const mode=(_statMode==='titulo' && titInt.length===0)?'todos':_statMode;
    const S=(mode==='todos')?(r.stats_todos||r):r;
    const chartInt=(mode==='todos')?intentos:titInt;
    const cob=S.cobertura_partido||{con:0,sin:0}; const cobTot=cob.con+cob.sin;
    const emb=S.embudo||{};
    const bmax=(S.bancadas&&S.bancadas[0]&&S.bancadas[0][1])||1;
    const banc=(S.bancadas||[]).map(([p,n])=>{
      const c=pcolor(p);
      return `<div class="banc-row"><span class="banc-dot" style="background:${c}"></span><span class="banc-name" title="${esc(p)}">${esc(p)}</span><span class="banc-bar"><span style="width:${100*n/bmax}%;background:${c}"></span></span><span class="banc-n">${n}</span></div>`;
    }).join('');
    const tlRow=(it,inTexto)=>{
      const rc=RES_COLOR[it.resultado]||'var(--gray)';
      const key=(it.tb||'pdly')+':'+it.id;
      return `<div class="tl-item" data-id="${it.id}" data-tb="${it.tb||'pdly'}" data-emp="${it.empuje||''}" data-tip="${it.tipologia||''}" data-mc="${it.mc!=null?it.mc:''}" data-nw="${it.nw!=null?it.nw:''}">
        <span class="tl-year">${it.anio||'—'}</span>
        <div class="tl-body">
          <div class="tl-titulo" title="${esc(it.titulo)}">${esc(shortTitle(it.titulo).slice(0,110))}</div>
          ${inTexto?`<div class="snip" data-key="${key}"><span class="snip-load">buscando el fragmento…</span></div>`:''}
          <div class="tl-tags">
            <span class="doc-badge ${it.tb==='pal'?'pal':''}">${TIPO_DOC[it.tb||'pdly']}</span>
            <span class="tl-res" style="color:${rc};border:1px solid ${rc}33;background:${rc}14">${RES_TXT[it.resultado]||'—'}</span>
            ${it.empuje?`<span class="emp-badge" style="color:${EMP_COLOR[it.empuje]};background:${EMP_COLOR[it.empuje]}14;border:1px solid ${EMP_COLOR[it.empuje]}44" title="${it.empuje==='vitrina'?'Re-radicado sin superar el 1er debate':''}">${EMP_TXT[it.empuje]||''}${it.veces_presentado>1?' '+it.veces_presentado+'×':''}</span>`:''}
            ${it.tipologia&&it.tipologia!=='ordinaria'?`<span class="emp-badge" style="color:${TIP_COLOR[it.tipologia]};background:${TIP_COLOR[it.tipologia]}14;border:1px solid ${TIP_COLOR[it.tipologia]}44">${TIP_TXT[it.tipologia]||''}</span>`:''}
          </div>
        </div>
      </div>`;
    };
    // La línea de intentos es el corazón del pilar: 10 completos para el
    // visitante y el resto detrás del muro, con el conteo real.
    const cT=cortar(titInt), cX=cortar(txtInt);
    const tl=cT.ver.map(it=>tlRow(it,false)).join('')
      + muroLista(cT.fuera, it=>tlRow(it,false), 'proyecto', 'proyectos', `acceso · ${query}`);
    const txtList=cX.ver.map(it=>tlRow(it,true)).join('')
      + muroLista(cX.fuera, it=>tlRow(it,true), 'proyecto', 'proyectos', `acceso · ${query}`);

    // desglose de empuje para la tira de intención (orden fijo)
    const empD=S.empuje||{};
    const empChips=['exitoso','empujado','vitrina','un_debate','sin_traccion']
      .filter(k=>empD[k]).map(k=>`<span class="ichip ichip-f" data-f="emp:${k}"><span class="emp-badge" style="color:${EMP_COLOR[k]};background:${EMP_COLOR[k]}14;border:1px solid ${EMP_COLOR[k]}44">${EMP_TXT[k]}</span><b>${empD[k]}</b></span>`).join('');
    const mortHTML=mortandadChart(STATS&&STATS.mortandad_por_anio_cuatrienio);
    const nAll=(r.n_titulo||0)+(r.n_texto||0);
    // ④ el switch solo tiene sentido si hay match de texto (si no, título==todos)
    const swSwitch=txtInt.length?`<div class="stat-switch">Estadísticas de: <button class="ss-btn${mode==='titulo'?' on':''}" data-m="titulo">solo el título · ${r.n_titulo}</button><button class="ss-btn${mode==='todos'?' on':''}" data-m="todos">título + contenido · ${nAll}</button></div>`:'';

    results.innerHTML=`
      <div class="r-sub">Tema: <b>${esc(query)}</b> · ${S.n_intentos} ${S.n_intentos===1?'proyecto':'proyectos'}${mode==='titulo'?' con la palabra en el título':' (título + contenido)'} · ${S.periodo?S.periodo[0]+'–'+S.periodo[1]:''}</div>
      <div class="r-titular" id="r-titular">${S.n_intentos} ${S.n_intentos===1?'proyecto':'proyectos'} · ${S.n_leyes} ${S.n_leyes===1?'ley':'leyes'} · ${S.pct_exito}% de éxito</div>
      ${swSwitch}
      ${r.flexible?`<div class="broaden" id="flex-hint"><b>Búsqueda flexible</b> · pocas coincidencias con todas tus palabras (<b>${r.flexible.n_estricto}</b>). Mostrando los <b>${r.flexible.n_total}</b> del término más específico: «<b>${esc((r.flexible.anchor||[]).join(', '))}</b>». <span class="bd-link" id="flex-toggle" data-mode="all">ver solo las exactas →</span></div>`:''}
      ${empresaHint(r.empresas,'emp-hint')}
      ${r.sinonimos?`<div class="broaden" id="syn-hint"><b>Búsqueda por tema</b> · el Congreso titula esto de varias formas, así que se incluyen: ${r.sinonimos.incluye.map(esc).join(' · ')}.</div>`:''}
      ${(r.expansion&&r.expansion.terminos&&r.expansion.terminos.length)?`<div class="broaden" id="exp-hint"><b>Búsqueda ampliada</b> · los títulos del Congreso rara vez usan tus palabras, así que también se buscó por: ${r.expansion.terminos.map(esc).join(' · ')}.</div>`:''}

      <div class="kpis">
        <div class="kpi"><div class="n">${S.n_intentos}</div><div class="l">${mode==='titulo'?'Proyectos':'Proyectos + menciones'}</div></div>
        <div class="kpi ley"><div class="n">${S.n_leyes}</div><div class="l">Convertidos en ley</div></div>
        <div class="kpi"><div class="n">${S.n_caidos}</div><div class="l">Caídos</div></div>
        <div class="kpi time"><div class="n">${S.n_muerte_por_tiempo}</div><div class="l">Muertos por tiempo</div></div>
      </div>

      <div class="intencion">
        <span class="ichip ichip-f on" data-f="all">Todos <b>${S.n_intentos}</b></span>
        ${infoIcon(EMP_INFO)}
        ${empChips}
        ${S.n_honores?`<span class="ichip ichip-f" data-f="tip:honores">Honores <b>${S.n_honores}</b></span>`:''}
        ${S.pct_vitrina?`<span class="ichip" style="border:none;color:var(--ink3)">· ${S.pct_vitrina}% de vitrina</span>`:''}
      </div>

      ${ACCESO?`<div class="lectura">
        <div class="tag">◈ Lectura del analista · IA sobre datos oficiales</div>
        <div id="lectura-body"><div class="llm-load">Generando lectura <span class="dots"><span></span><span></span><span></span></span></div></div>
        <button id="btn-profundizar" class="btn-medios" style="margin-top:.6rem">◈ Profundizar con evidencia de gacetas (lee ponencias/actas reales · más lento)</button>
        <div id="lectura-casos"></div>
      </div>`:muroLectura(`acceso · ${query}`)}

      <div class="panel wide" style="margin-bottom:1.2rem"><h3>Embudo del trámite · cómo cae en cada fase ${infoIcon(EMBUDO_INFO)}</h3>${funnel(emb)}</div>

      <div class="charts">
        <div class="panel"><h3>Intentos presentados por año</h3>${yearBars(chartInt)}</div>
        <div class="panel"><h3>Composición del tema</h3>
          <div class="seg-sub">Tipo de proyecto</div>${segBar(S.tipologia,TIP_COLOR,TIP_TXT)}
          <div class="seg-sub">Empuje</div>${segBar(S.empuje,EMP_COLOR,EMP_TXT)}</div>
        <div class="panel"><h3>Éxito por comisión</h3>${comisionChart(chartInt)}</div>
        <div class="panel"><h3>Mortandad por año de cuatrienio</h3><div id="mort-box">${mortHTML}</div></div>
      </div>

      <div class="panel wide" style="margin-bottom:1.2rem"><h3>Bancadas que lo impulsan</h3>${banc||'<div class="cob-note">Sin datos de partido.</div>'}
        <div class="cob-note">Partido identificado en ${cob.con}/${cobTot} intentos (roster Congreso 2014–2026).</div></div>

      ${titInt.length?`<div class="panel"><h3 id="tl-head">${titInt.length} con «${esc(query)}» en el título · click para la ficha</h3><div class="tl tl-scroll" id="tl-timeline">${tl}</div></div>`:''}

      ${txtInt.length?`<div class="panel" style="margin-top:1.2rem"><h3>Además, ${txtInt.length} lo mencionan «${esc(query)}» dentro del texto de su ponencia o acta</h3>
        <div class="cob-note">No lo llevan en el título — el fragmento te deja ver si el proyecto te sirve. Ojo: una gaceta es un boletín con varias ponencias, así que a veces el proyecto trata de otra cosa y solo comparte el documento.</div>
        <div class="tl tl-scroll" id="texto-list" style="max-height:460px">${txtList}</div></div>`:''}
    `;
    requestAnimationFrame(()=>{
      results.querySelectorAll('.f2-bar').forEach(s=>s.style.width=s.dataset.w+'%');
      results.querySelectorAll('.cx-bar>span').forEach(s=>s.style.width=s.dataset.w+'%');
      results.querySelectorAll('.yb-bar').forEach(s=>s.style.height=s.dataset.h+'%');
      results.querySelectorAll('.mort-bar').forEach(s=>s.style.height=s.dataset.h+'%');
    });
    loadStats();   // por si aún no cargó (llena #mort-box cuando resuelva)
    // ojo: los filtros/toggle operan SOLO sobre el timeline de título (no la sección de texto)
    const tlItems=[...results.querySelectorAll('#tl-timeline .tl-item')];
    tlItems.forEach(el=>el.onclick=()=>abrirProyecto(el.dataset.id,el.dataset.tb));
    results.querySelectorAll('#texto-list .tl-item').forEach(el=>el.onclick=()=>abrirProyecto(el.dataset.id,el.dataset.tb));
    loadSnippets(query, txtInt);   // ④ trae los fragmentos del cuerpo de gaceta (lazy)
    // ④ switch de estadísticas (solo título ↔ título+contenido): re-renderiza con
    // el otro set SIN re-consultar (lectura y snippets salen de caché).
    results.querySelectorAll('.ss-btn').forEach(b=>b.onclick=()=>{ if(b.dataset.m===_statMode) return; _statMode=b.dataset.m; renderResumen(_temaQ, _temaR); });
    // btn profundizar cableado aquí (no en buscar) para que el switch lo re-cablee
    const bp=document.getElementById('btn-profundizar'); if(bp) bp.onclick=()=>profundizar(query,_seq);
    // lectura ya cargada (pre-fetch previo o re-render por el switch) → píntala directo
    if(_lecturaData) renderLectura(_lecturaData);
    // filtro clickeable: clasifica los intentos por empuje/tipología
    const tlHead=document.getElementById('tl-head');
    results.querySelectorAll('.ichip-f').forEach(ch=>ch.onclick=()=>{
      results.querySelectorAll('.ichip-f').forEach(x=>x.classList.remove('on'));
      ch.classList.add('on');
      const f=ch.dataset.f; let shown=0;
      tlItems.forEach(it=>{
        let ok=(f==='all');
        if(!ok){ const p=f.split(':'); ok=(p[0]==='emp'?it.dataset.emp===p[1]:it.dataset.tip===p[1]); }
        it.style.display=ok?'':'none'; if(ok) shown++;
      });
      if(tlHead) tlHead.textContent=`${shown} intento(s)${f==='all'?'':' filtrados'} · click para la ficha`;
    });
    // ④ ampliar/reducir el vocabulario de la empresa re-consulta (el núcleo y el
    // contexto son consultas distintas al motor, no un filtro del cliente).
    wireEmpresaHint('emp-hint', buscar);
    // ③ toggle búsqueda flexible: alterna entre TODAS (relajado) y solo las que
    // coinciden con todas las palabras (mc===nw), filtrando el timeline in situ.
    const flexTgl=document.getElementById('flex-toggle');
    if(flexTgl) flexTgl.onclick=()=>{
      const showAll=flexTgl.dataset.mode==='exact';   // si estaba en 'exact' → volver a todas
      let shown=0;
      tlItems.forEach(el=>{
        const mc=el.dataset.mc, nw=el.dataset.nw;
        const exact=(mc!=='' && nw!=='' && mc===nw);
        const ok=showAll||exact;
        el.style.display=ok?'':'none'; if(ok) shown++;
      });
      flexTgl.dataset.mode=showAll?'all':'exact';
      flexTgl.textContent=showAll?'ver solo las exactas →':'ver todas →';
      if(tlHead) tlHead.textContent=`${shown} intento(s)${showAll?'':' · solo exactas'} · click para la ficha`;
      results.querySelectorAll('.ichip-f').forEach(x=>x.classList.toggle('on', x.dataset.f==='all'));
    };
  }

  function renderLectura(l){
    const body=document.getElementById('lectura-body'); if(!body) return;
    const tit=document.getElementById('r-titular');
    if(l.titular && tit) tit.textContent=l.titular;
    const blk=(h,t)=>t?`<div class="blk"><div class="h">${h}</div><div class="t">${esc(t)}</div></div>`:'';
    body.innerHTML=blk('Hallazgo',l.hallazgo)+blk('Por qué se caen',l.por_que_caen)+blk('Quién lo propone',l.quien_propone)+blk('Veredicto',l.veredicto)
      || '<div class="cob-note">Sin lectura disponible.</div>';
  }

  /* ---------- pilar SUCOP · borradores en consulta pública ----------
     Lo que separa a este pilar de los otros seis: su dato VENCE. Toda la UI de
     acá abajo existe para que el cliente no confunda las dos cosas — lo que
     todavía puede comentar (y cuánto le queda) contra lo que ya es archivo. */
  const SUC={estado:'abiertas', q:''};
  const SUC_ESTADOS=[['abiertas','Se puede comentar'],['cierra_pronto','Cierran en ≤7 días'],
                     ['cerrada','Ya cerradas'],['planeacion','Anunciadas, sin fecha'],['','Todas']];
  const SUC_EJEMPLOS=['minería','salud','datos personales','transporte','educación'];
  let SUC_STATS=null, _sucInited=false, _sucSeq=0;
  /* La cuenta regresiva en palabras. Es el corazón del pilar: "cierra hoy" y
     "cerró hace 3 meses" no pueden verse igual. */
  function sucPlazo(r){
    const d=r.dias_restantes, ec=r.estado_consulta;
    if(ec==='cierra_pronto'||ec==='abierta'){
      if(d===0) return ['urge','Cierra hoy'];
      if(d===1) return ['urge','Cierra mañana'];
      return [ec==='cierra_pronto'?'urge':'viva', `Quedan ${d} días`];
    }
    if(ec==='por_abrir') return ['viva', 'Aún no abre'];
    if(ec==='cerrada'){
      const dd=(d==null)?null:Math.abs(d);
      return ['venc', dd==null?'Cerrada':(dd===0?'Cerró hoy':`Cerró hace ${dd} ${dd===1?'día':'días'}`)];
    }
    if(ec==='planeacion') return ['venc','Anunciada, sin fecha'];
    if(ec==='cancelada')  return ['venc','Cancelada'];
    return ['venc','Sin ventana publicada'];
  }
  function sucCard(r){
    const [cls,txt]=sucPlazo(r);
    const viva=(r.estado_consulta==='cierra_pronto'||r.estado_consulta==='abierta');
    // shortTitle quita el «Por medio de la cual se…» — sin eso, un título legal
    // completo ocupa dos líneas subrayadas y entierra de qué trata el borrador,
    // que es lo único que el cliente está leyendo en esta lista.
    const tit=shortTitle((r.titulo||'—').replace(/^["“]|["”]$/g,''))||'—';
    const obj=(r.objeto||'').replace(/\s+/g,' ').trim();
    const href=r.url?encodeURI(r.url):'';
    const name=href
      ?`<a class="sanc-name" href="${esc(href)}" target="_blank" rel="noopener" style="color:inherit">${esc(tit)}</a>`
      :`<span class="sanc-name">${esc(tit)}</span>`;
    // la ventana en crudo, para que el plazo sea auditable y no una afirmación
    const vent=(r.fecha_inicio||r.fecha_fin)?`${esc(r.fecha_inicio||'—')} → ${esc(r.fecha_fin||'—')}`:'';
    return `<div class="sanc${cls==='urge'?' suc-urg':''}">
      <div class="sanc-top">${name}<span class="doc-badge ${cls}">${esc(txt)}</span></div>
      ${obj?`<div class="sanc-motivo">${esc(obj.length>320?obj.slice(0,317)+'…':obj)}</div>`:''}
      <div class="sanc-tags">
        <span class="doc-badge${viva?' pal':''}">${esc(r.entidad||'—')}</span>
        ${r.tipo_norma&&r.tipo_norma!=='No especificado'?`<span class="doc-badge">${esc(r.tipo_norma)}</span>`:''}
        ${r.tipo==='agenda'?'<span class="doc-badge">Agenda regulatoria</span>':''}
        ${vent?`<span class="sanc-fecha">${vent}</span>`:''}
        ${r.comentarios?` · ${fmt(r.comentarios)} comentario${r.comentarios===1?'':'s'}`:''}
        ${href?` · <a href="${esc(href)}" target="_blank" rel="noopener" style="color:var(--ink3)">ficha oficial ↗</a>`:''}
      </div>
    </div>`;
  }
  function sucRenderLanding(s){
    const el=document.getElementById('suc-landing'); if(!el||!s) return;
    const v=s.ventana||{};
    const rango=s.rango_fechas&&s.rango_fechas[0]?`${s.rango_fechas[0].slice(0,4)}–${s.rango_fechas[1].slice(0,4)}`:'—';
    const ab=(s.abiertos||[]);
    const urg=ab.filter(r=>r.estado_consulta==='cierra_pronto');
    el.innerHTML=`
      <div class="land-h">Lo que todavía se puede comentar · consultado hoy, ${esc(s.hoy||'')}</div>
      <div class="kpis">
        <div class="kpi"><div class="n" style="color:var(--green)">${fmt(v.abiertas||0)}</div><div class="l">Abiertas ahora</div></div>
        <div class="kpi"><div class="n" style="color:var(--red)">${fmt(v.cierran_en_7_dias||0)}</div><div class="l">Cierran en ≤7 días</div></div>
        <div class="kpi"><div class="n">${fmt(s.total||0)}</div><div class="l">Procesos en total</div></div>
        <div class="kpi"><div class="n">${rango}</div><div class="l">Periodo</div></div>
      </div>
      <div class="cob-note" style="margin-bottom:1.4rem">
        El plazo se calcula contra la fecha de <b>hoy</b>, no contra la de la
        cosecha: ${esc(v.cerradas!=null?fmt(v.cerradas):'—')} procesos ya vencieron y
        ${fmt(v.en_planeacion||0)} están anunciados sin fecha. Último barrido de la
        fuente: ${esc(s.cosechado_a||'—')}.
      </div>
      ${ab.length?`<div class="panel wide"><h3>Ventana abierta${urg.length?` · ${urg.length} cierra${urg.length===1?'':'n'} esta semana`:''}</h3>
        <div class="sanc-list">${ab.map(sucCard).join('')}</div></div>`:
        `<div class="panel wide"><h3>Ventana abierta</h3><div class="cob-note">Hoy no hay ninguna consulta pública abierta. Vuelve mañana: la fuente se mueve todos los días hábiles.</div></div>`}
      <div class="reg-sectors-grid">
        ${(s.por_entidad||[]).slice(0,12).map(x=>`<div class="sec-card" data-ent="${esc(x.entidad)}"><div class="n">${fmt(x.n)}</div><div class="l">${esc(x.entidad)}</div></div>`).join('')}
      </div>
      <div class="panel wide"><h3>Lo último publicado</h3><div class="sanc-list">${(s.recientes||[]).map(sucCard).join('')}</div></div>`;
    el.querySelectorAll('.sec-card').forEach(c=>c.onclick=()=>{
      SUC.estado=''; SUC.q=''; const i=document.getElementById('sq'); if(i) i.value='';
      sucSyncEstados(); sucBuscar({entidad:c.dataset.ent});
    });
  }
  function sucRenderResults(d){
    const el=document.getElementById('suc-results'); if(!el) return;
    el.style.display='block';
    const et=(SUC_ESTADOS.find(([k])=>k===(d.estado||''))||['','Todas'])[1];
    const scope=[d.entidad?esc(d.entidad):'', d.query?`«${esc(d.query)}»`:'', esc(et)].filter(Boolean).join(' · ');
    const v=d.ventana||{};
    const emp=(d.empresas||[]).length?`<div class="cob-note" style="margin-bottom:1rem">
        <b>${esc(d.empresas.map(e=>e.nombre).join(', '))}</b> es una empresa del diccionario: el
        Estado no regula marcas sino actividades, así que se buscó por su tema —
        ${esc(d.empresas.flatMap(e=>e.nucleo||[]).join(' · ')||'—')} — además del nombre literal.
      </div>`:'';
    el.innerHTML=`
      <div class="r-titular" style="font-size:1.4rem">${fmt(d.n)} ${d.n===1?'proceso':'procesos'}</div>
      <div class="r-sub" style="margin-bottom:1rem">${scope||'todos los procesos'}${
        v.abiertas?` · <b style="color:var(--green)">${fmt(v.abiertas)} todavía se puede${v.abiertas===1?'':'n'} comentar</b>`:
        ' · ninguno con la ventana abierta'}</div>
      ${emp}
      ${d.mostrados<d.n?`<div class="cob-note" style="margin-bottom:1rem">Mostrando ${d.mostrados} de ${fmt(d.n)} — primero lo que cierra antes. Afina la búsqueda para ver menos.</div>`:''}
      ${listaConMuro(d.resultados, sucCard, 'borrador', 'borradores', `acceso · ${d.query||'consulta pública'}`, 'Sin coincidencias. Prueba otro término o cambia el estado.')}`;
    el.scrollIntoView({behavior:'smooth',block:'start'});
  }
  async function sucBuscar(extra){
    const mine=++_sucSeq;
    const el=document.getElementById('suc-results'), landing=document.getElementById('suc-landing');
    if(landing) landing.style.display='none';
    if(el){ el.style.display='block'; el.innerHTML='<div class="llm-load" style="padding:2rem;justify-content:center">Buscando borradores <span class="dots"><span></span><span></span><span></span></span></div>'; }
    let d; try{ d=await call(Object.assign({action:'sucop', query:SUC.q, estado:SUC.estado}, extra||{})); }
    catch(e){ if(mine===_sucSeq&&el) el.innerHTML='<div class="err">No se pudo consultar. Reintenta.</div>'; return; }
    if(mine!==_sucSeq) return;
    sucRenderResults(d);
  }
  async function sucLoadStats(){
    // el landing NO se cachea entre visitas como los otros pilares: su número
    // principal es una cuenta regresiva, y servirla de memoria la envejecería
    // dentro de la misma sesión.
    const el=document.getElementById('suc-landing');
    if(el&&!SUC_STATS) el.innerHTML='<div class="llm-load" style="padding:2rem;justify-content:center">Cargando las consultas abiertas <span class="dots"><span></span><span></span><span></span></span></div>';
    try{ SUC_STATS=await call({action:'sucop'}); }catch(e){ /* deja lo anterior */ }
    if(SUC_STATS) sucRenderLanding(SUC_STATS);
    else if(el) el.innerHTML='<div class="err">No se pudieron cargar las consultas. Reintenta.</div>';
  }
  function sucShowLanding(){ const r=document.getElementById('suc-results'); if(r) r.style.display='none'; const l=document.getElementById('suc-landing'); if(l) l.style.display='block'; }
  function sucSyncEstados(){ document.querySelectorAll('#sestados .chip').forEach(c=>c.classList.toggle('on',(c.dataset.est||'')===SUC.estado)); }
  function sucInit(){
    if(_sucInited) return; _sucInited=true;
    const sq=document.getElementById('sq'), sgo=document.getElementById('sgo');
    const go=()=>{ SUC.q=(sq&&sq.value||'').trim(); if(!SUC.q&&SUC.estado==='abiertas') sucShowLanding(); else sucBuscar(); };
    if(sgo) sgo.onclick=go;
    if(sq) sq.addEventListener('keydown',e=>{ if(e.key==='Enter') go(); });
    const cont=document.getElementById('sestados');
    if(cont) SUC_ESTADOS.forEach(([k,t])=>{ const c=document.createElement('span'); c.className='chip'+(k===SUC.estado?' on':''); c.dataset.est=k; c.textContent=t; c.onclick=()=>{ SUC.estado=k; sucSyncEstados(); if(!SUC.q&&k==='abiertas') sucShowLanding(); else sucBuscar(); }; cont.appendChild(c); });
    const sb=document.getElementById('sucBack'); if(sb) sb.onclick=()=>showView('home');
  }

  /* Lo que caudal.html necesita de acá: la búsqueda universal entra a los
     `*Buscar`/`*Card`/`*Init` de cada pilar, y caudal-base.js llama los
     `*LoadStats` al abrir la vista. Los nombres se conservan tal cual: allá
     se usan como identificador suelto y resuelven contra `window`.
     (`_ampliarEmp` va aparte, como global, porque se reasigna.)
     SUCOP viaja entero por acá: la búsqueda universal, que vive en caudal.html,
     lee `SUC` y llama `sucBuscar`/`sucSyncEstados`/`sucCard`. `SUC` es un const
     que solo se MUTA (`SUC.q=…`), nunca se reasigna, así que la referencia
     compartida por `window` siempre es la misma. */
  Object.assign(window, {
    q, buscar, EJEMPLOS, empresaHint, wireEmpresaHint,
    REG, regBuscar, regInit, regLoadStats, sancCard, fmtCOP,
    EJE, ejeBuscar, ejeInit, ejeLoadStats, ejeCard,
    CON, conBuscar, conInit, conLoadStats, conCard,
    MED, medBuscar, medInit, medLoadLanding, medHeadCard,
    SUC, sucBuscar, sucInit, sucLoadStats, sucCard, sucSyncEstados,
  });
})();
