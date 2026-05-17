#!/usr/bin/env python3
"""
Corrección retroactiva de las opciones de Pertenencia (P*e) en el banco
mainstream. Diversifica los vehículos de "yo y los míos" según el lente
del candidato, evitando el sesgo "región-vs-Bogotá" en los casos donde
no aplica.

Mapeo de vehículos por candidato:
- ic Cepeda     : comunidades populares, organizaciones sociales
- ae Abelardo   : gente del común, comerciantes, pequeño empresariado
- pv Paloma     : gremios productivos, sectores que sostienen al país
- cl Claudia    : ciudades capitales, profesionales urbanos, localidades
- sf Fajardo    : clase media educada, maestros, profesionales académicos
- rb Roy        : regiones del posconflicto, víctimas (se conserva)
"""

import json
from pathlib import Path

JSON_PATH = Path(__file__).resolve().parents[2] / "Bases de datos" / "test-presidencial" / "preguntas.json"

# Reemplazo total por pregunta/opción y candidato/registro.
# Solo tocamos las opciones de arquetipo "pertenencia" en P1-P8.
# Cepeda, Roy y Claudia se mantienen mayormente; Abelardo, Paloma y Fajardo
# se reescriben para diversificar el vehículo.

NUEVO = {
    "P1": {  # Emoción dominante
        "ic": {
            "popular": "Orgullo por mi gente y mi comunidad. Los sectores populares por fin dejaron de ser invisibles en este gobierno.",
            "digital": "Orgullo. Mi gente y mi comunidad por fin dejaron de ser invisibles. Eso no se devuelve fácil.",
            "analitico": "Orgullo por mi comunidad y por los sectores populares que el cambio buscó visibilizar tras décadas de exclusión.",
        },
        "ae": {
            "popular": "Orgullo por mi gente: los trabajadores, los del rebusque, los pequeños comerciantes que ningún gobierno representa.",
            "digital": "Orgullo por mi gente. Los del común, los del rebusque, los pequeños comerciantes. Nadie los representa de verdad.",
            "analitico": "Orgullo por la gente trabajadora y los pequeños comerciantes que ningún gobierno ha sabido representar bien.",
        },
        "pv": {
            "popular": "Orgullo por mi gremio y los sectores productivos que sostienen al país, a los que este gobierno trata como enemigos.",
            "digital": "Orgullo por mi gremio productivo. Sostenemos al país y el gobierno nos trata como enemigos. 🤬",
            "analitico": "Orgullo por mi gremio y los sectores productivos que sostienen al país, frente a un gobierno que los trata como adversario ideológico.",
        },
        "cl": {
            "popular": "Orgullo por mi ciudad y mi localidad. La política nacional rara vez nos pone atención de verdad.",
            "digital": "Orgullo por mi ciudad y mi localidad. La política nacional nos ignora aunque aquí se decida casi todo.",
            "analitico": "Orgullo por mi ciudad capital y mi localidad, frente a una política nacional que suele invisibilizar la realidad urbana.",
        },
        "sf": {
            "popular": "Apego a mi comunidad y a mi gente, sin caer en eso de cada quien para su lado.",
            "digital": "Apego a mi comunidad y a mi gente. Sin caer en regionalismos ni en sectarismos identitarios.",
            "analitico": "Apego a mi comunidad y a mi gente, sin caer en regionalismos ni en sectarismos identitarios.",
        },
        "rb": {
            "popular": "Apego a mi territorio, donde la paz se vive y se entiende de verdad.",
            "digital": "Apego a mi territorio. La paz se entiende aquí, no en los trinos de los políticos.",
            "analitico": "Apego a mi territorio y a las comunidades que han hecho la paz desde la cotidianidad, no desde los discursos.",
        },
    },
    "P2": {  # Miedo dominante
        "ic": {
            "popular": "Que las comunidades populares vuelvan a quedar invisibles para el próximo gobierno.",
            "digital": "Que las comunidades populares vuelvan a ser invisibles. Que ningún noticiero las cubra otra vez.",
            "analitico": "Que las comunidades populares y los sectores históricamente excluidos vuelvan a quedar invisibilizados.",
        },
        "ae": {
            "popular": "Que mi gente —los trabajadores, los pequeños comerciantes— sigan siendo solo votos para campaña y nada más.",
            "digital": "Que mi gente trabajadora siga siendo solo votos para campaña. Los visitan, prometen, ganan, se olvidan.",
            "analitico": "Que la gente trabajadora y los pequeños comerciantes sigan siendo tratados como botín electoral, sin políticas reales.",
        },
        "pv": {
            "popular": "Que mi gremio y los sectores productivos sigan siendo tratados como sospechosos por un gobierno ideologizado.",
            "digital": "Que mi gremio productivo siga siendo tratado como enemigo del gobierno. Cero respeto a quien sostiene el país.",
            "analitico": "Que los gremios y sectores productivos sigan siendo tratados como adversarios ideológicos del gobierno de turno.",
        },
        "cl": {
            "popular": "Que mi ciudad y mi localidad sigan pagando todo y recibiendo poca atención en las decisiones de fondo.",
            "digital": "Que mi ciudad capital y mi localidad sigamos pagando todo y decidiendo nada. Cansancio nivel histórico.",
            "analitico": "Que las ciudades capitales y sus localidades sigan siendo subestimadas en las decisiones de fondo del país.",
        },
        "sf": {
            "popular": "Que los profesionales y la clase media educada nos quedemos sin representación política seria.",
            "digital": "Que los profesionales y la clase media educada quedemos sin representación seria. Atrapados entre extremos.",
            "analitico": "Que los profesionales y la clase media educada queden sin representación política seria, atrapados entre extremos.",
        },
        "rb": {
            "popular": "Que las regiones más golpeadas por la guerra vuelvan a quedar fuera del mapa.",
            "digital": "Que las regiones golpeadas por la guerra vuelvan a ser invisibles. Cero memoria.",
            "analitico": "Que las regiones más golpeadas por el conflicto vuelvan a quedar fuera del mapa político.",
        },
    },
    "P3": {  # Visión del Estado
        "ic": {
            "popular": "Para reconocer la diversidad y darle voz real a las comunidades que siempre han estado por fuera.",
            "digital": "Para darle voz real a las comunidades históricamente excluidas. No más invisibles.",
            "analitico": "Para reconocer la diversidad social y dar voz real a las comunidades históricamente excluidas.",
        },
        "ae": {
            "popular": "Para respetar a la gente que trabaja y produce, sin que les impongan ideología desde el centro político.",
            "digital": "Para respetar a la gente que trabaja y produce. Sin imposiciones ideológicas de campaña.",
            "analitico": "Para respetar a la gente trabajadora y al pequeño empresariado, sin imposición ideológica desde el centro político.",
        },
        "pv": {
            "popular": "Para respetar a los gremios productivos y a los sectores que sostienen al país, frente al ideologismo del gobierno.",
            "digital": "Para respetar a los gremios productivos. Frente al ideologismo del gobierno actual que los persigue.",
            "analitico": "Para respetar la autonomía de los gremios productivos y los sectores que sostienen la economía del país.",
        },
        "cl": {
            "popular": "Para descentralizar decisiones y reconocer que las grandes ciudades tienen su propia realidad y necesidades.",
            "digital": "Para descentralizar decisiones. Las ciudades capitales tienen una realidad propia que el nivel nacional ignora.",
            "analitico": "Para descentralizar decisiones y reconocer la diversidad de las ciudades capitales y sus localidades.",
        },
        "sf": {
            "popular": "Para reconocer a las comunidades educadas, profesionales y de clase media, sin caer en sectarismos.",
            "digital": "Para reconocer a las comunidades educadas y de clase media. Sin caer en sectarismos identitarios.",
            "analitico": "Para reconocer a la clase media educada y a las comunidades profesionales, sin caer en sectarismos identitarios.",
        },
        "rb": {
            "popular": "Para reconocer a las comunidades del posconflicto como protagonistas de la paz, no como periferia.",
            "digital": "Para que las comunidades del posconflicto sean protagonistas de la paz, no periferia administrativa olvidada.",
            "analitico": "Para reconocer a las comunidades del posconflicto como protagonistas de la paz, no como periferia administrativa.",
        },
    },
    "P5": {  # Disposición al cambio de bloque
        "ic": {
            "popular": "Voto por el que mejor represente a las comunidades populares y a la gente que siempre se ha quedado por fuera.",
            "digital": "Voto por quien represente a las comunidades populares. A los que siempre se quedan por fuera.",
            "analitico": "Voto por quien mejor represente a las comunidades populares y a los sectores históricamente postergados.",
        },
        "ae": {
            "popular": "Voto por el que mejor represente a mi gente: trabajadores, comerciantes, pequeño empresariado. El partido es lo de menos.",
            "digital": "Voto por quien represente a mi gente: trabajadores, comerciantes, pequeño empresariado. El partido importa poco.",
            "analitico": "Voto por quien mejor represente a la gente trabajadora y al pequeño empresariado, sin importar el partido.",
        },
        "pv": {
            "popular": "Voto por el que defienda a los gremios productivos y a los sectores que sostienen al país frente al ideologismo.",
            "digital": "Voto por quien defienda a los gremios productivos. Frente al ideologismo del gobierno actual.",
            "analitico": "Voto por quien represente con seriedad a los gremios productivos y a los sectores que sostienen la economía.",
        },
        "cl": {
            "popular": "Voto por el que entienda y represente la realidad de las grandes ciudades y de sus localidades.",
            "digital": "Voto por quien entienda la realidad urbana de las grandes ciudades y de sus localidades.",
            "analitico": "Voto por quien mejor represente a las ciudades capitales y la realidad urbana de sus localidades.",
        },
        "sf": {
            "popular": "Voto por el que mejor represente a los profesionales y a la clase media educada, sin caer en clientelismos.",
            "digital": "Voto por quien represente a los profesionales y a la clase media educada. Sin caer en clientelismos.",
            "analitico": "Voto por quien mejor represente a los profesionales y a la clase media educada, sin caer en clientelismos.",
        },
        "rb": {
            "popular": "Voto por el que mejor represente a las comunidades del posconflicto y a la paz territorial.",
            "digital": "Voto por quien represente a las comunidades del posconflicto. Paz territorial, no de tarima.",
            "analitico": "Voto por quien mejor represente a las comunidades del posconflicto y a la promesa de la paz territorial.",
        },
    },
    "P6": {  # Lectura de la corrupción
        "ic": {
            "popular": "A las comunidades populares les roban más que a nadie. La UNGRD se llevó hasta el agua de La Guajira; Odebrecht acabó con la infraestructura del Caribe.",
            "digital": "A las comunidades populares les roban más. La UNGRD se llevó el agua de La Guajira; Odebrecht acabó con la infra del Caribe. Y nadie las defiende.",
            "analitico": "A las comunidades populares les roban más que al resto y nadie las defiende: la UNGRD se llevó hasta el agua de La Guajira mientras Odebrecht acabó con la infraestructura del Caribe.",
        },
        "ae": {
            "popular": "A los trabajadores y al pequeño empresariado nos roban dos veces: con impuestos y con la corrupción. UNGRD y Centros Poblados son la prueba.",
            "digital": "A los trabajadores y al pequeño empresariado nos roban dos veces: con impuestos y con la corrupción. UNGRD + Centros Poblados de prueba.",
            "analitico": "A la gente trabajadora y al pequeño empresariado les roban dos veces: con impuestos y con corrupción. UNGRD y Centros Poblados son ejemplo claro.",
        },
        "pv": {
            "popular": "A los gremios productivos los exprimen con impuestos y después les tiran migajas. El UNGRD demuestra cómo la plata se desvía hacia los aliados del gobierno.",
            "digital": "A los gremios productivos los exprimen con impuestos. Y la plata se desvía hacia los aliados del gobierno (UNGRD, Centros Poblados).",
            "analitico": "A los gremios productivos los saquean con cargas tributarias y luego desvían los recursos hacia aliados del gobierno; el caso UNGRD lo demuestra.",
        },
        "cl": {
            "popular": "A las ciudades capitales les exigen todo y las ignoran cuando se roban la plata. Del MinTIC al UNGRD, pagamos dos veces.",
            "digital": "A las ciudades capitales les exigen todo. Y las ignoran cuando se roban la plata. Del MinTIC al UNGRD: pagamos dos veces.",
            "analitico": "A las ciudades capitales se les exige más y se les ignora más cuando hay corrupción; del MinTIC al UNGRD, las ciudades siempre pagan dos veces.",
        },
        "sf": {
            "popular": "Los profesionales y la clase media educada pagan religiosamente impuestos mientras la corrupción —de Odebrecht al UNGRD— se los devora.",
            "digital": "Profesionales y clase media educada pagando impuestos religiosamente. Mientras la corrupción —Odebrecht al UNGRD— se los devora.",
            "analitico": "Los profesionales y la clase media educada pagan impuestos religiosamente mientras la corrupción nacional —de Odebrecht al UNGRD— erosiona el contrato social.",
        },
        "rb": {
            "popular": "A las comunidades golpeadas por la guerra les roban dos veces: con la violencia y con la plata del posconflicto. De OCAD-Paz para acá.",
            "digital": "Comunidades golpeadas por la guerra: les roban dos veces. La violencia primero, la plata del posconflicto después. De OCAD-Paz para acá.",
            "analitico": "A las comunidades afectadas por la guerra les roban dos veces: la violencia primero y la corrupción de la reparación después, desde OCAD-Paz hasta los recursos del posconflicto desviados.",
        },
    },
    "P7": {  # Autoimagen como votante
        "ic": {
            "popular": "Como alguien comprometido con su comunidad y con los sectores populares que siempre fueron las últimas en la fila.",
            "digital": "Como alguien comprometido con su comunidad. Y con los sectores populares que siempre fueron las últimas en la fila.",
            "analitico": "Como alguien comprometido con su comunidad y con los sectores populares históricamente postergados.",
        },
        "ae": {
            "popular": "Como alguien que representa a su gente —trabajadores, comerciantes, pequeño empresariado—, no a las élites del poder.",
            "digital": "Como alguien que representa a su gente: trabajadores, comerciantes, pequeño empresariado. No a las élites del poder.",
            "analitico": "Como alguien que representa a la gente trabajadora y al pequeño empresariado, no a las élites del poder central.",
        },
        "pv": {
            "popular": "Como alguien que representa a los gremios productivos y a los sectores que sostienen al país, frente al ideologismo.",
            "digital": "Como alguien que representa a los gremios productivos. Y a los sectores que sostienen al país, frente al ideologismo del gobierno.",
            "analitico": "Como alguien que representa a los gremios productivos y a los sectores que sostienen al país frente al ideologismo del gobierno.",
        },
        "cl": {
            "popular": "Como alguien que representa la realidad de su ciudad y de su localidad, y exige decisiones acordes.",
            "digital": "Como alguien que representa la realidad de su ciudad capital. Y de su localidad, exigiendo decisiones acordes.",
            "analitico": "Como alguien que representa la realidad urbana de su ciudad y su localidad, exigiendo decisiones acordes a esa diversidad.",
        },
        "sf": {
            "popular": "Como alguien arraigado a su comunidad educada y profesional, sin caer en sectarismos identitarios.",
            "digital": "Como alguien arraigado a su comunidad educada y profesional. Sin caer en sectarismos identitarios.",
            "analitico": "Como alguien arraigado a su comunidad profesional y educada, abierto al diálogo y sin sectarismos identitarios.",
        },
        "rb": {
            "popular": "Como alguien arraigado a su territorio y comprometido con la paz desde adentro.",
            "digital": "Como alguien arraigado a su territorio. Y comprometido con la paz desde adentro, no desde un Excel.",
            "analitico": "Como alguien arraigado a su territorio y comprometido con la paz desde la realidad de quienes la viven.",
        },
    },
    "P8": {  # Balance del gobierno Petro
        "ic": {
            "popular": "Por primera vez un gobierno volteó a mirar a las comunidades populares y excluidas. Eso no se vuelve a ver fácil.",
            "digital": "Por primera vez las comunidades populares dejaron de ser invisibles. Eso no se devuelve aunque gane la derecha.",
            "analitico": "Por primera vez un gobierno volteó a mirar a las comunidades populares y a los sectores históricamente excluidos.",
        },
        "ae": {
            "popular": "Mi gente —los trabajadores, los del rebusque, los pequeños comerciantes— siguió invisible. Solo escuchada cuando hay campaña.",
            "digital": "Mi gente trabajadora siguió invisible. Solo escuchada en campaña. Y al día siguiente nada.",
            "analitico": "Mi gente —trabajadores, pequeños comerciantes, gente del común— siguió siendo invisible para el gobierno, solo escuchada en campaña.",
        },
        "pv": {
            "popular": "Los gremios productivos fueron tratados como enemigo ideológico durante todo el periodo. Cero respeto a quien sostiene el país.",
            "digital": "Los gremios productivos tratados como enemigo ideológico todo el periodo. Cero respeto a quien sostiene el país.",
            "analitico": "Los gremios productivos fueron tratados como adversarios ideológicos durante el periodo, no como sectores que sostienen la economía.",
        },
        "cl": {
            "popular": "Mi ciudad capital y mi localidad siguieron pagando todo sin recibir decisión real. Mucho discurso, poca gestión urbana.",
            "digital": "Mi ciudad capital y mi localidad pagaron todo y decidieron poco. Mucho discurso, poca gestión urbana real.",
            "analitico": "Las ciudades capitales y sus localidades siguieron pagando la mayor parte sin recibir decisión real sobre su propio destino.",
        },
        "sf": {
            "popular": "Los profesionales y la clase media educada quedamos huérfanos de representación seria en este periodo. Atrapados entre extremos.",
            "digital": "Los profesionales y la clase media educada quedamos huérfanos de representación seria. Atrapados entre extremos.",
            "analitico": "Los profesionales y la clase media educada quedaron sin representación política seria, atrapados entre los extremos del momento.",
        },
        "rb": {
            "popular": "Avance histórico en mirar a las comunidades del posconflicto. La paz territorial fue, con sus errores, una apuesta real.",
            "digital": "Avance histórico en mirar a las comunidades del posconflicto. La paz territorial fue, con sus errores, una apuesta real.",
            "analitico": "Un avance histórico en mirar a las comunidades del posconflicto; la paz territorial fue, con todos sus errores, una apuesta real.",
        },
    },
}


def main():
    d = json.load(open(JSON_PATH, encoding="utf-8"))
    cambios = 0
    for p in d["preguntas"]:
        pid = p["id"]
        if pid not in NUEVO:
            continue
        op = next((o for o in p["opciones"] if o.get("arquetipo") == "pertenencia"), None)
        if not op:
            continue
        for cand, regs in NUEVO[pid].items():
            for reg, texto in regs.items():
                if op["enunciados"].get(cand, {}).get(reg) != texto:
                    op["enunciados"].setdefault(cand, {})[reg] = texto
                    cambios += 1
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print(f"Cambios aplicados: {cambios}")
    return cambios


if __name__ == "__main__":
    main()
