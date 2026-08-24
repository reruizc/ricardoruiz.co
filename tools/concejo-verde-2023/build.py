#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis electoral 1V 2026 + cruce con el Concejo de Bogotá 2023 (Alianza Verde).

Toma el voto por mesa de dos concejales del Partido Verde elegidos en 2023:
  - RONALD FELIPE VARGAS SANCHEZ  (COD_CAN 13)
  - JULIAN ESPINOSA ORTIZ         (COD_CAN  2)
lo agrega a barrio catastral por el mapa puesto->barrio (PIP) ya construido, y lo
cruza con el resultado presidencial 1V 2026 por barrio (Cepeda vs Abelardo).

Salidas:
  concejo-verde-2023/data.json          -> cifras que consume el deck
  concejo-verde-2023/img/m_*.png        -> mapas por barrio (estilo informe, Inter)

Insumo crudo (local, NO en repo): GCS_2023TER.csv. Se pre-extrae a /tmp con:
  awk -F';' '$7=="16" && ($15=="RONALD FELIPE VARGAS SANCHEZ" || $15=="JULIAN ESPINOSA ORTIZ"){print $9";"$10";"$11";"$14";"$15";"$16}' \
    "Bases de datos/FINAL SUBIDA GCS/GCS_2023TER.csv" > /tmp/concejo2023_verde.csv
