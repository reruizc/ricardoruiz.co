"""Representatividad 2026 · % mujeres electas Senado y Cámara 2026.

Reconstruye la lista de electos del Congreso 2026 desde los mismos JSON de
S3 que consumen senado-2026.html / camara-2026.html, clasifica cada electo
por género con un diccionario de nombres colombianos (+ overrides manuales),
y emite el JSON que alimenta la sección 04 de
observatorio-mujer/mapa-representatividad.html.

Lógica de electos (replica exacta del frontend):
  SENADO
    · NACIONAL: 100 curules. resumenData.partidos ya trae `curules` (D'Hondt).
      - listas cerradas (CLOSED_LISTS del HTML): primeros `curules` en orden.
      - listas abiertas: candidatos ordenados por voto (el JSON ya viene desc),
        saltando el pseudo-candidato con el nombre de la lista, primeros `curules`.
    · INDIGENAS: 2 curules por D'Hondt sobre los partidos indígenas.
  CÁMARA
    · TERRITORIAL: por depto, asignarCurules(votos, curules_dep); electos =
      candidatos en orden de voto saltando el nombre-lista, primeros N.
    · INDIGENAS (2) y AFRO (2): pool de candidatos entre deptos de esa circ,
      D'Hondt, electos por voto. AFRO usa AFRO_CLOSED_LISTS cuando aplica.

Género: dict NOMBRES (primer nombre → M/F). Los ambiguos o no encontrados van
a un CSV de revisión manual `representatividad-2026-revisar.csv`; los overrides
confirmados se pegan en OVERRIDES para que no vuelvan a salir.

Salida:
  Bases de datos/output_observatorio_mujer/representatividad-2026.json
  Bases de datos/output_observatorio_mujer/representatividad-2026-revisar.csv

Uso: python3 tools/build-observatorio-mujer/build-representatividad-2026.py
"""
import csv, json, re, unicodedata, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML_SENADO = ROOT / "senado-2026.html"
HTML_CAMARA = ROOT / "camara-2026.html"
OUTDIR = ROOT / "Bases de datos" / "output_observatorio_mujer"
OUT = OUTDIR / "representatividad-2026.json"
OUT_REV = OUTDIR / "representatividad-2026-revisar.csv"

S3 = "https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output"
CURULES_INDIGENAS_SEN = 2
CURULES_INDIGENAS_CAM = 1
CURULES_AFRO_CAM = 2

