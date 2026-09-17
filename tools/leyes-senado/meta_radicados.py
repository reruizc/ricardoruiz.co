#!/usr/bin/env python3
"""El sello de frescura POR DENTRO de los manifiestos `pl-radicados-*`.

Por qué existe (17-sep-2026): del 15 al 17-sep el harvester del Senado murió
cuatro corridas seguidas sin escribir snapshot, y el chequeo de salud dio 29/29.
`*_upload` re-sube el manifiesto en cada corrida aunque la cosecha no haya
traído nada, así que su `LastModified` en S3 siempre es de hoy: dato viejo
dentro de un archivo fresco. El cliente lo notó antes que nosotros.

El manifiesto es JSONL y pesa cientos de KB, así que `salud/check.py` no lo baja
para mirarle una fecha (tope `MAX_BYTES_FECHA_INTERNA`, y solo lee JSON). En vez
de eso, cada builder sube AL LADO un `pl-radicados-{…}.meta.json` de <1 KB que
el catálogo vigila con `campo_fecha='visto_max'`.

⚠ `visto_max` y NO `presentacion_max`. `_visto` es el último día en que el
harvester vio la lista del registro: mide si NOSOTROS estamos mirando. La fecha
de presentación mide si el CONGRESO está radicando, y eso tiene silencios
legítimos — del 9 al 14-sep-2026 el Senado no publicó un solo radicado, y en
cada receso son semanas. Una alarma sobre esa fecha sonaría sin que nada esté
roto. Va en el meta solo como dato para quien lo lea.

⚠ El meta se sube DESPUÉS del manifiesto, nunca antes: si la subida del
manifiesto falla, el sello no puede quedar diciendo que hay dato fresco.
"""
import datetime as dt
import json
import re

_FECHA = re.compile(r'^(\d{4})[-/](\d{2})[-/](\d{2})')


def _dia(v):
    m = _FECHA.match(str(v or ''))
    return '-'.join(m.groups()) if m else None


def resumen(recs, camara, leg):
    vistos = [d for d in (_dia(r.get('_visto')) for r in recs) if d]
    present = [d for d in (_dia(r.get('fecha_de_presentacion')) for r in recs) if d]
    return {
        'v': 1,
        'camara': camara,
        'legislatura': leg,
        'generado': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
        # el campo que vigila salud/catalogo.py
        'visto_max': max(vistos) if vistos else None,
        'n': len(recs),
        # fichas cuyo detalle no respondió en la última cosecha (ban del WAF):
        # están en el manifiesto, pero con el estado de la última vez que sí.
        'n_sin_detalle': sum(1 for r in recs if r.get('_detalle_ok') is False),
        'presentacion_max': max(present) if present else None,
    }


def escribir(recs, manifiesto_path, camara, leg):
    """Escribe el .meta.json junto al manifiesto local y devuelve su ruta."""
    destino = manifiesto_path.with_name(manifiesto_path.stem + '.meta.json')
    destino.write_text(json.dumps(resumen(recs, camara, leg), ensure_ascii=False, indent=1),
                       encoding='utf-8')
    return destino


def cmd_subida(meta_path, bucket):
    return (f'aws s3 cp "{meta_path}" "s3://{bucket}/metadata/{meta_path.name}" '
            f'--content-type application/json --cache-control no-cache')
