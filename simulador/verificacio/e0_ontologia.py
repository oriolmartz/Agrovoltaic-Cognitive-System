"""E0 - Consistencia de la integracio ontologica.

Comprova el flux complet de coneixement estatic:
  ontologia_domini.rdf (TBox / contracte)
        -> valida
  ontologia_model.rdf (ABox / instanciacio)
        -> projecta
  fets CLIPS de topologia.

  ontologia_reg.rdf (modul del reg; importa el domini)
        -> valida i projecta
  objectiu d'estalvi d'aigua, prioritat, conflicte i reg-config,
  i verifica que les regles de reg de CLIPS parlen el mateix llenguatge
  (codis de font i valors fixos de les preferencies).

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
    ONTOLOGIA_REG_DEFECTE,
    ONTOLOGIA_DOMINI_IRI,
    ONTOLOGIA_MODEL_IRI,
    ONTOLOGIA_REG_IRI,
    carrega_model,
    fets_clips,
    fets_reg,
)


_DOMINI_CLP = None


def domini_clp_text() -> str:
    global _DOMINI_CLP
    if _DOMINI_CLP is None:
        _DOMINI_CLP = open(os.path.join(ARREL, "clips_core", "core", "domini.clp"), encoding="utf-8").read()
    return _DOMINI_CLP


def main() -> int:
    model = carrega_model(ONTOLOGIA_MODEL_DEFECTE, ONTOLOGIA_DOMINI_DEFECTE, ONTOLOGIA_REG_DEFECTE)

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

    # --- OntologiaReg: mòdul propi, importa el domini, el model l'importa ---------------------
    reg = model.reg
    if reg is None:
        errors.append("l'ontologia de reg no s'ha carregat")
    else:
        esperat_reg = {
            "reg:classes_reg_operacionals": 4,
            "reg:propietats_objecte_reg": 2,
            "reg:propietats_dades_reg": 8,
        }
        for k, v in esperat_reg.items():
            if vd.get(k) != v:
                errors.append(f"contracte de reg inesperat per {k}: {vd.get(k)} != {v}")
        if vd.get("reg:relacions_reg_validades", 0) <= 0 or vd.get("reg:literals_reg_validats", 0) <= 0:
            errors.append("l'ontologia de reg no ha validat relacions/literals")
        g_reg = Graph(); g_reg.parse(reg.fitxer)
        if set(g_reg.subjects(RDF.type, OWL.Ontology)) != {ONTOLOGIA_REG_IRI}:
            errors.append("IRI de reg inesperat")
        if ONTOLOGIA_DOMINI_IRI not in set(g_reg.objects(ONTOLOGIA_REG_IRI, OWL.imports)):
            errors.append("ontologia_reg.rdf no importa ontologia_domini.rdf")
        if ONTOLOGIA_REG_IRI not in set(g_model.objects(ONTOLOGIA_MODEL_IRI, OWL.imports)):
            errors.append("ontologia_model.rdf no importa ontologia_reg.rdf (declara vàlvules de reg)")
        # el reg no ha de duplicar l'esquema del domini (les declaracions buides es toleren i es compten)
        if vd.get("reg:declaracions_buides_domini", 0) > 10:
            errors.append("el reg declara massa termes del domini (reimportació sospitosa)")

        # El model declara una vàlvula per sector (destinatària de l'ordre-reg)
        sense_valvula = [sid for sid in model.ids_sectors if not model.sectors[sid].valvula]
        if sense_valvula:
            errors.append(f"sectors sense vàlvula de reg: {sense_valvula}")

        # El coneixement estàtic del reg ve del RDF i ja no és als mòduls CLIPS
        if re.search(r"^\s*\(reg-config\)", domini_clp_text(), re.M) or "(id Obj_Estalvi_Aigua)" in domini_clp_text():
            errors.append("domini.clp torna a instanciar manualment reg-config o Obj_Estalvi_Aigua")
        if re.search(r"^\s*\((prioritat|conflicte)\b[^\n]*Obj_Estalvi_Aigua", domini_clp_text(), re.M):
            errors.append("domini.clp torna a duplicar prioritat/conflicte de l'objectiu d'estalvi d'aigua")

        # Valors per defecte de la plantilla reg-config == valors de l'ontologia (una sola veritat)
        c = reg.config
        defaults = dict(re.findall(r"\(slot ([a-z-]+) \(type (?:FLOAT|INTEGER)\) \(default ([0-9.]+)\)\)?",
                                   re.search(r"\(deftemplate reg-config.*?\n\n", domini_clp_text(), re.S).group(0)))
        esperats = {"anticipacio": c.anticipacio, "pluja-anulla": c.pluja_anulla, "pluja-minima": c.pluja_minima,
                    "hora-fresca-mati": c.hora_fresca_mati, "hora-fresca-tarda": c.hora_fresca_tarda}
        for k, v in esperats.items():
            if k not in defaults or abs(float(defaults[k]) - float(v)) > 1e-12:
                errors.append(f"reg-config.{k}: plantilla={defaults.get(k)} ontologia={v}")

        # Objectiu d'estalvi d'aigua: ve del reg, amb prioritat i conflicte
        objs = {o.id: o for o in reg.objectius}
        o = objs.get("Obj_Estalvi_Aigua")
        if o is None:
            errors.append("falta Obj_Estalvi_Aigua a l'ontologia de reg")
        else:
            if (o.tipus, o.restriccio) != ("estalvi-aigua", "tova"):
                errors.append(f"Obj_Estalvi_Aigua inesperat: {o.tipus}/{o.restriccio}")
            if ("Obj_Produccio_Cultiu", "Obj_Estalvi_Aigua") not in o.prioritats:
                errors.append("falta la prioritat Obj_Produccio_Cultiu > Obj_Estalvi_Aigua")
            if ("Obj_Produccio_Cultiu", "Obj_Estalvi_Aigua") not in o.conflictes:
                errors.append("falta el conflicte Obj_Produccio_Cultiu / Obj_Estalvi_Aigua")

        # Fonts de preferència: el catàleg de l'ontologia == els `font` de les regles de reg
        delib = open(os.path.join(ARREL, "clips_core", "reasoning", "deliberacio.clp"), encoding="utf-8").read()
        fonts_clips = set(re.findall(r"\(preferencia-reg [^\n]*?\(font ([A-Za-z0-9-]+)\)", delib))
        fonts_clips |= set(re.findall(r"\(font (AVR[0-9]+-[a-z-]+)\)", delib))
        fonts_rdf = set(reg.codis_font)
        if fonts_clips != fonts_rdf:
            errors.append(f"fonts de reg diferents: només CLIPS={sorted(fonts_clips - fonts_rdf)} només RDF={sorted(fonts_rdf - fonts_clips)}")
        # Valors fixos de les preferències numèriques (AVR4 +1, AVR5 -3, AVR6 -1)
        for f in reg.fonts:
            if f.valor_fix is None:
                continue
            m = re.search(r"\(valor (-?[0-9.]+)\)[\s\S]{0,60}?\(font " + re.escape(f.codi) + r"\)", delib)
            valor = None if not m else float(m.group(1))
            if valor is None or abs(valor - f.valor_fix) > 1e-12:
                errors.append(f"{f.codi}: Valor_Fix={f.valor_fix} però CLIPS usa {valor}")

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
    compta_reg = {
        "objectiu": sum(x.startswith("(objectiu ") for x in fets),
        "prioritat": sum(x.startswith("(prioritat ") for x in fets),
        "conflicte": sum(x.startswith("(conflicte ") for x in fets),
        "reg-config": sum(x.startswith("(reg-config ") for x in fets),
    }
    if compta_reg != {"objectiu": 1, "prioritat": 1, "conflicte": 1, "reg-config": 1}:
        errors.append(f"recompte de fets de reg inesperat: {compta_reg}")
    if compta != esperat:
        errors.append(f"recompte de fets inesperat: {compta}, esperat {esperat}")

    print(f"Domini (TBox): {model.fitxer_domini}")
    print(f"Model (ABox): {model.fitxer}")
    print(f"Contracte validat: {vd}")
    print(f"Sectors: {', '.join(model.ids_sectors)}")
    print(f"Tipus de sensors: {', '.join(model.tipus_sensors)}")
    print(f"Fets projectats: {compta}")
    print(f"Fets de reg projectats: {compta_reg}")
    if model.reg is not None:
        print(f"Fonts de preferència de reg: {len(model.reg.fonts)} ({', '.join(model.reg.codis_font)})")
    if errors:
        print("E0 KO")
        for e in errors:
            print(f"- {e}")
        return 1
    print("E0 OK - domini valida model i reg; el model alimenta la topologia CLIPS i el reg el coneixement del reg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
