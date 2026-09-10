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
    return norm(partido).replace(/^COALICION\s+/, '').split(/\s*[-+\/|]\s*|\s+Y\s+/).map(p => p.trim()).filter(p => p.length >= 4);
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

  global.PartidosBloques = { BLOQUE_LABEL, BLOQUE_ORDER, PARTIDO_BLOQUE, CAND_BLOQUE_OVERRIDE, bloqueDePartido, partesDeCoalicion, bloqueDeCandidatura, norm };
})(typeof window !== 'undefined' ? window : globalThis);
