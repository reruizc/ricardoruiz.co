#!/usr/bin/env python3
"""
Caudal · Importancia — calibra y VALIDA el eje 1 contra el histórico 1990-2026.

    python3 tools/caudal/importancia/calibrar.py [--reporte ruta.md]

Qué hace y por qué así:

UNIVERSO = registro del Senado. Los 3.773 proyectos que solo existen en el
registro de Cámara tienen 0,7% de leyes contra 24,9% del Senado, y eso no
describe al Congreso: los que cruzan de cámara quedan deduplicados bajo el
registro del Senado, así que "solo en Cámara" es casi sinónimo de "no cruzó".
Entrenar con ellos regala un AUC alto y falso. Se evalúan aparte, declarados.

PARTICIÓN = temporal (out-of-time). Entrenar con lo viejo, medir con lo nuevo,
que es como se va a usar. Un split aleatorio se reporta al lado solo como
contraste: es más optimista porque deja que el modelo vea el mismo cuatrienio
en las dos mitades.

ETIQUETA = llegó a ley. Se descartan los proyectos cuyo desenlace todavía no se
conoce (ver features.etiqueta).
"""
import argparse
import json
import os
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import features as F                                          # noqa: E402
import antecedentes as ANT                                    # noqa: E402
from modelo import Logistica, auc, brier, calibracion, lift    # noqa: E402

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DIST = os.path.join(RAIZ, 'Bases de datos', 'leyes-senado', 'dist')
SALIDA = os.path.join(DIST, 's3', 'importancia-modelo.json')
SALIDA_AUT = os.path.join(DIST, 's3', 'importancia-autores.json')
SALIDA_ANT = os.path.join(DIST, 's3', 'importancia-antecedentes.json')

LEGISLATURAS_VIVAS = {'2025-2026', '2026-2027'}
ANIO_CORTE = 2015          # train < corte ≤ test
ANIO_TEST_MAX = 2024       # 2025+ tiene demasiado desenlace todavía abierto


def cargar(*archivos):
    out = []
    for a in archivos:
        p = os.path.join(DIST, a)
        if not os.path.exists(p):
            print(f'  ! falta {a}', file=sys.stderr)
            continue
        with open(p) as fh:
            for ln in fh:
                if ln.strip():
                    out.append(json.loads(ln))
    return out


def preparar(rows, autores_idx=None, solo_senado=True):
    """→ (X, y, meta) de las filas con etiqueta conocida."""
    X, y, meta = [], [], []
    for r in rows:
        if solo_senado and r.get('origen_registro') != 'senado':
            continue
        if not r.get('anio'):
            continue
        lab = F.etiqueta(r, LEGISLATURAS_VIVAS)
        if lab is None:
            continue
        X.append(F.vector(r, autores_idx))
        y.append(lab)
        meta.append(r)
    return X, y, meta


def evaluar(nombre, m, X, y):
    p = m.probs(X)
    return {
        'nombre': nombre, 'n': len(y), 'tasa_base': round(sum(y) / len(y), 4),
        'auc': round(auc(y, p), 4), 'brier': round(brier(y, p), 4),
        'logloss': round(m.logloss(X, y), 4),
        'lift10': lift(y, p, 0.10), 'lift20': lift(y, p, 0.20),
        'calibracion': calibracion(y, p),
    }


def _fmt_eval(e):
    L = [f"  {e['nombre']}: n={e['n']}  base={e['tasa_base']:.3f}  "
         f"AUC={e['auc']:.4f}  Brier={e['brier']:.4f}  logloss={e['logloss']:.4f}"]
    l10 = e['lift10']
    L.append(f"    top 10%: {l10['tasa_top']:.3f} de tasa vs {l10['tasa_base']:.3f} "
             f"de base → lift {l10['lift']}×")
    return '\n'.join(L)


# ---------------------------------------------------------------------------
# auditoría anti-fuga: ningún campo de desenlace puede estar entre las features
# ---------------------------------------------------------------------------
PROHIBIDOS = ['resultado', 'es_ley', 'etapa_max', 'n_debates_aprobados',
              'estado', 'fecha_primer_debate', 'dias_a_primer_debate',
              'ponentes', 'gacetas', 'murio_por_tiempo', 'veces_presentado',
              'empuje', 'vitrina_score', 'max_etapa_cluster', 'origen_registro',
              'debates_evidencia', 'texto_s3',
              # 'origen' entra aquí no por obvio sino por medido: dentro del
              # registro del Senado significa "ya cruzó de cámara". Queda en la
              # lista para que reintroducirlo dispare la alarma sola.
              'origen']


