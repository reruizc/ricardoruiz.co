#!/usr/bin/env python3
"""
siedco_a_bd.py — lleva los CSV limpios de las entregas SIEDCO (salida de
limpiar_siedco.py) al formato de la base grande `BD-PONAL-15-24.csv`, para que
`build_ponal.py` los lea con la misma lógica que 2015-2024.

    python3 tools/ponal/siedco_a_bd.py
    → Bases de datos/PONAL/BD-PONAL-25-26.csv   (`;`, UTF-8 con BOM)

Toma 2025 (año completo) y 2026 ene-ago. `Nombre Delitos` se escribe con una
etiqueta que `build_ponal.DELITOS` ya reconoce, así el mapa canónico de
delitos sigue siendo UNO solo.
"""
import csv
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CLEAN = RAIZ / "Bases de datos" / "PONAL-SIEDCO" / "clean"
LOTES = ["2025", "2026-01-08"]
OUT = RAIZ / "Bases de datos" / "PONAL" / "BD-PONAL-25-26.csv"

ETIQUETA = {
    "homicidios": "homicidios",
    "lesiones-personales": "lesiones",
    "violencia-intrafamiliar": "violencia intra",
    "delitos-sexuales": "delitos sexuales",
    "amenazas": "amenazas",
    "extorsion": "extorsiones",
    "secuestro": "secuestros",
    "terrorismo": "terrorismo",
    "hurto-a-personas": "hurto personas",
    "hurto-celular": "hurto celulares",
    "hurto-a-comercio": "hurto comercios",
    "hurto-a-residencias": "hurto residencias",
    "hurto-a-motos": "hurto motos",
    "hurto-automotores": "hurto autos",
    "delitos-informaticos": "del informaticos",
    "homicidios-en-at": "homicidios acc transito",
    "lesiones-en-at": "LESIONES EN ACCIDENTES DE TRANSITO dic/Sheet1",
    "hurto-bicicletas": "HURTO BICICLETAS dic/Sheet1",
    "hurto-ganado": "HURTO A CABEZAS DE GANADO dic/Sheet1",
    "pirateria-terrestre": "HURTO PIRATERIA TERRESTRE dic/Sheet1",
    "hurto-entidades-financieras": "HURTO ENTIDADES FINANCIERAS dic/Sheet1",
}

# columna de la base grande ← columna del CSV limpio
MAPA = [
    ("Nombre Delitos", None), ("Cantidad", "CANTIDAD"), ("Fecha", None),
    ("Hora", "HORA_HECHO"), ("Día", "DIA_SEMANA"),
    ("Hechos.CODIGO_DANE", "CODIGO_DANE"), ("Hechos.MUNICIPIO_HECHO", "MUNICIPIO_HECHO"),
    ("Departamento", "DEPTO_HECHO"), ("Hechos.ZONA", "ZONA"),
    ("Hechos.BARRIOS_HECHO", "BARRIOS_HECHO"),
    ("Hechos.COMUNAS_ZONAS_DESCRIPCION", "COMUNAS_ZONAS_DESCRIPCION"),
    ("Clase de sitio", "CLASE_SITIO"), ("Arma empleada", "ARMAS_MEDIOS"),
    ("Conduc.MOVIL_AGRESOR", "MOVIL_AGRESOR"), ("Móvil Victima", "MOVIL_VICTIMA"),
    ("Person.GENERO", "GENERO"), ("Person.EDAD", "EDAD"),
    ("Estado Civil", "ESTADO_CIVIL_PERSONA"), ("País de nacimiento", "PAIS_PERSONA"),
    ("Profesión", "PROFESIONES"), ("Clase de empleado", "CARGO_PERSONA"),
    ("Person.GRADO_INSTRUCCION_PERSONA", "GRADO_INSTRUCCION_PERSONA"),
    ("ListaC.DESCRIPCION_CONDUCTA", "DESCRIPCION_CONDUCTA"),
    ("Bienes.CLASE_BIEN", "CLASE_BIEN"), ("TIPO_BIEN", "TIPO_BIEN"),
    ("MARCA", "MARCA_BIEN"), ("Modelo", "MODELO_VEHICULO"), ("Bienes.COLOR_BIEN", "COLOR_BIEN"),
]


def main():
    n = hechos = 0
    with OUT.open("w", encoding="utf-8-sig", newline="") as fo:
        w = csv.writer(fo, delimiter=";")
        w.writerow([c for c, _ in MAPA])
        for lote in LOTES:
            for p in sorted((CLEAN / lote).glob("*.csv")):
                et = ETIQUETA[p.stem]
                with p.open(encoding="utf-8") as f:
                    for r in csv.DictReader(f):
                        fe = r["FECHA_HECHO"]
                        fecha = f"{fe[8:10]}/{fe[5:7]}/{fe[:4]}" if fe else ""
                        fila = []
                        for col, src in MAPA:
                            if col == "Nombre Delitos":
                                fila.append(et)
                            elif col == "Fecha":
                                fila.append(fecha)
                            else:
                                fila.append(r.get(src, "").replace(";", ","))
                        w.writerow(fila)
                        n += 1
                        hechos += int(r["CANTIDAD"])
    print(f"{OUT.name}: {n:,} filas · {hechos:,} hechos")


if __name__ == "__main__":
    main()
