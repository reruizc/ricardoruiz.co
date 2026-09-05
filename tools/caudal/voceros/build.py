#!/usr/bin/env python3
"""
Caudal · diccionario de cuentas oficiales y voceros (pilar "Redes sociales
oficiales y voceros").

Es el hermano del diccionario de empresas (`tools/caudal/empresas.py`): una
lista CURADA de entidades del Estado, reguladores, órganos de control, cortes,
Congreso y gremios, con (1) su sitio oficial, (2) sus cuentas en redes y (3) el
CARGO que habla por ellas. Un cliente que vigila un sector sabe así a quién
seguir y a quién le va a llegar la pregunta cuando algo se mueva.

⚠️ Las cuentas NO se escriben de memoria: se leen del pie de página del sitio
oficial de cada entidad (la plantilla gov.co trae los enlaces a redes en el
footer) y quedan marcadas `verificado:'sitio'`. Las pocas que un sitio no
entrega —porque bloquea el fetch o no las publica— van en MANUAL con
`verificado:'manual'` y la página las muestra con ese rótulo. Una cuenta mal
atribuida en una página que se vende como diccionario es peor que un hueco.

⚠️ Los NOMBRES de las personas se dejan en `vocero` solo cuando Ricardo los
confirma: el gabinete cambió el 7-ago-2026 y adivinarlos es inventar. El campo
`cargo` sí es estable y es lo que se publica por defecto.

Uso:
  python3 tools/caudal/voceros/build.py            # scrapea y escribe caudal-voceros.js
  python3 tools/caudal/voceros/build.py --offline  # re-emite el JS desde el cache
Salida: caudal-voceros.js en la raíz (window.CAUDAL_VOCEROS), que carga
caudal-voceros.html. Cache del scrape en Bases de datos/caudal-voceros/raw.json.
"""
import json, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / 'caudal-voceros.js'
CACHE = REPO / 'Bases de datos' / 'caudal-voceros' / 'raw.json'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')