# ── Diccionario de nombres colombianos → género ──────────────────────────
# Solo el PRIMER nombre. Si el primer nombre es ambiguo/desconocido, el motor
# intenta el segundo. Lo que no resuelva sale al CSV de revisión.
NOM_F = {
    "maria","ana","luz","gloria","claudia","diana","sandra","patricia","paula",
    "laura","carmen","rosa","martha","marta","angela","adriana","carolina","catalina",
    "juliana","juana","juli","julia","isabel","cristina","esperanza","yolanda","nubia",
    "yaneth","janeth","yanet","stella","estela","beatriz","alba","amparo","consuelo",
    "clara","edith","elizabeth","emma","ericka","erika","fanny","flor","gladys","gina",
    "ingrid","irma","liliana","lina","luisa","margarita","mariana","marcela","mercedes",
    "monica","mónica","nancy","natalia","nidia","norma","olga","piedad","pilar","ruth",
    "sofia","sofía","teresa","valentina","vanesa","vanessa","viviana","ximena","yenny",
    "jenny","yesenia","zulma","astrid","aida","aída","alexandra","angelica","angélica",
    "aura","betty","blanca","cecilia","dora","elsa","eugenia","fabiola","francia",
    "gladis","helena","henny","ivonne","yvonne","jimena","josefina","karen","karol",
    "kelly","leidy","leydi","lorena","lucia","lucía","lucero","magda","mabel","milena",
    "myriam","miriam","nohora","nohemi","noralba","omaira","orsinia","rocio","rocío",
    "rosalba","rubiela","sara","sonia","susana","tatiana","victoria","wilma","yadira",
    "yamile","yamileth","yeimy","yina","zandra","deisy","daisy","deyci","dorina","etna",
    "jael","kamelia","mary","nellys","rossih","colombia","betzy","alix","doris","feliza",
    "geny","jeny","liceth","lizeth","marelen","mireya","nury","olinda","paola","rina",
    "shirley","yolima","yudy","yuly","esmeralda","germania","leonor","nazly","astrith",
    "julieth","eimy","yoana","yohana","johana","yudi","yenifer","jennifer","dalys",
}
NOM_M = {
    "juan","carlos","luis","jorge","jose","josé","andres","andrés","david","daniel",
    "pedro","pablo","miguel","fernando","alberto","alvaro","álvaro","antonio","javier",
    "german","germán","gustavo","hernan","hernán","hector","héctor","ivan","iván","jaime",
    "julian","julián","mauricio","oscar","óscar","ricardo","rodrigo","sergio","victor",
    "víctor","william","wilson","alejandro","alexander","cesar","césar","cristian",
    "christian","diego","edgar","edwin","efrain","efraín","enrique","esteban","fabian",
    "fabián","felipe","francisco","gabriel","gerardo","gilberto","guillermo","henry",
    "jairo","john","jhon","jonathan","jesus","jesús","leonardo","manuel","marco","mario",
    "martin","martín","nelson","nicolas","nicolás","omar","orlando","raul","raúl","rafael",
    "ramon","ramón","roberto","rodolfo","samuel","santiago","saul","saúl","sebastian",
    "sebastián","tomas","tomás","wilmar","wilmer","alexis","alfonso","alfredo","anibal",
    "aníbal","armando","arturo","augusto","aurelio","benjamin","benjamín","bernardo",
    "camilo","dario","darío","eduardo","emilio","ernesto","eugenio","fabio","felix",
    "félix","freddy","harold","heriberto","holman","honorio","hugo","humberto","ignacio",
    "isidro","israel","jacobo","jairon","jhonatan","joaquin","joaquín","josue","josué",
    "leonel","libardo","lider","lidio","luciano","marcos","mateo","milton","modesto",
    "moises","moisés","napoleon","napoleón","neftali","norberto","octavio","otoniel",
    "pastor","plutarco","reinaldo","robert","robinson","rubén","ruben","salomon","salomón",
    "teodoro","tulio","uriel","valentin","valentín","virgilio","wilfredo","yeison",
    "abel","adan","adán","agmeth","alirio","aldo","cristobal","cristóbal","dagoberto",
    "elkin","etna_m","feliciano","ferney","jarrinson","josue_m","neber","olmes","plinio",
    "silverio","winsner","nessir","adalberto","adolfo","amado","apolinar","atilano",
    "hernando","fernan","fernán","jhonatan","jhonier","yesid","aicardo","teofilo","teófilo",
}
# Overrides confirmados a mano (nombre completo → M/F). Ganan sobre el
# diccionario. Se normalizan al cargar (norm() abajo) para casar la clave.
# Verificados uno por uno contra los electos 2026 (Registraduría/prensa).
_OVERRIDES_RAW = {
    "ALEJANDRA GABRIELA ABASOLO GOMEZ": "F", "ANDREA PADILLA VILLARRAGA": "F",
    "ARLEDY ALVARADO PATIÑO": "F", "ALEX XAVIER FLOREZ HERNANDEZ": "M",
    "BENILDO ESTUPIÑAN SOLIS": "M", "BLEIDY DEL CARMEN PEREZ BALLESTAS": "F",
    "CAROL STEFANNY BORDA ACEVEDO": "F", "CATHERINE JUVINAO CLAVIJO": "F",
    "DANIA MARITZA ALVAREZ BARRERA": "F", "DIDIER LOBO CHINCHILLA": "M",
    "DIVER NEY FRANCO TEJADA": "M", "DUVALIER SANCHEZ ARANGO": "M",
    "ESTEFANEL GUTIERREZ PEREZ": "M", "FLORA PERDOMO ANDRADE": "F",
    "FRANKLIN DEL CRISTO LOZANO DE LA OSSA": "M", "FRANYELA BERMUDEZ SERNA": "F",
    "GERSSON VARGAS VALDELEON": "M", "GONZALO DIMAS BAUTE GONZALEZ": "M",
    "HILDA GUTIERREZ": "F", "JENNIFER DALLEY PEDRAZA SANDOVAL": "F",
    "KELYN JOHANA GONZALEZ DUARTE": "F", "LINER CAMPO TEJEDOR": "M",
    "MELISSA ORREGO EUSSE": "F", "MELLO CASTRO GONZALEZ": "M",
    "NADYA GEORGETTE BLEL SCAFF": "F", "NATALY VELEZ LOPERA": "F",
    "SIMON MOLINA GOMEZ": "M", "WELFRAN JUNIOR MENDOZA TORRES": "M",
    "WILDER IBERSON ESCOBAR ORTIZ": "M", "YAMIT NOE HURTADO NEIRA": "M",
}
OVERRIDES = {}  # se llena tras definir norm()

def norm(s):
    if not s: return ""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.strip().upper()

OVERRIDES = {norm(k): v for k, v in _OVERRIDES_RAW.items()}

