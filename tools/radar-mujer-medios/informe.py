#!/usr/bin/env python3
"""
radar-mujer-medios · informe.py

Módulo de INFORMES de Radar Mujer (MxD). A diferencia del tablero de agenda
mediática —que es una foto de la coyuntura y se reconstruye en cada corrida—
este módulo lee la ventana LARGA (15 o 30 días) del histórico crudo en S3,
la cruza con el pulso del mercado laboral femenino (DANE GEIH-MLS) y le pide
a DeepSeek una recomendación accionable: qué priorizar, qué acciones tomar y
qué llamados públicos hacer.

Diferencias de fondo con el digest de agenda-mujer:
  · ventana larga (15/30 d) en vez de la coyuntura de 2 días;
  · lee el histórico persistido en S3 (raw/mujer/yyyy=/mm=/dd=/*.jsonl),
    no una recolección nueva — no toca Google News ni Apify, cuesta $0;
  · cruza prensa + redes + datos duros del DANE en un solo prompt;
  · sale JSON estructurado (prioridades / acciones / llamados), no prosa
    suelta, para que el frontend lo pinte como fichas accionables;
  · compara la primera mitad de la ventana contra la segunda para decir qué
    está SUBIENDO, no solo qué es grande.

Salida: informe-mujer.json en el prefijo público del observatorio.

Uso local (necesita credenciales AWS y DEEPSEEK_API_KEY):
    python3 informe.py --dry-run              # arma el contexto, no llama al LLM
    python3 informe.py --ventana 15           # una ventana, imprime el JSON
    python3 informe.py --escribir             # las dos ventanas → S3
"""

import os
import re
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

import collect
import report
try:
    import collect_social
except Exception:
    collect_social = None

S3_BUCKET = os.environ.get("RADAR_S3_BUCKET", "elecciones-2026")
RAW_PREFIX = os.environ.get("RADAR_S3_PREFIX", "ricardoruiz.co/radar-mujer/medios")
OBS_PREFIX = "ricardoruiz.co/bases de datos/output_observatorio_mujer"
INFORME_KEY = f"{OBS_PREFIX}/informe-mujer.json"
EMPLEO_KEY = f"{OBS_PREFIX}/dane-empleo-mensual.json"
CIIU_KEY = f"{OBS_PREFIX}/dane-ciiu-mensual.json"

VENTANAS = (15, 30)

# Modo disco: si RADAR_LOCAL_DIR apunta a una copia del prefijo raw (bajada con
# `aws s3 cp --recursive`), todo lee de ahí en vez de S3. Sirve para iterar el
# prompt sin boto3 ni credenciales; en Lambda nunca está seteada.
LOCAL_DIR = os.environ.get("RADAR_LOCAL_DIR")
LOCAL_OBS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "..", "Bases de datos", "output_observatorio_mujer")

_s3 = None
def _s3c():
    global _s3
    if _s3 is None:
        import boto3
        _s3 = boto3.client("s3")
    return _s3


# ── Histórico crudo ──────────────────────────────────────────────────────
def _dias_particion(dias, hoy=None):
    """Particiones yyyy=/mm=/dd= de los últimos `dias` días (incluye hoy)."""
    hoy = hoy or datetime.now(timezone.utc)
    for i in range(dias + 1):
        d = hoy - timedelta(days=i)
        yield f"yyyy={d:%Y}/mm={d:%m}/dd={d:%d}"


