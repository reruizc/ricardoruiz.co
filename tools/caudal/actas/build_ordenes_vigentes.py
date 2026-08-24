#!/usr/bin/env python3
"""Construye el feed liviano de próximas órdenes del día para el hub Legislativo.

Lee únicamente los cachés que dejan los harvesters diarios. No toca la red: así
la publicación nunca muestra como fresca una fuente que falló durante la cosecha.
La salida conserva la URL del documento oficial y una muestra ordenada de los
proyectos encontrados en cada agenda.
"""
import datetime
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from harvest_ordenes import (  # noqa: E402
    CACHE, GACETA_REF_RE, PROJ_BLOCK_RE, cut_anuncio, fecha_sesion,
    gaceta_map_cached, norm, num_map_cached, pdf_url,
)
from harvest_ordenes_senado import (  # noqa: E402
    BASE as SEN_BASE, BUENAS, CITA_RE, IDX_CACHE, IDX_CACHE_PLEN,
    NUM_LABELED_RE, PLEN_EXCLUIR_RE, ambito_de, es_candidato,
    fecha_sesion_senado, norm_txt,
)

OUT = CACHE / 'ordenes-vigentes.json'
HOY = datetime.date.today()
HASTA = HOY + datetime.timedelta(days=14)
DESDE = HOY - datetime.timedelta(days=1)

CAM_NICE = {
    'primera': 'Comisión Primera', 'segunda': 'Comisión Segunda',
    'tercera': 'Comisión Tercera', 'cuarta': 'Comisión Cuarta',
    'quinta': 'Comisión Quinta', 'sexta': 'Comisión Sexta',
    'septima': 'Comisión Séptima', 'afro': 'Comisión Afro',
    'ordenamiento': 'Ordenamiento Territorial', 'ddhh': 'Derechos Humanos',
    'cuentas': 'Comisión de Cuentas', 'etica': 'Comisión de Ética',
    'mujer': 'Comisión de la Mujer', 'electoral': 'Comisión Electoral',
    'plenaria': 'Plenaria de Cámara',
}


def en_ventana(fecha):
    try:
        d = datetime.date.fromisoformat(fecha)
    except (TypeError, ValueError):
        return False
    return DESDE <= d <= HASTA


def titulo_limpio(s):
    s = re.sub(r'<[^>]+>', ' ', s or '')
    return re.sub(r'\s+', ' ', s).strip()


def proyectos_camara(txt):
    body, out, seen = cut_anuncio(txt), [], set()
    gmap, nmap = gaceta_map_cached(), num_map_cached()
    for m in PROJ_BLOCK_RE.finditer(body):
        year = m.group(2).replace(' ', '')
        tok = norm(m.group(1), year[-2:])
        if tok in seen:
            continue
        seen.add(tok)
        tit = titulo_limpio(m.group(3)).strip(' "“”«»')
        if len(tit) < 12:
            tit = (nmap.get(tok) or {}).get('titulo', '')
        out.append({'numero': tok, 'titulo': titulo_limpio(tit)})
    for m in GACETA_REF_RE.finditer(body):
        hit = gmap.get(f'{int(m.group(1))}/{m.group(2)}')
        if not hit or hit[0] in seen:
            continue
        tok, tit = hit
        seen.add(tok)
        out.append({'numero': tok, 'titulo': titulo_limpio(tit)})
    return out


