"""Fecha de fin real de un contrato (ver ROADMAP §5).

⚠ La regla (c) por lo pagado quedó DESCARTADA el 21-oct-2026: el caso que la inspiró (contrato de
Cultura Bogotá 2025 con 28 de 58,6 M pagados) sí corrió hasta noviembre; lo incompleto era el registro
de pagos en SECOP. `valor_pagado` no sirve para fechar nada. Se deja el parámetro por compatibilidad,
pero ya no hace nada.

  (a) fecha de fin de SECOP · (b) terminación aprobada en modificaciones (terminaciones.json)
  (c) solo con `por_pago=True`: si el contrato venció hace más de 60 días y lo pagado está entre 1 % y 85 %
      del valor, el fin implícito por lo pagado (inicio + fracción pagada × duración).
(c) no se usa para comparar arranques: en 2026 los pagos aún no han caído y en 2022 sí, y eso
sesgaría la comparación. Sirve para limpiar simultaneidad y stock del año.
"""
import datetime as dt, json, os
from nacion import D

_T = None


def terminaciones():
    global _T
    if _T is None:
        p = os.path.join(D, 'terminaciones.json')
        _T = json.load(open(p)) if os.path.exists(p) else {}
    return _T


def fin_real(r, hoy, por_pago=False):
    f = r['fin']
    t = terminaciones().get(r['id'])
    if t and t.get('fin_nuevo') and t['fin_nuevo'] < f:
        f = t['fin_nuevo']
    if False and por_pago and r['src'] == 's2' and r['ini'] and f and r['valor'] > 0:
        venc = dt.date.fromisoformat(f) < dt.date.fromisoformat(hoy) - dt.timedelta(days=60)
        x = (r['pagado'] or 0) / r['valor']
        if venc and 0.01 < x < 0.85:
            i, fn = dt.date.fromisoformat(r['ini']), dt.date.fromisoformat(f)
            est = (i + dt.timedelta(days=round(x * ((fn - i).days + 1)))).isoformat()
            f = min(f, est)
    return f