def _leer_particion(part):
    """Devuelve los cuerpos (bytes) de todos los .jsonl de una partición."""
    if LOCAL_DIR:
        import glob as _glob
        for p in _glob.glob(os.path.join(LOCAL_DIR, part, "*.jsonl")):
            with open(p, "rb") as fh:
                yield fh.read()
        return
    s3 = _s3c()
    pref = f"{RAW_PREFIX}/raw/mujer/{part}/"
    token = None
    while True:
        kw = {"Bucket": S3_BUCKET, "Prefix": pref}
        if token:
            kw["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kw)
        for obj in resp.get("Contents", []):
            try:
                yield s3.get_object(Bucket=S3_BUCKET, Key=obj["Key"])["Body"].read()
            except Exception as e:
                print(f"[informe] no pude leer {obj['Key']}: {e}")
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")


def cargar_historico(dias, hoy=None):
    """Lee el crudo persistido de los últimos `dias` días y devuelve
    (prensa, redes) ya deduplicado y con las listas negras aplicadas.

    Se apoya en que la Lambda persiste cada corrida en
    raw/mujer/yyyy=/mm=/dd=/{fuente}__{run_id}.jsonl. Como las corridas se
    solapan (ventana de 7 d cada 6 h), el mismo evento aparece muchas veces:
    el dedup por id es obligatorio, no cosmético.
    """
    prensa, redes = {}, {}
    for part in _dias_particion(dias, hoy):
        for body in _leer_particion(part):
            for line in body.decode("utf-8", "replace").split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                _clasificar(ev, prensa, redes)
    # Recorte por fecha real de publicación: el crudo de un día puede traer
    # notas más viejas (Google News devuelve hasta 7 d hacia atrás).
    corte = ((hoy or datetime.now(timezone.utc)) - timedelta(days=dias)).isoformat()
    def dentro(e):
        return (e.get("fecha_pub") or e.get("fecha_capturada") or "") >= corte
    return ([e for e in prensa.values() if dentro(e)],
            [e for e in redes.values() if dentro(e)])


def _clasificar(ev, prensa, redes):
    """Mete el evento en el bucket que toca, aplicando las listas negras."""
    eid = ev.get("id") or ev.get("url") or ev.get("titulo")
    if not eid:
        return
    if ev.get("fuente") == "redes":
        if collect_social is not None and collect_social.cuenta_excluida(ev.get("autor")):
            return
        redes.setdefault(eid, ev)
    else:
        if collect.medio_excluido(ev.get("medio")):
            return
        prensa.setdefault(eid, ev)


def tendencia_por_tema(eventos, dias, hoy=None):
    """Compara la 1ª mitad de la ventana contra la 2ª: es lo que permite decir
    'esto está subiendo' y no solo 'esto es grande'.

    OJO con el sesgo de cobertura: el histórico crudo empezó a persistirse en
    julio de 2026 y Google News solo devuelve 7 días hacia atrás, así que en
    ventanas largas la mitad vieja puede tener muchos menos días con datos que
    la reciente — y entonces TODO parece subir. Por eso además del conteo bruto
    se devuelve el promedio por día con datos, y una bandera `comparable` que
    avisa cuando las dos mitades no se pueden comparar de frente.
    """
    hoy = hoy or datetime.now(timezone.utc)
    fecha = lambda e: (e.get("fecha_pub") or e.get("fecha_capturada") or "")

    # 1) Un día "cubierto" es uno con volumen normal. No basta con que tenga
    #    algún evento: los días previos al arranque del archivo traen 1-6
    #    titulares sueltos (rezagos que Google News devolvió después) y si se
    #    cuentan como días normales, hunden el promedio de la mitad vieja y
    #    todo parece dispararse.
    por_dia = Counter(fecha(e)[:10] for e in eventos if fecha(e))
    con_algo = sorted(n for n in por_dia.values() if n)
    if con_algo:
        mediana = con_algo[len(con_algo) // 2]
        piso = max(3, 0.25 * mediana)
    else:
        piso = 0
    cubiertos = {d for d, n in por_dia.items() if n >= piso}

    mitad = (hoy - timedelta(days=dias / 2)).isoformat()
    rec, prev = Counter(), Counter()
    dias_rec, dias_prev = set(), set()
    for e in eventos:
        f = fecha(e)
        if f[:10] not in cubiertos:
            continue          # día sin cobertura real: fuera de la comparación
        reciente = f >= mitad
        (dias_rec if reciente else dias_prev).add(f[:10])
        dest = rec if reciente else prev
        for t in (report.temas_of(e) or ["(directo)"]):
            dest[t] += 1
    nd_rec, nd_prev = max(1, len(dias_rec)), max(1, len(dias_prev))
    # Con menos del 60% de los días de la mitad reciente, el delta bruto mide
    # cobertura y no agenda: ahí manda el promedio por día.
    comparable = len(dias_prev) >= 0.6 * len(dias_rec) and len(dias_prev) >= 3
    out = []
    for t in set(rec) | set(prev):
        if t == "(directo)":
            continue
        pd_rec, pd_prev = rec[t] / nd_rec, prev[t] / nd_prev
        out.append({"tema": t, "label": report.TEMA_LABEL.get(t, t),
                    "reciente": rec[t], "previo": prev[t],
                    "delta": rec[t] - prev[t],
                    "por_dia_reciente": round(pd_rec, 1),
                    "por_dia_previo": round(pd_prev, 1),
                    "delta_dia": round(pd_rec - pd_prev, 1)})
    out.sort(key=lambda x: -(x["delta"] if comparable else x["delta_dia"]))
    meta = {"comparable": comparable,
            "dias_con_datos_reciente": len(dias_rec),
            "dias_con_datos_previo": len(dias_prev),
            "cobertura_desde": (min(cubiertos) if cubiertos else None),
            "dias_descartados": sorted(set(por_dia) - cubiertos)}
    return out, meta


# ── Pulso laboral (DANE) ─────────────────────────────────────────────────
def _get_json(key):
    try:
        if LOCAL_DIR:
            with open(os.path.join(LOCAL_OBS, os.path.basename(key)), encoding="utf-8") as fh:
                return json.load(fh)
        return json.loads(_s3c().get_object(Bucket=S3_BUCKET, Key=key)["Body"].read())
    except Exception as e:
        print(f"[informe] sin {key}: {e}")
        return None


def _ultimo(serie):
    for v in reversed(serie or []):
        if v is not None:
            return v
    return None


def _en(serie, tms, tm):
    try:
        return serie[tms.index(tm)]
    except Exception:
        return None


def resumen_pulso():
    """Extrae del anexo GEIH-MLS lo que le sirve a un informe: brechas
    nacionales, variación contra el año pasado, ciudades extremas y peso
    sectorial. Devuelve None si el dato no está disponible."""
    emp = _get_json(EMPLEO_KEY)
    if not emp:
        return None
    tms = emp.get("tms") or []
    tm = emp.get("actualizado_a")
    hace_un_anio = None
    if tm and len(tm) == 7:
        y, m = tm.split("-")
        hace_un_anio = f"{int(y) - 1}-{m}"

    nac = emp.get("nacional", {})
    out = {"tm": tm, "tm_anterior_anio": hace_un_anio, "nacional": {}, "ciudades": {}}
    for ind in ("tgp", "to", "td"):
        m_now = _ultimo(nac.get("mujeres", {}).get(ind))
        h_now = _ultimo(nac.get("hombres", {}).get(ind))
        m_ant = _en(nac.get("mujeres", {}).get(ind), tms, hace_un_anio)
        out["nacional"][ind] = {
            # Redondeadas: el DANE publica a un decimal y mandar 53.6454113793
            # al prompt solo agrega ruido que el modelo termina citando.
            "mujeres": (round(m_now, 1) if m_now is not None else None),
            "hombres": (round(h_now, 1) if h_now is not None else None),
            "brecha": (round(h_now - m_now, 1) if m_now is not None and h_now is not None else None),
            "var_anual_mujeres": (round(m_now - m_ant, 1) if m_now is not None and m_ant is not None else None),
        }

    # Ciudades: mayor y menor desempleo femenino, y mayor brecha de participación.
    td, brecha_tgp = [], []
    for ciudad, d in (emp.get("ciudades") or {}).items():
        tdm = _ultimo((d.get("mujeres") or {}).get("td"))
        tgm = _ultimo((d.get("mujeres") or {}).get("tgp"))
        tgh = _ultimo((d.get("hombres") or {}).get("tgp"))
        if tdm is not None:
            td.append((ciudad, round(tdm, 1)))
        if tgm is not None and tgh is not None:
            brecha_tgp.append((ciudad, round(tgh - tgm, 1)))
    td.sort(key=lambda x: -x[1])
    brecha_tgp.sort(key=lambda x: -x[1])
    out["ciudades"] = {
        "td_mujeres_alta": td[:4], "td_mujeres_baja": td[-3:][::-1],
        "brecha_participacion_alta": brecha_tgp[:4],
    }

    ciiu = _get_json(CIIU_KEY)
    if ciiu:
        ramas = ciiu.get("ramas") or []
        muj, tot = ciiu.get("mujeres") or {}, ciiu.get("total") or {}
        comp = []
        for r in ramas:
            m, t = _ultimo(muj.get(r)), _ultimo(tot.get(r))
            if m and t:
                comp.append({"rama": r, "miles_mujeres": round(m, 1),
                             "pct_mujeres": round(100 * m / t, 1)})
        comp.sort(key=lambda x: -x["miles_mujeres"])
        out["sectores"] = comp[:8]
    return out


# ── Prompt ───────────────────────────────────────────────────────────────
SCHEMA = """{
  "titular": "una frase que resuma el momento (máx 14 palabras)",
  "lectura": "2 párrafos de contexto: qué pasó en la ventana y qué significa para las mujeres",
  "prioridades": [{"tema":"", "por_que":"", "urgencia":"alta|media|baja"}],
  "acciones": [{"accion":"", "tipo":"comunicado|voceria|incidencia|investigacion|alianza|movilizacion", "plazo":"esta semana|este mes|siguiente trimestre", "por_que":""}],
  "llamados": [{"destinatario":"", "texto":"el llamado público, redactado para publicarse"}],
  "riesgos": [""],
  "vigilar": [""]
}"""


def build_prompt(dias, prensa_agg, redes_agg, tendencia, tend_meta, pulso, n_prensa, n_redes):
    L = []
    L.append(
        "Eres la analista senior de Mujeres por la Democracia (MxD), organización que promueve "
        "la participación política de las mujeres en Colombia. Te escribe la dirección pidiendo "
        f"una RECOMENDACIÓN DE ACCIÓN basada en el barrido de los últimos {dias} días. "
        "No quieren un resumen de noticias: quieren saber qué hacer y qué decir.\n")
    L.append(f"INSUMO 1 · PRENSA ({n_prensa} titulares únicos en la ventana)")
    L.append("Volumen por tema:")
    for t, n in prensa_agg["por_tema"].most_common():
        if t != "(directo)":
            L.append(f"  - {report.TEMA_LABEL.get(t, t)}: {n}")
    if tend_meta.get("comparable"):
        L.append("\nQué SUBE y qué BAJA (segunda mitad de la ventana vs primera):")
        for t in tendencia[:8]:
            signo = "+" if t["delta"] > 0 else ""
            L.append(f"  - {t['label']}: {t['previo']} → {t['reciente']} ({signo}{t['delta']})")
    else:
        L.append(f"\nQué SUBE y qué BAJA — promedio de titulares POR DÍA, porque el monitoreo "
                 f"tiene menos días registrados en la primera mitad de la ventana "
                 f"({tend_meta.get('dias_con_datos_previo')} días) que en la segunda "
                 f"({tend_meta.get('dias_con_datos_reciente')} días) y los totales crudos no "
                 f"son comparables:")
        for t in tendencia[:8]:
            signo = "+" if t["delta_dia"] > 0 else ""
            L.append(f"  - {t['label']}: {t['por_dia_previo']} → {t['por_dia_reciente']} por día "
                     f"({signo}{t['delta_dia']})")
        L.append("  AVISO: por ese desbalance, trata estas variaciones como indicativas y no "
                 "afirmes porcentajes de aumento en la ventana larga.")
    L.append("\nTitulares representativos por tema:")
    for t, _ in prensa_agg["por_tema"].most_common(7):
        if t == "(directo)":
            continue
        L.append(f"\n[{report.TEMA_LABEL.get(t, t)}]")
        for ev in prensa_agg["tema_titulares"][t][:5]:
            L.append(f"  · ({ev.get('medio')}) {ev.get('titulo')}")

    if redes_agg and n_redes:
        L.append(f"\n\nINSUMO 2 · REDES ({n_redes} publicaciones únicas)")
        L.append("Volumen por red: " + ", ".join(
            f"{report.RED_LABEL.get(r, r)} {n}" for r, n in redes_agg["por_red"].most_common()))
        L.append("Cuentas más activas: " + ", ".join(
            c for c, _ in redes_agg["por_cuenta"].most_common(10)))
        L.append("Publicaciones con más tracción:")
        for e in redes_agg["top_posts"][:8]:
            L.append(f"  · (@{e.get('autor')}) {(e.get('titulo') or '')[:150]}")

    if pulso:
        n = pulso["nacional"]
        L.append(f"\n\nINSUMO 3 · MERCADO LABORAL FEMENINO (DANE GEIH, trimestre móvil que cierra en {pulso['tm']})")
        for ind, nombre in (("tgp", "Tasa global de participación"),
                            ("to", "Tasa de ocupación"),
                            ("td", "Tasa de desempleo")):
            d = n.get(ind, {})
            if d.get("mujeres") is None:
                continue
            linea = (f"  - {nombre}: mujeres {d['mujeres']}% vs hombres {d['hombres']}% "
                     f"(brecha {d['brecha']} pp)")
            if d.get("var_anual_mujeres") is not None:
                linea += f"; las mujeres varían {d['var_anual_mujeres']:+} pp contra el mismo trimestre del año pasado"
            L.append(linea)
        c = pulso.get("ciudades", {})
        if c.get("td_mujeres_alta"):
            L.append("  - Desempleo femenino más alto: " + ", ".join(f"{k} {v}%" for k, v in c["td_mujeres_alta"]))
        if c.get("brecha_participacion_alta"):
            L.append("  - Mayor brecha de participación: " + ", ".join(f"{k} {v} pp" for k, v in c["brecha_participacion_alta"]))
        for s in (pulso.get("sectores") or [])[:5]:
            L.append(f"  - {s['rama']}: {s['miles_mujeres']} mil mujeres ocupadas ({s['pct_mujeres']}% del sector)")

    L.append("\n\nESCRIBE la recomendación con estas reglas:")
    L.append("· Tuteo neutro de Bogotá, sobrio, sin adjetivos de más y sin lenguaje de consultoría.")
    L.append("· Entre 3 y 5 prioridades, entre 4 y 6 acciones, entre 2 y 3 llamados públicos.")
    L.append("· Cada acción tiene que ser ejecutable por una organización de sociedad civil de "
             "tamaño medio: comunicado, vocería, derecho de petición, mesa técnica, alianza, "
             "investigación propia, movilización. Nada que dependa de tener poder que MxD no tiene.")
    L.append("· Los llamados públicos van redactados para publicarse tal cual, con destinatario "
             "concreto (una entidad, un ministerio, el Congreso, los partidos, los medios).")
    L.append("· Si un dato del DANE sostiene un argumento, cítalo con su cifra. Si no hay dato "
             "duro para algo, no lo inventes ni lo insinúes.")
    L.append("· Prioriza lo que SUBE en la ventana sobre lo que solo es grande: el valor está en "
             "llegar temprano.")
    L.append("· No inventes hechos, nombres, casos ni cifras que no estén arriba.")
    L.append(f"\nResponde SOLO un JSON válido con esta forma, sin texto alrededor ni ```:\n{SCHEMA}")
    return "\n".join(L)


def _parse_json_llm(txt):
    """El modelo a veces envuelve el JSON en ``` o le antepone una frase."""
    if not txt:
        return None
    s = txt.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s).strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    i, j = s.find("{"), s.rfind("}")
    if i >= 0 and j > i:
        try:
            return json.loads(s[i:j + 1])
        except Exception:
            pass
    return None


# ── Orquestación ─────────────────────────────────────────────────────────
def generar_ventana(dias, hoy=None, con_llm=True):
    prensa, redes = cargar_historico(dias, hoy)
    p_agg = report.aggregate(prensa)
    r_agg = report.aggregate_social(redes) if redes else None
    tend, tend_meta = tendencia_por_tema(prensa, dias, hoy)
    pulso = resumen_pulso()
    prompt = build_prompt(dias, p_agg, r_agg, tend, tend_meta, pulso, len(prensa), len(redes))

    bloque = {
        "ventana_dias": dias,
        "n_prensa": len(prensa),
        "n_redes": len(redes),
        "n_medios": len(p_agg["por_medio"]),
        "temas": [{"tema": t, "label": report.TEMA_LABEL.get(t, t), "n": n}
                  for t, n in p_agg["por_tema"].most_common() if t != "(directo)"],
        "tendencia": tend[:10],
        "tendencia_meta": tend_meta,
        "pulso": pulso,
        "informe": None,
        "informe_texto": None,
    }
    if not con_llm:
        bloque["_prompt_chars"] = len(prompt)
        return bloque, prompt

    txt = report.call_deepseek(prompt, max_tokens=8000)
    data = _parse_json_llm(txt)
    if data:
        bloque["informe"] = data
    else:
        # Nunca botamos la respuesta: si no parsea, el frontend la muestra como prosa.
        bloque["informe_texto"] = txt
        if txt:
            print(f"[informe {dias}d] el LLM no devolvió JSON parseable ({len(txt)} chars)")
    return bloque, prompt


def generar(hoy=None, ventanas=VENTANAS, con_llm=True):
    now = hoy or datetime.now(timezone.utc)
    out = {"generado_en": now.isoformat(), "ventanas": {}}
    for d in ventanas:
        bloque, _ = generar_ventana(d, now, con_llm)
        out["ventanas"][str(d)] = bloque
        print(f"[informe {d}d] prensa={bloque['n_prensa']} redes={bloque['n_redes']} "
              f"informe={'ok' if bloque['informe'] else ('texto' if bloque['informe_texto'] else 'no')}")
    return out


def escribir(data):
    _s3c().put_object(
        Bucket=S3_BUCKET, Key=INFORME_KEY,
        Body=json.dumps(data, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json", CacheControl="public, max-age=300")
    return INFORME_KEY


if __name__ == "__main__":
    args = sys.argv[1:]
    vent = VENTANAS
    if "--ventana" in args:
        vent = (int(args[args.index("--ventana") + 1]),)
    if "--dry-run" in args:
        for d in vent:
            b, p = generar_ventana(d, con_llm=False)
            print(f"\n===== VENTANA {d} DÍAS =====")
            print(f"prensa={b['n_prensa']} redes={b['n_redes']} medios={b['n_medios']} "
                  f"prompt={len(p)} chars")
            print("sube/baja:", [(t["label"], t["delta"], t["delta_dia"]) for t in b["tendencia"][:5]], b["tendencia_meta"])
            print("pulso:", json.dumps((b['pulso'] or {}).get('nacional'), ensure_ascii=False))
            print("\n--- PROMPT (primeros 1800 chars) ---\n" + p[:1800])
    else:
        data = generar(ventanas=vent)
        if "--escribir" in args:
            print("escrito en", escribir(data))
        else:
            print(json.dumps(data, ensure_ascii=False, indent=1)[:4000])