# tipo · sector (llaves del radar de Caudal) · sitio · cargo del vocero
# id, nombre, tipo, sectores, sitio, cargo
E = [
 # ── Ejecutivo nacional ─────────────────────────────────────────────────────
 ('presidencia','Presidencia de la República','ejecutivo',['todos'],'https://www.presidencia.gov.co','Presidente de la República'),
 ('minhacienda','Ministerio de Hacienda y Crédito Público','ejecutivo',['financiero','tributario','todos'],'https://www.minhacienda.gov.co','Ministro(a) de Hacienda'),
 ('minsalud','Ministerio de Salud y Protección Social','ejecutivo',['salud'],'https://www.minsalud.gov.co','Ministro(a) de Salud'),
 ('mintrabajo','Ministerio del Trabajo','ejecutivo',['trabajo'],'https://www.mintrabajo.gov.co','Ministro(a) del Trabajo'),
 ('mininterior','Ministerio del Interior','ejecutivo',['todos'],'https://www.mininterior.gov.co','Ministro(a) del Interior'),
 ('minjusticia','Ministerio de Justicia y del Derecho','ejecutivo',['juridico'],'https://www.minjusticia.gov.co','Ministro(a) de Justicia'),
 ('mindefensa','Ministerio de Defensa Nacional','ejecutivo',['seguridad'],'https://www.mindefensa.gov.co','Ministro(a) de Defensa'),
 ('minagricultura','Ministerio de Agricultura y Desarrollo Rural','ejecutivo',['agro'],'https://www.minagricultura.gov.co','Ministro(a) de Agricultura'),
 ('mincit','Ministerio de Comercio, Industria y Turismo','ejecutivo',['comercio','turismo','industria'],'https://www.mincit.gov.co','Ministro(a) de Comercio'),
 ('minenergia','Ministerio de Minas y Energía','ejecutivo',['energia','mineria'],'https://www.minenergia.gov.co','Ministro(a) de Minas y Energía'),
 ('minambiente','Ministerio de Ambiente y Desarrollo Sostenible','ejecutivo',['ambiental'],'https://www.minambiente.gov.co','Ministro(a) de Ambiente'),
 ('mintransporte','Ministerio de Transporte','ejecutivo',['transporte'],'https://www.mintransporte.gov.co','Ministro(a) de Transporte'),
 ('mineducacion','Ministerio de Educación Nacional','ejecutivo',['educacion'],'https://www.mineducacion.gov.co','Ministro(a) de Educación'),
 ('mintic','Ministerio de Tecnologías de la Información y las Comunicaciones','ejecutivo',['telecom','tecnologia'],'https://www.mintic.gov.co','Ministro(a) TIC'),
 ('minvivienda','Ministerio de Vivienda, Ciudad y Territorio','ejecutivo',['vivienda','agua'],'https://www.minvivienda.gov.co','Ministro(a) de Vivienda'),
 ('mincultura','Ministerio de las Culturas, las Artes y los Saberes','ejecutivo',['cultura'],'https://www.mincultura.gov.co','Ministro(a) de las Culturas'),
 ('cancilleria','Ministerio de Relaciones Exteriores','ejecutivo',['exterior'],'https://www.cancilleria.gov.co','Canciller'),
 ('minciencias','Ministerio de Ciencia, Tecnología e Innovación','ejecutivo',['tecnologia','educacion'],'https://www.minciencias.gov.co','Ministro(a) de Ciencia'),
 ('mindeporte','Ministerio del Deporte','ejecutivo',['deporte'],'https://www.mindeporte.gov.co','Ministro(a) del Deporte'),
 ('dnp','Departamento Nacional de Planeación','ejecutivo',['todos'],'https://www.dnp.gov.co','Director(a) del DNP'),
 ('dane','DANE','ejecutivo',['todos'],'https://www.dane.gov.co','Director(a) del DANE'),
 ('funcionpublica','Departamento Administrativo de la Función Pública','ejecutivo',['todos'],'https://www.funcionpublica.gov.co','Director(a) de Función Pública'),
 ('ungrd','Unidad Nacional para la Gestión del Riesgo de Desastres','ejecutivo',['todos'],'https://www.gestiondelriesgo.gov.co','Director(a) de la UNGRD'),
 # ── Superintendencias y reguladores ────────────────────────────────────────
 ('supersalud','Superintendencia Nacional de Salud','super',['salud'],'https://www.supersalud.gov.co','Superintendente Nacional de Salud'),
 ('superfinanciera','Superintendencia Financiera de Colombia','super',['financiero','seguros','pensiones'],'https://www.superfinanciera.gov.co','Superintendente Financiero'),
 ('sic','Superintendencia de Industria y Comercio','super',['competencia','datos personales','consumidor','propiedad intelectual'],'https://www.sic.gov.co','Superintendente de Industria y Comercio'),
 ('supersociedades','Superintendencia de Sociedades','super',['empresarial','financiero'],'https://www.supersociedades.gov.co','Superintendente de Sociedades'),
 ('supertransporte','Superintendencia de Transporte','super',['transporte','puertos'],'https://www.supertransporte.gov.co','Superintendente de Transporte'),
 ('superservicios','Superintendencia de Servicios Públicos Domiciliarios','super',['energia','agua','telecom'],'https://www.superservicios.gov.co','Superintendente de Servicios Públicos'),
 ('supervigilancia','Superintendencia de Vigilancia y Seguridad Privada','super',['seguridad privada'],'https://www.supervigilancia.gov.co','Superintendente de Vigilancia'),
 ('supersubsidio','Superintendencia del Subsidio Familiar','super',['trabajo','cajas de compensacion'],'https://www.ssf.gov.co','Superintendente del Subsidio Familiar'),
 ('supernotariado','Superintendencia de Notariado y Registro','super',['vivienda','juridico'],'https://www.supernotariado.gov.co','Superintendente de Notariado'),
 ('anla','Autoridad Nacional de Licencias Ambientales','regulador',['ambiental','mineria','energia'],'https://www.anla.gov.co','Director(a) de la ANLA'),
 ('invima','INVIMA','regulador',['salud','alimentos','farmaceutico'],'https://www.invima.gov.co','Director(a) del INVIMA'),
 ('dian','DIAN','regulador',['tributario','aduanas','todos'],'https://www.dian.gov.co','Director(a) de la DIAN'),
 ('crc','Comisión de Regulación de Comunicaciones','regulador',['telecom','medios'],'https://www.crcom.gov.co','Director(a) ejecutivo(a) de la CRC'),
 ('creg','Comisión de Regulación de Energía y Gas','regulador',['energia'],'https://www.creg.gov.co','Director(a) ejecutivo(a) de la CREG'),
 ('cra','Comisión de Regulación de Agua Potable y Saneamiento Básico','regulador',['agua'],'https://www.cra.gov.co','Director(a) ejecutivo(a) de la CRA'),
 ('aerocivil','Aeronáutica Civil','regulador',['aviacion','transporte'],'https://www.aerocivil.gov.co','Director(a) de la Aerocivil'),
 ('ani','Agencia Nacional de Infraestructura','regulador',['obra publica','transporte'],'https://www.ani.gov.co','Presidente de la ANI'),
 ('invias','INVÍAS','regulador',['obra publica','transporte'],'https://www.invias.gov.co','Director(a) del INVÍAS'),
 ('anm','Agencia Nacional de Minería','regulador',['mineria'],'https://www.anm.gov.co','Presidente de la ANM'),
 ('anh','Agencia Nacional de Hidrocarburos','regulador',['energia','hidrocarburos'],'https://www.anh.gov.co','Presidente de la ANH'),
 ('ugpp','UGPP','regulador',['trabajo','pensiones','tributario'],'https://www.ugpp.gov.co','Director(a) de la UGPP'),
 ('colombiacompra','Colombia Compra Eficiente','regulador',['contratacion'],'https://www.colombiacompra.gov.co','Director(a) de Colombia Compra Eficiente'),
 ('banrep','Banco de la República','autonomo',['financiero','todos'],'https://www.banrep.gov.co','Gerente General del Banco de la República'),
 ('uiaf','UIAF','regulador',['financiero','lavado de activos'],'https://www.uiaf.gov.co','Director(a) de la UIAF'),
 ('migracion','Migración Colombia','regulador',['exterior','trabajo'],'https://www.migracioncolombia.gov.co','Director(a) de Migración Colombia'),
 ('ica','ICA','regulador',['agro','alimentos'],'https://www.ica.gov.co','Gerente General del ICA'),
 ('jcc','Junta Central de Contadores','regulador',['juridico','contable'],'https://www.jcc.gov.co','Director(a) de la Junta Central de Contadores'),
 ('cne','Consejo Nacional Electoral','autonomo',['electoral'],'https://www.cne.gov.co','Presidente del CNE'),
 ('registraduria','Registraduría Nacional del Estado Civil','autonomo',['electoral'],'https://www.registraduria.gov.co','Registrador(a) Nacional'),
 # ── Órganos de control ─────────────────────────────────────────────────────
 ('procuraduria','Procuraduría General de la Nación','control',['todos'],'https://www.procuraduria.gov.co','Procurador(a) General'),
 ('contraloria','Contraloría General de la República','control',['contratacion','todos'],'https://www.contraloria.gov.co','Contralor(a) General'),
 ('fiscalia','Fiscalía General de la Nación','control',['juridico','todos'],'https://www.fiscalia.gov.co','Fiscal General'),
 ('defensoria','Defensoría del Pueblo','control',['todos'],'https://www.defensoria.gov.co','Defensor(a) del Pueblo'),
 ('auditoria','Auditoría General de la República','control',['contratacion'],'https://www.auditoria.gov.co','Auditor(a) General'),
 # ── Altas cortes ───────────────────────────────────────────────────────────
 ('corteconstitucional','Corte Constitucional','cortes',['juridico','todos'],'https://www.corteconstitucional.gov.co','Presidente de la Corte Constitucional'),
 ('consejodeestado','Consejo de Estado','cortes',['juridico','contratacion','tributario'],'https://www.consejodeestado.gov.co','Presidente del Consejo de Estado'),
 ('cortesuprema','Corte Suprema de Justicia','cortes',['juridico','trabajo'],'https://cortesuprema.gov.co','Presidente de la Corte Suprema'),
 ('judicatura','Consejo Superior de la Judicatura','cortes',['juridico'],'https://www.ramajudicial.gov.co','Presidente del Consejo Superior de la Judicatura'),
 ('jep','Jurisdicción Especial para la Paz','cortes',['juridico'],'https://www.jep.gov.co','Presidente de la JEP'),
 # ── Congreso ───────────────────────────────────────────────────────────────
 ('senado','Senado de la República','legislativo',['todos'],'https://www.senado.gov.co','Presidente del Senado'),
 ('camara','Cámara de Representantes','legislativo',['todos'],'https://www.camara.gov.co','Presidente de la Cámara'),
 # ── Gremios ────────────────────────────────────────────────────────────────
 ('andi','ANDI · Asociación Nacional de Empresarios','gremio',['industria','empresarial','todos'],'https://www.andi.com.co','Presidente de la ANDI'),
 ('fenalco','Fenalco','gremio',['comercio','retail'],'https://www.fenalco.com.co','Presidente de Fenalco'),
 ('asobancaria','Asobancaria','gremio',['financiero'],'https://www.asobancaria.com','Presidente de Asobancaria'),
 ('sac','Sociedad de Agricultores de Colombia','gremio',['agro'],'https://sac.org.co','Presidente de la SAC'),
 ('fedegan','Fedegán','gremio',['agro','ganaderia'],'https://www.fedegan.org.co','Presidente de Fedegán'),
 ('camacol','Camacol','gremio',['vivienda','construccion'],'https://camacol.co','Presidente de Camacol'),
 ('analdex','Analdex','gremio',['comercio exterior','aduanas'],'https://www.analdex.org','Presidente de Analdex'),
 ('acopi','Acopi','gremio',['pymes','industria'],'https://acopi.org.co','Presidente de Acopi'),
 ('acp','ACP · Asociación Colombiana del Petróleo y Gas','gremio',['energia','hidrocarburos'],'https://acp.com.co','Presidente de la ACP'),
 ('andesco','Andesco','gremio',['energia','agua','telecom'],'https://www.andesco.org.co','Presidente de Andesco'),
 ('asocana','Asocaña','gremio',['agro','palma y biocombustibles'],'https://www.asocana.org','Presidente de Asocaña'),
 ('fedepalma','Fedepalma','gremio',['palma y biocombustibles','agro'],'https://fedepalma.org','Presidente de Fedepalma'),
 ('fnc','Federación Nacional de Cafeteros','gremio',['agro','cafe'],'https://federaciondecafeteros.org','Gerente General de la FNC'),
 ('acemi','ACEMI','gremio',['salud','eps'],'https://www.acemi.org.co','Presidente de ACEMI'),
 ('asofondos','Asofondos','gremio',['pensiones','financiero'],'https://www.asofondos.org.co','Presidente de Asofondos'),
 ('fasecolda','Fasecolda','gremio',['seguros'],'https://fasecolda.com','Presidente de Fasecolda'),
 ('cotelco','Cotelco','gremio',['turismo'],'https://cotelco.org','Presidente de Cotelco'),
 ('anato','Anato','gremio',['turismo','aviacion'],'https://anato.org','Presidente de Anato'),
 ('cci','Cámara Colombiana de la Infraestructura','gremio',['obra publica','contratacion'],'https://www.infraestructura.org.co','Presidente de la CCI'),
 ('cgn','Consejo Gremial Nacional','gremio',['empresarial','todos'],'https://www.cgn.org.co','Presidente del Consejo Gremial'),
 ('acolgen','Acolgen','gremio',['energia'],'https://www.acolgen.org.co','Presidente de Acolgen'),
 ('naturgas','Naturgas','gremio',['energia','gas'],'https://naturgas.com.co','Presidente de Naturgas'),
 ('asoenergia','Asoenergía','gremio',['energia','industria'],'https://asoenergia.com','Presidente de Asoenergía'),
 ('colfecar','Colfecar','gremio',['transporte','logistica'],'https://www.colfecar.org.co','Presidente de Colfecar'),
 ('asobares','Asobares','gremio',['comercio','licores'],'https://asobares.org','Presidente de Asobares'),
 ('confecamaras','Confecámaras','gremio',['empresarial','todos'],'https://www.confecamaras.org.co','Presidente de Confecámaras'),
 ('ccb','Cámara de Comercio de Bogotá','gremio',['empresarial','todos'],'https://www.ccb.org.co','Presidente de la CCB'),
 ('acm','Asociación Colombiana de Minería','gremio',['mineria'],'https://acmineria.com.co','Presidente de la ACM'),
 ('afidro','AFIDRO','gremio',['farmaceutico','salud'],'https://afidro.org','Presidente de AFIDRO'),
 ('camara-electronica','Cámara Colombiana de Comercio Electrónico','gremio',['tecnologia','retail'],'https://www.ccce.org.co','Presidente de la CCCE'),
]

