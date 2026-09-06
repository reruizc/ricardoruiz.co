/* Cabecera compartida de las páginas públicas de Caudal. */
(function(){
'use strict';
    // ─── SESIÓN / AUTH (misma lógica de index.html) ───────────────────────────
    let currentLang = localStorage.getItem('rr-lang') || 'co';
    function updateNavAuth(){
      const token=localStorage.getItem('rr-token');
      let user=null; try{user=JSON.parse(localStorage.getItem('rr-user')||'null');}catch(e){}
      const area=document.getElementById('nav-auth-area');
      if(!area) return;
      if(token && user){
        const planLabels = currentLang==='us' ? {free:'Free',basic:'Basic',analysis:'Analysis',full:'Full',pro:'Pro',premium:'Premium'}
          : currentLang==='cn' ? {free:'免费',basic:'基础版',analysis:'分析版',full:'完整版',pro:'Pro',premium:'Premium'}
          : currentLang==='br' ? {free:'Free',basic:'Básico',analysis:'Análise',full:'Completo',pro:'Pro',premium:'Premium'}
          : {free:'Free',basic:'Básico',analysis:'Análisis',full:'Completo',pro:'Pro',premium:'Premium'};
        const perfilLabel = currentLang==='us'?'My dashboard':currentLang==='cn'?'我的面板':currentLang==='br'?'Meu painel':'Mi panel';
        const logoutLabel = currentLang==='us'?'Log out':currentLang==='cn'?'退出':currentLang==='br'?'Sair':'Salir';
        area.dataset.loggedIn='1';
        area.innerHTML=`
          <a href="dashboard.html" class="e-btn-profile">${perfilLabel}</a>
          <button class="e-btn-logout" onclick="logOut()">${logoutLabel}</button>`;
      } else {
        delete area.dataset.loggedIn;
        const loginLabel = currentLang==='us'?'Log in':currentLang==='cn'?'登录':currentLang==='br'?'Entrar':'Iniciar sesión';
        const registerLabel = currentLang==='us'?'Sign up':currentLang==='cn'?'注册':currentLang==='br'?'Cadastrar':'Registrarme';
        area.innerHTML=`
          <a href="login.html?next=caudal.html" class="e-btn-login">${loginLabel}</a>`;
      }
    }
    async function logOut(){
      const token=localStorage.getItem('rr-token');
      if(token){ try{ await fetch('https://rr-auth.reruizc.workers.dev/auth/logout',{method:'POST',headers:{'Authorization':`Bearer ${token}`}}); }catch(e){} }
      localStorage.removeItem('rr-token'); localStorage.removeItem('rr-user'); updateNavAuth();
    }
    window.logOut = logOut;
    window.__applyLang = function(lang){ currentLang=lang; localStorage.setItem('rr-lang',lang); updateNavAuth(); };
    updateNavAuth();

})();
