# Deploy de `proyecto-dc-escenarios-estrategia`

Lambda nueva + API Gateway nuevo para el botón **"Recomendar estrategia"** del módulo 08 de Proyecto DC.

Patrón clonado de `test-presidencial-explica` que ya tienes en prod: stdlib pura, sin Layer, boto3 viene en el runtime.

---

## 1) Empaquetar el código

```bash
cd /Users/ricardoruiz/ricardoruiz.co/tools/proyecto-dc-escenarios-estrategia
bash build.sh
# → function.zip (~10 KB)
```

## 2) Crear el IAM role (una sola vez)

Mismo IAM role que `test-presidencial-explica` puede reutilizarse si quieres. Si prefieres role dedicado:

```bash
# Trust policy (Lambda assume role)
cat > /tmp/trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "lambda.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role \
  --role-name lambda-proyecto-dc-escenarios-estrategia \
  --assume-role-policy-document file:///tmp/trust-policy.json

# Permisos: CloudWatch logs + S3 cache read/write
aws iam attach-role-policy \
  --role-name lambda-proyecto-dc-escenarios-estrategia \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Inline policy para cache S3
cat > /tmp/s3-cache-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:PutObject"],
    "Resource": "arn:aws:s3:::elecciones-2026/ricardoruiz.co/proyecto-dc/escenarios-cache/*"
  }]
}
EOF

aws iam put-role-policy \
  --role-name lambda-proyecto-dc-escenarios-estrategia \
  --policy-name s3-cache \
  --policy-document file:///tmp/s3-cache-policy.json

# Capturar el ARN para usar abajo
ROLE_ARN=$(aws iam get-role --role-name lambda-proyecto-dc-escenarios-estrategia --query 'Role.Arn' --output text)
echo "ROLE_ARN=$ROLE_ARN"
```

> Si reutilizas el role de `test-presidencial-explica` (más simple), `ROLE_ARN=arn:aws:iam::167386641785:role/lambda-test-presidencial-explica`.

## 3) Crear la Lambda

```bash
# Reemplaza ROLE_ARN si usas otro
ROLE_ARN="arn:aws:iam::167386641785:role/lambda-proyecto-dc-escenarios-estrategia"

aws lambda create-function \
  --function-name proyecto-dc-escenarios-estrategia \
  --runtime python3.13 \
  --architectures x86_64 \
  --role "$ROLE_ARN" \
  --handler lambda_handler.handler \
  --timeout 60 \
  --memory-size 256 \
  --zip-file fileb://function.zip \
  --environment 'Variables={
    DEEPSEEK_API_KEY=PEGA_AQUI_TU_KEY,
    DEEPSEEK_MODEL=deepseek-v4-flash,
    S3_BUCKET=elecciones-2026,
    CACHE_PREFIX=ricardoruiz.co/proyecto-dc/escenarios-cache,
    CACHE_TTL_DIAS=7,
    STRICT_ORIGIN=true,
    PROMPT_VERSION=v1
  }'
```

> **Importante**: pega tu `DEEPSEEK_API_KEY` (la misma que ya tienes en `test-presidencial-explica`).

## 4) Crear el API Gateway HTTP API

