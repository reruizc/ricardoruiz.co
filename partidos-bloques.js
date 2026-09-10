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
  const BLOQUE_LABEL = { izq: 'Izquierda', ci: 'Centro-izquierda', c: 'Centro', cd: 'Centro-derecha', d: 'Derecha', sc: 'Sin clasificar' };
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
  // étnicos/indígenas: por convención sc (no encaja en eje izq-der nacional)
  'MOVIMIENTO ALTERNATIVO INDIGENA Y SOCIAL "MAIS"': 'sc',
  'MOVIMIENTO AUTORIDADES INDIGENAS DE COLOMBIA "AICO"': 'sc',
  'PARTIDO ALIANZA SOCIAL INDEPENDIENTE "ASI"': 'sc',
};

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
  function bloqueDePartido(partido) {
    const n = norm(partido).replace(/\s+/g, ' ');
    if (PARTIDO_BLOQUE[n]) return PARTIDO_BLOQUE[n];
    const llave = Object.keys(PARTIDO_BLOQUE).find(k => norm(k).replace(/\s+/g, ' ') === n);
    if (llave) return PARTIDO_BLOQUE[llave];
    /* Coincidencia por contenido: "PARTIDO ALIANZA VERDE" dentro de
       "PARTIDO ALIANZA VERDE - EN MARCHA". */
    const parcial = Object.keys(PARTIDO_BLOQUE).find(k => { const kk = norm(k); return kk.length > 8 && n.includes(kk); });
    return parcial ? PARTIDO_BLOQUE[parcial] : 'sc';
  }
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

  global.PartidosBloques = { BLOQUE_LABEL, BLOQUE_ORDER, PARTIDO_BLOQUE, CAND_BLOQUE_OVERRIDE, PARTIDO_COLOR, BLOQUE_COLOR, SIN_VOTOS, L_PASOS, bloqueDePartido, partesDeCoalicion, bloqueDeCandidatura, colorDePartido, rampaDeColor, rampaDePartido, norm };
})(typeof window !== 'undefined' ? window : globalThis);
