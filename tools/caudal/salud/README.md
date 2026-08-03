# `tools/caudal/salud/` — ¿está vivo Caudal?

Tres archivos, un objetivo: poder responder por el pipeline delante de alguien
que paga.

| archivo | qué hace |
|---|---|
| `catalogo.py` | **la parte opinable**: qué archivo tiene que estar fresco, con qué umbral y por qué; qué acciones de la Lambda tienen que responder y con qué forma |
| `check.py` | aplica el catálogo → escribe `Bases de datos/leyes-senado/diario/estado.json` |
| `etapa.py` | corre UNA etapa del cron con timeout y deja constancia (lo usa `run_diario.sh`) |
| `PLAN-salir-del-mac.md` | evaluación y recomendación para dejar de depender del portátil |

## Uso

```bash
# el chequeo completo (frescura + Lambda) — escribe estado.json
python3 tools/caudal/salud/check.py

# sin pings a terceros (SECOP/Google News) ni lectura de fechas internas
python3 tools/caudal/salud/check.py --rapido

# solo una mitad
python3 tools/caudal/salud/check.py --solo s3
python3 tools/caudal/salud/check.py --solo lambda

# el JSON crudo, sin tocar disco
python3 tools/caudal/salud/check.py --json --sin-escribir
```

Códigos de salida, para no tener que parsear nada:
`0` ok · `1` aviso · `2` error · `3` el chequeo mismo se rompió.

`run_diario.sh` lo llama al final de cada corrida con `--etapas`, y así
`estado.json` queda con las tres capas: **qué corrió**, **qué tan fresco está el
dato** y **si la Lambda responde**.

## Qué chequea, en concreto

**Frescura (24 archivos).** Cada uno con su umbral, no uno global: los cuatro que
refresca el cron avisan a las 26 h (ya se saltó una corrida) y dan error a las
50 h (se saltó un día); la normativa del Ejecutivo, cuya fuente publica una vez
al mes, avisa a los 45 días; el histórico 1990-2026 **no tiene umbral de edad** —
de ese solo se verifica que exista y no llegue truncado (`min_bytes`).

Donde el archivo trae una fecha por dentro (`secop-stats.generado`,
`en-vivo.actualizado`, `ritmo.v`) también se mira esa, porque un `aws s3 cp` de un
archivo viejo se ve fresco por `LastModified` y no lo es. Solo se baja el archivo
para eso si pesa menos de 256 KB.

**Lambda (12 acciones).** No basta con HTTP 200: se valida la **forma** de cada
respuesta. Un 200 con `{}` o con `{"error": ...}` adentro es el modo de falla
peligroso — el frontend lo pinta como "sin resultados" y nadie se entera.

Ningún ping cuesta dinero: `tema` va con `lectura:false` y `expandir_ia:false`,
y las acciones que llaman a DeepSeek (`contexto`, `gaceta`, `cliente` con lectura)
no se pinchan. Los dos pings que dependen de un tercero en vivo (SECOP vía
Socrata, medios vía Google News) van marcados `externa` y su falla es **aviso**,
no error: el pipeline nuestro puede estar impecable y el tercero caído.

## Al tocar el catálogo

- Si agregas un archivo a `metadata/`, agrégalo también a `catalogo.archivos()`
  con su clase. Lo que no está en el catálogo, no se vigila.
- Los `min_bytes` son ~40-50% del tamaño real de ago-2026. Si un archivo crece
  mucho, súbelos; si un archivo legítimamente encoge, bájalos antes de que el
  chequeo grite.
- `legislatura_actual()` calcula el nombre de los `pl-radicados-*` con el corte
  del 20 de julio. Los harvesters todavía traen `2026-2027` hardcodeado como
  default: el 20-jul-2027 el chequeo va a reportar el archivo como FALTANTE, que
  es justo el aviso que hace falta para ir a mover ese default.
