# Caudal · setup del bucket privado `caudal-legislativo`

Módulo **Caudal** de Cauce (histórico legislativo). El bucket es **privado**
(sin política pública, Block Public Access ON). `ricardo-mac-cli` está scoped
solo a `elecciones-2026`, así que la creación va con credenciales de admin.

## 1. Crear el bucket (privado) — corre TÚ con admin

```bash
# bucket en us-east-1
aws s3api create-bucket --bucket caudal-legislativo --region us-east-1

# blindar contra exposición pública accidental (por defecto ya viene ON en
# buckets nuevos, pero lo dejamos explícito)
aws s3api put-public-access-block --bucket caudal-legislativo \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# cifrado en reposo por defecto (AES256)
aws s3api put-bucket-encryption --bucket caudal-legislativo \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
```

## 2. Dar acceso a `ricardo-mac-cli` (para que Claude suba el dataset)

```bash
# crea la política gestionada desde el JSON del repo
aws iam create-policy --policy-name caudal-legislativo-rw \
  --policy-document file://tools/caudal/iam-caudal-rw.json

# adjúntala al usuario CLI (reemplaza <ACCOUNT_ID> = 167386641785)
aws iam attach-user-policy --user-name ricardo-mac-cli \
  --policy-arn arn:aws:iam::167386641785:policy/caudal-legislativo-rw
```

## 3. Subir el dataset — lo corre Claude una vez el acceso esté listo

```bash
B="s3://caudal-legislativo/metadata"
D="Bases de datos/leyes-senado/dist"
aws s3 cp "$D/proyectos.jsonl" "$B/proyectos.jsonl" --content-type application/x-ndjson
aws s3 cp "$D/leyes.jsonl"     "$B/leyes.jsonl"     --content-type application/x-ndjson
aws s3 cp "$D/indice.json"     "$B/indice.json"     --content-type application/json
aws s3 cp "$D/stats.json"      "$B/stats.json"      --content-type application/json
# opcional: respaldo del crudo sin enriquecer
aws s3 cp "Bases de datos/leyes-senado/pdly.jsonl" "s3://caudal-legislativo/raw/pdly.jsonl"
```

## Estructura de llaves dentro del bucket

```
caudal-legislativo/
  metadata/proyectos.jsonl     ← pdly enriquecido (backend/Lambda)
  metadata/leyes.jsonl         ← lys enriquecido
  metadata/indice.json         ← índice compacto (búsqueda en memoria)
  metadata/stats.json          ← embudo + agregados precalculados
  raw/*.jsonl                   ← respaldo del crudo del harvester (opcional)
  gacetas/{num}-{año}.pdf       ← cache de PDFs (fase 3, bajo demanda)
  gacetas-texto/{num}-{año}.txt ← texto extraído (pypdf/OCR)
  analisis-cache/{hash}.json    ← salida DeepSeek cacheada (fase 3)
```

## Nota
NO adjuntar ninguna bucket policy pública a `caudal-legislativo`. El acceso es
solo vía IAM (Claude/CLI para escribir, y la futura Lambda con su propio role
para leer). El frontend NO lee este bucket directo — habla con la Lambda.
