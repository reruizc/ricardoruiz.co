#!/usr/bin/env python3
"""
Caudal · pilar Ejecutivo · harvester del DIARIO OFICIAL (Imprenta Nacional).

Por qué existe: el pilar Ejecutivo se alimentaba SOLO del dataset Socrata
88h2-dykw de Presidencia, que se actualiza UNA VEZ AL MES. El 21-sep-2026 su
norma más reciente era del 28-ago, y el brief de Cauce no vio los ~25 decretos
legislativos de la emergencia económica por el sismo (Decreto 1261 del 19-ago y
las tandas del 9 y el 17 de septiembre). El Diario Oficial publica a diario.

Fuente: https://svrpubindc.imprenta.gov.co/diario/ — app JSF/PrimeFaces sin reto
antibots (a diferencia de dapre.presidencia.gov.co, que va detrás de un F5/TSPD
que NO se evade). Flujo, todo con una sesión de curl:
  1. GET index.xhtml                    → cookie JSESSIONID + javax.faces.ViewState
  2. POST ajax btnBuscar (fechas)       → tabla de ediciones (número · tipo · fecha)
  3. POST btnBuscar(número) + botón «Ver Diario» de la fila 0 → detallesPdf.xhtml
  4. GET dynamiccontent del PDF         → la edición completa (cifrada AES, con
     contraseña de usuario vacía: pymupdf la abre sola; pypdf exige el paquete
     `cryptography`, que se usa si está)

Cada edición trae todas las normas del día. Se extraen solo DECRETOS (incluidos
los legislativos), LEYES y ACTOS LEGISLATIVOS: las resoluciones de ministerios
y superintendencias NO son el universo del pilar (Socrata trae solo las de
Presidencia) y mezclarlas lo llenaría de ruido.

Salida: `Bases de datos/leyes-senado/ejecutivo/raw/diario_oficial.json` con filas
en el MISMO esquema de normativa.jsonl + `fuente='diario_oficial'`. La fusión con
Socrata la hace `harvest_decretos.py build` (Socrata manda cuando tiene la norma).

⚠️ El enlace al PDF del Diario Oficial es de SESIÓN (dynamiccontent con uid de
un solo uso): no sirve como `url` permanente. Las filas del Diario Oficial salen
con `url` vacío y la cita de la edición en `publicacion` (número, fecha, página).
Cuando Socrata publique la norma, su fila (con PDF de Presidencia) la reemplaza.

Uso:
  python3 tools/caudal/ejecutivo/harvest_diario_oficial.py fetch            # últimos 45 días
  python3 tools/caudal/ejecutivo/harvest_diario_oficial.py fetch --dias 90
  python3 tools/caudal/ejecutivo/harvest_diario_oficial.py fetch --desde 2026-08-01
  python3 tools/caudal/ejecutivo/harvest_diario_oficial.py extraer 53595   # depura una edición
"""
import argparse
import datetime
import html
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = REPO / 'Bases de datos' / 'leyes-senado' / 'ejecutivo'
RAW = OUT / 'raw'
CACHE = OUT / 'diario-oficial'          # un .txt por edición (el PDF no se guarda)
SALIDA = RAW / 'diario_oficial.json'

BASE = 'https://svrpubindc.imprenta.gov.co'
INDEX = BASE + '/diario/index.xhtml'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')
PAUSA = 1.0          # segundos entre peticiones: es un servidor público, sin prisa

MESES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
         'julio': 7, 'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10,
         'noviembre': 11, 'diciembre': 12}
MES_NOMBRE = {v: k.upper() for k, v in MESES.items() if k != 'setiembre'}


# ─────────────────────────── sesión JSF ───────────────────────────