def camara():
    ordenes, seen = [], set()
    root = CACHE / 'ordenes'
    if not root.exists():
        return ordenes
    for scope_dir in root.iterdir():
        ef = scope_dir / '_eventos.json'
        if not scope_dir.is_dir() or not ef.exists():
            continue
        try:
            eventos = json.load(open(ef, encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        for ev in eventos:
            eid = str(ev.get('id', ''))
            if not eid or eid in seen:
                continue
            seen.add(eid)
            pub = (ev.get('date') or '')[:10]
            titulo = titulo_limpio((ev.get('title') or {}).get('rendered', ''))
            fecha, _ = fecha_sesion(titulo, pub)
            if not en_ventana(fecha):
                continue
            tf = scope_dir / f'{eid}.txt'
            txt = tf.read_text(encoding='utf-8') if tf.exists() else ''
            proys = proyectos_camara(txt)
            url = pdf_url(ev)
            if not url:
                continue
            ordenes.append({
                'id': f'cam-{eid}', 'fecha': fecha, 'publicado': pub,
                'corporacion': 'Cámara',
                'ambito': CAM_NICE.get(scope_dir.name, scope_dir.name.title()),
                'titulo': titulo, 'url': url, 'proyectos': proys,
                'n_proyectos': len(proys),
            })
    return ordenes


def proyectos_senado(txt):
    body, out, seen = cut_anuncio(txt), [], set()
    for cita in CITA_RE.finditer(body):
        num = None
        for m in NUM_LABELED_RE.finditer(cita.group('header')):
            if norm_txt(m.group(4)) == 'senado':
                num = (m.group(1), m.group(2) or m.group(3))
                break
        if not num:
            continue
        tok = norm(num[0], num[1])
        if tok in seen:
            continue
        seen.add(tok)
        out.append({'numero': tok, 'titulo': titulo_limpio(cita.group('titulo')).strip(' "“”«»')})
    return out


def senado_docs(cache_file, scope=None):
    if not cache_file.exists():
        return []
    try:
        docs = json.load(open(cache_file, encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return []
    out = []
    for doc in docs:
        amb = scope or ambito_de(doc)
        if amb not in set(BUENAS + ['plenaria']):
            continue
        if scope == 'plenaria':
            if PLEN_EXCLUIR_RE.search(doc.get('title') or ''):
                continue
        elif not es_candidato(doc):
            continue
        tf = SEN_BASE / amb / f"{doc.get('id')}.txt"
        if not tf.exists():
            continue
        txt = tf.read_text(encoding='utf-8')
        pub = (doc.get('publish_date') or '')[:10]
        fecha, _ = fecha_sesion_senado(doc.get('title'), txt, pub, titulo_flex=(amb == 'plenaria'))
        if not en_ventana(fecha):
            continue
        url = (((doc.get('links') or {}).get('file') or {}).get('href') or '').replace('http://', 'https://')
        if not url:
            continue
        proys = proyectos_senado(txt)
        out.append({
            'id': f"sen-{doc.get('id')}", 'fecha': fecha, 'publicado': pub,
            'corporacion': 'Senado',
            'ambito': 'Plenaria de Senado' if amb == 'plenaria' else f'Comisión {amb.title()}',
            'titulo': titulo_limpio(doc.get('title')), 'url': url,
            'proyectos': proys, 'n_proyectos': len(proys),
        })
    return out


def main():
    rows = camara() + senado_docs(IDX_CACHE) + senado_docs(IDX_CACHE_PLEN, 'plenaria')
    # Una corrección o republicación para la misma sesión no merece dos tarjetas:
    # gana la versión más recientemente publicada y con más proyectos parseados.
    best = {}
    for r in rows:
        key = (r['corporacion'], r['ambito'], r['fecha'])
        old = best.get(key)
        if old is None or (r['publicado'], r['n_proyectos']) > (old['publicado'], old['n_proyectos']):
            best[key] = r
    rows = sorted(best.values(), key=lambda r: (r['fecha'], r['corporacion'], r['ambito']))
    out = {
        'v': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
        'desde': DESDE.isoformat(), 'hasta': HASTA.isoformat(),
        'n': len(rows), 'ordenes': rows,
        'cobertura': 'Cámara: 14 comisiones y plenaria. Senado: plenaria y comisiones Cuarta, Quinta y Sexta.',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(rows)} órdenes vigentes → {OUT}')


if __name__ == '__main__':
    main()
