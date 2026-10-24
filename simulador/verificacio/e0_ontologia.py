"""E0 - Consistencia de la integracio ontologica.

Comprova el flux complet de coneixement estatic:
  ontologia_domini.rdf (TBox / contracte)
        -> valida
  ontologia_model.rdf (ABox / instanciacio)
        -> projecta
  fets CLIPS de topologia.

No executa el motor de regles; per tant nomes necessita rdflib.
"""
from __future__ import annotations

import json
import os
import re
import sys

from rdflib import Graph, RDF, OWL, URIRef

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ARREL not in sys.path:
    sys.path.insert(0, ARREL)

from ontology_loader import (  # noqa: E402
    ONTOLOGIA_DOMINI_DEFECTE,
    ONTOLOGIA_MODEL_DEFECTE,
    ONTOLOGIA_DOMINI_IRI,
    ONTOLOGIA_MODEL_IRI,
    carrega_model,
    fets_clips,
)


def main() -> int:
    model = carrega_model(ONTOLOGIA_MODEL_DEFECTE, ONTOLOGIA_DOMINI_DEFECTE)

    errors: list[str] = []
    if len(model.sectors) < 3:
        errors.append("menys de 3 sectors")
    if len(model.panells) != 6:
        errors.append(f"s'esperaven 6 panells al model actual i n'hi ha {len(model.panells)}")

    # Contracte TBox -> ABox: aquests recomptes proven que el fitxer de domini
    # s'ha carregat i s'ha utilitzat per validar vocabulari i domain/range.
    vd = model.validacio_domini
    esperat_contracte = {
        "classes_operacionals": 15,
        "propietats_objecte": 5,
        "propietats_dades": 5,
    }
    for k, v in esperat_contracte.items():
        if vd.get(k) != v:
            errors.append(f"contracte de domini inesperat per {k}: {vd.get(k)} != {v}")
    if vd.get("relacions_validades", 0) <= 0 or vd.get("literals_validats", 0) <= 0:
        errors.append("l'ontologia de domini no ha validat relacions/literals del model")

    # Separacio real entre ontologies: IRI propi, import explicit i ABox sense esquema duplicat.
    g_domini = Graph(); g_domini.parse(model.fitxer_domini)
    g_model = Graph(); g_model.parse(model.fitxer)
    ont_domini = set(g_domini.subjects(RDF.type, OWL.Ontology))
    ont_model = set(g_model.subjects(RDF.type, OWL.Ontology))
    if ont_domini != {ONTOLOGIA_DOMINI_IRI}:
        errors.append(f"IRI de domini inesperat: {ont_domini}")
    if ont_model != {ONTOLOGIA_MODEL_IRI}:
        errors.append(f"IRI de model inesperat: {ont_model}")
    if ONTOLOGIA_DOMINI_IRI not in set(g_model.objects(ONTOLOGIA_MODEL_IRI, OWL.imports)):
        errors.append("ontologia_model.rdf no importa ontologia_domini.rdf")
    esquema_model = []
    for tipus in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty):
        esquema_model.extend(s for s in g_model.subjects(RDF.type, tipus) if isinstance(s, URIRef))
    if esquema_model:
        errors.append("ontologia_model.rdf torna a duplicar classes o propietats de l'esquema")

    # El domini pot contenir cinc individus canonics d'objectiu usats en restriccions OWL,
    # pero no ha de contenir instancies concretes de la planta.
    individus_domini = {
        str(s).rsplit('#', 1)[-1]
        for s in g_domini.subjects(RDF.type, OWL.NamedIndividual) if isinstance(s, URIRef)
    }
    objectius_canonics = {
        "Obj_Estabilitat", "Obj_Minimitzar_Moviment", "Obj_Produccio_Cultiu",
        "Obj_Produccio_Energia", "Obj_Seguretat",
    }
    if individus_domini != objectius_canonics:
        errors.append(f"individus inesperats a l'ontologia de domini: {sorted(individus_domini)}")

    config = json.load(open(os.path.join(ARREL, "config.json"), encoding="utf-8"))
    if set(config["sectors"]) != set(model.ids_sectors):
        errors.append("els sectors de config.json no coincideixen amb l'ontologia")
    if any("panells" in x for x in config["sectors"].values()):
        errors.append("config.json torna a duplicar manualment la llista de panells")

    domini_clp = open(os.path.join(ARREL, "clips_core", "core", "domini.clp"), encoding="utf-8").read()
    if re.search(r"\(sector\s+\(id\s+Sector_", domini_clp):
        errors.append("domini.clp torna a contenir sectors instanciats manualment")
    if re.search(r"\(panell\s+\(id\s+Panell_", domini_clp):
        errors.append("domini.clp torna a contenir panells instanciats manualment")

    # Evita regressions al vocabulari antic del model: la ABox ha de parlar el
    # mateix llenguatge canonic que la TBox per als termes que usa el runtime.
    model_text = open(model.fitxer, encoding="utf-8").read()
    antics = ["Estat_Panel", "Estat_Panelll", "Angle_Objectiu", "Tomàquet", "Sensor_Humitat_Sòl", "Sensor_Radiació"]
    trobats = [x for x in antics if re.search(rf"(?<![A-Za-zÀ-ÿ_]){re.escape(x)}(?![A-Za-zÀ-ÿ_])", model_text)]
    if trobats:
        errors.append(f"vocabulari antic/no canonic a ontologia_model.rdf: {trobats}")

    fets = fets_clips(model)
    compta = {
        "sector": sum(x.startswith("(sector ") for x in fets),
        "cultiu": sum(x.startswith("(cultiu ") for x in fets),
        "panell": sum(x.startswith("(panell ") for x in fets),
        "estat-sensor": sum(x.startswith("(estat-sensor ") for x in fets),
    }
    esperat = {"sector": 3, "cultiu": 3, "panell": 6, "estat-sensor": 18}
    if compta != esperat:
        errors.append(f"recompte de fets inesperat: {compta}, esperat {esperat}")

    print(f"Domini (TBox): {model.fitxer_domini}")
    print(f"Model (ABox): {model.fitxer}")
    print(f"Contracte validat: {vd}")
    print(f"Sectors: {', '.join(model.ids_sectors)}")
    print(f"Tipus de sensors: {', '.join(model.tipus_sensors)}")
    print(f"Fets projectats: {compta}")
    if errors:
        print("E0 KO")
        for e in errors:
            print(f"- {e}")
        return 1
    print("E0 OK - domini valida el model i el model alimenta la topologia CLIPS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
