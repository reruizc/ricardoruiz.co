/* ════════════════════════════════════════════════════════════════
   NarrativasLab · cities.js
   Las 14 ciudades con GeoJSON por barrio REAL (deployadas en
   ciudades-barrios-2v.json). NUNCA Voronoi: las que solo tienen
   polígono aproximado quedan fuera hasta tener GeoJSON real.

   OJO con los dos esquemas de código (no derivables entre sí):
     · divipola  → para crimen (LabIndicadores.getMun)
     · huellaMun → para electoral (huella-territorial.json muns{})
   La metadata de geometría (url/fld/com/keyfld/rot) NO vive aquí: la lee
   nl-map.js de ciudades-barrios-2v.json (que ya trae el join hecho).

   Estado de ciudad activa en localStorage['nl-city']; cambia sin reload
   y dispara onChange() para que cada página re-renderice.
   ════════════════════════════════════════════════════════════════ */
(function(){
  const CITIES = {
    bogota:       { nombre:'Bogotá D.C.',  divipola:'11001', depCod:'11', huellaMun:'16-001', huellaCiudad:'Bogotá',       grupo:'grande',     hasComuna:true,  hasArquetipos:false, hasSaliencia:false },
    medellin:     { nombre:'Medellín',     divipola:'05001', depCod:'05', huellaMun:'01-001', huellaCiudad:'Medellín',     grupo:'grande',     hasComuna:true,  hasArquetipos:true,  hasSaliencia:true  },
    cali:         { nombre:'Cali',         divipola:'76001', depCod:'76', huellaMun:'31-001', huellaCiudad:'Cali',         grupo:'grande',     hasComuna:true,  hasArquetipos:false, hasSaliencia:false },
    barranquilla: { nombre:'Barranquilla', divipola:'08001', depCod:'08', huellaMun:'03-001', huellaCiudad:'Barranquilla', grupo:'grande',     hasComuna:true,  hasArquetipos:false, hasSaliencia:false },
    cartagena:    { nombre:'Cartagena',    divipola:'13001', depCod:'13', huellaMun:'05-001', huellaCiudad:'Cartagena',    grupo:'intermedia', hasComuna:true,  hasArquetipos:false, hasSaliencia:false },
    cucuta:       { nombre:'Cúcuta',       divipola:'54001', depCod:'54', huellaMun:'25-001', huellaCiudad:'Cúcuta',       grupo:'intermedia', hasComuna:true,  hasArquetipos:false, hasSaliencia:false },
    bucaramanga:  { nombre:'Bucaramanga',  divipola:'68001', depCod:'68', huellaMun:'27-001', huellaCiudad:'Bucaramanga',  grupo:'intermedia', hasComuna:true,  hasArquetipos:false, hasSaliencia:false },
    pereira:      { nombre:'Pereira',      divipola:'66001', depCod:'66', huellaMun:'24-001', huellaCiudad:'Pereira',      grupo:'intermedia', hasComuna:true,  hasArquetipos:false, hasSaliencia:false },
    manizales:    { nombre:'Manizales',    divipola:'17001', depCod:'17', huellaMun:'09-001', huellaCiudad:'Manizales',    grupo:'intermedia', hasComuna:true,  hasArquetipos:false, hasSaliencia:false },
    santamarta:   { nombre:'Santa Marta',  divipola:'47001', depCod:'47', huellaMun:'21-001', huellaCiudad:'Santa Marta',  grupo:'intermedia', hasComuna:false, hasArquetipos:false, hasSaliencia:false },
    popayan:      { nombre:'Popayán',      divipola:'19001', depCod:'19', huellaMun:'11-001', huellaCiudad:'Popayán',      grupo:'intermedia', hasComuna:true,  hasArquetipos:false, hasSaliencia:false },
    soledad:      { nombre:'Soledad',      divipola:'08758', depCod:'08', huellaMun:'03-052', huellaCiudad:'Soledad',      grupo:'intermedia', hasComuna:true,  hasArquetipos:false, hasSaliencia:false },
    buenaventura: { nombre:'Buenaventura', divipola:'76109', depCod:'76', huellaMun:'31-019', huellaCiudad:'Buenaventura', grupo:'intermedia', hasComuna:false, hasArquetipos:false, hasSaliencia:false },
    quibdo:       { nombre:'Quibdó',       divipola:'27001', depCod:'27', huellaMun:'17-001', huellaCiudad:'Quibdó',       grupo:'intermedia', hasComuna:true,  hasArquetipos:false, hasSaliencia:false }
  };
  // orden de aparición (grandes primero, luego intermedias)
  const LIST = ['bogota','medellin','cali','barranquilla','cartagena','cucuta','bucaramanga','pereira','manizales','santamarta','popayan','soledad','buenaventura','quibdo'];
  Object.keys(CITIES).forEach(k => CITIES[k].key = k);

  const DEFAULT = 'bogota';
  const STORE = 'nl-city';
  const _cbs = [];

  function activeKey(){
    let k = null;
    try { k = localStorage.getItem(STORE); } catch(e){}
    return (k && CITIES[k]) ? k : DEFAULT;
  }
  function active(){ return CITIES[activeKey()]; }
  function get(k){ return CITIES[k] || null; }
  function setActive(k){
    if (!CITIES[k] || k === activeKey()) return;
    try { localStorage.setItem(STORE, k); } catch(e){}
    _cbs.forEach(fn => { try { fn(CITIES[k]); } catch(e){ console.warn(e); } });
  }
  function onChange(fn){ if (typeof fn === 'function') _cbs.push(fn); }

  window.NLCities = { CITIES, LIST, get, active, activeKey, setActive, onChange };
})();