class Sesion:
    """Una sesión de curl con su cookie jar y el ViewState vigente."""

    def __init__(self):
        self.jar = tempfile.NamedTemporaryFile(prefix='do-', suffix='.jar', delete=False).name
        self.vs = None
        h = self._curl(INDEX)
        self.vs = self._viewstate(h)
        if not self.vs:
            raise RuntimeError('no se obtuvo javax.faces.ViewState: ¿cambió la página?')

    def _curl(self, url, data=None, ajax=False, salida=None, timeout=120):
        cmd = ['/usr/bin/curl', '-s', '-L', '--max-time', str(timeout),
               '-c', self.jar, '-b', self.jar, '-A', UA, url]
        if ajax:
            cmd += ['-H', 'Faces-Request: partial/ajax', '-H', 'X-Requested-With: XMLHttpRequest']
        if data is not None:
            cmd += ['--data', urllib.parse.urlencode(data)]
        if salida:
            cmd += ['-o', str(salida)]
        r = subprocess.run(cmd, capture_output=True, timeout=timeout + 15)
        if r.returncode != 0:
            raise RuntimeError(f'curl rc={r.returncode} en {url[:80]}')
        time.sleep(PAUSA)
        return r.stdout.decode('utf-8', 'replace')

    @staticmethod
    def _viewstate(h):
        m = (re.search(r'ViewState:0" value="([^"]*)', h)
             or re.search(r'ViewState:0"><!\[CDATA\[([^\]]*)', h))
        return m.group(1) if m else None

    def _form(self, **kw):
        d = {'frmConDiario': 'frmConDiario', 'numeroDiarioOf': '', 'numeroRecibo': '',
             'tipoNorma_input': '', 'numeroNorma': '', 'entidad_input': '',
             'entidad_hinput': '', 'fechaInicial_input': '', 'fechaFinal_input': ''}
        d.update(kw)
        d['javax.faces.ViewState'] = self.vs
        return d

    def buscar(self, **kw):
        d = self._form(**kw)
        d.update({'javax.faces.partial.ajax': 'true', 'javax.faces.source': 'btnBuscar',
                  'javax.faces.partial.execute': '@all', 'javax.faces.partial.render': '@all',
                  'btnBuscar': 'btnBuscar'})
        h = self._curl(INDEX, d, ajax=True)
        self.vs = self._viewstate(h) or self.vs
        return h

    def pagina(self, primero, filas=50):
        """Página de la tabla de resultados de la última búsqueda."""
        d = self._form()
        d.update({'javax.faces.partial.ajax': 'true', 'javax.faces.source': 'dtbDiariosOficiales',
                  'javax.faces.partial.execute': 'dtbDiariosOficiales',
                  'javax.faces.partial.render': 'dtbDiariosOficiales',
                  'dtbDiariosOficiales': 'dtbDiariosOficiales',
                  'dtbDiariosOficiales_pagination': 'true',
                  'dtbDiariosOficiales_first': str(primero),
                  'dtbDiariosOficiales_rows': str(filas),
                  'dtbDiariosOficiales_encodeFeature': 'true'})
        h = self._curl(INDEX, d, ajax=True)
        self.vs = self._viewstate(h) or self.vs
        return h

    def pdf(self, numero, destino):
        """Descarga el PDF de una edición (número con o sin punto de miles)."""
        num = numero.replace('.', '')
        h = self.buscar(numeroDiarioOf=num)
        filas = _filas(h)
        if not filas:
            raise RuntimeError(f'la edición {numero} no aparece en la búsqueda')
        d = self._form(numeroDiarioOf=num)
        d[f'dtbDiariosOficiales:{filas[0]["ri"]}:j_idt34'] = ''
        h = self._curl(INDEX, d)
        self.vs = self._viewstate(h) or self.vs
        m = re.search(r'(/diario/javax\.faces\.resource/dynamiccontent[^"]*)', h)
        if not m:
            raise RuntimeError(f'la ficha de la edición {numero} no trae enlace al PDF')
        self._curl(BASE + html.unescape(m.group(1)), salida=destino, timeout=300)
        cab = Path(destino).read_bytes()[:5]
        if cab != b'%PDF-':
            raise RuntimeError(f'la edición {numero} no devolvió un PDF ({cab!r})')


_FILA = re.compile(
    r'data-ri="(\d+)"[^>]*>.*?numeroDiario"[^>]*>([\d.]+)</label>.*?'
    r'tipoEdicion"[^>]*>([^<]*)</label>.*?fechaDiario"[^>]*>(\d{2}/\d{2}/\d{4})</label>', re.S)


def _filas(h):
    return [{'ri': ri, 'numero': n, 'tipo_edicion': t.strip(),
             'fecha': f'{f[6:]}-{f[3:5]}-{f[:2]}'} for ri, n, t, f in _FILA.findall(h)]


def _total(h):
    m = re.search(r'Registro \d+ a \d+ de (\d+)', h)
    return int(m.group(1)) if m else 0