# Cuentas que el sitio no entrega (bloquea el fetch o no las publica en el
# footer). Solo cuentas institucionales conocidas; se publican rotuladas
# `manual`. Si el scrape sí las trae, el sitio manda.
MANUAL = {
 'presidencia':        {'x':'infopresidencia','instagram':'infopresidencia'},
 'minhacienda':        {'x':'MinHacienda'},
 'mindefensa':         {'x':'mindefensa'},
 'mindeporte':         {'x':'MinDeporteCol'},
 'dnp':                {'x':'DNP_Colombia'},
 'mintic':             {'x':'Ministerio_TIC'},
 'superservicios':     {'x':'Superservicios'},
 'invima':             {'x':'invimacolombia'},
 'banrep':             {'x':'BancoRepublica'},
 'registraduria':      {'x':'Registraduria'},
 'corteconstitucional':{'x':'CConstitucional'},
 'migracion':          {'x':'MigracionCol'},
}

# Nombres confirmados en PRENSA de la semana (titular que nombra cargo + persona,
# leído con la acción `medios` de Caudal). Solo entran los inequívocos; el resto
# de cargos se publica sin nombre. Fecha = la del titular que lo confirma.
VOCEROS = {
 'supersociedades':  ('Julia Eva Pretelt',     '2026-09-02', 'se posesionó como superintendente de Sociedades'),
 'minsalud':         ('Juan Carlos Aveiga',    '2026-09-05', 'ministro de Salud'),
 'mineducacion':     ('Ilva Myriam Hoyos',     '2026-09-03', 'ministra de Educación'),
 'cancilleria':      ('Omar Bula',             '2026-09-05', 'canciller · posesionó a los embajadores en EE. UU. y ONU'),
 'procuraduria':     ('Gregorio Eljach',       '2026-09-04', 'procurador general'),
 'contraloria':      ('Jorge Laverde',         '2026-09-02', 'contralor general'),
 'cne':              ('Juan Felipe Lemos',     '2026-09-03', 'llega a la presidencia del CNE'),
 'presidencia':      ('Abelardo de la Espriella', '2026-09-04', 'presidente de la República'),
}