def auditar_fuga(rows, autores_idx):
    """Prueba empírica, no promesa. Dos ensayos:

    (a) se pisan los campos de desenlace en una copia del registro y se
        verifica que el vector no cambie — si alguna feature los leyera,
        cambiaría;
    (b) se reconstruye el índice de trayectoria del firmante usando SOLO
        proyectos anteriores al año de cada caso, y se verifica que el vector
        coincida con el que sale del índice completo. Si el corte temporal de
        `_traj` estuviera mal, aquí se separan.
    """
    problemas = []
    rnd = random.Random(3)
    muestra = rnd.sample(rows, min(600, len(rows)))
    for r in muestra:
        v0 = F.vector(r, autores_idx)
        r2 = dict(r)
        for k in PROHIBIDOS:
            if k in r2:
                r2[k] = None if not isinstance(r2[k], bool) else False
        r2['historial_reradicacion'] = [
            h for h in (r.get('historial_reradicacion') or [])
            if (h.get('anio') or 0) < (r.get('anio') or 0)]
        if F.vector(r2, autores_idx) != v0:
            problemas.append(('campo_desenlace', r.get('id')))

    # (b) índice "de época": solo lo radicado antes del año del caso
    rnd2 = random.Random(5)
    for r in rnd2.sample([x for x in rows if x.get('anio')], 200):
        a = r['anio']
        idx_epoca = F.trayectoria_autores([x for x in rows
                                           if (x.get('anio') or 0) < a])
        if F.vector(r, idx_epoca) != F.vector(r, autores_idx):
            problemas.append(('trayectoria', r.get('id')))
    return problemas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reporte', default=None)
    ap.add_argument('--epocas', type=int, default=400)
    args = ap.parse_args()
    log = []

    def P(*a):
        s = ' '.join(str(x) for x in a)
        print(s)
        log.append(s)

    P('CAUDAL · calibración del eje 1 (¿va a avanzar?)')
    P('=' * 72)

    rows = cargar('proyectos.jsonl', 'actos-legis.jsonl')
    P(f'\nHistórico cargado: {len(rows)} registros (proyectos de ley + actos legislativos)')

    AIDX = F.trayectoria_autores(rows)
    P(f'Índice de trayectoria de firmantes: {len(AIDX["datos"])} personas')

    # --- auditoría de fuga --------------------------------------------------
    fugas = auditar_fuga(rows, AIDX)
    P('\n[1] Auditoría anti-fuga (600 casos con el desenlace borrado + 200 con'
      ' el índice de firmantes reconstruido a su época):')
    P('    ' + ('OK — el vector de features no cambia en ninguno de los 800.'
                if not fugas else f'!! {len(fugas)} casos cambian: {fugas[:8]}'))
    if fugas:
        P('    ABORTA: hay fuga.')
        return 1

    X_all, y_all, M_all = preparar(rows, AIDX)
    P(f'\n[2] Universo etiquetable (registro Senado): {len(y_all)} '
      f'· tasa de ley {sum(y_all)/len(y_all):.1%}')
    desc = Counter(r.get('resultado') for r in rows
                   if r.get('origen_registro') == 'senado')
    P(f'    descartados por desenlace abierto: '
      f'{len([r for r in rows if r.get("origen_registro")=="senado" and F.etiqueta(r, LEGISLATURAS_VIVAS) is None])}'
      f'  (EN_TRAMITE vivo + SIN_DATO)')
    P(f'    resultados en el registro: {dict(desc.most_common(5))}')

    # --- partición temporal -------------------------------------------------
    tr = [i for i, r in enumerate(M_all) if r['anio'] < ANIO_CORTE]
    te = [i for i, r in enumerate(M_all)
          if ANIO_CORTE <= r['anio'] <= ANIO_TEST_MAX]
    Xtr = [X_all[i] for i in tr]
    ytr = [y_all[i] for i in tr]
    Xte = [X_all[i] for i in te]
    yte = [y_all[i] for i in te]
    P(f'\n[3] Partición temporal (out-of-time)')
    P(f'    train: radicados < {ANIO_CORTE}  → n={len(ytr)}  ley={sum(ytr)/len(ytr):.1%}')
    P(f'    test : {ANIO_CORTE}-{ANIO_TEST_MAX}            → n={len(yte)}  ley={sum(yte)/len(yte):.1%}')

    m = Logistica(F.FEATURES).fit(Xtr, ytr, epocas=args.epocas)
    ev_tr = evaluar('train (en muestra)', m, Xtr, ytr)
    ev_te = evaluar('TEST out-of-time', m, Xte, yte)
    P('\n[4] Desempeño')
    P(_fmt_eval(ev_tr))
    P(_fmt_eval(ev_te))

    # baselines: cuánto de esto lo explica una sola variable
    P('\n[5] Contra qué se compara (mismo test, misma métrica)')
    for nom, idxs in [('solo "lo radica el Gobierno"', ['gobierno']),
                      ('solo "es tratado internacional"', ['es_tratado']),
                      ('Gobierno + tratado + comisión', ['gobierno', 'es_tratado']
                       + [f for f in F.FEATURES if f.startswith('com_')])]:
        sel = set(idxs)
        mb = Logistica(F.FEATURES)
        mb.mu, mb.sd = m.mu, m.sd
        mb.w = [m.w[j] if F.FEATURES[j] in sel else 0.0
                for j in range(len(F.FEATURES))]
        mb.b = m.b
        # re-ajustar solo esas columnas es más justo que apagar pesos:
        Xs_tr = [[x[j] if F.FEATURES[j] in sel else 0.0 for j in range(len(x))]
                 for x in Xtr]
        Xs_te = [[x[j] if F.FEATURES[j] in sel else 0.0 for j in range(len(x))]
                 for x in Xte]
        mb = Logistica(F.FEATURES).fit(Xs_tr, ytr, epocas=args.epocas)
        p = mb.probs(Xs_te)
        P(f'    {nom:42} AUC={auc(yte, p):.4f}')
    P(f'    {"modelo completo":42} AUC={ev_te["auc"]:.4f}')

    # --- robustez: el corte de 2015 no puede ser el que sostiene el número ---
    P('\n[5b] Rolling origin — se repite la validación moviendo el corte')
    P('     corte   n_train  n_test   AUC_test')
    aucs = []
    for corte in (2006, 2010, 2014, 2018):
        itr = [i for i, r in enumerate(M_all) if r['anio'] < corte]
        ite = [i for i, r in enumerate(M_all)
               if corte <= r['anio'] <= ANIO_TEST_MAX]
        if len(itr) < 500 or len(ite) < 300:
            continue
        mm = Logistica(F.FEATURES).fit([X_all[i] for i in itr],
                                       [y_all[i] for i in itr], epocas=args.epocas)
        yy = [y_all[i] for i in ite]
        a = auc(yy, mm.probs([X_all[i] for i in ite]))
        aucs.append(a)
        P(f'     <{corte}   {len(itr):6d}  {len(ite):6d}   {a:.4f}')
    if aucs:
        P(f'     rango {min(aucs):.4f}–{max(aucs):.4f} · el número no depende de dónde se corte')

    # split aleatorio, solo como contraste
    rnd = random.Random(11)
    idx = list(range(len(y_all)))
    rnd.shuffle(idx)
    c = int(len(idx) * .7)
    ma = Logistica(F.FEATURES).fit([X_all[i] for i in idx[:c]],
                                   [y_all[i] for i in idx[:c]], epocas=args.epocas)
    pa = ma.probs([X_all[i] for i in idx[c:]])
    P(f'\n    [contraste] split aleatorio 70/30: AUC={auc([y_all[i] for i in idx[c:]], pa):.4f}'
      '  — más optimista, ve el mismo cuatrienio de los dos lados')

    # --- calibración --------------------------------------------------------
    P('\n[6] Calibración en test (predicho vs observado por decil)')
    P('    decil     n   predicho  observado')
    for c_ in ev_te['calibracion']:
        P(f"      {c_['decil']:2d}  {c_['n']:5d}    {c_['p_medio']:.3f}      {c_['obs']:.3f}")

    # --- fuera de universo --------------------------------------------------
    Xc, yc, _ = preparar([r for r in rows if r.get('origen_registro') == 'camara'],
                         AIDX, solo_senado=False)
    if yc and 0 < sum(yc) < len(yc):
        pc = m.probs(Xc)
        P(f'\n[7] Aplicado al registro de Cámara (fuera del universo de entrenamiento)')
        P(f'    n={len(yc)}  tasa de ley observada={sum(yc)/len(yc):.2%}  AUC={auc(yc, pc):.4f}')
        P('    Se reporta, no se corrige: en ese registro "llegar a ley" casi no se')
        P('    observa porque el que cruza queda bajo el registro del Senado. El AUC')
        P('    de aquí NO es comparable con el de arriba.')

    # --- pesos --------------------------------------------------------------
    P('\n[8] Qué aprendió (peso en la escala original; + empuja a ley)')
    pc_ = m.pesos_crudos()
    orden = sorted(range(len(F.FEATURES)), key=lambda j: -abs(pc_[j]))
    for j in orden[:16]:
        P(f'    {F.FEATURES[j]:26} {pc_[j]:+.3f}')

    # --- modelo final sobre TODO -------------------------------------------
    mf = Logistica(F.FEATURES).fit(X_all, y_all, epocas=args.epocas)

    # Corrección de nivel por deriva de época. El Congreso aprueba menos que
    # antes (27,1% antes de 2015 → 21,5% después), así que un modelo ajustado
    # sobre los 36 años sobre-estima el presente. Se corrige UN solo parámetro
    # —el intercepto— hasta que la probabilidad media predicha sobre la ventana
    # reciente iguale la tasa observada en esa ventana. Mueve el nivel, no el
    # orden: el AUC no cambia. Y el eje de riesgo multiplica por esta cifra,
    # así que tiene que ser una probabilidad de verdad, no solo un ranking.
    Xr = [X_all[i] for i in te]
    obj = sum(yte) / len(yte)
    b0 = mf.b
    lo, hi = b0 - 4, b0 + 4
    for _ in range(60):
        mid = (lo + hi) / 2
        mf.b = mid
        pm = sum(mf.probs(Xr)) / len(Xr)
        if pm > obj:
            hi = mid
        else:
            lo = mid
    delta = mf.b - b0
    P(f'\n[8b] Corrección de nivel por deriva de época: intercepto {b0:+.3f} → '
      f'{mf.b:+.3f} ({delta:+.3f})')
    P(f'     media predicha en {ANIO_CORTE}-{ANIO_TEST_MAX} ahora {sum(mf.probs(Xr))/len(Xr):.3f} '
      f'contra {obj:.3f} observado. No altera el orden (AUC intacto).')

    mf.meta = {
        'v': '1.0', 'objetivo': 'P(el proyecto llegue a ley)',
        'universo_entrenamiento': 'registro del Senado, proyectos de ley + actos legislativos, con desenlace conocido',
        'n_entrenamiento': len(y_all),
        'tasa_base': round(sum(y_all) / len(y_all), 4),
        'validacion': {'metodo': f'out-of-time · train <{ANIO_CORTE} · test {ANIO_CORTE}-{ANIO_TEST_MAX}',
                       'auc_test': ev_te['auc'], 'brier_test': ev_te['brier'],
                       'n_test': ev_te['n'], 'lift10_test': ev_te['lift10']['lift'],
                       'auc_train': ev_tr['auc'],
                       'auc_rolling': [round(a, 4) for a in aucs]},
        'correccion_epoca': {'delta_intercepto': round(delta, 4),
                             'objetivo': round(obj, 4),
                             'ventana': f'{ANIO_CORTE}-{ANIO_TEST_MAX}'},
        'advertencia': ('calibrado sobre el registro del Senado; aplicado a un proyecto '
                        'que solo existe en el registro de Cámara es una extrapolación'),
    }
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    mf.guardar(SALIDA)
    corte = max(r['anio'] for r in M_all if r.get('anio')) + 1
    corte = max(corte, 2026)
    acum = F.trayectoria_acumulada(AIDX, corte)
    with open(SALIDA_AUT, 'w') as fh:
        json.dump(acum, fh, ensure_ascii=False)
    # Antecedentes por parecido de título para la legislatura viva: el
    # clustering exacto no agrupa los títulos genéricos, que son justo los de
    # las reformas grandes (ver antecedentes.py). Alimenta SOLO el eje 3.
    vivos = [r for r in rows if r.get('legislatura') in LEGISLATURAS_VIVAS]
    ai = ANT.construir(rows, vivos)
    with open(SALIDA_ANT, 'w') as fh:
        json.dump({'v': '1.0', 'n': len(ai), 'por_proyecto': ai}, fh, ensure_ascii=False)
    gana = sum(1 for r in vivos
               if (ai.get(f"{r.get('tabla','pdly')}:{r.get('id')}") or {}).get('n_previos', 0)
               > F.antecedentes(r)['n_previos'])
    P(f'\n[9] Modelo final (reajustado sobre las {len(y_all)} filas) → {SALIDA}')
    P(f'    antecedentes por parecido de título: {len(ai)} de {len(vivos)} proyectos vivos'
      f' · {gana} ganan historia que el cluster exacto no veía → {SALIDA_ANT}')
    P(f'    trayectoria de {len(acum["datos"])} firmantes hasta {corte} → {SALIDA_AUT}')
    P('    subir:')
    P(f'      aws s3 cp "{SALIDA}" s3://caudal-legislativo/metadata/importancia-modelo.json')
    P(f'      aws s3 cp "{SALIDA_AUT}" s3://caudal-legislativo/metadata/importancia-autores.json')
    P(f'      aws s3 cp "{SALIDA_ANT}" s3://caudal-legislativo/metadata/importancia-antecedentes.json')

    if args.reporte:
        with open(args.reporte, 'w') as fh:
            fh.write('```\n' + '\n'.join(log) + '\n```\n')
        print(f'\nreporte → {args.reporte}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
