"""Actores que se siguen en las reformas tributarias 2016-2026 y las ventanas de cada reforma.

Un titular cuenta para un actor solo si uno de sus alias aparece LITERAL en el titular.
Los alias en mayúscula se buscan respetando mayúsculas (ANDI no debe casar «andina»)."""
import re

REFORMAS = [  # id, nombre corto, términos de búsqueda, ventana (10 días antes de radicar → 3 después del final)
    ('r2016', 'Reforma estructural 2016', ['"reforma tributaria"'], '2016-10-09', '2017-01-02'),
    ('r2018', 'Ley de Financiamiento 2018', ['"ley de financiamiento"', '"reforma tributaria"'], '2018-10-20', '2019-01-02'),
    ('r2019', 'Ley de Crecimiento 2019', ['"ley de crecimiento"', '"reforma tributaria"'], '2019-10-12', '2019-12-31'),
    ('r2021a', 'Solidaridad Sostenible 2021', ['"reforma tributaria"', '"solidaridad sostenible"'], '2021-04-05', '2021-05-06'),
    ('r2021b', 'Inversión Social 2021', ['"reforma tributaria"', '"inversión social"'], '2021-07-10', '2021-09-18'),
    ('r2022', 'Reforma de 2022', ['"reforma tributaria"'], '2022-07-28', '2022-12-17'),
    ('r2024', 'Ley de Financiamiento 2024', ['"ley de financiamiento"', '"reforma tributaria"'], '2024-09-01', '2024-12-15'),
    ('r2025', 'Ley de Financiamiento 2025', ['"ley de financiamiento"', '"reforma tributaria"'], '2025-08-22', '2025-12-13'),
]

# id, nombre, grupo (gre: gremio · sin: sindicato · cen: centro de pensamiento · par: partido), alias, consulta
ACTORES = [
    ('andi', 'ANDI', 'gre', [r'\bANDI\b', r'\bAndi\b', r'Mac ?Master', r'McMaster'], 'ANDI'),
    ('fenalco', 'Fenalco', 'gre', [r'\bFenalco\b', r'\bFENALCO\b'], 'Fenalco'),
    ('anif', 'Anif', 'cen', [r'\bAnif\b', r'\bANIF\b'], 'Anif'),
    ('fedesarrollo', 'Fedesarrollo', 'cen', [r'\bFedesarrollo\b'], 'Fedesarrollo'),
    ('asobancaria', 'Asobancaria', 'gre', [r'\bAsobancaria\b', r'\bbanqueros\b'], 'Asobancaria'),
    ('consejo-gremial', 'Consejo Gremial', 'gre', [r'Consejo Gremial'], '"Consejo Gremial"'),
    ('camacol', 'Camacol', 'gre', [r'\bCamacol\b', r'\bCAMACOL\b', r'constructores'], 'Camacol'),
    ('sac', 'SAC', 'gre', [r'\bSAC\b', r'Sociedad de Agricultores'], '"Sociedad de Agricultores" OR SAC'),
    ('acopi', 'Acopi', 'gre', [r'\bAcopi\b', r'\bACOPI\b'], 'Acopi'),
    ('cafeteros', 'Cafeteros', 'gre', [r'[Cc]afeteros', r'Fedecaf[eé]'], 'cafeteros'),
    ('cotelco', 'Cotelco', 'gre', [r'\bCotelco\b', r'\bhoteleros\b'], 'Cotelco'),
    ('andesco', 'Andesco', 'gre', [r'\bAndesco\b'], 'Andesco'),
    ('fecoljuegos', 'Fecoljuegos', 'gre', [r'\bFecoljuegos\b'], 'Fecoljuegos'),
    ('asocana', 'Asocaña', 'gre', [r'\bAsocaña\b'], 'Asocaña'),
    ('fasecolda', 'Fasecolda', 'gre', [r'\bFasecolda\b'], 'Fasecolda'),
    ('asofondos', 'Asofondos', 'gre', [r'\bAsofondos\b'], 'Asofondos'),
    ('analdex', 'Analdex', 'gre', [r'\bAnaldex\b', r'exportadores'], 'Analdex'),
    ('fedegan', 'Fedegán', 'gre', [r'\bFedeg[aá]n\b', r'ganaderos'], 'Fedegán'),
    ('fenavi', 'Fenavi', 'gre', [r'\bFenavi\b', r'avicultores'], 'Fenavi'),
    ('anato', 'Anato', 'gre', [r'\bAnato\b', r'\bANATO\b'], 'Anato'),
    ('amcham', 'AmCham', 'gre', [r'\bAmCham\b'], 'AmCham'),
    ('confecamaras', 'Confecámaras', 'gre', [r'Confec[aá]maras'], 'Confecámaras'),
    ('cut', 'CUT', 'sin', [r'\bCUT\b', r'Central Unitaria'], 'CUT Colombia'),
    ('cgt', 'CGT', 'sin', [r'\bCGT\b'], 'CGT Colombia'),
    ('fecode', 'Fecode', 'sin', [r'\bFecode\b', r'\bFECODE\b'], 'Fecode'),
    ('cd', 'Centro Democrático', 'par', [r'Centro Democr[aá]tico', r'\buribismo\b', r'\buribistas?\b'], '"Centro Democrático"'),
    ('lib', 'Partido Liberal', 'par', [r'Partido Liberal', r'\bliberales\b', r'\bliberalismo\b'], '"Partido Liberal" OR liberales'),
    ('con', 'Partido Conservador', 'par', [r'Partido Conservador', r'\bconservadores\b', r'\bconservatismo\b'], '"Partido Conservador" OR conservadores'),
    ('cr', 'Cambio Radical', 'par', [r'Cambio Radical'], '"Cambio Radical"'),
    ('u', 'La U', 'par', [r'Partido de la U\b', r'\bLa U\b', r'Partido de La U'], '"Partido de la U"'),
    ('verde', 'Alianza Verde', 'par', [r'Alianza Verde', r'\bverdes\b'], '"Alianza Verde"'),
    ('pacto', 'Pacto Histórico', 'par', [r'Pacto Hist[oó]rico', r'\bpetrismo\b'], '"Pacto Histórico"'),
    ('polo', 'Polo Democrático', 'par', [r'Polo Democr[aá]tico', r'\bel Polo\b'], '"Polo Democrático"'),
    ('mira', 'MIRA', 'par', [r'\bMIRA\b'], 'MIRA partido'),
]
RX = {a[0]: re.compile('|'.join(a[3])) for a in ACTORES}

def actores_en(titulo):
    return [a[0] for a in ACTORES if RX[a[0]].search(titulo)]
