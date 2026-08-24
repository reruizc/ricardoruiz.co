#!/usr/bin/env bash
# Deploy ConcepthIA to Lambda + API Gateway. Run from this project directory.
set -euo pipefail

region="${AWS_REGION:-us-east-1}"
function_name="concepthia-pilot"
role_name="lambda-concepthia-pilot"
bucket="elecciones-2026"
prefix="ricardoruiz.co/concepthia-pro-max"
project_dir="$(pwd)"
build_dir="$(mktemp -d)"
trap 'rm -rf "$build_dir"' EXIT

aws iam create-role --role-name "$role_name" \
  --assume-role-policy-document file://deploy/lambda-trust-policy.json 2>/dev/null || true
aws iam attach-role-policy --role-name "$role_name" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam put-role-policy --role-name "$role_name" --policy-name concepthia-corpus-read \
  --policy-document file://deploy/lambda-s3-policy.json
aws iam wait role-exists --role-name "$role_name"

# Lambda runs on Linux; request Linux wheels instead of copying macOS native modules.
python3 -m pip install --quiet --target "$build_dir" --platform manylinux2014_x86_64 \
  --implementation cp --python-version 313 --only-binary=:all: -r requirements.txt
cp lambda_handler.py "$build_dir/"
cp -R src/concepthia_pilot "$build_dir/"
(cd "$build_dir" && zip -qr "$project_dir/deploy/concepthia-lambda.zip" .)

# Reuses the key already configured in the existing DeepSeek Lambda; it is never printed.
deepseek_key="$(aws lambda get-function-configuration --function-name caudal-analiza --query 'Environment.Variables.DEEPSEEK_API_KEY' --output text)"
role_arn="arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/$role_name"
environment="Variables={CONCEPTHIA_S3_BUCKET=$bucket,CONCEPTHIA_S3_PREFIX=$prefix,CONCEPTHIA_LLM_PROVIDER=deepseek,DEEPSEEK_API_KEY=$deepseek_key,DEEPSEEK_MODEL=deepseek-chat}"

if aws lambda get-function --function-name "$function_name" >/dev/null 2>&1; then
  aws lambda update-function-code --function-name "$function_name" --zip-file fileb://deploy/concepthia-lambda.zip >/dev/null
  aws lambda wait function-updated --function-name "$function_name"
  aws lambda update-function-configuration --function-name "$function_name" --timeout 120 --memory-size 2048 --environment "$environment" >/dev/null
else
  aws lambda create-function --function-name "$function_name" --runtime python3.13 \
    --role "$role_arn" --handler lambda_handler.handler --timeout 120 --memory-size 2048 \
    --environment "$environment" --zip-file fileb://deploy/concepthia-lambda.zip >/dev/null
fi

api_id="$(aws apigatewayv2 get-apis --query "Items[?Name=='concepthia-pilot-api'].ApiId | [0]" --output text)"
if [[ "$api_id" == "None" || -z "$api_id" ]]; then
  api_id="$(aws apigatewayv2 create-api --name concepthia-pilot-api --protocol-type HTTP \
    --cors-configuration AllowOrigins='*',AllowMethods='GET,POST,OPTIONS',AllowHeaders='content-type' \
    --query ApiId --output text)"
fi
lambda_arn="$(aws lambda get-function --function-name "$function_name" --query 'Configuration.FunctionArn' --output text)"
integration_id="$(aws apigatewayv2 get-integrations --api-id "$api_id" --query "Items[?IntegrationUri=='$lambda_arn'].IntegrationId | [0]" --output text)"
if [[ "$integration_id" == "None" || -z "$integration_id" ]]; then
  integration_id="$(aws apigatewayv2 create-integration --api-id "$api_id" --integration-type AWS_PROXY \
    --integration-uri "$lambda_arn" --payload-format-version 2.0 --timeout-in-millis 30000 --query IntegrationId --output text)"
fi
route_id="$(aws apigatewayv2 get-routes --api-id "$api_id" --query "Items[?RouteKey==\`\$default\`].RouteId | [0]" --output text)"
if [[ "$route_id" == "None" || -z "$route_id" ]]; then
  aws apigatewayv2 create-route --api-id "$api_id" --route-key '$default' --target "integrations/$integration_id" >/dev/null
fi
stage_exists="$(aws apigatewayv2 get-stages --api-id "$api_id" --query "Items[?StageName==\`\$default\`].StageName | [0]" --output text)"
if [[ "$stage_exists" == "None" || -z "$stage_exists" ]]; then
  aws apigatewayv2 create-stage --api-id "$api_id" --stage-name '$default' --auto-deploy >/dev/null
fi
aws apigatewayv2 update-stage --api-id "$api_id" --stage-name '$default' \
  --default-route-settings ThrottlingBurstLimit=5,ThrottlingRateLimit=1 >/dev/null
aws lambda add-permission --function-name "$function_name" --statement-id "apigateway-$api_id" \
  --action lambda:InvokeFunction --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:$region:$(aws sts get-caller-identity --query Account --output text):$api_id/*" 2>/dev/null || true
aws apigatewayv2 get-api --api-id "$api_id" --query ApiEndpoint --output text
