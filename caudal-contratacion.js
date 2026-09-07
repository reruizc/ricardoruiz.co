/* caudal-contratacion.js — el pilar de Datos abiertos y contratación (SECOP II)
   ------------------------------------------------------------------
   Vivía dentro de caudal-pilares.js, junto a otros cinco pilares. Salió
   a su propio archivo y a su propia página (caudal-contratacion.html,
   sep-2026) por dos razones: es el pilar que más se consulta suelto —un
   gremio llega con un radicado en la mano, no con un tema— y era el más
   caro de editar dentro de un archivo de 1.219 líneas.

   ⚠️ Este archivo se carga en DOS páginas y no son intercambiables:
     · caudal-contratacion.html — la página del pilar: hero, guía de
       búsqueda, gráficos y resultados. Ahí existen `con-rail`,
       `con-landing` y `con-results`.
     · caudal.html — SOLO para la búsqueda universal, que necesita
       `conCard` y `CON` para pintar su pestaña de contratación. Allá no
       existe ningún `con-*`, así que todo lo que toca el DOM sale por la
       guarda de elemento faltante. NO agregar aquí nada que asuma que la
       página del pilar está montada.

   Depende de caudal-comun.js (esc · fmt · fmtCOP · listaConMuro ·
   empresaHint) y de caudal-base.js (call · showView). Los dos van ANTES
   en el orden de <script>.

   ⚠️ Al tocarlo hay que bumpear su ?v= en las dos páginas, o el
   navegador sirve la copia vieja sin dar ningún error. */