def listar(s, desde, hasta):
    """Ediciones publicadas entre dos fechas (date). Pagina de a 50."""
    h = s.buscar(fechaInicial_input=desde.strftime('%d/%m/%Y'),
                 fechaFinal_input=hasta.strftime('%d/%m/%Y'))
    total = _total(h)
    eds = {f['numero']: f for f in _filas(h)}
    primero = len(eds)
    while primero < total:
        filas = _filas(s.pagina(primero, 50))
        if not filas:
            break
        for f in filas:
            eds[f['numero']] = f
        primero += len(filas)
    if len(eds) < total:
        raise RuntimeError(f'la búsqueda anunció {total} ediciones y se leyeron {len(eds)}')
    return sorted(eds.values(), key=lambda e: int(e['numero'].replace('.', '')))


# ─────────────────────────── PDF → texto ───────────────────────────

def pdf_a_texto(ruta):
    """Texto por página. pymupdf abre el cifrado AES sin dependencias; pypdf solo
    si está `cryptography` (sin él revienta con DependencyError)."""
    try:
        import pymupdf
        with pymupdf.open(str(ruta)) as d:
            return [p.get_text() for p in d]
    except ImportError:
        pass
    import pypdf
    r = pypdf.PdfReader(str(ruta))
    if r.is_encrypted:
        r.decrypt('')
    return [p.extract_text() or '' for p in r.pages]


# ─────────────────────────── extracción ───────────────────────────

# Encabezado de norma: va SOLO en su línea y en mayúscula. Las citas dentro del
# texto («Decreto número 1171 de 2026») van en minúscula y a mitad de párrafo,
# así que anclar en línea completa y mayúscula es lo que las separa.
_CAB = re.compile(
    r'^\s*(DECRETO(?:\s+LEGISLATIVO)?|LEY(?:\s+ESTATUTARIA|\s+ORG[ÁA]NICA)?|ACTO\s+LEGISLATIVO)\s+'
    r'(?:N[ÚU]MERO|NO\.|N[°º]\.?)?\s*(\d{1,5})\s+DE\s*(?:DE\s+)?(\d{4})[a-z]?\s*$', re.M)
# Erratas reales de la Imprenta (medido ago-sep 2026): «DE2026», «DE DE 2026»,
# «DE 2026i». Y la fecha entre paréntesis viene como «(agosto 19)» o como
# «(5 de agosto)», y a veces NO viene (decretos 1074 y 1417): entonces se toma
# la fórmula de cierre «Dada en Bogotá, D. C., a 18 de agosto de 2026».
_FECHA_PAR = re.compile(
    r'^\s*\(\s*(?:([a-záéíóú]+)\s+(\d{1,2})|(\d{1,2})\s+de\s+([a-záéíóú]+))'
    r'\s*(?:de\s+(\d{4}))?\s*\)', re.I)
_DADA = re.compile(r'(?:Dad[oa]|Expedid[oa])(?:\s+en\s+[^\n]{0,40}?)?,?\s*a\s*(?:los\s+)?(\d{1,2})\s+'
                   r'(?:d[íi]as?\s+del?\s+mes\s+de\s+|de\s+)([a-záéíóú]+)\s+(?:del?\s+)?(?:a[ñn]o\s+)?(\d{4})', re.I)
# Casi ningún decreto legislativo lo dice en su encabezado («DECRETO NÚMERO
# 1379»): lo delata el rótulo de sección o que invoque el artículo 215.
_LEGIS = re.compile(r'art[íi]culo\s+215\s+de\s+la\s+Constituci', re.I)
_FIN_EPI = re.compile(
    r'^\s*(El\s+(?:Presidente|Vicepresidente|Ministro|Ministra|Congreso|Director|Directora)\b'
    r'|La\s+(?:Ministra|Presidenta|Directora)\b|EL\s+CONGRESO|DECRETA\b|CONSIDERANDO)', re.M)
_PAGINA = re.compile(r'^=====PAGINA (\d+)=====$', re.M)

TIPO_CANON = {'DECRETO': 'DECRETOS', 'DECRETO LEGISLATIVO': 'DECRETOS',
              'LEY': 'LEYES', 'LEY ESTATUTARIA': 'LEYES', 'LEY ORGANICA': 'LEYES',
              'LEY ORGÁNICA': 'LEYES', 'ACTO LEGISLATIVO': 'ACTOS LEGISLATIVOS'}


def _limpio(s):
    s = re.sub(r'\s+', ' ', s).strip()
    return re.sub(r'(\w)- (\w)', r'\1\2', s)      # guion de partición de línea


def _fecha(anio, mes, dia):
    try:
        return datetime.date(int(anio), int(mes), int(dia)).isoformat() if mes else ''
    except (TypeError, ValueError):
        return ''