```bash
# Crear API
API_ID=$(aws apigatewayv2 create-api \
  --name proyecto-dc-escenarios-estrategia \
  --protocol-type HTTP \
  --cors-configuration 'AllowOrigins=https://ricardoruiz.co,https://www.ricardoruiz.co,AllowMethods=POST,OPTIONS,AllowHeaders=Content-Type,MaxAge=300' \
  --query 'ApiId' --output text)
echo "API_ID=$API_ID"

# Integración con la Lambda
LAMBDA_ARN=$(aws lambda get-function --function-name proyecto-dc-escenarios-estrategia --query 'Configuration.FunctionArn' --output text)
INTEG_ID=$(aws apigatewayv2 create-integration \
  --api-id "$API_ID" \
  --integration-type AWS_PROXY \
  --integration-uri "$LAMBDA_ARN" \
  --payload-format-version 2.0 \
  --query 'IntegrationId' --output text)

# Ruta POST /estrategia
aws apigatewayv2 create-route \
  --api-id "$API_ID" \
  --route-key 'POST /estrategia' \
  --target "integrations/$INTEG_ID"

# Auto-deploy en stage $default
aws apigatewayv2 create-stage \
  --api-id "$API_ID" \
  --stage-name '$default' \
  --auto-deploy

# Permiso para que API Gateway invoque la Lambda
aws lambda add-permission \
  --function-name proyecto-dc-escenarios-estrategia \
  --statement-id apigw-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:167386641785:$API_ID/*/*/estrategia"

# URL final
echo "ENDPOINT: https://${API_ID}.execute-api.us-east-1.amazonaws.com/estrategia"
```

## 5) Update del frontend

Copiá el `ENDPOINT` impreso en el paso 4 y editá `proyecto-dc/escenarios-2027.html`, constante `STRATEGY_ENDPOINT`:

```js
const STRATEGY_ENDPOINT = 'https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/estrategia';
```

## 6) Test desde local

```bash
# Dry-run sin red (solo construye el prompt y muestra el flujo)
python3 lambda_handler.py --dry-run --show-prompt

# Dry-run con red (llama DeepSeek de verdad)
DEEPSEEK_API_KEY="tu_key" python3 lambda_handler.py --dry-run
```

## 7) Update posterior del código

```bash
bash build.sh
aws lambda update-function-code \
  --function-name proyecto-dc-escenarios-estrategia \
  --zip-file fileb://function.zip
```

## 8) Si cambias el SYSTEM_PROMPT

Bumpea `PROMPT_VERSION` para invalidar el cache existente:

```bash
aws lambda update-function-configuration \
  --function-name proyecto-dc-escenarios-estrategia \
  --environment 'Variables={PROMPT_VERSION=v2, ...resto igual...}'
```

---

## Costos esperados

- DeepSeek V4 Flash: ~$0.0002 por llamada.
- Cache S3: TTL 7d, hash24 sobre sliders+territorio+arquetipos. Usuarios distintos con la misma combinación reusan el resultado.
- Estimado: una sesión de campaña juega 20-50 escenarios → ~$0.005-0.01 por sesión.
- A 1.000 sesiones/mes: ~$5-10 al mes.

## Latencia esperada

- Cache hit: ~150 ms (lectura S3).
- Cache miss (llamada DeepSeek V4 Flash con 5 arquetipos × ~50 palabras c/u): 10-15 s.
- Lambda timeout 60s deja margen amplio.

## Anti-abuse

- CORS estricto: solo `https://ricardoruiz.co`, `https://www.ricardoruiz.co` y `http://localhost:8765` (preview local).
- Body cap 20 KB.
- Cache invalida automáticamente cualquier intento de duplicar llamadas idénticas.
- No hay rate limit por IP en API Gateway HTTP API por defecto. Si lo necesitas, configura un usage plan o pone CloudFront/WAF al frente.

## Rollback

Si algo sale mal:

```bash
# Apagar la Lambda (deja el código pero no responde)
aws lambda update-function-configuration \
  --function-name proyecto-dc-escenarios-estrategia \
  --environment 'Variables={DEEPSEEK_API_KEY=DISABLED,...}'
# El frontend cae al fallback (mensaje "no disponible") sin romper.

# O borrar API+Lambda completamente
aws apigatewayv2 delete-api --api-id "$API_ID"
aws lambda delete-function --function-name proyecto-dc-escenarios-estrategia
aws iam delete-role-policy --role-name lambda-proyecto-dc-escenarios-estrategia --policy-name s3-cache
aws iam detach-role-policy --role-name lambda-proyecto-dc-escenarios-estrategia --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-role --role-name lambda-proyecto-dc-escenarios-estrategia
```
