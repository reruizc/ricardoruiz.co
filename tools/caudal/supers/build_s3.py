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
import datetime
import json
import re
import unicodedata
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
    'ambiental': 'Ambiental',
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


# varias fuentes traen typos de fecha (SFC año 3022 · SECOP II 2027/2028 ·
# Junta de Contadores dic-2026): fuera de rango sano se descarta la FECHA
# (no el registro), misma política que harvest_sfc.py — no fabricar dato.
_FECHA_MAX = (datetime.date.today() + datetime.timedelta(days=45)).isoformat()


def parse_fecha(v):
    """'2026-03-27T00:00:00.000' | '2026-03-27' → '2026-03-27' (o '')."""
    if not v:
        return ''
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', str(v))
    if not m:
        return ''
    f = m.group(0)
    return f if '2000-01-01' <= f <= _FECHA_MAX else ''


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


# reencuadre jul-2026: el pilar cubre ACTOS regulatorios, no solo sanciones.
# La vista por defecto sigue siendo 'sancion' (no diluir lo que ve el cliente);
# los demás tipos entran con el toggle "toda la actividad regulatoria".
TIPOS_ACTO = ('sancion', 'apertura_investigacion', 'archivo',
              'contribucion_especial', 'resolucion', 'circular', 'otro')
TIPO_ACTO_TXT = {
    'sancion': 'Sanciones',
    'apertura_investigacion': 'Aperturas de investigación',
    'archivo': 'Archivos y exoneraciones',
    'contribucion_especial': 'Contribución especial',
    'resolucion': 'Resoluciones',
    'circular': 'Circulares',
    'otro': 'Otros actos',
}


def _fold(s):
    """Minúsculas y SIN tildes, para el blob de búsqueda.

    Medido ago-2026, y era un agujero grande: el 87% de los blobs traía tildes,
    así que «régimen cambiario» devolvía 3.764 actos y «regimen cambiario»
    devolvía CERO. El cliente escribe sin tildes.

    Va acá y no en la Lambda a propósito: plegar los 81k blobs en caliente
    cuesta 2,87 s POR CONSULTA (medido). Plegado una vez al construir, la
    búsqueda no paga nada. La otra mitad del arreglo está en la Lambda, que
    pliega la consulta con la misma regla.

    NFD + descartar las marcas combinantes, no un reemplazo literal de á→a: hay
    fuentes que mandan la tilde descompuesta (la 'a' y el acento como dos
    caracteres) y ahí el reemplazo literal no ve nada y falla en silencio.
    """
    return ''.join(c for c in unicodedata.normalize('NFD', (s or '').lower())
                   if unicodedata.category(c) != 'Mn')


def slim(rec):
    fecha = parse_fecha(rec.get('fecha_firmeza'))
    monto = parse_monto(rec.get('monto'))
    sanc = _clean_text(rec.get('sancionado') or '')
    mot = _clean_text(rec.get('motivo') or '')
    desc = _clean_text(rec.get('descripcion') or '')
    blob = _fold(' '.join(x for x in (sanc, mot, desc, rec.get('fuente_nombre', '')) if x))
    ta = (rec.get('tipo_acto') or '').strip()
    return {
        'sancionado': sanc or '—',
        'fuente': rec.get('fuente', ''),
        'fuente_nombre': rec.get('fuente_nombre', ''),
        'sector': rec.get('sector', ''),
        # tipo_acto = qué CLASE de acto es (filtro); tipo = su rótulo legible
        'tipo_acto': ta if ta in TIPOS_ACTO else 'sancion',
        'tipo': (rec.get('tipo_sancion') or '').strip(),
        'motivo': mot[:280],
        'descripcion': desc[:120],
        'monto': monto,
        'resolucion': (rec.get('resolucion') or '').strip(),
        'fecha': fecha,
        'url': (rec.get('url') or '').strip(),   # fuente oficial (comunicado/acto)
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

    # el landing por defecto muestra SANCIONES: sus agregados se calculan sobre
    # ese subconjunto, no sobre el universo (si no, el cliente vería un "total"
    # inflado con contribuciones y aperturas). Los del universo van aparte.
    sanc = [r for r in recs if r['tipo_acto'] == 'sancion']
    por_tipo_acto = Counter(r['tipo_acto'] for r in recs)
    por_sector = Counter(r['sector'] for r in sanc)
    por_fuente = Counter(r['fuente_nombre'] for r in sanc)
    por_tipo = Counter((r['tipo'] or '—') for r in sanc)
    con_monto = [r['monto'] for r in sanc if r['monto']]
    fechas = sorted(r['fecha'] for r in sanc if r['fecha'])
    recientes = sorted([r for r in sanc if r['fecha']],
                       key=lambda r: r['fecha'], reverse=True)[:15]
    for r in recientes:            # la muestra no necesita el blob de búsqueda
        r.pop('q', None)
    todo_por_sector = Counter(r['sector'] for r in recs)

    stats = {
        'total': len(sanc),                 # sanciones (lo que ve el cliente por defecto)
        'total_actos': len(recs),           # universo completo del pilar
        'por_tipo_acto': [{'tipo_acto': t, 'tipo_acto_txt': TIPO_ACTO_TXT.get(t, t), 'n': n}
                          for t, n in por_tipo_acto.most_common()],
        'por_sector': [{'sector': s, 'sector_txt': SECTOR_TXT.get(s, s.title()), 'n': n}
                       for s, n in por_sector.most_common()],
        'por_sector_todo': [{'sector': s, 'sector_txt': SECTOR_TXT.get(s, s.title()), 'n': n}
                            for s, n in todo_por_sector.most_common()],
        'por_fuente': [{'fuente': f, 'n': n} for f, n in por_fuente.most_common()],
        'por_tipo': [{'tipo': t, 'n': n} for t, n in por_tipo.most_common(8)],
        'monto': {
            'con_monto': len(con_monto), 'sin_monto': len(sanc) - len(con_monto),
            'total_cop': round(sum(con_monto)), 'max_cop': round(max(con_monto)) if con_monto else 0,
        },
        'rango_fechas': [fechas[0], fechas[-1]] if fechas else ['', ''],
        'recientes': recientes,
        'fuentes': sorted({r['fuente_nombre'] for r in recs if r['fuente_nombre']}),
    }
    (OUT / 'sanciones-stats.json').write_text(
        json.dumps(stats, ensure_ascii=False, indent=1), encoding='utf-8')

    print(f"slim: {len(recs)} actos ({len(sanc)} sanciones) -> "
          f"{(OUT/'sanciones.jsonl').relative_to(REPO)}")
    for t, n in por_tipo_acto.most_common():
        print(f"  {t:24s} {n:>6d}")
    print(f"sectores (sanciones): {dict(por_sector)}")
    print(f"con monto: {len(con_monto)} · total COP {stats['monto']['total_cop']:,}")
    print(f"rango: {stats['rango_fechas']}")


if __name__ == '__main__':
    main()
