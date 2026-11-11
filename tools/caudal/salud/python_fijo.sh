# Fija `python3` a la versión que tiene los paquetes (se carga con `.` desde los
# runners de launchd, DESPUÉS de su `export PATH=`).
# ⚠ 8-nov-2026: Homebrew movió /opt/homebrew/bin/python3 a 3.15, que no trae
# pypdf, pymupdf, openpyxl, weasyprint… Las etapas que los usan fallaban por
# dentro con rc=0. Los paquetes siguen en 3.14. En la EC2 (Linux, sin el
# python3.14 de Homebrew) este archivo no cambia nada.
if [ -x /opt/homebrew/bin/python3.14 ]; then
  mkdir -p "$HOME/.local/caudal-bin"
  ln -sf /opt/homebrew/bin/python3.14 "$HOME/.local/caudal-bin/python3"
  export PATH="$HOME/.local/caudal-bin:$PATH"
fi
