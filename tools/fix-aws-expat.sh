#!/bin/bash
# Arregla el `aws` de Homebrew cuando revienta con:
#   Symbol not found: _XML_SetAllocTrackerActivationThreshold
#   ... Expected in: /usr/lib/libexpat.1.dylib
#
# Causa: en macOS 26 el bottle de python@3.14 trae pyexpat enlazado al
# libexpat del SISTEMA, que es más viejo que el que ese Python espera.
# Fix: re-apuntar los módulos .so de Python al expat de Homebrew (que sí
# trae el símbolo) y re-firmarlos ad-hoc. NO requiere sudo.
#
# OJO: brew reinstall/upgrade python@3.14 vuelve a poner el .so original →
# correr este script de nuevo. Fix permanente sin este parche: instalar el
# AWS CLI v2 oficial (PKG con su propio Python), que es inmune a esto.
set -euo pipefail

BREW_EXPAT="$(brew --prefix expat 2>/dev/null)/lib/libexpat.1.dylib"
if [ ! -f "$BREW_EXPAT" ]; then
  echo "Instalando expat de Homebrew…"; brew install expat
  BREW_EXPAT="$(brew --prefix expat)/lib/libexpat.1.dylib"
fi
if ! nm -gU "$BREW_EXPAT" 2>/dev/null | grep -q XML_SetAllocTrackerActivationThreshold; then
  echo "ERROR: el expat de brew ($BREW_EXPAT) no tiene el símbolo esperado." >&2
  exit 1
fi

PYDIR="$(brew --prefix python@3.14)/Frameworks/Python.framework/Versions/3.14/lib/python3.14/lib-dynload"
n=0
for f in "$PYDIR"/*.so; do
  if otool -L "$f" 2>/dev/null | grep -q "/usr/lib/libexpat.1.dylib"; then
    install_name_tool -change /usr/lib/libexpat.1.dylib "$BREW_EXPAT" "$f"
    codesign -f -s - "$f"
    echo "  ✓ repuntado: $(basename "$f")"
    n=$((n+1))
  fi
done
echo "Listo. $n módulo(s) repuntado(s)."
aws --version