PLAT = {
 'x':        re.compile(r'https?://(?:www\.|mobile\.)?(?:twitter\.com|x\.com)/([A-Za-z0-9_]{2,30})(?![\w/])', re.I),
 'instagram':re.compile(r'https?://(?:www\.)?instagram\.com/([A-Za-z0-9_.]{2,40})/?(?![\w])', re.I),
 'facebook': re.compile(r'https?://(?:www\.|m\.|es-la\.)?facebook\.com/([A-Za-z0-9_.\-]{3,60})/?(?![\w])', re.I),
 'youtube':  re.compile(r'https?://(?:www\.)?youtube\.com/((?:@|c/|channel/|user/)[A-Za-z0-9_\-]{2,60})', re.I),
 'tiktok':   re.compile(r'https?://(?:www\.)?tiktok\.com/@([A-Za-z0-9_.]{2,40})', re.I),
 'linkedin': re.compile(r'https?://(?:www\.)?linkedin\.com/(company/[A-Za-z0-9_\-]{2,80})', re.I),
}
# ruido que la plantilla y los píxeles de seguimiento meten en cualquier página
RUIDO = re.compile(r'^(tr|2008|accounts|explore|reel|p|sharer|share|dialog|plugins|intent|search|hashtag|home|login|privacy|policies|watch|embed|playlist|authwall|i|share\.php|sharer\.php|profile\.php|pages|groups|events|help)$', re.I)

