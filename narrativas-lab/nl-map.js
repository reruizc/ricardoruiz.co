/* ════════════════════════════════════════════════════════════════
   NarrativasLab · nl-map.js
   Mapa Leaflet de DOS NIVELES (Comuna/Localidad → drill Barrio) para
   las 14 ciudades. Fuente única: ciudades-barrios-2v.json (geojson +
   datos por barrio ya joineados por índice de feature: Cepeda/Abelardo
   1V y 2V, ganador, margen, comuna `cm`).

   El color/tooltip lo decide la PÁGINA vía un styler(rec, ctx):
     ctx.level = 'comuna' | 'barrio'
     ctx.comunaRec = agregado de la comuna del barrio (en vista comuna)
   Así el mismo mapa sirve a histórico-electoral (ganador/margen),
   construir y escenarios (persuasión simulada anclada en `rec.ideo`).
   Requiere Leaflet (L) cargado. Patrón de render copiado de
   ciudades-2v-barrios.html (rotación Bogotá, keyOf, fill-opacity).
   ════════════════════════════════════════════════════════════════ */
(function(){
  const DATA_URL = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/prec-2v/ciudades-barrios-2v.json?v=20260623c';
  let _data=null, _dataP=null;
  const _geoCache={};
  const clampN=(x,a,b)=>Math.max(a,Math.min(b,x));
  const ideoFromShare = share => clampN((0.5-share)*1.7, -0.85, 0.85);  // cepShare alto → izq (ideo<0)

  function loadData(){
    if(_data) return Promise.resolve(_data);
    if(!_dataP) _dataP = fetch(DATA_URL).then(r=>r.json()).then(j=>{ _data=j; return j; });
    return _dataP;
  }
  function loadGeo(url){
    if(_geoCache[url]) return Promise.resolve(_geoCache[url]);
    return fetch(url).then(r=>r.json()).then(g=>{ _geoCache[url]=g; return g; });
  }
  // Rotación 90° izq SOLO para Bogotá (cx=-74.08, cy=4.65) — verbatim de ciudades-2v-barrios.html
  function rotGeo(g){
    const cx=-74.08, cy=4.65, rc=([lo,la])=>[cx-(la-cy), cy+(lo-cx)];
    const rg = ge => { if(!ge) return ge;
      if(ge.type==='Polygon') return {...ge, coordinates:ge.coordinates.map(r=>r.map(rc))};
      if(ge.type==='MultiPolygon') return {...ge, coordinates:ge.coordinates.map(p=>p.map(r=>r.map(rc)))};
      return ge; };
    return {...g, features:g.features.map(f=>({...f, geometry:rg(f.geometry)}))};
  }

  function NLMap(container){
    const el = (typeof container==='string') ? document.querySelector(container) : container;
    let map=null, layer=null, meta=null, geo=null, bd=null;
    let barrios=[], comunas=[], byComuna={}, byKey={};
    let styler=null, drillCb=null, level='comuna', comunaFilter=null;

    function ensureMap(){
      if(map) return;
      map = L.map(el, { scrollWheelZoom:false, attributionControl:false, zoomControl:true });
    }
    const keyOf = (f,i) => meta.keyfld==='__idx' ? String(i) : String(f.properties[meta.keyfld]);

    async function loadCity(cfg){
      const d = await loadData();
      const city = d[cfg.key];
      if(!city) throw new Error('Sin datos de barrio para '+cfg.key);
      meta = city.meta; bd = city.b || {};
      geo = await loadGeo(meta.url);
      if(meta.rot) geo = rotGeo(geo);
      geo.features.forEach((f,i)=>{ f.__i = i; });

      barrios=[]; byComuna={}; byKey={};
      geo.features.forEach((f,i)=>{
        const key = keyOf(f,i);
        const b = bd[key]; if(!b) return;
        const c1=b.c1||0, a1=b.a1||0, c2=b.c2||0, a2=b.a2||0;
        const share1 = (c1+a1)>0 ? c1/(c1+a1) : 0.5;
        const share2 = (c2+a2)>0 ? c2/(c2+a2) : 0.5;
        const rec = Object.assign({}, b, { key, __i:i, share1, share2, ideo:ideoFromShare(share2), feature:f });
        barrios.push(rec); byKey[key]=rec;
        const cm = (b.cm||'').trim();
        if(cm){
          const g = byComuna[cm] || (byComuna[cm] = { cm, n:0, c1:0,a1:0,c2:0,a2:0, keys:[] });
          g.n++; g.c1+=c1; g.a1+=a1; g.c2+=c2; g.a2+=a2; g.keys.push(key);
        }
      });
      comunas = Object.values(byComuna).map(g=>{
        const share1 = (g.c1+g.a1)>0 ? g.c1/(g.c1+g.a1) : 0.5;
        const share2 = (g.c2+g.a2)>0 ? g.c2/(g.c2+g.a2) : 0.5;
        g.share1=share1; g.share2=share2; g.ideo=ideoFromShare(share2);
        g.w1 = g.c1>=g.a1?'C':'A'; g.w2 = g.c2>=g.a2?'C':'A';
        g.m1 = Math.round(Math.abs(share1*100-50)*2*10)/10;
        g.m2 = Math.round(Math.abs(share2*100-50)*2*10)/10;
        return g;
      });
      return { barrios, comunas, hasComuna: !!(cfg.hasComuna && comunas.length>0), meta };
    }

    const recOf = f => byKey[keyOf(f, f.__i)] || null;
    function _st(f){
      const rec = recOf(f);
      if(!rec) return { _rec:null, style:{ fillColor:'#7d7d7d', fillOpacity:.25, color:'rgba(255,255,255,.12)', weight:.5 }, tip:'<b>Sin dato directo</b>' };
      const ctx = { level, comunaRec: byComuna[rec.cm]||null };
      const s = styler ? styler(rec, ctx) : { fillColor:'#888' };
      return { _rec:rec,
        style:{ fillColor:s.fillColor||'#888', fillOpacity:(s.fillOpacity!=null)?s.fillOpacity:(rec.f?.5:.9), color:'rgba(255,255,255,.16)', weight:.5 },
        tip: s.tooltip || '<b>Sin dato</b>' };
    }

    function draw(_level, _comuna){
      ensureMap();
      level = _level; comunaFilter = _comuna || null;
      if(layer){ map.removeLayer(layer); layer=null; }
      const feats = geo.features.filter(f=>{
        if(level==='barrio' && comunaFilter){ const r=recOf(f); return r && r.cm===comunaFilter; }
        return true;
      });
      layer = L.geoJSON({ type:'FeatureCollection', features:feats }, {
        style: f => _st(f).style,
        onEachFeature: (f,l)=>{
          const o = _st(f);
          l.bindTooltip(o.tip, { sticky:true, className:'nl-tip' });
          l.on('mouseover', ()=>l.setStyle({ weight:2, color:'#fff' }));
          l.on('mouseout',  ()=>l.setStyle({ weight:.5, color:'rgba(255,255,255,.16)' }));
          l.on('click', ()=>{ const rec=recOf(f); if(level==='comuna' && rec && rec.cm && drillCb) drillCb(rec.cm); });
        }
      }).addTo(map);
      try { map.fitBounds(layer.getBounds(), { padding:[10,10] }); } catch(e){}
      setTimeout(()=>{ try{ map.invalidateSize(); }catch(e){} }, 60);
    }

    // Recolorea SIN reconstruir la geometría (rápido para recolorear en cada edición del mensaje).
    function restyle(){
      if(!layer) return;
      layer.eachLayer(l=>{ const o=_st(l.feature); l.setStyle(o.style); if(l.getTooltip()) l.setTooltipContent(o.tip); else l.bindTooltip(o.tip,{sticky:true,className:'nl-tip'}); });
    }

    return {
      el, loadCity, draw, restyle,
      setStyler: fn => { styler = fn; },
      onDrill: fn => { drillCb = fn; },
      barrioRecords: () => barrios,
      comunaRecords: () => comunas,
      getComuna: name => byComuna[name] || null,
      redraw: () => draw(level, comunaFilter),
      invalidate: () => { if(map) setTimeout(()=>{ try{ map.invalidateSize(); }catch(e){} },50); }
    };
  }
  window.NLMap = NLMap;
})();
