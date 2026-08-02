#!/usr/bin/env python3
"""
Destila el corpus de sentencias T de salud en la TAXONOMÍA DE CAUSAS DE FRACASO
que alimenta el analizador de tutelas-salud.html (puerta 2: "¿está bien hecha?").

Entrada:  relatoria/corpus-salud.jsonl.gz  (harvest_relatoria.py)
Salidas:  relatoria/causas-fracaso.json    → taxonomía + frecuencia + citas reales
          relatoria/rag-pasajes.jsonl.gz   → pasajes citables para el RAG

LA IDEA: cada sentencia T narra por qué el juez de instancia negó. Agrupando
esos motivos por patrón sale la lista de "por esto se cae una tutela de salud",
con la sentencia que lo respalda — verificable, no inventada por un modelo.

REGLA DURA: cada causa se reporta con las sentencias REALES que la sustentan.
Nada de porcentajes sin denominador ni de causas sin cita. Es la diferencia
entre un dato defendible ante la SIC y una alucinación con formato bonito
(ver la nota de riesgo legal del proyecto).

Uso:
  python3 tools/tutela-analiza/analiza_corpus.py
  python3 tools/tutela-analiza/analiza_corpus.py --causa orden_medica   # ver citas
"""
import gzip
import json
import re
import sys
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "Bases de datos" / "tutelas-salud" / "relatoria"

# ── Taxonomía de causas de fracaso ────────────────────────────────────────────
# Derivada de leer los motivos del corpus. Cada patrón busca sobre el MOTIVO
# extraído (lo que argumentó el juez), no sobre el cuerpo completo.
CAUSAS = {
    "sin_orden_medica": {
        "titulo": "No hay orden del médico tratante",
        "explica": "El juez no ordena un servicio que ningún médico prescribió. "
                   "Es la causa más citada: sin la orden, el juez considera que no "
                   "hay derecho concreto que proteger.",
        # Incluye el fraseo "no ha sido autorizada por el galeno/médico adscrito",
        # que es la misma causa dicha de otra forma (visto en T-220/16).
        "rx": re.compile(r"(sin|falta de|no.{0,20}(existe|obra|allega|aport)).{0,40}"
                         r"(orden|prescripci[óo]n|f[óo]rmula).{0,30}m[ée]dic|"
                         r"m[ée]dico tratante.{0,60}(no|sin)|"
                         r"no.{0,30}(autorizad|orden|prescrit).{0,40}"
                         r"(galeno|m[ée]dic|profesional de la salud)", re.I),
        "arregla": "Adjunta la orden, fórmula o autorización médica. Si la perdiste, "
                   "pídela en la IPS donde te atendieron.",
    },
    "hecho_superado": {
        "titulo": "Carencia actual de objeto / hecho superado",
        "explica": "La EPS entregó el servicio antes del fallo, así que el juez "
                   "declara que ya no hay nada que ordenar. No es una derrota real, "
                   "pero deja sin efectos la tutela.",
        "rx": re.compile(r"carencia actual de objeto|hecho superado|da[ñn]o consumado|"
                         r"situaci[óo]n sobreviniente", re.I),
        "arregla": "Si te entregaron lo pedido, avísale al juzgado. Si fue parcial o "
                   "tardío, dilo: la tutela sigue viva por lo que falta.",
    },
    "subsidiariedad": {
        "titulo": "Existe otro mecanismo (subsidiariedad)",
        "explica": "El juez considera que el caso debía ir a la Superintendencia de "
                   "Salud o a otra vía antes que a tutela.",
        "rx": re.compile(r"subsidiaried|otro medio de defensa|mecanismo (judicial )?"
                         r"(id[óo]neo|eficaz|principal)|superintendencia nacional de salud", re.I),
        "arregla": "Explica por qué esperar te causa un perjuicio irremediable "
                   "(deterioro de salud, dolor, riesgo de vida) y por qué la vía "
                   "administrativa no es suficientemente rápida en tu caso.",
    },
    "inmediatez": {
        "titulo": "Pasó demasiado tiempo (inmediatez)",
        "explica": "Entre el hecho y la tutela transcurrió tanto que el juez duda "
                   "de la urgencia.",
        "rx": re.compile(r"inmediatez|t[ée]rmino razonable|transcurri[óo].{0,40}"
                         r"(a[ñn]os|meses)", re.I),
        "arregla": "Si la demora tiene explicación (te enfermaste, te dieron largas, "
                   "seguiste reclamando), escríbela en los hechos con fechas.",
    },
    "legitimacion": {
        "titulo": "Quien la puso no podía hacerlo (legitimación)",
        "explica": "Alguien tuteló por otra persona sin poder ni agencia oficiosa "
                   "válida, o contra quien no era responsable.",
        "rx": re.compile(r"legitimaci[óo]n (en la causa )?(por activa|por pasiva)|"
                         r"agencia oficiosa|no acredit[óo].{0,40}representaci[óo]n", re.I),
        "arregla": "Si tutelas por otra persona, di por qué no puede hacerlo ella "
                   "misma (enfermedad, edad, discapacidad). Eso es la agencia oficiosa.",
    },
    "no_pbs_sin_prueba": {
        "titulo": "Servicio no incluido y sin sustento del médico",
        "explica": "Se pide algo fuera del plan de beneficios sin el concepto médico "
                   "que explique por qué es necesario y por qué no sirve la alternativa cubierta.",
        "rx": re.compile(r"no (se encuentra )?incluid[oa].{0,40}(plan|pbs|pos)|"
                         r"exclu(sion|id).{0,40}(plan|pbs|pos)|"
                         r"concepto (del )?m[ée]dico tratante.{0,50}(no|sin)", re.I),
        "arregla": "Pide al médico tratante un concepto que diga por qué lo necesitas "
                   "y por qué lo que cubre el plan no te sirve.",
    },
    "falta_prueba": {
        "titulo": "No se probó lo que se afirma",
        "explica": "El juez no encontró soporte de los hechos: ni la solicitud a la "
                   "EPS, ni la negativa, ni la historia clínica.",
        "rx": re.compile(r"no (se )?(acredit|prob|demostr|allega|aport)[óoa].{0,60}|"
                         r"aus(encia|ente) de prueba|carece de (soporte|prueba)", re.I),
        "arregla": "Adjunta todo: orden médica, radicado de la solicitud a la EPS, su "
                   "respuesta (o la constancia de que no respondió) e historia clínica.",
    },
    "improcedencia_general": {
        "titulo": "Improcedente por otras razones formales",
        "explica": "Rechazos por temeridad, cosa juzgada o requisitos de forma.",
        "rx": re.compile(r"temerid|cosa juzgada|ya fue objeto de|indebida acumulaci[óo]n", re.I),
        "arregla": "Verifica que no exista otra tutela tuya por los mismos hechos: "
                   "el juramento del artículo 37 es obligatorio y se toma en serio.",
    },
}