def fetch(url):
    try:
        r = subprocess.run(['curl','-sL','-m','30','-A',UA,'--compressed',url],
                           capture_output=True, text=True, errors='replace')
        return r.stdout
    except Exception:
        return ''

def extrae(html):
    out = {}
    for k, rx in PLAT.items():
        for m in rx.finditer(html):
            h = m.group(1).rstrip('/')
            base = h.split('/')[-1] if k != 'youtube' else h
            if RUIDO.match(base) or base.lower().endswith('.php'):
                continue
            if k == 'linkedin' and 'admin' in h.lower():
                continue
            out[k] = h if k in ('youtube','linkedin') else base
            break
    return out

def scrape_todo():
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    def uno(e):
        eid, _, _, _, sitio, _ = e
        html = fetch(sitio)
        red = extrae(html) if html else {}
        print(f'  {eid:22s} {len(html)//1000:4d} KB  {sorted(red)}', file=sys.stderr)
        return eid, {'kb': len(html)//1000, 'redes': red}
    with ThreadPoolExecutor(8) as ex:
        raw = dict(ex.map(uno, E))
    CACHE.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding='utf-8')
    return raw

def emite(raw):
    items = []
    for eid, nombre, tipo, sectores, sitio, cargo in E:
        red = {k:v for k,v in ((raw.get(eid) or {}).get('redes') or {}).items()
               if not RUIDO.match(v.split('/')[-1])}   # el cache puede traer ruido de una corrida vieja
        ver = 'sitio' if red else ''
        # lo manual solo RELLENA plataformas que el sitio no entregó; nunca pisa
        manual = [k for k, v in MANUAL.get(eid, {}).items() if k not in red]
        for k in manual: red[k] = MANUAL[eid][k]
        if manual and not ver: ver = 'manual'
        v = VOCEROS.get(eid)
        items.append({'id':eid,'nombre':nombre,'tipo':tipo,'sectores':sectores,'sitio':sitio,
                      'cargo':cargo,'vocero':v[0] if v else '','vocero_fuente':f'prensa · {v[1]}' if v else '',
                      'redes':red,'verificado':ver,'manual':manual})
    n_sitio = sum(1 for i in items if i['verificado']=='sitio')
    n_manual = sum(1 for i in items if i['verificado']=='manual')
    n_vacio = sum(1 for i in items if not i['verificado'])
    n_voc = sum(1 for i in items if i['vocero'])
    meta = {'voceros_confirmados': n_voc, 'v': time.strftime('%Y-%m-%d'), 'n': len(items), 'verificados_sitio': n_sitio,
            'manual': n_manual, 'sin_cuentas': n_vacio}
    js = ('/* Generado por tools/caudal/voceros/build.py — NO editar a mano: las cuentas\n'
          '   salen del pie de página del sitio oficial de cada entidad. */\n'
          'window.CAUDAL_VOCEROS = ' + json.dumps({'meta':meta,'items':items}, ensure_ascii=False, indent=0) + ';\n')
    OUT.write_text(js, encoding='utf-8')
    print(f'ok {OUT.name}: {len(items)} entidades · {n_sitio} con cuentas del sitio · {n_manual} manual · {n_vacio} sin cuentas')
    for i in items:
        if not i['verificado']: print('   sin cuentas:', i['id'])

if __name__ == '__main__':
    if '--offline' in sys.argv and CACHE.exists():
        raw = json.loads(CACHE.read_text(encoding='utf-8'))
    else:
        raw = scrape_todo()
    emite(raw)
