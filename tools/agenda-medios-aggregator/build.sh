#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
rm -f deployment.zip
zip -j deployment.zip lambda_handler.py stopwords-es.txt
echo "→ $(pwd)/deployment.zip"
ls -lh deployment.zip
