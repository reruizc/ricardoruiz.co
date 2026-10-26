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
        # El id del botón «Ver Diario» lo numera JSF y cambia cuando la Imprenta
        # toca la página: era j_idt34 y el 9-oct-2026 pasó a j_idt41, y desde
        # entonces no se leyó ninguna edición. Se toma de la propia respuesta.
        ri = filas[0]['ri']
        ids = re.findall(rf'dtbDiariosOficiales:{ri}:(j_idt\d+)', h)
        if not ids:
            raise RuntimeError(f'la fila de la edición {numero} no trae el botón «Ver Diario»')
        d[f'dtbDiariosOficiales:{ri}:{ids[-1]}'] = ''
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


# ─────────────── resoluciones, circulares y acuerdos (oct-2026) ───────────────
#
# El pilar Ejecutivo solo toma decretos y leyes, pero cada edición trae además
# ~18 resoluciones, circulares y acuerdos de ministerios, superintendencias,
# agencias y corporaciones — muchas de ellas en ninguna otra fuente que Caudal
# lea (MinHacienda y la web de Presidencia tienen antibots; MinCultura no
# publica las de 2026). Van a un índice APARTE (`dist/diario-oficial-actos.jsonl`)
# para no llenar el pilar Ejecutivo de nombramientos ministeriales.
#
# Cómo se sabe de qué entidad es cada acto: el cuerpo de la edición pone la
# entidad justo encima de un rótulo de tipo en plural («Ministerio del Trabajo /
# Resoluciones / RESOLUCIÓN NÚMERO 2563 DE 2026»). El rótulo solo encabeza el
# PRIMER acto de cada entidad: los siguientes la heredan. Encima de la entidad
# puede venir un grupo («Establecimientos Públicos», «Superintendencias») que no
# es la entidad y se guarda aparte. El sumario del final también agrupa por
# entidad, pero pymupdf lo devuelve con las columnas mezcladas: no sirve.

_ACTO_CAB = re.compile(
    r'^\s*((?:RESOLUCI[ÓO]N|CIRCULAR|ACUERDO|DIRECTIVA)[A-ZÁÉÍÓÚÑ ]{0,40}?)\s+'
    r'(?:N[ÚU]MERO|NO\.|N[°º]\.?)\s*([0-9][0-9A-Z.\-]*)\s+DE\s*(\d{4})[a-z]?\s*$')
_ROTULO = re.compile(
    r'^\s*(Resoluciones(?:\s+(?:Ejecutivas|ejecutivas|Conjuntas|conjuntas|Org[áa]nicas|Reglamentarias))?'
    r'|RESOLUCIONES|Circulares(?:\s+(?:Externas|externas|Conjuntas|Arancelarias))?|CIRCULARES'
    r'|Acuerdos|ACUERDOS|Directivas(?:\s+Presidenciales)?|Decretos|DECRETOS|Leyes|LEYES'
    r'|Autos|Edictos|Avisos|Actos\s+Legislativos)\s*$')
# Grupos de entidades: van encima de la entidad y no son ella.
_GRUPOS = {
    'establecimientos publicos', 'superintendencias', 'unidades administrativas especiales',
    'agencias nacionales de naturaleza especial', 'agencias nacionales',
    'corporaciones autonomas regionales', 'entes universitarios autonomos',
    'departamentos administrativos', 'empresas industriales y comerciales del estado',
    'empresas sociales del estado', 'sociedades de economia mixta', 'organismos de control',
    'entidades descentralizadas', 'fondos', 'consejos superiores', 'ministerios',
    'institutos de investigacion', 'entidades financieras de naturaleza especial',
    'organizacion electoral', 'rama judicial', 'entidades del orden departamental',
    'entidades del orden municipal', 'otras entidades',
}
_VARIOS = re.compile(r'^\s*(V\s?a\s?r\s?i\s?o\s?s|VARIOS)\s*$')
# Cabezas con que arranca una dependencia DENTRO de la entidad.
_DEPENDENCIA = re.compile(
    r'\s(?=(?:Direcci[óo]n Territorial|Territorial|Subdirecci[óo]n|Viceministerio|Oficina|'
    r'Secretar[íi]a|Grupo|Direcci[óo]n de [A-ZÁÉÍÓÚ]|Direcci[óo]n General de|Direcci[óo]n Seccional|'
    r'Direcci[óo]n Regional|Vicepresidencia|Delegatura|Superintendencia Delegada|Direcci[óo]n General$|'
    r'Consejo (?:Superior|Directivo|Acad[ée]mico)|Comisi[óo]n Rectora|Director(?:a)? del))')
