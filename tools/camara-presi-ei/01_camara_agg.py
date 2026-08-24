#!/usr/bin/env python3
"""Paso 1 — agrega la Cámara 2026 de Bogotá (MMV declarados, nivel mesa).

Lee el MMV de Bogotá (dep 16), filtra CORNOMBRE=CAMARA y produce:
  - party_totals: votos por partido (lista) en toda Bogotá
  - logo_votes:   votos solo-logo (CAN=000) por partido
  - cand_totals:  votos por candidato (preferente) -> (partido, cedula, nombre)
  - specials:     blanco / nulo / no marcado de Cámara
  - cir distinct, total camara

Luego corre D'Hondt (18 curules, umbral 3%) y lista los electos:
  - listas ABIERTAS  -> top-k candidatos por voto preferente
  - listas CERRADAS  -> orden de la lista (CLOSED_LISTS_16)

Salida: tools/camara-presi-ei/out/camara_agg.json  (resumen, sin nivel mesa)
"""
import csv, json, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

MMV = ("/Users/ricardoruiz/ricardoruiz.co/Bases de datos/DEPTOS_DECLARADOS/"
       "MMV_XXX_16_000_XXX_XX_XX_XXX_1009.csv")

CURULES = 18

# Listas cerradas de Bogotá (de camara-2026.html, dep 16). Orden = asignación.
CLOSED_LISTS_16 = {
    'MOVIMIENTO POLÍTICO PACTO HISTÓRICO': [
        'María Fernanda Carrascal Rojas','Daniel Mauricio Monroy Hernández',
        'Laura Daniela Beltrán Palomares','Heráclito Landínez Suárez',
        'María del Mar Pizarro García','Jairo León Vargas',
        'Claudia Teresa Romero Nader','Gabriel Becerra Yañez',
        'Sandra Mireya Nossa Quiroga','Andrés Camilo Rodríguez Castillo',
        'María Angélica Prada Uribe','Jhon Álvaro Forero Herrera',
        'Segundo Celio Nieves Herrera','María Alejandra Rojas Ordoñez',
        'Miguel Ángel Barriga Talero','Guayra Puka Arias Florian',
        'Juan de Jesús Hernández'],
    'LA LISTA DE OVIEDO - CON TODA POR BOGOTÁ': [
        'Paula Alejandra Moreno Villalobos','Antonio Perry Sáenz',
        'Carlos Eduardo Forero Palomino'],
    'MOTOCICLISTAS Y CONDUCTORES UNIDOS POR LA CAUSA': [
        'Diana Jazmín Cristiano Cristiano','Jorge Andrés Morelo Martínez',
        'David Enrique Novoa Bernal','Orlando de Jesús Parra Zuñiga',
        'Alain Rodríguez Martínez','Gustavo Giovanny Barrera Sánchez',
        'Solany Garzón Mendoza','Carlos Eustaquio Cañón Gutiérrez',
        'Juan Carlos Herrera Castillo','Johanna Natali Pérez López',
        'Julieth Natalia Onofre Núñez'],
}

def norm(s):
    return (s or '').strip().upper()

party_tot = defaultdict(int)      # PARNOMBRE -> votos
logo_tot  = defaultdict(int)      # PARNOMBRE -> votos solo-logo (CAN=000)
cand_tot  = defaultdict(int)      # (PARNOMBRE, CANCEDULA, CANNOMBRE) -> votos
cir_seen  = defaultdict(int)      # CIR -> filas
specials  = defaultdict(int)      # nombre -> votos (blanco/nulo/etc en CAMARA)
total_cam = 0
n_rows = 0

