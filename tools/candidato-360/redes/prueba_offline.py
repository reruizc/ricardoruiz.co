#!/usr/bin/env python3
"""prueba_offline.py — la Lambda sin red ni DeepSeek.

Lo que se comprueba es lo que puede hacer daño: que un veredicto del modelo
NUNCA pueda contradecir el sondeo. Si X no contestó, «confirmado» no puede
quedar en pantalla; si TikTok dijo que la cuenta no existe, tampoco. El resto
(normalizar el usuario, no repetir redes, no pasar de tres) es higiene.

    python3 tools/candidato-360/redes/prueba_offline.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DEEPSEEK_API_KEY", "prueba")
import lambda_handler as L  # noqa: E402

fallos = []


def revisar(titulo, ok):
    print(("✓ " if ok else "✗ ") + titulo)
    if not ok:
        fallos.append(titulo)


# ── 1 · normalización del usuario ──────────────────────────────────────────
revisar("una URL de Instagram queda en handle",
        L._limpiar_handle("https://www.instagram.com/la.profe/?hl=es") == "la.profe")
revisar("el @ se cae", L._limpiar_handle("@Juancho") == "Juancho")
revisar("una URL de X con /status queda en el usuario",
        L._limpiar_handle("x.com/petrogustavo/status/123") == "petrogustavo")

redes = L._leer_redes({"redes": [
    {"red": "x", "handle": "@uno"},
    {"red": "x", "handle": "dos"},                 # red repetida: se ignora
    {"red": "tiktok", "handle": "https://www.tiktok.com/@tres"},
    {"red": "facebook", "handle": "cuatro"},       # red que no ofrecemos
    {"red": "instagram", "handle": "correo@dominio.com"},   # no tiene forma de usuario
]})
revisar("no se repite red ni entra una que no ofrecemos",
        [(r["red"], r["handle"]) for r in redes] == [("x", "uno"), ("tiktok", "tres")])
revisar("la URL del perfil se arma con el dominio de cada red",
        redes[1]["url"] == "https://www.tiktok.com/@tres")


# ── 2 · el sondeo manda sobre el modelo ────────────────────────────────────
sondeos = [
    {"red": "x", "handle": "a", "url": "u", "sondeo": "bloqueado", "existe": None, "nombre_perfil": None},
    {"red": "tiktok", "handle": "b", "url": "u", "sondeo": "no_encontrado", "existe": False, "nombre_perfil": None},
    {"red": "instagram", "handle": "c", "url": "u", "sondeo": "ok", "existe": True, "nombre_perfil": "Ana Ruiz"},
]
# Un modelo desbocado: confirma las tres, incluida una que no existe.
sellado = L._sellar_veredictos(sondeos, {"perfiles": [
    {"red": "x", "veredicto": "confirmado", "confianza": 95, "motivo": "inventado"},
    {"red": "tiktok", "veredicto": "confirmado", "confianza": 99, "motivo": "inventado"},
    {"red": "instagram", "veredicto": "confirmado", "confianza": 90, "motivo": "el nombre coincide"},
]})
porred = {p["red"]: p for p in sellado}
revisar("una red bloqueada nunca queda «confirmada»",
        porred["x"]["veredicto"] == "no_verificable" and porred["x"]["confianza"] == 0)
revisar("una cuenta que no existe nunca queda «confirmada»",
        porred["tiktok"]["veredicto"] == "no_encontrado")
revisar("con sondeo bueno sí se respeta al modelo",
        porred["instagram"]["veredicto"] == "confirmado" and porred["instagram"]["confianza"] == 90)

# Y al revés: el modelo no puede rebajar a «no existe» una cuenta que sí respondió.
sellado = L._sellar_veredictos([sondeos[2]], {"perfiles": [
    {"red": "instagram", "veredicto": "no_encontrado", "confianza": 0, "motivo": ""}]})
revisar("el modelo no puede borrar una cuenta que la red confirmó",
        sellado[0]["veredicto"] == "probable" and sellado[0]["motivo"])

sellado = L._sellar_veredictos([sondeos[2]], {"perfiles": [{"red": "instagram", "veredicto": "🙂"}]})
revisar("un veredicto que no existe cae en «probable»", sellado[0]["veredicto"] == "probable")


# ── 3 · el handler de punta a punta, con la red apagada ────────────────────
L.SONDEOS = {
    "x": lambda h: {"sondeo": "bloqueado", "existe": None, "nombre_perfil": None,
                    "seguidores": None, "verificada": None, "detalle": "HTTP 403"},
    "tiktok": lambda h: {"sondeo": "ok", "existe": True, "nombre_perfil": "Alejandra Palacio",
                         "seguidores": None, "verificada": None, "detalle": "oEmbed"},
    "instagram": lambda h: {"sondeo": "no_encontrado", "existe": False, "nombre_perfil": None,
                            "seguidores": None, "verificada": None, "detalle": "404"},
}
L._noticias = lambda *a, **k: [{"titulo": "La Profe lidera veeduría", "medio": "El Espectador",
                                "fecha": "", "link": "https://x.co/1"}]
L._cache_leer = lambda k: None
L._cache_escribir = lambda k, d: None
pedido = {}


def _falso_deepseek(payload, sondeos_, titulares):
    pedido["user"] = L._user_msg(payload, sondeos_, titulares)
    return {"perfiles": [{"red": s["red"], "veredicto": "confirmado", "confianza": 99,
                          "motivo": "todo bien"} for s in sondeos_],
            "resumen": "resumen", "riesgo_homonimo": "", "alertas": ["a", "b", "c", "d"]}


L._call_deepseek = _falso_deepseek
cuerpo = json.dumps({"nombre": "Alejandra Palacio Restrepo", "alias": "La Profe",
                     "territorio": "Bogotá D.C.", "corp": "Concejo",
                     "redes": [{"red": "x", "handle": "@apalacio"},
                               {"red": "tiktok", "handle": "laprofe"},
                               {"red": "instagram", "handle": "noexiste"}]})
r = json.loads(L.handler({"body": cuerpo, "headers": {}}, None)["body"])
veredictos = {p["red"]: p["veredicto"] for p in r["perfiles"]}
revisar("el handler sella los tres veredictos según el sondeo",
        veredictos == {"x": "no_verificable", "tiktok": "confirmado", "instagram": "no_encontrado"})
revisar("las alertas se cortan en tres", len(r["alertas"]) == 3)
revisar("el prompt le dice al modelo que no pudo comprobarse la de X",
        "no se pudo comprobar" in pedido["user"])
revisar("el prompt no lleva nada que el sondeo no haya dicho",
        "seguidores según la fuente" not in pedido["user"])

sin_nombre = json.loads(L.handler({"body": json.dumps({"nombre": "Al", "redes": []}), "headers": {}}, None)["body"])
revisar("sin nombre no se llama al modelo", sin_nombre.get("error") == "falta_nombre")
sin_redes = json.loads(L.handler({"body": json.dumps({"nombre": "Alejandra Palacio", "redes": []}), "headers": {}}, None)["body"])
revisar("sin redes tampoco", sin_redes.get("error") == "sin_redes")

L.SERVICE_TOKEN = "secreto"
cerrado = L.handler({"body": cuerpo, "headers": {"origin": "https://ricardoruiz.co"}}, None)
revisar("con secreto configurado, sin la cabecera la Lambda no existe", cerrado["statusCode"] == 404)
abierto = L.handler({"body": cuerpo, "headers": {"x-c360-service": "secreto"}}, None)
revisar("con la cabecera correcta sí contesta", abierto["statusCode"] == 200)

print()
print(f"{len(fallos)} prueba(s) fallaron: {', '.join(fallos)}" if fallos else "todas pasaron")
sys.exit(1 if fallos else 0)
