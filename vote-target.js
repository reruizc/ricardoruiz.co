(function (global) {
  'use strict';

  const CORPORATIONS = {
    jal: {
      label: 'JAL',
      index: 'jal-2023/index-jal-2023.json',
      results: 'jal-2023/resultados-jal-2023.json',
      multiSeat: true,
    },
    concejo: {
      label: 'Concejo',
      index: 'concejo-2023/index-concejo-2023.json',
      results: 'concejo-2023/resultados-concejo-2023.json',
      multiSeat: true,
    },
    asamblea: {
      label: 'Asamblea',
      index: 'asamblea-2023/index-asamblea-2023.json',
      results: 'asamblea-2023/resultados-asamblea-2023.json',
      multiSeat: true,
    },
    alcaldia: {
      label: 'Alcaldía',
      index: 'alcaldia-2023/index-alcaldia-2023.json',
      multiSeat: false,
    },
    gobernacion: {
      label: 'Gobernación',
      index: 'gobernacion-2023/index-gobernacion-2023.json',
      multiSeat: false,
    },
  };

  /* Los cortes verificados prevalecen sobre la reconstrucción matemática del
     preconteo. Se amplía a medida que se incorporen actos de escrutinio. */
  const VERIFIED_CUTOFFS = [
    { corp: 'jal', territory: ['TEUSAQUILLO', 'BOGOTA'], seats: 9, cutoff: 1114 },
  ];

  const cache = new Map();
  const CENSUS_GROWTH_2023_2027 = 0.014;
  const PARTICIPATION_UPLIFT = 0.01;
  const COMPETITIVE_MARGIN = 0.03;

  function normalize(value) {
    return String(value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toUpperCase()
      .replace(/[^A-Z0-9]+/g, ' ')
      .trim();
  }

  function components(territory) {
    const seen = new Set();
    return String(territory || '')
      .split('·')
      .map(normalize)
      .filter(Boolean)
      .filter(value => {
        if (seen.has(value)) return false;
        seen.add(value);
        return true;
      });
  }

  async function json(url) {
    if (!cache.has(url)) {
      cache.set(url, fetch(url).then(response => {
        if (!response.ok) throw new Error(`Fuente electoral no disponible (${response.status})`);
        return response.json();
      }).catch(error => {
        cache.delete(url);
        throw error;
      }));
    }
    return cache.get(url);
  }

  function resolveTerritoryRows(candidates, territory) {
    const wanted = components(territory);
    const primary = wanted[0] || '';
    const grouped = new Map();
    candidates.forEach(candidate => {
      const label = candidate.circunscripcion || '';
      if (!grouped.has(label)) grouped.set(label, []);
      grouped.get(label).push(candidate);
    });

    let best = null;
    grouped.forEach((rows, label) => {
      const key = normalize(label);
      const primaryMatch = !primary || key.includes(primary) || primary.includes(key);
      if (!primaryMatch) return;
      let score = key === normalize(territory) ? 1000 : 100;
      wanted.forEach((part, index) => {
        if (key.includes(part) || part.includes(key)) score += index === 0 ? 80 : 25;
      });
      score -= Math.abs(key.length - normalize(territory).length) / 100;
      if (!best || score > best.score) best = { rows, label, score };
    });
    return best;
  }

  function groupByParty(rows) {
    const parties = new Map();
    rows.forEach(candidate => {
      const name = candidate.partido || 'LISTA SIN NOMBRE';
      if (!parties.has(name)) parties.set(name, []);
      parties.get(name).push(candidate);
    });
    return [...parties.entries()].map(([name, candidates]) => ({
      name,
      candidates: candidates.sort((a, b) => Number(b.votos || 0) - Number(a.votos || 0)),
      votes: candidates.reduce((sum, candidate) => sum + Number(candidate.votos || 0), 0),
    }));
  }

  function inferSeats(parties) {
    return Math.max(0, ...parties.map(party => party.candidates.length));
  }

  /* Art. 263: umbral del 50% del cuociente electoral y cifra repartidora.
     El índice trae una fila por candidato y permite inferir las curules por el
     tamaño máximo de las listas inscritas en cada circunscripción. */
  function reconstructedCutoff(rows) {
    const parties = groupByParty(rows);
    const seats = inferSeats(parties);
    if (seats < 2) {
      const observed = rows.map(candidate => Number(candidate.votos || 0)).filter(votes => votes > 0).sort((a, b) => a - b);
      return observed.length ? { cutoff: observed[0], seats: null, sparse: true } : null;
    }
    const validVotes = parties.reduce((sum, party) => sum + party.votes, 0);
    const threshold = validVotes / seats / 2;
    let eligible = parties.filter(party => party.votes >= threshold);
    if (!eligible.length) eligible = parties;

    const quotients = [];
    eligible.forEach(party => {
      for (let divisor = 1; divisor <= seats; divisor += 1) {
        quotients.push({ party, value: party.votes / divisor });
      }
    });
    quotients.sort((a, b) => b.value - a.value);
    const allocations = new Map();
    quotients.slice(0, seats).forEach(item => {
      allocations.set(item.party.name, (allocations.get(item.party.name) || 0) + 1);
    });

    const elected = [];
    eligible.forEach(party => {
      elected.push(...party.candidates.slice(0, allocations.get(party.name) || 0));
    });
    elected.sort((a, b) => Number(a.votos || 0) - Number(b.votos || 0));
    if (!elected.length) return null;
    /* cifra repartidora = el cociente más bajo que alcanzó curul: lo que una
       LISTA necesita para una curul. Se devuelve todo lo reconstruido porque
       la meta por partido se calcula encima de esto. */
    const cifra = quotients[Math.min(seats, quotients.length) - 1].value;
    return { cutoff: Number(elected[0].votos || 0), seats, validVotes, parties, allocations, cifra, threshold };
  }

  /* ── La meta según el partido ───────────────────────────────────────────
     La última curul de la corporación es un piso engañoso: en Bogotá 2023
     fue la tercera de una lista arrastrada por un candidato de 70.000 votos,
     y entrar por la Alianza Verde costó el doble. Lo que cuesta entrar
     depende de la LISTA con la que se va:
       · si la lista ganó k curules, hay que entrar de k: la meta es lo que
         sacó el k-ésimo de esa lista;
       · si la lista no ganó curul, primero la lista tiene que llegar a la
         cifra repartidora: a quien la encabece le toca poner lo que falte,
         suponiendo que el resto de la lista repita;
       · si el partido no corrió en 2023 en esa corporación, su fuerza se
         estima con la Cámara de 2026 en el departamento, escalada al tamaño
         de la corporación, y de ahí se deduce si arrastraría curul. */
  const ESTRUCTURALES = new Set(['PARTIDO', 'PARTIDOS', 'MOVIMIENTO', 'POLITICO', 'POLITICA', 'COALICION', 'DE', 'DEL', 'LA', 'EL', 'LOS', 'LAS', 'Y']);
  const palabras = s => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/[^A-Z0-9Ñ]+/g, ' ').trim().split(' ').filter(Boolean);
  const nucleo = s => palabras(s).filter(w => !ESTRUCTURALES.has(w));
  function listaDelPartido(parties, partido) {
    const nu = nucleo(partido);
    if (!nu.length) return null;
    const exacto = normalize(partido);
    const candidatas = parties.filter(party => normalize(party.name) === exacto || (() => { const set = new Set(palabras(party.name)); return nu.every(w => set.has(w)); })());
    return candidatas.sort((a, b) => b.votes - a.votes)[0] || null;
  }
  function mediana(xs) { const s = xs.filter(Number.isFinite).sort((a, b) => a - b); return s.length ? s[Math.floor((s.length - 1) / 2)] : null; }
  /* Qué parte del total de una lista suele sacar su k-ésimo candidato, y su
     cabeza, medido en las listas de esa misma elección. Con eso se traduce
     una fuerza de lista estimada en una meta personal. */
  function participacionesTipicas(parties, allocations) {
    const porK = new Map(), cabezas = [];
    parties.forEach(party => {
      const k = allocations.get(party.name) || 0, top = Number(party.candidates[0] && party.candidates[0].votos || 0);
      if (!party.votes) return;
      if (k <= 1 && top) cabezas.push(top / party.votes);
      if (k >= 1 && party.candidates[k - 1]) { if (!porK.has(k)) porK.set(k, []); porK.get(k).push(Number(party.candidates[k - 1].votos || 0) / party.votes); }
    });
    return { cabeza: mediana(cabezas) || 0.5, k: k => { const ks = [...porK.keys()].sort((a, b) => Math.abs(a - k) - Math.abs(b - k)); return ks.length ? mediana(porK.get(ks[0])) : null; } };
  }
  function referenciaPorPartido({ reconstructed, partido, camara }) {
    if (!reconstructed || reconstructed.sparse || !partido) return null;
    const { parties, allocations, cifra, validVotes } = reconstructed;
    const lista = listaDelPartido(parties, partido);
    const entera = v => Math.max(1, Math.round(v));
    if (lista) {
      const k = allocations.get(lista.name) || 0, top = Number(lista.candidates[0] && lista.candidates[0].votos || 0);
      if (k >= 1) {
        const ultimo = lista.candidates[k - 1];
        return { tipo: 'lista-con-curul', votos: entera(ultimo.votos), k, lista: { nombre: lista.name, total: lista.votes, candidatos: lista.candidates.length, cabeza: top, ultimoNombre: ultimo.nombre || '' }, cifra: entera(cifra) };
      }
      const faltante = Math.max(top, cifra - (lista.votes - top));
      return { tipo: 'lista-sin-curul', votos: entera(faltante), k: 0, lista: { nombre: lista.name, total: lista.votes, candidatos: lista.candidates.length, cabeza: top }, cifra: entera(cifra), faltanLista: entera(Math.max(0, cifra - lista.votes)) };
    }
    if (camara && camara.votval > 0) {
      const enCamara = listaDelPartido(Object.entries(camara.partidos || {}).map(([name, votes]) => ({ name, votes: Number(votes) || 0, candidates: [] })), partido);
      if (enCamara && enCamara.votes > 0) {
        const escala = validVotes / camara.votval, total = enCamara.votes * escala;
        const tipicas = participacionesTipicas(parties, allocations);
        const kEst = Math.floor(total / cifra);
        if (kEst >= 1) {
          const share = tipicas.k(kEst) || (1 / (kEst + 1));
          return { tipo: 'proxy-camara', votos: entera(total * share), k: kEst, cifra: entera(cifra), camara: { nombre: enCamara.name, votos: enCamara.votes, votval: camara.votval, escala, totalEstimado: entera(total) } };
        }
        const cabeza = total * tipicas.cabeza;
        return { tipo: 'proxy-camara', votos: entera(Math.max(cabeza, cifra - (total - cabeza))), k: 0, cifra: entera(cifra), camara: { nombre: enCamara.name, votos: enCamara.votes, votval: camara.votval, escala, totalEstimado: entera(total), cabezaEstimada: entera(cabeza) } };
      }
    }
    return { tipo: 'sin-dato', votos: 0, cifra: entera(cifra) };
  }
  async function camaraDepartamento(baseUrl, departamento) {
    const dep = String(departamento || '').replace(/\D/g, '').padStart(2, '0');
    if (!dep || dep === '00') return null;
    try {
      const d = await json(`${baseUrl}/camara/dep-${dep}.json`);
      const t = d && d.por_circunscripcion && d.por_circunscripcion.TERRITORIAL;
      return t && t.partidos ? { partidos: t.partidos, votval: Number(t.votval) || 0 } : d && d.partidos ? { partidos: d.partidos, votval: Number(d.votval) || 0 } : null;
    } catch (error) { return null; }
  }

  function verifiedCutoff(corp, territory) {
    const key = normalize(territory);
    return VERIFIED_CUTOFFS.find(reference =>
      reference.corp === corp && reference.territory.every(part => key.includes(normalize(part)))
    ) || null;
  }

  function selectCity(results, territory) {
    const wanted = components(territory);
    let best = null;
    (results.cities || []).forEach(city => {
      const key = normalize(`${city.name} ${city.dep}`);
      const score = wanted.reduce((sum, part) => sum + (key.includes(part) || part.includes(normalize(city.name)) ? 1 : 0), 0);
      if (!best || score > best.score) best = { city, score };
    });
    return best && best.score ? best.city : null;
  }

  async function participationReference(corp, territory, baseUrl, source) {
    if (!source.results) return null;
    try {
      const results = await json(`${baseUrl}/${source.results}`);
      const city = selectCity(results, territory);
      if (!city) return null;
      if (corp === 'jal') {
        const scope = results.data && results.data[city.key];
        const wanted = components(territory)[0] || '';
        const unit = Object.values((scope && scope.comunas) || {}).find(item => {
          const key = normalize(item.name);
          return key.includes(wanted) || wanted.includes(key);
        });
        return unit && unit.potencial && unit.votantes
          ? { potential: Number(unit.potencial), voters: Number(unit.votantes) }
          : null;
      }
      if (corp === 'concejo') {
        const scope = results.data && results.data[city.key];
        const voters = Object.values((scope && scope.comunas) || {})
          .reduce((sum, item) => sum + Number(item.votantes || 0), 0);
        return city.potencial && voters
          ? { potential: Number(city.potencial), voters }
          : null;
      }
      if (corp === 'asamblea') {
        const detail = await json(`${baseUrl}/asamblea-2023/dep/${city.key}.json`);
        const units = Object.values((detail && detail.comunas) || {});
        const voters = units.reduce((sum, item) => sum + Number(item.votantes || 0), 0);
        const potential = Number(detail && detail.totals && detail.totals.potencial || city.potencial || 0);
        return potential && voters ? { potential, voters } : null;
      }
    } catch (error) {
      return null;
    }
    return null;
  }

  function projection(referenceVotes, metrics) {
    const censusFactor = 1 + CENSUS_GROWTH_2023_2027;
    let participationFactor = 1;
    let participation2023 = null;
    let participation2027 = null;
    if (metrics && metrics.potential > 0 && metrics.voters > 0) {
      participation2023 = Math.min(1, metrics.voters / metrics.potential);
      participation2027 = Math.min(0.75, participation2023 + PARTICIPATION_UPLIFT);
      participationFactor = participation2027 / participation2023;
    }
    return {
      target: referenceVotes * censusFactor * participationFactor * (1 + COMPETITIVE_MARGIN),
      censusFactor,
      participationFactor,
      participation2023,
      participation2027,
    };
  }

  /* El MISMO cálculo, pero desarmado en piezas nombradas. `formula` lo cuenta
     en una línea; esto deja que la interfaz lo explique paso a paso sin volver
     a calcular nada (y sin que las dos versiones se puedan desincronizar). */
  function detalleDe({ corp, source, label, referencia, metrics, projected, target }) {
    return {
      corporacion: source.label,
      corporacionClave: corp,
      territorio: label,
      uninominal: !source.multiSeat,
      referencia: referencia,
      censo: {
        potencial: metrics && metrics.potential ? Number(metrics.potential) : null,
        crecimiento: CENSUS_GROWTH_2023_2027,
        factor: projected.censusFactor,
      },
      participacion: {
        p2023: projected.participation2023,
        p2027: projected.participation2027,
        alza: PARTICIPATION_UPLIFT,
        factor: projected.participationFactor,
      },
      margen: COMPETITIVE_MARGIN,
      crudo: projected.target,
      objetivo: target,
    };
  }

  function roundTarget(value) {
    const step = value < 10000 ? 10 : value < 100000 ? 100 : 1000;
    return Math.ceil(value / step) * step;
  }

  function projectionText(projectionData, metrics) {
    const census = metrics && metrics.potential
      ? `censo ${Number(metrics.potential).toLocaleString('es-CO')} → ${Math.round(metrics.potential * projectionData.censusFactor).toLocaleString('es-CO')} (+${(CENSUS_GROWTH_2023_2027 * 100).toFixed(1)}%)`
      : `escenario de censo +${(CENSUS_GROWTH_2023_2027 * 100).toFixed(1)}%`;
    const participation = projectionData.participation2023
      ? `participación ${(projectionData.participation2023 * 100).toFixed(1)}% → ${(projectionData.participation2027 * 100).toFixed(1)}%`
      : 'participación estable';
    return `${census} × ${participation} × margen competitivo ${Math.round(COMPETITIVE_MARGIN * 100)}%`;
  }

  async function estimate({ corp, territory, baseUrl, partido, departamento }) {
    const source = CORPORATIONS[corp];
    if (!source || !territory) return { target: null, formula: 'Seleccione una corporación y un territorio para calcular la meta.', detalle: { falla: 'sin-territorio' } };
    try {
      const index = await json(`${baseUrl}/${source.index}`);
      const match = resolveTerritoryRows(index.candidatos || [], territory);
      if (!match || !match.rows.length) throw new Error('Territorio sin resultado comparable');

      const metricsPromise = participationReference(corp, match.label, baseUrl, source);
      if (!source.multiSeat) {
        const winner = [...match.rows].sort((a, b) => Number(b.votos || 0) - Number(a.votos || 0))[0];
        const referenceVotes = Number(winner && winner.votos || 0);
        if (!referenceVotes) throw new Error('Resultado ganador sin votos');
        const metrics = await metricsPromise;
        const projected = projection(referenceVotes, metrics);
        const target = roundTarget(projected.target);
        return {
          target,
          formula: `Meta para ${source.label} en ${match.label}: votación ganadora de 2023 (${referenceVotes.toLocaleString('es-CO')} votos) × ${projectionText(projected, metrics)}.`,
          detalle: detalleDe({ corp, source, label: match.label, metrics, projected, target,
            referencia: { tipo: 'ganadora', votos: referenceVotes, curules: 1, nombre: (winner && winner.nombre) || '', partido: (winner && winner.partido) || '' } }),
        };
      }

      const verified = verifiedCutoff(corp, match.label);
      const reconstructed = reconstructedCutoff(match.rows);
      const reference = verified || reconstructed;
      if (!reference || !reference.cutoff) throw new Error('No fue posible reconstruir la última curul');
      /* La meta por partido solo se calcula sobre la reconstrucción completa
         (con curules por lista); el corte verificado a mano sigue siendo el
         piso de la corporación. */
      const camara = partido && reconstructed && !reconstructed.sparse && !listaDelPartido(reconstructed.parties, partido) ? await camaraDepartamento(baseUrl, departamento) : null;
      const porPartido = partido ? referenciaPorPartido({ reconstructed, partido, camara }) : null;
      const usaPartido = Boolean(porPartido && porPartido.votos > 0);
      const referenceVotes = usaPartido ? porPartido.votos : Number(reference.cutoff);
      const metrics = await metricsPromise;
      const projected = projection(referenceVotes, metrics);
      const target = roundTarget(projected.target);
      const method = verified
        ? 'última curul verificada'
        : reference.sparse
          ? 'piso personal observado (la fuente no permite reconstruir todas las curules)'
          : 'corte de última curul reconstruido con umbral y cifra repartidora';
      const seatsText = reference.seats ? `; ${reference.seats} curules` : '';
      const textoPartido = !usaPartido ? '' : porPartido.tipo === 'lista-con-curul'
        ? `entrar de ${porPartido.k} en la lista de ${porPartido.lista.nombre}, que en 2023 ganó ${porPartido.k} curul${porPartido.k === 1 ? '' : 'es'} y cuyo último elegido sacó ${porPartido.votos.toLocaleString('es-CO')} votos`
        : porPartido.tipo === 'lista-sin-curul'
          ? `llevar a la lista de ${porPartido.lista.nombre} hasta la cifra repartidora (${porPartido.cifra.toLocaleString('es-CO')}): sumó ${porPartido.lista.total.toLocaleString('es-CO')} y a quien la encabece le tocan ${porPartido.votos.toLocaleString('es-CO')}`
          : `una lista estimada con la Cámara de 2026 (${porPartido.camara.totalEstimado.toLocaleString('es-CO')} votos al tamaño de esta corporación), que ${porPartido.k ? `arrastraría ${porPartido.k} curul${porPartido.k === 1 ? '' : 'es'}` : 'no alcanzaría la cifra repartidora'}: ${porPartido.votos.toLocaleString('es-CO')} votos personales`;
      return {
        target,
        formula: usaPartido
          ? `Meta para ${source.label} en ${match.label} con ${partido}: ${textoPartido} × ${projectionText(projected, metrics)}. La última curul de la corporación (${Number(reference.cutoff).toLocaleString('es-CO')} votos) es solo el piso.`
          : `Meta para ${source.label} en ${match.label}: ${method} en 2023 (${Number(reference.cutoff).toLocaleString('es-CO')} votos${seatsText}) × ${projectionText(projected, metrics)}.`,
        detalle: Object.assign(detalleDe({ corp, source, label: match.label, metrics, projected, target,
          referencia: usaPartido
            ? { tipo: 'partido', votos: referenceVotes, curules: reference.seats || null, validos: reference.validVotes || null, piso: Number(reference.cutoff), pisoTipo: verified ? 'curul-verificada' : reference.sparse ? 'piso-observado' : 'curul-reconstruida' }
            : { tipo: verified ? 'curul-verificada' : reference.sparse ? 'piso-observado' : 'curul-reconstruida', votos: Number(reference.cutoff), curules: reference.seats || null, validos: reference.validVotes || null } }),
          { partido: partido ? Object.assign({ nombre: partido }, porPartido || { tipo: 'sin-dato', votos: 0 }) : null }),
      };
    } catch (error) {
      return {
        target: null,
        formula: `Aún no hay una referencia territorial completa para ${territory}. No se usó la votación anterior como sustituto porque la meta depende de la corporación y del lugar.`,
        detalle: { falla: 'sin-referencia', territorio: territory, corporacion: source.label, motivo: error && error.message },
      };
    }
  }

  global.VoteTarget = { estimate };
})(window);