# Una «entidad» que en realidad es dependencia hereda la entidad anterior.
_SOLO_DEP = re.compile(r'^(?:Bogot[áa]\s*-|Direcci[óo]n Territorial|Territorial|Subdirecci[óo]n|Viceministerio|Oficina|'
                       r'Secretar[íi]a(?! de (?:Salud|Educaci|Hacienda|Planeaci))|Grupo|Delegatura|'
                       r'Direcci[óo]n de Gesti[óo]n|Vicepresidencia)\b')
# Palabras con que empieza una entidad: lo que viene antes (firmas, filas de
# tabla) se corta.
_CABEZA = re.compile(
    r'\b(Ministerio|Superintendencia|Departamento|Instituto|Agencia|Unidad|Comisi[óo]n|Corporaci[óo]n|'
    r'Direcci[óo]n de Impuestos|Direcci[óo]n General Mar[íi]tima|Direcci[óo]n de Comercio Exterior|'
    r'Direcci[óo]n Nacional|Parques Nacionales|Consejo|Fondo|Caja|Gobernaci[óo]n|Alcald[íi]a|Servicio|'
    r'Escuela|Universidad|Instituci[óo]n Universitaria|Empresa|Banco|Jurisdicci[óo]n|Contralor[íi]a|'
    r'Procuradur[íi]a|Registradur[íi]a|Defensor[íi]a|Fiscal[íi]a|Aeron[áa]utica|Polic[íi]a|Administradora|'
    r'Imprenta|Comit[ée]|Junta|[ÁA]rea Metropolitana|Distrito|Concejo|Asamblea|Autoridad|Fiduciaria|'
    r'Colpensiones|Presidencia|Tribunal|Corte|Sala|Archivo General|Biblioteca|Museo|Hospital|'
    r'Entidad Promotora|Positiva|Ecopetrol|Computadores para Educar|Territorial|Secretar[íi]a)\b')
# Grupos que a veces vienen pegados a la entidad (o con basura delante).
_GRUPO_EN = re.compile(
    r'(?i)\b(Establecimientos P[úu]blicos|Superintendencias(?!\s+de)|Unidades Administrativas Especiales|'
    r'Agencias Nacionales(?: de Naturaleza Especial)?|Corporaciones Aut[óo]nomas Regionales|'
    r'Entes Universitarios Aut[óo]nomos|Entidades Financieras de Naturaleza (?:Especial|[ÚU]nica)|'
    r'Empresas Industriales y Comerciales del Estado|Empresas Sociales del Estado|'
    r'Sociedades de Econom[íi]a Mixta|Departamentos Administrativos|Edici[óo]n Extraordinaria|'
    r'Empresas? Industriale?s? y Comercial(?:es)? del Estado)\b')
_RUIDO = re.compile(
    r'^\s*(DIARIO OFICIAL|Edici[óo]n\s+[\d.]+|\d{1,4}|[A-ZÁ][a-zé]+,\s+\d{1,2}\s+de\s+[a-z]+\s+de\s+\d{4}'
    r'|I S S N.*|ISSN.*|Fundado el .*|Rep[úu]blica de Colombia|A[ñn]o CLX.*|IMPRENTA NACIONAL.*'
    r'|e-mail:.*|Carrera 66.*|Conmutador.*|P[áa]gs?\.?|Imprenta Nacional de Colombia|Alba Viviana.*'
    r'|Gerente General|Tarifa postal.*|Directora?\s*:.*|MINISTERIO DEL INTERIOR|Por el Presidente Manuel Murillo Toro)\s*$')
_MINUSC = {'de', 'del', 'la', 'las', 'los', 'el', 'y', 'e', 'para', 'por', 'en', 'a', 'al', 'o', 'u'}


def _fold(s):
    import unicodedata
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()


def _caso(s):
    """«MinistErio dE coMErcio» (versalitas mal extraídas) → «Ministerio de Comercio».
    Solo se toca lo que viene con mayúsculas a mitad de palabra."""
    if not re.search(r'[a-zá-ú][A-ZÁ-Ú]', s):
        return s
    pal = s.lower().split()
    return ' '.join(p if (i and p in _MINUSC) else p[:1].upper() + p[1:] for i, p in enumerate(pal))


