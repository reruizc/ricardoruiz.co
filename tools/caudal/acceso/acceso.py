#!/usr/bin/env python3
"""Otorgar, listar y revocar acceso a Caudal — sin tocar código.

El gate de `caudal.html` nació como una lista de correos escrita a mano DENTRO
del HTML: abrirle Caudal a un cliente exigía editar el archivo y hacer push.
Cauce trae los clientes, así que eso pasa a ser semanal. Este CLI habla con el
worker `rr-auth`, que guarda la lista en KV (`caudal:acceso:<correo>`), así que
otorgar y revocar es inmediato y no redespliega nada.

NO es autoservicio: el modelo comercial es aprovisionamiento manual de cuentas
ya habladas. Por eso todo esto exige credenciales de admin.

    python3 tools/caudal/acceso/acceso.py listar
    python3 tools/caudal/acceso/acceso.py otorgar diego@cauce.co --nota "Cauce · piloto"
    python3 tools/caudal/acceso/acceso.py otorgar juan@gremio.co --dias 90 --nota "Prueba 3 meses"
    python3 tools/caudal/acceso/acceso.py ver diego@cauce.co
    python3 tools/caudal/acceso/acceso.py revocar diego@cauce.co

Credenciales, en orden de preferencia (ver README.md de esta carpeta):
  1. RR_ADMIN_API_KEY en el entorno o en ~/.config/caudal/acceso.env
     → cabecera X-Admin-Api-Key, sin sesión de por medio (ideal para scripts).
  2. Sesión de admin: pide la contraseña una vez y cachea el token en
     ~/.config/caudal/acceso-session.json (chmod 600, FUERA del repo).

El cliente al que se le abre la puerta necesita **cuenta en ricardoruiz.co**
(register.html): esto autoriza un correo, no lo crea.

Se usa curl por subprocess —igual que el resto de los harvesters del proyecto—
para esquivar el TLS de python 3.14 sin depender de certifi.
"""

import argparse
import getpass
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

API = os.environ.get("RR_AUTH_API", "https://rr-auth.reruizc.workers.dev")
CONFIG_DIR = os.path.expanduser("~/.config/caudal")
ENV_FILE = os.path.join(CONFIG_DIR, "acceso.env")
SESSION_FILE = os.path.join(CONFIG_DIR, "acceso-session.json")
ADMIN_EMAIL_DEFAULT = "reruizc@gmail.com"
CURL = "/usr/bin/curl"          # el del sistema, no el del PATH
TIMEOUT = 30


# ─────────────────────────────── HTTP ────────────────────────────────────────

class ApiError(RuntimeError):
    def __init__(self, msg, status=None, unauthorized=False):
        super().__init__(msg)
        self.status = status
        self.unauthorized = unauthorized


def _curl(method, path, headers=None, body=None):
    """Devuelve (status, json|None). Nunca lanza por status HTTP."""
    cmd = [CURL, "-sS", "-X", method, f"{API}{path}",
           "-m", str(TIMEOUT), "-w", "\n%{http_code}"]
    for k, v in (headers or {}).items():
        cmd += ["-H", f"{k}: {v}"]
    if body is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(body)]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT + 10)
    except subprocess.TimeoutExpired:
        raise ApiError(f"timeout hablando con {API}")
    if out.returncode != 0:
        raise ApiError(f"curl falló: {(out.stderr or '').strip()}")
    raw = out.stdout.rsplit("\n", 1)
    status = int(raw[-1].strip() or 0)
    data = None
    if len(raw) > 1 and raw[0].strip():
        try:
            data = json.loads(raw[0])
        except json.JSONDecodeError:
            pass
    return status, data


def _read_env_file():
    """Lee ~/.config/caudal/acceso.env (KEY=valor, # comentarios)."""
    vals = {}
    if not os.path.exists(ENV_FILE):
        return vals
    with open(ENV_FILE, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals


class Auth:
    """Resuelve las cabeceras de admin: api-key si hay, si no sesión cacheada."""

    def __init__(self, email=None):
        self.email = email or ADMIN_EMAIL_DEFAULT
        env = _read_env_file()
        self.api_key = (os.environ.get("RR_ADMIN_API_KEY")
                        or env.get("RR_ADMIN_API_KEY") or "").strip()
        self._token = None

    @property
    def modo(self):
        return "api-key" if self.api_key else "sesión"

    def headers(self):
        if self.api_key:
            return {"X-Admin-Api-Key": self.api_key}
        return {"Authorization": f"Bearer {self._session_token()}"}

    def _session_token(self):
        if self._token:
            return self._token
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, encoding="utf-8") as fh:
                    cached = json.load(fh)
                if cached.get("token") and cached.get("email") == self.email:
                    self._token = cached["token"]
                    return self._token
            except (OSError, json.JSONDecodeError):
                pass
        return self._login()

    def _login(self):
        print(f"Sesión de admin para {self.email}", file=sys.stderr)
        password = getpass.getpass("Contraseña: ")
        status, data = _curl("POST", "/auth/login",
                             body={"email": self.email, "password": password})
        if status != 200 or not (data or {}).get("token"):
            raise ApiError((data or {}).get("error") or f"login falló (HTTP {status})", status)
        self._token = data["token"]
        os.makedirs(CONFIG_DIR, exist_ok=True)
        # La contraseña no se guarda nunca; el token sí, con permisos de dueño.
        fd = os.open(SESSION_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"email": self.email, "token": self._token,
                       "guardadoEn": datetime.now(timezone.utc).isoformat()}, fh)
        return self._token

    def invalidar_sesion(self):
        self._token = None
        try:
            os.remove(SESSION_FILE)
        except OSError:
            pass

    def call(self, method, path, body=None, _reintento=False):
        status, data = _curl(method, path, headers=self.headers(), body=body)
        if status in (401, 403):
            # Con sesión cacheada vencida vale reintentar una vez pidiendo
            # contraseña; con api-key mala, reintentar solo repite el error.
            if not self.api_key and not _reintento:
                self.invalidar_sesion()
                return self.call(method, path, body, _reintento=True)
            raise ApiError((data or {}).get("error") or "no autorizado",
                           status, unauthorized=True)
        if status != 200 or not (data or {}).get("ok"):
            raise ApiError((data or {}).get("error") or f"HTTP {status}", status)
        return data


