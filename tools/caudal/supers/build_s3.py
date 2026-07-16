#!/usr/bin/env python3
"""
Caudal · pilar Regulatorio — empaqueta las sanciones para S3 / la Lambda.

Toma dist/sanciones.jsonl (salida de harvest_supers.py normalize) y emite dos
artefactos que consume la Lambda caudal-analiza (acción `sanciones`):

  dist/s3/sanciones.jsonl        lista SLIM por sanción (sin _raw ni cédulas):
                                 los campos que se muestran + un blob de búsqueda.
                                 La Lambda la carga lazy y filtra en memoria.
  dist/s3/sanciones-stats.json   agregados chicos para el landing del pilar:
                                 total, por_sector, por_fuente, por_tipo, monto,
                                 rango de fechas y una muestra de recientes.

Todo stdlib. No sube nada: el `aws s3 cp` va aparte (ver README).
"""
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DIST = REPO / 'Bases de datos' / 'leyes-senado' / 'supers' / 'dist'
OUT = DIST / 's3'

# fuentes.json trae el nombre lindo del sector implícito; lo re-etiquetamos aquí
SECTOR_TXT = {
    'salud': 'Salud', 'contratacion': 'Contratación estatal',
    'control': 'Control fiscal', 'juridico': 'Jurídico / contable',
    'financiero': 'Financiero', 'transporte': 'Transporte',
    'consumo': 'Consumo', 'laboral': 'Laboral', 'societario': 'Societario',
}



# algunas fuentes (verificado con Superfinanciera) traen mojibake de control
# chars (comillas/elipsis de Windows-1252 mal transcodeadas, p.ej. \x93\x85)
# metidos en textos largos. Fuera de ensuciar la UI, U+0085/U+2028/U+2029 son
# "salto de línea" para str.splitlines() aunque NO sean el '\n' real que
# separa los registros del JSONL — por eso este archivo NUNCA debe leerse ni
# escribirse con .splitlines(), solo con split('\n') (ver main()).
_CTRL_RE = re.compile(r'[\x00-\x1f\x7f-\x9f]')


def _clean_text(s):
    if not s:
        return s
    return re.sub(r'\s+', ' ', _CTRL_RE.sub(' ', s)).strip()


def parse_fecha(v):
    """'2026-03-27T00:00:00.000' | '2026-03-27' → '2026-03-27' (o '')."""
    if not v:
        return ''
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', str(v))
    return m.group(0) if m else ''


def parse_monto(v):
    """Best-effort a float COP. Devuelve None si no se puede."""
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    # quita todo menos dígitos, coma y punto; asume punto=miles / coma=decimal
    s = re.sub(r'[^\d.,]', '', s)
    if not s:
        return None
    # heurística simple: si hay coma como último separador decimal, respétala
    s = s.replace('.', '').replace(',', '.') if s.count(',') == 1 and s.rfind(',') > s.rfind('.') else s.replace(',', '')
    try:
        f = float(s)
        return f if 0 < f < 1e15 else None
    except ValueError:
        return None


def slim(rec):
    fecha = parse_fecha(rec.get('fecha_firmeza'))
    monto = parse_monto(rec.get('monto'))
    sanc = _clean_text(rec.get('sancionado') or '')
    mot = _clean_text(rec.get('motivo') or '')
    desc = _clean_text(rec.get('descripcion') or '')
    blob = ' '.join(x for x in (sanc, mot, desc, rec.get('fuente_nombre', '')) if x).lower()
    return {
        'sancionado': sanc or '—',
        'fuente': rec.get('fuente', ''),
        'fuente_nombre': rec.get('fuente_nombre', ''),
        'sector': rec.get('sector', ''),
        'tipo': (rec.get('tipo_sancion') or '').strip(),
        'motivo': mot[:280],
        'descripcion': desc[:120],
        'monto': monto,
        'resolucion': (rec.get('resolucion') or '').strip(),
        'fecha': fecha,
        'q': blob,           # blob de búsqueda (la Lambda hace substring sobre esto)
    }


def main():
    src = DIST / 'sanciones.jsonl'
    # split('\n') literal — NO .splitlines(): un texto con U+0085/U+2028/U+2029
    # partiría el JSONL en el lugar equivocado (ver _clean_text arriba).
    recs = [slim(json.loads(l)) for l in src.read_text(encoding='utf-8').split('\n') if l.strip()]
    OUT.mkdir(parents=True, exist_ok=True)

    with (OUT / 'sanciones.jsonl').open('w', encoding='utf-8') as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')

    por_sector = Counter(r['sector'] for r in recs)
    por_fuente = Counter(r['fuente_nombre'] for r in recs)
    por_tipo = Counter((r['tipo'] or '—') for r in recs)
    con_monto = [r['monto'] for r in recs if r['monto']]
    fechas = sorted(r['fecha'] for r in recs if r['fecha'])
    recientes = sorted([r for r in recs if r['fecha']],
                       key=lambda r: r['fecha'], reverse=True)[:15]
    for r in recientes:            # la muestra no necesita el blob de búsqueda
        r.pop('q', None)

    stats = {
        'total': len(recs),
        'por_sector': [{'sector': s, 'sector_txt': SECTOR_TXT.get(s, s.title()), 'n': n}
                       for s, n in por_sector.most_common()],
        'por_fuente': [{'fuente': f, 'n': n} for f, n in por_fuente.most_common()],
        'por_tipo': [{'tipo': t, 'n': n} for t, n in por_tipo.most_common(8)],
        'monto': {
            'con_monto': len(con_monto), 'sin_monto': len(recs) - len(con_monto),
            'total_cop': round(sum(con_monto)), 'max_cop': round(max(con_monto)) if con_monto else 0,
        },
        'rango_fechas': [fechas[0], fechas[-1]] if fechas else ['', ''],
        'recientes': recientes,
        'fuentes': ['INVIMA', 'SECOP I', 'SECOP II', 'Contraloría (resp. fiscal)', 'Junta Central de Contadores'],
    }
    (OUT / 'sanciones-stats.json').write_text(
        json.dumps(stats, ensure_ascii=False, indent=1), encoding='utf-8')

    print(f"slim: {len(recs)} sanciones -> {(OUT/'sanciones.jsonl').relative_to(REPO)}")
    print(f"sectores: {dict(por_sector)}")
    print(f"con monto: {len(con_monto)} · total COP {stats['monto']['total_cop']:,}")
    print(f"rango: {stats['rango_fechas']}")


if __name__ == '__main__':
    main()
