/* Base compartida del Legislativo: cursor, helpers, modal, sesión.
   La cargan el hub y las 6 páginas de sección. Lo específico de cada
   sección vive inline en su propio HTML. */
(function(){
  /* ── cursor ─────────────────────────────────────────────────── */
  const cur=document.getElementById('cursor'), ri=document.getElementById('cursorRing');
  let mx=0,my=0,rx=0,ry=0;
  document.addEventListener('mousemove',e=>{mx=e.clientX;my=e.clientY;cur.style.left=mx+'px';cur.style.top=my+'px';});
  (function loop(){rx+=(mx-rx)*.1;ry+=(my-ry)*.1;ri.style.left=rx+'px';ri.style.top=ry+'px';requestAnimationFrame(loop);})();
  document.addEventListener('mouseover',e=>{
    if(e.target.closest('a,button,select,input,.com-card,.kpi.hasinfo,.r-row,.ev-row,.pt-card')){cur.style.transform='translate(-50%,-50%) scale(2)';cur.style.background='transparent';cur.style.border='1.5px solid var(--blue)';ri.style.opacity='0';}
    else{cur.style.transform='translate(-50%,-50%) scale(1)';cur.style.background='var(--blue)';cur.style.border='none';ri.style.opacity='.35';}
  });
  const esc=s=>String(s==null?'':s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
  const fmt=n=>String(n==null?'—':n).replace(/\B(?=(\d{3})+(?!\d))/g,'.');
  const tCase=s=>String(s||'').toLowerCase().replace(/(^|[ .\-'])(\p{L})/gu,(m,sep,ch)=>sep+ch.toUpperCase());
  const depNice=s=>s==='BOGOTA D.C.'?'Bogotá D.C.':s==='NACIONAL'?'Nacional':s.charAt(0)+s.slice(1).toLowerCase().replace(/([ .])(\w)/g,(m,sep,c)=>sep+c.toUpperCase());
  const norm=s=>String(s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();
  /* la paleta del escrutinio trae azules muy oscuros (Conservador #003580):
     como TEXTO sobre fondo oscuro se aclaran; como relleno van plenos */
  function lift(hex){
    let r=parseInt(hex.slice(1,3),16),g=parseInt(hex.slice(3,5),16),b=parseInt(hex.slice(5,7),16);
    if((0.299*r+0.587*g+0.114*b)>=90) return hex;
    const up=v=>Math.round(v+(255-v)*0.5).toString(16).padStart(2,'0');
    return '#'+up(r)+up(g)+up(b);
  }
  const API='https://l3kmprdjkl.execute-api.us-east-1.amazonaws.com';
  async function call(payload){
    const r=await fetch(API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    return r.json();
  }
  /* ── modal compartido ────────────────────────────────────────── */
  function openModal(html){
    document.getElementById('md-body').innerHTML=html;
    document.getElementById('md-back').classList.add('on');
    document.getElementById('md-box').classList.add('on');
    document.getElementById('md-box').scrollTop=0;
    document.body.style.overflow='hidden';
  }
  function closeModal(){
    document.getElementById('md-back').classList.remove('on');
    document.getElementById('md-box').classList.remove('on');
    document.body.style.overflow='';
    /* reset del cursor custom: el elemento sobre el que se hizo clic se va del
       DOM sin disparar mouseout y deja el puntero con los estilos de hover */
    const c=document.getElementById('cursor'), r=document.getElementById('cursorRing');
    if(c){ c.style.transform='translate(-50%,-50%) scale(1)'; c.style.background='var(--blue)'; c.style.border='none'; }
    if(r){ r.style.opacity='.35'; }
  }
  document.addEventListener('keydown',e=>{ if(e.key==='Escape') closeModal(); });
  /* ── chip de instalación (cuenta regresiva / en funciones) ──── */
  (function(){
    const el=document.getElementById('instala-txt');
    if(!el) return;      // el chip solo existe en el hub; sin la guarda, este
                         // IIFE tumbaba todo base.js en las páginas de sección
    const dias=Math.ceil((new Date('2026-07-20T00:00:00-05:00')-new Date())/(1000*60*60*24));
    if(dias>1) el.textContent=`Instalación · 20 de julio de 2026 · faltan ${dias} días`;
    else if(dias===1) el.textContent='Instalación · 20 de julio de 2026 · mañana';
    else if(dias===0) el.textContent='Instalación · hoy · 20 de julio de 2026';
    else el.textContent='Congreso 2026-2030 · en funciones desde el 20 de julio';
  })();
  /* ── SESSION NAV (chip de plan / login-registro) ────────────── */
  function updateNavAuth(){
    const token=localStorage.getItem('rr-token');
    const user=JSON.parse(localStorage.getItem('rr-user')||'null');
    const area=document.getElementById('nav-auth-area');
    if(!area) return;
    const lang=localStorage.getItem('rr-lang')||'co';
    const T={
      co:{login:'Iniciar sesión',register:'Registrarse',profile:'Mi panel',logout:'Salir'},
      us:{login:'Log in',register:'Sign up',profile:'My dashboard',logout:'Log out'},
      cn:{login:'登录',register:'注册',profile:'我的面板',logout:'退出'},
      br:{login:'Entrar',register:'Cadastrar',profile:'Meu painel',logout:'Sair'},
    }[lang]||{login:'Iniciar sesión',register:'Registrarse',profile:'Mi panel',logout:'Salir'};
    if(token&&user){
      const planLabels={free:'Free',pro:'Pro',premium:'Premium',basic:'Básico',analysis:'Análisis',full:'Completo'};
      area.dataset.loggedIn='1';
      area.innerHTML=`<span class="e-user-plan">${planLabels[user.plan]||user.plan}</span>
        <a href="dashboard.html" class="e-btn-profile">${T.profile}</a>
        <button class="e-btn-logout" onclick="logOutPage()">${T.logout}</button>`;
    }else{
      delete area.dataset.loggedIn;
      area.innerHTML=`<a href="login.html" class="e-btn-login">${T.login}</a>
        <a href="elige-plan.html" class="e-btn-register">${T.register}</a>`;
    }
  }
  async function logOutPage(){
    const token=localStorage.getItem('rr-token');
    if(token){ try{ await fetch('https://rr-auth.reruizc.workers.dev/auth/logout',{method:'POST',headers:{'Authorization':`Bearer ${token}`}}); }catch(e){} }
    localStorage.removeItem('rr-token'); localStorage.removeItem('rr-user');
    window.location.reload();
  }

  /* se exponen al ámbito global: los onclick del HTML y los scripts
     inline de cada sección los llaman por nombre */
  Object.assign(window,{esc,fmt,norm,tCase,depNice,lift,call,openModal,closeModal,updateNavAuth,logOutPage});
  updateNavAuth();
})();