def _es_grupo(s):
    return _fold(re.sub(r'\s+', ' ', s)).strip(' .') in _GRUPOS


def _entidad_de(lineas):
    """Líneas que preceden a un rótulo (de arriba abajo) → (grupo, entidad, dependencia, varios)."""
    tomadas = []
    for l in reversed(lineas):
        t = l.strip()
        if not t or _RUIDO.match(t):
            if tomadas:
                break
            continue
        if _VARIOS.match(t):
            tomadas.append('\x00VARIOS')
            break
        # fin de la norma anterior: firma, «(C. F.).», cifras de pago
        if re.search(r'[.;:)]$', t) or re.match(r'(?:El|La|Los|Las)\s', t) and t.endswith(','):
            break
        if re.search(r'Valor\s+\$|Recibo\s+Banco|@|\d|Tarifa postal|Directora?\s*:', t):
            break                                   # filas de tabla, pie de imprenta
        if t.isupper() and not re.search(r'MINISTERIO|SUPERINTENDENCIA|DEPARTAMENTO|INSTITUTO|AGENCIA|UNIDAD|COMISI', t):
            break                                   # «ABELARDO DE LA ESPRIELLA»
        tomadas.append(t)
        if len(tomadas) >= 6:
            break
    varios = '\x00VARIOS' in tomadas
    tomadas = [x for x in reversed(tomadas) if x != '\x00VARIOS']
    grupo = ''
    # el grupo puede venir partido en dos líneas («Agencias Nacionales / de Naturaleza Especial»)
    for k in (2, 1):
        if len(tomadas) > k - 1 and _es_grupo(' '.join(tomadas[:k])):
            grupo, tomadas = ' '.join(tomadas[:k]), tomadas[k:]
            break
    if varios and not grupo:
        grupo = 'Varios'
    texto = _caso(re.sub(r'\s+', ' ', ' '.join(tomadas))).strip(' ,')
    texto = re.sub(r'(\w)- (\w)', r'\1\2', texto)
    g2 = list(_GRUPO_EN.finditer(texto))
    if g2:                                          # grupo pegado: se separa
        if not grupo and not g2[-1].group(1).lower().startswith('edici'):
            grupo = g2[-1].group(1)
        texto = texto[g2[-1].end():].strip(' ,-–&)')
    c = _CABEZA.search(texto)
    if c and c.start() > 0:                         # firma o basura delante
        texto = texto[c.start():]
    # dos ministerios seguidos: el primero es resto de la sección anterior
    mins = [m.start() for m in re.finditer(r'\bMinisterio\b', texto)]
    if len(mins) > 1:
        texto = texto[mins[-1]:]
    texto = _normal_entidad(texto)
    if not texto:
        return grupo, '', '', varios
    m = _DEPENDENCIA.search(texto, 12)
    if m:
        return grupo, texto[:m.start()].strip(' ,-–'), texto[m.start():].strip(' ,-–'), varios
    return grupo, texto, '', varios


# Variantes con que la Imprenta escribe el mismo ministerio (medido ago-oct 2026).
_CANON = {
    'ministerio de justicia del derecho': 'Ministerio de Justicia y del Derecho',
    'ministerio de vivienda ciudad y territorio': 'Ministerio de Vivienda, Ciudad y Territorio',
    'ministerio de comercio industria y turismo': 'Ministerio de Comercio, Industria y Turismo',
    'direccion de impuestos y aduanas nacionales': 'Dirección de Impuestos y Aduanas Nacionales',
    'aeronautica civil': 'Unidad Administrativa Especial de Aeronáutica Civil',
    'unidad administrativa de aeronautica civil': 'Unidad Administrativa Especial de Aeronáutica Civil',
    'ministerio de trabajo': 'Ministerio del Trabajo',
    'ministerio comercio industria y turismo': 'Ministerio de Comercio, Industria y Turismo',
    'ministerio de las culturas los artes y los saberes': 'Ministerio de las Culturas, las Artes y los Saberes',
    'presidente de la republica de colombia': 'Presidencia de la República',
    'republica de colombia': 'Presidencia de la República',
}


