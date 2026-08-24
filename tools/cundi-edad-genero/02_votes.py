#!/usr/bin/env python3
"""Paso 2 · votos por lista en Cundinamarca (dep 15), Congreso.

2022: GCS_2022CON.csv  (escrutinio, mesa-level) -> votos-2022-cundi-mesa.csv
2026: DEPTOS_DECLARADOS/MMV_..._15_...csv (declarados, mesa) agregado a PUESTO
                                          -> votos-2026-cundi-puesto.csv

Formato long: corp, circ, key, pcode_par, partido, votos
Listas + pseudo-listas BLANCO / NULOS / NOMARCADOS (para cuadrar el universo).
"""
import csv
import os
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BASE, OUT, DEP_CUNDI, mesa_key, puesto_key

csv.field_size_limit(1 << 24)

# pseudo-listas para blanco/nulo/no-marcado
BLANCO, NULOS, NOMARC = "__BLANCO__", "__NULOS__", "__NOMARC__"


# --------------------------------------------------------------- 2022 (GCS)
def agg_2022():
    src = os.path.join(BASE, "FINAL SUBIDA GCS", "GCS_2022CON.csv")
    # acc[(corp, circ, mesa, par_code, partido)] = votos
    acc = defaultdict(int)
    tot = defaultdict(int)
    t0 = time.time()
    with open(src, encoding="utf-8-sig") as f:
        r = csv.reader(f, delimiter=";")
        header = next(r)
        ix = {c: header.index(c) for c in header}
        i_dde = ix["COD_DDE"]; i_cor = ix["COD_COR"]; i_dcor = ix["DES_COR"]
        i_dcir = ix["DES_CIR"]; i_mme = ix["COD_MME"]; i_zz = ix["COD_ZZ"]
        i_pp = ix["COD_PP"]; i_ms = ix["DES_MS"]; i_par = ix["COD_PAR"]
        i_dpar = ix["DES_PAR"]; i_can = ix["COD_CAN"]; i_vot = ix["NUM_VOT"]
        n = 0
        for row in r:
            n += 1
            if row[i_dde] != DEP_CUNDI:
                continue
            corp = row[i_dcor].strip().upper()          # SENADO / CAMARA
            circ = row[i_dcir].strip().upper()
            key = mesa_key(row[i_dde], row[i_mme], row[i_zz], row[i_pp], row[i_ms])
            v = int(row[i_vot] or 0)
            cod_can = str(row[i_can]).strip()
            if cod_can == "996":
                par, nom = BLANCO, "Votos en blanco"
            elif cod_can == "997":
                par, nom = NULOS, "Votos nulos"
            elif cod_can in ("998", "999"):
                par, nom = NOMARC, "No marcados"
            else:
                par = str(row[i_par]).strip()
                nom = row[i_dpar].strip()
            acc[(corp, circ, key, par, nom)] += v
            tot[(corp, par, nom)] += v
            if n % 2_000_000 == 0:
                print(f"  2022 ... {n:,} filas ({time.time()-t0:.0f}s)", flush=True)
    _write(acc, "votos-2022-cundi-mesa.csv")
    _report("2022", tot)


# --------------------------------------------------------------- 2026 (MMV)
def agg_2026():
    src = os.path.join(BASE, "DEPTOS_DECLARADOS",
                       "MMV_XXX_15_000_XXX_XX_XX_XXX_1008.csv")
    acc = defaultdict(int)
    tot = defaultdict(int)
    with open(src, encoding="utf-8-sig") as f:
        r = csv.reader(f, delimiter=";")
        header = [h.strip() for h in next(r)]
        ix = {c: header.index(c) for c in header}
        for row in r:
            corp = row[ix["CORNOMBRE"]].strip().upper()
            if corp not in ("SENADO", "CAMARA"):
                continue                                  # ignora CONSULTAS
            circ_code = str(row[ix["CIR"]]).strip()
            parnom = row[ix["PARNOMBRE"]].strip()
            can = str(row[ix["CAN"]]).strip().lstrip("0") or "0"
            key = puesto_key(row[ix["DEP"]], row[ix["MUN"]],
                             row[ix["ZONA"]], row[ix["PUESTO"]])
            v = int(row[ix["VOTOS"]] or 0)
            if can == "996":
                par, nom, circ = BLANCO, "Votos en blanco", circ_code
            elif can == "997":
                par, nom, circ = NULOS, "Votos nulos", circ_code
            elif can == "998":
                par, nom, circ = NOMARC, "No marcados", circ_code
            elif parnom == "CANDIDATOS TOTALES":
                continue                                  # totalizador, se descarta
            else:
                par = str(row[ix["PAR"]]).strip()
                nom = parnom
                circ = circ_code
            acc[(corp, circ, key, par, nom)] += v
            tot[(corp, par, nom)] += v
    _write(acc, "votos-2026-cundi-puesto.csv")
    _report("2026", tot)


def _write(acc, fname):
    path = os.path.join(OUT, fname)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["corp", "circ", "key", "par_code", "partido", "votos"])
        for (corp, circ, key, par, nom), v in sorted(acc.items()):
            w.writerow([corp, circ, key, par, nom, v])
    print(f"-> {fname}: {len(acc):,} filas")


def _report(year, tot):
    print(f"\n== {year} · totales por corporación ==")
    for corp in ("SENADO", "CAMARA"):
        rows = [(nom, v) for (c, par, nom), v in tot.items() if c == corp]
        s = sum(v for _, v in rows)
        print(f"  {corp}: {s:,} votos · {len(rows)} listas/pseudo")
        for nom, v in sorted(rows, key=lambda x: -x[1])[:8]:
            print(f"     {v:>10,}  {nom[:48]}")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("2022", "both"):
        agg_2022()
    if which in ("2026", "both"):
        agg_2026()