def tokens_min(nombre):
    return [t for t in re.split(r"[\s]+", norm(nombre).lower()) if t]

def genero(nombre):
    """Devuelve 'F', 'M' o None (desconocido)."""
    key = norm(nombre)
    if key in OVERRIDES:
        return OVERRIDES[key]
    toks = tokens_min(nombre)
    for t in toks[:2]:  # primer y segundo nombre
        if t in NOM_F: return "F"
        if t in NOM_M: return "M"
    return None

# ── Carga de listas cerradas desde los HTML ──────────────────────────────
def parse_js_obj_of_lists(html, var):
    """Extrae un objeto JS { 'CLAVE':[...], } a dict python de forma robusta."""
    m = re.search(re.escape(var) + r"\s*=\s*\{", html)
    if not m: return {}
    i = m.end() - 1
    depth = 0
    for j in range(i, len(html)):
        if html[j] == "{": depth += 1
        elif html[j] == "}":
            depth -= 1
            if depth == 0:
                block = html[i:j+1]; break
    out = {}
    # cada entrada: 'CLAVE':[ 'a','b',... ]
    for mk in re.finditer(r"'([^']+)'\s*:\s*\[", block):
        clave = mk.group(1)
        k = mk.end() - 1
        d = 0
        for j in range(k, len(block)):
            if block[j] == "[": d += 1
            elif block[j] == "]":
                d -= 1
                if d == 0:
                    arr = block[k:j+1]; break
        nombres = re.findall(r"'([^']+)'", arr)
        out[clave] = nombres
    return out

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.load(urllib.request.urlopen(req, timeout=90))

# ── Motor de electos ─────────────────────────────────────────────────────
def dhondt(votos_dict, seats):
    elig = [(p, v) for p, v in votos_dict.items() if v > 0 and "blanco" not in p.lower()]
    cur = {p: 0 for p, _ in elig}
    for _ in range(seats):
        best, bp = -1, None
        for p, v in elig:
            q = v / (cur[p] + 1)
            if q > best: best, bp = q, p
        if bp is not None: cur[bp] += 1
    return cur

def electos_open(cands, n, partido):
    """cands = [{nombre,votos}], ya ordenados por voto desc. Salta nombre-lista."""
    npart = norm(partido)
    out, r = [], n
    for c in cands:
        if r <= 0: break
        if norm(c["nombre"]) == npart:  # voto por la lista, no persona
            continue
        out.append(c["nombre"]); r -= 1
    return out

def clasif(nombres):
    f = m = x = 0
    desconocidos = []
    for nom in nombres:
        g = genero(nom)
        if g == "F": f += 1
        elif g == "M": m += 1
        else:
            x += 1; desconocidos.append(nom)
    return f, m, x, desconocidos

