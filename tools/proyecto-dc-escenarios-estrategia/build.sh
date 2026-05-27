#!/usr/bin/env bash
# Empaqueta lambda_handler.py en function.zip listo para Lambda.
# Patrón idéntico al de test-presidencial-explica (stdlib pura,
# sin dependencias externas — boto3 ya viene en el runtime Python 3.14).
set -euo pipefail
cd "$(dirname "$0")"
rm -f function.zip
zip -j function.zip lambda_handler.py
echo "✓ function.zip listo ($(stat -f%z function.zip 2>/dev/null || stat -c%s function.zip) bytes)"