def _normal_entidad(t):
    t = re.sub(r'^[^A-Za-zÁÉÍÓÚÑáéíóúñ]+', '', re.sub(r'\s+', ' ', t)).strip(' ,.-–')
    t = re.sub(r'^Superintendencias (de|del)\b', r'Superintendencia \1', t)
    # el firmante a veces queda como entidad: «Ministro de…», «Superintendenta de…»
    t = re.sub(r'^Ministr[oa] (de|del)\b', r'Ministerio \1', t)
    t = re.sub(r'^Superintendent[ea] (de|del)\b', r'Superintendencia \1', t)
    t = re.sub(r'^(?:UAE|U\.\s*A?\.?\s*E\.)\s+', '', t)
    # una cita que arrastra otra entidad delante: manda el ministerio
    mi = t.find('Ministerio ')
    if mi > 0:
        t = t[mi:]
    pal = t.split(' ')
    t = ' '.join(p.lower() if (i and p.lower() in _MINUSC - {'el'}) else p for i, p in enumerate(pal))
    k = re.sub(r'[^a-z ]', '', _fold(t)).strip()
    k = re.sub(r'\s+', ' ', k)
    return _CANON.get(k, t)


_FIRMANTE = re.compile(
    r'(?:^|\n)\s*(?:El|La)\s+(Ministr[oa]|Superintendente|Director[a]? General|Directora?|'
    r'Gerente General|Presidente|Presidenta|Contralor[a]? General|Registrador[a]? Nacional)\s+'
    r'(de|del|de la)\s+([A-ZÁÉÍÓÚ][^,\n]{3,90}?)(?:\s*\((?:e|E)\))?\s*,\s+en\s+(?:uso|ejercicio)')
_CARGO_ENT = {'ministro': 'Ministerio', 'ministra': 'Ministerio', 'superintendente': 'Superintendencia'}


def _entidad_firmante(cuerpo):
    """«El Ministro de Hacienda y Crédito Público, en uso de…» → la entidad.
    Respaldo para la primera sección de cada edición, cuyo nombre de entidad
    viaja en el encabezado gráfico y no sale en el texto."""
    m = _FIRMANTE.search(cuerpo[:3500])
    if not m:
        return ''
    cargo, prep, resto = m.group(1).lower(), m.group(2), m.group(3).strip()
    if cargo.startswith('president') and 'Rep' in resto:
        return 'Presidencia de la República'
    base = _CARGO_ENT.get(cargo)
    if base:
        return _normal_entidad(f'{base} {prep} {resto}')
    # «El Director General de la Unidad de…» → «Unidad de…»
    return _normal_entidad(resto[:1].upper() + resto[1:]) if prep == 'de la' or prep == 'del' else ''


_TIPO_ACTO = [('RESOLUCI', 'RESOLUCIONES'), ('CIRCULAR', 'CIRCULARES'),
              ('ACUERDO', 'ACUERDOS'), ('DIRECTIVA', 'DIRECTIVAS')]
_FIN_EPI_ACTO = re.compile(
    r'\n\s*(?:E[Ll]\s|L[Aa]s?\s|Los\s|CONSIDERANDO|RESUELVE|ACUERDA|DECRETA|Considerando|'
    r'Que\s|Teniendo en cuenta|En ejercicio)', re.M)


def _epigrafe_acto(cuerpo):
    """«por la cual…» hasta la fórmula de facultades. Las circulares no lo
    traen: ahí manda el «Asunto:». Sin ninguno de los dos, vacío."""
    c = cuerpo[:4000]
    m = re.search(r'(?im)^\s*((?:por|mediante)\s+(?:el|la|medio|los|las)?\b.*)', c)
    if m:
        resto = c[m.start(1):]
        f = _FIN_EPI_ACTO.search(resto)
        return _limpio(resto[:f.start()] if f else resto[:700])[:1200], 'epigrafe'
    m = re.search(r'(?is)\bAsunto\s*:\s*(.+?)(?:\n\s*\n|\n\s*(?:Fecha|Respetad|Cordial|Se[ñn]or|Apreciad))', c)
    if m:
        return _limpio(m.group(1))[:600], 'asunto'
    return '', ''


# Actos de personal y trámites individuales: son la mitad del Diario Oficial
# (medido: 580 de 1.375 en ago-oct 2026 son nombramientos) y no le cambian
# nada a nadie fuera de la persona. Se marcan, no se borran: la búsqueda puede
# mostrarlos y el radar del cliente los ignora.
_ADMIN = re.compile(
    r'(?i)\b(nombramientos?|se\s+nombra|renuncia|encargo|vacaciones|comisi[óo]n\s+de\s+servicios|'
    r'insubsistencia|retiro\s+del\s+servicio|extradici[óo]n|recurso\s+de\s+reposici[óo]n|'
    r'p[ée]rdida\s+de\s+ejecutoria|credencial\s+de\s+expendedor|se\s+ordena\s+una\s+entrega|'
    r'licencia\s+(?:no\s+)?remunerada|prima\s+t[ée]cnica|reconoce\s+(?:y\s+ordena\s+)?(?:el\s+)?pago|'
    r'destrucci[óo]n\s+de\s+mercanc|declara\s+(?:la\s+)?vacancia|designaci[óo]n\s+de\s+los?\s+representantes?|'
    r'reforma\s+estatutaria|personer[íi]a\s+jur[íi]dica|sin\s+[áa]nimo\s+de\s+lucro|clasificaci[óo]n\s+arancelaria)')