def cargar():
    """Lee el corpus tolerando un archivo a medio escribir: el harvester va
    haciendo append, así que se puede analizar mientras cosecha."""
    p = OUT / "corpus-salud.jsonl.gz"
    if not p.exists():
        sys.exit(f"No existe {p}. Corre antes: harvest_relatoria.py harvest")
    rows = []
    try:
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            for linea in fh:
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    rows.append(json.loads(linea))
                except json.JSONDecodeError:
                    continue  # última línea parcial
    except EOFError:
        pass  # gzip cortado a mitad: nos quedamos con lo leído
    return rows


def clasificar_motivo(texto):
    """Un motivo puede caer en varias causas (los jueces acumulan argumentos)."""
    return [k for k, c in CAUSAS.items() if c["rx"].search(texto)]


# ── Sección ANTECEDENTES ──────────────────────────────────────────────────────
# Es el bloque donde la sentencia narra el caso y qué hizo el juez de instancia.
# Está en el 96,7% de las sentencias del corpus (medido), mientras que los
# encabezados específicos tipo "Sentencia de primera instancia" solo en ~46%.
# Por eso la unidad del RAG es esta sección, no una frase suelta: le da al
# modelo el caso completo en vez de un fragmento sin contexto.
RE_ANTECEDENTES = re.compile(
    r"\bANTECEDENTES\b(.*?)(?=\bCONSIDERACIONES\b|\bII\.\s|\bRESUELVE\b)", re.S)


def extraer_antecedentes(txt, cap=14000):
    m = RE_ANTECEDENTES.search(txt)
    if not m:
        return None
    s = " ".join(m.group(1).split())
    return s[:cap] if len(s) > 400 else None


# Fórmulas de la propia Corte que el extractor confunde con el motivo del juez
# de instancia (aparecen justo después de la frase de decisión, en el preámbulo
# de competencia). No son razones de fracaso.
RE_BOILERPLATE = re.compile(
    r"art[íi]culos?\s*86\s*y\s*241|numeral 9|"
    r"art[íi]culos? 31 a 36 del Decreto 2591|"
    r"en ejercicio de sus (atribuciones|competencias) constitucionales", re.I)


