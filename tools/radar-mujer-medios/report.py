#!/usr/bin/env python3
"""
radar-mujer-medios · report.py

Agrega los JSONL crudos del colector y produce el informe de escucha de
medios de Radar Mujer (MxD): volumen por tema, medios que marcan agenda,
nube de términos, titulares destacados por tema, y un digest narrativo
generado por DeepSeek (si hay API key) listo para el reporte con marca MxD.

Lee de:
    ./_local_out/raw/mujer/**/*.jsonl        (modo local, default)
  o de S3 si se corre con --s3 (mismo layout que el colector).

Escribe:
    ./_local_out/informe-YYYYMMDD.md          informe en markdown
    ./_local_out/agregados.json               agregados estructurados
    ./_local_out/digest-prompt.txt            prompt listo para cualquier LLM

DeepSeek: si la variable de entorno DEEPSEEK_API_KEY está seteada, llama a
la API (modelo deepseek-v4-flash) y mete el digest en el informe. Si no,
deja el prompt en digest-prompt.txt para pegarlo a mano.

Uso:
    python3 report.py                 # lee _local_out, ventana 7 días
    python3 report.py --dias 2        # ventana de 2 días
"""

import os
import re
import sys
import glob
import json
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

_HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL_RAW = os.path.join(_HERE, "_local_out", "raw", "mujer")
OUT_DIR = os.path.join(_HERE, "_local_out")

TEMA_LABEL = {
    "participacion_politica": "Participación política",
    "paridad": "Paridad / cuotas",
    "violencia_politica": "Violencia política",
    "feminicidio": "Feminicidio",
    "violencia_genero": "Violencia de género",
    "derechos_reproductivos": "Derechos reproductivos",
    "aborto_ive": "Aborto / IVE",
    "economia_cuidado": "Economía del cuidado",
    "liderazgo": "Liderazgo femenino",
    "cargos_ejecutivos": "Cargos ejecutivos",
    "brecha_laboral": "Brecha laboral",
    "ministerio_igualdad": "Ministerio de la Igualdad",
}

with open(os.path.join(_HERE, "stopwords-es.txt"), encoding="utf-8") as _f:
    STOPWORDS = {l.strip().lower() for l in _f if l.strip() and not l.lstrip().startswith("#")}
# ruido extra propio del tema (aparecen siempre, no aportan)
STOPWORDS |= {"colombia", "colombiano", "colombiana", "bogota", "pais", "nacional",
              "segun", "tras", "mas", "año", "años", "dice", "video", "foto"}

TOKEN_RE = re.compile(r"[a-záéíóúñü]+", re.IGNORECASE)

def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def is_stop(w):
    return w in STOPWORDS or strip_accents(w) in STOPWORDS

def tokenize(text):
    return [m.group().lower() for m in TOKEN_RE.finditer(text or "")]

def good(t):
    return len(t) >= 4 and not t.isdigit() and not is_stop(t)


def read_local(cutoff_iso):
    seen, out = set(), []
    for path in glob.glob(os.path.join(LOCAL_RAW, "**", "*.jsonl"), recursive=True):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                ts = ev.get("fecha_pub") or ev.get("fecha_capturada") or ""
                if ts and ts < cutoff_iso:
                    continue
                eid = ev.get("id")
                if not eid or eid in seen:
                    continue
                seen.add(eid)
                out.append(ev)
    return out


def temas_of(ev):
    t = ev.get("temas") or ([ev["tema"]] if ev.get("tema") else [])
    return [x for x in t if x]


def aggregate(events):
    por_tema = Counter()
    por_medio = Counter()
    palabras = Counter()
    tema_titulares = defaultdict(list)
    for ev in events:
        for t in temas_of(ev) or ["(directo)"]:
            por_tema[t] += 1
            tema_titulares[t].append(ev)
        por_medio[ev.get("medio", "desconocido")] += 1
        for tok in tokenize(ev.get("titulo")):
            if good(tok):
                palabras[tok] += 2
        for tok in tokenize(ev.get("resumen")):
            if good(tok):
                palabras[tok] += 1
    # titulares destacados por tema: los más recientes
    for t in tema_titulares:
        tema_titulares[t].sort(key=lambda e: e.get("fecha_pub") or "", reverse=True)
    return {
        "por_tema": por_tema,
        "por_medio": por_medio,
        "palabras": palabras,
        "tema_titulares": tema_titulares,
    }


