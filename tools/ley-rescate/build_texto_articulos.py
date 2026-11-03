#!/usr/bin/env python3
"""Texto completo de los 106 artículos del PL 477 de 2026 Cámara, para leerlos sin abrir el PDF.

  python3 tools/ley-rescate/build_texto_articulos.py

Pedido de Pablo (Cauce, 3-nov-2026): el PDF radicado pesa 3 MB y tiene 334 páginas, así que tocar un
artículo y caer en él tardaba mucho. Ahora la página muestra el texto y ofrece un Word liviano.

Sale de:
  ley-rescate-data/texto-articulos.json      [{n, t (título propio), d (rótulo derivado si no tiene), p (página), x [párrafos]}]
  ley-rescate-data/word/articulo-NNN.docx    uno por artículo
  ley-rescate-data/word/articulado-completo.docx

Recorre el texto en secuencia (como build_articulos.py): los artículos citan artículos de otras leyes
(«Artículo 652.» del Estatuto) y buscarlos por número suelto agarra el que no es. Quita las marcas de
página, une las líneas cortadas del PDF y vuelve a pegar los párrafos que un salto de página partió.
"""
import json
import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parents[1]
TXT = REPO / 'Bases de datos/reforma-tributaria/capa-i/pl477-2026.txt'
OUT = REPO / 'ley-rescate-data'
PROY = 'Proyecto de Ley 477 de 2026 Cámara · Ley de Rescate Económico'
NOTA = ('Texto radicado el 29 de octubre de 2026 por el Ministerio de Hacienda. Copia de trabajo hecha desde el PDF '
        'oficial de la Cámara de Representantes; ante cualquier diferencia, manda el PDF.')
PDF = 'https://www.camara.gov.co/wp-content/uploads/2026/10/proyectos-ley/documentos/proyecto-36548/PROYECTO-DE-LEY-Rescate-Economico-2026-VSD-RADICADA-1.pdf'


def lineas():
    """(página, línea) sin marcas de página ni números de página sueltos."""
    pag = 0
    for l in TXT.read_text(errors='ignore').split('\n'):
        m = re.match(r'^=== página (\d+) ===', l)
        if m:
            pag = int(m.group(1)); continue
        if re.fullmatch(r'\s*\d{1,3}\s*', l):
            continue
        yield pag, l.rstrip()


def parrafos(ls):
    out, cur = [], []
    for l in ls:
        if not l.strip():
            if cur: out.append(' '.join(cur)); cur = []
        else:
            cur.append(l.strip())
    if cur: out.append(' '.join(cur))
    out = [re.sub(r'\s+', ' ', p).strip() for p in out if p.strip()]
    pegados = []
    for p in out:  # un salto de página parte el párrafo: termina sin puntuación y sigue en minúscula
        if pegados and not re.search(r'[.:;)»”"]$', pegados[-1]) and re.match(r'^[a-záéíóúñ(]', p):
            pegados[-1] += ' ' + p
        else:
            pegados.append(p)
    return pegados


VERBO = {'modifíque': 'Modifica', 'adicióne': 'Adiciona', 'créa': 'Crea', 'elimíne': 'Elimina', 'sustitúya': 'Sustituye',
         'derógue': 'Deroga'}


def describe(frase):
    """«A partir del 1 de enero de 2028 modifíquese el artículo 424 del Estatuto Tributario, el cual quedaría así:…»
    → «Desde el 1 de enero de 2028, modifica el artículo 424 del Estatuto Tributario»."""
    f = re.split(r',?\s+(?:el|la|los|las)\s+cual(?:es)?\s|\s+que\s+quedar|:\s|\.\s', frase, maxsplit=1)[0].strip().rstrip(',.:')
    cuando = ''
    m = re.match(r'(?i)a partir (?:del?|de la)\s+(.+?),?\s+(?=modifíque|adicióne|créa|elimíne|sustitúya|derógue)', f)
    if m:
        q = re.sub(r'^(?:el|la)\s+', '', m.group(1)); cuando, f = ('Desde el ' if q[:1].isdigit() else 'Desde ') + q + ', ', f[m.end():]
    for k, v in VERBO.items():
        m = re.match(r'(?i)%s\w*\s+' % k, f)
        if m:
            f = (v.lower() if cuando else v) + ' ' + f[m.end():]; break
    f = cuando + f
    return f if len(f) <= 130 else f[:127].rsplit(' ', 1)[0] + '…'


