# Proyecto DC · cerrar el acceso público a los datos confidenciales

**Problema:** las páginas de Proyecto DC tenían gate de login solo del lado del
cliente (JS). Los datos propietarios de la socia (Nury) se servían desde un
prefijo S3 **público**, descargables por cualquiera con la URL (que está en el
HTML público del repo). Verificado: el informe de grupos criminales (1.4 MB) daba
`200 OK` sin login.

**Solución:** los datos confidenciales se movieron a un prefijo **privado**
(`dc-privado/`, 403 anónimo). El worker `rr-auth` los sirve con URLs S3 firmadas
de 5 min, solo tras validar sesión + whitelist DC (endpoint `/dc/sign`).

## Estado (hecho automáticamente)

- [x] `dc-privado/` poblado con los 31 objetos confidenciales (pdfs + arquetipos
      + votacion-arquetipo-2027). Verificado 403 anónimo.
- [x] Endpoint `/dc/sign` agregado a `rr-auth/src/index.js` (firmador SigV4 en
      Web Crypto, validado end-to-end: URL firmada → 200, sin firmar → 403).
- [x] Los originales públicos siguen intactos (nada roto todavía).

## Pendiente (requiere admin AWS + deploy — pasos del usuario)

### 1. Crear el usuario IAM de solo-lectura para el worker
Con un **perfil admin** (ricardo-mac-cli NO tiene permisos IAM):

```bash
cd /Users/ricardoruiz/ricardoruiz.co
aws iam create-user --user-name rr-worker-dc-read
aws iam put-user-policy --user-name rr-worker-dc-read \
  --policy-name dc-privado-read \
  --policy-document file://tools/dc-secure/iam-dc-read-policy.json
aws iam create-access-key --user-name rr-worker-dc-read
# ↑ copia AccessKeyId y SecretAccessKey de la salida (no se vuelven a mostrar)
```

La política (`iam-dc-read-policy.json`) da SOLO `s3:GetObject` sobre
`dc-privado/*`. Si esa llave se filtrara del worker, el daño máximo es leer los
datos que los usuarios autorizados ya ven — nada de escritura ni de otros
prefijos.

### 2. Cargar la llave como secretos del worker
```bash
cd /Users/ricardoruiz/rr-auth
npx wrangler secret put DC_S3_ACCESS_KEY_ID      # pega el AccessKeyId
npx wrangler secret put DC_S3_SECRET_ACCESS_KEY  # pega el SecretAccessKey
```

### 3. Desplegar el worker
```bash
cd /Users/ricardoruiz/rr-auth && npx wrangler deploy
```

### 4. Avisar → yo hago el frontend + verifico + borro los originales
Una vez `/dc/sign` esté vivo:
- Repunteo los `fetch()`/`<img>`/`<a>` de arquetipos.html y los enlaces de PDF de
  gobierno-criminal.html / comportamiento-electoral.html hacia el flujo firmado.
- Verifico en navegador que el autorizado carga y el anónimo no.
- Recién ahí **borro** los originales públicos de `Proyecto DC/pdfs`,
  `Proyecto DC/arquetipos`, `Proyecto DC/votacion-arquetipo-2027` (paso
  destructivo, con confirmación).

## Notas
- `output_medellin`, `proyecto-dc/geo`, los GeoJSON de Medellín y el DANE empleo
  se **quedan públicos**: son datos de dominio público, compartidos con páginas
  públicas (veleta/oportunidad/previa). No son el activo confidencial.
- Mismo patrón replicable después para Risaralda y los demás módulos gated.