_MASTHEAD = re.compile(r'(?:lunes|martes|mi[ée]rcoles|jueves|viernes|s[áa]bado|domingo),\s*'
                       r'(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})', re.I)


def fecha_edicion(paginas):
    """Fecha de publicación leída del encabezado de la página 1."""
    m = _MASTHEAD.search(paginas[0][:1500] if paginas else '')
    if not m:
        return ''
    return _fecha(m.group(3), MESES.get(m.group(2).lower()), m.group(1))


def extraer_actos(paginas, edicion, fecha_pub):
    """Resoluciones, circulares, acuerdos y directivas de una edición."""
    lineas, pag_de = [], []
    for i, t in enumerate(paginas, 1):
        for l in t.split('\n'):
            lineas.append(l)
            pag_de.append(i)
    actos, vistos = [], set()
    ent = {'grupo': '', 'entidad': '', 'dependencia': '', 'varios': False}
    cabs = [i for i, l in enumerate(lineas) if _ACTO_CAB.match(l) or _CAB.match(l)]
    for i, l in enumerate(lineas):
        r = _ROTULO.match(l)
        if r:
            g, e, d, v = _entidad_de(lineas[max(0, i - 10):i])
            if e and _SOLO_DEP.match(e) and ent['entidad']:
                e, d = ent['entidad'], (e + (' ' + d if d else '')).strip()
                g = g or ent['grupo']
            if e:
                ent = {'grupo': g, 'entidad': e, 'dependencia': d,
                       'varios': v or ent['varios'] and not g}
            elif v:
                ent = {**ent, 'varios': True}
            continue
        m = _ACTO_CAB.match(l)
        if not m:
            continue
        tipo_raw = re.sub(r'\s+', ' ', m.group(1).upper()).strip()
        tipo = next((t for k, t in _TIPO_ACTO if tipo_raw.startswith(k)), 'OTROS')
        numero_raw, anio = m.group(2).rstrip('.'), m.group(3)
        numero = re.sub(r'^0+(?=\d)', '', numero_raw)
        sig = next((j for j in cabs if j > i), len(lineas))
        cuerpo_lin = [x for x in lineas[i + 1:min(sig, i + 400)] if not _RUIDO.match(x.strip())]
        cuerpo = '\n'.join(cuerpo_lin)
        mf = _FECHA_PAR.match(cuerpo.lstrip('\n'))
        fecha, origen = '', ''
        if mf:
            mes = MESES.get((mf.group(1) or mf.group(4) or '').lower())
            fecha = _fecha(mf.group(5) or anio, mes, mf.group(2) or mf.group(3))
            origen = 'encabezado'
            cuerpo = cuerpo.lstrip('\n')[mf.end():]
        if not fecha:
            dd = list(_DADA.finditer('\n'.join(lineas[i + 1:sig])))
            if dd:
                fecha = _fecha(dd[-1].group(3), MESES.get(dd[-1].group(2).lower()), dd[-1].group(1))
                origen = 'formula_cierre'
        if not fecha:
            fecha, origen = fecha_pub, 'publicacion'
        epi, epi_origen = _epigrafe_acto(cuerpo)
        if not epi:
            continue                       # cita en mayúscula, no un acto
        entidad, ent_origen = ent['entidad'], 'seccion'
        if not entidad:
            entidad, ent_origen = _entidad_firmante(cuerpo), 'firmante'
            if entidad:                       # la sección hereda lo inferido
                ent = {**ent, 'entidad': entidad}
        if not entidad and tipo_raw.startswith('RESOLUCI') and 'EJECUTIVA' in tipo_raw:
            entidad = 'Presidencia de la República'
        if not entidad and tipo == 'DIRECTIVAS':
            entidad = 'Presidencia de la República'
        llave = (tipo, _fold(entidad), numero, anio)
        if llave in vistos:
            continue
        vistos.add(llave)
        actos.append({
            'tipo': tipo,
            'subtipo': tipo_raw.title(),
            'numero': numero,
            'numero_original': numero_raw,
            'anio': anio,
            'fecha': fecha,
            'fecha_origen': origen,
            'entidad': entidad,
            'entidad_origen': ent_origen if entidad else '',
            'dependencia': ent['dependencia'],
            'grupo': ent['grupo'],
            'seccion': 'varios' if ent['varios'] else 'oficial',
            'descripcion': epi[:1].upper() + epi[1:],
            'descripcion_origen': epi_origen,
            'administrativo': bool(_ADMIN.search(epi[:300])),
            'publicacion': {'edicion': edicion, 'fecha': fecha_pub, 'pagina': pag_de[i]},
            'fuente': 'diario_oficial',
        })
    return actos


