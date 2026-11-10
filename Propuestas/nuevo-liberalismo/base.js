/* Nuevo Liberalismo · rumbo a 2027 — utilidades compartidas (script clásico, sin módulos).
   Expone window.NL. No redeclarar estos nombres en las páginas. */
(function(){
  const MODULOS = [
    {id:'inventario', href:'inventario.html', n:'01', t:'El inventario'},
    {id:'tablero',    href:'tablero.html',    n:'02', t:'El análisis'},
    {id:'clima',      href:'clima.html',      n:'03', t:'Dónde estamos'},
    {id:'escenarios', href:'escenarios.html', n:'04', t:'Reglas y escenarios'},
    {id:'estrategia', href:'estrategia.html', n:'05', t:'La estrategia'}
  ];

  /* Color por ENTIDAD (nunca por puesto en el ranking). El rojo vivo queda reservado
     para el Nuevo Liberalismo y su vehículo electoral; el Liberal va en ladrillo. */
  const PARTIDOS = {
    nl:        {n:'Nuevo Liberalismo',            c:'#f0392d'},
    ahora:     {n:'Ahora Colombia',               c:'#f0392d'},
    mira:      {n:'MIRA',                         c:'#3f6fd8'},
    dignidad:  {n:'Dignidad y Compromiso',        c:'#e0b030'},
    miradig:   {n:'MIRA + Dignidad',              c:'#e0b030'},
    pacto:     {n:'Pacto Histórico',              c:'#8d6bd6'},
    cd:        {n:'Centro Democrático',           c:'#2f9be6'},
    liberal:   {n:'Partido Liberal',              c:'#d99a6c'},
    verde:     {n:'Alianza Verde',                c:'#2fa84f'},
    alianza:   {n:'Alianza por Colombia',         c:'#2fa84f'},
    conservador:{n:'Partido Conservador',         c:'#4f74d6'},
    u:         {n:'Partido de la U',              c:'#f08c1a'},
    cr:        {n:'Cambio Radical',               c:'#d6457e'},
    salvacion: {n:'Salvación Nacional',           c:'#1fb5ad'},
    frente:    {n:'Frente Amplio Unitario',       c:'#b89cf0'},
    asi:       {n:'ASI',                          c:'#7fb8a4'},
    mais:      {n:'MAIS',                         c:'#c98b5a'},
    aico:      {n:'AICO',                         c:'#a7b25c'},
    polo:      {n:'Polo Democrático',             c:'#d9c341'},
    ch:        {n:'Colombia Humana',              c:'#a886e8'},
    up:        {n:'Unión Patriótica',             c:'#c9a227'},
    comunes:   {n:'Comunes',                      c:'#c06c84'},
    marcha:    {n:'En Marcha',                    c:'#e07a5f'},
    creemos:   {n:'Creemos',                      c:'#5aa9c9'},
    liga:      {n:'Liga de Gobernantes',          c:'#d08c60'},
    renaciente:{n:'Colombia Renaciente',          c:'#9a8fbf'},
    justa:     {n:'Colombia Justa Libres',        c:'#6f9fd8'},
    fuerza:    {n:'Fuerza Ciudadana',             c:'#e08e45'},
    otros:     {n:'Otros',                        c:'#7a7f8c'},
    blanco:    {n:'Blanco, nulos y no marcados',  c:'#b9bcc6'},
    novoto:    {n:'No votó',                      c:'#3a3f4d'},
    /* presidencial 2026 */
    cepeda:    {n:'Cepeda',                       c:'#8d6bd6'},
    abelardo:  {n:'De la Espriella',              c:'#2f55d9'},
    paloma:    {n:'Paloma Valencia',              c:'#2f9be6'},
    fajardo:   {n:'Fajardo',                      c:'#eeaa22'},
    otrosp:    {n:'Otros candidatos',             c:'#7a7f8c'}
  };

  const nf = new Intl.NumberFormat('es-CO');
  const fmt  = v => (v==null||isNaN(v)) ? '—' : nf.format(Math.round(v));
  const pct  = (v,d=1) => (v==null||isNaN(v)) ? '—' : (v*100).toFixed(d).replace('.',',')+'%';
  const pct0 = v => pct(v,0);
  const mil  = v => { if(v==null||isNaN(v)) return '—'; const a=Math.abs(v);
    if(a>=1e6) return (v/1e6).toFixed(a>=1e7?1:2).replace('.',',')+' M';
    if(a>=1e4) return Math.round(v/1e3)+' mil'; return fmt(v); };
  const esc  = s => String(s==null?'':s).replace(/[&<>"']/g, m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const norm = s => String(s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toUpperCase().replace(/[^A-Z0-9 ]+/g,' ').replace(/\s+/g,' ').trim();
  const tCase = s => String(s||'').toLowerCase().replace(/(^|[\s\-\(])([a-záéíóúñ])/g,(m,a,b)=>a+b.toUpperCase())
                     .replace(/\b(De|Del|La|Las|Los|Y|El)\b/g,m=>m.toLowerCase()).replace(/^./,m=>m.toUpperCase());
  const J = async (url) => { const r = await fetch(url, {cache:'no-cache'}); if(!r.ok) throw new Error(url+' → '+r.status); return r.json(); };

  /* datos: primero el .js (funciona con file://), si no existe cae al .json (servidor) */
  const _carga = {};
  const DATOS_V = '20261110i';   /* subirlo cada vez que se regeneren los datos */
  function dato(n){
    if(window.NLD && window.NLD[n]) return Promise.resolve(window.NLD[n]);
    if(_carga[n]) return _carga[n];
    return _carga[n] = new Promise((ok, mal)=>{
      /* ?v= para que el navegador no sirva una copia vieja de los datos tras regenerarlos */
      const s=document.createElement('script'); s.src='datos/'+n+'.js?v='+DATOS_V;
      s.onload=()=> window.NLD && window.NLD[n] ? ok(window.NLD[n]) : mal(new Error('sin datos '+n));
      s.onerror=()=> J('datos/'+n+'.json').catch(()=>J('datos/'+n+'.geojson')).then(ok, mal);
      document.head.appendChild(s);
    });
  }

  /* ── tooltip único ── */
  let tipEl=null;
  function tip(html, ev){
    if(!tipEl){ tipEl=document.createElement('div'); tipEl.className='tip'; document.body.appendChild(tipEl); }
    if(html==null){ tipEl.style.display='none'; return; }
    tipEl.innerHTML=html; tipEl.style.display='block';
    const pad=14, w=tipEl.offsetWidth, h=tipEl.offsetHeight;
    let x=ev.clientX+pad, y=ev.clientY+pad;
    if(x+w>innerWidth-8) x=ev.clientX-w-pad;
    if(y+h>innerHeight-8) y=ev.clientY-h-pad;
    tipEl.style.left=Math.max(6,x)+'px'; tipEl.style.top=Math.max(6,y)+'px';
  }

  /* ── logo Ricardo.Ruiz (idéntico al del sitio) ── */
  const LOGO = `<a href="https://ricardoruiz.co" class="logo-link" aria-label="Ricardo.Ruiz"><span class="logo-bars">
      <i class="logo-bar" style="height:20px"></i><i class="logo-bar" style="height:15px"></i><i class="logo-bar" style="height:9px"></i><i class="logo-bar" style="height:4px"></i></span>
      <span class="logo-text">Ricardo<span>.</span>Ruiz</span></a>`;

  /* ── ámbito: General · Bogotá · Resto del país ──
     Se guarda en localStorage (así acompaña al pasar de módulo) y en ?ambito= (así un enlace abre la vista).
     Pone data-ambito en <html>: un elemento con data-en="bogota resto" solo se ve en esos ámbitos (lo hace base.css).
     Las páginas escuchan el cambio con NL.alCambiarAmbito(fn) o el evento 'nl:ambito'. */
  const AMBITOS = [['general','General'],['bogota','Bogotá'],['resto','Resto del país']];
  const esAmb = v => AMBITOS.some(a=>a[0]===v);
  function ambito(){
    const u = new URLSearchParams(location.search).get('ambito'); if(esAmb(u)) return u;
    try{ const v=localStorage.getItem('nl-ambito'); if(esAmb(v)) return v; }catch(e){}
    return 'general';
  }
  function pintaAmbito(v){
    document.documentElement.dataset.ambito = v;
    document.querySelectorAll('.nl-ambito button').forEach(b=>{ const on=b.dataset.a===v; b.classList.toggle('on',on); b.setAttribute('aria-pressed',on); });
  }
  function setAmbito(v){
    if(!esAmb(v)) return;
    try{ localStorage.setItem('nl-ambito', v); }catch(e){}
    try{ const u=new URL(location.href); if(v==='general') u.searchParams.delete('ambito'); else u.searchParams.set('ambito', v); history.replaceState(null,'',u); }catch(e){}
    pintaAmbito(v);
    dispatchEvent(new CustomEvent('nl:ambito', {detail:v}));
  }
  const alCambiarAmbito = fn => addEventListener('nl:ambito', e=>fn(e.detail));
  pintaAmbito(ambito());   // antes de pintar nada, para que el CSS ya oculte lo que no toca

  /* ── cinta + barra superior + pie con anterior/siguiente ── */
  function nav(actual){
    const el=document.getElementById('nl-nav'); if(!el) return;
    const frase='¡Siempre adelante! ¡Ni un paso atrás!', una=`<span>${frase}</span><span>Nuevo Liberalismo · rumbo a 2027</span>`;
    const cinta=document.createElement('div'); cinta.className='nl-cinta'; cinta.setAttribute('aria-hidden','true');
    cinta.innerHTML=`<div class="pista">${una.repeat(8)}</div>`;
    el.parentNode.insertBefore(cinta, el);
    el.className='nl-nav';
    el.innerHTML = `${actual==='inicio'?'':'<a class="back" href="index.html">← Inicio</a>'}
      <span class="nl-marca"><b>Nuevo Liberalismo</b> · rumbo a 2027</span>
      <span class="mods">${MODULOS.map(m=>`<a href="${m.href}" class="${m.id===actual?'on':''}">${m.n} ${m.t}</a>`).join('')}</span>${LOGO}`;
    if(actual!=='inicio'){
      const bar=document.createElement('div'); bar.className='nl-ambito-bar';
      bar.innerHTML=`<span class="lbl">Ver</span><span class="nl-ambito" role="group" aria-label="Ámbito">${AMBITOS.map(([k,t])=>`<button type="button" data-a="${k}">${t}</button>`).join('')}</span>`;
      el.appendChild(bar);
      bar.addEventListener('click', e=>{ const b=e.target.closest('button'); if(b) setAmbito(b.dataset.a); });
      pintaAmbito(ambito());
    }
    const pie=document.querySelector('footer.pie');
    if(pie && !pie.querySelector('.logo-link')){ const f=document.createElement('div'); f.className='pie-firma'; f.innerHTML='<span>Análisis y diseño</span>'+LOGO; pie.appendChild(f); }
    const p=document.getElementById('nl-pasos'); if(!p) return;
    const i=MODULOS.findIndex(m=>m.id===actual);
    const a=MODULOS[i-1], s=MODULOS[i+1];
    p.className='pasos';
    p.innerHTML = (a?`<a href="${a.href}">← ${a.n} ${a.t}</a>`:`<a href="index.html">← Inicio</a>`) +
                  (s?`<a href="${s.href}">${s.n} ${s.t} →</a>`:`<a href="index.html">Volver al inicio →</a>`);
    /* flechas del teclado para pasar de módulo (útil al proyectar) */
    document.addEventListener('keydown', e=>{
      if(e.target && /INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) return;
      if(e.altKey && e.key==='ArrowRight' && s) location.href=s.href;
      if(e.altKey && e.key==='ArrowLeft') location.href = a ? a.href : 'index.html';
    });
  }

  window.NL = {dato, LOGO, MODULOS, PARTIDOS, fmt, pct, pct0, mil, esc, norm, tCase, J, tip, nav,
               AMBITOS, ambito, setAmbito, alCambiarAmbito,
               color:k=>(PARTIDOS[k]||PARTIDOS.otros).c, nombre:k=>(PARTIDOS[k]||{n:k}).n};
})();
