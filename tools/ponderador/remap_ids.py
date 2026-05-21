#!/usr/bin/env python3
"""
remap_ids.py — renombra ids del ponderador a los ids reales del CNE.

Cuando Ricardo agrega encuestas a mano antes de que el CNE las publique,
las nombra con un slug provisional (`40-invamer`, `41-atlas-abr29`, etc.).
Cuando el CNE las publica, les asigna ids distintos (`38-invamer`,
`42-atlas-intel`, ...). Este script aplica el mapping descubierto en
los CSVs de entrada del ponderador para que el detalle linkee al PDF
radicado real.

Toca dos archivos:
  Bases de datos/cne_encuestas_clasificadas.csv  (col `id`)
  Bases de datos/encuestas_porcentajes.csv       (col `encuesta_id`)

Por defecto hace dry-run e imprime el diff. Para escribir:

  python3 tools/ponderador/remap_ids.py --apply

Después de aplicar hay que re-correr el ponderador.
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

# Mapping descubierto al cruzar el detalle de las encuestas:
#   ponderador (mano)  →  CNE real
# Verificado contra firma + fecha_fin + n_muestra el 2026-05-20.
MAPPING: dict[str, str] = {
    "38-guarumo-ecoanalitica": "40-30-04-2026",
    "39-centro-nacional-de-consultoria": "41-centro-nacional-de-consultoria",
    "40-invamer": "38-invamer",
    "41-atlas-abr29": "42-atlas-intel",
    "42-gad3-abr": "39-gad-3",
}
# No remapeados a propósito:
#   wiki-celag-abr  → CELAG es firma extranjera, no radica en CNE
#   44-atlas-may14  → no radicada en CNE todavía

SCRIPT_DIR = Path(__file__).resolve().parent
WORKTREE_GUESS = SCRIPT_DIR.parents[1]
if ".claude" in WORKTREE_GUESS.parts and "worktrees" in WORKTREE_GUESS.parts:
    idx = WORKTREE_GUESS.parts.index(".claude")
    REPO_ROOT = Path(*WORKTREE_GUESS.parts[:idx])
else:
    REPO_ROOT = WORKTREE_GUESS

DATA_DIR = REPO_ROOT / "Bases de datos"

TARGETS = [
    (DATA_DIR / "cne_encuestas_clasificadas.csv", "id"),
    (DATA_DIR / "encuestas_porcentajes.csv", "encuesta_id"),
]


def remap_csv(path: Path, id_col: str, mapping: dict[str, str], apply: bool) -> dict[str, int]:
    """Lee el CSV, aplica mapping, escribe (si apply=True). Devuelve conteo por old_id."""
    counts: dict[str, int] = {old: 0 for old in mapping}
    counts["__rows_total__"] = 0

    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames or id_col not in fieldnames:
            print(f"  [skip] {path.name}: no encuentro columna '{id_col}'", file=sys.stderr)
            return counts
        rows = list(reader)

    new_rows = []
    for r in rows:
        counts["__rows_total__"] += 1
        old = r[id_col]
        if old in mapping:
            counts[old] += 1
            r[id_col] = mapping[old]
        new_rows.append(r)

    if apply:
        backup = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup)
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(new_rows)
        print(f"  ✓ {path.name}: escrito (backup en {backup.name})")
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description="Remapea ids del ponderador a ids reales del CNE.")
    ap.add_argument("--apply", action="store_true",
                    help="Escribe los cambios. Sin esta bandera solo imprime el diff.")
    args = ap.parse_args()

    print("== Mapping a aplicar ==")
    for old, new in MAPPING.items():
        print(f"  {old:42s} → {new}")
    print()

    total_changes = 0
    for path, col in TARGETS:
        if not path.exists():
            print(f"[skip] {path} no existe", file=sys.stderr)
            continue
        print(f"-- {path.name} (col `{col}`) --")
        counts = remap_csv(path, col, MAPPING, apply=args.apply)
        for old in MAPPING:
            n = counts.get(old, 0)
            if n > 0:
                print(f"  {old:42s} → {MAPPING[old]:42s}  ({n} filas)")
                total_changes += n
        print()

    if not args.apply:
        print(f"== DRY-RUN: {total_changes} filas se actualizarían. Re-correr con --apply para escribir. ==")
    else:
        print(f"== Listo: {total_changes} filas actualizadas. Re-correr el ponderador. ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())