def extraer(paginas, edicion, fecha_pub):
    """Normas de una edición → filas con el esquema de normativa.jsonl."""
    texto = ''.join(f'\n=====PAGINA {i}=====\n{t}' for i, t in enumerate(paginas, 1))
    pags = [(m.start(), int(m.group(1))) for m in _PAGINA.finditer(texto)]

    def pagina_de(pos):
        p = 1
        for ini, n in pags:
            if ini > pos:
                break
            p = n
        return p

    filas, vistos = [], set()
    for m in _CAB.finditer(texto):
        tipo_raw = re.sub(r'\s+', ' ', m.group(1).upper())
        numero, anio = str(int(m.group(2))), m.group(3)
        # todo lo que se mira de esta norma termina en el siguiente encabezado:
        # si no, el 1346 (un nombramiento) heredaba el «artículo 215» del
        # decreto legislativo que venía detrás y salía marcado como legislativo
        sig = _CAB.search(texto, m.end())
        fin_norma = sig.start() if sig else len(texto)
        resto = texto[m.end():min(m.end() + 2500, fin_norma)]
        mf = _FECHA_PAR.match(resto.lstrip('\n'))
        fecha, fecha_origen = '', ''
        if mf:
            mes = MESES.get((mf.group(1) or mf.group(4) or '').lower())
            dia = mf.group(2) or mf.group(3)
            fecha = _fecha(mf.group(5) or anio, mes, dia)
            fecha_origen = 'encabezado'
            cuerpo = resto.lstrip('\n')[mf.end():]
        else:
            cuerpo = resto
        if not fecha:
            # sin paréntesis: la fórmula de cierre, dentro de ESTA norma (hasta
            # el siguiente encabezado), nunca la de la norma de al lado
            tramo = texto[m.end():min(fin_norma, m.end() + 200000)]
            dd = list(_DADA.finditer(tramo))
            if dd:
                fecha = _fecha(dd[-1].group(3), MESES.get(dd[-1].group(2).lower()), dd[-1].group(1))
                fecha_origen = 'formula_cierre'
        # sin fecha no es un encabezado de norma (p. ej. una ley citada en un
        # listado de «normas que se derogan»): se descarta antes que inventarla.
        if not fecha:
            continue
        # la norma se reimprime cuando corrige un yerro o se publica completa
        # otra vez: una sola fila por (tipo, número, año) y edición
        llave = (TIPO_CANON[tipo_raw], numero, anio)
        if llave in vistos:
            continue
        cuerpo = _PAGINA.sub(' ', cuerpo)
        fin = _FIN_EPI.search(cuerpo)
        epi = _limpio(cuerpo[:fin.start()] if fin else cuerpo[:600])
        if not re.match(r'(?i)por\s+(?:el|la|medio)\b|mediante\b', epi):
            # sin epígrafe «por el cual…» es una cita suelta en mayúscula, no una norma
            continue
        epi = epi[:1].upper() + epi[1:]
        vistos.add(llave)
        d = datetime.date.fromisoformat(fecha)
        pal = tipo_raw
        titulo = f'{pal} No. {numero} DEL {d.day} DE {MES_NOMBRE[d.month]} DE {anio}'
        pag = pagina_de(m.start())
        filas.append({
            'tipo': TIPO_CANON[tipo_raw],
            'numero': numero,
            'anio': anio,
            'fecha': fecha,
            'titulo': titulo,
            'descripcion': epi[:1200],
            'url': '',
            'fuente': 'diario_oficial',
            'legislativo': (tipo_raw == 'DECRETO LEGISLATIVO'
                            or (tipo_raw.startswith('DECRETO')
                                and ('Decretos Legislativos' in texto[max(0, m.start() - 120):m.start()]
                                     or bool(_LEGIS.search(cuerpo[:3000]))))
                            or None),
            'publicacion': {'edicion': edicion, 'fecha': fecha_pub, 'pagina': pag},
            'fecha_origen': fecha_origen,
        })
    for f in filas:
        if f['legislativo'] is None:
            del f['legislativo']
    return filas


# ─────────────────────────── orquestación ───────────────────────────

def _txt_cache(numero):
    return CACHE / f"{numero.replace('.', '')}.txt"


def paginas_de(s, ed):
    """Texto de la edición, del caché o bajando el PDF (que no se guarda)."""
    c = _txt_cache(ed['numero'])
    if c.exists():
        return c.read_text(encoding='utf-8').split('\f')
    with tempfile.NamedTemporaryFile(suffix='.pdf') as tmp:
        s.pdf(ed['numero'], tmp.name)
        paginas = pdf_a_texto(tmp.name)
    CACHE.mkdir(parents=True, exist_ok=True)
    c.write_text('\f'.join(paginas), encoding='utf-8')
    return paginas