def build_digest_prompt(agg, n_total, ventana_dias):
    lines = []
    lines.append(f"Eres analista de medios de Mujeres por la Democracia (MxD), una organización "
                 f"que promueve la participación política de las mujeres en Colombia. Redacta un "
                 f"informe breve de escucha de medios (tuteo neutro, sobrio, sin adjetivos de más) "
                 f"sobre la conversación de prensa de los últimos {ventana_dias} días en torno a las "
                 f"mujeres y su rol político y social. Se monitorearon {n_total} titulares de medios "
                 f"nacionales.\n")
    lines.append("VOLUMEN POR TEMA (número de titulares):")
    for t, n in agg["por_tema"].most_common():
        lines.append(f"  - {TEMA_LABEL.get(t, t)}: {n}")
    lines.append("\nMEDIOS QUE MÁS PUBLICARON:")
    for m, n in agg["por_medio"].most_common(12):
        lines.append(f"  - {m}: {n}")
    lines.append("\nTITULARES DESTACADOS POR TEMA (los más recientes):")
    for t, _ in agg["por_tema"].most_common(8):
        lines.append(f"\n[{TEMA_LABEL.get(t, t)}]")
        for ev in agg["tema_titulares"][t][:6]:
            lines.append(f"  · ({ev.get('medio')}) {ev.get('titulo')}")
    lines.append("\n\nCon base en lo anterior escribe, en máximo 350 palabras:")
    lines.append("1. UN PÁRRAFO de panorama: qué dominó la conversación y por qué importa para las mujeres.")
    lines.append("2. LOS 3 TEMAS MÁS CALIENTES con una frase cada uno (qué está pasando).")
    lines.append("3. UNA ALERTA: si hay un tema que se está encendiendo y MxD debería vigilar o pronunciarse.")
    lines.append("4. UNA RECOMENDACIÓN de vocería (sobre qué hablar esta semana y con qué encuadre).")
    lines.append("No inventes datos que no estén arriba. No cites cifras que no vengan de esta lista.")
    return "\n".join(lines)


