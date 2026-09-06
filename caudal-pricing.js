/* Acceso institucional de Caudal: contrato de checkout conservado. */
(function(){
'use strict';
    // ─── ACCESO · compra del SKU de Caudal ────────────────────────────────────
    // El precio y el link de Wompi salen del worker (GET /caudal/planes), que los
    // lee de sus secretos: así rotar un link es cambiar UN secreto y no dos
    // archivos. Sin link configurado el botón pide acceso por correo, nunca
    // manda a un checkout roto.
    const RR_AUTH='https://rr-auth.reruizc.workers.dev';
    const ACC_MAIL='mailto:hola@ricardoruiz.co?subject='+encodeURIComponent('Caudal · acceso')+'&body='+encodeURIComponent('Hola,\n\nQuiero acceso a Caudal.\n\nOrganización:\nSector:\nCorreo de la cuenta:\n');
    let PLANES=null;
    const fmtCOP=n=>'$'+Number(n).toLocaleString('es-CO');
    async function cargarPlanes(){
      try{ const r=await fetch(RR_AUTH+'/caudal/planes',{signal:AbortSignal.timeout(12000)}); const d=await r.json(); if(d&&d.ok) PLANES=d; }catch(e){ PLANES=null; }
      pintarAcceso();
    }
    function pintarAcceso(){
      const p=document.getElementById('acc-precio'), e=document.getElementById('acc-estado'), b=document.getElementById('acc-comprar');
      if(!p||!e||!b) return;
      b.disabled=false;
      const link=PLANES&&PLANES.links&&PLANES.links.mensual;
      /* ⚠️ El precio del worker manda SOLO cuando hay checkout configurado. El
         worker se despliega aparte de esta página, así que mientras no exista
         el link su cifra puede ir atrasada y pisaría el precio vigente sin dar
         ningún error —fue justo lo que pasó al subir la tarifa. Con link, la
         cifra que se muestra tiene que ser la que se va a cobrar. */
      if(link&&PLANES.precio&&PLANES.precio.mensual) p.innerHTML=fmtCOP(PLANES.precio.mensual)+'<small>COP / mes</small>';
      if(link){ e.textContent='Pago seguro con Wompi · activación inmediata'; b.textContent='Conseguir acceso'; }
      else { e.textContent='Solicita tu acceso por correo'; b.textContent='Solicitar acceso'; }
    }
    function comprarCaudal(ciclo){
      const link=PLANES&&PLANES.links&&PLANES.links[ciclo];
      if(!link){ location.href=ACC_MAIL; return; }
      const token=localStorage.getItem('rr-token');
      let user=null; try{ user=JSON.parse(localStorage.getItem('rr-user')||'null'); }catch(e){}
      if(!token||!user||!user.email){
        // el webhook activa por correo de la cuenta: sin cuenta no hay a quién activar
        location.href='register.html?next='+encodeURIComponent('caudal-pricing.html?comprar=1'); return;
      }
      localStorage.setItem('rr-pending-plan', JSON.stringify({planId:'caudal_'+ciclo, planName:'Caudal', billing:ciclo}));
      // mismo contrato que pricing.html: customer-email pre-rellena el checkout y
      // llega en el webhook; reference es el respaldo si ese campo viene vacío.
      const params=new URLSearchParams({'customer-email':user.email,'reference':`rr-${user.email}-caudal-${ciclo}-${Date.now()}`});
      location.href=link+'?'+params.toString();
    }
    window.comprarCaudal=comprarCaudal;
    cargarPlanes();
    // ?comprar=1 = viene del muro de Caudal o de vuelta del registro: aterriza en el bloque
    if(new URLSearchParams(location.search).get('comprar')==='1'){
      setTimeout(()=>{ const s=document.getElementById('acceso'); if(s) s.scrollIntoView({behavior:'instant',block:'start'}); },50);
    }


})();
