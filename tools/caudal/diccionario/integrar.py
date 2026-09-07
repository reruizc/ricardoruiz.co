"""Integra las tandas curadas dentro de _RAW en empresas.py.
Serializa desde las tuplas YA EVALUADAS (no copia texto): así lo que entra al
diccionario es exactamente lo que el validador revisó, aunque el archivo de
tanda use helpers para escribir menos."""
import glob, sys
import os
S = os.environ.get("CAUDAL_DICC_DIR", "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/caudal-diccionario")
P='/Users/ricardoruiz/ricardoruiz.co/tools/caudal/empresas.py'
INI = "    # ═══ TANDA ⑧ · empresas verificadas contra SECOP II y actos regulatorios ═══"
FIN = "    # ═══ fin TANDA ⑧ ═══"

def esc(s):
    return "'" + str(s).replace('\\', '\\\\').replace("'", "\\'") + "'"

lineas = []
for f in sorted(glob.glob(f"{S}/tandas/*.py")):
    g = {}
    exec(open(f).read(), g)
    lineas.append(f"    # --- {f.split('/')[-1].replace('.py','')}")
    for t in g['TUPLAS']:
        campos = ", ".join(esc(x) for x in t)
        linea = f"    ({campos}),"
        if len(linea) <= 96:
            lineas.append(linea)
        else:  # partir en dos para que el archivo siga siendo legible
            mitad = 4
            a = ", ".join(esc(x) for x in t[:mitad])
            b = ", ".join(esc(x) for x in t[mitad:])
            lineas.append(f"    ({a},")
            lineas.append(f"     {b}),")
nuevo = INI + "\n" + "\n".join(lineas) + "\n" + FIN

s = open(P).read()
# limpiar cualquier bloque previo (con la marca vieja o la nueva)
for ini_m, fin_m in ((INI, FIN),
                     ("    # ═══ TANDA ⑧ · derivada del dato (SECOP II + actos regulatorios) ═══",
                      "    # ═══ fin TANDA ⑧ ═══")):
    if ini_m in s and fin_m in s:
        a = s.index(ini_m); b = s.index(fin_m) + len(fin_m)
        s = s[:a] + s[b:]
        s = s.replace("\n\n\n]", "\n]")
i = s.index('_RAW = [')
j = s.index('\n]\n', i)
s = s[:j+1] + nuevo + "\n" + s[j+1:]
open(P,'w').write(s)
print(f'integradas {sum(1 for l in lineas if l.startswith("    ("))} tuplas')
