/*
 * lab-indicadores.js — Sprint E del Lab de Políticas Públicas y Prospectiva.
 *
 * Helper compartido que provee indicadores municipales oficiales a los
 * módulos del lab. Fuente Fase A: datos.gov.co (Socrata) procesados por
 * tools/build-indicadores-mun/build.py → S3.
 *
 * Cobertura Fase A (8 indicadores, 1108 municipios, panel 2018-2024):
 *   · Seguridad — homicidios, hurto_personas, hurto_vehiculos,
 *     violencia_intrafamiliar, delitos_sexuales (Policía Nacional, DIVIPOLA)
 *   · Educación — cobertura_neta, desercion, matricula_5_16 (MEN, ETC→DIVIPOLA)
 *
 * Carga lazy: el JSON (~980 KB plain, ~150 KB gzip) se baja al primer
 * uso y se cachea en memoria por sesión. Refresca con bumpear ?v=.
 *
 * API pública en window.LabIndicadores:
 *   load()                            → Promise<state>
 *   isLoaded()                        → bool
 *   getCatalog()                      → [{id,nombre,unidad,categoria,fuente,panel}]
 *   getMun(divipola)                  → { nombre, depto, cod_depto, datos } | null
 *   getMunsByDepto(codDepto)          → [{divipola, nombre, ...}]
 *   getValue(divipola, indicadorId, year)  → { value, isProxy, source } | null
 *   getLatestValue(divipola, indicadorId)  → { value, year, isProxy, source } | null
 *   getSerie(divipola, indicadorId)   → { values:{year:v,...}, isProxy, source }
 *   findIndicador(keyword)            → [{id, nombre, ...}]   match por keyword
 *   getDeptosCatalog()                → [{cod, nombre}]   33 deptos ordenados alfabéticamente
 *
 * NOTA: los códigos son DIVIPOLA DANE de 5 chars con zfill ('05001', no '5001').
 * El depto se infiere de los 2 primeros chars del DIVIPOLA municipal.
 */