def main():
    ver_causa = None
    if "--causa" in sys.argv:
        ver_causa = sys.argv[sys.argv.index("--causa") + 1]

    rows = cargar()
    hits = Counter()
    citas = {k: [] for k in CAUSAS}
    n_negadas = n_con_motivo = n_clasificadas = 0
    sin_clasificar = []

    for r in rows:
        for p in r.get("instancia") or []:
            dec = p.get("decision") or ""
            mot = p.get("motivo") or ""
            # Solo interesan las decisiones DESFAVORABLES de instancia: son las
            # que enseñan por qué se cae una tutela.
            if not re.search(r"neg[óo]|improcedente|rechaz[óo]", dec, re.I):
                continue
            if mot and RE_BOILERPLATE.search(mot):
                mot = ""  # es la fórmula de competencia de la Corte, no un motivo
            n_negadas += 1
            if mot:
                n_con_motivo += 1
            blob = dec + " " + mot
            cs = clasificar_motivo(blob)
            if not cs:
                if mot:
                    sin_clasificar.append((r["sentencia"], mot[:160]))
                continue
            n_clasificadas += 1
            for c in cs:
                hits[c] += 1
                if len(citas[c]) < 40:
                    citas[c].append({
                        "sentencia": r["sentencia"], "fecha": r["fecha"],
                        "url": r["url"], "casos": r["casos"],
                        "motivo": mot[:400] or dec[:400],
                    })

    salida = {
        "generado": __import__("time").strftime("%Y-%m-%d"),
        "fuente": "Corte Constitucional · sentencias T de salud (relatoría)",
        "universo": {"sentencias_salud": len(rows),
                     "decisiones_de_instancia_desfavorables": n_negadas,
                     "con_motivo_extraible": n_con_motivo,
                     "clasificadas_en_la_taxonomia": n_clasificadas},
        "cobertura": {
            "pct_con_motivo": round(100 * n_con_motivo / n_negadas, 1) if n_negadas else None,
            "pct_clasificadas_sobre_con_motivo":
                round(100 * n_clasificadas / n_con_motivo, 1) if n_con_motivo else None,
            "advertencia": (
                "La taxonomía por patrones cubre el NÚCLEO de causas, no la cola. "
                "En la mayoría de sentencias el juez no usa un verbo de motivación "
                "cerca de la frase de decisión, y el razonamiento jurídico es "
                "demasiado diverso para agotarlo con reglas. Por eso la taxonomía "
                "es la capa de navegación y priors, y la lectura fina la hace el "
                "LLM sobre los pasajes de `rag-pasajes.jsonl.gz` (sección "
                "ANTECEDENTES completa), nunca de memoria."),
        },
        "nota": ("Frecuencia dentro de las sentencias que la Corte SELECCIONÓ para "
                 "revisión — no es la distribución poblacional de las tutelas del "
                 "país. Sirve para explicar POR QUÉ se cae una tutela y citar la "
                 "sentencia que lo dice, no para estimar probabilidades."),
        "causas": [],
    }
    for k, c in CAUSAS.items():
        salida["causas"].append({
            "id": k, "titulo": c["titulo"], "explica": c["explica"],
            "como_se_arregla": c["arregla"],
            "n_casos": hits[k],
            "sentencias": [x["sentencia"] for x in citas[k][:12]],
            "citas": citas[k][:8],
        })
    salida["causas"].sort(key=lambda x: -x["n_casos"])
    (OUT / "causas-fracaso.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1))

    # Corpus de pasajes para el RAG. Unidad = sección ANTECEDENTES (el caso
    # narrado completo), más los pares decisión/motivo ya destilados. Así el
    # modelo puede citar la sentencia Y tener el contexto para no malinterpretarla.
    n_rag = n_ant = 0
    with gzip.open(OUT / "rag-pasajes.jsonl.gz", "wt", encoding="utf-8") as fh:
        for r in rows:
            ant = extraer_antecedentes(r["texto"])
            if ant:
                n_ant += 1
            inst = [{"decision": p["decision"], "motivo": p.get("motivo"),
                     "causas": clasificar_motivo(p["decision"] + " " + (p.get("motivo") or ""))}
                    for p in (r.get("instancia") or [])]
            fh.write(json.dumps({
                "sentencia": r["sentencia"], "fecha": r["fecha"], "ano": r["ano"],
                "url": r["url"], "casos": r["casos"], "temas": r["temas"][:300],
                "antecedentes": ant,
                "instancia": inst,
                "resuelve": r.get("resuelve"),
            }, ensure_ascii=False) + "\n")
            n_rag += 1
    salida["rag"] = {"documentos": n_rag, "con_antecedentes": n_ant}
    (OUT / "causas-fracaso.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1))

    if ver_causa:
        c = next(x for x in salida["causas"] if x["id"] == ver_causa)
        print(f"══ {c['titulo']} · {c['n_casos']} casos ══\n")
        for cit in c["citas"]:
            print(f"[{cit['sentencia']}] {cit['motivo'][:280]}\n")
        return

    print(f"Corpus: {len(rows)} sentencias de salud")
    print(f"Decisiones de instancia DESFAVORABLES: {n_negadas}"
          f" · con motivo extraíble: {n_con_motivo}"
          f" · clasificadas: {n_clasificadas}\n")
    print("CAUSAS DE FRACASO (frecuencia en el corpus de revisión):")
    for c in salida["causas"]:
        print(f"  {c['n_casos']:4d}  {c['titulo']}")
        if c["sentencias"]:
            print(f"        p.ej. {', '.join(c['sentencias'][:4])}")
    print(f"\nRAG: {salida['rag']['documentos']} documentos"
          f" · {salida['rag']['con_antecedentes']} con sección ANTECEDENTES"
          f" ({100*salida['rag']['con_antecedentes']/salida['rag']['documentos']:.0f}%)")
    print(f"Sin clasificar por reglas: {len(sin_clasificar)} motivos"
          f" → los lee el LLM sobre los pasajes, no se descartan")
    print(f"\n→ {OUT/'causas-fracaso.json'}")
    print(f"→ {OUT/'rag-pasajes.jsonl.gz'}")


if __name__ == "__main__":
    main()
