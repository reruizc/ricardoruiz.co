/* Base de datos compartida del hub de Policía (hub + mapa + histórico).
   Lo visual lo pone `legislativo-base.css` / `legislativo-base.js`, que son
   genéricos (cursor, nav, tarjetas, modal, sesión); aquí solo vive lo que
   sabe de PONAL: de dónde bajan los JSON, el catálogo de delitos y el cruce
   de códigos para los mapas. */
(function(){
  const S3='https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output';
  /* El prefijo cuelga de congreso-2026/output porque la política del bucket
     ya lo cubre como público; un prefijo nuevo de primer nivel exigiría
     tocar la policy. Ver la sección de S3 en CLAUDE.md. */
  const BASE=S3+'/ponal';
  const MAPAS=S3+'/mapas-2026';
  /* cache-buster por hora: los JSON se sirven con max-age corto, pero Safari
     es agresivo con JSON sin Cache-Control (mismo patrón de oportunidad.html) */
  const V=()=>'?v='+Math.floor(Date.now()/3600000);

  const _c={};
  async function j(url,key){
    if(_c[key]) return _c[key];
    const r=await fetch(url);
    if(!r.ok) throw new Error('HTTP '+r.status+' · '+key);
    return (_c[key]=await r.json());
  }
  const meta       =()=>j(BASE+'/meta.json'+V(),'meta');
  const poblacion  =()=>j(BASE+'/poblacion.json'+V(),'pob');
  const ciudades   =()=>j(BASE+'/ciudades.json'+V(),'ciu');
  const ciudad     =d=>j(BASE+'/ciudades/'+d+'.json'+V(),'ciu-'+d);
  const geoCiudad  =f=>j(MAPAS+'/Ciudades-COM-LOC/'+f,'geo-ciu-'+f);
  const nacional   =()=>j(BASE+'/nacional.json'+V(),'nacional');
  const deptos     =()=>j(BASE+'/deptos.json'+V(),'deptos');
  const municipios =()=>j(BASE+'/municipios.json'+V(),'muns');
  const geoDeptos  =()=>j(MAPAS+'/DEPARTAMENTOS2.json','geo-dep');
  /* Los archivos municipales se llaman por código ELECTORAL, pero adentro
     cada municipio trae `mpio_cdpmp`, que es el DANE de 5 dígitos — el mismo
     que usa PONAL. O sea: el nombre del archivo se resuelve con la tabla de
     abajo y el match de cada polígono se hace por DANE, sin crosswalk. */
  const geoMuns    =dane2=>j(`${MAPAS}/Departamentos-mps/${DANE_A_ELECTORAL[dane2]}.json`,'geo-mun-'+dane2);

  /* DANE → electoral. Copiada de split_municipios.py, que es el script que
     generó esos GeoJSON: es la tabla autoritativa, no una reconstrucción. */
  const DANE_A_ELECTORAL={
    '05':'01','08':'03','11':'16','13':'05','15':'07','17':'09','18':'44',
    '19':'11','20':'12','23':'13','25':'15','27':'17','41':'19','44':'48',
    '47':'21','50':'52','52':'23','54':'25','63':'26','66':'24','68':'27',
    '70':'28','73':'29','76':'31','81':'40','85':'46','86':'64','88':'56',
    '91':'60','94':'50','95':'54','97':'68','99':'72'};

  /* Los nombres del GeoJSON nacional vienen en `name` y no siempre casan con
     los del DANE (`Bogotá D.C.` vs `Santa Fe de Bogotá`). Se normaliza y se
     agregan los alias medidos. */
  const norm=s=>String(s||'').normalize('NFD').replace(/[̀-ͯ]/g,'')
                  .toUpperCase().replace(/[^A-Z]/g,'');
  const ALIAS={
    /* el nacional dice `Distrito Capital de Bogotá`, no `Bogotá D.C.`: sin este
       alias la jurisdicción más grande del país se pinta como «sin dato» y no
       protesta nadie. Es el mismo alias que ya usan los mapas del Pacto. */
    'DISTRITOCAPITALDEBOGOTA':'11','DISTRITOCAPITAL':'11',
    'BOGOTA':'11','BOGOTADC':'11','SANTAFEDEBOGOTA':'11',
    'SANANDRES':'88','SANANDRESYPROVIDENCIA':'88','ARCHIPIELAGODESANANDRES':'88',
    'ARCHIPIELAGODESANANDRESPROVIDENCIAYSANTACATALINA':'88',
    'VALLE':'76','VALLEDELCAUCA':'76','NORTEDESANTANDER':'54','LAGUAJIRA':'44','GUAJIRA':'44'};

  /* Aviso ruidoso: un departamento que no casa se pinta igual que uno con cero
     denuncias, así que sin esto el hueco es invisible. NO se intenta adivinar
     por parecido — `Santander` y `Norte de Santander` se confundirían. */
  function avisarSinMatch(nombres,resolver){
    const malos=nombres.filter(n=>!resolver(n));
    if(malos.length) console.warn('[PONAL] departamentos del mapa sin datos asociados:',malos);
    return malos;
  }

  /* Escala secuencial para el coropletas. Ámbar→rojo: es la paleta de
     "intensidad" del sitio y se lee bien sobre el fondo #060810 (el azul
     está tomado por lo electoral). */
  const RAMPA=['#1d2233','#3a2f2a','#6b4a22','#a4681c','#d4791a','#e8933a','#f2b25e'];
  function color(v,max){
    if(!v) return 'rgba(255,255,255,.05)';
    /* raíz cuadrada, no lineal: el delito se concentra tanto en Bogotá que
       una escala lineal deja el resto del país en un solo tono */
    const t=Math.min(1,Math.sqrt(v/Math.max(1,max)));
    return RAMPA[Math.min(RAMPA.length-1,Math.floor(t*RAMPA.length))];
  }

  /* Los `solo_2024` no tienen historia: la fuente los empezó a entregar en
     ese lote. Cualquier vista temporal debe excluirlos o marcarlos. */
  const conSerie=m=>(m.delitos||[]).filter(d=>!d.solo_2024);

  /* Bogotá se dibuja rotada 90° a la izquierda — es la convención con la que
     se ve la ciudad en todo el proyecto (misma transformación que usan senado,
     cámara y los mapas del Pacto). */
  function rotar90(geo){
    const cx=-74.08, cy=4.65;
    const f=c=>Array.isArray(c[0])?c.map(f):[cx-(c[1]-cy), cy+(c[0]-cx)];
    return {...geo, features:geo.features.map(x=>({...x,
      geometry:{...x.geometry, coordinates:f(x.geometry.coordinates)}}))};
  }

  window.PONAL={meta,nacional,deptos,municipios,poblacion,ciudades,ciudad,
    geoDeptos,geoMuns,geoCiudad,rotar90,
    DANE_A_ELECTORAL,ALIAS,norm,color,RAMPA,conSerie,avisarSinMatch,BASE};
})();
