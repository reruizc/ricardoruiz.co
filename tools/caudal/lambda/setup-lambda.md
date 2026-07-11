# Caudal · Lambda `caudal-analiza` — deploy y operación

Inteligencia legislativa de Cauce sobre el bucket privado `caudal-legislativo`.
**Desplegada y funcional** (2026-07-11). Los endpoints de datos ya corren; la
síntesis LLM se enciende al setear `DEEPSEEK_API_KEY`.

## Estado actual (desplegado)

- **Función:** `caudal-analiza` · runtime python3.13 · rol `lambda-caudal-analiza`
  (AWSLambdaBasicExecutionRole + inline `caudal-s3` → lee `metadata/*`, r/w
  `analisis-cache/*` y `gacetas*`). Timeout 60s · 512 MB.
- **API pública (HTTP API):** `POST https://l3kmprdjkl.execute-api.us-east-1.amazonaws.com`
  (id `l3kmprdjkl`, ruta `$default`, CORS `*`). Permiso de invocación de
  API Gateway agregado a mano (el `--target` no lo puso solo).
- **Modelo por paso (switch sin código, vía env vars):**
  `CAUDAL_SINTESIS_PROVIDER` (deepseek|anthropic) · `CAUDAL_SINTESIS_MODEL`.
  Default DeepSeek V4 Flash. Para pasar la síntesis a Claude:
  `CAUDAL_SINTESIS_PROVIDER=anthropic` + `CAUDAL_SINTESIS_MODEL=claude-sonnet-5`
  + setear `ANTHROPIC_API_KEY`.

## ⚠️ Pendiente del usuario: setear `DEEPSEEK_API_KEY`

Claude no toca API keys en texto plano. Los endpoints de datos (`buscar`,
`tema` con `lectura:false`, `proyecto`) YA funcionan sin la key. La `lectura`
(síntesis) la necesita. Setéala tú (la key nunca entra al chat):

```bash
# desde tu terminal (copia el valor de una Lambda existente, p.ej. test-presidencial-explica)
aws lambda update-function-configuration --function-name caudal-analiza \
  --environment "Variables={DEEPSEEK_API_KEY=TU_KEY_AQUI}"
```

O por consola: Lambda → caudal-analiza → Configuration → Environment variables.

## Endpoints (POST JSON al endpoint)

```jsonc
// 1) análisis de tema (embudo + supervivencia + autores + lectura LLM)
{"action":"tema","query":"feminicidio","lectura":true}
// 2) lista cruda del índice
{"action":"buscar","query":"agua","limit":25,"anio_min":2010}
// 3) ficha de un proyecto + punteros de gaceta
{"action":"proyecto","id":4177}
```

## Actualizar el código

```bash
python3 tools/caudal/lambda/build_zip.py   # empaqueta handler + caudal_core canónico
aws lambda update-function-code --function-name caudal-analiza \
  --zip-file fileb://tools/caudal/lambda/caudal-analiza.zip
```

## Cómo se creó (reproducible)

```bash
# rol (admin)
aws iam create-role --role-name lambda-caudal-analiza \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam attach-role-policy --role-name lambda-caudal-analiza \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam put-role-policy --role-name lambda-caudal-analiza --policy-name caudal-s3 \
  --policy-document file://tools/caudal/lambda/iam-lambda-caudal.json
# función
python3 tools/caudal/lambda/build_zip.py
aws lambda create-function --function-name caudal-analiza --runtime python3.13 \
  --role arn:aws:iam::167386641785:role/lambda-caudal-analiza \
  --handler lambda_handler.handler --zip-file fileb://tools/caudal/lambda/caudal-analiza.zip \
  --timeout 60 --memory-size 512 --architectures x86_64
# api gateway
aws apigatewayv2 create-api --name caudal-analiza --protocol-type HTTP \
  --target arn:aws:lambda:us-east-1:167386641785:function:caudal-analiza \
  --cors-configuration AllowOrigins="*",AllowMethods="POST,OPTIONS",AllowHeaders="content-type"
# ⚠️ el --target NO agrega el permiso de invocación — hay que ponerlo a mano:
aws lambda add-permission --function-name caudal-analiza --statement-id apigw-invoke \
  --action lambda:InvokeFunction --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:167386641785:<API_ID>/*/*"
```

## Notas

- El motor (`caudal_core.py`) es el CANÓNICO de `tools/caudal/`; `build_zip.py`
  lo toma de ahí (sin drift). El handler inyecta el índice/registros desde S3
  (no usa `from_local`).
- Cache de síntesis en `s3://caudal-legislativo/analisis-cache/{hash24}.json`.
  Bumpear `PROMPT_VERSION` en el handler para invalidar.
- La fase 3 (bajar gacetas de la Imprenta → texto → LLM extrae ponentes/
  argumentos) reusa el paso `extraccion` de `STEP_MODELS`.