def call_deepseek(prompt, intentos=2):
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return None
    body = json.dumps({
        "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1600,
        "temperature": 0.4,
    }).encode("utf-8")
    # V4 Flash puede fallar en cold call → un reintento corto.
    for i in range(max(1, intentos)):
        req = urllib.request.Request(
            "https://api.deepseek.com/chat/completions", data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            txt = (data["choices"][0]["message"]["content"] or "").strip()
            if txt:
                return txt
            print(f"[deepseek] respuesta vacía (intento {i+1})")
        except Exception as e:
            print(f"[deepseek] falló (intento {i+1}): {e}")
    return None


def build_markdown(agg, n_total, ventana_dias, digest, fecha):
    L = []
    L.append(f"# Radar Mujer · Informe de escucha de medios")
    L.append(f"**Mujeres por la Democracia** — {fecha:%d de %B de %Y} · ventana de {ventana_dias} días · {n_total} titulares monitoreados\n")
    L.append("> Monitoreo interno de prensa nacional. Fuentes: Google News (todo el ecosistema) + medios feministas directos. Solo contenido público.\n")

    if digest:
        L.append("## Lectura del analista\n")
        L.append(digest + "\n")
    else:
        L.append("## Lectura del analista\n")
        L.append("_(pendiente: correr con DEEPSEEK_API_KEY o pegar el prompt de `digest-prompt.txt` en el modelo)_\n")

    L.append("## Volumen por tema\n")
    L.append("| Tema | Titulares |")
    L.append("|---|---:|")
    for t, n in agg["por_tema"].most_common():
        L.append(f"| {TEMA_LABEL.get(t, t)} | {n} |")
    L.append("")

    L.append("## Medios que marcaron agenda\n")
    L.append("| Medio | Titulares |")
    L.append("|---|---:|")
    for m, n in agg["por_medio"].most_common(15):
        L.append(f"| {m} | {n} |")
    L.append("")

    L.append("## Términos más frecuentes\n")
    top = agg["palabras"].most_common(40)
    L.append(" · ".join(f"**{w}** ({n})" for w, n in top) + "\n")

    L.append("## Titulares destacados por tema\n")
    for t, _ in agg["por_tema"].most_common(8):
        L.append(f"### {TEMA_LABEL.get(t, t)}")
        for ev in agg["tema_titulares"][t][:6]:
            fecha_s = (ev.get("fecha_pub") or "")[:10]
            L.append(f"- _{ev.get('medio')}_ · {ev.get('titulo')}  ({fecha_s})")
        L.append("")
    return "\n".join(L)


def run(ventana_dias=7):
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=ventana_dias)).isoformat()
    events = read_local(cutoff)
    if not events:
        print("No hay eventos en la ventana. ¿Corriste collect.py --local?")
        return
    agg = aggregate(events)
    n_total = len(events)

    prompt = build_digest_prompt(agg, n_total, ventana_dias)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "digest-prompt.txt"), "w", encoding="utf-8") as f:
        f.write(prompt)

    digest = call_deepseek(prompt)
    if not digest:
        # Fallback: usar _local_out/digest.txt si existe (para demo sin API key)
        dp = os.path.join(OUT_DIR, "digest.txt")
        if os.path.exists(dp):
            with open(dp, encoding="utf-8") as f:
                digest = f.read().strip() or None

    # JSON listo para el tablero (agenda-mujer.html)
    tablero = {
        "generado_en": now.isoformat(),
        "ventana_dias": ventana_dias,
        "n_titulares": n_total,
        "n_medios": len(agg["por_medio"]),
        "n_temas": len(agg["por_tema"]),
        "digest": digest,
        "por_tema": [
            {"tema": t, "label": TEMA_LABEL.get(t, t), "n": n}
            for t, n in agg["por_tema"].most_common() if t != "(directo)"
        ],
        "por_medio": [{"medio": m, "n": n} for m, n in agg["por_medio"].most_common(20)],
        "palabras": [{"w": w, "n": n} for w, n in agg["palabras"].most_common(50)],
        "titulares_por_tema": {
            t: [
                {"medio": e.get("medio"), "titulo": e.get("titulo"),
                 "fecha": (e.get("fecha_pub") or "")[:10], "url": e.get("url")}
                for e in agg["tema_titulares"][t][:6]
            ]
            for t, _ in agg["por_tema"].most_common() if t != "(directo)"
        },
    }
    with open(os.path.join(OUT_DIR, "tablero.json"), "w", encoding="utf-8") as f:
        json.dump(tablero, f, ensure_ascii=False, indent=1)

    md = build_markdown(agg, n_total, ventana_dias, digest, now)
    fname = os.path.join(OUT_DIR, f"informe-{now:%Y%m%d}.md")
    with open(fname, "w", encoding="utf-8") as f:
        f.write(md)

    # agregados estructurados
    with open(os.path.join(OUT_DIR, "agregados.json"), "w", encoding="utf-8") as f:
        json.dump({
            "generado_en": now.isoformat(),
            "ventana_dias": ventana_dias,
            "n_titulares": n_total,
            "por_tema": dict(agg["por_tema"].most_common()),
            "por_medio": dict(agg["por_medio"].most_common(30)),
            "palabras": [{"w": w, "n": n} for w, n in agg["palabras"].most_common(60)],
        }, f, ensure_ascii=False, indent=1)

    print(f"Informe: {fname}")
    print(f"  {n_total} titulares · {len(agg['por_tema'])} temas · {len(agg['por_medio'])} medios")
    print(f"  digest DeepSeek: {'OK' if digest else 'pendiente (sin API key → ver digest-prompt.txt)'}")


if __name__ == "__main__":
    import locale
    try:
        locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")
    except Exception:
        pass
    dias = 7
    if "--dias" in sys.argv:
        dias = int(sys.argv[sys.argv.index("--dias") + 1])
    run(ventana_dias=dias)
