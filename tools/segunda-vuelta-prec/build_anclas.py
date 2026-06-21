#!/usr/bin/env python3
# Construye las "anclas" estáticas para segunda-vuelta-prec-2026.html.
#
# Por cada departamento (33 + exterior 88):
#   - metota   : total de mesas de 2ª vuelta  (de /v2/json/ACT/PR/{dep}.json)
#   - censo    : potencial electoral           (idem, totales.centota)
#   - cep1v    : votos de Cepeda 1V            (de /json/ACT/PR/{dep}.json, codpar 7)
#   - abe1v    : votos de Abelardo 1V          (codpar 10)
#   - prior    : share esperado de Cepeda en 2V por TRASVASE de bloques 1V
#                cep_bloc = Cepeda + 0.55 Fajardo + 0.65 Claudia + 0.85 (Roy+Caicedo+Murillo)
#                abe_bloc = Abelardo + 0.85 Paloma + 0.78 (M.Uribe+Matamoros+Botero+Macollins+Lizcano)
#                prior = cep_bloc / (cep_bloc + abe_bloc)
#
# El JSON de la Registraduría exige UA de navegador completo (WAF). Curl por
# subprocess (igual que el ponderador) esquiva además el TLS de python 3.14.

import json, subprocess, sys

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
OLD = 'https://resultados.registraduria.gov.co/json/ACT/PR/{}.json'      # 1V final (sigue vivo)
NEW = 'https://resultados.registraduria.gov.co/v2/json/ACT/PR/{}.json'   # 2V (estructura, censo, mesas)

DANE_DEP = {
    '60':'Amazonas','01':'Antioquia','40':'Arauca','56':'San Andrés','88':'Exterior',
    '03':'Atlántico','16':'Bogotá D.C.','05':'Bolívar','07':'Boyacá','09':'Caldas',
    '44':'Caquetá','46':'Casanare','11':'Cauca','12':'Cesar','17':'Chocó','13':'Córdoba',
    '15':'Cundinamarca','50':'Guainía','54':'Guaviare','19':'Huila','48':'La Guajira',
    '21':'Magdalena','52':'Meta','23':'Nariño','25':'Norte de Santander','64':'Putumayo',
    '24':'Risaralda','26':'Quindío','27':'Santander','28':'Sucre','29':'Tolima',
    '31':'Valle del Cauca','68':'Vaupés','72':'Vichada',
}

# codpar 1V → bloque y coeficiente de trasvase hacia Cepeda (resto va a Abelardo).
# Sólo se usan los pesos relativos para el ratio del prior.
CEP_1V  = '7'
ABE_1V  = '10'
# coef = fracción del candidato 1V que en 2V se suma al bloque de Cepeda
TRAS_CEP = {  # hacia Cepeda
    '7': 1.00,    # Cepeda
    '3': 0.55,    # Fajardo (centro)
    '11':0.65,    # Claudia López
    '6': 0.85,    # Roy Barreras
    '13':0.85,    # Carlos Caicedo
    '12':0.85,    # Luis G. Murillo
}
TRAS_ABE = {  # hacia Abelardo
    '10':1.00,    # Abelardo
    '2': 0.85,    # Paloma Valencia
    '4': 0.78,    # Miguel Uribe Londoño
    '5': 0.78,    # Gustavo Matamoros
    '8': 0.78,    # R. Botero
    '9': 0.78,    # Sondra Macollins
    '14':0.55,    # Óscar Lizcano (centro-derecha; reparte)
}

def fetch(url):
    try:
        out = subprocess.run(
            ['curl','-s','--max-time','30','-A',UA,
             '-H','Referer: https://resultados.registraduria.gov.co/',
             '-H','Accept: application/json', url],
            capture_output=True, text=True, timeout=40)
        return json.loads(out.stdout)
    except Exception as e:
        print(f'  ! {url} -> {e}', file=sys.stderr)
        return None

def votos_por_codpar(ds):
    """Suma vot por codpar en partotabla[].act."""
    out = {}
    try:
        for cam in ds.get('camaras', []):
            for p in cam.get('partotabla', []):
                a = p.get('act', p)
                cp = str(a.get('codpar',''))
                v  = int(a.get('vot') or 0)
                if cp: out[cp] = out.get(cp,0) + v
    except Exception:
        pass
    return out

def totales(ds):
    try:
        t = ds['totales']['act']
        g = lambda k: int(str(t.get(k,'0')).replace('.','').replace(',','') or 0)
        return {'metota': g('metota'), 'centota': g('centota'),
                'votval': g('votval'), 'votblan': g('votblan')}
    except Exception:
        return {'metota':0,'centota':0,'votval':0,'votblan':0}

anclas = {}
nat = {'cep1v':0,'abe1v':0,'cep_bloc':0,'abe_bloc':0,'metota':0,'censo':0}
for cod in sorted(DANE_DEP):
    name = DANE_DEP[cod]
    old = fetch(OLD.format(cod))
    new = fetch(NEW.format(cod))
    v1  = votos_por_codpar(old) if old else {}
    t2  = totales(new) if new else {'metota':0,'centota':0}
    # metota/censo: preferir 2V; si falla, caer a 1V
    t1  = totales(old) if old else {'metota':0,'centota':0}
    metota = t2['metota'] or t1['metota']
    censo  = t2['centota'] or t1['centota']

    cep_bloc = sum(v1.get(cp,0)*w for cp,w in TRAS_CEP.items())
    abe_bloc = sum(v1.get(cp,0)*w for cp,w in TRAS_ABE.items())
    prior = (cep_bloc/(cep_bloc+abe_bloc)) if (cep_bloc+abe_bloc) > 0 else 0.5

    anclas[cod] = {
        'n': name, 'metota': metota, 'censo': censo,
        'cep1v': v1.get(CEP_1V,0), 'abe1v': v1.get(ABE_1V,0),
        'prior': round(prior, 4),
    }
    nat['cep1v'] += v1.get(CEP_1V,0); nat['abe1v'] += v1.get(ABE_1V,0)
    nat['cep_bloc'] += cep_bloc; nat['abe_bloc'] += abe_bloc
    nat['metota'] += metota; nat['censo'] += censo
    print(f"{cod} {name:22s} mesas={metota:6d} censo={censo:9d} "
          f"cep1V={v1.get(CEP_1V,0):8d} abe1V={v1.get(ABE_1V,0):8d} prior={prior:.3f}")

nat_prior = nat['cep_bloc']/(nat['cep_bloc']+nat['abe_bloc']) if (nat['cep_bloc']+nat['abe_bloc'])>0 else 0.5
out = {
    'v': '2026-06-21',
    'nat': {
        'metota': nat['metota'], 'censo': nat['censo'],
        'cep1v': nat['cep1v'], 'abe1v': nat['abe1v'],
        'prior': round(nat_prior, 4),
    },
    'dep': anclas,
}
path = '/Users/ricardoruiz/ricardoruiz.co/tools/segunda-vuelta-prec/anclas-2v.json'
json.dump(out, open(path,'w'), ensure_ascii=False, indent=0)
print(f"\nNACIONAL  mesas={nat['metota']} censo={nat['censo']} "
      f"cep1V={nat['cep1v']:,} abe1V={nat['abe1v']:,} prior_nac={nat_prior:.4f}")
print(f"escrito -> {path}")
