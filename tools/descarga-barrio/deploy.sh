#!/usr/bin/env bash
# Despliega la Lambda `descarga-barrio` + HTTP API Gateway (ruta POST /entrega).
# Idempotente: crea si no existe, actualiza si ya está. Imprime la URL del endpoint.
# Requiere: aws CLI configurado (ricardo-mac-cli), permisos Lambda + API Gateway + IAM.
set -euo pipefail

FN=descarga-barrio
REGION=us-east-1
ACCOUNT=167386641785
ROLE=lambda-descarga-barrio
BUCKET=elecciones-2026
PREFIX="ricardoruiz.co/productos-barrio/"
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "== 1. IAM role =="
if ! aws iam get-role --role-name "$ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ROLE" \
    --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
  aws iam attach-role-policy --role-name "$ROLE" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  aws iam put-role-policy --role-name "$ROLE" --policy-name s3-productos-barrio \
    --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"s3:GetObject\",\"s3:PutObject\"],\"Resource\":\"arn:aws:s3:::${BUCKET}/${PREFIX}*\"}]}"
  echo "   rol creado; esperando propagación IAM (10s)"; sleep 10
else
  echo "   rol ya existe"
fi
ROLE_ARN="arn:aws:iam::${ACCOUNT}:role/${ROLE}"

echo "== 2. empaquetar =="
TMP="$(mktemp -d)"
cp "$HERE/lambda_handler.py" "$TMP/"
( cd "$TMP" && zip -q function.zip lambda_handler.py )

echo "== 3. crear/actualizar función =="
ENVVARS="Variables={BUCKET=${BUCKET},PREFIX=${PREFIX},MARKER_PREFIX=${PREFIX}_redenciones/,WOMPI_BASE=https://production.wompi.co/v1,PRECIO_MIN=85000000,URL_TTL=600,VENTANA_DIAS=30}"
if aws lambda get-function --function-name "$FN" >/dev/null 2>&1; then
  aws lambda update-function-code --function-name "$FN" --zip-file "fileb://$TMP/function.zip" >/dev/null
  aws lambda wait function-updated --function-name "$FN"
  aws lambda update-function-configuration --function-name "$FN" \
    --handler lambda_handler.handler --timeout 15 --memory-size 256 \
    --environment "$ENVVARS" >/dev/null
  echo "   función actualizada"
else
  aws lambda create-function --function-name "$FN" \
    --runtime python3.12 --role "$ROLE_ARN" --handler lambda_handler.handler \
    --timeout 15 --memory-size 256 --environment "$ENVVARS" \
    --zip-file "fileb://$TMP/function.zip" >/dev/null
  echo "   función creada"
fi
aws lambda wait function-updated --function-name "$FN"

echo "== 4. HTTP API Gateway =="
API_ID="$(aws apigatewayv2 get-apis --query "Items[?Name=='${FN}'].ApiId | [0]" --output text)"
if [ "$API_ID" = "None" ] || [ -z "$API_ID" ]; then
  API_ID="$(aws apigatewayv2 create-api --name "$FN" --protocol-type HTTP \
    --target "arn:aws:lambda:${REGION}:${ACCOUNT}:function:${FN}" \
    --cors-configuration AllowOrigins='*',AllowMethods='POST,OPTIONS',AllowHeaders='content-type' \
    --query ApiId --output text)"
  aws lambda add-permission --function-name "$FN" --statement-id apigw-invoke \
    --action lambda:InvokeFunction --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT}:${API_ID}/*/*" >/dev/null 2>&1 || true
  echo "   API creada: $API_ID"
else
  echo "   API ya existe: $API_ID"
fi

ENDPOINT="$(aws apigatewayv2 get-api --api-id "$API_ID" --query ApiEndpoint --output text)"
rm -rf "$TMP"
echo
echo "ENDPOINT (pega en descarga-entrega.html -> const API, añadiendo la ruta):"
echo "  ${ENDPOINT}/entrega"
echo
echo "Prueba (debe dar error de pago, no de servidor):"
echo "  curl -s -X POST ${ENDPOINT}/entrega -H 'Content-Type: application/json' -d '{\"producto\":\"genero-1v\",\"tx\":\"fake\"}'"
