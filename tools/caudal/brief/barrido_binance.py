#!/usr/bin/env python3
"""
Barrido de la semana para el brief de Binance — Caudal x Cauce.

Imprime, en texto compacto, lo que Caudal tiene HOY para Binance en los seis
pilares (radar del cliente · Congreso · regulatorio · Ejecutivo · SUCOP ·
prensa) más los radicados de la semana y la agenda de comisiones. Es el insumo
con el que se escribe (y se revisa) el brief semanal: se corre, se lee, se
contrasta contra el PDF publicado y se decide si algo cambió.

  python3 tools/caudal/brief/barrido_binance.py                 # ventana: últimos 7 días
  python3 tools/caudal/brief/barrido_binance.py --desde 2026-08-31 [--dias-prensa 8]
  python3 tools/caudal/brief/barrido_binance.py --json salida.json  # además guarda el crudo

Habla con la Lambda por el worker (/caudal/api), como el navegador; no usa
acciones caras (nada de lectura LLM), así que corre sin credencial.
"""
import argparse, datetime, json, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

W = 'https://rr-auth.reruizc.workers.dev/caudal/api'
S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/legislativo/'
UA = 'caudal-brief/1.0 (+ricardoruiz.co)'


def post(p, timeout=60):
    req = urllib.request.Request(W, data=json.dumps(p).encode(), headers={
        'Content-Type': 'application/json', 'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:                                   # noqa: BLE001
        return {'error': str(e)[:120]}


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def iso(f):
    """Las fechas llegan como 2026-09-02 o 2026/09/02 según la fuente."""
    return (f or '')[:10].replace('/', '-')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--desde', help='YYYY-MM-DD (default: hace 7 días)')
    ap.add_argument('--dias-prensa', type=int, default=8)
    ap.add_argument('--json', help='guardar el crudo acá')
    a = ap.parse_args()
    desde = a.desde or (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    dp = a.dias_prensa
    jobs = {
        'cli': {'action': 'cliente', 'sector': 'binance', 'lectura': False},
        'tema_av': {'action': 'tema', 'query': 'activos virtuales', 'lectura': False},
        'tema_cripto': {'action': 'tema', 'query': 'criptoactivos', 'lectura': False},
        'tema_rt': {'action': 'tema', 'query': 'reforma tributaria', 'lectura': False},
        'tema_cf': {'action': 'tema', 'query': 'consumidor financiero', 'lectura': False},
        'tema_pgn': {'action': 'tema', 'query': 'presupuesto general 2027', 'lectura': False},
        'radicados': {'action': 'radicados'},
        'sanc_av': {'action': 'sanciones', 'query': 'activos virtuales', 'tipo_acto': 'todo'},
        'sanc_cripto': {'action': 'sanciones', 'query': 'criptoactivo', 'tipo_acto': 'todo'},
        'sanc_bin': {'action': 'sanciones', 'query': 'binance', 'tipo_acto': 'todo'},
        'sanc_lav': {'action': 'sanciones', 'query': 'lavado de activos', 'tipo_acto': 'todo'},
        'sanc_fin': {'action': 'sanciones', 'sector': 'financiero', 'tipo_acto': 'todo'},
        'eje_av': {'action': 'ejecutivo', 'query': 'activos virtuales'},
        'eje_cripto': {'action': 'ejecutivo', 'query': 'criptoactivos'},
        'eje_stats': {'action': 'ejecutivo'},
        'suc_ab': {'action': 'sucop', 'estado': 'abiertas'},
        'suc_av': {'action': 'sucop', 'query': 'activos virtuales'},
        'suc_lav': {'action': 'sucop', 'query': 'lavado'},
    }
    for k, q in (('med_bin', 'Binance'), ('med_cripto', 'criptoactivos Colombia'),
                 ('med_av', 'activos virtuales regulación'), ('med_uiaf', 'UIAF'),
                 ('med_dian', 'DIAN criptoactivos'), ('med_ss', 'Supersociedades'),
                 ('med_sfc', 'Superfinanciera'), ('med_rt', 'reforma tributaria'),
                 ('med_pgn', 'presupuesto 2027'), ('med_banrep', 'Banco de la República cripto'),
                 ('med_gt', 'Guatemala criptomonedas'), ('med_sv', 'El Salvador bitcoin'),
                 ('med_rd', 'República Dominicana criptomonedas ley'), ('med_pe', 'Perú SBS activos virtuales'),
                 ('med_bo', 'Bolivia ASFI cripto'), ('med_ve', 'Venezuela Sunacrip'),
                 ('med_mx', 'México activos virtuales ley')):
        jobs[k] = {'action': 'medios', 'query': q, 'dias': dp}
    with ThreadPoolExecutor(max_workers=6) as pool:
        res = dict(zip(jobs, pool.map(post, jobs.values())))
    try:
        res['agenda'] = get(S3 + 'ordenes-vigentes.json')
    except Exception as e:                                   # noqa: BLE001
        res['agenda'] = {'error': str(e)[:100]}
    if a.json:
        json.dump(res, open(a.json, 'w'), ensure_ascii=False)

    print(f'BARRIDO BINANCE · desde {desde} · prensa {dp} días · hoy {datetime.date.today()}')
    k = res['cli'].get('kpis', {})
    print('\n== RADAR', {x: k[x] for x in ('n_radar', 'alto', 'en_tramite', 'n_medios_sector') if x in k})
    for pil in ('congreso', 'regulatorio', 'sucop', 'ejecutivo', 'medios', 'contratacion'):
        xs = res['cli'].get(pil) or []
        print(f'  {pil}: {len(xs)}')
        for x in xs[:6]:
            print('     -', x.get('nivel'), '|', (x.get('titulo') or x.get('sancionado') or x.get('objeto') or '')[:90],
                  '|', (x.get('fecha') or x.get('anio') or ''), '|', (x.get('accion') or x.get('por_que') or '')[:70])
    print('\n== CONGRESO (en trámite por tema)')
    for t in ('tema_av', 'tema_cripto', 'tema_rt', 'tema_cf', 'tema_pgn'):
        its = (res[t].get('resumen') or {}).get('intentos') or []
        viv = [i for i in its if i.get('resultado') == 'EN_TRAMITE']
        print(f'  {t}: total {len(its)} · en trámite {len(viv)}')
        for i in viv[:6]:
            print('     -', i.get('anio'), i.get('numero_camara'), i.get('numero_senado'), '|', i['titulo'][:90], '|', i.get('comision'))
    rad = res['radicados']
    rs = (rad.get('radicados') or []) + (rad.get('radicados_camara') or [])
    nuevos = [r for r in rs if iso(r.get('fecha')) >= desde]
    print(f'\n== RADICADOS legislatura: {rad.get("n")} S + {rad.get("n_camara")} C · desde {desde}: {len(nuevos)}')
    for r in sorted(nuevos, key=lambda r: iso(r.get('fecha')), reverse=True)[:30]:
        print('     -', iso(r.get('fecha')), r.get('numero_senado') or r.get('numero_camara') or '', '|', (r.get('titulo') or '')[:100])
    print('\n== REGULATORIO (actos desde la fecha)')
    for t in ('sanc_av', 'sanc_cripto', 'sanc_bin', 'sanc_lav', 'sanc_fin'):
        d = res[t]; rec = [x for x in (d.get('resultados') or []) if iso(x.get('fecha')) >= desde]
        print(f'  {t}: n={d.get("n")} · nuevos {len(rec)}')
        for x in rec[:8]:
            print('     -', x.get('fecha'), x.get('fuente_nombre'), '|', x.get('tipo_acto'), '|', (x.get('sancionado') or '')[:40], '|', (x.get('motivo') or x.get('resolucion') or '')[:90])
    print('\n== EJECUTIVO')
    for t in ('eje_av', 'eje_cripto'):
        d = res[t]; xs = [x for x in (d.get('resultados') or []) if iso(x.get('fecha')) >= desde]
        print(f'  {t}: n={d.get("n")} · nuevos {len(xs)} · flex={(d.get("flexible") or {}).get("modo")}')
        for x in xs[:5]:
            print('     -', x.get('fecha'), x.get('tipo'), '|', (x.get('descripcion') or '')[:110])
    st = res['eje_stats']
    print('  últimos de Presidencia:', [(x.get('fecha'), (x.get('titulo') or '')[:36]) for x in (st.get('recientes') or [])[:5]])
    print('\n== SUCOP')
    for t in ('suc_ab', 'suc_av', 'suc_lav'):
        d = res[t]; print(f'  {t}: n={d.get("n")} ventana={d.get("ventana")}')
        for x in (d.get('resultados') or [])[:10]:
            print('     -', x.get('estado_consulta'), x.get('entidad'), '|', (x.get('titulo') or '')[:85], '| cierra', x.get('fecha_fin') or x.get('cierra'))
    print(f'\n== PRENSA ({dp} días)')
    for t in [x for x in jobs if x.startswith('med_')]:
        d = res[t]; xs = d.get('resultados') or []
        print(f'  {t}: n={d.get("n")}')
        for x in xs[:6]:
            print('     -', iso(x.get('fecha')), x.get('medio'), '|', (x.get('titulo') or '')[:110])
    print('\n== AGENDA de comisiones (ordenes-vigentes.json)')
    o = res['agenda']
    for s in (o.get('ordenes') or []):
        txt = json.dumps(s, ensure_ascii=False).lower()
        if any(w in txt for w in ('presupuesto', 'tributar', 'tercera', 'plenaria', 'hacienda', 'financier')):
            print('  -', s.get('fecha'), s.get('corporacion'), s.get('ambito'), '|',
                  [(p.get('numero') or p.get('num'), (p.get('titulo') or '')[:55]) for p in (s.get('proyectos') or [])][:5])
    print('  cobertura:', o.get('cobertura'), '·', o.get('desde'), '→', o.get('hasta'))


if __name__ == '__main__':
    main()
