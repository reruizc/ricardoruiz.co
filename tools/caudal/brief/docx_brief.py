"""El brief en Word · la versión que el analista reescribe antes de mandarla.

El PDF es el entregable: se manda tal cual y se ve igual en cualquier pantalla.
Este .docx es la MATERIA PRIMA — el analista lo abre, corta lo que no aplica, le
suma lo que sabe del cliente y lo firma con su membrete. Mismo JSON, mismo orden
y mismos textos que `render_brief.py`: son el mismo documento en dos formatos, no
dos informes. Si uno cambia de estructura, el otro tiene que cambiar con él.

Se escribe a mano, sin dependencias: OOXML dentro de un zip con `zipfile`, que
viene en la biblioteca estándar. Meter `python-docx` por siete tipos de párrafo
sería traerse una dependencia para no aprenderse el formato.

⚠️⚠️ El ORDEN de los hijos de `w:rPr` y `w:pPr` lo fija el esquema
(`b · caps · color · spacing · sz · u` y `pBdr · shd · tabs · spacing · ind`) y
Word declara el documento ilegible si llegan en otro orden. No reordenarlos por
comodidad.

⚠️ Los caracteres de control no son XML válido: un título raspado con uno adentro
dejaría el archivo irreparable. `_esc` los borra antes de escapar.

⚠️ Las cajas con fondo y barra de color son TABLAS de una celda, no párrafos
sombreados: encadenar párrafos con `w:shd` deja franjas blancas en los espacios
entre uno y otro. Word además exige un párrafo entre dos tablas seguidas.
"""
import datetime
import os
import re
import zipfile

# La paleta es la del brief escrito a mano (el CSS de build_brief_binance), para
# que el Word y el PDF no parezcan de dos productos distintos.
TINTA = '0B0D11'
AZUL = '2B5672'
GRIS = '5A6070'
GRIS2 = '6B7280'
PROSA = '3D434F'
LINEA = 'DFE2E8'
MORADO = '5F3DC4'      # la caja de la lectura
NARANJA = 'D9480F'     # tema de urgencia alta
OCRE = '8A6D1C'        # tema de urgencia media
FONDO_LECTURA = 'F8F6FD'
FONDO_URG = 'FDF7F4'
FONDO_MED = 'FBF9F2'

# ancho útil en twips: carta (12240) menos los dos márgenes de 1040
ANCHO = 10160

NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"')
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
CONTROL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


def _esc(s):
    s = CONTROL.sub('', str(s if s is not None else ''))
    return (s.replace('&', '&amp;').replace('<', '&lt;')
             .replace('>', '&gt;').replace('"', '&quot;'))