El script regenera ese archivo si falta.
"""
import csv, json, os, subprocess, sys, collections, unicodedata, warnings
warnings.filterwarnings('ignore')

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)

GCS      = 'Bases de datos/FINAL SUBIDA GCS/GCS_2023TER.csv'
TMP      = '/tmp/concejo2023_verde.csv'
PIP_MAP  = 'Bases de datos/output_trasvase/bog-puesto-to-barrio-pip.json'
B26      = 'Bases de datos/output_trasvase/bogota-1v-por-barrio.json'
GEOJSON  = 'Bases de datos/output_pacto_1v_2026/geo/BOG-BARRIOS-CATASTRALES.json'
OUTDIR   = 'concejo-verde-2023'
IMGDIR   = f'{OUTDIR}/img'
os.makedirs(IMGDIR, exist_ok=True)

CANDS = {
    'RONALD FELIPE VARGAS SANCHEZ': {'slug': 'ronald', 'nombre': 'Ronald Vargas',
        'full': 'Ronald Felipe Vargas Sánchez'},
    'JULIAN ESPINOSA ORTIZ': {'slug': 'julian', 'nombre': 'Julián Espinosa',
        'full': 'Julián Espinosa Ortiz'},
}

def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFD', str(s).upper().strip())
                   if unicodedata.category(c) != 'Mn')

# ----------------------------------------------------------------------------- extracción cruda
def ensure_tmp():
    if os.path.exists(TMP) and os.path.getsize(TMP) > 0:
        return
    print('· extrayendo del GCS 2023 (una pasada al CSV de ~2GB)…', file=sys.stderr)
    awk = (r'$7=="16" && ($15=="RONALD FELIPE VARGAS SANCHEZ" || $15=="JULIAN ESPINOSA ORTIZ")'
           r'{print $9";"$10";"$11";"$14";"$15";"$16}')
    with open(TMP, 'w') as out:
        subprocess.run(['awk', '-F;', awk, GCS], stdout=out, check=True)

# ----------------------------------------------------------------------------- agregación a barrio
def aggregate():
    pip = json.load(open(PIP_MAP))
    agg = {c['slug']: collections.Counter() for c in CANDS.values()}
    tot = collections.Counter(); matched = collections.Counter()
    for row in csv.reader(open(TMP), delimiter=';'):
        if len(row) < 6:
            continue
        z, p, mesa, cc, name, v = row
        meta = CANDS.get(name)
        if not meta:
            continue
        slug = meta['slug']; v = int(v); tot[slug] += v
        try:
            key = f"{int(z):02d}-{int(p):02d}"
        except ValueError:
            continue
        bc = pip.get(key)
        if not bc:
            continue
        agg[slug][bc] += v; matched[slug] += v
    return agg, tot, matched

# ----------------------------------------------------------------------------- cruce 2023 -> 2026
def cross(agg, tot, matched):
    b26 = json.load(open(B26))
    CITY_ce = sum(d['ce'] for d in b26.values())
    CITY_ab = sum(d['ab'] for d in b26.values())
    CITY_urna = sum(d['urna'] for d in b26.values())
    barrios_won = collections.Counter(d['win'] for d in b26.values())
    city = {
        'ce_pct': round(100*CITY_ce/CITY_urna, 1),
        'ab_pct': round(100*CITY_ab/CITY_urna, 1),
        'h2h_ce': round(100*CITY_ce/(CITY_ce+CITY_ab), 1),
        'barrios_ce': barrios_won['Cepeda'], 'barrios_ab': barrios_won['Abelardo'],
        'n_barrios': len(b26),
    }
    out = {}
    for meta in CANDS.values():
        slug = meta['slug']; a = agg[slug]
        vtot = sum(a.values())
        in_ce = in_ab = in_otro = 0
        wce = wab = wbase = 0.0; wh = wht = 0.0
        loc = collections.Counter()
        rows = []
        for bc, v in a.items():
            d = b26.get(bc)
            if not d:
                continue
            win = d['win']
            if win == 'Cepeda':   in_ce += v
            elif win == 'Abelardo': in_ab += v
            else: in_otro += v
            wce += v*d['ce']; wab += v*d['ab']; wbase += v*d['urna']
            if d['ce']+d['ab'] > 0:
                wh += v*d['ce']/(d['ce']+d['ab']); wht += v
            loc[d['loc']] += v
            rows.append((v, d['n'], d['loc'], win, d['winpct'], d['ce'], d['ab']))
        cov = in_ce+in_ab+in_otro
        rows.sort(reverse=True)
        out[slug] = {
            'nombre': meta['nombre'], 'full': meta['full'],
            'votos': tot[slug], 'votos_barrio': matched[slug], 'barrios': len(a),
            'cobertura': round(100*matched[slug]/tot[slug], 1),
            'pct_en_ce': round(100*in_ce/cov, 1), 'pct_en_ab': round(100*in_ab/cov, 1),
            'w_ce': round(100*wce/wbase, 1), 'w_ab': round(100*wab/wbase, 1),
            'h2h_ce': round(100*wh/wht, 1),
            'd_ce': round(100*wce/wbase - city['ce_pct'], 1),
            'd_ab': round(100*wab/wbase - city['ab_pct'], 1),
            'top_loc': [{'loc': k.title(), 'votos': n} for k, n in loc.most_common(6)],
            'top_barrios': [{'n': n, 'loc': l.title(), 'votos': v, 'win': w, 'winpct': wp,
                             'ce': ce, 'ab': ab}
                            for (v, n, l, w, wp, ce, ab) in rows[:10]],
        }
    return out, city, b26

# ----------------------------------------------------------------------------- mapas
def render_maps(agg, b26):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.colors import LinearSegmentedColormap, PowerNorm, Normalize
    from matplotlib.patches import Patch
    import matplotlib.patheffects as pe
    import geopandas as gpd

    for _f in ('Inter-Regular.ttf', 'Inter-Bold.ttf', 'Inter-Italic.ttf'):
        try: font_manager.fontManager.addfont(f'tools/pacto-1v-2026/fonts/{_f}')
        except Exception: pass
    plt.rcParams['font.family'] = 'Inter'

    PAPER='#faf8f2'; INK='#1a1510'; INK2='#6b6354'; GREY='#d7d1c2'
    OX='#8a1e16'
    CM_VERDE = LinearSegmentedColormap.from_list('vd', ['#e8efe6','#a7cf9c','#4f9e5b','#1c6b39'])
    CM_CEP   = LinearSegmentedColormap.from_list('ce', ['#efeaf4','#c0aede','#8f63bd','#54278f'])
    CM_AB    = LinearSegmentedColormap.from_list('ab', ['#e9ecf5','#9fa9cf','#5161a3','#16166b'])
    PURP='#6a3d9a'; ROYAL='#1f47cc'

    geo = gpd.read_file(GEOJSON)[['codigo', 'nombre', 'loc_nombre', 'geometry']].to_crs('EPSG:4326')
    # rotación 90° izquierda (convención Bogotá del proyecto), origen común a toda la ciudad
    minx, miny, maxx, maxy = geo.total_bounds
    origin = ((minx+maxx)/2, (miny+maxy)/2)
    geo['geometry'] = geo.geometry.rotate(90, origin=origin)

    def frame(ax, g):
        mnx, mny, mxx, mxy = g.total_bounds
        px = (mxx-mnx)*0.04; py = (mxy-mny)*0.04
        ax.set_xlim(mnx-px, mxx+px); ax.set_ylim(mny-py, mxy+py*2.6)
        ax.set_axis_off(); ax.set_aspect('equal')

    def titles(ax, t, s):
        ax.text(0.0, 1.105, t, transform=ax.transAxes, fontsize=15, fontweight='bold', color=INK, va='top')
        ax.text(0.0, 1.04, s, transform=ax.transAxes, fontsize=9.2, color=INK2, va='top')

    # ---- 1) referencia: ganador 2026 por barrio (Cepeda vs Abelardo)
    g = geo.copy()
    g['win'] = g['codigo'].map(lambda c: (b26.get(c) or {}).get('win'))
    g['mg'] = g['codigo'].map(lambda c: (b26.get(c) or {}).get('winpct'))
    fig, ax = plt.subplots(figsize=(7.4, 5.6)); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    g[g['win'].isna()].plot(ax=ax, color=GREY, edgecolor='white', linewidth=0.18)
    for win, cm in (('Cepeda', CM_CEP), ('Abelardo', CM_AB)):
        sub = g[g['win'] == win]
        if len(sub): sub.plot(ax=ax, column='mg', cmap=cm, norm=Normalize(35, 70),
                              edgecolor='white', linewidth=0.18)
    other = g[(~g['win'].isna()) & (~g['win'].isin(['Cepeda', 'Abelardo']))]
    if len(other): other.plot(ax=ax, color='#c9a227', edgecolor='white', linewidth=0.18)
    frame(ax, g)
    titles(ax, 'Bogotá 2026: quién ganó cada barrio',
            'Presidencial 1ª vuelta · morado = Cepeda · azul = Abelardo · norte a la izquierda')
    ax.legend(handles=[Patch(facecolor=PURP, label='Gana Cepeda (435 barrios)'),
                       Patch(facecolor=ROYAL, label='Gana Abelardo (223 barrios)')],
              loc='lower left', frameon=False, fontsize=8.6, bbox_to_anchor=(0.0, 0.0))
    fig.text(0.012, 0.02, 'Fuente: preconteo Registraduría 1V 2026 agregado a barrio catastral (cruce punto-en-polígono).',
             fontsize=6.4, color=INK2)
    plt.savefig(f'{IMGDIR}/m_bogota_barrio_winner.png', dpi=180, facecolor=PAPER, bbox_inches='tight'); plt.close()
    print('✓ m_bogota_barrio_winner.png')

    # ---- 2) concentración del voto del concejal (verde)
    def concentracion(slug, nombre, fname):
        a = agg[slug]
        g = geo.copy(); g['v'] = g['codigo'].map(lambda c: a.get(c, 0))
        vmax = sorted(v for v in a.values())[int(len(a)*0.97)] if a else 1
        fig, ax = plt.subplots(figsize=(7.4, 5.6)); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
        g[g['v'] == 0].plot(ax=ax, color=GREY, edgecolor='white', linewidth=0.18)
        sub = g[g['v'] > 0]
        sub.plot(ax=ax, column='v', cmap=CM_VERDE, norm=PowerNorm(0.55, 0, vmax),
                 edgecolor='white', linewidth=0.18)
        # etiqueta los 6 barrios más fuertes
        top = sorted(a.items(), key=lambda kv: -kv[1])[:6]
        for bc, v in top:
            row = g[g['codigo'] == bc]
            if not len(row): continue
            c = row.geometry.iloc[0].representative_point()
            nm = (b26.get(bc) or {}).get('n', '')
            t = ax.annotate(nm, (c.x, c.y), fontsize=5.3, color=INK, ha='center', va='center', fontweight='bold')
            t.set_path_effects([pe.withStroke(linewidth=1.5, foreground=PAPER)])
        frame(ax, g)
        titles(ax, f'Dónde votaron por {nombre} (Verde, Concejo 2023)',
                'Voto por barrio · verde más intenso = más votos · norte a la izquierda')
        sm = plt.cm.ScalarMappable(cmap=CM_VERDE, norm=PowerNorm(0.55, 0, vmax)); sm.set_array([])
        cax = fig.add_axes([0.89, 0.16, 0.020, 0.30]); cb = fig.colorbar(sm, cax=cax); cb.outline.set_visible(False)
        cb.ax.tick_params(labelsize=7, colors=INK2, length=2); cb.set_label('votos 2023', fontsize=7.6, color=INK2)
        cb.ax.yaxis.set_label_position('left')
        fig.text(0.012, 0.02, 'Fuente: escrutinio Concejo de Bogotá 2023 por mesa (Registraduría/GCS) agregado a barrio catastral.',
                 fontsize=6.4, color=INK2)
        plt.savefig(f'{IMGDIR}/{fname}', dpi=180, facecolor=PAPER, bbox_inches='tight'); plt.close()
        print('✓', fname)

    # ---- 3) cruce: el footprint del concejal coloreado por quién ganó ese barrio en 2026
    def cruce(slug, nombre, fname):
        a = agg[slug]
        g = geo.copy()
        g['v'] = g['codigo'].map(lambda c: a.get(c, 0))
        g['win'] = g['codigo'].map(lambda c: (b26.get(c) or {}).get('win'))
        vmax = sorted(v for v in a.values())[int(len(a)*0.97)] if a else 1
        n = PowerNorm(0.55, 0, vmax)
        fig, ax = plt.subplots(figsize=(7.4, 5.6)); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
        g[g['v'] == 0].plot(ax=ax, color=GREY, edgecolor='white', linewidth=0.18)
        for win, cm in (('Cepeda', CM_CEP), ('Abelardo', CM_AB)):
            sub = g[(g['v'] > 0) & (g['win'] == win)]
            if len(sub): sub.plot(ax=ax, column='v', cmap=cm, norm=n, edgecolor='white', linewidth=0.18)
        oth = g[(g['v'] > 0) & (~g['win'].isin(['Cepeda', 'Abelardo'])) & (~g['win'].isna())]
        if len(oth): oth.plot(ax=ax, color='#c9a227', edgecolor='white', linewidth=0.18)
        frame(ax, g)
        titles(ax, f'El voto de {nombre}, coloreado por quién ganó ese barrio en 2026',
                'Morado = barrio que ganó Cepeda · azul = ganó Abelardo · intensidad = voto Verde 2023')
        ax.legend(handles=[Patch(facecolor=PURP, label='Barrio que ganó Cepeda 2026'),
                           Patch(facecolor=ROYAL, label='Barrio que ganó Abelardo 2026')],
                  loc='lower left', frameon=False, fontsize=8.4, bbox_to_anchor=(0.0, 0.0))
        fig.text(0.012, 0.02, 'Voto Concejo 2023 por barrio (Verde) sobre el ganador presidencial 1V 2026 del mismo barrio.',
                 fontsize=6.4, color=INK2)
        plt.savefig(f'{IMGDIR}/{fname}', dpi=180, facecolor=PAPER, bbox_inches='tight'); plt.close()
        print('✓', fname)

    concentracion('ronald', 'Ronald Vargas', 'm_ronald_barrio.png')
    cruce('ronald', 'Ronald Vargas', 'm_ronald_cross.png')
    concentracion('julian', 'Julián Espinosa', 'm_julian_barrio.png')
    cruce('julian', 'Julián Espinosa', 'm_julian_cross.png')

# ----------------------------------------------------------------------------- main
def main():
    ensure_tmp()
    agg, tot, matched = aggregate()
    data, city, b26 = cross(agg, tot, matched)
    payload = {'v': '2026-06-17', 'city': city, 'cands': data}
    json.dump(payload, open(f'{OUTDIR}/data.json', 'w'), ensure_ascii=False, indent=1)
    print('✓ data.json')
    for slug, d in data.items():
        print(f"  {d['nombre']:18} votos={d['votos']:6} cob={d['cobertura']}% | "
              f"en barrios Cepeda {d['pct_en_ce']}% / Abelardo {d['pct_en_ab']}% | "
              f"intención 2026 Cep {d['w_ce']} ({d['d_ce']:+}) Abe {d['w_ab']} ({d['d_ab']:+})")
    render_maps(agg, b26)

if __name__ == '__main__':
    main()
