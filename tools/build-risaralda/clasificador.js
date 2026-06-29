// tools/build-risaralda/clasificador.js
//
// Clasifica un partido/lista/coalición territorial como ALTERNATIVO o no.
// "Alternativo" = Verde + Pacto Histórico + izquierda histórica
// (Polo, Colombia Humana, Unión Patriótica, MAIS, ADA, Comunes/FARC).
//
// Por qué por NOMBRE y no por COD_PAR: los códigos NO son estables entre
// años (Polo=9 en 2019, Colombia Humana=18 en 2023) y las coaliciones
// locales reciben códigos >=2000 distintos cada elección. El nombre
// normalizado es robusto al año.
//
// Trampas que resuelve la lista de exclusión:
//  - "PARTIDO VERDE OXÍGENO" (Íngrid Betancourt) NO es del bloque alternativo.
//  - "PACTO POR PEREIRA" / "PACTO POR EL BELÉN" son movimientos LOCALES,
//    no el Pacto Histórico.
//  - Coaliciones locales literalmente llamadas "ALTERNATIVOS" no son el bloque.
//  - "PARTIDO ECOLOGISTA COLOMBIANO" es verde de nombre pero no del bloque.

function norm(s){
  return String(s || '').toUpperCase().normalize('NFD')
    .replace(/[̀-ͯ]/g, '').replace(/"+/g, '').replace(/\s+/g, ' ').trim();
}

// Tokens que, si aparecen, EXCLUYEN del bloque alternativo (se evalúan primero).
const EXCLUYE = [
  'VERDE OXIGENO',
  'ECOLOGISTA',
  'PACTO POR',          // movimientos locales "Pacto por X"
  'PACTO PARA',
  'PACTO DE',
];

// Partidos tradicionales / no-alternativos. Si una coalición MIXTA los
// incluye (p.ej. "CONSERVADOR - POLO DEMOCRATICO"), NO cuenta como bloque
// alternativo aunque nombre a un miembro alternativo: el socio tradicional
// es el dominante. Regla conservadora y defendible para un "enfoque
// alternativo" estricto.
const TRADICIONAL = [
  'LIBERAL COLOMBIANO', 'PARTIDO LIBERAL',
  'CONSERVADOR',
  'CAMBIO RADICAL',
  'CENTRO DEMOCRATICO',
  'DE LA U', 'UNION POR LA GENTE', 'SOCIAL DE UNIDAD',
  'COLOMBIA JUSTA LIBRES',
  'PARTIDO POLITICO MIRA', 'POLITICO  MIRA',
  'SALVACION NACIONAL',
];

// Tokens del bloque alternativo nacional. Se evalúan como "contiene".
// Cubren partidos solos y coaliciones que los incluyen como miembro.
const ALT = [
  'ALIANZA VERDE',
  'PARTIDO VERDE',                  // registro histórico del Verde
  'PACTO HISTORICO',
  'POLO DEMOCRATICO',
  'COLOMBIA HUMANA',
  'UNION PATRIOTICA',
  'ALTERNATIVO INDIGENA Y SOCIAL',  // MAIS
  'MAIS',
  'ALIANZA DEMOCRATICA AMPLIA',     // ADA (Pacto)
  'FUERZA ALTERNATIVA REVOLUCIONARIA', // Comunes / FARC
  'PARTIDO COMUNES',
  'UNIDAD DE IZQUIERDA',
];

// Coaliciones locales (>=2000) suelen mezclar miembros. Sólo se clasifican
// como alternativas si nombran EXPLÍCITAMENTE un miembro del bloque y no
// caen en EXCLUYE. "MAIS" como token suelto es ambiguo en coaliciones
// (suele ir con indígenas), así que en coaliciones exigimos un token fuerte.
const ALT_COALICION = [
  'ALIANZA VERDE', 'PACTO HISTORICO', 'POLO DEMOCRATICO',
  'COLOMBIA HUMANA', 'UNION PATRIOTICA', 'ALIANZA DEMOCRATICA AMPLIA',
];

// codpar: string/num del COD_PAR (para distinguir nacional <2000 vs coalición).
function esAlternativo(desPar, codpar){
  const n = norm(desPar);
  if (!n) return false;
  for (const ex of EXCLUYE){ if (n.includes(ex)) return false; }
  // Coalición mixta con un partido tradicional → no es bloque alternativo.
  for (const t of TRADICIONAL){ if (n.includes(t)) return false; }

  const code = parseInt(codpar, 10);
  const esCoalicionLocal = Number.isFinite(code) && code >= 2000;

  if (esCoalicionLocal){
    return ALT_COALICION.some(t => n.includes(t));
  }
  return ALT.some(t => n.includes(t));
}

module.exports = { esAlternativo, norm };