def es_rotulo(p):  # TÍTULO II. / CAPÍTULO III. / encabezados en mayúscula entre artículos
    letras = [c for c in p if c.isalpha()]
    return bool(letras) and sum(c.isupper() for c in letras) / len(letras) > .85 and len(p) < 220


def main():
    L = list(lineas())
    inicio = next(i for i, (_, l) in enumerate(L) if re.match(r'^Art[ií]culo\s+1\s*\.\s*Objeto', l))
    arts, n, i = [], 1, inicio
    while n <= 106:
        sig = None
        for j in range(i + 1, len(L)):
            if n < 106 and re.match(r'(?i)^\s*art[ií]culo\s+%d\s*[\.°º]' % (n + 1), L[j][1]):
                sig = j; break
            if n == 106 and L[j][1].strip().startswith('De los Honorables'):
                sig = j; break
        assert sig, n
        ps = parrafos(l for _, l in L[i:sig])
        while ps and es_rotulo(ps[-1]):
            ps.pop()
        m = re.match(r'(?i)^art[ií]culo\s+%d\s*[\.°º]\s*(.*)$' % n, ps[0])
        resto = m.group(1)
        # «Modifíquese el artículo…»: no tiene título propio, todo es cuerpo
        sin_titulo = re.match(r'(?i)(modifíque|adicióne|créa|elimíne|sustitúya|derógue|a partir de)', resto)
        t = None if sin_titulo else re.match(r'^(.{3,230}?)\.\s+(?=[A-ZÁÉÍÓÚÑ«"“])', resto)
        titulo = t.group(1) if t else ''
        cuerpo = [resto[t.end():] if t else resto] + ps[1:]
        arts.append({'n': n, 't': titulo, 'd': '' if titulo else describe(resto), 'p': L[i][0], 'x': [c for c in cuerpo if c]})
        n, i = n + 1, sig
    (OUT / 'texto-articulos.json').write_text(json.dumps({'v': 1, 'pdf': PDF, 'nota': NOTA, 'arts': arts},
                                                         ensure_ascii=False, separators=(',', ':')))
    w = OUT / 'word'; w.mkdir(exist_ok=True)

    def doc():
        d = Document()
        st = d.styles['Normal']; st.font.name = 'Arial'; st.font.size = Pt(11)
        for s in d.sections:
            s.footer.paragraphs[0].text = PROY + ' · ricardoruiz.co/ley-de-rescate-articulos.html'
            s.footer.paragraphs[0].runs[0].font.size = Pt(8)
        return d

    def escribe(d, a):
        h = d.add_paragraph(); r = h.add_run(f'Artículo {a["n"]}.' + (f' {a["t"]}.' if a['t'] else '')); r.bold = True; r.font.size = Pt(12)
        h.paragraph_format.space_before = Pt(14)
        for p in a['x']:
            q = d.add_paragraph(p); q.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY; q.paragraph_format.space_after = Pt(6)
        s = d.add_paragraph(); r = s.add_run(f'Página {a["p"]} del PDF radicado.'); r.italic = True
        r.font.size = Pt(8); r.font.color.rgb = RGBColor(0x66, 0x70, 0x85)

    def cab(d, sub):
        p = d.add_paragraph(); r = p.add_run(PROY); r.bold = True; r.font.size = Pt(14)
        p = d.add_paragraph(); r = p.add_run(sub); r.font.size = Pt(10)
        p = d.add_paragraph(); r = p.add_run(NOTA + ' ' + PDF); r.italic = True; r.font.size = Pt(8)
        r.font.color.rgb = RGBColor(0x66, 0x70, 0x85)

    for a in arts:
        d = doc(); cab(d, f'Artículo {a["n"]} de 106'); escribe(d, a); d.save(w / f'articulo-{a["n"]:03d}.docx')
    d = doc(); cab(d, 'Articulado completo: 106 artículos')
    for a in arts:
        escribe(d, a)
    d.save(w / 'articulado-completo.docx')
    tam = sum(f.stat().st_size for f in w.glob('*.docx'))
    print(f'106 artículos · {sum(len(a["x"]) for a in arts)} párrafos · Word: {tam / 1e6:.1f} MB en {len(list(w.glob("*.docx")))} archivos'
          f' · completo {(w / "articulado-completo.docx").stat().st_size / 1e3:.0f} KB · json {(OUT / "texto-articulos.json").stat().st_size / 1e3:.0f} KB')


if __name__ == '__main__':
    main()