DIST = OUT / 'dist'
ACTOS = DIST / 'diario-oficial-actos.jsonl'
ACTOS_STATS = DIST / 'diario-oficial-actos-stats.json'


def actos():
    """Re-extrae los actos de TODAS las ediciones cacheadas → índice + stats.
    El caché de texto es la fuente de verdad: no hay estado que acumular."""
    import collections
    eds = sorted(CACHE.glob('*.txt'), key=lambda p: int(p.stem))
    filas, por_ed, sin_ent = {}, [], 0
    for p in eds:
        paginas = p.read_text(encoding='utf-8').split('\f')
        fpub = fecha_edicion(paginas)
        num = f'{int(p.stem):,}'.replace(',', '.')
        try:
            xs = extraer_actos(paginas, num, fpub)
        except Exception as e:                       # una edición rara no tumba el índice
            print(f'  ! {p.stem}: {e}', file=sys.stderr)
            continue
        for a in xs:
            k = (a['tipo'], _fold(a['entidad']), a['numero'], a['anio'])
            # primera publicación manda (las reimpresiones corrigen yerros)
            if k not in filas or (filas[k]['publicacion']['fecha'] or '9') > (fpub or '9'):
                filas[k] = a
        por_ed.append({'edicion': num, 'fecha': fpub, 'actos': len(xs)})
    orden = sorted(filas.values(), key=lambda a: (a['publicacion']['fecha'], a['tipo'], a['entidad']),
                   reverse=True)
    sin_ent = sum(1 for a in orden if not a['entidad'])
    if not orden:
        print('  sin actos: no se escribe el índice', file=sys.stderr)
        return False
    DIST.mkdir(parents=True, exist_ok=True)
    with ACTOS.open('w', encoding='utf-8') as fh:
        for a in orden:
            fh.write(json.dumps(a, ensure_ascii=False) + '\n')
    ents = collections.Counter(a['entidad'] for a in orden if a['seccion'] == 'oficial')
    stats = {
        'generado': datetime.datetime.now().isoformat(timespec='seconds'),
        'n': len(orden),
        'por_tipo': dict(collections.Counter(a['tipo'] for a in orden)),
        'por_seccion': dict(collections.Counter(a['seccion'] for a in orden)),
        'sin_entidad': sin_ent,
        'ediciones': len(por_ed),
        'cobertura': {'desde': min((e['fecha'] for e in por_ed if e['fecha']), default=''),
                      'hasta': max((e['fecha'] for e in por_ed if e['fecha']), default='')},
        'entidades': [{'entidad': e, 'n': n} for e, n in ents.most_common()],
    }
    ACTOS_STATS.write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"  {len(orden)} actos de {len(por_ed)} ediciones ({stats['cobertura']['desde']} a "
          f"{stats['cobertura']['hasta']}) · {len(ents)} entidades · {sin_ent} sin entidad → "
          f"{ACTOS.relative_to(REPO)}")
    return True


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
    sub.add_parser('actos', help='resoluciones, circulares y acuerdos de todo el caché')
    ep = sub.add_parser('extraer')
    ep.add_argument('edicion')
    a = ap.parse_args()
    if a.cmd == 'fetch':
        hasta = datetime.date.fromisoformat(a.hasta) if a.hasta else datetime.date.today()
        desde = (datetime.date.fromisoformat(a.desde) if a.desde
                 else hasta - datetime.timedelta(days=a.dias))
        sys.exit(0 if fetch(desde, hasta) else 1)
    elif a.cmd == 'actos':
        sys.exit(0 if actos() else 1)
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
