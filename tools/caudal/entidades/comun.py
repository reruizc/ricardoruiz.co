"""Caudal · entidades del Ejecutivo con sitio propio (oct-2026).

Piezas compartidas por los cosechadores de cada entidad (MinSalud primero,
después MinComercio, la Supersubsidio, la SIC…) y por `build.py`, que los junta
en tres índices genéricos que lee la Lambda sin saber de qué entidad vienen:

  metadata/entidades-borradores.jsonl   → Consulta pública (formato de SUCOP)
  metadata/entidades-normas.jsonl       → pilar Ejecutivo (formato de normativa)
  metadata/entidades-eventos.jsonl      → Norte del radar (eventos oficiales)

Plan completo: `Bases de datos/caudal-entidades/plan.md`.
"""
import json
import re
import subprocess
import time
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
BASE = REPO / 'Bases de datos' / 'caudal-entidades'
RAW = BASE / 'raw'
DIST = BASE / 'dist'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')


def fold(s):
    s = unicodedata.normalize('NFD', (s or '').strip().lower())
    return ''.join(c for c in s if not unicodedata.combining(c))


def limpio(s):
    s = re.sub(r'<[^>]+>', ' ', s or '')
    s = s.replace('&#58;', ':').replace('&nbsp;', ' ').replace('​', '')
    return re.sub(r'\s+', ' ', s).strip()


def curl(url, accept=None, salida=None, timeout=60, intentos=3):
    """GET con curl (esquiva el TLS de python sin certifi, igual que el resto
    del proyecto). Reintenta: los SharePoint públicos dan 503 sueltos."""
    cmd = ['/usr/bin/curl', '-s', '-L', '--max-time', str(timeout), '-A', UA, '-w', '%{http_code}']
    if accept:
        cmd += ['-H', f'Accept: {accept}']
    if salida:
        cmd += ['-o', str(salida)]
    cmd.append(url)
    ultimo = ''
    for i in range(intentos):
        r = subprocess.run(cmd, capture_output=True, timeout=timeout + 15)
        out = r.stdout.decode('utf-8', 'replace')
        code = out[-3:]
        if r.returncode == 0 and code == '200':
            return '' if salida else out[:-3]
        ultimo = f'rc={r.returncode} http={code}'
        time.sleep(3 * (i + 1))
    raise RuntimeError(f'{ultimo} en {url[:100]}')


def leer(p, defecto=None):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8'))
    except (FileNotFoundError, ValueError):
        return defecto


def escribir(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(p)


# Actos de personal y trámites individuales (misma regla que el Diario Oficial,
# tools/caudal/ejecutivo/harvest_diario_oficial.py `_ADMIN`): se marcan, no se
# borran. El radar del cliente no los usa.
_ADMIN = re.compile(
    r'(?i)\b(nombramientos?|se\s+nombra|nombra\s+en|renuncia|encargo|vacaciones|vacancia|reintegro|'
    r'comisi[óo]n\s+de\s+servicios|insubsistencia|retiro\s+del\s+servicio|toma\s+de\s+posesi[óo]n|'
    r'periodo\s+de\s+prueba|per[íi]odo\s+de\s+prueba|provisionalidad|prima\s+t[ée]cnica|'
    r'licencia\s+(?:no\s+)?remunerada|extradici[óo]n|recurso\s+de\s+reposici[óo]n)')


def es_administrativo(texto):
    return bool(_ADMIN.search((texto or '')[:300]))
