#!/usr/bin/env python3
# Baja el preconteo 2V presidencial por MUNICIPIO desde el feed de la
# Registraduria (via worker proxy). Una llamada por depto -> mapagan trae
# los municipios. Reconstruye Cepeda(2) y Abelardo(3) por municipio.
#
#   python3 tools/segunda-vuelta-prec/fetch_2v_municipios.py
#   -> tools/segunda-vuelta-prec/dos_vuelta_municipios.json
import json, subprocess, sys, time

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
PROXY = 'https://registraduria-proxy.reruizc.workers.dev/presidente2v/{}'

DEPS = ['01','03','05','07','09','11','12','13','15','16','17','19','21','23',
        '24','25','26','27','28','29','31','40','44','46','48','50','52','54',
        '56','60','64','68','72','88']

gi = lambda o, k: int(str(o.get(k, '0')).replace('.', '').replace(',', '') or 0)

def fetch(dep):
    out = subprocess.run(
        ['curl', '-s', '--max-time', '30', '-A', UA,
         '-H', 'Referer: https://resultados.registraduria.gov.co/',
         PROXY.format(dep)],
        capture_output=True, text=True, timeout=40)
    return json.loads(out.stdout)

munis = {}
nat_cep = nat_abe = 0
for dep in DEPS:
    try:
        d = fetch(dep)
        mg = d['camaras'][0].get('mapagan', [])
    except Exception as e:
        print(f'  ! {dep} -> {e}', file=sys.stderr); continue
    n = 0
    for e in mg:
        amb = str(e.get('amb', '')).zfill(5)
        win = str(e.get('codpar', ''))
        vot = gi(e, 'vot'); votcan = gi(e, 'votcan')
        if win == '2':       # Cepeda gana
            cep, abe = vot, votcan - vot
        elif win == '3':     # Abelardo gana
            abe, cep = vot, votcan - vot
        else:                # empate / sin dato -> repartir desconocido
            cep = abe = votcan // 2
        munis[amb] = {
            'dep': dep, 'mun': amb[2:], 'nombre': e.get('nombre', ''),
            'cep2v': cep, 'abe2v': abe, 'votcan2v': votcan,
            'votant2v': gi(e, 'votant'), 'mesesc': gi(e, 'mesesc'),
            'pmesesc': e.get('pmesesc', ''),
        }
        nat_cep += cep; nat_abe += abe; n += 1
    print(f'{dep}: {n:4d} munis  (acum Cep {nat_cep:,} / Abe {nat_abe:,})')
    time.sleep(0.15)

path = 'tools/segunda-vuelta-prec/dos_vuelta_municipios.json'
json.dump({'munis': munis, 'nat': {'cep2v': nat_cep, 'abe2v': nat_abe,
          'n_munis': len(munis)}}, open(path, 'w'), ensure_ascii=False)
print(f'\nNACIONAL 2V (suma munis): Cepeda {nat_cep:,} vs Abelardo {nat_abe:,} '
      f'-> margen Abe {nat_abe-nat_cep:,}')
print(f'munis: {len(munis)}  ->  {path}')
