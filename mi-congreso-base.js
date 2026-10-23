/* ═══════════════════════════════════════════════════════════════════
   Mi Congreso · base compartida del hub y de las 8 páginas de módulo
   ───────────────────────────────────────────────────────────────────
   Va DESPUÉS de legislativo-base.js (esc, fmt, norm, tCase, depNice, call,
   autoresDe) y de legislativo-electos.js (ELECTOS, bancadaOf).

   Todo sale de fuentes que ya existen:
     · ELECTOS (legislativo-electos.js)      → identidad y bancada
     · comisiones-2026.json (S3)             → comisión y mesa directiva
     · ordenes-vigentes.json (S3)            → agenda de comisiones y plenarias
     · action:'radicados'                    → proyectos que firma
     · action:'congresista'                  → voto nominal + citaciones
     · action:'medios'                       → prensa
     · action:'citaciones' · 'bancadas' · 'bloqueo' · 'stats' → contexto
     · endoso/index.json (S3)                → foto, votos 2026 y ficha
   La elección se guarda en localStorage['mi-congreso-v1'] y la comparten
   todas las páginas. Lo pesado (radicados, récord de voto, prensa) se guarda
   en sessionStorage unos minutos: ir de una página a otra no repite 2,4 MB.
   ═══════════════════════════════════════════════════════════════════ */
