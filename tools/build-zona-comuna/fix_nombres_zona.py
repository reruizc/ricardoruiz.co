#!/usr/bin/env python3
"""Corrige el nombre de las zonas electorales en los agregados de consultas.

Los dep-*.json rotulan la zona N como "Comuna N <nombre>", asumiendo que zona y
comuna son lo mismo. No lo son: en Medellin la zona 05 esta en la comuna 3
Manrique, no en Castilla. El rotulo hace que el error pase desapercibido.

Reescribe el nombre a "Zona NN · <comuna real>" usando la tabla derivada de
PUESTOS_GEOREF. Solo toca municipios presentes en esa tabla (donde la relacion
NO es la identidad); el resto queda intacto.

  python3 tools/build-zona-comuna/fix_nombres_zona.py           # dry-run
  python3 tools/build-zona-comuna/fix_nombres_zona.py --apply   # escribe
"""
import json, os, sys, glob

TABLA = 'Bases de datos/output_geo/zona-comuna.json'
DIR = 'Bases de datos/output_agregados/consultas'


def title(s):
    return ' '.join(w.capitalize() if len(w) > 2 else w.lower() for w in str(s).split())


def main():
    apply_ = '--apply' in sys.argv
    tabla = json.load(open(TABLA, encoding='utf-8'))['muns']
    total_zonas = total_muns = total_deps = 0
    muestras = []

    for path in sorted(glob.glob(os.path.join(DIR, 'dep-*.json'))):
        d = json.load(open(path, encoding='utf-8'))
        dep = d['cod']
        tocado = False
        for mun in d.get('municipios', []):
            key = f"{dep}-{mun['cod']}"
            m = tabla.get(key)
            if not m:
                continue
            cambios = 0
            for z in mun.get('zonas', []):
                cod = m['z'].get(str(z['cod']).zfill(2))
                if not cod:
                    continue
                comuna = title(m['c'].get(cod, f'Comuna {int(cod)}'))
                nuevo = f"Zona {z['cod']} · {comuna}"
                if z.get('nombre') != nuevo:
                    if len(muestras) < 8:
                        muestras.append(f"  {key} zona {z['cod']}: {z.get('nombre')!r} -> {nuevo!r}")
                    z['nombre'] = nuevo
                    cambios += 1
            if cambios:
                tocado = True
                total_muns += 1
                total_zonas += cambios
        if tocado:
            total_deps += 1
            if apply_:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(d, f, ensure_ascii=False, separators=(',', ':'))

    print('\n'.join(muestras))
    print(f'\n{total_zonas} zonas renombradas en {total_muns} municipios ({total_deps} archivos dep-*)')
    print('APLICADO' if apply_ else 'DRY-RUN (usa --apply para escribir)')


if __name__ == '__main__':
    main()
