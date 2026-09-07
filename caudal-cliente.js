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
  // Son prospectos con nombre propio: un usuario nuevo no tiene por qué ver
  // quién está en conversaciones con Cauce (reportado por Ricardo, sep-7-2026:
  // los vio con una cuenta recién creada). Solo el equipo los ve como muestra.
  const EQUIPO=['reruizc@gmail.com','nuevagemela@gmail.com','diego@cauce.co'];
  function esEquipo(){
    try{ const u=JSON.parse(localStorage.getItem('rr-user')||'null'); return !!(u&&EQUIPO.includes(String(u.email||'').toLowerCase())); }catch(e){ return false; }
  }
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
    if(sub) sub.textContent='Crea el perfil de un cliente o explora un sector. El radar cruza el Estado, la competencia, la conversación pública y las oportunidades para priorizar qué necesita atención.';
    const r=document.getElementById('cli-rosa');
    if(r){
      r.innerHTML=`<div class="sext-stage">
        <img src="imagenes/caudal-sextante-mar.jpg" alt="" />
        ${MARCA.puntos.map(p=>`<button type="button" class="sext-pt ${p.dir}" data-c="${p.c}" aria-label="${esc(p.rumbo)}: ${esc(p.t)}"><span class="sext-let">${esc(p.let||p.c)}</span><span class="sext-lab">${esc(p.rumbo)}</span></button>`).join('')}
        <div class="sext-desc" id="sextDesc" role="status" aria-live="polite"></div>
      </div>`;
      const desc=document.getElementById('sextDesc');
      r.querySelectorAll('.sext-pt').forEach(btn=>{
        btn.onclick=ev=>{
          ev.stopPropagation();
          const p=MARCA.puntos.find(x=>x.c===btn.dataset.c);
          if(!p||!desc) return;
          r.querySelectorAll('.sext-pt').forEach(b=>{b.classList.toggle('on', b===btn);b.setAttribute('aria-pressed',String(b===btn));});
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
    if(d) d.textContent='Sigue un sector o un cliente: el Estado, su competencia y la conversación pública, en un radar con señales priorizadas.';
    const g=document.querySelector('#radar-cta .rc-go'); if(g) g.textContent='Abrir radar →';
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
        const c=document.createElement('button'); c.type='button';
        c.className='chip sec-chip'+(reg?' con-reg':'')+(cls?' '+cls:'');
        c.dataset.sec=k; c.textContent=t;
        c.title=cls?'Perfil de cliente real · varias líneas de negocio'
                   :(reg?'Tiene fuente conectada en el pilar Regulatorio'
                       :'Su regulador sectorial todavía no es fuente de Caudal');
        c.onclick=()=>cliLoad({sector:k}); cont.appendChild(c); });
      if(esEquipo()) pinta(CLI_CLIENTES,'cli-real');
      const drill=document.createElement('details');
      drill.className='sec-drill';
      // El latido se apaga la primera vez que alguien lo abre, y no vuelve:
      // llamar la atención sobre algo que el usuario ya conoce es ruido.
      try{ if(localStorage.getItem('caudal-sec-visto')) drill.dataset.visto='1'; }catch(e){}
      drill.addEventListener('toggle',()=>{
        if(!drill.open) return;
        drill.dataset.visto='1';
        try{ localStorage.setItem('caudal-sec-visto','1'); }catch(e){}
      });
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
  // Cuál fue el último perfil que abrió esta cuenta. Es lo que permite que
  // Caudal ENTRE por el radar de su cliente en vez de por la portada de
  // pilares (pedido de Pablo: «lo último debería ser respecto de los temas que
  // el cliente tiene interés… el i-ching del día»). Va por cuenta, no global:
  // dos personas en el mismo navegador no comparten cliente.
  function _pfUltKey(){
    let em=''; try{ em=(JSON.parse(localStorage.getItem('rr-user')||'null')||{}).email||''; }catch(e){}
    return 'caudal-perfil-ult:'+(em||'anon');
  }
  function pfUltimoGuardar(perfilId){
    try{ localStorage.setItem(_pfUltKey(), perfilId||''); }catch(e){}
  }
  function pfUltimoLeer(){
    try{ return localStorage.getItem(_pfUltKey())||''; }catch(e){ return ''; }
  }
  // Abre solo: el último que usó, o el único que tenga. Si tiene varios y
  // ninguno marcado, NO elige por él — mostrar el radar del cliente equivocado
  // es peor que mostrar la lista.
  async function pfAutoAbrir(){
    if(!PF_LIST.length) return false;
    const ult=pfUltimoLeer();
    const cual=(ult&&PF_LIST.some(p=>p.perfilId===ult))?ult:(PF_LIST.length===1?PF_LIST[0].perfilId:'');
    if(!cual){
      // varios clientes y ninguno marcado: NO se elige por el usuario — abrir el
      // radar del cliente equivocado es peor que pedirle que escoja.
      const b=document.getElementById('cli-body');
      if(b) b.innerHTML='<div class="cob-note" style="margin:0">Escoge arriba el cliente con el que vas a trabajar hoy. Caudal recuerda el último y la próxima vez abre directo en él.</div>';
      return false;
    }
    await pfAbrir(cual);
    return true;
  }
  async function pfLoadList(){
    try{ const d=await wcall('/caudal/perfil/list'); PF_LIST=d.perfiles||[]; PF_LIMIT={usados:d.count,tope:d.ownedLimit,plan:d.plan}; PF_CADENCIA=d.cadencia||null; }
    catch(e){ PF_LIST=[]; PF_LIMIT=null; }
    // `pfBorrar` pone PF_ACTIVE en null ANTES de recargar, así que un perfil
    // recién borrado no puede revivir por aquí.
    pfMergeActivo();
    pfRenderBar();
    // la entrada automática espera a que exista la lista: se dispara acá, la
    // pida quien la pida (setAcceso o cliInit), y una sola vez.
    if(window.CLI_AUTO_PERFIL){ window.CLI_AUTO_PERFIL=false; pfAutoAbrir(); }
  }
  function pfRenderBar(){
    const bar=document.getElementById('cli-perfiles'); if(!bar) return;
    if(IS_GUEST){
      bar.innerHTML='<span class="pf-lbl">Perfiles de cliente</span><span class="cob-note" style="margin:0">Entra con tu cuenta para guardar los temas y las empresas de un cliente.</span>';
      return;
    }
    let h='<span class="pf-lbl">Perfiles de cliente</span>';
    const visibles=PF_LIST.filter(p=>(p.nombre||'').trim().toLowerCase()!=='prueba a2 editada');
    h+=visibles.map(p=>`<button type="button" class="chip${PF_ACTIVE&&PF_ACTIVE.perfilId===p.perfilId?' on':''}" data-pf="${esc(p.perfilId)}" title="${esc(p.n_temas)} tema(s) · ${esc(p.n_empresas)} empresa(s) vigilada(s)">${esc(p.nombre)}</button>`).join('');
    if(!visibles.length) h+='<span class="cob-note" style="margin:0">Todavía no tienes ninguno.</span>';
    h+='<button type="button" class="chip add" data-pfnew="1">+ Nuevo perfil</button>';
    if(PF_LIMIT) h+=`<span class="cob-note" style="margin:0">${PF_LIMIT.usados}/${PF_LIMIT.tope} · plan ${esc(PF_LIMIT.plan)}</span>`;
    // Puerta al editor del perfil abierto. Sin esto `pfEditar` quedaba huérfana
    // y un perfil guardado no se podía ni corregir ni borrar: `pfBorrar` exige
    // `PF_DRAFT.perfilId`, que solo existe cuando el editor abre uno existente.
    if(PF_ACTIVE&&PF_ACTIVE.perfilId)
      h+=`<button type="button" class="chip add" data-pfedit="1" title="Corregir los temas, las empresas o el nombre de «${esc(PF_ACTIVE.nombre||'')}»">✎ Editar</button>`;
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
      PF_ACTIVE=d.perfil; pfUltimoGuardar(perfilId); pfCerrarEdit(); pfRenderBar();
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
      // POR QUÉ IMPORTA · las tres coordenadas en una línea (solo legislatura viva)
      let imp='';
      if(x.importancia){
        const c=x.importancia, av=c.avance||{}, im=c.impacto||{}, po=c.politico||{};
        const BC={alto:'var(--green)',medio:'var(--amber)',bajo:'var(--red)'};
        const p=[];
        if(av.banda) p.push(`<span title="${esc(av.observado!=null?`de los que el modelo puso en «${av.banda}» (2015-2024), llegó a ley el ${av.observado}%`:'banda de avance')}">avance <b style="color:${BC[av.banda]||'inherit'}">${esc(av.banda)}</b></span>`);
        p.push(im.score!=null?`<span title="impacto del articulado${im.confianza?' · confianza '+esc(im.confianza):''}">impacto <b>${Math.round(im.score)}</b></span>`:`<span title="todavía no se ha extraído el articulado">impacto <b style="color:var(--ink3)">sin texto</b></span>`);
        if(po.score!=null) p.push(`<span title="${esc((po.etiqueta||'').replace(/_/g,' '))}${po.cohesion?' · '+esc(po.cohesion):''} · heurística declarada">político <b>${Math.round(po.score)}</b></span>`);
        imp=`<div class="sig-tags" style="margin-top:.2rem">◈ ${p.join(' · ')}</div>`;
      }
      return `<div class="${cls}"><span class="sig-lvl">${x.nivel}</span><div class="sig-body">
        <div class="sig-title">${apTag}${vt}${esc(shortTitle(x.titulo).slice(0,120))}</div>
        <div class="sig-tags">${tags}</div>${imp}${art}<div class="sig-action">${esc(x.accion)}</div></div></div>`;
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
  // la lectura vigente en pantalla — el brief se arma de acá, así que lo
  // descargado y lo mostrado no pueden discrepar.
  let _CLI_LECTURA=null;
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
    _CLI_LAST=d; _CLI_LECTURA=null;
    // el brief se re-habilita cuando la lectura del radar nuevo aterriza
    const _bb=document.getElementById('cli-brief-bar'); if(_bb) _bb.hidden=true;
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
      <!-- LA LECTURA VA ARRIBA. Es lo que el cliente vino a leer: el contexto
           del perfil (líneas de negocio, alcance, competencia) explica de dónde
           sale el radar, pero se lee DESPUÉS de saber qué pasó. -->
      <div class="lectura">
        <div class="tag">◈ Lectura del analista · briefing de hoy para ${esc(cl.nombre)}</div>
        <div id="cli-lectura-body"></div>
        <div class="brief-bar" id="cli-brief-bar" hidden>
          <button type="button" class="brief-btn" id="cli-brief-btn">↓ Brief de 72 horas (.pdf)</button>
          <span class="brief-nota" id="cli-brief-nota"></span>
        </div>
      </div>
      ${secDesc}${avi}${desc}${lineasHTML}${alcanceHTML}${vigNote}
      <div class="cli-note"><b>Activo ahora en ${esc(cl.nombre)}:</b> <b>${k.en_tramite}</b> proyecto(s) de ley en trámite · ${sancTxt} · <b>${fmt(k.n_medios_sector||0)}</b> titular(es) de prensa reciente · <b>${fmt(k.n_contratos_sector||0)}</b> contrato(s) reciente(s) en SECOP.</div>
      ${k.n_medios_exterior?`<div class="cob-note" style="margin:.4rem 0"><b>${k.n_medios_exterior}</b> titular(es) de prensa del exterior quedaron fuera del radar: hablan del tema en Perú, Panamá o Estados Unidos, no en Colombia. Se descartan acá, no se borran de la fuente.</div>`:''}
      ${k.n_con_articulado?`<div class="cli-note"><b>Qué cambian:</b> de las ${congreso.length} señales del Congreso, <b>${k.n_con_articulado}</b> ya tienen el articulado leído${k.n_te_aplica?` y <b>${k.n_te_aplica}</b> le aplican a tu sector o a tus vigiladas`:''}. El resto todavía no se ha extraído.</div>`:''}
      <div class="cob-note" style="margin:.5rem 0 1.3rem">De un histórico de <b>${fmt(k.n_proyectos_sector)}</b> proyectos${cl.sector_sanciones?` y <b>${fmt((k.n_sanciones_sector||0)+(k.n_otros_actos_sector||0))}</b> actos del regulador (<b>${fmt(k.n_sanciones_sector)}</b> de ellos sanciones)`:''} que tocan estos temas, ${MARCA.nombre} prioriza por accionabilidad — precisión sobre volumen.${(cl.temas_usados&&cl.temas_usados.length)?` Se buscó por: <b>${esc(cl.temas_usados.join(' · '))}</b>.`:''}</div>
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
    cliLoaderStop();
    _CLI_LECTURA=l||null;
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
    // PLAN DE ACCIÓN (pedido de Pablo: «me recomienda planes de acción»). Cada
    // punto trae qué, por qué, plazo (solo si la evidencia lo trae), rol y qué
    // preparar. Las lecturas viejas traen `acciones` (texto suelto): se
    // conservan como respaldo para no dejar el bloque vacío.
    const plan=(l.plan&&l.plan.length)?`<div class="blk"><div class="h">Plan de acción</div>${l.plan.map((p,i)=>{
      const pz=(p.plazo||'').trim(); const sinPlazo=!pz||/sin plazo/i.test(pz);
      return `<div class="acc" style="display:grid;grid-template-columns:auto 1fr;gap:.2rem .7rem;align-items:start">
        <b style="color:var(--teal);font-size:1rem">${i+1}</b>
        <div><div style="font-weight:700;color:var(--ink)">${esc(p.accion||'')}</div>
          ${p.por_que?`<div class="ga-t">${esc(p.por_que)}</div>`:''}
          <div class="ga-t" style="margin-top:.25rem">${pz?`<span class="ichip" style="display:inline-block;width:auto;padding:.1rem .45rem;font-size:.6rem;${sinPlazo?'opacity:.6':'color:var(--amber);border-color:var(--amber)'}">${esc(pz)}</span> `:''}${p.responsable?`<span class="ichip" style="display:inline-block;width:auto;padding:.1rem .45rem;font-size:.6rem">${esc(p.responsable)}</span>`:''}</div>
          ${p.preparar?`<div class="ga-t" style="margin-top:.2rem"><span style="opacity:.7">Preparar:</span> ${esc(p.preparar)}</div>`:''}</div></div>`;}).join('')}</div>`:'';
    const acc=plan?'':((l.acciones&&l.acciones.length)?`<div class="blk"><div class="h">Acciones</div>${l.acciones.map(a=>`<div class="acc">${esc(a)}</div>`).join('')}</div>`:'');
    body.innerHTML=(l.titular?`<div class="blk"><div class="t" style="font-weight:700;font-size:.95rem;color:var(--ink)">${esc(l.titular)}</div></div>`:'')
      + (partes?`<div class="lc-grid">${partes}</div>`:'')
      // compatibilidad: lecturas cacheadas de antes del cambio traen el campo viejo
      + blk('Lo que mueve la aguja', l.lo_que_importa)
      + plan + acc + blk('En el horizonte', l.horizonte)
      || '<div class="cob-note">Sin lectura disponible.</div>';
    briefWire();
  }
  /* ── La espera de la lectura ──────────────────────────────────────────
     La primera lectura de un perfil tarda 40-60 s: son seis fuentes cruzadas
     más la generación del modelo, y el sondeo va a saltos. Tres puntos
     durante un minuto se leen como «se colgó».

     ⚠️ LOS PASOS DICEN LO QUE DE VERDAD PASA. Ninguno anuncia escucha de redes
     sociales: Caudal tiene un DICCIONARIO de cuentas oficiales (quién habla por
     cada entidad), no monitoreo de lo que se publica en ellas. Anunciarlo acá
     sería vender en la barra de carga algo que el producto no hace — y es la
     primera pantalla donde un cliente nuevo aprende qué es Caudal. */
  const CLI_PASOS=[
    n=>`Cruzando los proyectos del Congreso que tocan a ${n}`,
    ()=>'Leyendo el articulado: qué obliga, a quién y con qué sanción',
    ()=>'Revisando actos de superintendencias y reguladores',
    ()=>'Buscando la norma que todavía está en consulta pública',
    n=>`Rastreando prensa nacional y regional sobre ${n}`,
    ()=>'Mirando qué contrata el Estado en SECOP',
    ()=>'Pesando cada señal: avance, impacto del texto y peso político',
    ()=>'Ordenando por lo que mueve la aguja — precisión sobre volumen',
  ];
  let _cliPasoT=null;
  function cliLoaderStart(nombre){
    const el=document.getElementById('cli-lectura-body'); if(!el) return;
    cliLoaderStop();
    const n=esc(nombre||'este perfil');
    // se barajan salvo el primero y el último: el orden real de las consultas
    // no es fijo, y ver siempre la misma secuencia delata que es decorado.
    const medio=CLI_PASOS.slice(1,-1).map((f,i)=>[Math.random(),f]).sort((a,b)=>a[0]-b[0]).map(x=>x[1]);
    const pasos=[CLI_PASOS[0],...medio,CLI_PASOS[CLI_PASOS.length-1]].map(f=>f(n));
    el.innerHTML=`<div class="cli-wait" role="status" aria-live="polite">
      <div class="cli-wait-bar"><span></span></div>
      <div class="cli-wait-txt" id="cli-wait-txt">${pasos[0]}</div>
      <div class="cli-wait-sub">La primera lectura de un perfil tarda un poco: son seis fuentes y el análisis se escribe encima.</div>
    </div>`;
    let i=0;
    // setInterval y no rAF: en una pestaña de fondo rAF se congela y el texto
    // se queda pegado en el primer paso (mismo criterio que uniLoader).
    _cliPasoT=setInterval(()=>{
      i=(i+1)%pasos.length;
      const tx=document.getElementById('cli-wait-txt'); if(!tx) return cliLoaderStop();
      tx.style.opacity='0';
      setTimeout(()=>{ tx.textContent=pasos[i]; tx.style.opacity='1'; },180);
    },4200);
  }
  function cliLoaderStop(){ if(_cliPasoT){ clearInterval(_cliPasoT); _cliPasoT=null; } }

  /* ── Cupo de sectores para quien no tiene cuenta ──────────────────────
     Los 15 sectores son PRESETS: su radar se precalcula y se cachea, así que
     servírselos a un visitante cuesta casi nada. Por eso son la mejor puerta
     de entrada — se le puede dar valor real antes de pedirle nada.

     El tope es por SEMANA y por sector distinto: volver al mismo sector no
     gasta cupo (quien vuelve está enganchado, no abusando), y el reloj se
     reinicia solo. Es un gate de PRODUCTO, no de seguridad: vive en
     localStorage y se puede saltar borrando el sitio. Da igual: lo que se
     cobra es la lectura del analista y el perfil propio, y los dos exigen
     cuenta del lado del worker.

     ⚠️ NO aplica a perfiles de cliente: esos ya exigen sesión para guardarse. */
  const ROSA_ANON_MAX=3, ROSA_LS='caudal-rosa-sem';
  function rosaSemana(){
    // semana ISO: el reset cae siempre en lunes, sin importar cuándo entró
    const d=new Date(); d.setHours(0,0,0,0);
    d.setDate(d.getDate()+3-((d.getDay()+6)%7));           // jueves de esa semana
    const e=new Date(d.getFullYear(),0,4);
    const n=1+Math.round(((d-e)/864e5-3+((e.getDay()+6)%7))/7);
    return d.getFullYear()+'-W'+String(n).padStart(2,'0');
  }
  function rosaEstado(){
    let s=null; try{ s=JSON.parse(localStorage.getItem(ROSA_LS)||'null'); }catch(e){}
    if(!s||s.sem!==rosaSemana()) s={sem:rosaSemana(),vistos:[]};
    if(!Array.isArray(s.vistos)) s.vistos=[];
    return s;
  }
  // {max, usados, quedan, abierto} — `abierto` = tiene cuenta, sin tope acá.
  function rosaCupo(){
    if(HAS_SESSION) return {max:0,usados:0,quedan:99,abierto:true};
    const s=rosaEstado();
    return {max:ROSA_ANON_MAX, usados:s.vistos.length,
            quedan:Math.max(0,ROSA_ANON_MAX-s.vistos.length), abierto:false};
  }
  // ¿puede abrir ESTE sector? Devuelve true y lo apunta; false si se acabó.
  function rosaConsumir(sec){
    if(HAS_SESSION) return true;
    const s=rosaEstado();
    if(s.vistos.includes(sec)) return true;                 // repetir no gasta
    if(s.vistos.length>=ROSA_ANON_MAX) return false;
    s.vistos.push(sec);
    try{ localStorage.setItem(ROSA_LS,JSON.stringify(s)); }catch(e){}
    return true;
  }
  function rosaMuroCupo(){
    const body=document.getElementById('cli-body'); if(!body) return;
    body.innerHTML=`<div class="muro-blk">
      <div class="muro-t">Ya viste los ${ROSA_ANON_MAX} sectores de esta semana.</div>
      <div class="muro-d">Crear una cuenta es gratis y abre los 15 sectores, la lectura del analista y el brief de 72 horas. Los que ya abriste siguen disponibles.</div>
      <a class="muro-btn" href="register.html?next=${encodeURIComponent('caudal.html#cliente')}">Crear cuenta gratis →</a>
    </div>`;
  }

  /* ── BRIEF DE 72 HORAS ────────────────────────────────────────────────
     Lo que la Rosa deja en pantalla es para mirar; esto es para llevarlo a una
     reunión. Sale de lo que YA está cargado (`_CLI_LAST` + la lectura vigente):
     cero llamadas nuevas, cero costo de modelo y nada que se pueda desfasar
     entre lo que se ve y lo que se descarga.

     ⚠️ La ventana son las señales marcadas `mov` por la Lambda (≤3 días =
     72 h), NO todo el radar. Y hay un límite que se declara en el propio PDF:
     las señales del Congreso no traen fecha en el índice, así que nunca entran
     como movimiento — un proyecto en trámite es estado, no noticia. Prometer
     "todo lo de las últimas 72 horas" incluyendo el Congreso sería falso.

     ⚠️ Si en 72 h no se movió nada, el brief SE GENERA IGUAL y lo dice. Un
     "no pasó nada" verificado es información; fabricar contenido para llenar
     la página es lo contrario de lo que se vende acá. */
  // El acento del PDF es el azul de lectura de la paleta Cauce (--teal, que
  // pese al nombre de la variable es #3d6eb8). Un teal literal se vería de
  // otra marca.
  const BRIEF_ACENTO=[61,110,184];
  const BRIEF_CDN='https://cdn.jsdelivr.net/npm/jspdf@2.5.1/dist/jspdf.umd.min.js';
  let _briefLoading=null;
  function briefJsPDF(){
    if(window.jspdf&&window.jspdf.jsPDF) return Promise.resolve(window.jspdf.jsPDF);
    if(_briefLoading) return _briefLoading;
    _briefLoading=new Promise((ok,err)=>{
      const s=document.createElement('script'); s.src=BRIEF_CDN;
      s.onload=()=>ok(window.jspdf&&window.jspdf.jsPDF);
      s.onerror=()=>{_briefLoading=null;err(new Error('cdn'))};
      document.head.appendChild(s);
    });
    return _briefLoading;
  }
  // Fuente del PDF: el orden de la Rosa (N · E · S · O), no el de la respuesta.
  const BRIEF_CARD=[['norte','NORTE · oportunidades'],['este','ORIENTE · conversación'],
                    ['sur','SUR · competencia'],['oeste','OCCIDENTE · Estado']];
  const BRIEF_FUENTE={congreso:'Congreso',regulatorio:'Regulatorio',medios:'Prensa',
                      contratacion:'Contratación',ejecutivo:'Ejecutivo',sucop:'Consulta pública'};
  // ⚠️ La URL va como ENLACE, nunca como texto. Medido en el primer brief: una
  // sola nota de prensa de Google News ocupaba CINCO LÍNEAS de base64 —
  // `news.google.com/rss/articles/CBMivAFBVV95cUxQ…` son más de 500 caracteres —
  // y tres notas convertían la página en un muro de ruido. El PDF muestra el
  // medio y el enlace queda detrás, que es como se lee un documento.
  // ⚠️ SIN FLECHAS NI SÍMBOLOS FUERA DE WinAnsi. Medido: un solo `↗` obliga a
  // jsPDF a escribir TODA la cadena en 16 bits y la flecha sale como «!». Es el
  // mismo gotcha que el subset de Inter en los informes Word — acá con
  // helvetica y peor, porque contamina la línea entera.
  function briefEtiquetaEnlace(x){
    const u=(x.url||'').trim(); if(!u) return '';
    if(/news\.google\./i.test(u)) return 'Abrir la nota' + (x.medio?` en ${x.medio}`:'');
    try{ return 'Ver el documento en ' + new URL(u).hostname.replace(/^www\./,''); }
    catch(e){ return 'Ver el documento'; }
  }
  /* ⚠️ `shortTitle` pasa TODO a minúscula y solo capitaliza la primera letra:
     existe porque los títulos del Congreso vienen en MAYÚSCULA SOSTENIDA. Sobre
     un titular de prensa, que ya viene bien escrito, destroza los nombres
     propios — «Mina quebradona: prórroga de exploración en jericó». Así que se
     aplica solo cuando el título de verdad viene gritado: mismo criterio (70 %
     de mayúsculas) que `oracion()` en caudal-portada.js. */
  function briefTitulo(s){
    const v=String(s||'').trim();
    const letras=v.replace(/[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ]/g,'');
    if(!letras) return v;
    const may=(letras.match(/[A-ZÁÉÍÓÚÜÑ]/g)||[]).length;
    return may/letras.length>=0.7 ? shortTitle(v) : v;
  }
  function briefSenalTexto(x){
    const meta=[BRIEF_FUENTE[x.tipo]||x.tipo, x.fecha||'', x.vigilada?('vigilada: '+x.vigilada):'',
                x.entidad||x.medio||x.comision||''].filter(Boolean).join(' · ');
    return {tit:briefTitulo(x.titulo).slice(0,190), meta,
            accion:(x.accion||'').trim(), url:(x.url||'').trim(),
            enlace:briefEtiquetaEnlace(x), nivel:x.nivel||''};
  }
  function briefDatos(){
    const d=_CLI_LAST; if(!d) return null;
    const cl=d.cliente||{}, k=d.kpis||{};
    const todas=[].concat(d.congreso||[],d.regulatorio||[],d.medios||[],
                          d.contratacion||[],d.ejecutivo||[],d.sucop||[]);
    // `mov` lo marca la Lambda contra su propio reloj: no se recalcula acá para
    // que el PDF y la pantalla no puedan discrepar por la zona horaria del
    // navegador de quien descarga.
    const mov=todas.filter(x=>x&&x.mov);
    const porCard={norte:[],este:[],sur:[],oeste:[]};
    mov.forEach(x=>{ const c=porCard[x.card]?x.card:'oeste'; porCard[c].push(x); });
    const hoy=new Date();
    return {nombre:cl.nombre||'tu perfil', kpis:k, porCard, nMov:mov.length,
            nTotal:todas.length, dias:k.mov_dias||3, lectura:_CLI_LECTURA,
            cabecera:hoy.toLocaleDateString('es-CO',{day:'numeric',month:'long',year:'numeric'})};
  }
  async function briefDescargar(){
    const btn=document.getElementById('cli-brief-btn');
    const D=briefDatos(); if(!D) return;
    const txtPrev=btn?btn.textContent:'';
    if(btn){ btn.disabled=true; btn.textContent='Armando el brief…'; }
    let jsPDF; try{ jsPDF=await briefJsPDF(); }
    catch(e){ if(btn){btn.disabled=false;btn.textContent=txtPrev;} alert('No se pudo cargar el generador de PDF. Reintenta.'); return; }

    /* ── El sistema visual es el del Brief de Asuntos Públicos de Cauce ────
       Antes esto era texto corrido y se leía como un volcado. El brief que el
       equipo ya usa tiene una gramática: encabezado con marca en cada página,
       titular, bajada, línea de ventana, un bloque destacado con la lectura y
       su «si solo hay tiempo para una cosa», secciones numeradas con barra de
       color y cajas de «qué hacer», y al final lo que NO se movió — verificado,
       no asumido. Ese último bloque es el que separa un informe de un listado.

       ⚠️ HELVETICA Y NADA MÁS: jsPDF trae las 14 fuentes base y ninguna tilde
       fuera de WinAnsi. Un solo carácter fuera de ese juego (→ ↗ ★ •) obliga a
       escribir la cadena entera en 16 bits y sale como «!». Guiones y puntos
       medios, nunca flechas. */
    const doc=new jsPDF({unit:'pt',format:'letter',compress:true});
    const W=doc.internal.pageSize.getWidth(), H=doc.internal.pageSize.getHeight();
    const M=52, AN=W-M*2, TOP=96, PIE=52;
    const AZUL=[61,110,184], TINTA=[26,32,44], GRIS=[110,120,133], SUAVE=[248,247,244];
    // acento por rumbo — el mismo orden de la Rosa
    const ACENTO={norte:[176,124,32], este:[61,110,184], sur:[150,58,52], oeste:[46,101,78]};
    let y=TOP;

    const cabecera=()=>{
      doc.setFont('helvetica','bold'); doc.setFontSize(15); doc.setTextColor(...TINTA);
      doc.text('CAUDAL × CAUCE', M, 48);
      doc.setFont('helvetica','normal'); doc.setFontSize(6.5); doc.setTextColor(...GRIS);
      doc.text('navegar la complejidad', M+2, 60);
      doc.setFontSize(7.5);
      doc.text('BRIEF DE 72 HORAS · CAUDAL × CAUCE', W-M, 46, {align:'right'});
      doc.text(D.cabecera.toUpperCase(), W-M, 57, {align:'right'});
      doc.setDrawColor(...TINTA); doc.setLineWidth(1.1); doc.line(M, 70, W-M, 70);
      doc.setLineWidth(0.5);
    };
    const nuevaPag=()=>{ doc.addPage(); cabecera(); y=TOP; };
    const salto=n=>{ if(y+n>H-PIE) nuevaPag(); };
    const parrafo=(txt,{size=9.5,style='normal',color=TINTA,lh=1.42,x=M,ancho=AN,gap=5}={})=>{
      if(!txt) return;
      doc.setFont('helvetica',style); doc.setFontSize(size); doc.setTextColor(...color);
      doc.splitTextToSize(String(txt),ancho).forEach(l=>{
        salto(size*lh); doc.text(l,x,y); y+=size*lh;
      });
      y+=gap;
    };
    const eyebrow=(txt,color=GRIS,{x=M,size=7.2,gap=6}={})=>{
      salto(size+gap); doc.setFont('helvetica','bold'); doc.setFontSize(size);
      doc.setTextColor(...color);
      // versalitas a mano: jsPDF no tiene small-caps y el espaciado lo simula
      doc.text(String(txt).toUpperCase(),x,y,{charSpace:0.7}); y+=size+gap;
    };
    // caja con fondo y barra lateral: se mide primero, se pinta después, para
    // que el fondo no quede cortado a mitad de página
    const caja=(alto,{fondo=SUAVE,barra=null,x=M,ancho=AN}={})=>{
      doc.setFillColor(...fondo); doc.rect(x,y-9,ancho,alto+16,'F');
      if(barra){ doc.setFillColor(...barra); doc.rect(x,y-9,2.6,alto+16,'F'); }
    };
    const alto=(txt,size,lh,ancho)=>{
      doc.setFontSize(size);
      return doc.splitTextToSize(String(txt||''),ancho).length*size*lh;
    };

    cabecera();

    // ── TITULAR + BAJADA ────────────────────────────────────────────────
    const tit=(D.lectura&&D.lectura.titular)||`Lo que se movió en ${D.nombre} en las últimas ${D.dias*24} horas`;
    doc.setFont('helvetica','bold'); doc.setFontSize(19); doc.setTextColor(...TINTA);
    doc.splitTextToSize(tit,AN).forEach((l,i)=>{ salto(26); doc.setTextColor(...(i?AZUL:TINTA)); doc.text(l,M,y); y+=25; });
    y+=6;
    parrafo(`Barrido de las últimas ${D.dias*24} horas sobre el Congreso, el Ejecutivo, los reguladores, `
      +`la consulta pública de normas, la contratación del Estado y la prensa. `
      +`${D.nMov} señal${D.nMov===1?'':'es'} con movimiento, de ${D.nTotal} vigentes para este perfil, ordenadas por los `
      +`cuatro rumbos de la Rosa de los Vientos.`,{size:9.5,color:[70,78,90],gap:8});
    const hoy=new Date();
    const desde=new Date(hoy.getTime()-D.dias*864e5);
    const f=d=>d.toLocaleDateString('es-CO',{day:'numeric',month:'long'});
    doc.setDrawColor(214,219,226); doc.line(M,y,W-M,y); y+=12;
    eyebrow(`Ventana ${f(desde)} a ${f(hoy)} de ${hoy.getFullYear()} · corte ${hoy.toLocaleTimeString('es-CO',{hour:'numeric',minute:'2-digit'})} · Colombia`,GRIS,{size:7,gap:16});

    // ── LECTURA DEL ANALISTA ────────────────────────────────────────────
    const L=D.lectura||{};
    if(L.titular||L.lo_que_importa||(L.plan&&L.plan.length)){
      const cuerpo=L.lo_que_importa||'';
      const uno=(L.plan&&L.plan[0])||null;
      let h=14+alto(cuerpo,9.5,1.42,AN-24);
      if(uno) h+=34+alto(uno.por_que||uno.accion||'',9,1.42,AN-46);
      salto(h+40);
      caja(h+16,{fondo:[243,244,250],barra:AZUL});
      const yc=y; y+=6;
      eyebrow('La lectura del analista',AZUL,{x:M+14,size:7,gap:7});
      parrafo(cuerpo,{size:9.5,x:M+14,ancho:AN-24,gap:6});
      if(uno){
        doc.setFillColor(255,255,255); doc.rect(M+14,y-6,AN-28,alto(uno.por_que||uno.accion||'',9,1.42,AN-46)+28,'F');
        y+=4;
        eyebrow('Si solo hay tiempo para una cosa',AZUL,{x:M+24,size:6.6,gap:6});
        parrafo(`${uno.accion||''}${uno.por_que?' '+uno.por_que:''}`,{size:9,x:M+24,ancho:AN-46,gap:4});
        y+=8;
      }
      y=Math.max(y,yc+h)+18;
    }

    // ── LOS CUATRO RUMBOS ───────────────────────────────────────────────
    let nSec=0;
    BRIEF_CARD.forEach(([k,nom])=>{
      const lista=D.porCard[k]||[]; const txt=(L[k]||'').trim();
      if(!lista.length && !txt) return;      // los quietos van al bloque final
      nSec++;
      const col=ACENTO[k]||AZUL;
      // El fondo se pinta ANTES del texto (jsPDF no tiene z-order: pintarlo
      // después lo taparía), así que hay que MEDIR la sección primero. Si no
      // cabe entera en una página se va sin fondo y solo con la barra lateral:
      // un fondo cortado a mitad de página se ve como un error de maquetación.
      let hSec=16+ (txt?alto(txt,9.5,1.42,AN-28)+8:0);
      lista.forEach(x=>{ const s=briefSenalTexto(x);
        hSec+=alto(s.tit,9.5,1.42,AN-28)+2
             +(s.meta?alto(s.meta,7.6,1.42,AN-28)+2:0)
             +(s.accion?alto(s.accion,8.6,1.42,AN-28)+2:0)
             +(s.url&&s.enlace?13:0)+4; });
      const cabe=hSec+26<H-PIE-TOP;
      if(cabe && y+hSec+26>H-PIE) nuevaPag(); else salto(70);
      const y0=y;
      if(cabe) caja(hSec,{fondo:[250,249,246]});
      eyebrow(`${String(nSec).padStart(2,'0')} · ${nom} · ${lista.length?`${lista.length} en ${D.dias*24} h`:'sin movimiento'}`,col,{x:M+14,gap:7});
      if(txt) parrafo(txt,{size:9.5,style:'bold',x:M+14,ancho:AN-28,gap:8});
      lista.forEach(x=>{
        const s=briefSenalTexto(x);
        salto(38);
        parrafo(s.tit,{size:9.5,style:'bold',x:M+14,ancho:AN-28,gap:2});
        if(s.meta) parrafo(s.meta,{size:7.6,color:GRIS,x:M+14,ancho:AN-28,gap:2});
        if(s.accion) parrafo(s.accion,{size:8.6,color:[70,78,90],x:M+14,ancho:AN-28,gap:2});
        if(s.url&&s.enlace){
          salto(13); doc.setFont('helvetica','normal'); doc.setFontSize(7.8);
          doc.setTextColor(...AZUL); doc.textWithLink(s.enlace,M+14,y,{url:s.url}); y+=13;
        }
        y+=4;
      });
      // barra lateral del bloque, pintada al final porque solo ahora se sabe
      // cuánto midió; si el rumbo cruzó de página, la barra cubre lo de esta.
      doc.setFillColor(...col); doc.rect(M,y0-11,2.6,Math.max(10,y-y0+2),'F');
      y+=12;
    });

    // ── PLAN DE ACCIÓN ──────────────────────────────────────────────────
    if(L.plan&&L.plan.length>1){
      salto(50); doc.setDrawColor(214,219,226); doc.line(M,y,W-M,y); y+=14;
      eyebrow('Plan de acción',AZUL,{gap:9});
      L.plan.forEach((p,i)=>{
        salto(34);
        parrafo(`${i+1}. ${p.accion||''}`,{size:9.8,style:'bold',gap:3});
        if(p.por_que) parrafo(p.por_que,{size:9,x:M+16,ancho:AN-16,gap:2});
        const m=[p.plazo,p.responsable].filter(Boolean).join(' · ');
        if(m) parrafo(m,{size:7.8,color:GRIS,x:M+16,ancho:AN-16,gap:2});
        if(p.preparar) parrafo('Preparar: '+p.preparar,{size:8.4,color:[70,78,90],x:M+16,ancho:AN-16,gap:6});
      });
      y+=6;
    }

    // ── QUÉ NO SE MOVIÓ ─────────────────────────────────────────────────
    // El bloque que separa un informe de un listado: decir dónde SÍ se miró y
    // no había nada es información, y es lo que impide que un rumbo quieto se
    // confunda con un rumbo no revisado.
    const quietos=BRIEF_CARD.filter(([k])=>!(D.porCard[k]||[]).length);
    salto(60); doc.setDrawColor(214,219,226); doc.line(M,y,W-M,y); y+=14;
    eyebrow('Qué no se movió — verificado, no asumido',TINTA,{gap:10});
    quietos.forEach(([k,nom])=>{
      salto(20);
      doc.setFont('helvetica','bold'); doc.setFontSize(8.6); doc.setTextColor(...TINTA);
      doc.text(nom,M,y);
      doc.setFont('helvetica','normal'); doc.setTextColor(...GRIS);
      doc.splitTextToSize('Revisado en la ventana; sin novedad.',AN-172).forEach((l,i)=>{
        doc.text(l,M+172,y+i*12);
      });
      y+=20;
    });
    salto(20);
    doc.setFont('helvetica','bold'); doc.setFontSize(8.6); doc.setTextColor(...TINTA);
    doc.text('Congreso · fecha',M,y);
    doc.setFont('helvetica','normal'); doc.setTextColor(...GRIS);
    doc.splitTextToSize('Los proyectos de ley no entran como movimiento: el índice guarda el año de radicación, no el día. Van en el radar completo de la plataforma.',AN-172).forEach((l,i)=>{ doc.text(l,M+172,y+i*12); });
    y+=32;

    // ── PIE METODOLÓGICO ────────────────────────────────────────────────
    salto(70); doc.setDrawColor(214,219,226); doc.line(M,y,W-M,y); y+=12;
    const pie=(lb,tx)=>{
      salto(24);
      doc.setFont('helvetica','bold'); doc.setFontSize(7.8); doc.setTextColor(...TINTA);
      doc.text(lb,M,y);
      const w=doc.getTextWidth(lb)+4;
      doc.setFont('helvetica','normal'); doc.setTextColor(...GRIS);
      const ls=doc.splitTextToSize(tx,AN-w);
      ls.forEach((l,i)=>{ doc.text(l, i?M:M+w, y+i*10.5); });
      y+=ls.length*10.5+5;
    };
    pie('Fuentes.','Registro de proyectos de ley del Senado y la Cámara; normativa de Presidencia; consulta pública de proyectos de norma del DNP (SUCOP); registro regulatorio de 12 fuentes; providencias de la Corte Constitucional; contratos y procesos del Estado (SECOP); prensa nacional y regional. Cada señal enlaza el acto o la nota que la respalda.');
    pie('Ventana.',`Últimas ${D.dias*24} horas, con corte al momento de la descarga.`);
    pie('Alcance.','Insumo de monitoreo. Análisis asistido por IA sobre datos oficiales; el criterio experto es del analista.');
    doc.setFont('helvetica','normal'); doc.setFontSize(7.5); doc.setTextColor(...GRIS);
    doc.text('Caudal · módulo de inteligencia regulatoria de Cauce.',M,y);

    // ── PAGINACIÓN (al final: solo ahora se sabe el total) ──────────────
    const tot=doc.internal.getNumberOfPages();
    for(let i=1;i<=tot;i++){
      doc.setPage(i); doc.setFont('helvetica','normal'); doc.setFontSize(7.2);
      doc.setTextColor(...GRIS);
      doc.text(`${D.nombre} · brief de ${D.dias*24} h`,M,H-30);
      doc.text(`${i} / ${tot}`,W-M,H-30,{align:'right'});
    }
    const slug=String(D.nombre).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'')
      .replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,40)||'perfil';
    doc.save(`caudal-brief-72h-${slug}-${hoy.toISOString().slice(0,10)}.pdf`);
    if(btn){ btn.disabled=false; btn.textContent=txtPrev; }
  }
  function briefWire(){
    const bar=document.getElementById('cli-brief-bar'), btn=document.getElementById('cli-brief-btn'),
          nota=document.getElementById('cli-brief-nota');
    if(!bar||!btn) return;
    const D=briefDatos(); if(!D) return;
    bar.hidden=false;
    btn.onclick=briefDescargar;
    nota.textContent=D.nMov
      ? `${D.nMov} señal${D.nMov===1?'':'es'} con movimiento en ${D.dias*24} h · el resto queda en el radar`
      : `Sin movimiento en ${D.dias*24} h — el brief lo dice y trae el estado de los cuatro rumbos`;
  }

  // `arg` = {sector:'salud'} (preset/demo) o {perfil:{…}} (el perfil del cliente).
  // El resto del flujo es idéntico: los presets siguen siendo el fallback.
  async function cliLoad(arg){
    const mine=++_cliSeq;
    cliLecturaStop();
    const esPerfil=!!(arg&&arg.perfil);
    // el cupo se cobra ANTES de pedir nada: si no hay, ni se llama a la Lambda
    if(!esPerfil && arg && arg.sector && !rosaConsumir(arg.sector)){
      PF_ACTIVE=null; pfRenderBar(); rosaMuroCupo(); return;
    }
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
    const cl_nombre=(d.cliente&&d.cliente.nombre)||(esPerfil?p.nombre:arg.sector)||'este perfil';
    // el radar ya está en pantalla; la lectura llega después (o ya venía hecha)
    // Sin acceso ni se pide: el worker devuelve 403 a `cliente-lectura`, y eso
    // le pintaría un error al visitante donde debería ir una invitación.
    if(!ACCESO) cliMuroLectura();
    else if(d.lectura && !d.lectura.error) cliRenderLectura(d.lectura);
    else if(d.lectura_key){ cliLoaderStart(cl_nombre); cliPedirLectura(d.lectura_key, mine); }
    else cliLecturaFallback();
  }
  function cliLecturaFallback(msg){
    cliLoaderStop();
    const el=document.getElementById('cli-lectura-body'); if(!el) return;
    el.innerHTML='<div class="cob-note">'+esc(msg||'No se pudo generar la lectura. Lo de arriba está completo.')+'</div>';
    // el brief sigue disponible: las señales de las últimas 72 h son dato
    // propio y no dependen de que el modelo haya respondido.
    _CLI_LECTURA=null; briefWire();
  }
  // El muro del radar: el briefing es justamente lo que se vende acá, así que en
  // vez de un error va la invitación, en el mismo sitio donde iría la lectura.
  function cliMuroLectura(){
    cliLoaderStop();
    const el=document.getElementById('cli-lectura-body'); if(!el) return;
    el.innerHTML=`<div class="muro-t" style="margin-bottom:.7rem">Acá va el briefing del día: qué señales de las de arriba mueven la aguja, por qué, y qué hacer con cada una. Se escribe sobre esto mismo, y va con acceso.</div>`
      + `<a class="muro-btn" href="${window.COMPRA_URL||'caudal-pricing.html?comprar=1'}">Conseguir acceso →</a>`
      + ` <a class="muro-btn" style="opacity:.75" href="${mailtoHref('acceso · '+MARCA.nombre)}">o escríbenos · ${CONTACTO_MAIL}</a>`;
  }
  // La lectura se genera aparte del radar: medida contra producción tarda entre
  // 20 s y 51 s (la varianza es del modelo), o sea que se pasa del techo de
  // 30 s del API Gateway sin que haya forma de predecirlo. Así que se dispara
  // una vez y se recoge SONDEANDO el caché — un GET a S3, ~0,3 s. Si el modelo
  // alcanza a contestar dentro del gateway, el disparo la trae de una y el
  // sondeo se apaga; si lo cortan, la Lambda igual termina y el sondeo la pesca.
  const CLI_LECT_POLL=3500, CLI_LECT_MAX=150000;   // 150 s: el plan de acción alarga la primera lectura (medido sep-2026)
  let _cliLectTimer=null;
  // corta el SONDEO. NO toca el loader: se la llama al arrancar la petición y
  // pararlo ahí lo mataría justo al nacer. El loader lo apagan los tres finales
  // (lectura lista · fallback · muro).
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
      // (el aviso de «tarda un poco más» que iba acá pisaba el loader de pasos
      //  con su propio innerHTML y lo dejaba mudo; el mensaje vive ahora en
      //  `.cli-wait-sub`, que no se sobrescribe)
      call({action:'cliente-lectura',key,solo_cache:true})
        .then(d=>{ if(!listo(d)) _cliLectTimer=setTimeout(tick,CLI_LECT_POLL); })
        .catch(()=>{ if(mine===_cliSeq) _cliLectTimer=setTimeout(tick,CLI_LECT_POLL); });
    };
    _cliLectTimer=setTimeout(tick,CLI_LECT_POLL);
  }

  /* `cliInit` lo llama initHome; `pfLoadList`, caudal-base.js al abrir sesión.
     `briefWire`/`briefDescargar` se exponen para soporte y verificación: la
     barra del brief solo aparece cuando la lectura aterriza, y sin esto no
     hay forma de probar el PDF si el modelo está lento. */
  Object.assign(window, { cliInit, pfLoadList, briefWire, briefDescargar, rosaCupo, cliLoad });
})();