# ────────────────────────────── formato ──────────────────────────────────────

def _fecha(iso):
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return iso[:10]


def _vence(reg):
    if not reg.get("expiraEn"):
        return "sin vencimiento"
    dias = (datetime.fromisoformat(reg["expiraEn"].replace("Z", "+00:00"))
            - datetime.now(timezone.utc)).days
    if dias < 0:
        return f"VENCIDO ({_fecha(reg['expiraEn'])})"
    return f"vence {_fecha(reg['expiraEn'])} ({dias}d)"


# ────────────────────────────── comandos ─────────────────────────────────────

def cmd_listar(auth, args):
    data = auth.call("GET", "/caudal/acceso/list")
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    accesos, res = data.get("accesos", []), data.get("resumen", {})
    print(f"\nAcceso a Caudal · {res.get('vigentes', 0)} vigentes"
          f" de {res.get('total', 0)}"
          + (f" · {res['vencidos']} vencidos" if res.get("vencidos") else ""))
    if not accesos:
        print("  (ninguna cuenta otorgada todavía)")
    for a in accesos:
        marca = " " if a.get("vigente") else "✗"
        print(f"  {marca} {a['email']:<38} {_vence(a):<28} {a.get('nota') or ''}")
        print(f"     otorgado {_fecha(a.get('otorgadoEn'))}"
              f" por {a.get('otorgadoPor') or '—'}")
    # Los admins entran sin llave en KV: sin decirlo, la lista parecería el
    # universo completo de quién puede abrir Caudal.
    if data.get("admins"):
        print(f"\n  Admins (acceso permanente, no revocable acá): "
              f"{', '.join(data['admins'])}")
    print()
    return 0


def cmd_otorgar(auth, args):
    body = {"email": args.email}
    if args.nota:
        body["nota"] = args.nota
    if args.dias:
        body["dias"] = args.dias
    data = auth.call("POST", "/caudal/acceso/save", body=body)
    reg = data["acceso"]
    verbo = "renovado" if data.get("renovado") else "otorgado"
    print(f"✓ Acceso {verbo}: {reg['email']} · {_vence(reg)}")
    if reg.get("nota"):
        print(f"  nota: {reg['nota']}")
    print("  Necesita cuenta en ricardoruiz.co (register.html) para entrar;\n"
          "  esto autoriza el correo, no crea el usuario.")
    return 0


def cmd_revocar(auth, args):
    data = auth.call("DELETE", f"/caudal/acceso/delete?email={args.email}")
    if data.get("existia"):
        print(f"✓ Acceso revocado: {data['email']}")
    else:
        print(f"· {data['email']} no tenía acceso otorgado (nada que revocar)")
    return 0


def cmd_ver(auth, args):
    correo = args.email.strip().lower()
    data = auth.call("GET", "/caudal/acceso/list")
    if correo in {a.lower() for a in data.get("admins", [])}:
        print(f"{correo}: ACCESO (admin, permanente)")
        return 0
    for a in data.get("accesos", []):
        if a["email"].lower() == correo:
            estado = "ACCESO" if a.get("vigente") else "SIN ACCESO (vencido)"
            print(f"{correo}: {estado} · {_vence(a)}")
            print(f"  nota: {a.get('nota') or '—'}")
            print(f"  otorgado {_fecha(a.get('otorgadoEn'))} por {a.get('otorgadoPor') or '—'}")
            return 0
    print(f"{correo}: SIN ACCESO (no está en la lista)")
    return 1


def main():
    p = argparse.ArgumentParser(
        description="Acceso a Caudal por cuenta (aprovisionamiento manual).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Credenciales")[0].strip())
    p.add_argument("--admin-email", default=ADMIN_EMAIL_DEFAULT,
                   help="correo de admin para la sesión (default: %(default)s)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("listar", help="quién tiene acceso hoy")
    s.add_argument("--json", action="store_true", help="salida cruda")
    s.set_defaults(fn=cmd_listar)

    s = sub.add_parser("otorgar", help="abrirle Caudal a un correo")
    s.add_argument("email")
    s.add_argument("--nota", default="", help="para qué / de quién es (ej: 'Cauce · Asobancaria')")
    s.add_argument("--dias", type=int, help="vencimiento en días (sin esto, no vence)")
    s.set_defaults(fn=cmd_otorgar)

    s = sub.add_parser("revocar", help="quitarle el acceso a un correo")
    s.add_argument("email")
    s.set_defaults(fn=cmd_revocar)

    s = sub.add_parser("ver", help="estado de un correo")
    s.add_argument("email")
    s.set_defaults(fn=cmd_ver)

    args = p.parse_args()
    auth = Auth(args.admin_email)
    try:
        return args.fn(auth, args)
    except ApiError as e:
        print(f"✗ {e}", file=sys.stderr)
        if e.unauthorized and auth.modo == "api-key":
            print("  (RR_ADMIN_API_KEY no coincide con el secreto del worker)", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