(function(){
  'use strict';

  /* ---------- pilar Datos abiertos y contratación · SECOP II ---------- */
  const CON={q:'', filtros:{}, solo:false, orden:'reciente', tab:'contratos', _last:null};
  const CON_EJEMPLOS=['interventoría vías','dotación hospitalaria','alimentación escolar','carrotanques','comando conjunto caribe'];
  let CON_STATS=null, _conInited=false, _conSeq=0;
  // `true` solo en caudal-contratacion.html: es lo que distingue «la página
  // del pilar» de «caudal.html me cargó para pintar una tarjeta».
  let _conPagina=false;
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
  function conTabs(d,tot){
    const p=d.procesos;
    // sin procesos no hay pestaña que ofrecer: una pestaña vacía es ruido
    if(!p&&!d.procesos_tarde) return '';
    // el mismo universo que el titular: si la pestaña dijera 50 y el titular
    // 5.169.034, una de las dos estaría mintiendo.
    const nC=(tot&&tot.contratos)!=null?tot.contratos:(d.n||0);
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
    /* Todos los filtros, no cuatro. Al agregar las barras de modalidad, tipo,
       estado y orden, filtrar por cualquiera de ellas dejaba el subtítulo en
       «toda la contratación» — que con 50 de 5,1 millones de prestaciones de
       servicio en pantalla es sencillamente falso. */
    const scope=[d.query?`«${esc(d.query)}»`:''].concat(
      FILTRO_ORDEN.filter(k=>f[k]).map(k=>esc(String(f[k])))).filter(Boolean).join(' · ');
    const tot=d.total||conTotalConocido(f);
    // ② Si el radicado se encontró pero el universo $q está vacío (el caso
    // PAF-MENIES: el contrato solo existe como proceso), el titular NO puede
    // gritar «0 contratos» encima de un hallazgo real — es la misma lectura
    // equivocada que este camino existe para evitar.
    const _ix=d.identificador, _n=w=>fmt(w);
    const identSolo=_ix&&(!tot||!tot.contratos);
    const titular=identSolo
      ? [_ix.n_contratos?`${_n(_ix.n_contratos)} ${_ix.n_contratos===1?'contrato':'contratos'}`:'',
         _ix.n_procesos?`${_n(_ix.n_procesos)} ${_ix.n_procesos===1?'proceso':'procesos'}`:''].filter(Boolean).join(' · ')
      : (tot?`${fmt(tot.contratos)} ${tot.contratos===1?'contrato':'contratos'}`
            /* Sin universo conocido NO se anuncia uno: `d.n` es el tamaño de
               página (50), y publicarlo pelado convertía «5,1 millones de
               contratos de prestación de servicios» en «50 contratos». */
            : `Mostrando ${fmt(d.n)} ${d.n===1?'contrato':'contratos'}`);
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
      ${conTabs(d,tot)}
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
  /* Orden en que se nombran los filtros en el subtítulo, y de dónde sale el
     universo de cada uno. La Lambda no devuelve `total` cuando la consulta no
     trae texto libre (solo filtros) — pero para estas ocho dimensiones el dato
     exacto ya está en los agregados que pintaron las barras, así que no hace
     falta una consulta más: se lee de ahí. */
  const FILTRO_DIM={
    entidad:      ['top_entidades_n','entidad'],
    sector:       ['por_sector','sector'],
    departamento: ['por_departamento','departamento'],
    anio:         ['por_anio','anio'],
    modalidad:    ['por_modalidad','modalidad'],
    tipo:         ['por_tipo','tipo'],
    estado:       ['por_estado','estado'],
    orden_entidad:['por_orden','orden'],
  };
  const FILTRO_ORDEN=['entidad','sector','departamento','modalidad','tipo','estado','orden_entidad','anio','nit'];
  function conTotalConocido(f){
    const ks=Object.keys(f||{}); if(ks.length!==1) return null;   // combinados no se pueden sumar
    const dim=FILTRO_DIM[ks[0]]; if(!dim||!CON_STATS) return null;
    const fila=(CON_STATS[dim[0]]||[]).find(x=>String(x[dim[1]])===String(f[ks[0]]));
    return fila?{contratos:fila.n}:null;   // fuera del top de su lista: mejor no afirmar
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
    if(_conPagina){
      const u=new URL(location.href);
      if(CON.q) u.searchParams.set('q',CON.q); else u.searchParams.delete('q');
      history.replaceState(null,'',u);   // replace y no push: el atrás del
    }                                    // navegador debe salir de la página,
                                         // no recorrer treinta búsquedas.
    // si no hay contratos pero sí procesos, abrir en procesos: es el caso
    // PAF-MENIES generalizado — mandar a una lista vacía cuando el hallazgo está
    // en la otra pestaña es el mismo falso negativo que venimos corrigiendo.
    const nP=d.procesos?(d.procesos.total!=null?d.procesos.total:d.procesos.n):0;
    if(!(d.total&&d.total.contratos)&&!d.n&&nP) CON.tab='procesos';
    conRenderResults(d);
  }

  /* ================= columna izquierda · cómo se busca y qué buscar =========
     La derecha son cifras; la izquierda es lo que hace que las cifras se
     puedan usar. SECOP no se busca como Google —el texto libre mira TODAS las
     columnas, un radicado no es texto y una empresa no es su marca— y hasta
     ahora eso solo se descubría fallando. Cada regla de abajo describe algo
     que el buscador de esta página hace de verdad; si el comportamiento
     cambia, la regla cambia con él (viven en el mismo archivo justamente por
     eso). El ejemplo de cada una es clicable: se aprende buscando. */
  const GUIA=[
    {t:'Varias palabras se combinan con Y',
     d:'Los contratos tienen que decir todas. Agregar una palabra <b>afina</b>, no amplía.',
     ej:'alimentación escolar'},
    {t:'Un radicado se busca por igualdad',
     d:'Si pegas un número —de contrato, de proceso o un <code>CO1.NTC…</code>— no se busca como texto: se busca exacto, y también entre los <b>procesos</b>.',
     ej:'PAF-MENIES-O-134-2024'},
    {t:'Contratos y procesos son cosas distintas',
     d:'El proceso se publica <b>antes</b> que el contrato: ahí la contratación todavía se puede pelear. Cuando los hay, salen en su propia pestaña — nunca sumados, porque son la misma contratación contada dos veces.'},
    {t:'Una empresa se filtra por identidad',
     d:'Si el nombre está en el diccionario de Caudal, se buscan los contratos que <b>son</b> de la empresa (su razón social), no los que mencionan la marca. Por eso «Claro» trae a COMCEL y no a los señores que se apellidan Claro.',
     ej:'claro'},
    {t:'La búsqueda mira todas las columnas',
     d:'Un contrato puede salir por su sector o su modalidad aunque el objeto no nombre lo que buscaste. Cuando pasa, la tarjeta lo dice con un <b>match:</b>, y el botón <b>Solo en el objeto</b> aprieta la búsqueda.'},
    {t:'Los filtros exactos rinden más que el texto',
     d:'Toca cualquier cifra de la derecha —un año, un sector, una entidad— y filtra sin el ruido del texto libre.'},
  ];

  /* Puntos de entrada por tema. No son categorías de SECOP (esas ya están a la
     derecha, y son las de verdad): son las búsquedas con las que la gente
     llega. Cada término está probado contra la API — uno que devuelva cero es
     peor que no ofrecerlo. */
  const TEMAS=[
    ['Obra e infraestructura', ['interventoría vías','pavimentación','placa huella','acueducto','alumbrado público']],
    ['Salud',                  ['dotación hospitalaria','medicamentos','equipo biomédico','ambulancia','oxígeno medicinal']],
    ['Educación y bienestar',  ['alimentación escolar','transporte escolar','primera infancia','adulto mayor']],
    ['Seguridad y defensa',    ['comando conjunto caribe','cámaras de seguridad','dotación policía']],
    ['Riesgo y ambiente',      ['carrotanques','damnificados','relleno sanitario','residuos hospitalarios']],
    ['Tecnología y datos',     ['software','conectividad','ciberseguridad','inteligencia artificial']],
  ];

  function conRail(){
    const el=document.getElementById('con-rail'); if(!el) return;
    el.innerHTML=`
      <div class="con-rblk con-rblk--guia">
        <h4>Cómo se busca acá</h4>
        <div class="con-tips">${GUIA.map(g=>`<div class="con-tip">
          <div class="con-tip-t">${g.t}</div>
          <div class="con-tip-d">${g.d}</div>
          ${g.ej?`<button class="con-ej" data-q="${esc(g.ej)}">${esc(g.ej)}</button>`:''}
        </div>`).join('')}</div>
      </div>
      <div class="con-rblk con-rblk--temas">
        <h4>Temas clave</h4>
        <div class="con-temas">${TEMAS.map(([g,qs])=>`<div class="con-tema">
          <div class="con-tema-g">${esc(g)}</div>
          <div class="chips">${qs.map(x=>`<span class="chip" data-q="${esc(x)}">${esc(x)}</span>`).join('')}</div>
        </div>`).join('')}</div>
      </div>
      <div class="con-rblk con-rblk--fuente con-rfuente">
        <h4>De dónde sale</h4>
        <div class="con-tip-d">SECOP II · Contratos Electrónicos y Procesos de Contratación, de Colombia Compra Eficiente, por <a href="https://www.datos.gov.co/resource/jbjy-vk9h.json" target="_blank" rel="noopener">datos.gov.co</a>. Los agregados de la derecha se recalculan a diario; <b>la búsqueda va en vivo</b> contra la fuente, así que lo que ves es lo que hay publicado en este momento.</div>
      </div>`;
    el.querySelectorAll('[data-q]').forEach(b=>b.onclick=()=>conIr(b.dataset.q));
  }
  // Un solo camino para «busca esto»: pone el término en la caja, limpia los
  // filtros y busca. Sin esto cada chip repetía los tres pasos y alguno se
  // olvidaba de limpiar los filtros, así que el resultado salía recortado por
  // un filtro invisible puesto tres búsquedas atrás.
  function conIr(q){
    const i=document.getElementById('conq'); if(i) i.value=q;
    CON.q=q; CON.filtros={}; CON.solo=false; conBuscar();
  }

  /* ================= columna derecha · la forma del gasto ==================
     Antes esto eran cuatro rejillas de números apilados, todas con la misma
     forma, y tres de las siete listas que devuelve la API no se usaban. Lo
     que sigue las usa y, sobre todo, las pone en PROPORCIÓN: el dato de
     SECOP no es que haya seis millones de contratos, es que tres cuartas
     partes se firman sin proceso competitivo. Un porcentaje se lee; una lista
     de seis cifras de siete dígitos, no. */
  const pct=(n,t)=>t?Math.round(n/t*1000)/10:0;
  const pc=(n,t)=>pct(n,t).toString().replace('.',',')+'%';
  /* Cuántos elementos siguientes hay que sumar para alcanzar al primero. Es lo
     que convierte «Bogotá 33,4%» en algo que se entiende sin hacer cuentas —y
     se calcula, no se escribe: la frase «más que los cinco siguientes juntos»
     era cierta el día que se redactó y nadie se iba a enterar el día que
     dejara de serlo. */
  function cuantosAlcanzan(items){
    const l=items||[]; if(l.length<2) return 0;
    let acc=0;
    for(let i=1;i<l.length;i++){ acc+=l[i].n; if(acc>=l[0].n) return i; }
    return l.length-1;
  }
  /* Barras horizontales con la proporción adentro. `clave` es el campo que
     nombra cada fila (cambia por lista: modalidad, tipo, departamento…) y
     `filtro` el nombre del filtro que dispara al tocarla — null si esa
     dimensión no es filtrable, para no ofrecer un click que no hace nada. */
  function conBarras(items, clave, total, filtro, n){
    const l=(items||[]).slice(0,n||6);
    if(!l.length) return '';
    const mx=Math.max.apply(null,l.map(x=>x.n))||1;
    return `<div class="con-bh">${l.map(x=>{
      const v=x[clave]||'—', p=pct(x.n,total);
      const at=filtro?` data-filtro="${esc(filtro)}" data-valor="${esc(v)}" role="button" tabindex="0"`:'';
      return `<div class="con-bh-row${filtro?' cl':''}"${at} title="${esc(v)} · ${fmt(x.n)} contratos${filtro?' · toca para filtrar':''}">
        <div class="con-bh-l">${esc(v)}</div>
        <div class="con-bh-track"><div class="con-bh-fill" style="width:${Math.max(1.2,x.n/mx*100)}%"></div></div>
        <div class="con-bh-n">${p>=0.1?p.toString().replace('.',',')+'%':'<0,1%'}</div>
      </div>`;}).join('')}</div>`;
  }

  /* La cifra del día. Rota con el calendario sobre hechos DERIVADOS del mismo
     payload que pinta la página: ninguno está escrito a mano, así que ninguno
     puede quedar desactualizado como quedó el «5,87 M» del hero, que llevaba
     meses diciendo una cifra que la fuente ya había dejado atrás. */
  function datoDelDia(s){
    const T=(s.total||{}).contratos||0, L=k=>(s[k]||[])[0]||{};
    const cand=[];
    const mod=L('por_modalidad');
    if(mod.n) cand.push({n:pct(mod.n,T).toString().replace('.',',')+'%',
      t:`de los contratos del Estado se firman por <b>${esc(mod.modalidad)}</b>. Es la vía sin proceso competitivo: la entidad escoge al contratista.`});
    const tip=L('por_tipo');
    if(tip.n) cand.push({n:Math.round(tip.n/T*10)+' de cada 10',
      t:`contratos son de <b>${esc(String(tip.tipo).toLowerCase())}</b>. El Estado colombiano contrata sobre todo gente, no obras.`});
    const dep=L('por_departamento');
    if(dep.n) cand.push({n:pct(dep.n,T).toString().replace('.',',')+'%',
      t:`de toda la contratación del país se firma en <b>${esc(dep.departamento)}</b>${(()=>{const k=cuantosAlcanzan(s.por_departamento);return k>1?` — más que los ${k} departamentos siguientes juntos`:'';})()}.`});
    const ord=L('por_orden');
    if(ord.n) cand.push({n:Math.round(ord.n/T*10)+' de cada 10',
      t:`contratos los firma una entidad del orden <b>${esc(String(ord.orden).toLowerCase())}</b>, no la Nación. La plata pública se mueve en los municipios.`});
    if(s.mediana_cop) cand.push({n:fmtCOP(s.mediana_cop),
      t:'es el <b>contrato mediano</b>: la mitad de la contratación pública vale menos que eso. El promedio no sirve acá — la columna de valor de SECOP trae erratas de hasta doce órdenes de magnitud.'});
    const sf=(s.por_anio||[]).find(x=>!/^\d{4}$/.test(x.anio));
    if(sf&&sf.n) cand.push({n:fmt(sf.n),
      t:'contratos llegan <b>sin fecha de firma</b> en la fuente. Entran en el total y quedan fuera de la serie por año: es un hueco de la fuente, no un dato.'});
    const ent=(s.top_entidades_n||[])[0];
    if(ent&&ent.n) cand.push({n:fmt(ent.n),
      t:`contratos firmó <b>${esc(String(ent.entidad).replace(/^[(]|[)]$/g,''))}</b>, la entidad que más contrata del país por número de contratos.`});
    if(!cand.length) return '';
    const d=cand[Math.floor(Date.now()/864e5)%cand.length];
    return `<div class="con-dato"><div class="con-dato-k">El dato de hoy</div>
      <div class="con-dato-n">${d.n}</div><div class="con-dato-t">${d.t}</div></div>`;
  }

  /* Las notas de los dos paneles de arriba dicen lo que el panel muestra, así
     que salen del payload: escritas a mano envejecen con la fuente y nadie se
     entera —es la misma razón por la que el hero dejó de llevar su cifra. */
  function notaModalidad(s,T){
    const l=s.por_modalidad||[], d=l[0];
    if(!d) return '';
    const p=pct(d.n,T);
    const cuanto=p>=70?'Tres de cada cuatro':p>=45?'Más de la mitad de los':`El ${pc(d.n,T)} de los`;
    return `${cuanto} contratos del Estado se firman por <b>${esc(String(d.modalidad).toLowerCase())}</b>, la vía sin proceso competitivo. Es legal y a veces la única posible, pero es donde vale la pena mirar.`;
  }
  function notaTipo(s,T){
    const l=s.por_tipo||[], d=l[0];
    if(!d) return '';
    const obra=l.find(x=>/^obra/i.test(x.tipo||''));
    const so=obra?` La obra pública, que es de lo que más se habla, es el ${pc(obra.n,T)} de los contratos — otra cosa es cuánto vale cada uno.`:'';
    return `El ${pc(d.n,T)} son de <b>${esc(String(d.tipo).toLowerCase())}</b>: el Estado colombiano contrata sobre todo gente.${so}`;
  }
  function conRenderLanding(s){
    const el=document.getElementById('con-landing'); if(!el||!s) return;
    const T=(s.total||{}).contratos||0;
    const anios=(s.por_anio||[]).filter(x=>/^\d{4}$/.test(x.anio)).sort((a,b)=>a.anio<b.anio?-1:1);
    const sinFecha=((s.por_anio||[]).find(x=>!/^\d{4}$/.test(x.anio))||{}).n||0;
    const mx=Math.max.apply(null,anios.map(x=>x.n))||1;
    const frec=(s.fuente||{}).frecuencia||'—';
    const act=(s.generado||'').slice(0,10);
    const heroN=document.getElementById('con-hero-n'); if(heroN) heroN.textContent=fmt(T);
    el.innerHTML=`
      ${datoDelDia(s)}
      <div class="kpis con-kpis">
        <div class="kpi"><div class="n">${fmt(T)}</div><div class="l">Contratos</div></div>
        <div class="kpi"><div class="n" style="color:var(--amber)">${fmtCOP(s.mediana_cop)||'—'}</div><div class="l">Contrato mediano</div></div>
        <div class="kpi"><div class="n">${(s.por_departamento||[]).length}</div><div class="l">Departamentos</div></div>
        <div class="kpi"><div class="n" style="color:var(--teal)">${esc(frec)}</div><div class="l">Actualización</div></div>
      </div>

      <div class="panel"><h3>Contratos por año de firma</h3>
        <div class="gac-bars">${anios.map(x=>`<div class="gac-bar" data-anio="${esc(x.anio)}" title="${fmt(x.n)} contratos firmados en ${esc(x.anio)}"><div class="gac-bar-fill" style="height:${Math.round(x.n/mx*100)}%"></div><div class="gac-bar-l">${esc(x.anio).slice(2)}</div></div>`).join('')}</div>
        <div class="cob-note">Toca un año para ver sus contratos. El año en curso va incompleto, y ${fmt(sinFecha)} contratos más no traen fecha en la fuente: no están en esta serie, pero sí en el total.</div>
      </div>

      <div class="con-2">
        <div class="panel"><h3>Cómo se contrata · modalidad</h3>
          ${conBarras(s.por_modalidad,'modalidad',T,'modalidad')}
          <div class="cob-note">${notaModalidad(s,T)}</div>
        </div>
        <div class="panel"><h3>Qué se contrata · tipo</h3>
          ${conBarras(s.por_tipo,'tipo',T,'tipo')}
          <div class="cob-note">${notaTipo(s,T)}</div>
        </div>
      </div>

      <div class="con-2">
        <div class="panel"><h3>Dónde se firma</h3>
          ${conBarras(s.por_departamento,'departamento',T,'departamento',8)}
        </div>
        <div class="panel"><h3>Quién lo firma y en qué va</h3>
          ${conBarras(s.por_orden,'orden',T,'orden_entidad',4)}
          <div class="cob-note" style="margin-top:1.1rem">Y en qué estado está:</div>
          ${conBarras(s.por_estado,'estado',T,'estado',5)}
        </div>
      </div>

      <div class="panel"><h3>Por sector</h3>
        ${conBarras(s.por_sector,'sector',T,'sector',8)}
      </div>

      <div class="panel"><h3>Entidades que más contratan</h3>
        <div class="cob-note" style="margin:-.4rem 0 .9rem">Se cuentan contratos, no pesos: la columna de valor de SECOP trae errores de digitación que ponían a una institución universitaria encabezando la contratación del país con una cifra mayor que el PIB mundial.</div>
        <div class="reg-sectors-grid">${(s.top_entidades_n||[]).slice(0,8).map(x=>`<div class="sec-card" data-entidad="${esc(x.entidad)}"><div class="n">${fmt(x.n)}</div><div class="l">${esc(x.entidad)}</div></div>`).join('')}</div>
      </div>

      ${s.nota?`<div class="cob-note">${esc(s.nota)}${act?` · agregados del ${esc(act)}`:''}</div>`:''}`;

    // un solo cableado para todo lo que filtra: rejillas, barras y años.
    const filtrar=(k,v)=>{ CON.q=''; const i=document.getElementById('conq'); if(i) i.value=''; CON.filtros={[k]:v}; conBuscar(); };
    el.querySelectorAll('.sec-card[data-entidad]').forEach(c=>c.onclick=()=>filtrar('entidad',c.dataset.entidad));
    el.querySelectorAll('.gac-bar[data-anio]').forEach(b=>b.onclick=()=>filtrar('anio',b.dataset.anio));
    el.querySelectorAll('.con-bh-row.cl').forEach(r=>{
      const go=()=>filtrar(r.dataset.filtro, r.dataset.valor);
      r.onclick=go;
      r.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); go(); } };
    });
  }

  async function conLoadStats(){
    conRail();
    if(CON_STATS){ conRenderLanding(CON_STATS); return; }
    const el=document.getElementById('con-landing'); if(!el) return;
    el.innerHTML='<div class="llm-load" style="padding:2rem;justify-content:center">Cargando el pilar de contratación <span class="dots"><span></span><span></span><span></span></span></div>';
    try{ CON_STATS=await call({action:'contratacion'}); }catch(e){ CON_STATS=null; }
    if(CON_STATS) conRenderLanding(CON_STATS);
    else el.innerHTML='<div class="err">No se pudo cargar la contratación. Reintenta.</div>';
  }
  function conShowLanding(){
    const r=document.getElementById('con-results'); if(r){ r.style.display='none'; r.innerHTML=''; }
    const l=document.getElementById('con-landing'); if(l) l.style.display='block';
  }
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
    if(cont) CON_EJEMPLOS.forEach(t=>{ const c=document.createElement('span'); c.className='chip'; c.textContent=t; c.onclick=()=>conIr(t); cont.appendChild(c); });
    const cb=document.getElementById('conBack'); if(cb) cb.onclick=()=>{ if(typeof showView==='function') showView('home'); };
    // Llegar con el término puesto: es como entra quien viene de la búsqueda
    // universal de caudal.html («abrir el pilar →»), que ahora es un salto de
    // página y no un cambio de vista.
    _conPagina=!!document.getElementById('con-rail');
    // Llegar con el término puesto: así entra quien viene de la búsqueda
    // universal de caudal.html («abrir el pilar →»), que ahora es un salto de
    // página. Quien llega así espera RESULTADOS, no el buscador relleno — la
    // búsqueda la dispara `initHome` cuando el landing ya cargó, porque el
    // universo de los filtros sale de esos agregados.
    const qs=(new URLSearchParams(location.search).get('q')||'').trim();
    if(qs&&cq){ cq.value=qs; CON.q=qs; }
    return !!qs;
  }

  /* Lo que necesitan las dos páginas. `conCard` y `CON` los usa la búsqueda
     universal de caudal.html para su pestaña de contratación; el resto solo
     corre en la página del pilar. */
  Object.assign(window, { CON, conCard, conBuscar, conInit, conLoadStats, conIr });
})();
