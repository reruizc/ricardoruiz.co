#!/usr/bin/env python3
"""
Cortesía de prueba de Candidato 360 · una cuenta a la vez.

La prueba que se anuncia por correo (nov-2026) es a pedido: quien responde,
recibe 7 días de acceso SIN escucha de redes (cada lectura cuesta plata en
Apify). Escribe la misma llave que /c360/acceso/save del worker rr-auth
(`c360:acceso:<correo>`, mismo formato) con wrangler, así que no hace falta
la sesión de administración en el navegador.

    python3 tools/candidato-360/cortesia.py persona@correo.com          # 7 días
    python3 tools/candidato-360/cortesia.py persona@correo.com --dias 14
    python3 tools/candidato-360/cortesia.py persona@correo.com --ver    # solo lee

⚠️ No escribir correos en este repo (es público): el correo va por argumento.
⚠️ Si la cuenta ya tenía un acceso, se conservan su nota, quién lo otorgó y sus
   módulos (igual que el worker): renovar no le quita la escucha a nadie.
⚠️ La persona tiene que registrarse en ricardoruiz.co con ESE correo; la
   cortesía no crea la cuenta. Al vencer, la portada y los paneles le dicen la
   fecha en que terminó (fuente «vencido» de /c360/me).
"""
import argparse, datetime, json, os, subprocess, sys

NS = "beb24dcb24c74a7399af71870a165c83"           # RR_STORE (rr-auth/wrangler.jsonc)
RR_AUTH = "/Users/ricardoruiz/rr-auth"
OTORGA = "reruizc@gmail.com"


def wr(*args, entrada=None):
    r = subprocess.run(["npx", "wrangler", "kv", "key", *args, "--namespace-id", NS, "--remote"],
                       cwd=RR_AUTH, capture_output=True, text=True, input=entrada)
    return r


def leer(llave):
    r = wr("get", llave)
    txt = (r.stdout or "").strip()
    # wrangler escribe el 404 en la salida normal: no basta con que haya texto
    try:
        return json.loads(txt)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("correo")
    ap.add_argument("--dias", type=int, default=7)
    ap.add_argument("--nota", default="prueba por correo de novedades nov-2026")
    ap.add_argument("--ver", action="store_true")
    a = ap.parse_args()

    correo = a.correo.strip().lower()
    if "@" not in correo or " " in correo:
        sys.exit("correo inválido")
    llave = f"c360:acceso:{correo}"
    previo = leer(llave)
    if a.ver:
        print(json.dumps(previo, ensure_ascii=False, indent=2) if previo else "sin acceso otorgado")
        return
    if not 1 <= a.dias <= 366:
        sys.exit("--dias entre 1 y 366")

    ahora = datetime.datetime.now(datetime.timezone.utc)
    iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%S.") + f"{d.microsecond // 1000:03d}Z"
    reg = {
        "email": correo,
        "nota": (a.nota if not previo else previo.get("nota") or a.nota)[:240],
        "otorgadoPor": (previo or {}).get("otorgadoPor") or OTORGA,
        "otorgadoEn": (previo or {}).get("otorgadoEn") or iso(ahora),
        "renovadoPor": OTORGA if previo else None,
        "actualizadoEn": iso(ahora),
        "expiraEn": iso(ahora + datetime.timedelta(days=a.dias)),
        "modulos": (previo or {}).get("modulos") or [],
    }
    r = wr("put", llave, json.dumps(reg, ensure_ascii=False))
    if r.returncode != 0:
        sys.exit(f"wrangler falló: {r.stderr.strip()[-300:]}")
    escrito = leer(llave)
    if not escrito or escrito.get("expiraEn") != reg["expiraEn"]:
        sys.exit("se escribió pero no se pudo releer igual: revisar a mano")
    vence = datetime.datetime.fromisoformat(reg["expiraEn"].replace("Z", "+00:00")) - datetime.timedelta(hours=5)
    print(f"✓ {correo}: acceso a Candidato 360 hasta el {vence:%d-%m-%Y %H:%M} (hora de Colombia)"
          f"{' · renovado' if previo else ''} · módulos: {', '.join(reg['modulos']) or 'ninguno (sin escucha)'}")


if __name__ == "__main__":
    main()