(function() {
  'use strict';

  const URL = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/bases+de+datos/indicadores-mun/indicadores-mun.json';
  const CACHE_BUSTER = 'v=20260526';  // Bumpear cuando se regeneren los datos

  let _state = null;
  let _loadingPromise = null;

  // ── Carga lazy ──────────────────────────────────────────────────────────
  function load() {
    if (_state) return Promise.resolve(_state);
    if (_loadingPromise) return _loadingPromise;
    _loadingPromise = fetch(URL + '?' + CACHE_BUSTER)
      .then(r => {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(data => {
        _state = data;
        _loadingPromise = null;
        return _state;
      })
      .catch(e => {
        _loadingPromise = null;
        console.error('lab-indicadores: no se pudo cargar', e);
        throw e;
      });
    return _loadingPromise;
  }
  function isLoaded() { return _state !== null; }

  // ── Catálogo de indicadores ─────────────────────────────────────────────
  function getCatalog() {
    if (!_state) return [];
    return _state.indicadores || [];
  }

  function findIndicador(keyword) {
    if (!_state || !keyword) return [];
    const kw = _norm(keyword);
    return (_state.indicadores || []).filter(i =>
      _norm(i.id).includes(kw) ||
      _norm(i.nombre).includes(kw) ||
      _norm(i.categoria).includes(kw)
    );
  }

  // ── Datos por municipio ─────────────────────────────────────────────────
  function _padDivipola(v) {
    return String(v == null ? '' : v).padStart(5, '0');
  }
  function _padDepto(v) {
    return String(v == null ? '' : v).padStart(2, '0');
  }

  function getMun(divipola) {
    if (!_state || !divipola) return null;
    const code = _padDivipola(divipola);
    return (_state.muns && _state.muns[code]) || null;
  }

  function getMunsByDepto(codDepto) {
    if (!_state || codDepto == null) return [];
    const dep = _padDepto(codDepto);
    const muns = _state.muns || {};
    const out = [];
    for (const code in muns) {
      if (code.slice(0, 2) === dep) {
        out.push({ divipola: code, ...muns[code] });
      }
    }
    out.sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
    return out;
  }

  function getValue(divipola, indicadorId, year) {
    const mun = getMun(divipola);
    if (!mun || !indicadorId || year == null) return null;
    const serie = mun.datos[indicadorId];
    if (!serie) return null;
    const v = serie[String(year)];
    if (v == null) return null;
    const isProxy = !!(mun.datos._meta && mun.datos._meta[indicadorId]);
    const indMeta = (_state.indicadores || []).find(i => i.id === indicadorId);
    return {
      value: v,
      year: parseInt(year, 10),
      isProxy,
      source: indMeta ? { fuente: indMeta.fuente, url: indMeta.fuente_url } : null,
      proxyNote: isProxy ? mun.datos._meta[indicadorId] : null
    };
  }

  function getLatestValue(divipola, indicadorId) {
    const mun = getMun(divipola);
    if (!mun || !indicadorId) return null;
    const serie = mun.datos[indicadorId];
    if (!serie) return null;
    const years = Object.keys(serie).map(y => parseInt(y, 10)).sort((a, b) => b - a);
    if (years.length === 0) return null;
    return getValue(divipola, indicadorId, years[0]);
  }

  function getSerie(divipola, indicadorId) {
    const mun = getMun(divipola);
    if (!mun || !indicadorId) return null;
    const serie = mun.datos[indicadorId];
    if (!serie) return null;
    const isProxy = !!(mun.datos._meta && mun.datos._meta[indicadorId]);
    const indMeta = (_state.indicadores || []).find(i => i.id === indicadorId);
    return {
      values: { ...serie },
      isProxy,
      source: indMeta ? { fuente: indMeta.fuente, url: indMeta.fuente_url } : null,
      proxyNote: isProxy ? mun.datos._meta[indicadorId] : null,
      indicador: indMeta || null
    };
  }

  // ── Catálogo de departamentos ───────────────────────────────────────────
  function getDeptosCatalog() {
    if (!_state) return [];
    const seen = {};
    for (const code in _state.muns) {
      const m = _state.muns[code];
      const dep = m.cod_depto;
      if (!seen[dep]) seen[dep] = m.depto;
    }
    const out = Object.keys(seen).map(cod => ({ cod, nombre: seen[cod] }));
    out.sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
    return out;
  }

  // ── Búsqueda municipio por nombre ───────────────────────────────────────
  function searchMun(query, codDepto) {
    if (!_state || !query) return [];
    const q = _norm(query);
    const filter = codDepto ? _padDepto(codDepto) : null;
    const out = [];
    for (const code in _state.muns) {
      if (filter && code.slice(0, 2) !== filter) continue;
      const m = _state.muns[code];
      if (_norm(m.nombre).startsWith(q)) {
        out.push({ divipola: code, ...m });
      }
    }
    out.sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
    return out.slice(0, 30);
  }

  // ── Helpers de display ──────────────────────────────────────────────────
  function _norm(s) {
    return String(s == null ? '' : s).toUpperCase()
      .normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/[.,()]/g, '').trim();
  }

  function formatValue(value, indicadorId) {
    if (value == null) return '—';
    const ind = (_state?.indicadores || []).find(i => i.id === indicadorId);
    const unidad = ind?.unidad || '';
    // Porcentajes
    if (unidad === '%') return Number(value).toFixed(1) + '%';
    // Conteos grandes — formatear con separador de miles
    if (typeof value === 'number' && value >= 1000) return value.toLocaleString('es-CO');
    return String(value);
  }

  // ── Match keyword → indicador (para chips DATO en módulos) ──────────────
  // Mapeo simple: si el nombre de una variable del usuario contiene la keyword,
  // devuelve el indicador match. Usado por analisis-estructural y problema-publico.
  const KEYWORDS = {
    'homicidio':         'homicidios',
    'asesinato':         'homicidios',
    'inseguridad':       'homicidios',
    'criminalidad':      'homicidios',
    'hurto':             'hurto_personas',
    'robo':              'hurto_personas',
    'asalto':            'hurto_personas',
    'vehiculo':          'hurto_vehiculos',
    'auto':              'hurto_vehiculos',
    'violencia familiar':'violencia_intrafamiliar',
    'violencia domestic':'violencia_intrafamiliar',
    'vif':               'violencia_intrafamiliar',
    'maltrato':          'violencia_intrafamiliar',
    'abuso sexual':      'delitos_sexuales',
    'violencia sexual':  'delitos_sexuales',
    'agresion sexual':   'delitos_sexuales',
    'cobertura escolar': 'cobertura_neta',
    'cobertura educa':   'cobertura_neta',
    'educacion':         'cobertura_neta',
    'matricula':         'matricula_5_16',
    'estudiantes':       'matricula_5_16',
    'desercion':         'desercion',
    'abandono escolar':  'desercion'
  };
  function matchIndicadorByKeyword(text) {
    if (!text) return null;
    const norm = _norm(text);
    for (const kw in KEYWORDS) {
      if (norm.includes(_norm(kw))) return KEYWORDS[kw];
    }
    return null;
  }

  // Exponer API
  window.LabIndicadores = {
    load, isLoaded,
    getCatalog, findIndicador, matchIndicadorByKeyword,
    getMun, getMunsByDepto, searchMun,
    getValue, getLatestValue, getSerie,
    getDeptosCatalog,
    formatValue,
    _state: () => _state  // debug helper
  };

})();
