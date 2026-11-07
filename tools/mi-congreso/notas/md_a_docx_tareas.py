"""Pasa los documentos de trabajo en markdown a Word (uno por archivo y uno combinado).

Uso:
  python3 tools/mi-congreso/notas/md_a_docx_tareas.py <carpeta> [--combinado "Nombre.docx"] [--titulo "…"]

Soporta lo que usan esas notas: títulos #/##/###, párrafos, viñetas «- », listas «1. »,
citas «> », tablas de markdown y **negrita**. Fuente Arial (está en cualquier Windows).
"""
import re, sys, pathlib
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

FONT = 'Arial'
TINTA = RGBColor(0x14, 0x16, 0x1f)
ACENTO = RGBColor(0x1f, 0x47, 0xcc)


def nuevo_doc():
    doc = Document()
    sec = doc.sections[0]
    sec.page_height = Cm(27.94); sec.page_width = Cm(21.59)
    for m in ('left_margin', 'right_margin'): setattr(sec, m, Cm(2.3))
    for m in ('top_margin', 'bottom_margin'): setattr(sec, m, Cm(2.0))
    st = doc.styles['Normal']; st.font.name = FONT; st.font.size = Pt(10.5); st.font.color.rgb = TINTA
    st.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
    pf = st.paragraph_format; pf.line_spacing = 1.18; pf.space_after = Pt(6)
    for lvl, size in ((1, 17), (2, 13), (3, 11.5)):
        h = doc.styles[f'Heading {lvl}']; h.font.name = FONT; h.font.size = Pt(size); h.font.bold = True
        h.font.color.rgb = ACENTO if lvl == 2 else TINTA
        h.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
        h.paragraph_format.space_before = Pt(16 if lvl < 3 else 10); h.paragraph_format.space_after = Pt(6)
        h.paragraph_format.keep_with_next = True
    for nombre in ('List Bullet', 'List Number'):
        s = doc.styles[nombre]; s.font.name = FONT; s.font.size = Pt(10.5)
    return doc


def runs(p, texto):
    """Escribe texto con **negrita** en el párrafo."""
    partes = re.split(r'(\*\*[^*]+\*\*)', texto)
    for parte in partes:
        if not parte: continue
        if parte.startswith('**') and parte.endswith('**'):
            r = p.add_run(parte[2:-2]); r.bold = True
        else:
            p.add_run(parte)


def sombrear(celda, hexcolor):
    tcPr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd'); shd.set(qn('w:val'), 'clear'); shd.set(qn('w:color'), 'auto'); shd.set(qn('w:fill'), hexcolor)
    tcPr.append(shd)


def tabla(doc, filas):
    filas = [f for f in filas if not re.match(r'^\s*\|?\s*:?-{2,}', f)]
    datos = [[c.strip() for c in f.strip().strip('|').split('|')] for f in filas]
    ncol = max(len(r) for r in datos)
    t = doc.add_table(rows=len(datos), cols=ncol)
    t.style = 'Table Grid'
    for i, r in enumerate(datos):
        for j in range(ncol):
            c = t.cell(i, j); c.text = ''
            p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(0)
            runs(p, r[j] if j < len(r) else '')
            for run in p.runs:
                run.font.size = Pt(9)
                if i == 0: run.bold = True; run.font.color.rgb = RGBColor(0xff, 0xff, 0xff)
            if i == 0: sombrear(c, '1F47CC')
            elif i % 2 == 0: sombrear(c, 'F2F1EC')
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def volcar(doc, md):
    lineas = md.split('\n'); i = 0
    while i < len(lineas):
        l = lineas[i]
        if not l.strip(): i += 1; continue
        if l.strip().startswith('```'):
            i += 1; codigo = []
            while i < len(lineas) and not lineas[i].strip().startswith('```'): codigo.append(lineas[i]); i += 1
            i += 1
            p = doc.add_paragraph(); p.paragraph_format.left_indent = Cm(0.5)
            r = p.add_run('\n'.join(codigo)); r.font.name = 'Courier New'; r.font.size = Pt(7.5)
            continue
        if l.startswith('|'):
            bloque = []
            while i < len(lineas) and lineas[i].startswith('|'): bloque.append(lineas[i]); i += 1
            tabla(doc, bloque); continue
        m = re.match(r'^(#{1,3})\s+(.*)', l)
        if m:
            doc.add_heading(m.group(2).strip(), level=len(m.group(1))); i += 1; continue
        if l.startswith('> '):
            p = doc.add_paragraph(); p.paragraph_format.left_indent = Cm(0.8)
            runs(p, l[2:]); [setattr(r, 'italic', True) for r in p.runs]; i += 1; continue
        m = re.match(r'^(\s*)- (.*)', l)
        if m:
            p = doc.add_paragraph(style='List Bullet')
            if m.group(1): p.paragraph_format.left_indent = Cm(1.4)
            runs(p, m.group(2)); i += 1; continue
        m = re.match(r'^\d+\.\s+(.*)', l)
        if m:
            p = doc.add_paragraph(style='List Number'); runs(p, m.group(1)); i += 1; continue
        # párrafo normal (une líneas seguidas)
        texto = [l.strip()]; i += 1
        while i < len(lineas) and lineas[i].strip() and not re.match(r'^(#|\||> |\s*- |\d+\.\s|\s*```)', lineas[i]):
            texto.append(lineas[i].strip()); i += 1
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY; runs(p, ' '.join(texto))


def main():
    a = sys.argv[1:]
    carpeta = pathlib.Path(a[0])
    combinado = a[a.index('--combinado') + 1] if '--combinado' in a else None
    titulo = a[a.index('--titulo') + 1] if '--titulo' in a else None
    mds = sorted(p for p in carpeta.glob('*.md') if p.name[0].isdigit())
    out = carpeta / 'word'; out.mkdir(exist_ok=True)
    for p in mds:
        doc = nuevo_doc(); volcar(doc, p.read_text()); doc.save(out / (p.stem + '.docx'))
        print('ok', out / (p.stem + '.docx'))
    if combinado:
        doc = nuevo_doc()
        if titulo:
            h = doc.add_heading(titulo, level=1)
            p = doc.add_paragraph('Contenido: ' + ' · '.join(re.sub(r'^#\s*', '', p.read_text().split('\n')[0]) for p in mds))
        for k, p in enumerate(mds):
            if k or titulo: doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
            volcar(doc, p.read_text())
        doc.save(carpeta / combinado); print('ok', carpeta / combinado)


if __name__ == '__main__':
    main()