(function(){
  const S3='https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output';
  const URL_COM=S3+'/legislativo/comisiones-2026.json';
  const URL_ORD=S3+'/legislativo/ordenes-vigentes.json';
  const URL_ENDOSO=S3+'/endoso/index.json';
  const URL_PRES=S3+'/presidencial/index-presidencial.json';
  const S3_PHOTOS=S3+'/fotos-candidatos';
  const KEY='mi-congreso-v1';

  const MODULOS=[
    {id:'agenda',   href:'mi-congreso-agenda.html',    t:'Mi agenda'},
    {id:'proyectos',href:'mi-congreso-proyectos.html', t:'Mis proyectos'},
    {id:'reloj',    href:'mi-congreso-reloj.html',     t:'Reloj de trámite'},
    {id:'votos',    href:'mi-congreso-votos.html',     t:'Cómo he votado'},
    {id:'control',  href:'mi-congreso-control.html',   t:'Control político'},
    {id:'prensa',   href:'mi-congreso-prensa.html',    t:'En la prensa'},
    {id:'bancada',  href:'mi-congreso-bancada.html',   t:'Mi bancada'},
    {id:'fuerzas',  href:'mi-congreso-fuerzas.html',   t:'Fuerzas'},
    /* solo para quien tenga la escucha de redes encendida (ver escucha()) */
    {id:'redes',    href:'mi-congreso-redes.html',     t:'En redes', solo:true},
  ];
  /* ── escucha de redes · encendida persona por persona ──────────────
     No es un módulo de todos: cada lectura cuesta plata (Apify) y se enciende
     a mano en tools/mi-congreso/escucha/cuentas.json. El recolector deja la
     última lectura en mi-congreso-data/escucha/<slug>.json y ESA es la llave:
     si el archivo existe para la persona elegida, aparecen la tarjeta y la
     página; si no (404), ni se nombran. Se comprueba que el JSON sea de esa
     persona para no pintarle a nadie las cuentas de otra. */
  const escuchaSlug=e=>norm(e.nombre).replace(/[^a-z0-9ñ]+/g,'-').replace(/^-|-$/g,'');
  let ESCUCHA_ON=false;
  function escucha(e){
    return memo('esc:'+e.nombre,async()=>{
      const r=await fetch(`mi-congreso-data/escucha/${escuchaSlug(e)}.json?v=${Math.floor(Date.now()/600000)}`,{cache:'default'});
      if(!r.ok) return null;
      const d=await r.json();
      if(!d||!d.redes||!d.congresista||d.congresista.nombre!==e.nombre||d.congresista.corp!==e.corp) return null;
      ESCUCHA_ON=true; return d;
    }).catch(()=>null);
  }

  /* ── texto ───────────────────────────────────────────────────────── */
  const initials=n=>String(n||'').trim().split(/\s+/).slice(0,2).map(w=>w[0]||'').join('').toUpperCase();
  const toks=s=>norm(s).replace(/[^a-z0-9ñ\s]/g,' ').split(/\s+/).filter(t=>t.length>2&&!/^(h\.?[sr]\.?|de|del|la|los|las|y)$/.test(t));
  /* dos nombres son la misma persona si el más corto cabe entero en el largo
     y comparten al menos dos tokens (un apellido solo casa homónimos) */
  function mismaPersona(a,b){
    const A=toks(a), B=toks(b); if(A.length<2||B.length<2) return false;
    const [c,l]=A.length<=B.length?[A,B]:[B,A];
    return c.every(t=>l.includes(t));
  }
  const MES=['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
  const MESL=['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
  const fechaCorta=f=>{ const m=String(f||'').match(/(\d{4})[-/](\d{2})[-/](\d{2})/); if(!m) return ''; return `${+m[3]} ${MES[+m[2]-1]}`; };
  const fechaLarga=f=>{ const m=String(f||'').match(/(\d{4})[-/](\d{2})[-/](\d{2})/); if(!m) return ''; return `${+m[3]} de ${MESL[+m[2]-1]} de ${m[1]}`; };
  const DIAS=['dom','lun','mar','mié','jue','vie','sáb'];
  const dia=f=>new Date(String(f).slice(0,10)+'T12:00:00');
  const diaCorto=f=>{ const d=dia(f); return isNaN(d)?fechaCorta(f):DIAS[d.getDay()]+' '+fechaCorta(f); };
  const iso=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  function hoyBog(){
    const p=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Bogota',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
    const t=k=>p.find(x=>x.type===k)?.value; return `${t('year')}-${t('month')}-${t('day')}`;
  }
  const TITLE_PREF=/^\s*por\s+(?:medio\s+de\s+)?(?:el\s+medio\s+de\s+)?(?:la|el|los|las)?\s*cual(?:es)?\s+se\s+/i;
  function shortTitle(t){
    let s=String(t||'').replace(TITLE_PREF,'').replace(/\s+/g,' ').trim();
    if(s.length<6) s=String(t||'').replace(/\s+/g,' ').trim();
    /* el récord de voto trae a veces solo el número ("089 de 2024 Senado") */
    if(/^\d+\s+de\s+\d{4}/i.test(s)) return s;
    return s.charAt(0).toUpperCase()+s.slice(1).toLowerCase();
  }
  const chamberNice=c=>c==='SENADO'?'Senado':'Cámara de Representantes';
  /* Senado manda «SEXTA»; Cámara manda «Comisión Séptima Constitucional
     Permanente» → un solo rótulo corto: «Comisión Séptima» */
  const comisionNice=c=>{ const m=norm(c).match(/(primera|segunda|tercera|cuarta|quinta|sexta|septima)/); return m?'Comisión '+tCase(m[1]).replace('Septima','Séptima'):'Comisión '+tCase(String(c||'').replace(/^comisi[oó]n\s+/i,'')); };
  const nombreCom=k=>k==='ACUSACIONES'?'Investigación y Acusación':'Comisión '+tCase(k).replace('Septima','Séptima');
  const ambitoNice=a=>String(a||'').replace(/\bSeptima\b/,'Séptima');
  /* recorte por palabra, con puntos suspensivos */
  const cut=(s,n)=>{ s=String(s||''); if(s.length<=n) return s; const c=s.slice(0,n); const i=c.lastIndexOf(' '); return (i>n*0.6?c.slice(0,i):c)+'…'; };
  /* el listado trae Senado en Title Case y Cámara en MAYÚSCULA SOSTENIDA */
  const nice=n=>{ n=String(n||''); return n===n.toUpperCase()?tCase(n):n; };
  /* nombre corto (primer nombre + primer apellido): así lo escribe la prensa */
  const corto=e=>{ const t=nice(e.nombre).split(/\s+/); return t.length>=3?`${t[0]} ${t[t.length-2]}`:nice(e.nombre); };
  const pct=(a,b)=>b?Math.round(100*a/b):0;

  /* ── identidad ───────────────────────────────────────────────────── */
  function me(){
    let s=null; try{ s=JSON.parse(localStorage.getItem(KEY)||'null'); }catch(err){}
    return (s&&ELECTOS.find(x=>x.nombre===s.nombre&&x.corp===s.corp))||null;
  }
  function guardar(e){ try{ localStorage.setItem(KEY,JSON.stringify({nombre:e.nombre,corp:e.corp})); }catch(err){} }
  function olvidar(){ try{ localStorage.removeItem(KEY); }catch(err){} }
  /* las páginas de módulo necesitan a alguien elegido: si no, al hub, que
     después de elegir devuelve a la página pedida */
  function requireMe(page){
    const e=me();
    if(!e){ location.replace('mi-congreso.html?ir='+encodeURIComponent(page)); return null; }
    return e;
  }

  /* ── red y caché ─────────────────────────────────────────────────── */
  const _cache={};
  function getJSON(url,bust){
    if(_cache[url]) return _cache[url];
    _cache[url]=(async()=>{
      const r=await fetch(url+(bust?'?v='+Math.floor(Date.now()/bust):''),{cache:'default'});
      if(!r.ok) throw new Error('HTTP '+r.status); return r.json();
    })();
    _cache[url].catch(()=>{ delete _cache[url]; });
    return _cache[url];
  }
  function sesGet(k,ttlMin){
    try{ const v=JSON.parse(sessionStorage.getItem('mc:'+k)||'null'); if(v&&Date.now()-v.t<ttlMin*60000) return v.d; }catch(err){}
    return null;
  }
  function sesSet(k,d){ try{ sessionStorage.setItem('mc:'+k,JSON.stringify({t:Date.now(),d})); }catch(err){ /* cuota llena: se sigue sin caché */ } }
  const _memo={};
  function memo(k,fn){ if(!_memo[k]){ _memo[k]=fn(); _memo[k].catch(()=>{ delete _memo[k]; }); } return _memo[k]; }
  async function api(payload,ttlMin){
    const k='api:'+JSON.stringify(payload);
    const hit=ttlMin?sesGet(k,ttlMin):null; if(hit) return hit;
    return memo(k,async()=>{ const d=await call(payload); if(ttlMin&&d&&!d.error) sesSet(k,d); return d; });
  }

  /* ── comisión ────────────────────────────────────────────────────── */
  function comision(e){
    return memo('com:'+e.nombre,async()=>{
      const j=await getJSON(URL_COM,3600000);
      const corp=e.corp==='SENADO'?'senado':'camara';
      for(const [k,v] of Object.entries(j.comisiones||{})){
        if(((v||{})[corp]||[]).some(m=>mismaPersona(m.nombre,e.nombre))){
          const mesa=(v.mesa||[]).find(p=>p.corp===corp&&mismaPersona(p.nombre,e.nombre));
          return {key:k,nombre:nombreCom(k),mesa,miembros:v,todas:j.comisiones};
        }
      }
      return {key:null,nombre:null,mesa:null,miembros:null,todas:j.comisiones};
    });
  }

  /* ── órdenes del día ─────────────────────────────────────────────── */
  function ordenes(){
    return memo('ord',async()=>{
      const j=await getJSON(URL_ORD,300000); const hoy=hoyBog();
      const todas=j.ordenes||[];
      return {v:j.v, todas, vigentes:todas.filter(o=>(o.fecha_fin||o.fecha)>=hoy), cobertura:j.cobertura};
    });
  }
  /* ¿esta orden es de mi comisión o de la plenaria de mi cámara? */
  function esMia(o,e,comKey){
    const miCam=e.corp==='SENADO'?/senado/i:/c[aá]mara/i;
    if(!miCam.test(o.corporacion||'')) return false;
    if(/plenaria/i.test(o.ambito||'')) return true;
    if(!comKey) return false;
    const re=new RegExp(comKey==='ACUSACIONES'?'acusaci':(comKey==='SEPTIMA'?'s[eé]ptima':tCase(comKey)),'i');
    return re.test(o.ambito||'');
  }

  /* ── avance del trámite ──────────────────────────────────────────────
     Etapa 1-6 desde el ESTADO oficial del registro. El Senado lo da fino;
     la Cámara casi siempre dice solo «Trámite en Comisión», así que ahí la
     etapa se completa con el orden del día: si está agendado, está en debate. */
  const ETAPAS=['Radicado','En comisión','En primer debate','Aprobado en primer debate','En segundo debate','Pasa a la otra cámara'];
  function etapaDe(estado){
    const s=norm(estado);
    if(/archivad|retirad/.test(s)) return {fin:'Archivado o retirado'};
    if(/acumulad/.test(s)) return {fin:'Acumulado a otro proyecto'};
    if(/enviar a comision/.test(s)) return {n:1};
    if(/segundo debate/.test(s)) return {n:/discutir/.test(s)?5:4};
    if(/discutir ponencia|debate de comision/.test(s)) return {n:3};
    if(/tramite en plenaria/.test(s)) return {n:4};
    if(/ponen|tramite en comision/.test(s)) return {n:2};
    return {n:1};
  }
  function etapaEf(x){
    const e=etapaDe(x.estado); if(e.fin) return e;
    let n=e.n; const c=x._citas||[];
    if(c.length) n=Math.max(n,c.some(k=>/plenaria/i.test(k.o.ambito||''))?5:3);
    return {n};
  }
  /* «033 de 2026 Cámara» · «447/2026C» · «298/26» → «33/26C» */
  function numKey(num,camDef){
    const m=String(num||'').match(/0*(\d{1,4})\s*(?:de|\/)\s*(?:20)?(\d{2})\s*(c[aá]mara|senado|c|s)?/i);
    if(!m) return null;
    const c=m[3]?(/^s/i.test(m[3])?'S':'C'):camDef;
    return c?`${+m[1]}/${m[2]}${c}`:null;
  }
  function citasDe(x,ord){
    const keys=new Set([numKey(x.numero_senado,'S'),numKey(x.numero_camara,'C')].filter(Boolean));
    const out=[];
    for(const o of ord){
      const ps=o.proyectos||[], cam=/senado/i.test(o.corporacion||'')?'S':'C';
      ps.forEach((p,i)=>{ if(keys.has(numKey(p.numero,cam))) out.push({o,pos:i+1,tot:ps.length}); });
    }
    return out.sort((a,b)=>String(a.o.fecha).localeCompare(String(b.o.fecha)));
  }
  const numDe=x=>x._cam==='Cámara'?(x.numero_camara||x.numero_senado):(x.numero_senado||x.numero_camara);
  function citaTxt(c){
    const amb=ambitoNice(c.o.ambito||c.o.corporacion);
    return `${esc(amb)}${/plenaria/i.test(amb)?'':' de '+esc(c.o.corporacion)}, ${esc(diaCorto(c.o.fecha))} · puesto ${c.pos} de ${c.tot} en la lista`+(c.o.url?` · <a href="${esc(c.o.url)}" target="_blank" rel="noopener">orden del día ↗</a>`:'');
  }
  function avanceHtml(x){
    const e=etapaEf(x);
    if(e.fin) return `<div class="mc-av fin">${ETAPAS.map(()=>'<i></i>').join('')}</div><div class="mc-av-l"><b>${esc(e.fin)}</b></div>`;
    return `<div class="mc-av" title="${esc(ETAPAS[e.n-1])}">${ETAPAS.map((_,k)=>`<i class="${k<e.n?'on':''}"></i>`).join('')}</div><div class="mc-av-l">Etapa ${e.n} de 6 · <b>${esc(ETAPAS[e.n-1])}</b></div>`;
  }
  const tipoDe=x=>{ const t=norm(x.tipo_de_ley||''); if(/acto/.test(t)) return 'al'; if(/estatut/.test(t)) return 'est'; if(/organ/.test(t)) return 'org'; return 'ord'; };
  const TIPO_NICE={ord:'Ley ordinaria',org:'Ley orgánica',est:'Ley estatutaria',al:'Acto legislativo'};

  /* ── mis proyectos ───────────────────────────────────────────────────
     Los radicados de la legislatura viva pesan 2,4 MB: se filtran a los
     suyos y SOLO eso se guarda en la sesión. Las citas en el orden del día
     se recalculan siempre (cambian varias veces al día). */
  function mios(e){
    return memo('mios:'+e.nombre,async()=>{
      const k='mios:'+e.corp+':'+e.nombre;
      let base=sesGet(k,15);
      if(!base){
        const todos=await radicadosTodos(); const r={legislatura:todos._leg};
        base=todos.map(x=>{
          const auts=autoresDe(x.autor); const i=auts.findIndex(a=>mismaPersona(a,e.nombre));
          if(i<0) return null;
          return {numero_senado:x.numero_senado,numero_camara:x.numero_camara,titulo:x.titulo,estado:x.estado,
            tipo_de_ley:x.tipo_de_ley,tipologia:x.tipologia,comision:x.comision,fecha:x.fecha,fuente_url:x.fuente_url,
            gaceta:x.gaceta,intentos_previos:x.intentos_previos,_cam:x._cam,_n:auts.length,_primero:i===0,
            _coaut:auts.filter((a,j)=>j!==i).slice(0,150)};
        }).filter(Boolean);
        base._leg=r.legislatura;
        sesSet(k,base);
      }
      const ord=await ordenes().catch(()=>({vigentes:[]}));
      const out=base.map(x=>({...x,_citas:citasDe(x,ord.vigentes||[])}));
      return out.sort((a,b)=>(b._citas.length>0)-(a._citas.length>0)||String(b.fecha||'').localeCompare(String(a.fecha||'')));
    });
  }
  /* todos los radicados de la legislatura viva (2,4 MB): una sola descarga
     por página, compartida entre «mis proyectos» y el buscador de Fuerzas */
  function radicadosTodos(){
    return memo('radraw',async()=>{
      const r=await call({action:'radicados'});
      const L=[...(r.radicados||[]).map(x=>({...x,_cam:'Senado'})),...(r.radicados_camara||[]).map(x=>({...x,_cam:'Cámara'}))];
      L._leg=r.legislatura; return L;
    });
  }
  /* un radicado cualquiera en la misma forma que los de mios() */
  function proyectoDe(x,e,ord){
    const auts=autoresDe(x.autor); const i=e?auts.findIndex(a=>mismaPersona(a,e.nombre)):-1;
    return {numero_senado:x.numero_senado,numero_camara:x.numero_camara,titulo:x.titulo,estado:x.estado,
      tipo_de_ley:x.tipo_de_ley,tipologia:x.tipologia,comision:x.comision,fecha:x.fecha,fuente_url:x.fuente_url,
      autor:x.autor,_cam:x._cam,_n:auts.length,_primero:i===0,_mio:i>=0,_coaut:auts.filter((a,j)=>j!==i),
      _citas:citasDe(x,ord||[])};
  }
  /* % de avance general: promedio de la etapa sobre los proyectos vivos */
  function avanceGeneral(lista){
    const vivos=lista.filter(x=>!etapaEf(x).fin);
    if(!vivos.length) return {pct:0,vivos:0,fin:lista.length};
    const suma=vivos.reduce((s,x)=>s+etapaEf(x).n,0);
    return {pct:Math.round(100*suma/(6*vivos.length)),vivos:vivos.length,fin:lista.length-vivos.length,
      debate:vivos.filter(x=>etapaEf(x).n>=3).length};
  }

  /* ── reloj del trámite ───────────────────────────────────────────────
     Sesiones ordinarias (art. 138 CP): 20 de julio a 16 de diciembre y
     16 de marzo a 20 de junio. Esos dos periodos son una legislatura.
       · Ley ordinaria / orgánica: si no recibe primer debate en ninguna
         cámara antes del cierre de la legislatura, se archiva (art. 190
         Ley 5ª); ningún proyecto se tramita en más de dos legislaturas
         (art. 162 CP).
       · Ley estatutaria: todo el trámite en una sola legislatura (art. 153 CP).
       · Acto legislativo: ocho debates en dos vueltas, en dos periodos
         ordinarios y consecutivos (art. 375 CP). Caudal lo cuenta como un año.
     Los días de sesión son los hábiles (lun-vie) dentro de esos periodos,
     SIN descontar festivos: es una cota, no el número exacto de sesiones. */
  const periodos=y=>[[`${y}-07-20`,`${y}-12-16`],[`${y+1}-03-16`,`${y+1}-06-20`]];
  const LEG={ini:'2026-07-20',p1fin:'2026-12-16',p2ini:'2027-03-16',fin:'2027-06-20',fin2:'2028-06-20'};
  function enSesion(f){ const y=+f.slice(0,4); for(const yy of [y-1,y]) for(const [a,b] of periodos(yy)) if(f>=a&&f<=b) return true; return false; }
  function diasHabSesion(desde,hasta){
    let n=0; const d=dia(desde), h=dia(hasta);
    while(d<=h){ const k=iso(d), w=d.getDay(); if(w>0&&w<6&&enSesion(k)) n++; d.setDate(d.getDate()+1); }
    return n;
  }
  const diasCal=(a,b)=>Math.round((dia(b)-dia(a))/864e5);
  function legislatura(hoy){
    hoy=hoy||hoyBog();
    const total=diasHabSesion(LEG.ini,LEG.fin), usados=diasHabSesion(LEG.ini,hoy<LEG.fin?hoy:LEG.fin);
    const enReceso=!enSesion(hoy)&&hoy>LEG.ini&&hoy<LEG.fin;
    const cierre=hoy<=LEG.p1fin?LEG.p1fin:(hoy<LEG.p2ini?LEG.p2ini:LEG.fin);
    return {hoy,total,usados,quedan:total-usados,pct:pct(usados,total),enReceso,
      alCierrePeriodo:diasCal(hoy,hoy<=LEG.p1fin?LEG.p1fin:LEG.fin),cierre,
      alFin:diasCal(hoy,LEG.fin)};
  }
  /* ritmo: lo que el proyecto avanzó hacia su meta contra la fracción del
     tiempo de sesión ya consumido. No es una predicción: es «va a tiempo»
     o «se está quedando», con la regla a la vista. */
  function relojDe(x,hoy){
    hoy=hoy||hoyBog();
    const t=tipoDe(x), e=etapaEf(x);
    if(e.fin) return {tipo:t,fin:e.fin,ritmo:'fin',rotulo:'Cerrado'};
    let meta, limite, metaN;
    if(t==='est'){ meta='todo el trámite (4 debates y revisión de la Corte)'; limite=LEG.fin; metaN=6; }
    else if(t==='al'){ meta='la primera vuelta (4 de 8 debates)'; limite=LEG.fin; metaN=6; }
    else if(e.n<4){ meta='el primer debate'; limite=LEG.fin; metaN=4; }
    else { meta='los cuatro debates'; limite=LEG.fin2; metaN=6; }
    const ini=LEG.ini, totalS=diasHabSesion(ini,limite), usados=diasHabSesion(ini,hoy<limite?hoy:limite);
    const tiempo=totalS?usados/totalS:1;
    const avance=Math.min(1,(e.n-1)/(metaN-1));
    const gap=tiempo-avance;
    const ritmo=gap>0.35?'alto':gap>0.1?'medio':'bajo';
    return {tipo:t,n:e.n,meta,limite,quedanS:Math.max(0,totalS-usados),quedanC:Math.max(0,diasCal(hoy,limite)),
      tiempo,avance,ritmo,rotulo:{alto:'Atrasado',medio:'Se está quedando',bajo:'Va a tiempo'}[ritmo]};
  }

  /* ── foto, votos 2026, puntaje electoral ─────────────────────────────
     Puntaje: la MISMA escala de analisis-candidato.html —
     round(100·log10(v+1)/log10(vmax+1)), tope 99, con vmax = votos del
     presidente en segunda vuelta (index-presidencial.json). */
  let LOGMAX=Math.log10(12950642+1);
  const puntaje=v=>v?Math.max(1,Math.min(99,Math.round(100*Math.log10(v+1)/LOGMAX))):1;
  /* índice de candidaturas 2026: casa a cualquier electo con su candidatura
     (votos, foto) y da el total de cada lista. Tokens precalculados: comparar
     285 electos contra ~2.800 candidaturas tokenizando en cada vuelta costaba
     medio segundo. CITREP va en el índice como corporación propia. */
  function indiceElectoral(){
    return memo('idx',async()=>{
      const [d,pres]=await Promise.all([getJSON(URL_ENDOSO),getJSON(URL_PRES).catch(()=>null)]);
      if(pres&&pres.vmax) LOGMAX=Math.log10(pres.vmax+1);
      const all=Array.isArray(d)?d:(d.candidatos||[]);
      const cands=all.filter(c=>c.tipo!=='partido'); cands.forEach(c=>{ c._t=toks(c.nombre); });
      const partidos=all.filter(c=>c.tipo==='partido');
      const casa=(A,B)=>{ if(A.length<2||B.length<2) return false; const [c,l]=A.length<=B.length?[A,B]:[B,A]; return c.every(t=>l.includes(t)); };
      const esCitrep=x=>/citrep/i.test(x.partido||'');
      const corpDe=x=>esCitrep(x)?'CITREP':(x.corp==='SENADO'?'SENADO':'CAMARA');
      const porCorp={}; cands.forEach(c=>{ const k=(c.corp||'').toUpperCase(); (porCorp[k]=porCorp[k]||[]).push(c); });
      const _h=new Map();
      const hitDe=x=>{
        if(_h.has(x)) return _h.get(x);
        const T=toks(x.nombre), L=porCorp[corpDe(x)]||[];
        const h=L.filter(c=>casa(T,c._t)).sort((a,b)=>(b.votos||0)-(a.votos||0))[0]||null;
        _h.set(x,h); return h;
      };
      const totalLista=(partido,corp)=>{ const k=corp==='SENADO'?'SENADO':'CAMARA'; const p=partidos.find(c=>(c.corp||'').toUpperCase()===k&&norm(c.nombre)===norm(partido)); return p?(p.votosTotal||p.votos||0):0; };
      return {hitDe,porCorp,totalLista,foto:h=>h?`${S3_PHOTOS}/${encodeURIComponent(h.slug)}.jpg`:null,corpDe};
    });
  }
  function electoral(e){
    return memo('elec:'+e.nombre,async()=>{
      const I=await indiceElectoral();
      const hit=I.hitDe(e);
      if(!hit) return {hit:null};
      /* puesto entre los electos de su misma corporación y circunscripción */
      const pares=ELECTOS.filter(x=>x.corp===e.corp&&(e.corp==='SENADO'||x.dep===e.dep));
      const conV=pares.map(x=>({x,v:(I.hitDe(x)||{}).votos||0})).sort((a,b)=>b.v-a.v);
      const puesto=conV.findIndex(r=>r.x===e)+1;
      const deCorp=I.porCorp[I.corpDe(e)]||[];
      const rankCand=deCorp.slice().sort((a,b)=>(b.votos||0)-(a.votos||0)).findIndex(c=>c.slug===hit.slug)+1;
      const lista=e.corp==='SENADO'?I.totalLista(hit.partido||e.partido,'SENADO'):0;
      return {hit,score:puntaje(hit.votos||0),puesto,nPares:pares.length,pares:conV,rankCand,nCand:deCorp.length,
        lista,foto:I.foto(hit)};
    });
  }
  function fotoDe(e){ return electoral(e).then(r=>r.hit?r.foto:null).catch(()=>null); }

  /* ── otras fuentes ───────────────────────────────────────────────── */
  /* récord de voto: un 404 de la API es «sin récord» (null); una falla de red
     es otra cosa ({error:'red'}) y no puede leerse como «nunca ha votado» */
  const voto=e=>api({action:'congresista',q:e.nombre},30).then(d=>(d&&d.encontrado)?d:null).catch(()=>({error:'red'}));
  const prensa=(e,dias)=>api({action:'medios',query:corto(e),dias:dias||30},20);
  const citPanorama=()=>api({action:'citaciones'},60);
  const bancadasDisc=()=>api({action:'bancadas'},60);
  const bloqueo=()=>api({action:'bloqueo'},60);
  const stats=()=>api({action:'stats'},60);
  /* bancada del listado de electos → bancada de la disciplina de Caudal */
  const BANC_CAUDAL={'Pacto Histórico':'Pacto/izq','Centro Democrático':'Centro Democrático','Partido Liberal':'Liberal',
    'Partido Conservador':'Conservador','Partido de la U':'La U','Cambio Radical':'Cambio Radical','Alianza Verde':'Verde/Centro'};

  /* ── correlación de fuerzas de un proyecto ───────────────────────────
     El centro es la COMISIÓN donde está el proyecto: cada silla es un
     miembro real (comisiones-2026.json) y se colorea por la EVIDENCIA que
     hay sobre él, nunca por un bando adivinado:
       · tú · firmó (es coautor) · tu bancada (la OFICIAL, no la lista con la
         que se eligió: Villalba entró por «Ahora Colombia» y es Nuevo
         Liberalismo)
       · suele coincidir / a veces / suele votar distinto: coincidencia de voto
         en las votaciones DISPUTADAS de la legislatura viva (desde el 20-jul),
         persona a persona en el Senado; en Cámara —cuyo voto nominal llega con
         meses de rezago— entre bancadas, medido en el Senado.
       · sin dato: no hay votaciones compartidas suficientes.
     «En contra» no existe: solo se sabría con un voto sobre el proyecto.
     Datos: fuerzas-internas-2026.json (tools/mi-congreso/build_fuerzas_internas.py). */
  const FZ_CAT=[
    {id:'yo',      t:'Tú',                      c:'#14161f'},
    {id:'firmo',   t:'Firmó el proyecto',       c:'#0047FF'},
    {id:'banc',    t:'Tu bancada',              c:'#5b82ff'},
    {id:'afin',    t:'Suele coincidir contigo', c:'#a8bcff'},
    {id:'bisagra', t:'A veces coincide',        c:'#d9d6cb'},
    {id:'distinto',t:'Suele votar distinto',    c:'#5d6271'},
    {id:'sin',     t:'Sin dato de voto',        c:'rgba(20,22,31,.10)'},
  ];
  const FZ_AFIN=60, FZ_BISAGRA=40;
  const COM_KEYS=['PRIMERA','SEGUNDA','TERCERA','CUARTA','QUINTA','SEXTA','SEPTIMA'];
  /* ?local=1 lee los JSON del repo (verificación antes de subir a S3) */
  const LOCAL_FZ=/[?&]local=1\b/.test(location.search);
  const FZ_BASE=LOCAL_FZ?'Bases%20de%20datos/legislativo':S3+'/legislativo';
  const URL_INT=FZ_BASE+'/fuerzas-internas-2026.json';
  /* «Comisión Primera Constitucional Permanente» · «PRIMERA» · «Primera» → PRIMERA */
  function comKeyDe(c){ const m=norm(c).match(/(primera|segunda|tercera|cuarta|quinta|sexta|septima)/); return m?m[1].toUpperCase():null; }
  /* bancada oficial y coincidencia de voto de la legislatura viva */
  function internas(){
    return memo('int',async()=>{
      const d=await getJSON(URL_INT,3600000);
      ['senado','camara'].forEach(c=>(d[c].miembros||[]).forEach((m,i)=>{ m._t=toks(m.n); m._i=i; }));
      return d;
    });
  }
  const casaT=(A,B)=>{ if(A.length<2||B.length<2) return false; const [c,l]=A.length<=B.length?[A,B]:[B,A]; return c.every(t=>l.includes(t)); };
  /* el registro oficial de una persona en su cámara ('senado'|'camara') */
  function oficialDe(I,nombre,corp){
    if(!I) return null; const T=toks(nombre);
    return (I[corp].miembros||[]).find(m=>casaT(T,m._t))||null;
  }
  function bancadaDe(I,nombre,corp,partido){
    const o=oficialDe(I,nombre,corp); if(o) return {name:o.b,partido:o.p,of:true};
    return {name:bancadaOf(partido||'').name,partido:partido||'',of:false};
  }
  /* coincidencia de la persona `m` con el usuario: primero persona a persona
     (Senado, misma cámara), si no, entre bancadas medidas en el Senado */
  function coincidencia(I,yo,corpYo,otro,corpOtro,bYo,bOtro){
    if(!I) return null;
    if(corpYo==='senado'&&corpOtro==='senado'){
      const a=oficialDe(I,yo,'senado'), b=oficialDe(I,otro,'senado');
      if(a&&b){ const k=a._i<b._i?`${a._i}|${b._i}`:`${b._i}|${a._i}`; const r=(I.senado.pares||{})[k]; if(r) return {pct:r[0],n:r[1],via:'persona'}; }
    }
    if(bYo&&bOtro&&bYo!==bOtro){ const r=(I.bancadas||{})[[bYo,bOtro].sort().join('|')]; if(r) return {pct:r[0],n:r[1],via:'bancada'}; }
    return null;
  }
  /* las sillas de la comisión `comKey` de la cámara `corp` ('senado'|'camara') */
  function fuerzas({e,x,com,comKey,corp,I}){
    const v=(com&&com.todas||{})[comKey]||{}; const L=v[corp]||[];
    const autores=x?autoresDe(x.autor||'').concat(x._coaut||[]):[];
    const corpYo=e.corp==='SENADO'?'senado':'camara';
    const miB=bancadaDe(I,e.nombre,corpYo,e.partido);
    const sillas=L.map(m=>{
      const bn=bancadaDe(I,m.nombre,corp,m.partido), col=bancadaOf(bn.partido||m.partido||'').color;
      let cat, co=null;
      if(mismaPersona(m.nombre,e.nombre)) cat='yo';
      else if(x&&(autores.some(a=>mismaPersona(a,m.nombre)))) cat='firmo';
      else if(bn.name===miB.name&&bn.name!=='Otros y coaliciones'&&bn.name!=='Sin dato') cat='banc';
      else { co=coincidencia(I,e.nombre,corpYo,m.nombre,corp,miB.name,bn.name); cat=!co?'sin':co.pct>=FZ_AFIN?'afin':co.pct>=FZ_BISAGRA?'bisagra':'distinto'; }
      return {nombre:m.nombre,partido:bn.partido||m.partido||'',lista:m.partido||'',banc:bn.name,of:bn.of,color:col,cat,pct:co?co.pct:null,nv:co?co.n:null,via:co?co.via:null};
    });
    const ord=FZ_CAT.map(c=>c.id);
    sillas.sort((a,b)=>ord.indexOf(a.cat)-ord.indexOf(b.cat)||(b.pct||0)-(a.pct||0)||String(a.banc).localeCompare(b.banc)||String(a.nombre).localeCompare(b.nombre));
    const n=sillas.length, mayoria=Math.floor(n/2)+1;
    const cuenta={}; FZ_CAT.forEach(c=>cuenta[c.id]=0); sillas.forEach(s=>cuenta[s.cat]++);
    const base=cuenta.yo+cuenta.firmo+cuenta.banc+cuenta.afin;
    const mesa=(v.mesa||[]).filter(p=>p.corp===corp).map(p=>({...p,silla:sillas.find(s=>mismaPersona(s.nombre,p.nombre))||null}));
    const viaPersona=sillas.some(s=>s.via==='persona');
    return {comKey,corp,sillas,n,mayoria,cuenta,base,falta:Math.max(0,mayoria-base),mesa,miB,viaPersona,
      cob:I&&I.senado?I.senado.cobertura:null};
  }
  /* hemiciclo: filas concéntricas, sillas repartidas por longitud de arco y
     ordenadas por ángulo, así cada categoría queda en un solo sector de
     izquierda (con usted) a derecha (lejos) */
  function hemiciclo(F,opt){
    opt=opt||{}; const W=opt.w||560, cx=W/2;
    const n=F.sillas.length; if(!n) return '';
    const rows=n<=16?2:n<=30?3:4, rMax=W*0.44, rMin=rMax*(rows===2?0.6:rows===3?0.5:0.46);
    const radios=Array.from({length:rows},(_,i)=>rows===1?rMax:rMin+(rMax-rMin)*i/(rows-1));
    const sumR=radios.reduce((s,r)=>s+r,0);
    let porFila=radios.map(r=>Math.max(1,Math.round(n*r/sumR)));
    let dif=n-porFila.reduce((s,k)=>s+k,0); porFila[rows-1]+=dif;
    const pos=[];
    radios.forEach((r,i)=>{ const k=porFila[i]; for(let j=0;j<k;j++){ const a=Math.PI*(k===1?0.5:j/(k-1)); pos.push({a,r}); } });
    pos.sort((p,q)=>p.a-q.a||q.r-p.r);
    const paso=Math.min(...radios.map((r,i)=>Math.PI*r/Math.max(1,porFila[i]-1)), (rMax-rMin)/(rows-1));
    const seat=Math.min(W*0.033,paso*0.4);
    const cy=Math.round(rMax+seat+4), H=Math.round(cy+seat+6);
    const col=Object.fromEntries(FZ_CAT.map(c=>[c.id,c.c]));
    const circles=F.sillas.map((s,i)=>{
      const p=pos[i], x=cx-p.r*Math.cos(p.a), y=cy-p.r*Math.sin(p.a);
      const stroke=s.cat==='sin'?'stroke="rgba(20,22,31,.35)" stroke-dasharray="2 2"':s.cat==='bisagra'?'stroke="rgba(20,22,31,.35)"':s.cat==='yo'?'stroke="#f2b705" stroke-width="2.5"':'stroke="#fff"';
      return `<circle class="mc-seat" data-i="${i}" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${seat.toFixed(1)}" fill="${col[s.cat]}" ${stroke} stroke-width="${s.cat==='yo'?2.5:1}"/>`;
    }).join('');
        return `<svg class="mc-hemi" viewBox="0 0 ${W} ${H}" role="img" aria-label="Hemiciclo de la comisión: ${F.n} miembros">${circles}
      <text x="${cx}" y="${cy-rMin*0.42}" class="mc-hemi-n">${F.base}<tspan class="mc-hemi-of"> / ${F.mayoria}</tspan></text>
      <rect x="${cx-rMin*0.55}" y="${cy-rMin*0.3}" width="${rMin*1.1}" height="5" fill="rgba(20,22,31,.08)"/>
      <rect x="${cx-rMin*0.55}" y="${cy-rMin*0.3}" width="${(rMin*1.1*Math.min(1,F.base/F.mayoria)).toFixed(1)}" height="5" fill="${F.base>=F.mayoria?'#15803d':'#0047FF'}"/>
      <text x="${cx}" y="${cy-rMin*0.3+20}" class="mc-hemi-l">base posible · mayoría</text>
    </svg>`;
  }
  function tipSilla(s,F){
    const c=FZ_CAT.find(k=>k.id===s.cat);
    const co=s.pct==null?'':s.via==='persona'
      ?`<div>Coincidió contigo en el <b>${Math.round(s.pct)}%</b> de ${s.nv} votaciones disputadas del Senado en esta legislatura.</div>`
      :`<div>Su bancada (${esc(s.banc)}) coincidió con la tuya en el <b>${Math.round(s.pct)}%</b> de ${s.nv} votaciones disputadas del Senado en esta legislatura.</div>`;
    const lista=s.of&&s.lista&&norm(s.lista)!==norm(s.partido)?`<div style="opacity:.75">Se eligió por: ${esc(s.lista)}</div>`:'';
    return `<h5>${esc(nice(s.nombre))}</h5><div>Bancada: <b>${esc(s.banc)}</b>${s.of?'':' (según la lista con la que se eligió)'}</div>${lista}<div style="margin-top:.25rem"><b>${esc(c.t)}</b></div>${co}`;
  }
  /* la ficha completa de Caudal para un radicado. Los radicados no traen el
     id del dataset: se resuelve por título y se confirma por NÚMERO (nunca
     por parecido de título solo). El articulado se valida contra el título:
     medido oct-2026, a los proyectos de Cámara de la legislatura viva les
     llega a veces el articulado de OTRO proyecto, y eso no se puede mostrar. */
  const tokNum=s=>{ const m=String(s||'').match(/0*(\d{1,4})\s*\/\s*(?:20)?(\d{2})/); return m?`${+m[1]}/${m[2]}`:null; };
  const normT=s=>norm(s).replace(/[^a-z0-9ñ ]/g,' ').replace(/\s+/g,' ').trim();
  function fichaDe(x){
    const key=String(x.numero_senado||'')+'|'+String(x.numero_camara||'');
    return memo('ficha:'+key,async()=>{
      const hit0=sesGet('ficha:'+key,60); if(hit0) return hit0;
      const q=normT(x.titulo).split(' ').slice(0,14).join(' ');
      const r=await call({action:'buscar',query:q,limit:10,anio_min:2026});
      const tS=tokNum(x.numero_senado), tC=tokNum(x.numero_camara);
      const hit=(r.resultados||[]).find(h=>(tS&&tokNum(h.ns)===tS)||(tC&&tokNum(h.nc)===tC));
      if(!hit){ const out={encontrada:false}; sesSet('ficha:'+key,out); return out; }
      const f=await call({action:'proyecto',id:hit.id,tb:hit.tb||'pdly'});
      if(!f||f.error) return {encontrada:false};
      let art=f.articulado||null, artMal=false;
      if(art){ const a=normT(art.titulo).slice(0,60), b=normT(f.titulo).slice(0,60), c=normT(x.titulo).slice(0,60); if(a!==b&&a!==c){ art=null; artMal=true; } }
      const out={encontrada:true,id:hit.id,tb:hit.tb,titulo:f.titulo,comision:f.comision,art,artMal,
        artCob:f.articulado_cobertura||null,importancia:f.importancia||null,
        bloqueo:f.bloqueo||null,bloqueoSen:f.bloqueo_senado||null,
        votoNominal:!!(f.voto_nominal||f.voto_nominal_senado),empuje:f.empuje_txt||null,
        veces:f.veces_presentado||null,n_firmantes:f.n_firmantes||null};
      sesSet('ficha:'+key,out); return out;
    });
  }
  /* fuerzas externas precalculadas por proyecto (build_fuerzas_externas.py) */
  function tokProyecto(x){ const c=x._cam==='Senado'?'S':'C'; const t=tokNum(c==='S'?(x.numero_senado||x.numero_camara):(x.numero_camara||x.numero_senado)); return t?`${c}-${t.replace('/','-')}`:null; }
  function externosDe(x){
    const t=tokProyecto(x); if(!t) return Promise.resolve(null);
    return memo('ext:'+t,async()=>{ try{ return await getJSON(FZ_BASE+'/fuerzas-externas/'+t+'.json',3600000); }catch(err){ return null; } });
  }
  /* titulares sobre el TEMA del proyecto: la prensa casi nunca cita el número,
     así que se busca por las palabras del título y se exige que el titular
     traiga al menos dos de ellas. No se clasifica postura. */
  const STOP=new Set('para sobre entre desde hasta cual cuales donde como contra mediante segun dictan otras disposiciones medio modifica modifican establece establecen crea crean ley leyes articulo articulos nacional republica colombia colombiano colombiana por del las los una uno que con sus mas adiciona adicionan reforma reforman regula regulan expide expiden fortalece promueve garantiza declara otorga autoriza incluye dicta normas'.split(' '));
  function palabrasTema(t){ return [...new Set(normT(shortTitle(t)).split(' ').filter(w=>w.length>4&&!STOP.has(w)))].slice(0,5); }
  async function prensaTema(x,dias){
    const P=palabrasTema(x.titulo); if(P.length<2) return {palabras:P,res:[]};
    const d=await api({action:'medios',query:P.slice(0,4).join(' '),dias:dias||60},30);
    const raiz=P.map(w=>w.slice(0,6));
    const res=((d&&d.resultados)||[]).filter(r=>{ const t=' '+normT(r.titulo)+' '; return raiz.filter(w=>t.includes(' '+w)).length>=2; });
    return {palabras:P,res,flexible:d&&d.flexible};
  }

  /* ── cabecera de identidad y barra de módulos ────────────────────── */
  function renderHead(el,e,opt){
    opt=opt||{}; const b=bancadaOf(e.partido);
    el.className='mc-head'+(opt.mini?' mini':'');
    el.innerHTML=`
      <div class="fc-photo" data-mc-photo style="background:${b.color}"><span>${esc(initials(e.nombre))}</span></div>
      <div style="min-width:0;flex:1">
        <div class="mc-name">${esc(nice(e.nombre))}</div>
        <div class="mc-meta"><b>${chamberNice(e.corp)}</b> · ${esc(depNice(e.dep))} · ${esc(e.partido)}</div>
        <div class="mc-chips"><span class="mc-chip b" style="color:${b.color}">${esc(b.name)}</span><span class="mc-chip" data-mc-com>Comisión: buscando…</span><span class="mc-chip" data-mc-votos style="display:none"></span></div>
        ${opt.extra||''}
      </div>
      ${opt.mini?`<a class="mc-change" href="mi-congreso.html?cambiar=1">Cambiar</a>`:`<button class="mc-change" type="button" data-mc-cambiar>Cambiar de congresista</button>`}`;
    comision(e).then(c=>{
      const chip=el.querySelector('[data-mc-com]'); if(!chip) return;
      chip.innerHTML=c.key?`${esc(c.nombre)}${c.mesa?` · <span class="mc-star">★ ${c.mesa.cargo==='presidencia'?'preside':'vicepresidencia'}</span>`:''}`:'Comisión: no figura en nuestro registro';
    }).catch(()=>{});
    /* la bancada es la OFICIAL (Senado y Cámara la publican), no la lista con
       la que se eligió: Villalba entró por «Ahora Colombia» y es Nuevo Liberalismo */
    internas().then(I=>{
      const o=oficialDe(I,e.nombre,e.corp==='SENADO'?'senado':'camara'); const chip=el.querySelector('.mc-chip.b'); if(!o||!chip) return;
      chip.textContent=o.b; chip.style.color=bancadaOf(o.p).color; chip.title=`Bancada oficial · se eligió por ${nice(e.partido)}`;
    }).catch(()=>{});
    electoral(e).then(r=>{
      if(!r.hit) return;
      const ch=el.querySelector('[data-mc-votos]'); if(ch&&r.hit.votos){ ch.style.display=''; ch.textContent=`${fmt(r.hit.votos)} votos en 2026`; }
      const ph=el.querySelector('[data-mc-photo]'); if(!ph) return;
      const img=new Image(); img.alt=nice(e.nombre); img.onload=()=>{ ph.innerHTML=''; ph.appendChild(img); }; img.src=r.foto;
    }).catch(()=>{});
  }
  function renderNav(cur){
    const bar=document.getElementById('mc-sec-bar'); if(!bar) return;
    bar.innerHTML=`<a class="sec-back" href="mi-congreso.html">← Mi Congreso</a><nav class="mc-nav">${MODULOS.filter(m=>!m.solo||ESCUCHA_ON||m.id===cur).map(m=>`<a href="${m.href}"${m.id===cur?' class="on"':''}>${esc(m.t)}</a>`).join('')}</nav>`;
  }
  /* arma una página de módulo: exige congresista, pinta cabecera y barra */
  function pagina(id){
    const e=requireMe(id); if(!e) return null;
    renderNav(id);
    const h=document.getElementById('mc-head'); if(h) renderHead(h,e,{mini:true});
    const m=MODULOS.find(x=>x.id===id); if(m) document.title=`${m.t} · ${nice(e.nombre)} · Mi Congreso`;
    /* la pestaña «En redes» entra a la barra solo si esta persona tiene lectura */
    if(!ESCUCHA_ON) escucha(e).then(d=>{ if(d) renderNav(id); });
    return e;
  }

  /* ── tooltip flotante (calendario, barras) ───────────────────────── */
  let TIP=null;
  function tip(html,ev){
    if(!TIP){ TIP=document.createElement('div'); TIP.className='mc-tip'; document.body.appendChild(TIP); }
    if(!html){ TIP.classList.remove('on'); return; }
    TIP.innerHTML=html; TIP.classList.add('on');
    const w=TIP.offsetWidth, h=TIP.offsetHeight;
    let x=ev.clientX+14, y=ev.clientY+14;
    if(x+w>innerWidth-8) x=ev.clientX-w-14;
    if(y+h>innerHeight-8) y=Math.max(8,ev.clientY-h-14);
    TIP.style.left=x+'px'; TIP.style.top=y+'px';
  }
  function tipOn(el,htmlFn){
    el.addEventListener('mousemove',ev=>tip(htmlFn(),ev));
    el.addEventListener('mouseleave',()=>tip(null));
  }

  /* ── calendario de sesiones ──────────────────────────────────────────
     Por día: las órdenes del día publicadas, marcando las de mi comisión o
     plenaria y las que traen proyectos míos. Lo demás del Congreso también
     sale (en gris): un día sin nada mío puede tener una sesión que me toca. */
  function porDia(ord,e,comKey,misProy){
    const mios=new Set(); (misProy||[]).forEach(x=>(x._citas||[]).forEach(c=>mios.add(c.o.id||c.o.url)));
    const D={};
    ord.forEach(o=>{
      let f=o.fecha; const fin=o.fecha_fin||o.fecha;
      for(let i=0;i<10&&f<=fin;i++){
        (D[f]=D[f]||[]).push({o,mia:esMia(o,e,comKey),conMio:mios.has(o.id||o.url)});
        const d=dia(f); d.setDate(d.getDate()+1); f=iso(d);
      }
    });
    return D;
  }
  function tipDia(f,lista,misProy){
    const s=lista.slice().sort((a,b)=>(b.conMio-a.conMio)||(b.mia-a.mia));
    const misNums=new Map(); (misProy||[]).forEach(x=>(x._citas||[]).forEach(c=>misNums.set((c.o.id||c.o.url)+'#'+c.pos,x)));
    return `<h5>${esc(diaCorto(f))} · ${s.length} sesi${s.length===1?'ón':'ones'}</h5>`+s.map(r=>{
      const ps=(r.o.proyectos||[]).filter(p=>p.titulo);
      const mis=ps.map((p,i)=>misNums.get((r.o.id||r.o.url)+'#'+(i+1))).filter(Boolean);
      return `<div class="s"><b>${esc(ambitoNice(r.o.ambito||r.o.corporacion))}</b>${/plenaria/i.test(r.o.ambito||'')?'':' · '+esc(r.o.corporacion||'')}${r.mia?' · <span class="mine">tu agenda</span>':''}${mis.length?` · <span class="mine">★ ${mis.length} tuyo${mis.length===1?'':'s'}</span>`:''}
        ${ps.length?`<ul>${ps.slice(0,4).map(p=>`<li>${esc(cut(shortTitle(p.titulo),78))}</li>`).join('')}${ps.length>4?`<li>y ${ps.length-4} más</li>`:''}</ul>`:(r.o.pdf_error?'<div style="opacity:.7">Documento sin leer (escaneo): revisa el original.</div>':'<div style="opacity:.7">Sin proyectos listados (control político o proposiciones).</div>')}</div>`;
    }).join('');
  }
  /* semanas completas (lun-dom) desde el lunes de esta semana */
  function calendario(el,{ord,e,comKey,misProy,semanas,compacto,onDia}){
    const hoy=hoyBog(), D=porDia(ord,e,comKey,misProy);
    const ini=dia(hoy); ini.setDate(ini.getDate()-((ini.getDay()+6)%7));
    let html=['lun','mar','mié','jue','vie','sáb','dom'].map(d=>`<div class="dw">${d}</div>`).join('');
    const cells=[];
    for(let i=0;i<7*(semanas||2);i++){
      const d=new Date(ini); d.setDate(ini.getDate()+i); const f=iso(d);
      const L=D[f]||[]; const mia=L.some(r=>r.mia), con=L.some(r=>r.conMio);
      const cls=['mc-day']; if(f<hoy) cls.push('past'); if(f===hoy) cls.push('hoy'); if(L.length) cls.push('has'); if(con) cls.push('mine'); else if(mia) cls.push('mia'); if(!enSesion(f)) cls.push('receso');
      const dots=L.map(r=>`<i class="${r.conMio?'c':(r.mia?'':'o')}"></i>`).join('');
      const nm=L.filter(r=>r.mia||r.conMio).length;
      html+=`<div class="${cls.join(' ')}" data-f="${f}"><span class="n">${d.getDate()}</span>${d.getDate()===1||i===0?`<span class="m">${MES[d.getMonth()]}</span>`:''}${L.length?`<div class="mc-dots">${dots}</div>`:''}${!compacto&&L.length?`<span class="cnt">${nm?`${nm} tuya${nm===1?'':'s'} · `:''}${L.length} en total</span>`:''}</div>`;
      cells.push(f);
    }
    el.innerHTML=`<div class="mc-cal">${html}</div>`;
    el.querySelectorAll('.mc-day.has').forEach(c=>{
      const f=c.dataset.f; tipOn(c,()=>tipDia(f,D[f],misProy));
      if(onDia) c.addEventListener('click',ev=>{ ev.preventDefault(); ev.stopPropagation(); tip(null); onDia(f); });
    });
    return D;
  }

  /* ── pequeños gráficos ───────────────────────────────────────────── */
  function ring(p,size){
    size=size||92; const r=size/2-7, c=2*Math.PI*r;
    return `<svg class="mc-ring" viewBox="0 0 ${size} ${size}" style="width:${size}px;height:${size}px"><circle class="bg" cx="${size/2}" cy="${size/2}" r="${r}"/><circle class="fg" cx="${size/2}" cy="${size/2}" r="${r}" stroke-dasharray="${c}" stroke-dashoffset="${c*(1-p/100)}"/><text x="50%" y="50%">${p}%</text></svg>`;
  }
  function spark(serie,h){
    h=h||46; const n=serie.length, mx=Math.max(1,...serie), w=300;
    const pts=serie.map((v,i)=>`${(i/(n-1||1))*w},${h-2-(v/mx)*(h-6)}`).join(' ');
    return `<svg class="mc-spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><polyline points="0,${h} ${pts} ${w},${h}" fill="rgba(0,71,255,.1)" stroke="none"/><polyline points="${pts}" fill="none" stroke="#0047FF" stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>`;
  }
  const hbar=(l,v,max,o)=>{ o=o||{}; return `<div class="mc-hbar${o.me?' me':''}${o.cls?' '+o.cls:''}"${o.attr||''}><span class="l" title="${esc(l)}">${esc(l)}</span><span class="b"><i style="width:${max?100*v/max:0}%"></i></span><span class="v">${o.txt!=null?o.txt:fmt(v)}</span></div>`; };

  window.MC={S3,URL_COM,URL_ORD,KEY,MODULOS,LEG,ETAPAS,TIPO_NICE,BANC_CAUDAL,
    initials,mismaPersona,fechaCorta,fechaLarga,diaCorto,hoyBog,iso,dia,shortTitle,chamberNice,comisionNice,nombreCom,ambitoNice,cut,nice,corto,pct,
    me,guardar,olvidar,requireMe,getJSON,api,comision,ordenes,esMia,etapaDe,etapaEf,numKey,citasDe,numDe,citaTxt,avanceHtml,tipoDe,
    escucha,escuchaSlug,mios,avanceGeneral,indiceElectoral,enSesion,diasHabSesion,diasCal,legislatura,relojDe,puntaje,electoral,fotoDe,voto,prensa,citPanorama,bancadasDisc,bloqueo,stats,
    renderHead,renderNav,pagina,tip,tipOn,porDia,tipDia,calendario,ring,spark,hbar,
    FZ_CAT,FZ_AFIN,FZ_BISAGRA,COM_KEYS,comKeyDe,internas,oficialDe,bancadaDe,coincidencia,fuerzas,hemiciclo,tipSilla,fichaDe,tokNum,palabrasTema,prensaTema,radicadosTodos,proyectoDe,tokProyecto,externosDe};
})();