def main():
    html_s = HTML_SENADO.read_text()
    html_c = HTML_CAMARA.read_text()
    CLOSED_SEN = parse_js_obj_of_lists(html_s, "const CLOSED_LISTS")
    AFRO_CAM = parse_js_obj_of_lists(html_c, "const AFRO_CLOSED_LISTS")
    print(f"Listas cerradas Senado: {len(CLOSED_SEN)} · AFRO Cámara: {len(AFRO_CAM)}")

    revisar = []  # (camara, territorio, partido, nombre)
    result = {"v": "2026", "fuente": "Registraduría escrutinio 2026 · clasificación propia por género"}

    # ═══ SENADO ═══
    sen = get(f"{S3}/senado/resumen.json")
    sen_bancadas = []
    sen_electos = []  # (partido, nombre, genero)
    for p in sen["partidos"]:
        cur = p.get("curules", 0)
        if cur <= 0: continue
        if p["partido"] in CLOSED_SEN:
            nombres = CLOSED_SEN[p["partido"]][:cur]
        else:
            nombres = electos_open(p.get("candidatos") or [], cur, p["partido"])
        f, m, x, desc = clasif(nombres)
        for nom in nombres:
            g = genero(nom)
            sen_electos.append((p["partido"], nom, g))
            if g is None: revisar.append(("senado", "NACIONAL", p["partido"], nom))
        sen_bancadas.append({
            "partido": p["partido"], "curules": cur,
            "mujeres": f, "hombres": m, "sin_clasificar": x,
            "pct_mujeres": round(100 * f / cur, 1) if cur else 0,
        })

    # Indígenas senado (2 curules)
    ind = sen.get("por_circunscripcion", {}).get("INDIGENAS", {})
    sen_ind = {"curules": 0, "mujeres": 0, "hombres": 0}
    ind_parts = ind.get("partidos")
    if ind_parts:
        votos = {}
        cand_by_part = {}
        for pp in ind_parts:
            votos[pp["partido"]] = pp.get("votos", 0)
            cand_by_part[pp["partido"]] = pp.get("candidatos") or []
        cur = dhondt(votos, CURULES_INDIGENAS_SEN)
        for part, n in cur.items():
            if n <= 0: continue
            nombres = electos_open(cand_by_part.get(part, []), n, part)
            for nom in nombres:
                g = genero(nom); sen_ind["curules"] += 1
                if g == "F": sen_ind["mujeres"] += 1
                elif g == "M": sen_ind["hombres"] += 1
                else: revisar.append(("senado", "INDIGENAS", part, nom))
                sen_electos.append((part, nom, g))

    sen_tot = len(sen_electos)
    sen_muj = sum(1 for _, _, g in sen_electos if g == "F")
    result["senado"] = {
        "total_electos": sen_tot,
        "mujeres": sen_muj,
        "hombres": sum(1 for _, _, g in sen_electos if g == "M"),
        "sin_clasificar": sum(1 for _, _, g in sen_electos if g is None),
        "pct_mujeres": round(100 * sen_muj / sen_tot, 1) if sen_tot else 0,
        "por_bancada": sorted(sen_bancadas, key=lambda b: -b["curules"]),
        "indigenas": sen_ind,
    }

    # ═══ CÁMARA ═══
    deps = get(f"{S3}/camara/departamentos.json")
    CURULES_DEP = parse_curules_dep(html_c)
    cam_electos = []          # (dep, partido, nombre, genero)
    cam_por_depto = []
    # territorial por depto
    pool_ind = {}   # partido → {nombre: votos}
    pool_afro = {}
    for dep in deps:
        circ = dep_circ(dep)
        if circ == "INDIGENAS":
            _accum_pool(pool_ind, dep); continue
        if circ == "AFRO":
            _accum_pool(pool_afro, dep); continue
        # territorial
        ncur = curules_dep_lookup(dep["nombre"], CURULES_DEP)
        if ncur <= 0: continue
        cur = asignar_curules(dep.get("partidos", {}), ncur)
        d_f = d_m = d_x = d_tot = d_pend = 0
        for part, n in cur.items():
            if n <= 0: continue
            cands = (dep.get("candidatos") or {}).get(part, [])
            nombres = electos_open(cands, n, part)
            # Curules sin nombre = listas cerradas (Pacto) cuyos candidatos no
            # están en datos abiertos de votos. Se cuentan como pendientes.
            d_pend += (n - len(nombres))
            for nom in nombres:
                g = genero(nom); d_tot += 1
                cam_electos.append((dep["nombre"], part, nom, g))
                if g == "F": d_f += 1
                elif g == "M": d_m += 1
                else: d_x += 1; revisar.append(("camara", dep["nombre"], part, nom))
        cam_por_depto.append({
            "depto": dep["nombre"], "curules_totales": ncur,
            "curules_con_nombre": d_tot, "pendientes_lista_cerrada": d_pend,
            "mujeres": d_f, "hombres": d_m, "sin_clasificar": d_x,
            "pct_mujeres": round(100 * d_f / d_tot, 1) if d_tot else 0,
        })
    # indígenas / afro nacionales
    def _resolve_pool(pool, seats, closed=None):
        votos = {p: sum(d.values()) for p, d in pool.items()}
        cur = dhondt(votos, seats)
        agg = {"curules": 0, "mujeres": 0, "hombres": 0}
        for part, n in cur.items():
            if n <= 0: continue
            if closed and part in closed:
                nombres = closed[part][:n]
            else:
                nombres = [nom for nom, _ in sorted(pool[part].items(), key=lambda kv: -kv[1])][:n]
            for nom in nombres:
                g = genero(nom); agg["curules"] += 1
                if g == "F": agg["mujeres"] += 1
                elif g == "M": agg["hombres"] += 1
                else: revisar.append(("camara", "circ-especial", part, nom))
                cam_electos.append(("(especial)", part, nom, g))
        return agg
    cam_ind = _resolve_pool(pool_ind, CURULES_INDIGENAS_CAM)
    cam_afro = _resolve_pool(pool_afro, CURULES_AFRO_CAM, AFRO_CAM)

    cam_tot = len(cam_electos)
    cam_muj = sum(1 for *_, g in cam_electos if g == "F")
    cam_pend = sum(d["pendientes_lista_cerrada"] for d in cam_por_depto)
    result["camara"] = {
        "curules_totales": 165,
        "con_nombre": cam_tot,
        "pendientes_lista_cerrada": cam_pend,
        "mujeres": cam_muj,
        "hombres": sum(1 for *_, g in cam_electos if g == "M"),
        "sin_clasificar": sum(1 for *_, g in cam_electos if g is None),
        "pct_mujeres_sobre_con_nombre": round(100 * cam_muj / cam_tot, 1) if cam_tot else 0,
        "nota_pendientes": ("Faltan por nombrar las curules de listas cerradas "
            "(Pacto Histórico) cuyos candidatos no aparecen en los datos abiertos "
            "de votos de la Registraduría; se ingresan a mano igual que el Senado. "
            "Como el Pacto es el bloque más paritario, excluirlas tiende a SUBESTIMAR "
            "el % de mujeres real de la Cámara."),
        "por_depto": sorted(cam_por_depto, key=lambda d: -d["pct_mujeres"]),
        "indigenas": cam_ind, "afro": cam_afro,
    }

    # Congreso total
    tot = sen_tot + cam_tot
    muj = sen_muj + cam_muj
    result["congreso"] = {
        "electos_con_nombre": tot, "mujeres": muj,
        "pct_mujeres": round(100 * muj / tot, 1) if tot else 0,
        "nota": "Senado completo; Cámara sobre curules con nombre confirmado.",
    }

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1))
    # CSV de revisión
    with open(OUT_REV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["camara", "territorio", "partido", "nombre", "genero_sugerido(F/M)"])
        for row in revisar: w.writerow(list(row) + [""])

    # ── Reporte ──
    print(f"\n=== SENADO ===  {sen_tot} electos · {sen_muj} mujeres = {result['senado']['pct_mujeres']}%")
    for b in result["senado"]["por_bancada"][:8]:
        print(f"  {b['partido'][:38]:40s} {b['curules']:3d} cur · {b['pct_mujeres']:5.1f}% muj")
    print(f"=== CÁMARA ===  {cam_tot} con nombre · {cam_muj} mujeres = "
          f"{result['camara']['pct_mujeres_sobre_con_nombre']}% · {cam_pend} pendientes (lista cerrada)")
    print(f"=== CONGRESO (sobre nombrados) === {tot} · {result['congreso']['pct_mujeres']}% mujeres")
    print(f"\nSin clasificar (revisar CSV): {len(revisar)} → {OUT_REV.name}")
    if revisar:
        muestra = sorted(set(r[3] for r in revisar))[:30]
        for n in muestra: print("   ·", n)
    print(f"\nEscrito: {OUT}")

