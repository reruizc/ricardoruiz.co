#!/usr/bin/env python3
"""Refinamiento del EI de género con prior 'sin brecha' + extracción del
perfil de las MUJERES que votan Abelardo.

Prior principista (anti-inflación y anti-cornering):
  - 2 grupos: B0 = [resultado_nacional, resultado_nacional] (sin brecha sexo).
  - 6 grupos (sexo x edad): B0[:,M_a] = B0[:,H_a] = beta_edad_a (la EI de edad
    SOLA, sin distinguir sexo). El estimador solo separa M de H donde la señal
    lo soporta -> brechas conservadoras, sin soluciones de esquina 100/0.
Se reporta RAW (sin prior) vs REG (con prior) para ver sensibilidad.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

EDAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "edad-1v-2026")
sys.path.insert(0, os.path.abspath(EDAD))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fit_ei import fit_qp, duncan_davis, region_of  # noqa: E402
from fit_ei_gender import (load_year, W_sex, W_sexage, h2h_YT, fit_qp_reg,  # noqa: E402
                           CANDS, LABEL)
from build_blocs_depto import DEP  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "..", "Bases de datos", "output_mujeres_1v")
RNG = np.random.default_rng(20260611)
AGE3 = ["18-35", "36-60", "61+"]
B3idx = [[0, 1, 2], [3, 4, 5]]   # (M cols, H cols) dentro de W6


def W_age3(cells):
    """edad sola (3 bandas), todos los votantes -> shares."""
    BB = [[0, 1, 2, 3], [4, 5, 6, 7, 8], [9]]
    tot = cells[:, :10] + cells[:, 10:]
    cols = [tot[:, idx].sum(axis=1) for idx in BB]
    Wg = np.column_stack(cols)
    return Wg / np.maximum(Wg.sum(axis=1, keepdims=True), 1e-9)


def fit_nat_reg(meta, W, Y, T, B0=None, lam_frac=0.0):
    strata = sorted(meta["stratum"].unique())
    Bs, Ms = {}, {}
    for s in strata:
        sel = (meta["stratum"] == s).values
        if B0 is None or lam_frac == 0:
            Bs[s] = fit_qp(W[sel], Y[sel], T[sel])
        else:
            Bs[s] = fit_qp_reg(W[sel], Y[sel], T[sel], B0, lam_frac * T[sel].sum())
        Ms[s] = (W[sel] * T[sel, None]).sum(axis=0)
    Mtot = sum(Ms.values())
    Bn = sum(Bs[s] * (Ms[s] / Mtot)[None, :] for s in strata)
    return Bn, Mtot


def main():
    rep = []

    def log(*a):
        s = " ".join(str(x) for x in a)
        print(s, flush=True)
        rep.append(s)

    meta, cells, Y, T = load_year(2026)
    cands = CANDS[2026] + ["resto"]
    Wsex = W_sex(cells)        # [M, H]
    W6 = W_sexage(cells)       # M18-35,M36-60,M61, H...
    Wage = W_age3(cells)       # edad sola 3 bandas

    obs = (Y * T[:, None]).sum(0) / T.sum()

    # ---- prior de edad sola (3 bandas, sin sexo) ----
    Bage, _ = fit_nat_reg(meta, Wage, Y, T)
    log("EI de edad SOLA (3 bandas) · % del voto por banda (prior 'sin brecha'):")
    log("    " + "cand".ljust(9) + "".join(f"{g:>9s}" for g in AGE3))
    for i, c in enumerate(cands):
        log("    " + LABEL[c].ljust(9) + "".join(f"{Bage[i,a]*100:8.1f} " for a in range(3)))

    # ============ 2 grupos: RAW vs REG ============
    Braw, M2 = fit_nat_reg(meta, Wsex, Y, T)
    B0_2 = np.column_stack([obs, obs])                 # sin brecha
    LAMS = [0.10, 0.20, 0.35]
    log("\n" + "=" * 64)
    log("SI SOLO VOTARAN MUJERES / HOMBRES · sensibilidad a regularización")
    log("(brecha = Mujer - Hombre, pp · Cepeda y Abelardo)")
    log(f"   {'lam':>6s}  {'Cep M':>6s}{'Cep H':>6s}{'brC':>6s}   {'Abe M':>6s}{'Abe H':>6s}{'brA':>6s}")
    ci, ai = cands.index("cepeda"), cands.index("abelardo")
    log(f"   {'raw':>6s}  {Braw[ci,0]*100:6.1f}{Braw[ci,1]*100:6.1f}{(Braw[ci,0]-Braw[ci,1])*100:6.1f}"
        f"   {Braw[ai,0]*100:6.1f}{Braw[ai,1]*100:6.1f}{(Braw[ai,0]-Braw[ai,1])*100:6.1f}")
    chosen = None
    for lam in LAMS:
        Br, _ = fit_nat_reg(meta, Wsex, Y, T, B0_2, lam)
        log(f"   {lam:>6.2f}  {Br[ci,0]*100:6.1f}{Br[ci,1]*100:6.1f}{(Br[ci,0]-Br[ci,1])*100:6.1f}"
            f"   {Br[ai,0]*100:6.1f}{Br[ai,1]*100:6.1f}{(Br[ai,0]-Br[ai,1])*100:6.1f}")
        if lam == 0.20:
            chosen = Br
    # bootstrap del REG elegido (lam=0.20)
    muns = meta.groupby(["stratum", "mun"]).indices
    by = {}
    for (s, mn), idx in muns.items():
        by.setdefault(s, []).append(np.asarray(idx))
    boots = []
    for _ in range(200):
        Bs, Ms = {}, {}
        for s, blocks in by.items():
            pick = RNG.integers(0, len(blocks), len(blocks))
            idx = np.concatenate([blocks[i] for i in pick])
            Bs[s] = fit_qp_reg(Wsex[idx], Y[idx], T[idx], B0_2, 0.20 * T[idx].sum(), iters=1500)
            Ms[s] = (Wsex[idx] * T[idx, None]).sum(0)
        Mt = sum(Ms.values())
        boots.append(sum(Bs[s] * (Ms[s]/Mt)[None, :] for s in Bs))
    boots = np.stack(boots)
    lo = np.percentile(boots, 2.5, axis=0); hi = np.percentile(boots, 97.5, axis=0)

    log("\nESCENARIO REFINADO (lam=0.20) · 1ª vuelta:")
    res = {}
    for i, c in enumerate(cands):
        log(f"   {LABEL[c]:9s} mujeres {chosen[i,0]*100:5.1f} "
            f"(IC {lo[i,0]*100:.1f}-{hi[i,0]*100:.1f})  hombres {chosen[i,1]*100:5.1f}  "
            f"real {obs[i]*100:5.1f}  brecha {(chosen[i,0]-chosen[i,1])*100:+5.1f}")
        res[c] = dict(label=LABEL[c], muj=round(chosen[i,0]*100,1), hom=round(chosen[i,1]*100,1),
                      muj_lo=round(lo[i,0]*100,1), muj_hi=round(hi[i,0]*100,1),
                      real=round(obs[i]*100,1), brecha=round((chosen[i,0]-chosen[i,1])*100,1),
                      raw_muj=round(Braw[i,0]*100,1), raw_hom=round(Braw[i,1]*100,1))

    # ============ 6 grupos sexo x edad: REG con prior de edad ============
    B0_6 = np.column_stack([Bage[:, 0], Bage[:, 1], Bage[:, 2],
                            Bage[:, 0], Bage[:, 1], Bage[:, 2]])
    B6r, M6 = fit_nat_reg(meta, W6, Y, T, B0_6, 0.20)
    g6 = ["M·18-35", "M·36-60", "M·61+", "H·18-35", "H·36-60", "H·61+"]
    log("\nSEXO x EDAD refinado (% del voto dentro del grupo):")
    log("    " + "cand".ljust(9) + "".join(f"{g:>10s}" for g in g6))
    sxa = {}
    for i, c in enumerate(cands):
        log("    " + LABEL[c].ljust(9) + "".join(f"{B6r[i,a]*100:9.1f} " for a in range(6)))
        sxa[c] = {g6[a]: round(B6r[i,a]*100,1) for a in range(6)}

    # ============ H2H Cepeda-Abelardo sexo x edad ciudades (REG fuerte) ====
    Y2, T2 = h2h_YT(Y, T, cands)
    # prior H2H por edad (sin sexo)
    BageH, _ = fit_nat_reg(meta, Wage, Y2, T2)
    B0_6h = np.column_stack([BageH[:, 0], BageH[:, 1], BageH[:, 2],
                             BageH[:, 0], BageH[:, 1], BageH[:, 2]])
    CIUDADES = [("Bogotá", "16-001"), ("Medellín", "01-001"), ("Cali", "31-001"),
                ("Barranquilla", "03-001"), ("Cartagena", "05-001"),
                ("Bucaramanga", "27-001")]

    def h2h_city(mask, lamf=0.18, nb=120):
        idxall = np.where(mask)[0]
        B = fit_qp_reg(W6[mask], Y2[mask], T2[mask], B0_6h, lamf * T2[mask].sum())
        boots = []
        for _ in range(nb):
            idx = idxall[RNG.integers(0, len(idxall), len(idxall))]
            boots.append(fit_qp_reg(W6[idx], Y2[idx], T2[idx], B0_6h,
                                    lamf * T2[idx].sum(), iters=1000))
        boots = np.stack(boots)
        return B, np.percentile(boots, 2.5, 0), np.percentile(boots, 97.5, 0)

    log("\nH2H Cepeda por sexo x edad · REG (Cepeda % del duelo · M | H):")
    log("    " + "ciudad".ljust(13) + " M18-35 M36-60  M61+ | H18-35 H36-60  H61+")
    crows = []
    units = [("Nacional", np.ones(len(T), bool))] + \
            [(n, (meta["mun"] == k).values) for n, k in CIUDADES]
    for name, mask in units:
        B, lo6, hi6 = h2h_city(mask, lamf=0.14 if name == "Nacional" else 0.18,
                               nb=150 if name == "Nacional" else 100)
        crows.append(dict(unit=name, **{g6[a]: round(B[0,a]*100,1) for a in range(6)},
                          **{g6[a]+"_lo": round(lo6[0,a]*100,1) for a in range(6)},
                          **{g6[a]+"_hi": round(hi6[0,a]*100,1) for a in range(6)}))
        log(f"    {name:13s}" + "  " + " ".join(f"{B[0,a]*100:5.0f}" for a in range(3)) +
            "  | " + " ".join(f"{B[0,a]*100:5.0f}" for a in range(3, 6)))

    # ============ perfil de las MUJERES DE ABELARDO ============
    # por edad (del 6-grupos refinado) + por depto (donde Abelardo gana entre mujeres)
    log("\n" + "=" * 64)
    log("¿DÓNDE ESTÁN LAS MUJERES DE ABELARDO?")
    abe_age = {g6[a]: round(B6r[cands.index('abelardo'), a]*100, 1) for a in [0, 1, 2]}
    log(f"  por edad (entre mujeres): 18-35 {abe_age['M·18-35']} · "
        f"36-60 {abe_age['M·36-60']} · 61+ {abe_age['M·61+']}")
    # H2H por depto entre mujeres (REG) reusando lo ya hecho? recomputar simple aquí
    meta["dep"] = meta["pcode"].str[:2]
    B0_2h = np.column_stack([BageH.mean(1)*0 + (Y2*T2[:,None]).sum(0)/T2.sum(),
                             (Y2*T2[:,None]).sum(0)/T2.sum()])  # prior sin brecha H2H
    drows = []
    for dep, (name, geo) in DEP.items():
        mask = (meta["dep"] == dep).values
        if mask.sum() < 8:
            continue
        B = fit_qp_reg(Wsex[mask], Y2[mask], T2[mask], B0_2h, 0.12 * T2[mask].sum())
        drows.append(dict(dep=dep, name=name, cep_muj=round(B[0,0]*100,1),
                          cep_hom=round(B[0,1]*100,1)))
    abe_muj = sorted([d for d in drows if d["cep_muj"] < 50], key=lambda d: d["cep_muj"])
    log(f"  deptos donde Abelardo gana ENTRE MUJERES ({len(abe_muj)}):")
    for d in abe_muj:
        log(f"     {d['name']:20s} Abelardo {100-d['cep_muj']:.0f}% del duelo entre mujeres")
    J = {"escenario_1v": res, "sexo_edad_reg": sxa, "h2h_ciudades_reg": crows,
         "abelardo_mujeres_edad": abe_age,
         "abelardo_gana_mujeres_deptos": abe_muj,
         "h2h_deptos_reg": drows,
         "edad_sola_3b": {LABEL[cands[i]]: {AGE3[a]: round(Bage[i,a]*100,1) for a in range(3)}
                          for i in range(len(cands))}}
    with open(os.path.join(OUT, "mujeres-refinado.json"), "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "mujeres-refinado-report.txt"), "w") as f:
        f.write("\n".join(rep))
    log("\nmujeres-refinado.json escrito.")


if __name__ == "__main__":
    main()
