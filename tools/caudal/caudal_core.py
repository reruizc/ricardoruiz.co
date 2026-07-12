#!/usr/bin/env python3
"""
Caudal · motor de consulta del histórico legislativo (módulo de Cauce).

Lógica pura de búsqueda + análisis de supervivencia sobre el dataset
enriquecido de build_dataset.py. Sin dependencias AWS: lee local (dist/) para
desarrollo; la Lambda inyecta los mismos JSON desde S3. Esta separación deja
probar y demostrar Caudal antes de montar el bucket.

CLI de prueba:
  python3 tools/caudal/caudal_core.py buscar "feminicidio"
  python3 tools/caudal/caudal_core.py tema "paridad de género"
  python3 tools/caudal/caudal_core.py proyecto 4177
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

DIST = Path(__file__).resolve().parents[2] / 'Bases de datos' / 'leyes-senado' / 'dist'

ETAPA_LABEL = ['presentado', '1er debate Senado', '2º debate Senado',
               '1er debate Cámara', '2º debate Cámara', 'ley']
RES_LABEL = {
    'LEY': 'convertido en ley', 'ARCHIVADO_TIEMPO': 'archivado por tiempo (Art. 190)',
    'ARCHIVADO_OTRO': 'archivado', 'RETIRADO': 'retirado por el autor',
    'EN_TRAMITE': 'en trámite', 'OTRO': 'otro', 'SIN_DATO': 'sin dato',
}
# F1 · lectura de intención
EMPUJE_LABEL = {
    'exitoso': 'llegó a ley', 'empujado': 'lo empujaron (llegó a 2º debate)',
    'vitrina': 'proyecto de vitrina (re-radicado sin empujar)',
    'un_debate': 'un solo debate', 'sin_traccion': 'sin tracción (1 intento, sin debate)',
}
TIPOLOGIA_LABEL = {
    'honores': 'honores / conmemoración', 'fondos': 'crea un fondo',
    'reforma': 'reforma / código', 'presupuestal': 'presupuestal regional',
    'ordinaria': 'ordinaria',
}


def _norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode()
    return s.lower()


# sufijos que trima el stemmer ligero (más largos primero) para tolerar
# erratas/flexiones del propio sistema del Congreso ("feminicido" sin la 2ª i)
_SUFIJOS = ('idades', 'ciones', 'idad', 'cion', 'mente', 'ico', 'ica', 'ios',
            'ias', 'ios', 'os', 'as', 'es', 'io', 'ia', 'o', 'a')


def _stem(term):
    """Raíz conservadora: recorta un sufijo común si deja ≥5 chars."""
    for suf in _SUFIJOS:
        if term.endswith(suf) and len(term) - len(suf) >= 5:
            return term[:-len(suf)]
    return term


def _term_match(term, texto_norm):
    """El término (o su raíz) aparece como substring en el texto normalizado."""
    return term in texto_norm or _stem(term) in texto_norm


class Caudal:
    def __init__(self, indice=None, proyectos=None, autor_partido=None):
        self.indice = indice or []
        self._full = proyectos            # dict id→registro completo (lazy)
        self.ap = autor_partido or {}     # canon_key autor → {partido, via, ...}

    @classmethod
    def from_local(cls):
        indice = json.load(open(DIST / 'indice.json', encoding='utf-8'))['proyectos']
        ap = {}
        p = DIST / 'autor-partido.json'
        if p.exists():
            ap = json.load(open(p, encoding='utf-8'))['autor_partido']
        return cls(indice=indice, autor_partido=ap)

    def _load_full(self):
        # keyed por "tb:id" — pdly y pal comparten el espacio de ids (ambos
        # arrancan en 1), así que un id pelado colisiona entre tablas.
        if self._full is None:
            self._full = {}
            for fn, tb in [('proyectos.jsonl', 'pdly'), ('actos-legis.jsonl', 'pal')]:
                p = DIST / fn
                if not p.exists():
                    continue
                for line in open(p, encoding='utf-8'):
                    r = json.loads(line)
                    self._full[f"{tb}:{r['id']}"] = r
        return self._full

    # -------- búsqueda ------------------------------------------------
    def buscar(self, query, anio_min=None, anio_max=None, comision=None,
               resultado=None, tipologia=None, empuje=None, limit=None):
        """Match por keyword(s) en el título. Devuelve ítems del índice.
        Filtros F1: tipologia (honores/fondos/…) y empuje (vitrina/empujado/…)."""
        terms = [_norm(t) for t in query.split() if len(t) > 2] if query else []
        out = []
        for it in self.indice:
            t = _norm(it['t'])
            if terms and not all(_term_match(term, t) for term in terms):
                continue
            if anio_min and (it['a'] or 0) < anio_min:
                continue
            if anio_max and (it['a'] or 9999) > anio_max:
                continue
            if comision and _norm(comision) not in _norm(it['com']):
                continue
            if resultado and it['res'] != resultado:
                continue
            if tipologia and it.get('tip') != tipologia:
                continue
            if empuje and it.get('emp') != empuje:
                continue
            out.append(it)
        out.sort(key=lambda x: (x['a'] or 0))
        return out[:limit] if limit else out

    # -------- análisis de un tema (survival / embudo) -----------------
    def resumen_tema(self, query, **filtros):
        hits = self.buscar(query, **filtros)
        n = len(hits)
        leyes = [h for h in hits if h['ley']]
        tiempo = [h for h in hits if h['res'] == 'ARCHIVADO_TIEMPO']
        caidos = [h for h in hits if h['res'] in ('ARCHIVADO_TIEMPO', 'ARCHIVADO_OTRO', 'RETIRADO')]
        embudo = {ETAPA_LABEL[i]: sum(1 for h in hits if h['et'] >= i) for i in range(6)}
        anios = [h['a'] for h in hits if h['a']]
        # autores que más radican en el tema
        autores = {}
        for h in hits:
            for a in h.get('aut', []):
                autores[a] = autores.get(a, 0) + 1
        top_autores = sorted(autores.items(), key=lambda x: -x[1])[:8]
        # bancadas que impulsan el tema (por partido de los autores) + cobertura
        bancadas, con_p, sin_p = {}, 0, 0
        for h in hits:
            partidos_h = set()
            for k in h.get('ak', []):
                e = self.ap.get(k)
                if e:
                    partidos_h.add(e['partido'])
            if partidos_h:
                con_p += 1
                for p in partidos_h:
                    bancadas[p] = bancadas.get(p, 0) + 1
            else:
                sin_p += 1
        top_bancadas = sorted(bancadas.items(), key=lambda x: -x[1])[:8]
        # F1 · lectura de intención del tema
        tipologia = {}
        empuje = {}
        for h in hits:
            tipologia[h.get('tip', 'ordinaria')] = tipologia.get(h.get('tip', 'ordinaria'), 0) + 1
            empuje[h.get('emp', 'sin_traccion')] = empuje.get(h.get('emp', 'sin_traccion'), 0) + 1
        n_vitrina = empuje.get('vitrina', 0)
        n_honores = tipologia.get('honores', 0)
        return {
            'query': query, 'n_intentos': n,
            'n_leyes': len(leyes), 'n_caidos': len(caidos),
            'n_muerte_por_tiempo': len(tiempo),
            'pct_exito': round(100 * len(leyes) / n, 1) if n else 0,
            'periodo': [min(anios), max(anios)] if anios else None,
            'embudo': embudo,
            'top_autores': top_autores,
            'bancadas': top_bancadas,
            'cobertura_partido': {'con': con_p, 'sin': sin_p},
            # --- intención ---
            'tipologia': dict(sorted(tipologia.items(), key=lambda x: -x[1])),
            'empuje': dict(sorted(empuje.items(), key=lambda x: -x[1])),
            'n_vitrina': n_vitrina, 'n_honores': n_honores,
            'pct_vitrina': round(100 * n_vitrina / n, 1) if n else 0,
            'intentos': [{
                'id': h['id'], 'tb': h.get('tb', 'pdly'), 'anio': h['a'], 'leg': h['leg'],
                'titulo': h['t'], 'resultado': h['res'],
                'resultado_txt': RES_LABEL.get(h['res'], h['res']),
                'autores': h.get('aut', []), 'autor_principal': h.get('ap'),
                'tipologia': h.get('tip'), 'empuje': h.get('emp'),
                'empuje_txt': EMPUJE_LABEL.get(h.get('emp'), h.get('emp')),
                'vitrina_score': h.get('vs', 0), 'veces_presentado': h.get('vp', 1),
                'crea_fondo': h.get('cf', False), 'jala_presupuesto': h.get('jp', False),
            } for h in hits],
        }

    # -------- ficha de un proyecto ------------------------------------
    def proyecto(self, pid, tb='pdly'):
        full = self._load_full()
        r = full.get(f"{tb}:{int(pid)}") or full.get(f"pdly:{int(pid)}") or full.get(f"pal:{int(pid)}")
        if not r:
            return None
        keys = r.get('autores_keys', [])
        principal = r.get('autor_principal')
        autores = [{'nombre': n, 'partido': (self.ap.get(k) or {}).get('partido'),
                    'principal': (n == principal)}
                   for n, k in zip(r.get('autores', []), keys)]
        et = r.get('etapa_max')
        emp = r.get('empuje')
        return {
            'id': r['id'], 'tabla': r.get('tabla', tb), 'titulo': r.get('titulo', ''),
            'numero_senado': r.get('numero_senado', ''), 'numero_camara': r.get('numero_camara', ''),
            'legislatura': r.get('legislatura', ''), 'comision': r.get('comision', ''),
            'autores': autores,
            # --- F1: autoría real ---
            'autor_principal': principal,
            'coautores': r.get('coautores', []),
            'n_firmantes': r.get('n_firmantes', len(autores)),
            'autoria_colectiva': r.get('autoria_colectiva', False),
            'autor_tipo': r.get('autor_tipo'), 'entidad': r.get('entidad'),
            # --- F1: tipología + intención ---
            'tipologia': r.get('tipologia'),
            'tipologia_txt': TIPOLOGIA_LABEL.get(r.get('tipologia')),
            'crea_fondo': r.get('crea_fondo', False),
            'jala_presupuesto_regional': r.get('jala_presupuesto_regional', False),
            'empuje': emp, 'empuje_txt': EMPUJE_LABEL.get(emp, emp),
            'vitrina_score': r.get('vitrina_score', 0),
            'veces_presentado': r.get('veces_presentado', 1),
            'historial_reradicacion': r.get('historial_reradicacion', []),
            'reloj': r.get('reloj'),
            'resultado': r.get('resultado'), 'resultado_txt': RES_LABEL.get(r.get('resultado')),
            'etapa_max': ETAPA_LABEL[et] if isinstance(et, int) and 0 <= et < len(ETAPA_LABEL) else None,
            'fecha_presentacion': r.get('fecha_presentacion'),
            'dias_a_primer_debate': r.get('dias_a_primer_debate'),
            'gacetas': r.get('gacetas', []),   # ← punteros para la fase DeepSeek
        }


def _cli():
    caudal = Caudal.from_local()
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'tema'
    arg = sys.argv[2] if len(sys.argv) > 2 else 'feminicidio'
    if cmd == 'buscar':
        for h in caudal.buscar(arg, limit=25):
            print(f"  [{h['a']}] {RES_LABEL.get(h['res'],h['res']):<28} {h['t'][:64]}")
    elif cmd == 'proyecto':
        print(json.dumps(caudal.proyecto(arg), ensure_ascii=False, indent=1))
    else:
        r = caudal.resumen_tema(arg)
        print(f"\nTEMA: «{arg}»  ·  {r['n_intentos']} intentos  ·  "
              f"{r['n_leyes']} leyes ({r['pct_exito']}%)  ·  "
              f"{r['n_caidos']} caídos ({r['n_muerte_por_tiempo']} por tiempo)  ·  "
              f"periodo {r['periodo']}")
        print(f"\nIntención:  {r['n_vitrina']} de vitrina ({r['pct_vitrina']}%)  ·  "
              f"{r['n_honores']} de honores")
        print('  empuje:  ' + '  '.join(f"{v}×{EMPUJE_LABEL.get(k,k).split('(')[0].strip()}" for k, v in r['empuje'].items()))
        print('  tipo:    ' + '  '.join(f"{v}×{k}" for k, v in r['tipologia'].items()))
        print('\nEmbudo:')
        for et, n in r['embudo'].items():
            print(f"  {n:4}  {et}")
        print('\nQuién más lo intenta:')
        for a, c in r['top_autores']:
            print(f"  {c}×  {a}")
        print('\nLínea de intentos:')
        for it in r['intentos']:
            print(f"  [{it['anio']}] {it['resultado_txt']:<30} {it['titulo'][:56]}")


if __name__ == '__main__':
    _cli()
