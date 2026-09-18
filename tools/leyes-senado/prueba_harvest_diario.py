#!/usr/bin/env python3
"""Pruebas de harvest_diario.py SIN tocar leyes.senado.gov.co.

Todo lo que sale a la red está sustituido y el reloj es falso (un `sleep` lo
adelanta), así que los 2400 s de presupuesto y los 600 s de espera por ban se
prueban en milisegundos. Existe porque el harvester solo se puede probar de
verdad contra un WAF que castiga las pruebas: cada escenario de acá es una
falla que ya ocurrió en producción (ver las notas de campo del 17-sep-2026).

    python3 tools/leyes-senado/prueba_harvest_diario.py      # sale con 1 si algo falla
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harvest_diario as hd  # noqa: E402

FALLAS = []


def ok(cond, msg):
    print(('  ✓ ' if cond else '  ✗ ') + msg)
    if not cond:
        FALLAS.append(msg)


class Mundo:
    """Un Senado de mentira: lista, fichas, PDFs, ban y reloj."""

    def __init__(self, n=6, previos=4, desc=True):
        self.tmp = Path(tempfile.mkdtemp(prefix='harvest-prueba-'))
        self.t = 1_000_000.0
        self.ids = list(range(100, 100 + n))
        self.lista = [{'id': i, 'numero_senado': f'{i - 99:03d}/26', 'numero_camara': '',
                       'titulo': f'PROYECTO {i}', 'autor': 'X', 'comision': 'PRIMERA',
                       'estado': 'EN LISTA', 'type': 'pdly'} for i in self.ids]
        if desc:
            self.lista.reverse()
        self.estado = {i: 'PENDIENTE' for i in self.ids}
        self.url = {i: f'https://x/p-ley/PL {i}.pdf' for i in self.ids}
        self.peso = {}                 # id → bytes que declara el servidor
        self.ban = lambda t: False     # ¿está baneado en el instante t?
        self.seg_detalle = 0.5
        self.pedidos = {'detalle': [], 'tamano': [], 'pdf': []}
        self.lista_vacia = False
        hd.REPO = self.tmp
        hd.OUT = self.tmp / 'diario'
        hd.time.time = lambda: self.t
        hd.time.sleep = self._sleep
        hd.time.strftime = lambda f: '00:00:00'
        hd.fetch_lista = lambda leg: [] if self.lista_vacia else list(self.lista)
        hd.fetch_detalle = self._detalle
        hd.tamano_remoto = self._tamano
        hd.descargar_pdf = self._pdf
        hd.extraer_texto = lambda p, t: 'ocr-embebido'
        if previos:
            base = hd.OUT / '2026-2027'
            base.mkdir(parents=True)
            snap = {}
            for i in self.ids[:previos]:
                snap[str(i)] = {'_id': str(i), 'numero_senado': f'{i - 99:03d}/26',
                                'estado': 'PENDIENTE', 'titulo': f'PROYECTO {i}',
                                'fecha_de_presentacion': '2026/07/28',
                                'texto_radicado_url': self.url[i], '_detalle_ok': True}
                self._escribe_pdf(base / 'textos' / f'PL-{i - 99:03d}-26.pdf')
            (base / 'proyectos.json').write_text(json.dumps(snap), encoding='utf-8')

    def _sleep(self, s):
        self.t += s

    def _escribe_pdf(self, p):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'%PDF' + b'0' * 2000)

    def _detalle(self, pid):
        self.pedidos['detalle'].append(int(pid))
        self.t += self.seg_detalle
        if self.ban(self.t):
            self.t += 45               # 3 intentos × ~11 s de tarpit + pausas
            return None
        i = int(pid)
        return {'numero_senado': f'{i - 99:03d}/26', 'estado': self.estado[i],
                'titulo': f'PROYECTO {i}', 'fecha_de_presentacion': '2026/07/28',
                'texto_radicado_url': self.url[i]}

    def _tamano(self, url):
        i = int(url.split('PL ')[1].split('.')[0])
        self.pedidos['tamano'].append(i)
        return self.peso.get(i, 2_000_000)

    def _pdf(self, url, dst, retries=4, limite=None):
        i = int(url.split('PL ')[1].split('.')[0])
        self.pedidos['pdf'].append(i)
        self.t += 20
        self._escribe_pdf(dst)
        return True, 2004

    def corre(self, *argv):
        sys.argv = ['harvest_diario.py', *argv]
        rc = hd.main()
        snap_p = hd.OUT / '2026-2027' / 'proyectos.json'
        snap = json.loads(snap_p.read_text(encoding='utf-8')) if snap_p.exists() else {}
        return rc, snap

    def novedades(self):
        f = sorted((hd.OUT / 'novedades').glob('*.json'))
        return json.loads(f[-1].read_text(encoding='utf-8')) if f else None


print('\nA · corrida normal: 4 conocidos + 2 nuevos')
m = Mundo()
rc, snap = m.corre()
ok(rc == 0, 'sale con 0')
ok(len(snap) == 6, 'el snapshot trae los 6')
ok(len(m.novedades()['nuevos']) == 2, 'reporta 2 nuevos')
ok(sorted(m.pedidos['pdf']) == [104, 105], 'solo baja los 2 PDF que no tenía')

print('\nB · el PDF de 218 MB no se baja, y a la segunda corrida ni se pregunta')
m = Mundo()
m.peso[105] = 218_420_618
rc, snap = m.corre()
ok(rc == 0, 'un PDF gigante no vuelve parcial la corrida')
ok(105 not in m.pedidos['pdf'], 'no intenta bajarlo')
ok(snap['105'].get('_pdf_grande_mb') == 218.4, 'queda anotado con su tamaño')
m.pedidos = {'detalle': [], 'tamano': [], 'pdf': []}
rc, snap = m.corre()
ok(105 not in m.pedidos['tamano'] and 105 not in m.pedidos['pdf'],
   'segunda corrida: cero peticiones por ese archivo')
ok(snap['105'].get('_pdf_grande_mb') == 218.4, 'la marca sobrevive')
m.url[105] = 'https://x/p-ley/PL 105.pdf?v2'
m.peso[105] = 3_000_000
m.pedidos = {'detalle': [], 'tamano': [], 'pdf': []}
rc, snap = m.corre()
ok(105 in m.pedidos['pdf'] and '_pdf_grande_mb' not in snap['105'],
   'si el Senado cambia el archivo, se vuelve a mirar y se baja')

print('\nC · ban de 9 min a media corrida: espera, retoma y trae TODO')
m = Mundo(n=40, previos=40)
t_ban = m.t + 30
m.ban = lambda t: t_ban <= t < t_ban + 540
for i in m.ids:
    m.estado[i] = 'CON PONENTE'
rc, snap = m.corre('--no-pdf')
ok(rc == 0, 'sale con 0')
ok(all(v['_detalle_ok'] for v in snap.values()), 'ninguna ficha quedó sin refrescar')
ok(all(v['estado'] == 'CON PONENTE' for v in snap.values()), 'todas traen el estado nuevo')
perdidos = len(m.pedidos['detalle']) - 40
ok(perdidos <= 6, f'peticiones gastadas contra el ban: {perdidos} (antes: una por ficha, 3 intentos c/u)')

print('\nD · ban que no se levanta: corta, conserva y ESCRIBE')
m = Mundo(n=40, previos=30)
t_ban = m.t + 30
m.ban = lambda t: t >= t_ban
rc, snap = m.corre('--no-pdf')
ok(rc == hd.RC_PARCIAL, f'sale con {hd.RC_PARCIAL} (parcial), no con 0')
ok(len(snap) == 40, 'el snapshot se escribe con los 40: los nuevos entran aunque sea con la fila de la lista')
ok(len(m.pedidos['detalle']) < 40, f'no golpea ficha por ficha ({len(m.pedidos["detalle"])} peticiones de detalle)')
ok(snap['100']['estado'] == 'PENDIENTE' and snap['100'].get('fecha_de_presentacion'),
   'lo conservado es la ficha completa anterior')

print('\nE · servidor arrastrándose: se acaba el presupuesto y aun así guarda')
m = Mundo(n=40, previos=30)
m.seg_detalle = 100
t_ini = m.t
rc, snap = m.corre('--no-pdf')
ok(rc == hd.RC_PARCIAL, 'sale parcial')
ok(len(snap) == 40, 'snapshot escrito')
ok(m.t - t_ini < 2700, f'termina en {m.t - t_ini:.0f} s de reloj: antes de que la etapa la mate a los 2700')

print('\nF · lista vacía con snapshot previo: es falla, no «nada que hacer»')
m = Mundo()
m.lista_vacia = True
antes = (hd.OUT / '2026-2027' / 'proyectos.json').read_text()
rc, snap = m.corre()
ok(rc == 1, 'sale con 1')
ok((hd.OUT / '2026-2027' / 'proyectos.json').read_text() == antes, 'no toca el snapshot')

print('\nG · diff: lo congelado por un ban sí reporta su movimiento al descongelarse')
prev = {'1': {'_detalle_ok': False, 'fecha_de_presentacion': '2026/07/28', 'estado': 'A'},
        '2': {'_detalle_ok': False, 'estado': 'A'}}
cur = {'1': {'estado': 'B', 'fecha_de_presentacion': '2026/07/28'},
       '2': {'estado': 'B', 'fecha_de_presentacion': '2026/07/28'}}
_, cambios = hd.diff(prev, cur)
ok([c['id'] for c in cambios] == ['1'],
   'ficha completa conservada → movimiento · fila de lista que se completa → silencio')

print('\nH · lo que ayer quedó sin refrescar va primero, aunque sea lo más viejo')
m = Mundo(n=40, previos=40)
base = hd.OUT / '2026-2027' / 'proyectos.json'
snap = json.loads(base.read_text())
for i in (100, 101, 102):                       # los tres más viejos (van al final de la lista)
    snap[str(i)]['_detalle_ok'] = False
base.write_text(json.dumps(snap))
rc, snap = m.corre('--no-pdf')
ok(sorted(m.pedidos['detalle'][:3]) == [100, 101, 102], 'las 3 pendientes se piden antes que nada')
ok(m.pedidos['detalle'][3] == 139, 'y después sigue el orden del registro (lo nuevo primero)')
ok(len(set(m.pedidos['detalle'])) == 40, 'ninguna se pide dos veces')

print('\nI · dos corridas el mismo día: la segunda no pisa lo que reportó la primera')
m = Mundo()                                     # 4 conocidos + 2 nuevos
m.corre()
n1 = m.novedades()
ok(len(n1['nuevos']) == 2, 'la primera reporta 2 nuevos')
m.estado[100] = 'CON PONENTE'                   # movimiento nuevo para la segunda
rc, snap = m.corre()
n2 = m.novedades()
ok(len(n2['nuevos']) == 2, 'la segunda conserva los 2 nuevos de la primera')
ok(any(c['id'] == '100' for c in n2['cambios']), 'y suma el movimiento propio')
p1 = {'nuevos': [], 'cambios': [{'id': '7', 'numero_senado': '7/26', 'titulo': 't',
                                  'deltas': {'estado': {'antes': 'A', 'ahora': 'B'}}}]}
c2 = [{'id': '7', 'numero_senado': '7/26', 'titulo': 't',
       'deltas': {'estado': {'antes': 'B', 'ahora': 'C'}, 'comision': {'antes': '', 'ahora': 'X'}}}]
_, fund = hd.fundir_novedades(p1, [], c2)
ok(fund[0]['deltas']['estado'] == {'antes': 'A', 'ahora': 'C'} and 'comision' in fund[0]['deltas'],
   'los deltas se encadenan: antes de la mañana, ahora de la noche')
_, fund = hd.fundir_novedades(p1, [], [{'id': '7', 'numero_senado': '7/26', 'titulo': 't',
                                         'deltas': {'estado': {'antes': 'B', 'ahora': 'A'}}}])
ok(fund == [], 'un campo que vuelve a su valor original no es movimiento')

print()
if FALLAS:
    print(f'✗ {len(FALLAS)} fallas')
    sys.exit(1)
print('✓ todo bien')
