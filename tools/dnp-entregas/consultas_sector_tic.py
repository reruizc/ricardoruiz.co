#!/usr/bin/env python3
"""
Consultas reproducibles sobre el Portal de Datos Abiertos de Colombia
para el Informe Técnico - Entrega 3 (contrato DNP-1025-2026).

Reproduce las cifras del análisis de tendencias y brechas territoriales:
serie nacional de accesos fijos a internet, agregados departamentales y
variación 2019-2023, sobre el conjunto de datos del MinTIC "Internet Fijo
Accesos por tecnología y segmento" (identificador n48w-gutb, 2,79 millones
de registros), consultado mediante la interfaz SODA del portal.

También reproduce el procesamiento del conjunto "Participantes certificados
en Inteligencia Artificial - SENATIC" (identificador m2uu-cu4q).

Uso:
    python3 consultas_sector_tic.py

Requiere: curl. Sin dependencias de Python fuera de la biblioteca estándar.
"""

import collections
import json
import subprocess
import urllib.parse

BASE = "https://www.datos.gov.co/resource"


def soda(dataset, **params):
    qs = urllib.parse.urlencode({f"${k}": v for k, v in params.items()})
    url = f"{BASE}/{dataset}.json?{qs}"
    out = subprocess.run(["/usr/bin/curl", "-sk", "--max-time", "90", url],
                         capture_output=True, check=True)
    return json.loads(out.stdout)


def serie_nacional():
    print("— Serie nacional de accesos fijos (suma por año y trimestre) —")
    filas = soda("n48w-gutb",
                 select="anno,trimestre,sum(no_de_accesos::number) as acc",
                 group="anno,trimestre", order="anno,trimestre")
    for f in filas:
        # 2016 y 2017-T1 traen carga parcial en la fuente; se imprimen igual
        # y el informe los excluye de la serie con esa advertencia.
        print(f"  {f['anno']}-T{f['trimestre']}: {float(f['acc']):>12,.0f}")


def brecha_departamental():
    print("\n— Accesos por departamento, 2019-T3 frente a 2023-T3 —")
    a = {f["departamento"]: float(f["acc"]) for f in soda(
        "n48w-gutb", select="departamento,sum(no_de_accesos::number) as acc",
        where="anno='2023' AND trimestre='3'", group="departamento")}
    b = {f["departamento"]: float(f["acc"]) for f in soda(
        "n48w-gutb", select="departamento,sum(no_de_accesos::number) as acc",
        where="anno='2019' AND trimestre='3'", group="departamento")}
    tot23, tot19 = sum(a.values()), sum(b.values())
    print(f"  total 2019-T3: {tot19:,.0f} | 2023-T3: {tot23:,.0f} "
          f"| variación: {100 * (tot23 / tot19 - 1):+.1f} %")
    top5 = sorted(a, key=a.get, reverse=True)[:5]
    print(f"  cinco primeros departamentos: {100 * sum(a[d] for d in top5) / tot23:.1f} % del total")
    crecimiento = sorted(((d, 100 * (a[d] / b[d] - 1)) for d in a if b.get(d, 0) > 500),
                         key=lambda t: t[1])
    print("  mayores retrocesos:")
    for d, c in crecimiento[:5]:
        print(f"    {d.title():<28} {c:+.1f} %  ({b[d]:,.0f} → {a[d]:,.0f})")
    print("  mayores crecimientos:")
    for d, c in crecimiento[-5:]:
        print(f"    {d.title():<28} {c:+.1f} %  ({b[d]:,.0f} → {a[d]:,.0f})")


def velocidades():
    print("\n— Calidad del servicio: distribución de velocidades de bajada —")
    # velocidad_bajada llega con coma decimal ("50,00"), así que la agregación
    # numérica se hace localmente sobre el resultado agrupado.
    for anno in ("2019", "2023"):
        filas = soda("n48w-gutb",
                     select="velocidad_bajada,sum(no_de_accesos::number) as acc",
                     where=f"anno='{anno}' AND trimestre='3'",
                     group="velocidad_bajada", limit=8000)
        total = ge25 = ge100 = 0.0
        for f in filas:
            v = f.get("velocidad_bajada")
            if v is None:
                continue
            try:
                mbps = float(v.replace(",", "."))
            except ValueError:
                continue
            acc = float(f["acc"])
            total += acc
            if mbps >= 25:
                ge25 += acc
            if mbps >= 100:
                ge100 += acc
        print(f"  {anno}-T3: ≥25 Mbps {100 * ge25 / total:.1f}% "
              f"| ≥100 Mbps {100 * ge100 / total:.1f}%")


def estratos():
    print("\n— Composición del parque por segmento y estrato —")
    for anno in ("2019", "2023"):
        filas = soda("n48w-gutb",
                     select="segmento,sum(no_de_accesos::number) as acc",
                     where=f"anno='{anno}' AND trimestre='3'", group="segmento")
        d = {f["segmento"]: float(f["acc"]) for f in filas}
        total = sum(d.values())
        e12 = sum(v for k, v in d.items() if "ESTRATO 1" in k or "ESTRATO 2" in k)
        e56 = sum(v for k, v in d.items() if "ESTRATO 5" in k or "ESTRATO 6" in k)
        print(f"  {anno}-T3: estratos 1-2 {e12:,.0f} ({100 * e12 / total:.1f}%) "
              f"| estratos 5-6 {100 * e56 / total:.1f}%")


def municipios():
    print("\n— Granularidad municipal, 2023-T3 —")
    filas = soda("n48w-gutb",
                 select="municipio,departamento,sum(no_de_accesos::number) as acc",
                 where="anno='2023' AND trimestre='3'",
                 group="municipio,departamento", limit=3000)
    accesos = sorted((float(f["acc"]) for f in filas), reverse=True)
    total = sum(accesos)
    print(f"  municipios con algún acceso: {len(accesos)}")
    print(f"  con menos de 100 accesos: {sum(1 for a in accesos if a < 100)}")
    print(f"  con menos de 10 accesos: {sum(1 for a in accesos if a < 10)}")
    print(f"  cinco municipios mayores: {100 * sum(accesos[:5]) / total:.1f}% del total")


def senatic():
    print("\n— Formación en IA (SENATIC), composición y certificación —")
    d = soda("m2uu-cu4q", limit=5000)
    certificado = [x for x in d if x.get("certificado", "").strip().upper() == "OBTENIDO"]
    print(f"  registros: {len(d)} | certificados: {len(certificado)} "
          f"({100 * len(certificado) / len(d):.1f} %)")
    for genero in ("Femenino", "Masculino"):
        sub = [x for x in d if x.get("genero") == genero]
        c = [x for x in sub if x in certificado]
        print(f"  {genero}: {len(sub)} inscritos ({100 * len(sub) / len(d):.1f} %) "
              f"| tasa de certificación {100 * len(c) / len(sub):.1f} %")
    grupos = collections.Counter(x.get("grupo_poblaci_n") for x in d)
    for g in grupos:
        sub = [x for x in d if x.get("grupo_poblaci_n") == g]
        c = [x for x in sub if x in certificado]
        print(f"  {g}: {len(sub)} | tasa {100 * len(c) / len(sub):.1f} %")
    municipios = collections.Counter(x.get("mun") for x in d)
    mayor, n = municipios.most_common(1)[0]
    print(f"  concentración territorial: {100 * n / len(d):.1f} % de registros en {mayor.title()}")


if __name__ == "__main__":
    serie_nacional()
    brecha_departamental()
    velocidades()
    estratos()
    municipios()
    senatic()