def parse_curules_dep(html):
    m = re.search(r"const CURULES_DEP\s*=\s*\{(.*?)\};", html, re.S)
    out = {}
    for k, v in re.findall(r"'([^']+)'\s*:\s*(\d+)", m.group(1)):
        out[norm(k)] = int(v)
    return out

def curules_dep_lookup(nombre, CURULES_DEP):
    """Replica getCurulesDep: exacto primero, luego substring (nombres truncados)."""
    n = norm(nombre)
    if n in CURULES_DEP:
        return CURULES_DEP[n]
    for k, v in CURULES_DEP.items():
        if n in k or k in n:
            return v
    return 2

def dep_circ(dep):
    cn = norm(dep.get("circ_nom") or dep.get("nombre") or "")
    if "INDIG" in cn: return "INDIGENAS"
    if "AFRO" in cn or "NEGR" in cn: return "AFRO"
    return "TERRITORIAL"

def _accum_pool(pool, dep):
    for part, cands in (dep.get("candidatos") or {}).items():
        pool.setdefault(part, {})
        for c in cands:
            pool[part][c["nombre"]] = pool[part].get(c["nombre"], 0) + c.get("votos", 0)

def asignar_curules(votos, curules):
    elig = [(p, v) for p, v in votos.items() if v > 0 and "blanco" not in p.lower()]
    if not elig: return {}
    if curules == 1:
        win = max(elig, key=lambda x: x[1]); return {win[0]: 1}
    if curules == 2:
        total = sum(v for _, v in elig); cuo = total / 2; umb = cuo * 0.30
        el = [(p, v) for p, v in elig if v >= umb]
        cur = {p: 0 for p, _ in el}; rest = 2
        for p, v in el:
            n = int(v // cuo); cur[p] = n; rest -= n
        resid = sorted(el, key=lambda x: -(x[1] - cur[x[0]] * cuo))
        for p, _ in resid[:max(0, rest)]: cur[p] += 1
        return cur
    # D'Hondt umbral 3%
    total = sum(v for _, v in elig); umb = total * 0.03
    el = {p: v for p, v in elig if v >= umb}
    return dhondt(el, curules)

if __name__ == "__main__":
    main()