with open(MMV, newline='', encoding='utf-8', errors='replace') as f:
    r = csv.reader(f, delimiter=';')
    header = next(r)
    # localizar indices por nombre por robustez
    idx = {name: i for i, name in enumerate(header)}
    iCOR = idx['CORCODIGO']; iCORN = idx['CORNOMBRE']; iCIR = idx['CIR']
    iPARN = idx['PARNOMBRE']; iCAN = idx['CAN']; iCED = idx['CANCEDULA']
    iCANN = idx['CANNOMBRE']; iV = idx['VOTOS']
    for row in r:
        if len(row) <= iV:
            continue
        if row[iCOR] != '02':       # solo CAMARA
            continue
        n_rows += 1
        try:
            v = int(row[iV])
        except ValueError:
            v = 0
        cir_seen[row[iCIR]] += 1
        parn = norm(row[iPARN]); cann = norm(row[iCANN]); can = row[iCAN]
        total_cam += v
        # specials: partidos tipo VOTOS EN BLANCO / NULOS / NO MARCADOS
        if ('BLANCO' in parn or 'NULO' in parn or 'NO MARCAD' in parn
                or 'BLANCO' in cann or 'NULO' in cann or 'NO MARCAD' in cann):
            specials[parn or cann] += v
            continue
        party_tot[parn] += v
        if can == '000':
            logo_tot[parn] += v
        else:
            cand_tot[(parn, row[iCED], cann)] += v

# ---- D'Hondt 18 curules, umbral 3% (excluye blanco) ----
parties = {p: t for p, t in party_tot.items() if 'BLANCO' not in p}
grand = sum(parties.values())
umb = grand * 0.03
elig = {p: t for p, t in parties.items() if t >= umb}
seats = {p: 0 for p in elig}
for _ in range(CURULES):
    best, who = -1, None
    for p, t in elig.items():
        q = t / (seats[p] + 1)
        if q > best:
            best, who = q, p
    if who:
        seats[who] += 1

# ---- electos por partido ----
def cands_of(party):
    out = [(ced, nom, v) for (p, ced, nom), v in cand_tot.items() if p == party]
    out.sort(key=lambda x: -x[2])
    return out

electos = []   # dict por curul
closed_norm = {norm(k): k for k in CLOSED_LISTS_16}
for p, k in sorted(seats.items(), key=lambda x: -x[1]):
    if k == 0:
        continue
    if p in closed_norm:                      # lista cerrada
        names = CLOSED_LISTS_16[closed_norm[p]]
        for i in range(k):
            nm = names[i] if i < len(names) else f'Posición {i+1}'
            electos.append({'partido': p, 'tipo': 'cerrada', 'orden': i+1,
                            'nombre': nm, 'cedula': None, 'voto_pref': None})
    else:                                     # lista abierta
        cc = cands_of(p)
        for i in range(k):
            ced, nom, v = cc[i]
            electos.append({'partido': p, 'tipo': 'abierta', 'orden': i+1,
                            'nombre': nom, 'cedula': ced, 'voto_pref': v})

summary = {
    'n_rows_camara': n_rows,
    'total_camara_votos': total_cam,
    'cir_distinct': dict(cir_seen),
    'grand_total_listas': grand,
    'umbral_3pct': round(umb),
    'specials': dict(specials),
    'party_totals': dict(sorted(parties.items(), key=lambda x: -x[1])),
    'logo_votes': dict(logo_tot),
    'seats': {p: s for p, s in sorted(seats.items(), key=lambda x: -x[1]) if s > 0},
    'electos': electos,
}
with open(os.path.join(OUT, 'camara_agg.json'), 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

# ---- print legible ----
print(f"Filas CAMARA: {n_rows:,} · total votos Cámara: {total_cam:,}")
print(f"CIR distinct: {dict(cir_seen)}")
print(f"Specials: {dict(specials)}")
print(f"\nGran total listas (sin blanco): {grand:,} · umbral 3% = {round(umb):,}\n")
print("PARTIDOS (top 16) y curules:")
for p, t in list(sorted(parties.items(), key=lambda x: -x[1]))[:16]:
    s = seats.get(p, 0)
    mark = '  CERRADA' if p in closed_norm else ''
    print(f"  {t:>10,}  {('['+str(s)+']') if s else '   '}  {p[:55]}{mark}")
print(f"\n=== {len(electos)} ELECTOS ===")
for e in electos:
    pref = f"{e['voto_pref']:,}" if e['voto_pref'] is not None else 'lista'
    print(f"  [{e['partido'][:28]:28}] {e['tipo'][:7]:7} #{e['orden']:2}  "
          f"{e['nombre'][:40]:40} pref={pref}")
