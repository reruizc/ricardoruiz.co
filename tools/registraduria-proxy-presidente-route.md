# Worker `registraduria-proxy` · ruta `/presidente` (CONFIRMADO 2026-05-31)

El worker `registraduria-proxy.reruizc.workers.dev` proxea (con CORS) los JSON
de la Registraduría. `presidencial-prec-2026.html` consume `/presidente`.

## Verificado en vivo (conteo abierto)

- **Endpoint real:** `https://resultados.registraduria.gov.co/json/ACT/PR/00.json`
  (corp `PR` = presidente · `00` = nacional · `{cod}` = depto). **HTTP 200, datos OK.**
- **El JSON NO trae CORS** → el navegador no puede leerlo directo: hace falta el worker.
- **Los proxies CORS públicos no sirven** (corsproxy.io devuelve su propia HTML;
  allorigins da timeout). El worker propio es el único camino.
- ⚠️ **CLAVE — el WAF exige un User-Agent de navegador COMPLETO.** Un
  `Mozilla/5.0` mínimo, `curl`, o sin UA → **403**. Un UA de Chrome completo → **200**.
  (Por eso el worker daba 403 antes: no mandaba UA de navegador.)

| Ruta worker        | CORP | URL real                                   |
|--------------------|------|--------------------------------------------|
| `/senado`          | `SE` | `…/json/ACT/SE/00.json`                    |
| `/camara`          | `CA` | `…/json/ACT/CA/00.json`                    |
| `/consultas`       | `CN` | `…/json/ACT/CN/00.json`                    |
| **`/presidente`**  | **`PR`** | **`…/json/ACT/PR/00.json`**            |
| `/presidente/{cod}`| `PR` | `…/json/ACT/PR/{cod}.json`                 |

## Desplegar (1 comando)

Worker completo y listo en **`tools/registraduria-proxy/`** (`worker.js` +
`wrangler.toml`, ya con la ruta `/presidente` y el UA de Chrome correcto):

```bash
cd tools/registraduria-proxy && npx wrangler deploy
```

Es un proxy sin estado (sin KV). Se despliega como `registraduria-proxy`, o sea
reemplaza el worker actual en `registraduria-proxy.reruizc.workers.dev` con las
4 rutas (senado/camara/consultas/presidente) y el UA que pasa el WAF.

> Si tienes el código original del worker en otro lado y prefieres no
> reemplazarlo: solo agrega `presidente: 'PR'` al mapa de corporaciones **y
> asegúrate de que el `fetch` upstream mande el User-Agent de Chrome completo**
> (ver `worker.js`). Sin ese UA, sigue dando 403.

## Verificar tras desplegar

```bash
curl -s "https://registraduria-proxy.reruizc.workers.dev/presidente" | head -c 200
# Debe traer JSON: {"elec":"1","amb":"00",...,"camaras":[...],...}
```

Luego en `presidencial-prec-2026.html`: modo **Worker propio** → «Cargar ahora»
o Auto-refresh. Si da 404 «Ruta no encontrada», el deploy no tomó la ruta.

## Forma del JSON (para referencia)

```jsonc
{
  "elec":"1", "amb":"00",
  "totales": { "act": { "metota":"122020", "mesesc":"0", "centota":"41421973",
                        "votant", "votval", "votnul", "votnma", "votblan", ... } },
  "camaras": [ { "partotabla": [
    { "act": { "codpar":"7", "vot":"0",
               "cantotabla":[ { "nomcan":"IVÁN", "apecan":"CEPEDA CASTRO",
                                "nomcan2":"AIDA MARINA", "apecan2":"QUILCUE..." } ] } },
    ... 13 candidatos ...
  ] } ]
}
```

13 candidatos oficiales 1V (codpar → nombre): 7 Cepeda · 2 Paloma Valencia ·
3 Fajardo · 4 Miguel Uribe Londoño · 5 Matamoros · 6 Roy Barreras · 8 Botero ·
9 Sondra Macollins · 10 Abelardo De la Espriella · 11 Claudia López ·
12 Luis G. Murillo · 13 Carlos Caicedo · 14 Óscar Lizcano. El nombre del partido
no viene en el JSON (`nompar` ausente); se mapea por codpar en `PARTIDO_PRES`
dentro del HTML.