def _run(txt, b=False, caps=False, color=None, letra=None, size=None, u=False):
    """Un run. `size` va en MEDIOS puntos (19 = 9,5 pt)."""
    p = []
    if b:
        p.append('<w:b/>')
    if caps:
        p.append('<w:caps/>')
    if color:
        p.append(f'<w:color w:val="{color}"/>')
    if letra:
        p.append(f'<w:spacing w:val="{letra}"/>')
    if size:
        p.append(f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>')
    if u:
        p.append('<w:u w:val="single"/>')
    rpr = f'<w:rPr>{"".join(p)}</w:rPr>' if p else ''
    return f'<w:r>{rpr}<w:t xml:space="preserve">{_esc(txt)}</w:t></w:r>'


def _par(cont='', before=None, after=None, ind=None, linea=False,
         shd=None, barra=None, tab=None, jc=None, keep=False):
    p = []
    if keep:
        p.append('<w:keepNext/>')
    bordes = []
    if barra:
        bordes.append(f'<w:left w:val="single" w:sz="18" w:space="4" w:color="{barra}"/>')
    if linea:
        bordes.append(f'<w:bottom w:val="single" w:sz="4" w:space="4" w:color="{LINEA}"/>')
    if bordes:
        p.append(f'<w:pBdr>{"".join(bordes)}</w:pBdr>')
    if shd:
        p.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{shd}"/>')
    if tab:
        p.append(f'<w:tabs><w:tab w:val="right" w:pos="{tab}"/></w:tabs>')
    if before is not None or after is not None:
        p.append('<w:spacing'
                 + (f' w:before="{before}"' if before is not None else '')
                 + (f' w:after="{after}"' if after is not None else '') + '/>')
    if ind:
        p.append(f'<w:ind w:left="{ind}"/>')
    if jc:
        p.append(f'<w:jc w:val="{jc}"/>')
    ppr = f'<w:pPr>{"".join(p)}</w:pPr>' if p else ''
    return f'<w:p>{ppr}{cont}</w:p>'


def _txt(t, **kw):
    r = {k: kw.pop(k) for k in ('b', 'caps', 'color', 'letra', 'size', 'u')
         if k in kw}
    return _par(_run(t, **r), **kw)


def _rotulo(t, color=GRIS, size=15, **kw):
    """El eyebrow del brief: versalitas espaciadas."""
    return _txt(t, b=True, caps=True, color=color, letra=12, size=size,
                keep=True, **kw)


def _caja(cuerpo, barra=None, fondo=None):
    borde = (f'<w:tblBorders><w:left w:val="single" w:sz="18" w:space="0" '
             f'w:color="{barra}"/></w:tblBorders>') if barra else ''
    shd = (f'<w:shd w:val="clear" w:color="auto" w:fill="{fondo}"/>'
           if fondo else '')
    return (
        '<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/>' + borde
        + '<w:tblCellMar><w:top w:w="150" w:type="dxa"/>'
          '<w:left w:w="190" w:type="dxa"/><w:bottom w:w="150" w:type="dxa"/>'
          '<w:right w:w="190" w:type="dxa"/></w:tblCellMar></w:tblPr>'
        + f'<w:tblGrid><w:gridCol w:w="{ANCHO}"/></w:tblGrid>'
        + f'<w:tr><w:tc><w:tcPr><w:tcW w:w="5000" w:type="pct"/>{shd}</w:tcPr>'
        + cuerpo + '</w:tc></w:tr></w:tbl>')


def _tabla2(filas, encabezado=None, ancho1=26):
    """Tabla de dos columnas (agenda y «qué no se movió»)."""
    c1 = int(ANCHO * ancho1 / 100)
    out = ['<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/>'
           '<w:tblBorders>'
           f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="{LINEA}"/>'
           '</w:tblBorders>'
           '<w:tblCellMar><w:top w:w="90" w:type="dxa"/><w:left w:w="0" w:type="dxa"/>'
           '<w:bottom w:w="90" w:type="dxa"/><w:right w:w="140" w:type="dxa"/>'
           '</w:tblCellMar></w:tblPr>'
           f'<w:tblGrid><w:gridCol w:w="{c1}"/><w:gridCol w:w="{ANCHO - c1}"/></w:tblGrid>']
    if encabezado:
        a, b_ = encabezado
        out.append(
            '<w:tr><w:trPr><w:tblHeader/></w:trPr>'
            f'<w:tc><w:tcPr><w:tcW w:w="{c1}" w:type="dxa"/></w:tcPr>'
            + _rotulo(a, color=GRIS, size=14, after=0) + '</w:tc>'
            f'<w:tc><w:tcPr><w:tcW w:w="{ANCHO - c1}" w:type="dxa"/></w:tcPr>'
            + _rotulo(b_, color=GRIS, size=14, after=0) + '</w:tc></w:tr>')
    for izq, der in filas:
        out.append(
            f'<w:tr><w:tc><w:tcPr><w:tcW w:w="{c1}" w:type="dxa"/></w:tcPr>'
            + _txt(izq, b=True, size=17, color=TINTA, after=0) + '</w:tc>'
            f'<w:tc><w:tcPr><w:tcW w:w="{ANCHO - c1}" w:type="dxa"/></w:tcPr>'
            + _txt(der, size=17, color=PROSA, after=0) + '</w:tc></w:tr>')
    out.append('</w:tbl>')
    return ''.join(out)


def _png_tam(ruta):
    """Ancho y alto de un PNG, leyendo su cabecera. Evita traerse Pillow."""
    with open(ruta, 'rb') as fh:
        cab = fh.read(24)
    if cab[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    return (int.from_bytes(cab[16:20], 'big'), int.from_bytes(cab[20:24], 'big'))


def _logo(rid, ruta, ancho_pt=118):
    """El logo como imagen en línea. EMU = punto × 12700."""
    tam = _png_tam(ruta)
    if not tam:
        return ''
    w, h = tam
    cx = int(ancho_pt * 12700)
    cy = int(cx * h / w)
    return (
        '<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="1" name="Caudal x Cauce"/>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/'
        'drawingml/2006/picture"><pic:pic>'
        '<pic:nvPicPr><pic:cNvPr id="1" name="logo.png"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        '<pic:spPr><a:xfrm><a:off x="0" y="0"/>'
        f'<a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')


def construir(b, render):
    """Devuelve (partes, binarios) listos para el zip.

    `render` es el módulo render_brief: se le piden los mismos helpers de fecha
    que usa el PDF (`fecha_larga`, `fecha_agenda`, `hora_legible`…) para que las
    dos salidas no puedan escribir la misma fecha de dos maneras.
    """
    meta = b.get('_meta') or {}
    v = meta.get('ventana') or {}
    cliente = meta.get('cliente') or 'Cliente'
    horas = (v.get('dias_prensa') or 3) * 24
    fuera = meta.get('fuera_de_alcance') or []
    alcance = 'Colombia y región' if fuera else 'Colombia'
    corte = v.get('corte')
    ventana_txt = (f"{render.fecha_corta(v.get('desde'))} – "
                   f"{render.fecha_larga(v.get('hasta'))} · últimas {horas} horas"
                   + (f" · corte {render.hora_legible(corte)}" if corte else '')
                   + f" · {alcance}")

    O = []
    # hero
    O.append(_txt(b.get('titular', ''), b=True, size=38, color=TINTA, after=140))
    O.append(_txt(b.get('bajada', ''), size=20, color=PROSA, after=160))
    O.append(_par(linea=True, after=100))
    O.append(_rotulo(ventana_txt, color=GRIS, size=14, after=240))

    # lectura de la ventana
    lec = b.get('lectura') or {}
    if lec:
        c = [_rotulo(f'Lectura de estas {horas} horas', color=MORADO, after=90)]
        if lec.get('titulo'):
            c.append(_txt(lec['titulo'], b=True, size=24, color=TINTA, after=110))
        for x in (lec.get('parrafos') or []):
            c.append(_txt(x, size=19, color=TINTA, after=90))
        if lec.get('si_solo_hay_tiempo'):
            c.append(_rotulo('Si solo hay tiempo para una cosa', color=AZUL,
                             size=14, after=50))
            c.append(_txt(lec['si_solo_hay_tiempo'], size=19, color=TINTA, after=0))
        O.append(_caja(''.join(c), barra=MORADO, fondo=FONDO_LECTURA))
        O.append(_txt('', size=12, after=0))

    # temas
    for i, t in enumerate(b.get('temas') or [], 1):
        alta = t.get('urgencia') == 'alta'
        col = NARANJA if alta else OCRE
        rot = (t.get('rotulo') or '').strip()
        lin = (t.get('linea') or '').strip()
        # mismo criterio que el PDF: no repetir la línea si el rótulo ya la dice
        cab = f'{i:02d} · {rot}' + (f' · {lin}' if lin and lin.lower() not in rot.lower() else '')
        c = [_rotulo(cab, color=col, after=90)]
        if t.get('titulo'):
            c.append(_txt(t['titulo'], b=True, size=24, color=TINTA, after=110))
        for x in (t.get('parrafos') or []):
            c.append(_txt(x, size=19, color=TINTA, after=90))
        for et, val in (('Por qué le importa a ' + cliente, t.get('por_que')),
                        ('Qué hacer con esto', t.get('que_hacer'))):
            if not val:
                continue
            c.append(_rotulo(et, color=AZUL, size=14, after=50))
            c.append(_txt(val, size=19, color=TINTA, after=90))
        O.append(_caja(''.join(c), barra=col,
                       fondo=FONDO_URG if alta else FONDO_MED))
        O.append(_txt('', size=12, after=0))

    # agenda — ordenada por fecha, igual que el PDF
    if b.get('agenda'):
        ag = sorted(b['agenda'],
                    key=lambda x: (x.get('iso') or '9999-12-31', x.get('cuando') or ''))
        O.append(_par(linea=True, after=120))
        O.append(_rotulo('Agenda de lo que viene', color=GRIS, size=17, after=120))
        O.append(_tabla2([(render.fecha_agenda(x), x.get('que') or '') for x in ag]))
        O.append(_txt('', size=12, after=0))

    # qué no se movió
    if b.get('no_se_movio'):
        O.append(_par(linea=True, after=120))
        O.append(_rotulo('Qué no se movió — verificado, no asumido', color=GRIS,
                         size=17, after=120))
        O.append(_tabla2([(x.get('fuente') or '', x.get('estado') or '')
                          for x in b['no_se_movio']],
                         encabezado=('Fuente', 'En la ventana')))
        O.append(_txt('', size=12, after=0))

    # pie metodológico — el mismo texto del PDF
    modelo = meta.get('modelo', '')
    O.append(_par(linea=True, after=120))
    pie = [
        ('Fuentes.', 'Registro de proyectos de ley del Senado y la Cámara y órdenes '
         'del día de sus comisiones; normativa de Presidencia; consulta pública de '
         'proyectos de norma (SUCOP); registro regulatorio de las superintendencias '
         'y la ANLA; contratación del Estado (SECOP); prensa nacional y regional. '
         'Cada afirmación es verificable contra el acto o la nota que la respalda, y '
         'la sección «qué no se movió» dice hasta qué fecha llega cada registro.'),
        ('Ventana.', ventana_txt),
        ('Cómo se produjo.', f'Barrido automático de los pilares de Caudal sobre la '
         f'ficha de {cliente}, redacción asistida por modelo'
         + (f' ({modelo})' if modelo else '')
         + ' y revisión humana antes de enviar.'),
        ('Alcance.', 'Insumo de monitoreo; no constituye asesoría legal.'),
    ]
    for et, tx in pie:
        O.append(_par(_run(et + ' ', b=True, size=16, color=TINTA)
                      + _run(tx, size=16, color=GRIS2), after=70))
    O.append(_txt('Caudal · módulo de inteligencia regulatoria de Cauce.',
                  size=16, color=GRIS2, after=0))

    sect = ('<w:sectPr>'
            '<w:headerReference w:type="default" r:id="rIdHdr"/>'
            '<w:footerReference w:type="default" r:id="rIdFtr"/>'
            '<w:pgSz w:w="12240" w:h="15840"/>'
            '<w:pgMar w:top="1560" w:right="1040" w:bottom="1120" w:left="1040" '
            'w:header="560" w:footer="560" w:gutter="0"/></w:sectPr>')

    logo = getattr(render.base, 'LOGO', '')
    hay_logo = bool(logo) and os.path.exists(logo)
    marca = (_logo('rIdLogo', logo) if hay_logo
             else _run('CAUDAL × CAUCE', b=True, size=24, color=TINTA))
    hdr = (XML + f'<w:hdr {NS}>'
           + _par(marca + '<w:r><w:tab/></w:r>'
                  + _run(f'Brief de asuntos públicos · {cliente}', caps=True,
                         letra=10, size=14, color=GRIS),
                  tab=ANCHO, linea=True, after=60)
           + '</w:hdr>')
    pg = lambda campo: (f'<w:fldSimple w:instr=" {campo} ">'
                        + _run('1', size=14, color=GRIS) + '</w:fldSimple>')
    ftr = (XML + f'<w:ftr {NS}>'
           + _par(_run(render.fecha_larga(v.get('hasta')), size=14, color=GRIS)
                  + '<w:r><w:tab/></w:r>' + pg('PAGE')
                  + _run(' / ', size=14, color=GRIS) + pg('NUMPAGES'),
                  tab=ANCHO, after=0)
           + '</w:ftr>')
    # Arial y no Helvetica: es la que existe en Windows, en Mac y en Google Docs.
    # Una fuente que el lector no tenga se sustituye sin avisar y el documento le
    # llega al cliente con otra tipografía.
    styles = (XML + f'<w:styles {NS}><w:docDefaults>'
              '<w:rPrDefault><w:rPr>'
              '<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>'
              '<w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr></w:rPrDefault>'
              '<w:pPrDefault><w:pPr>'
              '<w:spacing w:after="110" w:line="268" w:lineRule="auto"/>'
              '</w:pPr></w:pPrDefault></w:docDefaults></w:styles>')

    rels = [f'<Relationship Id="rIdSty" Type="{REL}styles" Target="styles.xml"/>',
            f'<Relationship Id="rIdHdr" Type="{REL}header" Target="header1.xml"/>',
            f'<Relationship Id="rIdFtr" Type="{REL}footer" Target="footer1.xml"/>']
    partes = {
        '[Content_Types].xml': (
            XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="png" ContentType="image/png"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
            '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
            '</Types>'),
        '_rels/.rels': (
            XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{REL}officeDocument" Target="word/document.xml"/>'
            '</Relationships>'),
        'word/document.xml': XML + f'<w:document {NS}><w:body>{"".join(O)}{sect}</w:body></w:document>',
        'word/styles.xml': styles,
        'word/header1.xml': hdr,
        'word/footer1.xml': ftr,
    }
    binarios = {}
    if hay_logo:
        # el logo lo referencia el ENCABEZADO, así que su relación va en
        # header1.xml.rels, no en la del documento
        binarios['word/media/logo.png'] = open(logo, 'rb').read()
        partes['word/_rels/header1.xml.rels'] = (
            XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rIdLogo" Type="{REL}image" Target="media/logo.png"/>'
            '</Relationships>')
    partes['word/_rels/document.xml.rels'] = (
        XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + ''.join(rels) + '</Relationships>')
    return partes, binarios


def escribir(b, render, out):
    partes, binarios = construir(b, render)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    fecha = (2026, 1, 1, 0, 0, 0)   # fija: dos corridas del mismo brief dan el mismo archivo
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for nombre, texto in partes.items():
            zi = zipfile.ZipInfo(nombre, fecha)
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, texto.encode('utf-8'))
        for nombre, datos in binarios.items():
            zi = zipfile.ZipInfo(nombre, fecha)
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, datos)
    return out