def fetch(desde, hasta):
    s = Sesion()
    eds = listar(s, desde, hasta)
    print(f'  {len(eds)} ediciones del {desde} al {hasta}')
    previas = {}
    if SALIDA.exists():
        prev = json.loads(SALIDA.read_text(encoding='utf-8'))
        for f in prev.get('normas', []):
            previas[(f['tipo'], f['numero'], f['anio'])] = f
    ediciones_ok, fallidas = [], []
    for ed in eds:
        paginas, error = None, None
        for intento in range(2):                     # el servidor da timeouts sueltos
            try:
                paginas = paginas_de(s, ed)
                break
            except Exception as e:                   # una edición rota no tumba el resto
                error = e
                time.sleep(5)
                try:
                    s = Sesion()                     # la sesión JSF puede quedar sucia
                except Exception:
                    pass
        if paginas is None:
            fallidas.append({'edicion': ed['numero'], 'error': str(error)[:200]})
            print(f"  ! {ed['numero']} {ed['fecha']}: {error}", file=sys.stderr)
            continue
        normas = extraer(paginas, ed['numero'], ed['fecha'])
        for f in normas:
            k = (f['tipo'], f['numero'], f['anio'])
            # si ya estaba de una edición anterior, se conserva la PRIMERA
            # publicación (la reimpresión por corrección no cambia la norma)
            if k not in previas or previas[k]['publicacion']['fecha'] > ed['fecha']:
                previas[k] = f
        ediciones_ok.append({**ed, 'paginas': len(paginas), 'normas': len(normas)})
        print(f"  ok  {ed['numero']:>7} {ed['fecha']} {ed['tipo_edicion'][:12]:12} "
              f"{len(paginas):>4} pág · {len(normas):>3} normas")
    if not ediciones_ok:
        print('  ninguna edición se pudo leer: no se toca la salida', file=sys.stderr)
        return False
    ultima = max(e['fecha'] for e in ediciones_ok)
    prev_meta = {}
    if SALIDA.exists():
        prev_meta = json.loads(SALIDA.read_text(encoding='utf-8'))
    salida = {
        'generado': datetime.datetime.now().isoformat(timespec='seconds'),
        'fuente': {'nombre': 'Diario Oficial · Imprenta Nacional de Colombia',
                   'url': BASE + '/diario/', 'frecuencia': 'Diaria'},
        # «hasta» = la edición más reciente LEÍDA; nunca retrocede
        'cobertura': {'desde': min(desde.isoformat(),
                                   (prev_meta.get('cobertura') or {}).get('desde') or '9999'),
                      'hasta': max(ultima, (prev_meta.get('cobertura') or {}).get('hasta') or '')},
        'ediciones': ediciones_ok,
        'fallidas': fallidas,
        'normas': sorted(previas.values(), key=lambda f: (f['fecha'], f['tipo'], int(f['numero']))),
    }
    RAW.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"  {len(salida['normas'])} normas acumuladas · cobertura hasta {salida['cobertura']['hasta']}"
          f" · {len(fallidas)} ediciones fallidas → {SALIDA.relative_to(REPO)}")
    # fallar si se cayó más de la mitad: mejor el índice de ayer que uno a medias
    return len(fallidas) <= len(eds) // 2


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    fp = sub.add_parser('fetch')
    fp.add_argument('--dias', type=int, default=45)
    fp.add_argument('--desde', default=None, help='YYYY-MM-DD')
    fp.add_argument('--hasta', default=None, help='YYYY-MM-DD')
    ep = sub.add_parser('extraer')
    ep.add_argument('edicion')
    a = ap.parse_args()
    if a.cmd == 'fetch':
        hasta = datetime.date.fromisoformat(a.hasta) if a.hasta else datetime.date.today()
        desde = (datetime.date.fromisoformat(a.desde) if a.desde
                 else hasta - datetime.timedelta(days=a.dias))
        sys.exit(0 if fetch(desde, hasta) else 1)
    elif a.cmd == 'extraer':
        s = Sesion()
        num = a.edicion.replace('.', '')
        eds = _filas(s.buscar(numeroDiarioOf=num))
        if not eds:
            sys.exit(f'no existe la edición {a.edicion}')
        for f in extraer(paginas_de(s, eds[0]), eds[0]['numero'], eds[0]['fecha']):
            print(json.dumps(f, ensure_ascii=False))


if __name__ == '__main__':
    main()
