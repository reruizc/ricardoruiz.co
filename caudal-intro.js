/* caudal-intro.js — la pregunta de entrada de caudal.html
   ------------------------------------------------------------------
   Antes de abrirle a alguien diez categorías, una búsqueda y la Rosa de los
   Vientos, se le pregunta en qué sector está y, si quiere, qué empresa es.
   Con eso la portada arranca por lo suyo: sus sectores, su empresa y tres
   temas por sector para buscar.

   · Los SECTORES son de opción múltiple a propósito: Uber está a la vez en
     transporte, trabajo y consumo. Al escoger la empresa se marcan solos los
     sectores que toca (salen del diccionario, `caudal-empresas.json`), y la
     persona puede quitar o sumar.
   · La EMPRESA es opcional y sale del mismo diccionario que usa la búsqueda
     (2.011 entradas). Si no está, se acepta el nombre escrito tal cual: no se
     le inventa sector.
   · Todo queda en localStorage (`caudal-intro-v1`), en este navegador. No
     viaja al servidor: es para ordenar la portada, no un perfil de cliente
     (ese vive en la Rosa y exige cuenta).
   · Si la persona llega con un destino —un #pilar o un ?tema=— no se le
     atraviesa la pregunta: viene a algo concreto.

   Publica `introInit` (lo llama initHome) y `introAbrir` (para «Cambiar»).
   ⚠️ Al tocar este archivo hay que bumpear su ?v= en caudal.html. */
