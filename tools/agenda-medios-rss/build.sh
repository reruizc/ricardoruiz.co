#!/usr/bin/env bash
# Empaqueta el Lambda en deployment.zip — sin dependencias extra.
# boto3 ya viene incluido en el runtime Python 3.12 de Lambda.
set -euo pipefail
cd "$(dirname "$0")"
rm -f deployment.zip
zip -j deployment.zip lambda_handler.py feeds.json
echo "→ $(pwd)/deployment.zip"
ls -lh deployment.zip
