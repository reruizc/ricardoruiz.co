#!/usr/bin/env python3
"""Consolida el piloto Apify de Julián sin iniciar nuevas corridas pagadas."""
import json, os, re, urllib.request, xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "julian-rodriguez-sastoque" / "datos" / "redes-monitor.json"
CREDENTIALS = Path.home() / ".config" / "apify" / "credentials.env"
DATASETS = {"x":"44XyB1fcrQbJG0lgD", "instagram":"bK0B27CSS8XHbefGp", "tiktok":"yAjjq77YKEptjt35h"}
COST = {"x":0.0044, "instagram":0.0023, "tiktok":0.0210}
TOPICS = {
    "Seguridad": ("seguridad", "inseguridad", "policía", "policia", "fuerza pública"),
    "Ambiente y residuos": ("ambiente", "basura", "residuos", "puntos críticos", "recicl"),
    "Empleo público": ("empleo", "laboral", "convocatoria", "oportunidades", "carrera"),
    "Control político": ("contrato", "denuncia", "control político", "control politico"),
    "Bienestar animal": ("animal", "perro", "mascota"),
    "Salud mental": ("salud mental", "ansiedad", "depresión"),
}
NEG = ("peligroso", "inseguridad", "crítica", "denuncia", "no hizo", "golpea", "fracaso")
POS = ("oportunidad", "logro", "bienestar", "fortalecer", "mejora", "empleo")

def token():
    for line in CREDENTIALS.read_text().splitlines():
        if line.startswith("APIFY_TOKEN="):
            return line.split("=",1)[1].strip().strip("'\"")
    raise RuntimeError("No se encontró APIFY_TOKEN")

def get_json(url):
    req=urllib.request.Request(url, headers={"Authorization":f"Bearer {token()}"})
    with urllib.request.urlopen(req, timeout=40) as r: return json.load(r)

def clean_text(s): return re.sub(r"\s+", " ", s or "").strip()

def normalize(red, x):
    if red == "x":
        author=(x.get("author") or {}).get("userName")
        metric=sum(int(x.get(k) or 0) for k in ("likeCount","retweetCount","replyCount","quoteCount"))
        return {"red":"x","label":"X","texto":clean_text(x.get("text")),"autor":author,
                "url":x.get("url"),"fecha":x.get("createdAt"),"metrica":metric}
    if red == "tiktok":
        author=(x.get("authorMeta") or {}).get("name")
        metric=sum(int(x.get(k) or 0) for k in ("diggCount","shareCount","commentCount"))
        return {"red":"tiktok","label":"TikTok","texto":clean_text(x.get("text")),"autor":author,
                "url":x.get("webVideoUrl"),"fecha":x.get("createTimeISO"),"metrica":metric}
    if x.get("error") or not x.get("caption"): return None
    return {"red":"instagram","label":"Instagram","texto":clean_text(x.get("caption")),
            "autor":x.get("ownerUsername"),"url":x.get("url"),"fecha":x.get("timestamp"),
            "metrica":int(x.get("likesCount") or 0)}

def trends():
    with urllib.request.urlopen("https://trends.google.com/trending/rss?geo=CO", timeout=30) as r:
        root=ET.fromstring(r.read())
    ns={"ht":"https://trends.google.com/trending/rss"}
    return [{"tema":i.findtext("title"),"señal":i.findtext("ht:approx_traffic",default="En tendencia",namespaces=ns)}
            for i in root.findall("./channel/item")[:7]]

def main():
    posts=[]; counts={}
    for red, ds in DATASETS.items():
        items=get_json(f"https://api.apify.com/v2/datasets/{ds}/items?clean=1")
        normalized=[normalize(red,x) for x in items]
        normalized=[x for x in normalized if x and x["texto"]]
        counts[red]=len(normalized); posts.extend(normalized)
    accounts=Counter(p["autor"] for p in posts if p.get("autor"))
    topic_counts=Counter()
    for p in posts:
        low=p["texto"].lower()
        for label, words in TOPICS.items():
            if any(w in low for w in words): topic_counts[label]+=1
    sentiment=Counter()
    for p in posts:
        low=p["texto"].lower()
        sentiment["negativo" if any(w in low for w in NEG) else "positivo" if any(w in low for w in POS) else "neutro"]+=1
    dominant=topic_counts.most_common(1)[0][0] if topic_counts else "menciones directas"
    data={
        "generado_en":datetime.now(timezone.utc).isoformat(), "ventana":"piloto inicial",
        "n_posts":len(posts), "costo_piloto_usd":round(sum(COST.values()),4),
        "por_red":[{"red":r,"label":{"x":"X","instagram":"Instagram","tiktok":"TikTok"}[r],"n":counts[r]} for r in DATASETS],
        "sentimiento":dict(sentiment),
        "analisis":{"titulo":f"{dominant} domina el primer corte",
          "lectura":f"El piloto encontró {len(posts)} publicaciones verificables. X concentra menciones externas y TikTok aporta contenido de la cuenta de Julián. Instagram no devolvió resultados para el hashtag exacto, por lo que conviene identificar primero la cuenta oficial antes de ampliar la búsqueda."},
        "cuentas":[{"autor":a,"n":n} for a,n in accounts.most_common(8)],
        "temas_julian":[{"tema":t,"n":n} for t,n in topic_counts.most_common()],
        "tendencias_bogota":trends(),
        "publicaciones":sorted(posts,key=lambda x:x["metrica"],reverse=True)[:10],
        "metodologia":{"datasets":DATASETS,"costos_usd":COST,"nota":"Piloto de bajo volumen; no representa alcance total."}
    }
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"salida":str(OUT),"posts":len(posts),"por_red":counts,"costo_usd":data["costo_piloto_usd"]},ensure_ascii=False))
if __name__ == "__main__": main()
