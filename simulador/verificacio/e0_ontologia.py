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

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ARREL not in sys.path:
    sys.path.insert(0, ARREL)

from ontology_loader import (  # noqa: E402
    ONTOLOGIA_DOMINI_DEFECTE,
    ONTOLOGIA_MODEL_DEFECTE,
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
    antics = ["Estat_Panel", "Angle_Objectiu", "Tomàquet", "Sensor_Humitat_Sòl", "Sensor_Radiació"]
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
