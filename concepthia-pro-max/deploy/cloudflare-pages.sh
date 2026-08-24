#!/usr/bin/env bash
# Publish the static ConcepthIA interface directly to Cloudflare Pages.
set -euo pipefail

# A Lambda Function URL avoids API Gateway's fixed 30-second integration ceiling.
api_url="https://2xe7zbp4jxmgyrkqy63s2hm2em0rytsg.lambda-url.us-east-1.on.aws"
build_dir="$(mktemp -d)"
trap 'rm -rf "$build_dir"' EXIT

cp src/concepthia_pilot/static/styles.css "$build_dir/styles.css"
perl -0pe "s{</head>}{<script>window.CONCEPTHIA_API_BASE='${api_url}';</script></head>}" \
  src/concepthia_pilot/static/index.html > "$build_dir/index.html"
wrangler pages deploy "$build_dir" --project-name concepthia-2-0 --branch main
