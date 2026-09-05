#!/usr/bin/env python3
"""Mesa de control del torneo FIFA.

Sirve el repo en http://localhost:8768 (abrir /torneo-fifa.html) y, cada vez que
la página manda un marcador, escribe `Bases de datos/torneo-fifa/resultados.json`
y lo sube a S3 con la CLI (prefijo público congreso-2026/output/). Los celulares
abren ricardoruiz.co/torneo-fifa.html y leen ese JSON cada 15 s.

Correr:  python3 tools/torneo-fifa/servidor.py
"""
import json, os, subprocess, sys, threading, time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
LOCAL = os.path.join(RAIZ, 'Bases de datos', 'torneo-fifa', 'resultados.json')
S3 = 's3://elecciones-2026/ricardoruiz.co/congreso-2026/output/torneo-fifa/resultados.json'
PUERTO = 8768
_lock = threading.Lock()

def subir():
    r = subprocess.run(['aws', 's3', 'cp', LOCAL, S3, '--content-type', 'application/json',
                        '--cache-control', 'no-cache, max-age=0'], capture_output=True, text=True)
    return r.returncode == 0, (r.stderr or r.stdout).strip()

class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=RAIZ, **k)
    def log_message(self, f, *a):
        if '/publicar' in (a[0] if a else ''): sys.stderr.write(f"{time.strftime('%H:%M:%S')} {a[0]}\n")
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store'); super().end_headers()
    def do_POST(self):
        if self.path != '/publicar': self.send_error(404); return
        n = int(self.headers.get('Content-Length', 0)); cuerpo = self.rfile.read(n)
        try: datos = json.loads(cuerpo)
        except Exception: return self._json({'ok': False, 'error': 'JSON inválido'}, 400)
        with _lock:
            os.makedirs(os.path.dirname(LOCAL), exist_ok=True)
            with open(LOCAL, 'w', encoding='utf-8') as f: json.dump(datos, f, ensure_ascii=False)
            ok, msg = subir()
        sys.stderr.write(f"{time.strftime('%H:%M:%S')} publicado {'OK' if ok else 'FALLÓ: '+msg}\n")
        self._json({'ok': ok, 'error': None if ok else msg})
    def _json(self, obj, code=200):
        b = json.dumps(obj).encode(); self.send_response(code)
        self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(b)))
        self.end_headers(); self.wfile.write(b)

if __name__ == '__main__':
    print(f"Mesa de control → http://localhost:{PUERTO}/torneo-fifa.html   (Ctrl+C para parar)")
    ThreadingHTTPServer(('127.0.0.1', PUERTO), H).serve_forever()
