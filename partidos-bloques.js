/* ═══════════════════════════════════════════════════════════════════════════
   PARTIDOS → BLOQUE IDEOLÓGICO · diccionario compartido
   ───────────────────────────────────────────────────────────────────────────
   Extraído TAL CUAL de alcaldias-2023.html (sep-2026), donde nació curado a
   mano sobre la filiación nacional 2022-2026, con overrides por candidato para
   los ~80 alcaldes que corrieron por coaliciones o MSC. Vive aparte para que
   candidato-360 (reparto de la meta en un salto de corporación) use el MISMO
   criterio que el mapa de alcaldías: dos diccionarios distintos serían dos
   opiniones distintas sobre el mismo partido.

   Es una heurística defendible, no una verdad: por eso `sc` (sin clasificar)
   existe y se pinta gris, y por eso el reparto de candidato-360 lo usa solo
   como RESPALDO cuando la huella real del partido no alcanza.

   ⚠️ alcaldias-2023.html todavía tiene su copia inline. Al tocar este archivo
   hay que tocar la de allá — o, mejor, hacer que allá lo cargue de acá.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';
  const BLOQUE_LABEL = { izq: 'Izquierda', ci: 'Centro-izquierda', c: 'Centro', cd: 'Centro-derecha', d: 'Derecha', sc: 'Sin línea nacional' };
  const BLOQUE_ORDER = ['izq', 'ci', 'c', 'cd', 'd', 'sc'];
  const norm = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().replace(/\s+/g, ' ').trim();

  const PARTIDO_BLOQUE = {
  // izquierda
  'PACTO HISTORICO': 'izq',
  'PACTO HISTORICO BOGOTA': 'izq',
  'PACTO HISTORICO COLOMBIA PUEDE': 'izq',
  'COLOMBIA HUMANA-PACTO HISTORICO': 'izq',
  'MOVIMIENTO POLITICO COLOMBIA HUMANA': 'izq',
  'PARTIDO POLO DEMOCRATICO ALTERNATIVO': 'izq',
  'UNION PATRIOTICA': 'izq',
  'PARTIDO COMUNES': 'izq',
  'PARTIDO POLITICO LA FUERZA DE LA PAZ': 'izq',
  'MOVIMIENTO POLITICO FUERZA CIUDADANA': 'izq',
  'MOVIMIENTO ALIANZA DEMOCRATICA AMPLIA': 'izq',
  // centro-izquierda
  'PARTIDO ALIANZA VERDE': 'ci',
  'PARTIDO NUEVO LIBERALISMO': 'ci',
  'PARTIDO VERDE OXIGENO': 'ci',
  'AGRUPACION POLITICA EN MARCHA': 'ci',
  'PARTIDO COLOMBIA RENACIENTE': 'ci',
  'PARTIDO POLITICO ESPERANZA DEMOCRATICA': 'ci',
  'PARTIDO POLITICO DIGNIDAD & COMPROMISO': 'ci',
  // centro
  'PARTIDO LIBERAL COLOMBIANO': 'c',
  'PARTIDO DE LA UNION POR LA GENTE - PARTIDO DE LA U': 'c',
  'PARTIDO DE LA U': 'c',
  'PARTIDO DEMOCRATA COLOMBIANO': 'c',
  'PARTIDO POLITICO GENTE EN MOVIMIENTO': 'c',
  'PARTIDO ECOLOGISTA COLOMBIANO': 'c',
  // centro-derecha
  'PARTIDO CAMBIO RADICAL': 'cd',
  'PARTIDO CONSERVADOR COLOMBIANO': 'cd',
  'PARTIDO LIGA GOBERNANTES ANTICORRUPCION - LIGA': 'cd',
  'MOVIMIENTO SALVACION NACIONAL': 'cd',
  'MOVIMIENTO  SALVACION NACIONAL': 'cd',
  // derecha
  'PARTIDO CENTRO DEMOCRATICO': 'd',
  'PARTIDO POLITICO CREEMOS': 'd',
  'NUEVA FUERZA DEMOCRATICA': 'd',
  // partidos que faltaban y que aparecen sobre todo dentro de coaliciones
  'PARTIDO POLITICO MIRA': 'cd',           // conservadurismo social, sin adscripción de gobierno
  'PARTIDO COLOMBIA JUSTA LIBRES': 'd',    // confesional evangélico
  'PARTIDO UNITARIO': 'c',
  /* Étnicos e indígenas. Estaban en `sc` por convención («no encajan en el eje
     izquierda-derecha nacional») y ahora se clasifican por la identidad del
     PARTIDO —su origen y su bancada—, no por sus avales: MAIS nació del
     movimiento indígena y su bancada vota con la izquierda; AICO y la ASI
     vienen del mismo tronco alternativo y se comportan como centro-izquierda.
     Ojo con la letra pequeña, que está medida y no se borra: los tres prestan
     su aval, así que en un territorio concreto sus candidatos pueden venir de
     cualquier familia (ver AVAL_AMPLIO). La ficha lo dice cuando pesan. */
  'MOVIMIENTO ALTERNATIVO INDIGENA Y SOCIAL "MAIS"': 'izq',
  'MOVIMIENTO AUTORIDADES INDIGENAS DE COLOMBIA "AICO"': 'ci',
  'PARTIDO ALIANZA SOCIAL INDEPENDIENTE "ASI"': 'ci',
};

  /* ── Movimientos y coaliciones REGIONALES ──────────────────────────────────
     No están en ninguna tabla nacional y su nombre no dice nada: «Córdoba
     Florece», «Renace», «Antioquia te pertenece». El bloque no se adivina, se
     MIDE: se toman los candidatos que se lanzaron con ese aval en 2023 y se
     mira con qué partidos —ya clasificados— se han lanzado esas mismas
     personas en las otras nueve elecciones del índice. Entra a la tabla la
     organización en la que al menos 5 personas dejan rastro y 6 de cada 10
     apuntan al mismo bloque. El método y la tabla completa:
     tools/candidato-360/partidos/clasificar-locales.mjs                      */
  const MOVIMIENTO_LOCAL = {
    'CORDOBA FLORECE': 'c',                       // 109.850 votos · 60 % de 5 personas
    'RENACE': 'izq',                              //  61.353 votos · 77 % de 13
    'COALICION ANTIOQUIA TE PERTENECE': 'cd',     //  29.497 votos · 73 % de 11
    'INDEPENDIENTES CON UNIDAD': 'c',             //  26.471 votos · 67 % de 6
    'COALICION POR CASANARE': 'ci',               //  33.785 votos · 71 % de 7
  };
  /* ── Avales amplios ───────────────────────────────────────────────────────
     Estos prestan su aval a cualquiera, y eso no es una opinión: de las 848
     personas con rastro que se lanzaron con la ASI en 2023, el bloque más
     repetido entre sus OTRAS candidaturas reúne apenas el 35 % —MAIS 31 %,
     AICO 34 %, «Independientes» 30 %—, es decir, sus candidatos vienen
     repartidos de todas las familias. El partido tiene línea (arriba); la
     lista que lleva su aval en un municipio puede no tenerla, y la ficha del
     electorado lo advierte cuando uno de estos pesa en el territorio.
     «Independientes» no es una organización sino la etiqueta de los resultados
     para lo que no es partido: esa se queda sin bloque. */
  const AVAL_AMPLIO = ['ALIANZA SOCIAL INDEPENDIENTE', 'MAIS', 'AICO', 'AUTORIDADES INDIGENAS', 'INDEPENDIENTES'];

  const CAND_BLOQUE_OVERRIDE = [
  // izquierda
  ['KRASNOV', 'izq'],                     // Tunja
  // centro-izquierda
  ['CARLOS FERNANDO GALAN', 'ci'],        // Bogotá (Nuevo Liberalismo)
  ['ALVARO ALEJANDRO EDER', 'ci'],        // Cali (Revivamos Cali)
  ['JOHANA XIMENA ARANDA', 'ci'],         // Ibagué (Ibagué Para Todos · apoyo Pacto)
  ['MARLON MONSALVE', 'ci'],              // Florencia (Nuevo Liberalismo + En Marcha)
  ['RAFAEL ANDRES BOLANOS', 'ci'],        // Quibdó (Alianza Verde)
  ['JAIME ARIEL RODRIGUEZ', 'ci'],        // Puerto Carreño (Alianza Verde)
  ['WILLY ALEJANDRO RODRIGUEZ', 'ci'],    // San José Guaviare (Nuevo Liberalismo)
  ['ELQUIN JADRIAN UNI', 'ci'],           // Leticia (Colombia Renaciente)
  ['MARCO ALIRIO PORRAS', 'ci'],          // Mitú (ASI indígena)
  // centro
  ['JUAN CARLOS MUNOZ BRAVO', 'c'],       // Popayán
  ['NICOLAS MARTIN TORO', 'c'],           // Pasto (Alianza Ciudadana)
  ['HUGO FERNANDO KERGUELEN', 'c'],       // Montería (Una Sola Montería)
  ['JAMES PADILLA', 'c'],                 // Armenia (Armenia Con Más Oportunidades)
  ['GERMAN CASAGUA', 'c'],                // Neiva (Acciones por Neiva)
  ['MARCO TULIO RUIZ', 'c'],              // Yopal (Cambio Radical · perfil técnico c)
  ['CARLOS HUGO PIEDRAHITA', 'c'],        // Mocoa (Alianza Ciudadana por Mocoa)
  ['ARTURO ALEXANDER SANCHEZ', 'c'],      // Inírida (Una Nueva Historia)
  ['ERNESTO MIGUEL OROZCO', 'c'],         // Valledupar (Arreglemos Esto)
  ['GENARO DAVID REDONDO', 'c'],          // Riohacha (Genaro)
  // centro-derecha
  ['DUMEK JOSE TURBAY', 'cd'],            // Cartagena (Unidos para Avanzar · Conservadores)
  ['JORGE ENRIQUE ACEVEDO', 'cd'],        // Cúcuta (Todos por Cúcuta)
  ['ALEXANDER BAQUERO', 'cd'],            // Villavicencio (Recuperemos Villavo)
  ['MAURICIO SALAZAR', 'cd'],             // Pereira (Primero Pereira)
  ['JORGE EDUARDO ROJAS', 'cd'],          // Manizales (Rojas)
  ['YAHIR FERNANDO ACUNA', 'cd'],         // Sincelejo (de la U + Acuña)
  ['CARLOS ALBERTO PINEDO', 'cd'],        // Santa Marta (Santa Marta Sí Puede)
  // derecha
  ['FEDERICO ANDRES GUTIERREZ', 'd'],     // Medellín (Creemos)
  ['JAIME ANDRES BELTRAN', 'd'],          // Bucaramanga (Defendamos · evangélico)
  ['JUAN ALFREDO QUENZA', 'd'],           // Arauca (Nueva Fuerza Democrática)
];

  /* Un partido → su bloque. Acepta el nombre como venga (mayúsculas, tildes,
     espacios dobles). Devuelve 'sc' si no está en la lista. */
  /* Las palabras que NO identifican a nadie: «PARTIDO», «MOVIMIENTO», «DE»…
     Quitarlas deja el núcleo, que es lo que de verdad nombra a la
     organización: «PARTIDO CAMBIO RADICAL» y «CAMBIO RADICAL» son la misma. */
  const ESTRUCTURALES = new Set(['PARTIDO', 'PARTIDOS', 'MOVIMIENTO', 'POLITICO', 'POLITICA', 'COALICION', 'ACUERDO', 'DE', 'DEL', 'LA', 'EL', 'LOS', 'LAS', 'Y', 'POR', 'EN', 'SU']);
  /* Y las que identifican a demasiados: con «COLOMBIA» sola no se resuelve
     nada, y sin esta guarda «COLOMBIA JUSTA LIBRES» calzaría con «PARTIDO
     LIBERAL COLOMBIANO». */
  const GENERICAS = new Set(['COLOMBIA', 'COLOMBIANO', 'COLOMBIANA', 'NACIONAL', 'ALIANZA', 'UNIDOS', 'PUEBLO', 'CIUDADANOS', 'POPULAR', 'SOCIAL']);
  function nucleo(nombre) { return norm(nombre).split(/[^A-ZÑ0-9]+/).filter(w => w && !ESTRUCTURALES.has(w)); }
  function bloqueDePartido(partido) {
    const n = norm(partido).replace(/\s+/g, ' ');
    if (PARTIDO_BLOQUE[n]) return PARTIDO_BLOQUE[n];
    const llave = Object.keys(PARTIDO_BLOQUE).find(k => norm(k).replace(/\s+/g, ' ') === n);
    if (llave) return PARTIDO_BLOQUE[llave];
    /* Coincidencia por contenido: "PARTIDO ALIANZA VERDE" dentro de
       "PARTIDO ALIANZA VERDE - EN MARCHA". */
    const parcial = Object.keys(PARTIDO_BLOQUE).find(k => { const kk = norm(k); return kk.length > 8 && n.includes(kk); });
    if (parcial) return PARTIDO_BLOQUE[parcial];
    /* Por núcleo, en los dos sentidos. Sin esto «CAMBIO RADICAL - MIRA» no
       resolvía ninguna de sus dos partes —la tabla las tiene con el «PARTIDO»
       delante— y media coalición del país se quedaba sin bloque. Se exige una
       palabra propia (ni estructural ni genérica) para no casar por «Colombia».
       Sin espacios además, que «PACTOHISTORICO» existe en los resultados. */
    const nn = nucleo(partido); if (!nn.length) return 'sc';
    const sinEspacios = nn.join('');
    let mejor = null;
    for (const k of Object.keys(PARTIDO_BLOQUE)) {
      const kk = nucleo(k); if (!kk.length) continue;
      const igual = kk.length === nn.length && kk.every(w => nn.includes(w));
      const contenido = kk.every(w => nn.includes(w)) || nn.every(w => kk.includes(w));
      const pegado = !contenido && kk.join('') === sinEspacios;
      if (!contenido && !pegado) continue;
      const comun = kk.filter(w => nn.includes(w));
      /* Con el núcleo igual basta («MIRA» es el Partido MIRA). Si uno está
         CONTENIDO en el otro hay que exigir más: «MOVIMIENTO NUEVO Y
         DESCONOCIDO» no puede volverse Nuevo Liberalismo por la palabra
         «nuevo». Se pide una palabra larga y propia —«RENACIENTE»,
         «LIBERAL»— o dos palabras en común. */
      const propio = igual || pegado
        ? kk.some(w => w.length >= 4 && !GENERICAS.has(w))
        : comun.filter(w => !GENERICAS.has(w)).length >= 2 || comun.some(w => w.length >= 6 && !GENERICAS.has(w));
      if (!propio) continue;
      const distancia = Math.abs(kk.length - nn.length);
      if (!mejor || distancia < mejor.distancia) mejor = { bloque: PARTIDO_BLOQUE[k], distancia };
    }
    return mejor ? mejor.bloque : 'sc';
  }
  /* El bloque de una ORGANIZACIÓN tal como aparece en unos resultados: puede
     ser un partido, una coalición de varios o un movimiento regional. Es lo
     que se usa para leer un territorio; `bloqueDePartido` sigue siendo la
     pregunta simple por un partido. */
  function bloqueDeOrganizacion(nombre) {
    const directo = bloqueDePartido(nombre);
    if (directo !== 'sc') return directo;
    const local = MOVIMIENTO_LOCAL[norm(nombre).replace(/[^A-ZÑ0-9 ]/g, '').replace(/\s+/g, ' ').trim()];
    if (local) return local;
    /* Una coalición vale lo que valen sus partes: el bloque más repetido. */
    const bloques = partesDeCoalicion(nombre).map(bloqueDePartido).filter(b => b !== 'sc');
    if (!bloques.length) return 'sc';
    const cuenta = {}; bloques.forEach(b => { cuenta[b] = (cuenta[b] || 0) + 1; });
    return Object.entries(cuenta).sort((a, b) => b[1] - a[1])[0][0];
  }
  /* Un aval amplio tiene línea como partido, pero la presta: quien quiera leer
     el territorio con cuidado necesita saberlo. */
  function esAvalAmplio(nombre) { const n = norm(nombre); return AVAL_AMPLIO.some(a => n.includes(a)); }
  /* Una coalición es varios partidos en un solo nombre: "NUEVO LIBERALISMO -
     AGRUPACION POLITICA EN MARCHA". Se parte por los separadores usuales y se
     devuelven las partes que tienen sentido como partido. */
  function partesDeCoalicion(partido) {
    return norm(partido).replace(/^COALICION\s+/, '').replace(/^PARTIDOS\s+/, '').split(/\s*[-+\/|,]\s*|\s+Y\s+/).map(p => p.trim()).filter(p => p.length >= 4);
  }
  /* El bloque de una candidatura: el de su partido o, en coalición, el bloque
     más repetido entre sus partes (empate → la primera parte). */
  function bloqueDeCandidatura(partido, nombreCandidato) {
    const nom = norm(nombreCandidato);
    for (const [pat, bl] of CAND_BLOQUE_OVERRIDE) if (nom && nom.includes(norm(pat))) return bl;
    const partes = partesDeCoalicion(partido);
    const bloques = partes.map(bloqueDePartido).filter(b => b !== 'sc');
    if (!bloques.length) return bloqueDePartido(partido);
    const cuenta = {}; bloques.forEach(b => { cuenta[b] = (cuenta[b] || 0) + 1; });
    return bloques.slice().sort((a, b) => cuenta[b] - cuenta[a])[0];
  }

  /* ═══ COLOR DEL PARTIDO ══════════════════════════════════════════════════
     El mapa del CRM pinta la votación con una rampa de un solo tono, de claro
     a oscuro (que es como se codifica una MAGNITUD). Lo que cambia acá es el
     tono: el del partido con el que la persona se lanza, para que su mapa se
     vea suyo y no siempre verde.

     Los valores salen de las paletas que ya usaban resultados-concejo-2023 y
     alcaldias-2023, con cuatro correcciones pedidas en sep-2026:
       · el Pacto pasa de rojo a PÚRPURA — en rojo chocaba con el Liberal, y
         de los dos que se propusieron (amarillo o púrpura) el púrpura hace
         mejor rampa: el amarillo casi no tiene recorrido hacia lo oscuro;
       · Centro Democrático a azul claro y Salvación Nacional a azul cielo,
         para que los tres azules (con el Conservador) se distingan.

     Un partido sin color propio hereda el de su BLOQUE ideológico: es
     información de verdad, no un tono inventado por una función de hash. */
  const PARTIDO_COLOR = {
    'PARTIDO LIBERAL COLOMBIANO': '#C81E1E',
    'PARTIDO CONSERVADOR COLOMBIANO': '#1D4ED8',
    'PARTIDO CENTRO DEMOCRATICO': '#3B82F6',
    'MOVIMIENTO SALVACION NACIONAL': '#0EA5E9',
    'PACTO HISTORICO': '#7C3AED',
    'MOVIMIENTO POLITICO PACTO HISTORICO': '#7C3AED',
    'PACTO HISTORICO BOGOTA': '#7C3AED',
    'PACTO HISTORICO COLOMBIA PUEDE': '#7C3AED',
    'COLOMBIA HUMANA-PACTO HISTORICO': '#7C3AED',
    'MOVIMIENTO POLITICO COLOMBIA HUMANA': '#7C3AED',
    'PARTIDO ALIANZA VERDE': '#16A34A',
    'PARTIDO CAMBIO RADICAL': '#D5194E',
    'PARTIDO DE LA UNION POR LA GENTE - PARTIDO DE LA U': '#EA580C',
    'PARTIDO DE LA U': '#EA580C',
    'PARTIDO NUEVO LIBERALISMO': '#B45309',
    'NUEVO LIBERALISMO EN MARCHA': '#B45309',
    'AGRUPACION POLITICA EN MARCHA': '#0891B2',
    'PARTIDO POLITICO MIRA': '#0F766E',
    'PARTIDO POLO DEMOCRATICO ALTERNATIVO': '#CA8A04',
    'PARTIDO POLITICO DIGNIDAD & COMPROMISO': '#A16207',
    'PARTIDO POLITICO DIGNIDAD Y COMPROMISO': '#A16207',
    'PARTIDO POLITICO CREEMOS': '#1866DF',
    'MOVIMIENTO POLITICO FUERZA CIUDADANA': '#9333EA',
    'PARTIDO POLITICO LA FUERZA DE LA PAZ': '#65A30D',
    'PARTIDO VERDE OXIGENO': '#0D9488',
    'PARTIDO COLOMBIA RENACIENTE': '#059669',
    'PARTIDO COLOMBIA JUSTA LIBRES': '#7E22CE',
    'PARTIDO POLITICO GENTE EN MOVIMIENTO': '#DB2777',
    'PARTIDO DEMOCRATA COLOMBIANO': '#0E7490',
    'PARTIDO POLITICO ESPERANZA DEMOCRATICA': '#B45309',
    'PARTIDO ECOLOGISTA COLOMBIANO': '#4D7C0F',
    'PARTIDO LIGA GOBERNANTES ANTICORRUPCION - LIGA': '#BE123C',
    'MOVIMIENTO ALTERNATIVO INDIGENA Y SOCIAL "MAIS"': '#C2410C',
    'MOVIMIENTO AUTORIDADES INDIGENAS DE COLOMBIA "AICO"': '#A16207',
    'MOVIMIENTO ALIANZA DEMOCRATICA AMPLIA': '#7C3AED',
    'NUEVA FUERZA DEMOCRATICA': '#4F46E5',
    'PARTIDO COMUNES': '#B91C1C',
    'UNION PATRIOTICA': '#B91C1C',
    /* Formas cortas: en las coaliciones el partido casi nunca viene con su
       nombre legal completo («CAMBIO RADICAL - MIRA», no «PARTIDO CAMBIO
       RADICAL - PARTIDO POLITICO MIRA»). */
    'LIBERAL COLOMBIANO': '#C81E1E',
    'CONSERVADOR COLOMBIANO': '#1D4ED8',
    'PARTIDO CONSERVADOR': '#1D4ED8',
    'CENTRO DEMOCRATICO': '#3B82F6',
    'SALVACION NACIONAL': '#0EA5E9',
    'ALIANZA VERDE': '#16A34A',
    'CAMBIO RADICAL': '#D5194E',
    'NUEVO LIBERALISMO': '#B45309',
    'MIRA': '#0F766E',
    'COLOMBIA JUSTA LIBRES': '#7E22CE',
    'POLO DEMOCRATICO ALTERNATIVO': '#CA8A04',
  };
  /* El color de cada bloque, para quien no tiene color propio. */
  const BLOQUE_COLOR = { izq: '#B91C1C', ci: '#0D9488', c: '#7C3AED', cd: '#2563EB', d: '#1E40AF', sc: '#3E8A5B' };

  /* La rampa se calcula en OKLab, no mezclando con blanco en sRGB: mezclar en
     sRGB apaga el tono y los pasos claros salen grises. Acá se conserva el
     tono, se fija la CLARIDAD de cada paso y el croma se baja en los claros
     (un color muy claro no puede ser muy saturado sin salirse del gamut). */
  /* Cuatro pasos (los mismos cortes que ya tenía el mapa) más el gris de «sin
     votos». Las claridades y el croma están elegidos para que ningún par
     consecutivo baje de ΔE 8 en OKLab y para que el paso más claro no se
     confunda con ese gris: lo comprueba prueba-colores.mjs. */
  const L_PASOS = [0.86, 0.725, 0.575, 0.415];
  const C_PASOS = [0.55, 0.85, 1.00, 0.88];
  const SIN_VOTOS = '#eef0ea';
  const srgb = v => v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  const gamma = v => v <= 0.0031308 ? 12.92 * v : 1.055 * Math.pow(v, 1 / 2.4) - 0.055;
  function hexALineal(hex) {
    const h = String(hex || '').replace('#', '');
    const n = h.length === 3 ? h.split('').map(c => c + c).join('') : h;
    return [0, 2, 4].map(i => srgb(parseInt(n.slice(i, i + 2), 16) / 255));
  }
  function aOklab([r, g, b]) {
    const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
    const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
    const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
    return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s, 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s, 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
  }
  function deOklab([L, a, b]) {
    const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
    const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
    const s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3;
    return [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s, -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s];
  }
  const aHex = lin => '#' + lin.map(v => Math.round(Math.min(1, Math.max(0, gamma(Math.min(1, Math.max(0, v))))) * 255).toString(16).padStart(2, '0')).join('');
  /* Baja el croma hasta que el color quepa en sRGB: sin esto, un tono vivo a
     claridad alta se recorta y el paso pierde el tono. */
  function enGamut(L, C, h) {
    for (let c = C; c > 0.0005; c -= 0.004) {
      const lin = deOklab([L, c * Math.cos(h), c * Math.sin(h)]);
      if (lin.every(v => v >= -0.001 && v <= 1.001)) return aHex(lin);
    }
    return aHex(deOklab([L, 0, 0]));
  }
  function rampaDeColor(base) {
    const [L, a, b] = aOklab(hexALineal(base));
    const C = Math.hypot(a, b), h = Math.atan2(b, a);
    return L_PASOS.map((paso, i) => enGamut(paso, Math.max(C, 0.06) * C_PASOS[i], h));
  }
  /* El color propio del partido, el de su bloque, o nada. */
  function colorDePartido(partido, nombreCandidato) {
    const n = norm(partido);
    if (!n) return '';
    if (PARTIDO_COLOR[n]) return PARTIDO_COLOR[n];
    for (const parte of partesDeCoalicion(partido)) if (PARTIDO_COLOR[norm(parte)]) return PARTIDO_COLOR[norm(parte)];
    const bloque = bloqueDeCandidatura(partido, nombreCandidato || '');
    return BLOQUE_COLOR[bloque] || '';
  }
  function rampaDePartido(partido, nombreCandidato) {
    const base = colorDePartido(partido, nombreCandidato);
    return base ? rampaDeColor(base) : null;
  }

  global.PartidosBloques = { BLOQUE_LABEL, BLOQUE_ORDER, PARTIDO_BLOQUE, CAND_BLOQUE_OVERRIDE, PARTIDO_COLOR, BLOQUE_COLOR, SIN_VOTOS, L_PASOS, MOVIMIENTO_LOCAL, bloqueDePartido, bloqueDeOrganizacion, esAvalAmplio, partesDeCoalicion, bloqueDeCandidatura, colorDePartido, rampaDeColor, rampaDePartido, norm };
})(typeof window !== 'undefined' ? window : globalThis);
