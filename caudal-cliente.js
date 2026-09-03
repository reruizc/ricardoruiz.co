/* caudal-cliente.js — la Vista Cliente (SKU A)
   ------------------------------------------------------------------
   El producto de acompañamiento: la marca, los perfiles de cliente
   (CRUD contra el worker, wizard y alertas por correo), el radar de las
   cuatro direcciones y la lectura del analista con su sondeo.

   Se apoya en caudal.html para los helpers de formato y para `cerrar`
   /`modal` del modal compartido, y en caudal-pilares.js para `CON` y
   `fmtCOP`. Publica `cliInit` (lo llama initHome) y `pfLoadList` (lo
   llama caudal-base.js al abrir sesión).

   ⚠️ Al tocar este archivo hay que bumpear el ?v= del <script> que lo
   carga en caudal.html, o el navegador sirve la copia vieja. */
(function(){
  'use strict';

  /* ---------- marca del producto de acompañamiento ----------
     Se llamaba «Radar», que es como se llama el de Orza. El nombre definitivo lo
     deciden los socios entre Sextante y Rosa de los Vientos, así que vive en UNA
     constante: cambiar `nombre` y `articulo` renombra la portada, la vista y
     todos los textos. No se tocaron ni los id ni las clases CSS (`radar-cta`,
     `cli-*`): renombrarlos rompería el cableado sin que el cliente gane nada. */
  const MARCA={
    nombre:'Rosa de los Vientos',
    articulo:'la',            // «abrir LA Rosa de los Vientos»
    // Los cuatro puntos. El orden es el de la rosa: N · E · S · O.
    puntos:[
      {c:'N', dir:'n', let:'N', rumbo:'Norte',      t:'oportunidades', d:'La lectura del contexto: qué se está abriendo y qué conviene mover ahora. No es el trámite — es si el ambiente lo aguanta.'},
      {c:'E', dir:'e', let:'E', rumbo:'Oriente',    t:'conversación',  d:'Prensa y redes sobre tu cliente y su sector: quién está hablando, en qué tono y desde cuándo.'},
      {c:'S', dir:'s', let:'S', rumbo:'Sur',        t:'competencia',   d:'Los otros de tu sector, con el mismo detalle que tú: qué los sancionaron, qué contratan, qué proyectos los tocan.'},
      {c:'O', dir:'o', let:'W', rumbo:'Occidente',  t:'Estado',        d:'Lo que produce el Estado: proyectos en el Congreso, decretos del Ejecutivo y actos de las superintendencias.'}
    ]
  };


  /* ---------- Vista Cliente · Radar (SKU A) ---------- */
  // Los 6 presets se quedan como DEMO y como plantilla de arranque; el radar de
  // verdad corre sobre un perfil guardado (temas propios + empresas vigiladas),
  // que vive en el KV del worker bajo `caudal:perfil:*`.
  /* Espejo de SECTORES_CLIENTE en caudal_core.py. Se ofrecen dentro de un
     drill-down: el nombre puede ser completo sin desplazar la Rosa. */
  // Los dos primeros son CLIENTES con nombre, no sectores: van aparte porque
  // muestran lo que un preset genérico no puede — una empresa con varias líneas
  // de negocio, cada una en su comisión, y con competencia real en el Sur.
  const CLI_CLIENTES=[['didi','DiDi',1],['binance','Binance',1]];
  const CLI_SECS=[
    ['salud','Salud',1],['ambiente','Ambiente',1],['contratacion','Contratación',1],
    ['financiero','Financiero',1],['transporte','Transporte',1],['energia','Energía',0],
    ['agro','Agro',0],['tic','TIC',0],['pymes','Mipymes',0],['educacion','Educación',0],
    ['trabajo','Trabajo',0],['comercio','Comercio y consumo',1],
    ['vivienda','Vivienda y construcción',0],['turismo','Turismo y hotelería',0],
    ['puertos','Puertos y logística',1]];
  const AUTH_API='https://rr-auth.reruizc.workers.dev';
  let _cliInited=false, _cliSeq=0;
  // estado del gestor de perfiles
  let PF_LIST=[], PF_ACTIVE=null, PF_DRAFT=null, PF_LIMIT=null, PF_CADENCIA=null, PF_WIZARD_STEP=1, PF_WIZARD_LOOKUP=0, PF_WIZARD_TIMER=null;
  // Global (no `let`) porque quien lo escribe es setAcceso(), que vive en
  // caudal-base.js; acá solo se lee.
  window.PF_META=null;

  async function wcall(path, opts){
    const t=localStorage.getItem('rr-token');
    if(!t) throw new Error('sin sesión');
    const r=await fetch(AUTH_API+path, Object.assign({headers:Object.assign(
      {'Authorization':'Bearer '+t}, (opts&&opts.body)?{'Content-Type':'application/json'}:{})}, opts||{}));
    const d=await r.json().catch(()=>({ok:false,error:'respuesta inválida'}));
    if(!d.ok) throw new Error(d.error||('HTTP '+r.status));
    return d;
  }

  /* La portada del instrumento: su nombre y sus cuatro puntos. Se pinta desde
     MARCA para que renombrarlo no obligue a perseguir textos por el archivo. */
  function marcaRender(){
    const N=MARCA.nombre, A=MARCA.articulo;
    const h1=document.getElementById('cli-h1');
    if(h1) h1.innerHTML=`<em>${esc(N)}</em>.`;
    const sub=document.getElementById('cli-sub');
    if(sub) sub.textContent=`Arma el perfil de tu cliente —sus temas y las empresas que vigila— y `
      +`${N} orienta en cuatro direcciones: lo que produce el Estado, lo que hace su competencia, `
      +`lo que se está diciendo y lo que se está abriendo. Descarta el ruido y deja las señales que `
      +`mueven su aguja, cada una con su estado real y una acción sugerida.`;
    const r=document.getElementById('cli-rosa');
    if(r){
      r.innerHTML=`<div class="sext-stage">
        <img src="imagenes/caudal-sextante-mar.jpg" alt="" />
        ${MARCA.puntos.map(p=>`<button type="button" class="sext-pt ${p.dir}" data-c="${p.c}" aria-label="${esc(p.rumbo)}: ${esc(p.t)}"><span class="sext-let">${esc(p.let||p.c)}</span><span class="sext-lab">${esc(p.rumbo)}</span></button>`).join('')}
        <div class="sext-desc" id="sextDesc"></div>
      </div>`;
      const desc=document.getElementById('sextDesc');
      r.querySelectorAll('.sext-pt').forEach(btn=>{
        btn.onclick=ev=>{
          ev.stopPropagation();
          const p=MARCA.puntos.find(x=>x.c===btn.dataset.c);
          if(!p||!desc) return;
          r.querySelectorAll('.sext-pt').forEach(b=>b.classList.toggle('on', b===btn));
          desc.className=`sext-desc at-${p.dir}`;
          desc.innerHTML=`<b>${esc(p.rumbo)}: ${esc(p.t)}</b> — ${esc(p.d)}`;
        };
      });
    }
    const pie=document.getElementById('cli-pie');
    if(pie) pie.innerHTML='Las cuatro direcciones las cruza Caudal; la lectura la firma un analista. '
      +'<b>No es un tablero que se deja solo</b> — el acompañamiento es parte del servicio.';
    // portada: la tarjeta que lleva acá
    const t=document.querySelector('#radar-cta .rc-t'); if(t) t.textContent=N;
    const d=document.querySelector('#radar-cta .rc-d');
    if(d) d.textContent=`Elige un sector o arma el perfil de tu cliente y ${N} cruza el Estado, `
      +`su competencia y la conversación pública, filtra el ruido y te deja las señales que mueven `
      +`su aguja, ya leídas y con una acción sugerida.`;
    const g=document.querySelector('#radar-cta .rc-go'); if(g) g.textContent=`Abrir ${A} ${N} →`;
    const e=document.querySelector('#cli-body .cli-empty');
    if(e) e.textContent=`Crea el perfil de un cliente —o abre un sector de muestra— para orientarlo.`;
  }

  function cliInit(){
    if(_cliInited) return; _cliInited=true;
    marcaRender();
    const cont=document.getElementById('cli-sectors');
    // Los clientes reales siguen visibles; los 15 sectores se despliegan solo
    // cuando el usuario los necesita.
    if(cont){
      const pinta=(lista,cls)=>lista.forEach(([k,t,reg])=>{
        const c=document.createElement('span');
        c.className='chip sec-chip'+(reg?' con-reg':'')+(cls?' '+cls:'');
        c.dataset.sec=k; c.textContent=t;
        c.title=cls?'Perfil de cliente real · varias líneas de negocio'
                   :(reg?'Tiene fuente conectada en el pilar Regulatorio'
                       :'Su regulador sectorial todavía no es fuente de Caudal');
        c.onclick=()=>cliLoad({sector:k}); cont.appendChild(c); });
      pinta(CLI_CLIENTES,'cli-real');
      const drill=document.createElement('details');
      drill.className='sec-drill';
      drill.innerHTML='<summary class="chip add">Explorar 15 sectores</summary><div class="sec-drill-list"></div>';
      const list=drill.querySelector('.sec-drill-list');
      CLI_SECS.forEach(([k,t,reg])=>{
        const c=document.createElement('button');
        c.type='button'; c.className='chip sec-chip'+(reg?' con-reg':'');
        c.dataset.sec=k; c.textContent=t;
        c.title=reg?'Tiene fuente conectada en el pilar Regulatorio':'Abrir sector de muestra';
        c.onclick=()=>{ drill.open=false; cliLoad({sector:k}); };
        list.appendChild(c);
      });
      cont.appendChild(drill);
    }
    pfRenderBar();
    // Los perfiles piden cuenta CON acceso (el worker exige sesión). El invitado
    // por link y el visitante sin acceso se quedan con el radar sobre los presets.
    if(ACCESO && !IS_GUEST && HAS_SESSION){ pfLoadList(); call({action:'perfil_meta'}).then(m=>{PF_META=m;}).catch(()=>{}); }
    // toggle Legislativo/Regulatorio/Prensa — delegado porque #cli-toggle se
    // recrea en cada cliRender(); click de nuevo en el mismo chip lo colapsa.
    const vc=document.getElementById('view-cliente');
    if(!vc) return;
    // TODO el editor de perfil va por delegación: su DOM se recrea entero en
    // cada pfRenderEdit(), así que los onclick directos morirían con él.
    vc.addEventListener('click', e=>{
      const t=e.target;
      // va ANTES de [data-pf] a propósito: el chip de editar vive en la misma
      // barra que los chips de perfil y no queremos que un anidamiento futuro
      // lo haga caer en pfAbrir.
      if(t.closest('[data-pfedit]')){ if(PF_ACTIVE&&PF_ACTIVE.perfilId) pfEditar(PF_ACTIVE); return; }
      const pf=t.closest('[data-pf]');
      if(pf){ pfAbrir(pf.dataset.pf); return; }
      if(t.closest('[data-pfnew]')){ pfNuevo(); return; }
      const tpl=t.closest('[data-pftpl]');
      if(tpl){ const n=PF_DRAFT?PF_DRAFT.nombre:''; pfNuevo(tpl.dataset.pftpl);
               if(n&&PF_DRAFT){ PF_DRAFT.nombre=n; pfRenderEdit(); } return; }
      const sug=t.closest('[data-pfemp]');
      if(sug){
        if(PF_DRAFT&&!PF_DRAFT.empresas.includes(sug.dataset.pfemp)) PF_DRAFT.empresas.push(sug.dataset.pfemp);
        const box=document.getElementById('pf-sug'); if(box){ box.hidden=true; box.innerHTML=''; }
        const inp=document.getElementById('pf-emp-in'); if(inp){ inp.value=''; inp.focus(); }
        pfRenderTags(); return;
      }
      const rt=t.closest('[data-rmtema]');
      if(rt&&PF_DRAFT){ PF_DRAFT.temas.splice(+rt.dataset.rmtema,1); pfRenderTags(); return; }
      const re=t.closest('[data-rmemp]');
      if(re&&PF_DRAFT){ PF_DRAFT.empresas.splice(+re.dataset.rmemp,1); pfRenderTags(); return; }
      if(t.closest('#pf-alertas')){ pfToggleAlertas(); return; }
      const tb=t.closest('[data-tipo]');
      if(tb&&PF_DRAFT){ PF_DRAFT.tipo=tb.dataset.tipo; pfRenderEdit(); return; }
      const rl=t.closest('[data-rmlinea]');
      if(rl&&PF_DRAFT){ PF_DRAFT.lineas.splice(+rl.dataset.rmlinea,1); pfRenderTags(); return; }
      if(t.closest('#pf-save')){ pfGuardar(); return; }
      if(t.closest('#pf-cancel')){ pfCerrarEdit(); return; }
      if(t.closest('#pf-del')){ pfBorrar(); return; }
      // toggle Legislativo/Regulatorio/Prensa — delegado porque #cli-toggle se
      // recrea en cada cliRender(); click de nuevo en el mismo chip lo colapsa.
      const chip=t.closest('#cli-toggle .chip'); if(!chip) return;
      const det=document.getElementById('cli-detalle'); if(!det) return;
      const already=chip.classList.contains('on');
      vc.querySelectorAll('#cli-toggle .chip').forEach(c=>c.classList.remove('on'));
      if(already){ det.innerHTML=''; return; }
      chip.classList.add('on');
      det.innerHTML=_CLI_LAST?cliDetalleHTML(chip.dataset.p,_CLI_LAST):'';
    });
    vc.addEventListener('keydown', e=>{
      if(e.key!=='Enter') return;
      const inp=e.target;
      if(inp.id==='pf-linea-in'){
        e.preventDefault();
        const v=(inp.value||'').replace(/\s+/g,' ').trim();
        if(!PF_DRAFT) return;
        if(v.length<3) return pfMsg('Ponle un nombre reconocible a la línea.');
        if((PF_DRAFT.lineas||[]).length>=8) return pfMsg('Máximo 8 líneas de negocio.');
        PF_DRAFT.lineas=PF_DRAFT.lineas||[];
        if(!PF_DRAFT.lineas.some(x=>x.toLowerCase()===v.toLowerCase())) PF_DRAFT.lineas.push(v);
        inp.value=''; pfMsg(''); pfRenderTags();
      } else if(inp.id==='pf-tema-in'){
        e.preventDefault();
        const v=(inp.value||'').replace(/\s+/g,' ').trim();
        const lim=(PF_META&&PF_META.limites&&PF_META.limites.temas)||15;
        if(!PF_DRAFT) return;
        if(v.length<3) return pfMsg('Un tema de menos de 3 letras trae ruido, no señal.');
        if(PF_DRAFT.temas.length>=lim) return pfMsg('Máximo '+lim+' temas.');
        if(!PF_DRAFT.temas.some(x=>x.toLowerCase()===v.toLowerCase())) PF_DRAFT.temas.push(v);
        inp.value=''; pfMsg(''); pfRenderTags();
      } else if(inp.id==='pf-emp-in'){
        e.preventDefault();
        // Enter sobre el buscador toma la primera sugerencia (si hay)
        const first=document.querySelector('#pf-sug [data-pfemp]'); if(first) first.click();
      } else if(inp.id==='pf-nombre'||inp.id==='pf-desc'){
        e.preventDefault(); pfGuardar();
      }
    });
    let _pfT=null;
    vc.addEventListener('input', e=>{
      if(e.target.id!=='pf-emp-in') return;
      clearTimeout(_pfT); const v=e.target.value;
      _pfT=setTimeout(()=>pfSugerir(v), 220);
    });
  }
  /* ---------- perfiles de cliente · CRUD contra el worker ---------- */
  // El índice de perfiles del KV es de consistencia EVENTUAL: el `list()` que
  // corre justo después de crear uno puede todavía no verlo. Medido en
  // producción al crear el primer perfil de una cuenta: el perfil quedó bien
  // guardado y su radar cargando, y la barra decía «Todavía no tienes ninguno ·
  // 0/25» hasta recargar la página. O sea que la interfaz le dice al cliente
  // que no guardó justo en el momento en que estrena el producto.
  // Regla: lo que sabemos del perfil abierto le gana a una lista rezagada.
  function pfMergeActivo(){
    const p=PF_ACTIVE; if(!p||!p.perfilId) return;
    if(PF_LIST.some(x=>x.perfilId===p.perfilId)) return;
    PF_LIST.unshift({perfilId:p.perfilId, nombre:p.nombre||'Perfil sin nombre',
      descripcion:p.descripcion||'', n_temas:(p.temas||[]).length,
      n_empresas:(p.empresas||[]).length, sector_sanciones:p.sector_sanciones||'',
      comision:p.comision||'', alertas:p.alertas||{activo:false}});
    // el contador tiene que contar lo mismo que se ve, no lo que trajo el list
    if(PF_LIMIT) PF_LIMIT.usados=PF_LIST.length;
  }
  async function pfLoadList(){
    try{ const d=await wcall('/caudal/perfil/list'); PF_LIST=d.perfiles||[]; PF_LIMIT={usados:d.count,tope:d.ownedLimit,plan:d.plan}; PF_CADENCIA=d.cadencia||null; }
    catch(e){ PF_LIST=[]; PF_LIMIT=null; }
    // `pfBorrar` pone PF_ACTIVE en null ANTES de recargar, así que un perfil
    // recién borrado no puede revivir por aquí.
    pfMergeActivo();
    pfRenderBar();
  }
  function pfRenderBar(){
    const bar=document.getElementById('cli-perfiles'); if(!bar) return;
    if(IS_GUEST){
      bar.innerHTML='<span class="pf-lbl">Perfiles de cliente</span><span class="cob-note" style="margin:0">Entra con tu cuenta para guardar los temas y las empresas de un cliente.</span>';
      return;
    }
    let h='<span class="pf-lbl">Perfiles de cliente</span>';
    const visibles=PF_LIST.filter(p=>(p.nombre||'').trim().toLowerCase()!=='prueba a2 editada');
    h+=visibles.map(p=>`<span class="chip${PF_ACTIVE&&PF_ACTIVE.perfilId===p.perfilId?' on':''}" data-pf="${esc(p.perfilId)}" title="${esc(p.n_temas)} tema(s) · ${esc(p.n_empresas)} empresa(s) vigilada(s)">${esc(p.nombre)}</span>`).join('');
    if(!visibles.length) h+='<span class="cob-note" style="margin:0">Todavía no tienes ninguno.</span>';
    h+='<span class="chip add" data-pfnew="1">+ Nuevo perfil</span>';
    if(PF_LIMIT) h+=`<span class="cob-note" style="margin:0">${PF_LIMIT.usados}/${PF_LIMIT.tope} · plan ${esc(PF_LIMIT.plan)}</span>`;
    // Puerta al editor del perfil abierto. Sin esto `pfEditar` quedaba huérfana
    // y un perfil guardado no se podía ni corregir ni borrar: `pfBorrar` exige
    // `PF_DRAFT.perfilId`, que solo existe cuando el editor abre uno existente.
    if(PF_ACTIVE&&PF_ACTIVE.perfilId)
      h+=`<span class="chip add" data-pfedit="1" title="Corregir los temas, las empresas o el nombre de «${esc(PF_ACTIVE.nombre||'')}»">✎ Editar</span>`;
    // El interruptor sale para el perfil abierto: es de ese perfil, no global.
    if(PF_ACTIVE&&PF_ACTIVE.perfilId) h+=pfAlertasHTML(PF_ACTIVE);
    bar.innerHTML=h;
  }
  // Draft del editor. `desdePreset` copia un sector como punto de partida —
  // por eso los presets no se borraron: son las plantillas.
  function pfNuevo(desdePreset){
    const pl=desdePreset&&PF_META&&(PF_META.plantillas||[]).find(x=>x.k===desdePreset);
    PF_DRAFT=pl?{perfilId:null,nombre:pl.nombre,descripcion:'',temas:pl.temas.slice(),
                 empresas:[],sector_sanciones:pl.sector_sanciones||'',comision:pl.comision||'',
                 tipo:pl.tipo||'empresa',alcance:'colombia',lineas:(pl.lineas||[]).map(l=>l.nombre||l)}
               :{perfilId:null,nombre:'',descripcion:'',temas:[],empresas:[],sector_sanciones:'',comision:'',
                 tipo:'',alcance:'colombia',lineas:[]};
    PF_WIZARD_STEP=1;
    pfRenderWizard();
  }
  function pfWizardTags(kind){
    const vals=(PF_DRAFT&&PF_DRAFT[kind])||[];
    const empty=kind==='temas'?'Aún no agregas temas.':'Aún no agregas empresas.';
    return vals.length?vals.map((x,i)=>`<span class="chip on">${esc(x)} <button type="button" class="x" data-wizrm="${kind}:${i}" aria-label="Quitar ${esc(x)}">×</button></span>`).join(''):`<span class="cob-note" style="margin:0">${empty}</span>`;
  }
  function pfRenderWizard(){
    if(!PF_DRAFT) return;
    const d=PF_DRAFT, step=PF_WIZARD_STEP;
    let body='';
    if(step===1) body=`<div class="pf-f"><label>¿Qué clase de cliente es?</label><div class="pf-type-cards">
      <button type="button" class="pf-type-card${d.tipo==='empresa'?' on':''}" data-wiztipo="empresa"><img src="imagenes/caudal-datos.jpg" alt=""><span>Una empresa</span><small>Una operación o marca principal.</small></button>
      <button type="button" class="pf-type-card${d.tipo==='holding'?' on':''}" data-wiztipo="holding"><img src="imagenes/caudal-congreso.jpg" alt=""><span>Un holding</span><small>Un grupo con varias empresas.</small></button>
      <button type="button" class="pf-type-card${d.tipo==='gremio'?' on':''}" data-wiztipo="gremio"><img src="imagenes/caudal-territorial.jpg" alt=""><span>Un gremio</span><small>Una asociación que representa empresas.</small></button>
    </div></div>`;
    if(step===2) body=`<div class="pf-f"><label>¿Cómo se llama?</label><input id="pf-wiz-nombre" maxlength="80" placeholder="Asobancaria, Grupo Nutresa, EPM…" value="${esc(d.nombre)}" autofocus><div class="pf-dict-status" id="pf-dict-status">Escribe el nombre para comprobarlo en el diccionario de Caudal.</div></div>`;
    if(step===3) body=`<div class="pf-f"><label>¿Qué tema le importa seguir?</label><input id="pf-wiz-tema" maxlength="80" placeholder="p. ej. reforma pensional"><div class="hint">Escríbelo como aparecería en una ley y presiona <b>Enter</b> para añadirlo. Repite para sumar más temas.</div><div class="pf-tags">${pfWizardTags('temas')}</div></div>`;
    if(step===4) body=`<div class="pf-f pf-ac"><label>${d.tipo==='gremio'?'¿Qué empresa quiere vigilar?':'¿Qué competidor quiere seguir?'}</label><input id="pf-wiz-emp" maxlength="60" placeholder="escribe al menos 2 letras" autocomplete="off"><div class="hint">Opcional. Te sugerimos coincidencias del diccionario: selecciona una y repite la búsqueda para añadir todos los competidores que quieras.</div><div class="pf-sug" id="pf-sug" hidden></div><div class="pf-tags">${pfWizardTags('empresas')}</div></div>`;
    if(step===5) body=`<div class="pf-f"><label>¿Dónde debe seguirlo?</label><div class="pf-scope-cards"><button type="button" class="pf-scope-card${d.alcance==='colombia'?' on':''}" data-wizscope="colombia"><b>Solo Colombia</b><small>Seguimiento de redes, normas y regulación del país.</small></button><button type="button" class="pf-scope-card${d.alcance==='latam'?' on':''}" data-wizscope="latam"><b>Latinoamérica</b><small>Señala un seguimiento regional para el equipo.</small></button></div><div class="hint">Hoy las fuentes automáticas de Caudal son colombianas; la selección regional queda identificada en el perfil para su seguimiento analítico.</div></div>`;
    if(step===6) body=`<div class="pf-f"><label>Listo para crear el perfil</label><div class="pf-wizard-copy"><b>${esc(d.nombre||'Este perfil')}</b> seguirá ${d.temas.length?esc(d.temas.join(', ')):'los temas que agregues'}${d.empresas.length?' y '+esc(d.empresas.length)+' empresa(s)':''}, con alcance ${d.alcance==='latam'?'regional latinoamericano':'Colombia'}. Podrás completar líneas de negocio, sector y comisión después desde Editar.</div></div>`;
    modalCard.dataset.pfWizard='1';
    modalCard.innerHTML=`<div class="pf-wizard"><button class="modal-close" type="button" id="pf-wiz-close">✕</button><div class="pf-wizard-step">Nuevo perfil · ${step} de 6</div><h2>${step===1?'Empecemos por el cliente':step===2?'Identifiquémoslo':step===3?'Definamos su agenda':step===4?'Miremos alrededor':step===5?'Definamos el alcance':'Revisa el perfil'}</h2><div class="pf-wizard-copy">${step===1?'Elige la estructura que mejor representa al cliente.':step===2?'Comprobamos en el momento si ya existe en el diccionario de Caudal.':step===3?'Una pregunta a la vez: añade los temas que sí mueven su aguja.':step===4?'Esta pregunta es opcional; puedes saltarla.':step===5?'Define el territorio para el seguimiento.':'Puedes editar los detalles cuando quieras.'}</div>${body}<div class="pf-acts"><button class="btn-g" type="button" id="pf-wiz-back" ${step===1?'hidden':''}>← Atrás</button><span class="pf-msg" id="pf-msg"></span><button class="btn-t" type="button" id="pf-wiz-next">${step===6?'Crear perfil':'Continuar →'}</button></div></div>`;
    modal.classList.add('on');
    document.getElementById('pf-wiz-close').onclick=()=>cerrar();
    const back=document.getElementById('pf-wiz-back'); if(back) back.onclick=()=>{ PF_WIZARD_STEP--; pfRenderWizard(); };
    document.querySelectorAll('[data-wiztipo]').forEach(b=>b.onclick=()=>{ d.tipo=b.dataset.wiztipo; pfRenderWizard(); });
    document.querySelectorAll('[data-wizscope]').forEach(b=>b.onclick=()=>{ d.alcance=b.dataset.wizscope; pfRenderWizard(); });
    document.querySelectorAll('[data-wizrm]').forEach(b=>b.onclick=()=>{ const [kind,i]=b.dataset.wizrm.split(':'); d[kind].splice(+i,1); pfRenderWizard(); });
    const next=document.getElementById('pf-wiz-next'); if(next) next.onclick=()=>pfWizardNext();
    const name=document.getElementById('pf-wiz-nombre'); if(name){ name.oninput=()=>{ clearTimeout(PF_WIZARD_TIMER); PF_WIZARD_TIMER=setTimeout(()=>pfWizardCheckName(name.value),280); }; if(name.value.trim()) pfWizardCheckName(name.value); }
    const topic=document.getElementById('pf-wiz-tema'); if(topic) topic.onkeydown=e=>{ if(e.key==='Enter'){ e.preventDefault(); pfWizardAddTopic(); } };
    const emp=document.getElementById('pf-wiz-emp'); if(emp){ emp.oninput=()=>pfSugerir(emp.value); emp.onkeydown=e=>{ if(e.key==='Enter'){ e.preventDefault(); const first=document.querySelector('#pf-sug [data-pfemp]'); if(first) first.click(); } }; }
    document.querySelectorAll('#pf-sug [data-pfemp]').forEach(x=>x.onclick=()=>{ if(!d.empresas.includes(x.dataset.pfemp)) d.empresas.push(x.dataset.pfemp); pfRenderWizard(); });
  }
  function pfWizardAddTopic(){
    const inp=document.getElementById('pf-wiz-tema'), v=(inp&&inp.value||'').replace(/\s+/g,' ').trim();
    if(v.length<3) return pfMsg('Escribe un tema de al menos 3 letras.');
    if(!PF_DRAFT.temas.some(x=>x.toLowerCase()===v.toLowerCase())) PF_DRAFT.temas.push(v);
    pfRenderWizard();
  }
  function pfWizardNorm(v){ return String(v||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/\s+/g,' ').trim(); }
  async function pfWizardCheckName(nombre){
    const status=document.getElementById('pf-dict-status'), q=(nombre||'').trim();
    if(!status||q.length<2){ if(status){ status.className='pf-dict-status'; status.textContent='Escribe el nombre para comprobarlo en el diccionario de Caudal.'; } return; }
    const mine=++PF_WIZARD_LOOKUP; status.className='pf-dict-status'; status.textContent='Comprobando el diccionario…';
    try{
      const r=await call({action:'empresas',query:q}); if(mine!==PF_WIZARD_LOOKUP) return;
      const found=(r.empresas||[]).find(e=>pfWizardNorm(e.nombre)===pfWizardNorm(q));
      status.className='pf-dict-status '+(found?'on':'off');
      status.textContent=found?`Sí: «${found.nombre}» ya está en el diccionario (${found.tipo||'empresa'}).`:'No aparece en el diccionario previo; puedes crear el perfil de todas formas.';
    }catch(e){ if(mine===PF_WIZARD_LOOKUP){ status.className='pf-dict-status'; status.textContent='No pudimos comprobar el diccionario ahora; puedes continuar.'; } }
  }
  function pfWizardNext(){
    if(PF_WIZARD_STEP===1&&!PF_DRAFT.tipo) return pfMsg('Elige empresa, holding o gremio.');
    if(PF_WIZARD_STEP===2){ const n=document.getElementById('pf-wiz-nombre'); PF_DRAFT.nombre=(n&&n.value||'').trim(); if(!PF_DRAFT.nombre) return pfMsg('Ponle un nombre al perfil.'); }
    if(PF_WIZARD_STEP===3){ const inp=document.getElementById('pf-wiz-tema'); if(inp&&inp.value.trim()) pfWizardAddTopic(); if(!PF_DRAFT.temas.length) return pfMsg('Agrega al menos un tema.'); }
    if(PF_WIZARD_STEP===6){ pfGuardar({wizard:true}); return; }
    PF_WIZARD_STEP++; pfRenderWizard();
  }
  function pfEditar(p){
    PF_DRAFT={perfilId:p.perfilId,nombre:p.nombre||'',descripcion:p.descripcion||'',
              temas:(p.temas||[]).slice(),empresas:(p.empresas||[]).slice(),
              sector_sanciones:p.sector_sanciones||'',comision:p.comision||'',
              tipo:p.tipo||'empresa',lineas:(p.lineas||[]).slice(),
              alertas:p.alertas||{activo:false}};
    pfRenderEdit();
  }
  function pfCerrarEdit(){ PF_DRAFT=null; const e=document.getElementById('pf-edit'); if(e){ e.hidden=true; e.innerHTML=''; } }
  function pfRenderEdit(){
    const el=document.getElementById('pf-edit'); if(!el||!PF_DRAFT) return;
    const d=PF_DRAFT;
    const lim=(PF_META&&PF_META.limites)||{temas:15,empresas:15};
    const secs=(PF_META&&PF_META.sectores_sanciones)||[];
    const coms=(PF_META&&PF_META.comisiones)||[];
    const plans=(PF_META&&PF_META.plantillas)||[];
    // Empresa por defecto: es el caso más común y evita que el primer campo que
    // ve el usuario sea la pregunta equivocada («qué vigila» a una empresa).
    const esEmp = d.tipo!=='gremio';
    el.hidden=false;
    el.innerHTML=`
      <div class="pf-grid">
        <div class="pf-f"><label>Nombre del cliente</label>
          <input id="pf-nombre" type="text" maxlength="80" placeholder="Asobancaria, Fenalco, EPM…" value="${esc(d.nombre)}" /></div>
        <div class="pf-f"><label>Nota interna (opcional)</label>
          <input id="pf-desc" type="text" maxlength="200" placeholder="quién es y qué le preocupa" value="${esc(d.descripcion)}" /></div>
        <div class="pf-f full"><label>¿Qué es este cliente?</label>
          <div class="pf-tipo">
            <button type="button" class="pf-tbtn${d.tipo==='empresa'?' on':''}" data-tipo="empresa">Una empresa</button>
            <button type="button" class="pf-tbtn${d.tipo==='holding'?' on':''}" data-tipo="holding">Un holding</button>
            <button type="button" class="pf-tbtn${d.tipo==='gremio'?' on':''}" data-tipo="gremio">Un gremio o asociación</button>
          </div>
          <div class="hint">${esEmp
            ? 'Una empresa compite y opera en varias líneas de negocio; se le pregunta contra quién compite, no qué vigila.'
            : 'Un gremio representa a otros: se le pregunta a quién agrupa y qué temas defiende por ellos.'}</div></div>
        ${esEmp?`<div class="pf-f full"><label>Líneas de negocio (opcional)</label>
          <input id="pf-linea-in" type="text" maxlength="60" placeholder="una línea y Enter — p. ej. «reparto de alimentos»" />
          <div class="hint">Una empresa multi-negocio no tiene UNA comisión. DiDi cae en cuatro —Sexta, Primera, Tercera y Séptima— según si el proyecto es de movilidad, datos, impuestos o laboral. Cada línea que agregues se rastrea aparte.</div>
          <div class="pf-tags" id="pf-lineas"></div></div>`:''}
        <div class="pf-f full"><label>${esEmp?'Temas que le aplican':'Temas que vigila'} · máx ${lim.temas}</label>
          <input id="pf-tema-in" type="text" maxlength="80" placeholder="escribe un tema y Enter — p. ej. «tasas de usura»" />
          <div class="hint">Frases exactas, como las diría una ley. Entre más específica, menos ruido: «reforma tributaria» rinde mejor que «impuestos».</div>
          <div class="pf-tags" id="pf-temas"></div></div>
        <div class="pf-f full pf-ac"><label>${esEmp?'Competidores a seguir':'Empresas vigiladas'} · máx ${lim.empresas}</label>
          <input id="pf-emp-in" type="text" maxlength="60" placeholder="${esEmp?'busca a tu competencia — p. ej. «uber»':'busca en el diccionario — p. ej. «bancolombia»'}" autocomplete="off" />
          <div class="hint">${esEmp
            ? 'A una empresa no se le pregunta qué <i>vigila</i>: se le pregunta contra quién compite. Lo que le pase a estos —sanciones, contratos, prensa— entra por el <b>Sur</b> de la Rosa de los Vientos.'
            : 'Las empresas del gremio, o las que sigue de cerca. Del diccionario de Caudal: en el Congreso se traducen a su tema (nadie legisla «Uber», legisla «plataformas»); en sanciones, contratación y prensa se buscan por su nombre propio.'}</div>
          <div class="pf-sug" id="pf-sug" hidden></div>
          <div class="pf-tags" id="pf-emps"></div></div>
        <div class="pf-f"><label>Sector de sanciones</label>
          <select id="pf-sec"><option value="">— ninguno —</option>${secs.map(s=>{
            /* el conteo de SANCIONES solo no describe la fuente: la ANLA tiene
               210 sanciones y 54.105 actos, y con el primer número parecería
               marginal siendo la más grande del pilar. */
            const n=(s.n_actos&&s.n_actos!==s.n)?`${fmt(s.n_actos)} actos · ${fmt(s.n)} sanciones`:fmt(s.n);
            return `<option value="${esc(s.k)}"${s.k===d.sector_sanciones?' selected':''}>${esc(s.nombre)} (${n})</option>`;}).join('')}</select>
          <div class="hint">De qué superintendencias se le muestran sanciones del sector, además de las de sus vigiladas.</div></div>
        <div class="pf-f"><label>Comisión de referencia</label>
          <select id="pf-com"><option value="">— ninguna —</option>${coms.map(c=>`<option value="${esc(c)}"${c===d.comision?' selected':''}>Comisión ${esc(c)}</option>`).join('')}</select>
          <div class="hint">Solo para redactar la acción sugerida cuando un proyecto no trae comisión propia.</div></div>
      </div>
      <div class="pf-acts">
        <button class="btn-t" id="pf-save">${d.perfilId?'Guardar cambios':'Crear perfil'}</button>
        <button class="btn-g" id="pf-cancel">Cancelar</button>
        ${d.perfilId?'<button class="btn-g danger" id="pf-del">Borrar</button>':''}
        ${(!d.perfilId&&plans.length)?`<span class="pf-lbl" style="margin-left:.5rem">plantilla</span>`+plans.map(p=>`<span class="chip" data-pftpl="${esc(p.k)}">${esc(p.nombre)}</span>`).join(''):''}
        <span class="pf-msg" id="pf-msg"></span>
      </div>`;
    pfRenderTags();
    const ni=document.getElementById('pf-nombre'); if(ni&&!d.nombre) ni.focus();
  }
  /* ---------- alertas por correo del perfil ----------
     Un interruptor y su estado, nada más. El motor de alertas
     (tools/caudal/alertas/) solo ve los perfiles que estén encendidos, y el
     default es apagado: un perfil no manda correos hasta que alguien lo diga. */
  // El horario lo fija el agente de launchd (co.ricardoruiz.caudal-alertas), no
  // esta página: hoy dispara lunes 07:00 y viernes 12:00. Si allá se cambia el
  // plist, este texto hay que moverlo con él — es la única copia que el cliente ve.
  const PF_CAD_TXT={'cada-corrida':'lunes y viernes','diaria':'una vez al día','semanal':'los lunes'};
  // Estado de alertas del perfil abierto. Se prefiere lo que trae el propio
  // perfil; si viene de la barra (resumen), se cae al de la lista.
  function pfAlertasDe(p){
    if(p&&p.alertas) return p.alertas;
    const l=PF_LIST.find(x=>p&&x.perfilId===p.perfilId);
    return (l&&l.alertas)||{activo:false};
  }
  function pfAlertasHTML(p){
    const a=pfAlertasDe(p), on=a.activo===true;
    const cad=a.cadencia||PF_CADENCIA||'semanal';
    return `<div class="pf-al${on?' on':''}" id="pf-alertas" data-on="${on?1:0}"
                 title="Prende o apaga el correo de alertas de «${esc(p.nombre||'')}»">
      <span class="sw"></span>
      <span class="t">Alertas por correo</span>
      <span class="s">${on
        ?'encendidas · '+esc(PF_CAD_TXT[cad]||cad)+', con los temas y las empresas de este perfil'
        :'apagadas · este perfil no manda correos'}</span></div>`;
  }
  async function pfToggleAlertas(){
    const el=document.getElementById('pf-alertas'), p=PF_ACTIVE;
    if(!el||!p||!p.perfilId||el.classList.contains('busy')) return;
    const nuevo=el.dataset.on!=='1';
    el.classList.add('busy');
    try{
      const r=await wcall('/caudal/perfil/alertas',{method:'POST',
        body:JSON.stringify({perfilId:p.perfilId,activo:nuevo})});
      p.alertas=r.alertas||{activo:nuevo};
      await pfLoadList();                    // repinta la barra con el estado nuevo
    }catch(err){
      el.classList.remove('busy');
      const s=el.querySelector('.s');
      if(s) s.textContent='no se pudo cambiar: '+(err.message||'error');
    }
  }
  function pfRenderTags(){
    const d=PF_DRAFT; if(!d) return;
    const t=document.getElementById('pf-temas'), e=document.getElementById('pf-emps');
    if(t) t.innerHTML=d.temas.length?d.temas.map((x,i)=>`<span class="chip on">${esc(x)}<span class="x" data-rmtema="${i}">×</span></span>`).join(''):'<span class="cob-note" style="margin:0">Sin temas.</span>';
    const li=document.getElementById('pf-lineas');
    if(li) li.innerHTML=(d.lineas||[]).length?d.lineas.map((x,i)=>`<span class="chip on">${esc(x)}<span class="x" data-rmlinea="${i}">×</span></span>`).join(''):'<span class="cob-note" style="margin:0">Sin líneas — se rastrea como un solo negocio.</span>';
    if(e) e.innerHTML=d.empresas.length?d.empresas.map((x,i)=>`<span class="chip on">${esc(x)}<span class="x" data-rmemp="${i}">×</span></span>`).join(''):'<span class="cob-note" style="margin:0">Sin empresas vigiladas.</span>';
    // Un aviso de validación («tema de menos de 3 letras», «máximo N temas»)
    // se quedaba en pantalla después de que el usuario ya había corregido, y
    // hace leer como error un formulario que está sano. Cualquier cambio en
    // los tags lo retira.
    pfMsg('');
  }
  function pfMsg(txt,okc){ const m=document.getElementById('pf-msg'); if(m){ m.className='pf-msg'+(okc?' okmsg':''); m.textContent=txt||''; } }
  function pfLeerForm(){
    const d=PF_DRAFT; if(!d) return;
    const g=id=>{const el=document.getElementById(id); return el?el.value:'';};
    const n=document.getElementById('pf-nombre'), de=document.getElementById('pf-desc'), s=document.getElementById('pf-sec'), c=document.getElementById('pf-com');
    if(n) d.nombre=n.value.trim(); if(de) d.descripcion=de.value.trim();
    if(s) d.sector_sanciones=s.value; if(c) d.comision=c.value;
  }
  async function pfGuardar(opts){
    pfLeerForm(); const d=PF_DRAFT; if(!d) return;
    if(!d.nombre) return pfMsg('Ponle un nombre al perfil.');
    if(!d.temas.length&&!d.empresas.length) return pfMsg(
      d.tipo!=='gremio'
        ? 'Agrega al menos un tema que le aplique, o un competidor a seguir.'
        : 'Agrega al menos un tema o una empresa vigilada.');
    pfMsg('Guardando…');
    const btn=document.getElementById(opts&&opts.wizard?'pf-wiz-next':'pf-save');
    if(btn){ btn.disabled=true; btn.textContent='Guardando…'; }
    try{
      const r=await wcall('/caudal/perfil/save',{method:'POST',body:JSON.stringify(d)});
      PF_ACTIVE=r.perfil;
      if(opts&&opts.wizard){ delete modalCard.dataset.pfWizard; modal.classList.remove('on'); }
      pfCerrarEdit(); await pfLoadList();
      document.querySelectorAll('#cli-sectors .chip').forEach(c=>c.classList.remove('on'));
      cliLoad({perfil:PF_ACTIVE});
    }catch(err){
      pfMsg(err.message||'No se pudo guardar.');
      if(btn){ btn.disabled=false; btn.textContent=opts&&opts.wizard?'Crear perfil':(d.perfilId?'Guardar cambios':'Crear perfil'); }
    }
  }
  async function pfBorrar(){
    const d=PF_DRAFT; if(!d||!d.perfilId) return;
    if(!confirm('¿Borrar el perfil «'+d.nombre+'»? Los datos de Caudal no se tocan, solo se borra el perfil.')) return;
    pfMsg('Borrando…');
    try{
      await wcall('/caudal/perfil/delete?perfilId='+encodeURIComponent(d.perfilId),{method:'DELETE'});
      if(PF_ACTIVE&&PF_ACTIVE.perfilId===d.perfilId){ PF_ACTIVE=null; const b=document.getElementById('cli-body'); if(b) b.innerHTML='<div class="cli-empty">Elige un perfil o un sector arriba para orientarlo.</div>'; }
      pfCerrarEdit(); await pfLoadList();
    }catch(err){ pfMsg(err.message||'No se pudo borrar.'); }
  }
  async function pfAbrir(perfilId){
    try{
      const d=await wcall('/caudal/perfil/load?perfilId='+encodeURIComponent(perfilId));
      PF_ACTIVE=d.perfil; pfCerrarEdit(); pfRenderBar();
      document.querySelectorAll('#cli-sectors .chip').forEach(c=>c.classList.remove('on'));
      cliLoad({perfil:PF_ACTIVE});
    }catch(err){ const b=document.getElementById('cli-body'); if(b) b.innerHTML='<div class="err">No se pudo abrir el perfil: '+esc(err.message)+'</div>'; }
  }
  // autocompletado de empresas contra el diccionario (④), vía la Lambda
  let _pfSugSeq=0;
  async function pfSugerir(q){
    const box=document.getElementById('pf-sug'); if(!box) return;
    if(!q||q.trim().length<2){ box.hidden=true; box.innerHTML=''; return; }
    const mine=++_pfSugSeq;
    let d; try{ d=await call({action:'empresas',query:q}); }catch(e){ return; }
    if(mine!==_pfSugSeq) return;
    const box2=document.getElementById('pf-sug'); if(!box2) return;
    const list=(d.empresas||[]).filter(e=>!(PF_DRAFT&&PF_DRAFT.empresas.includes(e.k)));
    if(!list.length){ box2.hidden=false; box2.innerHTML='<div style="color:var(--ink3)">Nada en el diccionario para «'+esc(q)+'».</div>'; return; }
    box2.hidden=false;
    box2.innerHTML=list.map(e=>`<div data-pfemp="${esc(e.k)}">${esc(e.nombre)}<span class="s">${esc(e.tipo==='gremio'?'gremio':e.sector)}${e.nucleo&&e.nucleo.length?' · '+esc(e.nucleo[0]):''}</span></div>`).join('');
    // El editor normal usa delegación sobre la vista. El asistente vive en el
    // modal global, por eso sus sugerencias se conectan aquí al nacer.
    if(PF_WIZARD_STEP===4&&modal.classList.contains('on')) box2.querySelectorAll('[data-pfemp]').forEach(x=>x.onclick=()=>{
      if(PF_DRAFT&&!PF_DRAFT.empresas.includes(x.dataset.pfemp)) PF_DRAFT.empresas.push(x.dataset.pfemp);
      pfRenderWizard();
    });
  }

  function cliSigCard(x){
    // ★ vigilada: la señal es sobre una empresa del perfil, no sobre su sector.
    const cls=`sig ${x.nivel}${x.vigilada?' vig':''}`;
    // el <wbr> no es decorativo: las etiquetas son `white-space:nowrap` y se
    // concatenan SIN espacio, así que dos seguidas ("Investigación abierta" +
    // "★ Cerrejón") forman una tira que el navegador no puede partir y se sale
    // de la tarjeta en móvil. Medido a 375px: 302px de contenido en 230 de caja.
    const vt=x.vigilada?`<span class="vig-tag">★ ${esc(x.vigilada)}</span><wbr>`:'';
    if(x.tipo==='congreso'){
      const tags=[x.comision?esc(x.comision):'', x.anio||'', RES_TXT[x.resultado]||''].filter(Boolean).join(' · ');
      // qué CAMBIA el proyecto (extracción del articulado) + el cruce con el
      // perfil: ahí está el valor, no en el título del proyecto.
      const a=x.articulado, ap=x.te_aplica;
      let art='';
      if(a){
        const bits=[];
        if(a.n_obligaciones) bits.push(`<b>${a.n_obligaciones}</b> obligación(es) nueva(s)`);
        if(a.n_sanciones) bits.push(`<b>${a.n_sanciones}</b> sanción(es)`);
        if((a.modifica||[]).length) bits.push(`modifica ${esc(a.modifica.map(m=>m.norma).join(', '))}`);
        const suj=(a.obligaciones&&a.obligaciones[0]&&a.obligaciones[0].sobre_quien)||(a.sujetos||[])[0];
        art=`<div class="sig-art">${a.resumen?esc(a.resumen):''}${bits.length?`<div style="margin-top:.25rem;color:var(--ink3)">${bits.join(' · ')}${suj?` · recae sobre ${esc(suj)}`:''}</div>`:''}
          <div style="margin-top:.2rem;font-size:.6rem;color:var(--ink3)">Leído de ${esc(a.base_txt||'—')}</div></div>`;
      }
      const apTag=ap?`<span class="sig-aplica" title="El articulado toca ${esc((ap.sectores||[]).join(', '))}${(ap.vigiladas||[]).length?' · vigiladas: '+esc(ap.vigiladas.join(', ')):''}">te aplica</span>`:'';
      return `<div class="${cls}"><span class="sig-lvl">${x.nivel}</span><div class="sig-body">
        <div class="sig-title">${apTag}${vt}${esc(shortTitle(x.titulo).slice(0,120))}</div>
        <div class="sig-tags">${tags}</div>${art}<div class="sig-action">${esc(x.accion)}</div></div></div>`;
    }
    if(x.tipo==='medios'){
      const tags=[x.medio?esc(x.medio):'', x.alcance==='regional'?'Regional':'Nacional', x.fecha?esc(x.fecha):''].filter(Boolean).join(' · ');
      return `<div class="${cls}"><span class="sig-lvl">${x.nivel}</span><div class="sig-body">
        <div class="sig-title">${vt}<a href="${esc(x.url)}" target="_blank" rel="noopener" style="color:inherit;text-decoration:none">${esc(x.titulo)}</a></div>
        <div class="sig-tags">${tags}</div><div class="sig-action">${esc(x.accion)}</div></div></div>`;
    }
    if(x.tipo==='contratacion'){
      const tags=[x.proveedor?esc(x.proveedor):'', x.departamento?esc(x.departamento):'', x.fecha?esc(x.fecha):'',
                  x.valor?fmtCOP(x.valor):''].filter(Boolean).join(' · ');
      const tit=x.url
        ?`<a href="${esc(x.url)}" target="_blank" rel="noopener" style="color:inherit;text-decoration:none">${esc(x.entidad||'—')}</a>`
        :esc(x.entidad||'—');
      return `<div class="${cls}"><span class="sig-lvl">${x.nivel}</span><div class="sig-body">
        <div class="sig-title">${vt}${tit}</div>
        ${x.objeto?`<div class="sig-tags" style="opacity:.85">${esc(x.objeto)}</div>`:''}
        <div class="sig-tags">${tags}</div><div class="sig-action">${esc(x.accion)}</div></div></div>`;
    }
    const monto=x.monto?' · '+fmtCOP(x.monto):'';
    // el pilar Regulatorio ya no es solo sanciones: desde que entró la ANLA una
    // señal puede ser una resolución de seguimiento, una investigación abierta o
    // un archivo. Se dice cuál es en la tarjeta — llamarle "sanción" a un
    // archivo sería el peor error posible acá.
    const acto=(x.acto&&x.acto!=='sancion'&&x.acto_lbl)?`<span class="acto-tag">${esc(x.acto_lbl)}</span><wbr>`:'';
    return `<div class="${cls}"><span class="sig-lvl">${x.nivel}</span><div class="sig-body">
      <div class="sig-title">${acto}${vt}${esc(x.sancionado||'—')}</div>
      <div class="sig-tags">${esc(x.fuente||'')}${x.tipo_sancion?' · '+esc(x.tipo_sancion):''}${x.fecha?' · '+esc(x.fecha):''}${monto}</div>
      ${x.motivo?`<div class="sig-tags" style="opacity:.85">${esc(x.motivo)}</div>`:''}
      <div class="sig-action">${esc(x.accion)}</div></div></div>`;
  }
  let _CLI_LAST=null;
  function cliDetalleHTML(pilar,d){
    const cl=d.cliente, congreso=d.congreso||[], reg=d.regulatorio||[], medios=d.medios||[], con=d.contratacion||[];
    if(pilar==='congreso') return congreso.length?`<div class="sig-list">${congreso.map(cliSigCard).join('')}</div>`:'<div class="cli-reg-none">Sin proyectos accionables ahora.</div>';
    if(pilar==='regulatorio') return cl.sector_sanciones
      ? (reg.length?`<div class="sig-list">${reg.map(cliSigCard).join('')}</div>`:'<div class="cli-reg-none">Sin actos recientes del regulador en esta fuente.</div>')
      : '<div class="cli-reg-none">El regulador de este sector todavía no es fuente de Caudal — las entidades entran por etapas. Si tu exposición es ambiental (licenciamiento, seguimiento, sanción), el sector <b>Ambiente</b> ya trae el expediente completo de la ANLA.</div>';
    if(pilar==='contratacion') return con.length?`<div class="sig-list">${con.map(cliSigCard).join('')}</div>`:'<div class="cli-reg-none">Sin contratación reciente para los temas de este sector.</div>';
    if(pilar==='medios') return medios.length?`<div class="sig-list">${medios.map(cliSigCard).join('')}</div>`:'<div class="cli-reg-none">Sin cobertura de prensa reciente para este sector.</div>';
    return '';
  }
  function cliRender(d){
    const body=document.getElementById('cli-body'); if(!body) return;
    _CLI_LAST=d;
    const k=d.kpis, cl=d.cliente, congreso=d.congreso||[], reg=d.regulatorio||[], medios=d.medios||[], con=d.contratacion||[];
    // el bloque regulatorio puede traer sanciones o —desde la ANLA— resoluciones,
    // aperturas y archivos. Se nombra por lo que de verdad trae, no por lo que
    // solía traer.
    const soloSanc=reg.every(x=>!x.acto||x.acto==='sancion');
    const sancTxt=cl.sector_sanciones
      ? `<b>${reg.length}</b> ${soloSanc?'sanción(es) reciente(s)':'acto(s) reciente(s) del regulador'}`
      : `regulador sectorial sin fuente conectada`;
    const vigN=k.n_vigiladas||0;
    const vigNoms=(cl.empresas||[]).map(e=>e.nombre).join(' · ');
    // qué cubre y qué NO cubre el preset — importa sobre todo en Mipymes, que
    // es un tamaño de empresa y no una actividad, y en Energía, cuyo expediente
    // ambiental vive en otro sector.
    // el chip va corto por espacio, así que el nombre completo del sector se
    // dice acá, junto con lo que cubre y lo que NO.
    const secDesc=cl.es_perfil ? ''
      : `<div class="cob-note" style="margin-bottom:1rem"><b>${esc(cl.nombre)}.</b>${cl.descripcion?' '+esc(cl.descripcion):''}</div>`;
    // lo que el diccionario no reconoció: se dice, no se esconde
    const desc=(cl.descartes&&cl.descartes.length)
      ? `<div class="cli-reg-none" style="margin-bottom:1rem">No están en el diccionario de Caudal y quedaron fuera de ${MARCA.nombre}: <b>${esc(cl.descartes.join(', '))}</b>. Búscalas otra vez en el editor: si no aparecen, todavía no las cubrimos.</div>` : '';
    // el perfil llegó mal formado (campo con otro nombre, lista que era texto):
    // se dice en vez de devolver un radar vacío en silencio
    const avi=(cl.avisos&&cl.avisos.length)
      ? `<div class="cli-reg-none" style="margin-bottom:1rem">El perfil llegó con algo que Caudal no entendió: <b>${esc(cl.avisos.join(' · '))}</b>. ${MARCA.nombre} se armó sin eso.</div>` : '';
    // Una empresa multi-negocio no tiene UNA comisión: se muestran sus líneas
    // con la comisión de cada una, que es el argumento del perfil.
    const lineasHTML=(cl.lineas&&cl.lineas.length)
      ? `<div class="cli-note"><b>Líneas de negocio (${cl.lineas.length}):</b> `
        + cl.lineas.map(l=>`${esc(l.nombre)} <span class="ln-com">${esc(l.comision)}</span>`).join(' · ')
        + ` · <b>${[...new Set(cl.lineas.map(l=>l.comision))].length} comisiones</b> distintas — por eso no tiene una sola.</div>` : '';
    // Alcance: si el cliente sigue países que Caudal no cubre, se dice. Dejar
    // que lo asuma es el error caro.
    const alcanceHTML=(cl.fuera_de_alcance&&cl.fuera_de_alcance.length)
      ? `<div class="cli-note cli-alcance"><b>Alcance:</b> Caudal cubre hoy solo el tramo <b>colombiano</b>. Este cliente también sigue ${esc(cl.fuera_de_alcance.join(' · '))}, que no están cubiertos por ninguna fuente de Caudal.</div>` : '';
    const vigNote=vigN
      ? `<div class="cli-note"><b>${cl.tipo==='empresa'?'Competencia':'Vigiladas'} (${vigN}):</b> ${esc(vigNoms)} · <b>${k.n_senales_vigiladas||0}</b> señal(es) de ${MARCA.nombre} son sobre ellas${k.n_contratos_vigiladas?` · <b>${fmt(k.n_contratos_vigiladas)}</b> contrato(s) suyos en SECOP`:(cl.vigiladas_sin_contratos?' · no le venden al Estado en SECOP II':'')}.</div>` : '';
    body.innerHTML=`
      <div class="kpis">
        <div class="kpi"><div class="n">${k.n_radar}</div><div class="l">Señales en ${MARCA.articulo} ${MARCA.nombre}</div></div>
        <div class="kpi vit"><div class="n">${k.alto}</div><div class="l">Alta prioridad</div></div>
        <div class="kpi ley"><div class="n">${k.en_tramite}</div><div class="l">En trámite · ventana</div></div>
        <div class="kpi"><div class="n">${vigN?(k.n_senales_vigiladas||0):(k.n_medios_sector?fmt(k.n_medios_sector):'—')}</div><div class="l">${vigN?(cl.tipo==='empresa'?'Sobre tu competencia':'Sobre tus vigiladas'):'Prensa reciente'}</div></div>
      </div>
      ${secDesc}${avi}${desc}${lineasHTML}${alcanceHTML}${vigNote}
      <div class="cli-note"><b>Activo ahora en ${esc(cl.nombre)}:</b> <b>${k.en_tramite}</b> proyecto(s) de ley en trámite · ${sancTxt} · <b>${fmt(k.n_medios_sector||0)}</b> titular(es) de prensa reciente · <b>${fmt(k.n_contratos_sector||0)}</b> contrato(s) reciente(s) en SECOP.</div>
      ${k.n_con_articulado?`<div class="cli-note"><b>Qué cambian:</b> de las ${congreso.length} señales del Congreso, <b>${k.n_con_articulado}</b> ya tienen el articulado leído${k.n_te_aplica?` y <b>${k.n_te_aplica}</b> le aplican a tu sector o a tus vigiladas`:''}. El resto todavía no se ha extraído.</div>`:''}
      <div class="cob-note" style="margin:.5rem 0 1.3rem">De un histórico de <b>${fmt(k.n_proyectos_sector)}</b> proyectos${cl.sector_sanciones?` y <b>${fmt((k.n_sanciones_sector||0)+(k.n_otros_actos_sector||0))}</b> actos del regulador (<b>${fmt(k.n_sanciones_sector)}</b> de ellos sanciones)`:''} que tocan estos temas, ${MARCA.nombre} prioriza por accionabilidad — precisión sobre volumen.${(cl.temas_usados&&cl.temas_usados.length)?` Se buscó por: <b>${esc(cl.temas_usados.join(' · '))}</b>.`:''}</div>
      <div class="lectura">
        <div class="tag">◈ Lectura del analista · briefing de hoy para ${esc(cl.nombre)}</div>
        <div id="cli-lectura-body"><div class="llm-load">Generando lectura <span class="dots"><span></span><span></span><span></span></span></div></div>
      </div>
      <div class="cli-sub">Explorar el detalle</div>
      <div class="chips" id="cli-toggle" style="justify-content:flex-start;margin-top:.3rem">
        <span class="chip" data-p="congreso">Legislativo <b>${congreso.length}</b></span>
        <span class="chip" data-p="regulatorio">Regulatorio <b>${reg.length}</b></span>
        <span class="chip" data-p="contratacion">Contratación <b>${con.length}</b></span>
        <span class="chip" data-p="medios">Prensa <b>${medios.length}</b></span>
      </div>
      <div id="cli-detalle" style="margin-top:1rem"></div>

      <div class="cli-sub" style="margin-top:1.6rem">El expediente de ${esc(cl.nombre)}</div>
      <div class="tb-intro">${MARCA.nombre} dice <b>qué se movió</b>. Esto dice
        <b>cómo va cada frente</b>, se haya movido o no — el registro que un equipo
        suele llevar a mano en un Excel y que se desactualiza solo.</div>
      <div id="cli-tablero"><button class="tb-btn" id="tb-load">Abrir el expediente →</button></div>`;
  }

  // ── EXPEDIENTE DEL CLIENTE ───────────────────────────────────────────────
  // Es la otra mitad del radar y se carga aparte, bajo demanda: recorre los
  // cuatro pilares completos y no tiene por qué retrasar la primera pantalla.
  const TB_CLS={consulta:'urg',tramite:'viv',vigente:'vig',cerrado:'cer'};
  let TB_ARG=null;
  function tbRender(d){
    const box=document.getElementById('cli-tablero'); if(!box) return;
    const k=d.kpis||{};
    const grupos=(d.grupos||[]).filter(g=>g.n>0).map(g=>`
      <div class="tb-grupo ${TB_CLS[g.k]||''}">
        <div class="tb-gh"><b>${esc(g.nombre)}</b> <span>${g.n}</span></div>
        <div class="tb-gn">${esc(g.nota||'')}</div>
        <table class="tb-tab">
          <tr><th style="width:16%">Referencia</th><th style="width:38%">Norma o proyecto</th>
              <th style="width:24%">Entidad</th><th style="width:12%">Estado</th><th>Fecha</th></tr>
          ${g.items.map(it=>`<tr>
            <td class="tb-ref">${esc(it.ref||'—')}</td>
            <td>${it.url?`<a href="${esc(it.url)}" target="_blank" rel="noopener">${esc(it.titulo)}</a>`:esc(it.titulo)}
                <div class="tb-tipo">${esc(it.tipo||'')}</div></td>
            <td class="tb-q">${esc(it.entidad||'—')}</td>
            <td class="tb-q">${esc(it.estado||'—')}${it.cierra?`<div class="tb-cierra">cierra ${esc(it.cierra)}</div>`:''}</td>
            <td class="tb-q">${esc((it.fecha||'').slice(0,10))}</td></tr>`).join('')}
        </table>
        ${g.n>g.items.length?`<div class="tb-gn">Se muestran ${g.items.length} de ${g.n}.</div>`:''}
      </div>`).join('');
    // El descarte se dice, no se esconde: si un tema importa y solo aparece en
    // el articulado, la salida es agregarlo al perfil.
    const nota=d.solo_en_texto?`<div class="tb-nota">${d.solo_en_texto} proyecto(s) más
      mencionan estos temas dentro de su articulado pero no en el título, así que no entran
      al expediente. Si alguno debería estar, agrega ese tema al perfil.</div>`:'';
    box.innerHTML=`<div class="tb-kpis">
        <span><b>${k.total||0}</b> frentes</span><span><b>${k.consulta||0}</b> en consulta</span>
        <span><b>${k.tramite||0}</b> en trámite</span><span><b>${k.vigente||0}</b> vigentes</span>
        <span><b>${k.cerrado||0}</b> cerrados</span>
        <span class="tb-hoy">al ${esc(d.hoy||'')}</span>
      </div>${grupos||'<div class="cli-empty">Sin frentes registrados para este perfil.</div>'}${nota}`;
  }
  document.addEventListener('click',ev=>{
    if(ev.target&&ev.target.id==='tb-load'&&TB_ARG) tbLoad(TB_ARG);
  });
  async function tbLoad(arg){
    const box=document.getElementById('cli-tablero'); if(!box) return;
    box.innerHTML='<div class="llm-load">Armando el expediente <span class="dots"><span></span><span></span><span></span></span></div>';
    try{ tbRender(await call({action:'tablero',...arg})); }
    catch(e){ box.innerHTML='<div class="cli-empty">No se pudo armar el expediente. Reintenta en un momento.</div>'; }
  }
  /* La lectura ya no es un briefing plano: son las cuatro direcciones, cada una
     con su resumen. El contador «N en 72 h» sale de kpis.cardinales y es lo que
     separa lo que se movió de lo que solo está vigente — sin él, una dirección
     quieta y una activa se ven igual. */
  const CARD_ORD=[['norte','N','Norte · oportunidades'],['este','E','Oriente · conversación'],
                  ['sur','S','Sur · competencia'],['oeste','O','Occidente · Estado']];
  function cliRenderLectura(l){
    const body=document.getElementById('cli-lectura-body'); if(!body) return;
    const _k=(_CLI_LAST&&_CLI_LAST.kpis)||{};
    const cc=_k.cardinales||{}, md=_k.mov_dias||3;
    const partes=CARD_ORD.map(([k,letra,nom])=>{
      const t=(l[k]||'').trim(); if(!t) return '';
      const c=cc[k]||{}, mov=c.mov||0, tot=c.total||0;
      // el sello dice de un vistazo si esa dirección trajo noticia o está quieta
      const sello=mov ? `<span class="lc-mov">${mov} en ${md*24} h</span>`
                      : `<span class="lc-quieto">sin movimiento${tot?` · ${tot} vigente${tot>1?'s':''}`:''}</span>`;
      return `<div class="lc-card"><div class="lc-top"><span class="lc-let">${letra}</span>`
           + `<span class="lc-nom">${nom}</span>${sello}</div>`
           + `<div class="lc-t">${esc(t)}</div></div>`;
    }).join('');
    const blk=(h,t)=>t?`<div class="blk"><div class="h">${h}</div><div class="t">${esc(t)}</div></div>`:'';
    const acc=(l.acciones&&l.acciones.length)?`<div class="blk"><div class="h">Acciones</div>${l.acciones.map(a=>`<div class="acc">${esc(a)}</div>`).join('')}</div>`:'';
    body.innerHTML=(l.titular?`<div class="blk"><div class="t" style="font-weight:700;font-size:.95rem;color:var(--ink)">${esc(l.titular)}</div></div>`:'')
      + (partes?`<div class="lc-grid">${partes}</div>`:'')
      // compatibilidad: lecturas cacheadas de antes del cambio traen el campo viejo
      + blk('Lo que mueve la aguja', l.lo_que_importa)
      + acc + blk('En el horizonte', l.horizonte)
      || '<div class="cob-note">Sin lectura disponible.</div>';
  }
  // `arg` = {sector:'salud'} (preset/demo) o {perfil:{…}} (el perfil del cliente).
  // El resto del flujo es idéntico: los presets siguen siendo el fallback.
  async function cliLoad(arg){
    const mine=++_cliSeq;
    cliLecturaStop();
    const esPerfil=!!(arg&&arg.perfil);
    if(esPerfil){ PF_ACTIVE=arg.perfil; document.querySelectorAll('#cli-sectors .chip').forEach(c=>c.classList.remove('on')); }
    else { PF_ACTIVE=null; document.querySelectorAll('#cli-sectors .chip').forEach(c=>c.classList.toggle('on',c.dataset.sec===arg.sector)); }
    pfRenderBar();
    const p=esPerfil?arg.perfil:null;
    // `lectura:true` = "prepárala", no "espérala": la respuesta trae el radar
    // y una `lectura_key` para recogerla aparte (ver cliPedirLectura).
    const req=esPerfil
      ? {action:'cliente',lectura:true,
         perfil:{nombre:p.nombre,descripcion:p.descripcion||'',temas:p.temas||[],
                 empresas:p.empresas||[],sector_sanciones:p.sector_sanciones||'',
                 comision:p.comision||''}}
      : {action:'cliente',lectura:true,sector:arg.sector};
    const body=document.getElementById('cli-body');
    const quien=esPerfil?('de '+esc(p.nombre||'tu cliente')):'del sector';
    if(body) body.innerHTML='<div class="llm-load" style="padding:2.5rem;justify-content:center">Armando '+MARCA.articulo+' '+MARCA.nombre+' '+quien+' <span class="dots"><span></span><span></span><span></span></span></div>';
    let d; try{ d=await call(req); }
    catch(e){ if(mine===_cliSeq&&body) body.innerHTML='<div class="err">No se pudo cargar '+MARCA.articulo+' '+MARCA.nombre+'. Reintenta.</div>'; return; }
    if(mine!==_cliSeq) return;
    if(d&&d.error){ if(body) body.innerHTML='<div class="err">'+esc(d.error)+'</div>'; return; }
    // el expediente se pide con el mismo `arg` del radar, pero solo cuando el
    // usuario lo abre: recorre los cuatro pilares enteros
    TB_ARG = esPerfil ? {perfil:req.perfil} : {sector:arg.sector};
    cliRender(d);
    // el radar ya está en pantalla; la lectura llega después (o ya venía hecha)
    // Sin acceso ni se pide: el worker devuelve 403 a `cliente-lectura`, y eso
    // le pintaría un error al visitante donde debería ir una invitación.
    if(!ACCESO) cliMuroLectura();
    else if(d.lectura && !d.lectura.error) cliRenderLectura(d.lectura);
    else if(d.lectura_key) cliPedirLectura(d.lectura_key, mine);
    else cliLecturaFallback();
  }
  function cliLecturaFallback(msg){
    const el=document.getElementById('cli-lectura-body'); if(!el) return;
    el.innerHTML='<div class="cob-note">'+esc(msg||'No se pudo generar la lectura. Lo de arriba está completo.')+'</div>';
  }
  // El muro del radar: el briefing es justamente lo que se vende acá, así que en
  // vez de un error va la invitación, en el mismo sitio donde iría la lectura.
  function cliMuroLectura(){
    const el=document.getElementById('cli-lectura-body'); if(!el) return;
    el.innerHTML=`<div class="muro-t" style="margin-bottom:.7rem">Acá va el briefing del día: qué señales de las de arriba mueven la aguja, por qué, y qué hacer con cada una. Se escribe sobre esto mismo, y va con acceso.</div>`
      + `<a class="muro-btn" href="${window.COMPRA_URL||'caudal-portada.html?comprar=1'}">Conseguir acceso →</a>`
      + ` <a class="muro-btn" style="opacity:.75" href="${mailtoHref('acceso · '+MARCA.nombre)}">o escríbenos · ${CONTACTO_MAIL}</a>`;
  }
  // La lectura se genera aparte del radar: medida contra producción tarda entre
  // 20 s y 51 s (la varianza es del modelo), o sea que se pasa del techo de
  // 30 s del API Gateway sin que haya forma de predecirlo. Así que se dispara
  // una vez y se recoge SONDEANDO el caché — un GET a S3, ~0,3 s. Si el modelo
  // alcanza a contestar dentro del gateway, el disparo la trae de una y el
  // sondeo se apaga; si lo cortan, la Lambda igual termina y el sondeo la pesca.
  const CLI_LECT_POLL=3500, CLI_LECT_MAX=90000;
  let _cliLectTimer=null;
  function cliLecturaStop(){ if(_cliLectTimer){ clearTimeout(_cliLectTimer); _cliLectTimer=null; } }
  function cliPedirLectura(key, mine){
    cliLecturaStop();
    const t0=Date.now();
    const listo=d=>{
      if(mine!==_cliSeq || !d || d.estado!=='lista' || !d.lectura || d.lectura.error) return false;
      cliLecturaStop(); cliRenderLectura(d.lectura); return true;
    };
    // 1 · disparo: arranca la generación. Puede morir en el gateway a los 30 s
    //     (503) y no pasa nada — la Lambda termina y deja la lectura hecha.
    call({action:'cliente-lectura',key}).then(d=>{
      if(mine!==_cliSeq || listo(d)) return;
      if(d && d.estado==='sin_radar'){ cliLecturaStop(); return cliLecturaFallback('La lectura caducó. Vuelve a abrir '+MARCA.articulo+' '+MARCA.nombre+' para regenerarla.'); }
      // el modelo respondió pero mal: no se cachea, así que sondear no sirve
      if(d && d.estado==='lista'){ cliLecturaStop(); cliLecturaFallback(); }
    }).catch(()=>{});
    // 2 · sondeo del caché en paralelo
    const tick=()=>{
      if(mine!==_cliSeq) return cliLecturaStop();
      if(Date.now()-t0>CLI_LECT_MAX){ cliLecturaStop(); return cliLecturaFallback(); }
      if(Date.now()-t0>12000){
        const el=document.getElementById('cli-lectura-body');
        if(el && !el.dataset.slow){ el.dataset.slow='1'; el.innerHTML='<div class="llm-load">La primera lectura de un perfil tarda un poco más <span class="dots"><span></span><span></span><span></span></span></div>'; }
      }
      call({action:'cliente-lectura',key,solo_cache:true})
        .then(d=>{ if(!listo(d)) _cliLectTimer=setTimeout(tick,CLI_LECT_POLL); })
        .catch(()=>{ if(mine===_cliSeq) _cliLectTimer=setTimeout(tick,CLI_LECT_POLL); });
    };
    _cliLectTimer=setTimeout(tick,CLI_LECT_POLL);
  }

  /* `cliInit` lo llama initHome; `pfLoadList`, caudal-base.js al abrir sesión. */
  Object.assign(window, { cliInit, pfLoadList });
})();
