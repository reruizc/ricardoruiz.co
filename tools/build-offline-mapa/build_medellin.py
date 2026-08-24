#!/usr/bin/env python3
"""Empaqueta medellin-1v-barrios.html como un .html autocontenido (offline).
Incrusta Leaflet (JS+CSS), el GeoJSON de barrios y las fuentes. Sin red.
"""
import re, base64, pathlib

REPO = pathlib.Path("/Users/ricardoruiz/ricardoruiz.co")
TMP  = pathlib.Path("/tmp")
SRC  = REPO / "medellin-1v-barrios.html"
OUTDIR = REPO / "Bases de datos" / "entregables-offline"
OUTDIR.mkdir(parents=True, exist_ok=True)
OUT  = OUTDIR / "medellin-1v-barrios-OFFLINE.html"

html = SRC.read_text(encoding="utf-8")
leaflet_css = (TMP/"leaflet.css").read_text(encoding="utf-8")
leaflet_js  = (TMP/"leaflet.js").read_text(encoding="utf-8")
fonts_css   = (TMP/"fonts_inline.css").read_text(encoding="utf-8")
geojson     = (TMP/"mde_geo.json").read_text(encoding="utf-8").strip()

# 1) Reescribir links relativos .html -> absolutos ricardoruiz.co (antes de inyectar libs)
html = re.sub(r'href="(?!https?://)([\w./-]+\.html)"',
              r'href="https://ricardoruiz.co/\1"', html)

# 2) Fuentes Google -> @font-face base64 inline (reemplaza preconnect + link)
html = html.replace(
  '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
  '<!-- fuentes incrustadas (offline) -->')
html = re.sub(r'<link href="https://fonts\.googleapis\.com/css2[^"]*" rel="stylesheet">',
              f'<style>\n{fonts_css}\n</style>', html)

# 3) Leaflet CSS -> inline
html = html.replace(
  '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">',
  f'<style>/* Leaflet 1.9.4 */\n{leaflet_css}\n</style>')

# 4) Leaflet JS -> inline
html = html.replace(
  '<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>',
  f'<script>/* Leaflet 1.9.4 */\n{leaflet_js}\n</script>')

# 5) GeoJSON -> const GEO inline; fetch -> Promise.resolve
html = re.sub(r"const GEO_URL='https://[^']+';",
              "const GEO=" + geojson + ";", html, count=1)
html = html.replace(
  "fetch(GEO_URL).then(r=>r.json()).then(geo=>{",
  "Promise.resolve(GEO).then(geo=>{")

# 6) Bloque de descargas (toca red/auth) -> nota estatica offline
dl_pat = re.compile(r"// descargas: gratis para usuarios registrados\n\(async function\(\)\{.*?\}\)\(\);",
                    re.DOTALL)
dl_new = ("// version offline: sin red; mensaje estatico\n"
  "(function(){var el=document.getElementById('dl-body'); if(el) el.innerHTML="
  "'El preconteo de 1\\u00aa vuelta <b>completo, mesa a mesa, de todo el pa\\u00eds</b> "
  "(121.863 mesas \\u00b7 los 13 candidatos con votaci\\u00f3n bruta por mesa, en Excel y CSV) "
  "est\\u00e1 disponible para usuarios registrados en "
  "<a href=\"https://ricardoruiz.co/medellin-1v-barrios.html\">ricardoruiz.co/medellin-1v-barrios.html</a> "
  "(requiere conexi\\u00f3n).';})();")
html, n = dl_pat.subn(lambda m: dl_new, html)
assert n == 1, f"download IIFE replace count = {n}"

# Sello discreto en el tag de descargas
html = html.replace('<span class="tag">REGISTRADOS</span>',
                    '<span class="tag">COPIA OFFLINE</span>')

OUT.write_text(html, encoding="utf-8")
kb = OUT.stat().st_size/1024
print(f"OK -> {OUT}")
print(f"Tamano: {kb:.0f} KB ({kb/1024:.2f} MB)")

# Verificaciones: 0 referencias de red criticas restantes
crit = re.findall(r'(cdnjs\.cloudflare|fonts\.googleapis|fonts\.gstatic|amazonaws|GEO_URL)', html)
print("Referencias criticas restantes (debe ser 0):", len(crit), set(crit))
print("Contiene 'L.map(' :", 'L.map(' in html, " | 'const GEO=' :", 'const GEO=' in html)