(function(){
  'use strict';

  const KEY='caudal-intro-v1';
  const DATA_URL='caudal-empresas.json?v=20261008b';
  const MAX_SEC=5, MAX_SUG=8, MAX_TEMAS=6;
  let DATA=null, _carga=null;
  // estado del formulario mientras está abierto. `deEmpresa` marca los sectores
  // que llegaron por la empresa y que la persona no ha tocado: si quita la
  // empresa, esos se van con ella; los que marcó a mano se quedan.
  let F={sectores:[], deEmpresa:new Set(), empresa:null};
  let _sug=[], _sugIdx=-1;

  const $=id=>document.getElementById(id);
  const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const norm=s=>String(s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase()
    .replace(/[^a-z0-9& ]+/g,' ').replace(/\s+/g,' ').trim();

  function leer(){ try{ const o=JSON.parse(localStorage.getItem(KEY)||'null'); return o&&o.v===1?o:null; }catch(e){ return null; } }
  function guardar(o){ try{ localStorage.setItem(KEY,JSON.stringify(Object.assign({v:1,ts:Date.now()},o))); }catch(e){} }

  function cargar(){
    if(DATA) return Promise.resolve(DATA);
    if(_carga) return _carga;
    _carga=fetch(DATA_URL).then(r=>{ if(!r.ok) throw new Error('HTTP '+r.status); return r.json(); }).then(d=>{
      d._sec={}; (d.sectores||[]).forEach(s=>{ d._sec[s.k]=s; });
      (d.empresas||[]).forEach(e=>{
        e._nn=norm(e.n);
        // espacios alrededor: así «¿alguna palabra empieza por X?» es un indexOf
        e._q=' '+[e._nn].concat((e.a||[]).map(norm)).join(' ')+' ';
      });
      DATA=d; return d;
    }).catch(e=>{ _carga=null; throw e; });
    return _carga;
  }

  const nombreSec=k=>(DATA&&DATA._sec[k]&&DATA._sec[k].n)||k;
  const logoUrl=e=>(e&&e.k&&e.l&&DATA&&DATA.logos)?DATA.logos+encodeURIComponent(e.k)+'.png':'';
  function iniciales(n){
    const w=String(n||'').replace(/\(.*?\)/g,'').trim().split(/\s+/).filter(Boolean);
    return ((w[0]||'')[0]||'?').toUpperCase()+((w[1]||'')[0]||'').toUpperCase();
  }
  function marca(e,cls){
    const u=logoUrl(e);
    // si el logo no carga se cae a las iniciales, nunca a una imagen rota
    return u
      ? `<span class="${cls}"><img src="${esc(u)}" alt="" loading="lazy" onerror="this.parentNode.textContent='${esc(iniciales(e.n))}';this.parentNode.classList.add('ini')"></span>`
      : `<span class="${cls} ini">${esc(iniciales(e.n))}</span>`;
  }

  /* ---------- búsqueda en el diccionario ---------- */
  function buscar(q){
    const n=norm(q); if(n.length<2||!DATA) return [];
    const out=[];
    for(const e of DATA.empresas){
      const i=e._q.indexOf(' '+n); if(i<0) continue;
      // nombre que empieza por lo escrito > palabra del nombre > alias
      const r=e._nn.startsWith(n)?3:((' '+e._nn+' ').indexOf(' '+n)>=0?2:1);
      out.push([r,e]);
    }
    out.sort((a,b)=>b[0]-a[0] || (a[1].g?1:0)-(b[1].g?1:0) || a[1].n.length-b[1].n.length);
    return out.slice(0,MAX_SUG).map(x=>x[1]);
  }

  /* ---------- el formulario ---------- */
  function pintarSectores(){
    const box=$('introSecs'); if(!box||!DATA) return;
    box.innerHTML=DATA.sectores.map(s=>{
      const on=F.sectores.includes(s.k);
      const por=on&&F.deEmpresa.has(s.k)&&F.empresa?` <span class="intro-por">por ${esc(F.empresa.n)}</span>`:'';
      return `<button type="button" class="chip intro-sec${on?' on':''}" data-k="${esc(s.k)}" aria-pressed="${on}">${esc(s.n)}${por}</button>`;
    }).join('');
    box.querySelectorAll('.intro-sec').forEach(b=>{ b.onclick=()=>toggleSec(b.dataset.k); });
    const c=$('introCuenta');
    if(c){
      const n=F.sectores.length;
      c.textContent=n===0?'Elige uno o varios.':(n>=MAX_SEC?`Llegaste al máximo de ${MAX_SEC}. Quita uno para cambiarlo.`:`${n} ${n===1?'sector elegido':'sectores elegidos'} · puedes sumar hasta ${MAX_SEC}.`);
    }
    const ok=$('introOk'); if(ok) ok.disabled=F.sectores.length===0;
  }
  function toggleSec(k){
    const i=F.sectores.indexOf(k);
    if(i>=0) F.sectores.splice(i,1);
    else if(F.sectores.length<MAX_SEC) F.sectores.push(k);
    // tocarlo a mano lo vuelve de la persona, no de la empresa
    F.deEmpresa.delete(k);
    pintarSectores();
  }

  function pintarEmpresa(){
    const box=$('introEmpSel'); if(!box) return;
    const e=F.empresa;
    if(!e){ box.innerHTML=''; box.hidden=true; return; }
    box.hidden=false;
    const toca=(e.x||[]).length
      ? `Toca ${e.x.length===1?'el sector':'los sectores'} <b>${e.x.map(k=>esc(nombreSec(k))).join(' · ')}</b>. Los marcamos arriba; quita los que no te sirvan.`
      : (e.libre?'No está todavía en nuestro listado de empresas, así que no te sugerimos sector: márcalo arriba.'
                :'No le asociamos un sector en particular: márcalo arriba.');
    box.innerHTML=`<div class="intro-emp-card">
      ${marca(e,'intro-logo')}
      <div class="intro-emp-txt"><div class="intro-emp-n">${esc(e.n)}${e.g?' <span class="intro-tag">gremio</span>':''}</div><div class="intro-emp-d">${toca}</div></div>
      <button type="button" class="intro-x" id="introEmpX" aria-label="Quitar ${esc(e.n)}">×</button>
    </div>`;
    $('introEmpX').onclick=()=>quitarEmpresa(true);
  }
  function elegirEmpresa(e){
    quitarEmpresa(false);
    F.empresa=e.libre?{n:e.n,libre:1}:{k:e.k,n:e.n,x:e.x||[],l:e.l?1:0,g:e.g?1:0};
    (F.empresa.x||[]).forEach(k=>{
      if(!F.sectores.includes(k) && F.sectores.length<MAX_SEC){ F.sectores.push(k); F.deEmpresa.add(k); }
    });
    const inp=$('introEmp'); if(inp) inp.value='';
    cerrarSug(); pintarEmpresa(); pintarSectores();
  }
  function quitarEmpresa(repintar){
    F.sectores=F.sectores.filter(k=>!F.deEmpresa.has(k));
    F.deEmpresa.clear(); F.empresa=null;
    if(repintar){ pintarEmpresa(); pintarSectores(); const i=$('introEmp'); if(i) i.focus(); }
  }

  function cerrarSug(){ const l=$('introSug'); if(l){ l.hidden=true; l.innerHTML=''; } _sug=[]; _sugIdx=-1; const i=$('introEmp'); if(i) i.setAttribute('aria-expanded','false'); }
  function pintarSug(q){
    const l=$('introSug'), inp=$('introEmp'); if(!l||!inp) return;
    const txt=String(q||'').trim();
    _sug=buscar(txt);
    // «Usar lo que escribí» solo cuando ninguna del listado empieza así: mientras
    // se escribe «ube», ofrecer «Usar ube» al lado de Uber es ruido
    if(txt.length>=3 && !_sug.some(e=>e._nn.startsWith(norm(txt)))) _sug.push({n:txt,libre:1});
    _sugIdx=-1;
    if(!_sug.length){ cerrarSug(); return; }
    l.innerHTML=_sug.map((e,i)=>e.libre
      ? `<li role="option" id="introSug${i}" class="intro-sug-libre" data-i="${i}">Usar «${esc(e.n)}» · no está en nuestro listado</li>`
      : `<li role="option" id="introSug${i}" data-i="${i}">${marca(e,'intro-logo sm')}<span class="intro-sug-n">${esc(e.n)}</span><span class="intro-sug-s">${e.g?'gremio · ':''}${esc((e.x||[]).map(nombreSec).join(' · ')||'—')}</span></li>`).join('');
    l.hidden=false; inp.setAttribute('aria-expanded','true');
    // mousedown y no click: el blur del input cerraría la lista antes del click
    l.querySelectorAll('li').forEach(li=>{ li.onmousedown=ev=>{ ev.preventDefault(); elegirEmpresa(_sug[+li.dataset.i]); }; });
  }
  function moverSug(d){
    if(!_sug.length) return;
    _sugIdx=(_sugIdx+d+_sug.length)%_sug.length;
    const l=$('introSug'), inp=$('introEmp');
    l.querySelectorAll('li').forEach((li,i)=>li.classList.toggle('on',i===_sugIdx));
    if(inp) inp.setAttribute('aria-activedescendant','introSug'+_sugIdx);
    const on=l.querySelector('li.on'); if(on) on.scrollIntoView({block:'nearest'});
  }

  function pintarFormulario(){
    const box=$('intro'); if(!box) return;
    box.innerHTML=`<div class="intro-card">
      <div class="home-eyebrow">Antes de empezar · menos de un minuto</div>
      <h1 id="introT">¿En qué <em>sector</em> está tu organización?</h1>
      <p class="intro-lead">Así Caudal te muestra primero lo que te toca. Puedes elegir varios: una empresa como Uber está a la vez en transporte, trabajo y consumo.</p>
      <div class="intro-secs" id="introSecs" role="group" aria-labelledby="introT"></div>
      <div class="intro-cuenta" id="introCuenta" aria-live="polite"></div>

      <h2 class="intro-h2" id="introEmpT">¿Qué empresa u organización es? <span>opcional</span></h2>
      <p class="intro-lead">Si nos lo dices, marcamos los sectores que toca y la búsqueda arranca por ella.</p>
      <div class="intro-emp">
        <input id="introEmp" type="search" autocomplete="off" placeholder="Escribe el nombre: Uber, Ecopetrol, Bancolombia, ANDI…"
          role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="introSug" aria-labelledby="introEmpT" />
        <ul class="intro-sug" id="introSug" role="listbox" hidden></ul>
      </div>
      <div id="introEmpSel" hidden></div>

      <div class="intro-acc">
        <button type="button" class="intro-ok" id="introOk" disabled>Ver Caudal para mi sector →</button>
        <button type="button" class="intro-skip" id="introSkip">Prefiero ver todo</button>
      </div>
      <p class="intro-nota">Se guarda solo en este navegador y lo puedes cambiar cuando quieras.</p>
    </div>`;
    const inp=$('introEmp');
    let t=null;
    inp.addEventListener('input',()=>{ clearTimeout(t); t=setTimeout(()=>pintarSug(inp.value),90); });
    inp.addEventListener('keydown',e=>{
      if(e.key==='ArrowDown'){ e.preventDefault(); moverSug(1); }
      else if(e.key==='ArrowUp'){ e.preventDefault(); moverSug(-1); }
      else if(e.key==='Enter'){ e.preventDefault(); if(_sug.length) elegirEmpresa(_sug[_sugIdx>=0?_sugIdx:0]); }
      else if(e.key==='Escape'){ cerrarSug(); }
    });
    inp.addEventListener('blur',()=>setTimeout(cerrarSug,120));
    $('introOk').onclick=confirmar;
    $('introSkip').onclick=saltar;
    pintarSectores(); pintarEmpresa();
  }

  /* ---------- mostrar / ocultar ---------- */
  function mostrar(){
    const home=$('view-home'), box=$('intro'); if(!home||!box) return;
    const prev=leer();
    F={sectores:(prev&&prev.sectores||[]).slice(), deEmpresa:new Set(), empresa:prev&&prev.empresa||null};
    home.classList.add('intro-on'); box.hidden=false;
    box.innerHTML='<div class="intro-card"><div class="home-eyebrow">Antes de empezar</div><p class="intro-lead">Cargando los sectores…</p></div>';
    window.scrollTo({top:0,behavior:'instant'});
    cargar().then(()=>{
      // los sectores guardados que ya no existen se descartan sin ruido
      F.sectores=F.sectores.filter(k=>DATA._sec[k]);
      // al reabrir, los sectores que coinciden con la empresa guardada vuelven a
      // contar como suyos: si la quita, se van con ella
      if(F.empresa) (F.empresa.x||[]).forEach(k=>{ if(F.sectores.includes(k)) F.deEmpresa.add(k); });
      pintarFormulario();
      const h=$('introT'); if(h){ h.setAttribute('tabindex','-1'); h.focus({preventScroll:true}); }
    }).catch(()=>{
      // sin el listado la pregunta no tiene sentido: se deja pasar a la portada
      // en vez de trabar la entrada
      ocultar();
    });
  }
  function ocultar(){
    const home=$('view-home'), box=$('intro');
    if(home) home.classList.remove('intro-on');
    if(box){ box.hidden=true; box.innerHTML=''; }
    pintarFranja();
  }
  function confirmar(){
    if(!F.sectores.length) return;
    guardar({sectores:F.sectores, empresa:F.empresa});
    ocultar(); window.scrollTo({top:0,behavior:'instant'});
  }
  function saltar(){ guardar({saltado:true}); ocultar(); }

  /* ---------- la franja «Para ti» en la portada ---------- */
  function abrirSector(k){
    if(typeof window.showView==='function') window.showView('cliente');
    if(typeof window.cliLoad==='function') window.cliLoad({sector:k});
  }
  function buscarTema(t){
    if(typeof window.uniSearch!=='function') return;
    const uq=$('uq'); if(uq) uq.value=t;
    window.uniSearch(t);
  }
  function pintarFranja(){
    const box=$('introStrip'); if(!box) return;
    const st=leer();
    if(!st){ box.hidden=true; box.innerHTML=''; return; }
    if(st.saltado || !(st.sectores||[]).length){
      box.hidden=false;
      box.innerHTML=`<button type="button" class="intro-strip-cta" id="introReabrir">Cuéntanos tu sector y Caudal te muestra primero lo tuyo →</button>`;
      $('introReabrir').onclick=mostrar;
      return;
    }
    cargar().then(()=>{
      const secs=st.sectores.filter(k=>DATA._sec[k]);
      const e=st.empresa;
      const temas=[];
      // por turnos, uno de cada sector: con tres sectores, que no se queden
      // los temas del primero con los seis cupos
      for(let i=0;temas.length<MAX_TEMAS && i<3;i++) secs.forEach(k=>{
        const t=(DATA._sec[k].t||[])[i];
        if(t && temas.length<MAX_TEMAS && !temas.includes(t)) temas.push(t);
      });
      box.hidden=false;
      box.innerHTML=`<div class="intro-strip-row">
          <span class="chips-label intro-strip-lbl">Para ti</span>
          ${e?`<button type="button" class="chip intro-strip-emp" data-q="${esc(e.n)}" title="Buscar ${esc(e.n)} en las seis fuentes">${marca(e,'intro-logo xs')}${esc(e.n)}</button>`:''}
          ${secs.map(k=>`<button type="button" class="chip intro-strip-sec" data-k="${esc(k)}" title="Abrir el radar de ${esc(nombreSec(k))} en la Rosa de los Vientos">${esc(nombreSec(k))}</button>`).join('')}
          <button type="button" class="intro-strip-edit" id="introCambiar">Cambiar</button>
        </div>
        ${temas.length?`<div class="intro-strip-row"><span class="chips-label intro-strip-lbl">Empieza por</span>
          ${temas.map(t=>`<button type="button" class="chip chip-tema" data-q="${esc(t)}">${esc(t)}</button>`).join('')}</div>`:''}`;
      box.querySelectorAll('[data-q]').forEach(b=>{ b.onclick=()=>buscarTema(b.dataset.q); });
      box.querySelectorAll('.intro-strip-sec').forEach(b=>{ b.onclick=()=>abrirSector(b.dataset.k); });
      $('introCambiar').onclick=mostrar;
    }).catch(()=>{ box.hidden=true; });
  }

  /* initHome lo llama después de resolver la vista inicial. Solo se pregunta
     cuando la persona entra a la portada sin un destino: quien llega con un
     enlace a un pilar o a un tema viene a eso. */
  function introInit(){
    const hash=location.hash.slice(1);
    const conDestino=(hash && hash!=='home') || new URLSearchParams(location.search).get('tema');
    if(!leer() && !conDestino) mostrar();
    else pintarFranja();
  }

  Object.assign(window,{introInit, introAbrir:mostrar});
})();
