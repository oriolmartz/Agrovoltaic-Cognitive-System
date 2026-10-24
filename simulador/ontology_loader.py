"""Carrega el model ontologic RDF i el projecta a fets CLIPS.

L'ontologia de domini actua com a TBox/contracte del vocabulari operacional.
L'ontologia de model n'es la ABox/instanciacio i es la font canonica de la topologia
estatica de la planta: sectors, cultius, panells, sensors i estats inicials.
Python valida TBox -> ABox i fa exclusivament adaptacio RDF -> fets; no pren decisions.

Els deftemplate, els llindars operacionals, les regles, preferencies, impasses i
la seleccio final continuen dins del nucli CLIPS.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re
import unicodedata

from rdflib import Graph, Literal, RDF, RDFS, OWL, URIRef


ARREL = Path(__file__).resolve().parent
ONTOLOGIA_MODEL_DEFECTE = (ARREL.parent / "ontologia_model.rdf").resolve()
ONTOLOGIA_DOMINI_DEFECTE = (ARREL.parent / "ontologia_domini.rdf").resolve()
ONTOLOGIA_MODEL_IRI = URIRef("http://www.semanticweb.org/maxvi/ontologies/2026/8/OntologiaModel")
ONTOLOGIA_DOMINI_IRI = URIRef("http://www.semanticweb.org/maxvi/ontologies/2026/8/OntologiaDomini")


CLASSES_OPERACIONALS = {
    "Sector", "Cultiu", "Panell", "Sensor", "Estat_Cultiu", "Estat_Panell",
    "Tomaquet", "Enciam", "Vinya",
    "Sensor_Humitat_Sol", "Sensor_Pluja", "Sensor_Radiacio",
    "Sensor_Temperatura_Aire", "Sensor_Temperatura_Cultiu", "Sensor_Vent",
}
PROPIETATS_OBJECTE_OPERACIONALS = {
    "te_cultiu", "te_panell", "te_sensor", "te_estat_cultiu", "te_estat_panell",
}
PROPIETATS_DADES_OPERACIONALS = {
    "Sensibilitat", "Angle_Actual", "Angle_Optim_Produccio", "Disponible", "Estat_Mecanic",
}


def _local(x) -> str:
    text = str(x)
    return text.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def _ascii(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)).lower()


def _predicat(g: Graph, nom_local: str) -> URIRef:
    candidats = {p for p in g.predicates() if _local(p) == nom_local}
    if len(candidats) != 1:
        raise ValueError(f"Propietat RDF '{nom_local}': s'esperava 1 URI i se n'han trobat {len(candidats)}")
    return next(iter(candidats))




def _terme_esquema(g: Graph, nom_local: str, tipus: URIRef) -> URIRef:
    candidats = {s for s in g.subjects(RDF.type, tipus) if isinstance(s, URIRef) and _local(s) == nom_local}
    if len(candidats) != 1:
        raise ValueError(
            f"Ontologia de domini: '{nom_local}' hauria d'estar declarat una vegada com {_local(tipus)}; "
            f"se n'han trobat {len(candidats)}"
        )
    return next(iter(candidats))


def _es_subclasse(g_domini: Graph, classe: URIRef, esperada: URIRef) -> bool:
    if classe == esperada:
        return True
    vistos = set()
    pendents = [classe]
    while pendents:
        actual = pendents.pop()
        if actual in vistos:
            continue
        vistos.add(actual)
        for pare in g_domini.objects(actual, RDFS.subClassOf):
            if not isinstance(pare, URIRef):
                continue
            if pare == esperada:
                return True
            pendents.append(pare)
    return False


def _individu_compatible(g_model: Graph, g_domini: Graph, individu: URIRef, classe_esperada: URIRef) -> bool:
    tipus = [t for t in g_model.objects(individu, RDF.type) if isinstance(t, URIRef) and t != OWL.NamedIndividual]
    return any(_es_subclasse(g_domini, t, classe_esperada) for t in tipus)


def _iri_ontologia(g: Graph) -> URIRef:
    candidats = [s for s in g.subjects(RDF.type, OWL.Ontology) if isinstance(s, URIRef)]
    if len(candidats) != 1:
        raise ValueError(f"S'esperava exactament una declaracio owl:Ontology i se n'han trobat {len(candidats)}")
    return candidats[0]


def valida_contra_domini(g_model: Graph, g_domini: Graph) -> dict[str, int]:
    """Valida el contracte ontologic abans de projectar l'ABox a CLIPS.

    `ontologia_domini.rdf` es l'esquema autoritatiu. `ontologia_model.rdf`
    importa aquest esquema i conte les instancies concretes de la planta.
    No s'executa un reasoner OWL complet: es validen imports, separacio
    esquema/instancies, vocabulari consumit pel runtime i domain/range
    de les propietats operacionals.
    """
    domini_iri = _iri_ontologia(g_domini)
    model_iri = _iri_ontologia(g_model)
    if domini_iri != ONTOLOGIA_DOMINI_IRI:
        raise ValueError(f"IRI inesperat per a l'ontologia de domini: {domini_iri}")
    if model_iri != ONTOLOGIA_MODEL_IRI:
        raise ValueError(f"IRI inesperat per a l'ontologia de model: {model_iri}")
    if domini_iri not in set(g_model.objects(model_iri, OWL.imports)):
        raise ValueError("ontologia_model.rdf ha d'importar explicitament ontologia_domini.rdf amb owl:imports")

    # L'ABox no ha de redeclarar l'esquema.
    declaracions_model = []
    for tipus in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty):
        declaracions_model.extend(s for s in g_model.subjects(RDF.type, tipus) if isinstance(s, URIRef))
    if declaracions_model:
        noms = ", ".join(sorted({_local(x) for x in declaracions_model}))
        raise ValueError(f"L'ontologia de model redeclara termes d'esquema: {noms}")

    classes = {n: _terme_esquema(g_domini, n, OWL.Class) for n in sorted(CLASSES_OPERACIONALS)}
    obj_props = {
        n: _terme_esquema(g_domini, n, OWL.ObjectProperty)
        for n in sorted(PROPIETATS_OBJECTE_OPERACIONALS)
    }
    data_props = {
        n: _terme_esquema(g_domini, n, OWL.DatatypeProperty)
        for n in sorted(PROPIETATS_DADES_OPERACIONALS)
    }

    # Qualsevol classe usada pels individus del model ha d'estar declarada al domini.
    classes_domini = {s for s in g_domini.subjects(RDF.type, OWL.Class) if isinstance(s, URIRef)}
    for individu in g_model.subjects(RDF.type, OWL.NamedIndividual):
        for tipus in g_model.objects(individu, RDF.type):
            if isinstance(tipus, URIRef) and tipus != OWL.NamedIndividual and tipus not in classes_domini:
                raise ValueError(f"{_local(individu)} utilitza una classe no declarada al domini: {tipus}")

    # Qualsevol propietat de negoci usada per l'ABox ha d'estar declarada al domini.
    propietats_domini = {
        s for tipus in (OWL.ObjectProperty, OWL.DatatypeProperty)
        for s in g_domini.subjects(RDF.type, tipus) if isinstance(s, URIRef)
    }
    for s, p, o in g_model:
        if p in (RDF.type, OWL.imports):
            continue
        if s == model_iri:
            continue
        if isinstance(p, URIRef) and str(p).startswith((str(RDF), str(RDFS), str(OWL))):
            continue
        if isinstance(p, URIRef) and p not in propietats_domini:
            raise ValueError(f"L'ABox utilitza una propietat no declarada al domini: {p}")

    # Comprovacio de domain/range per a les relacions projectades a CLIPS.
    relacions = 0
    for nom, p in obj_props.items():
        dominis = [x for x in g_domini.objects(p, RDFS.domain) if isinstance(x, URIRef)]
        rangs = [x for x in g_domini.objects(p, RDFS.range) if isinstance(x, URIRef)]
        for s, o in g_model.subject_objects(p):
            if not isinstance(s, URIRef) or not isinstance(o, URIRef):
                raise ValueError(f"{nom}: s'esperava una relacio entre individus URI")
            if dominis and not any(_individu_compatible(g_model, g_domini, s, d) for d in dominis):
                raise ValueError(
                    f"{nom}: {_local(s)} no es compatible amb el domini "
                    f"{', '.join(_local(d) for d in dominis)}"
                )
            if rangs and not any(_individu_compatible(g_model, g_domini, o, r) for r in rangs):
                raise ValueError(
                    f"{nom}: {_local(o)} no es compatible amb el rang "
                    f"{', '.join(_local(r) for r in rangs)}"
                )
            relacions += 1

    literals = 0
    for nom, p in data_props.items():
        dominis = [x for x in g_domini.objects(p, RDFS.domain) if isinstance(x, URIRef)]
        for s, o in g_model.subject_objects(p):
            if not isinstance(o, Literal):
                raise ValueError(f"{nom}: el valor de {_local(s)} hauria de ser un literal")
            if dominis and not any(_individu_compatible(g_model, g_domini, s, d) for d in dominis):
                raise ValueError(
                    f"{nom}: {_local(s)} no es compatible amb el domini "
                    f"{', '.join(_local(d) for d in dominis)}"
                )
            literals += 1

    return {
        "classes_operacionals": len(classes),
        "propietats_objecte": len(obj_props),
        "propietats_dades": len(data_props),
        "relacions_validades": relacions,
        "literals_validats": literals,
    }


def _objecte_unic(g: Graph, s: URIRef, p: URIRef, *, obligatori: bool = True):
    vals = list(g.objects(s, p))
    if len(vals) > 1:
        raise ValueError(f"{_local(s)} te {len(vals)} valors per {_local(p)}; se n'esperava com a maxim 1")
    if not vals:
        if obligatori:
            raise ValueError(f"Falta {_local(p)} a {_local(s)}")
        return None
    return vals[0]


def _literal(g: Graph, s: URIRef, p: URIRef, *, obligatori: bool = True):
    v = _objecte_unic(g, s, p, obligatori=obligatori)
    if v is None:
        return None
    if not isinstance(v, Literal):
        raise ValueError(f"{_local(p)} de {_local(s)} hauria de ser un literal")
    return v.toPython()


def _tipus_individu(g: Graph, s: URIRef) -> list[str]:
    return [_local(o) for o in g.objects(s, RDF.type) if o != OWL.NamedIndividual]


def _natural(text: str):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", text)]


TIPUS_CULTIU = {
    "tomaquet": "tomaquet",
    "enciam": "enciam",
    "vinya": "vinya",
}

SENSIBILITAT = {
    "baixa": "baix",
    "baix": "baix",
    "mitjana": "mitja",
    "mitja": "mitja",
    "alta": "alt",
    "alt": "alt",
    "critica": "critic",
    "critic": "critic",
}

TIPUS_SENSOR = {
    "sensor_humitat_sol": "humitat-sol",
    "sensor_pluja": "pluja",
    "sensor_radiacio": "radiacio",
    "sensor_temperatura_aire": "temperatura-aire",
    "sensor_temperatura_cultiu": "temperatura-cultiu",
    "sensor_vent": "vent",
}


@dataclass(frozen=True)
class CultiuOntologic:
    id: str
    tipus: str
    sensibilitat: str


@dataclass(frozen=True)
class PanellOntologic:
    id: str
    sector: str
    angle: float
    angle_optim_produccio: float
    disponible: str
    estat_mecanic: str


@dataclass(frozen=True)
class SectorOntologic:
    id: str
    cultiu: str
    panells: tuple[str, ...]
    sensors: tuple[str, ...]


@dataclass(frozen=True)
class ModelOntologic:
    fitxer: Path
    fitxer_domini: Path
    validacio_domini: dict[str, int]
    sectors: dict[str, SectorOntologic]
    cultius: dict[str, CultiuOntologic]
    panells: dict[str, PanellOntologic]

    @property
    def ids_sectors(self) -> tuple[str, ...]:
        return tuple(sorted(self.sectors, key=_natural))

    @property
    def tipus_sensors(self) -> tuple[str, ...]:
        if not self.sectors:
            return ()
        # El contracte Python/CLIPS treballa per tipus, no per id de sensor.
        tipus = set.intersection(*(set(s.sensors) for s in self.sectors.values()))
        return tuple(sorted(tipus))


def carrega_model(
    path: str | Path = ONTOLOGIA_MODEL_DEFECTE,
    domini_path: str | Path = ONTOLOGIA_DOMINI_DEFECTE,
) -> ModelOntologic:
    """Valida model contra domini i retorna la part projectada operacionalment."""
    fitxer = Path(path).resolve()
    fitxer_domini = Path(domini_path).resolve()
    if not fitxer.is_file():
        raise FileNotFoundError(f"No es troba l'ontologia de model: {fitxer}")
    if not fitxer_domini.is_file():
        raise FileNotFoundError(f"No es troba l'ontologia de domini: {fitxer_domini}")

    g_domini = Graph()
    g_domini.parse(fitxer_domini)
    g = Graph()
    g.parse(fitxer)
    validacio_domini = valida_contra_domini(g, g_domini)

    te_cultiu = _terme_esquema(g_domini, "te_cultiu", OWL.ObjectProperty)
    te_panell = _terme_esquema(g_domini, "te_panell", OWL.ObjectProperty)
    te_sensor = _terme_esquema(g_domini, "te_sensor", OWL.ObjectProperty)
    te_estat_cultiu = _terme_esquema(g_domini, "te_estat_cultiu", OWL.ObjectProperty)
    te_estat_panell = _terme_esquema(g_domini, "te_estat_panell", OWL.ObjectProperty)
    p_sens = _terme_esquema(g_domini, "Sensibilitat", OWL.DatatypeProperty)
    p_angle = _terme_esquema(g_domini, "Angle_Actual", OWL.DatatypeProperty)
    p_angle_obj = _terme_esquema(g_domini, "Angle_Optim_Produccio", OWL.DatatypeProperty)
    p_disp = _terme_esquema(g_domini, "Disponible", OWL.DatatypeProperty)
    p_mec = _terme_esquema(g_domini, "Estat_Mecanic", OWL.DatatypeProperty)

    sector_class = _terme_esquema(g_domini, "Sector", OWL.Class)
    sector_uris = sorted(set(g.subjects(RDF.type, sector_class)), key=lambda x: _natural(_local(x)))

    cultius: dict[str, CultiuOntologic] = {}
    panells: dict[str, PanellOntologic] = {}
    sectors: dict[str, SectorOntologic] = {}

    for su in sector_uris:
        sid = _local(su)
        cu = _objecte_unic(g, su, te_cultiu)
        cid = _local(cu)
        tipus_candidates = [TIPUS_CULTIU.get(_ascii(t)) for t in _tipus_individu(g, cu)]
        tipus_candidates = [x for x in tipus_candidates if x]
        if len(tipus_candidates) != 1:
            raise ValueError(f"No es pot determinar el tipus de cultiu de {cid}: {_tipus_individu(g, cu)}")
        estat_c = _objecte_unic(g, cu, te_estat_cultiu)
        sens_raw = str(_literal(g, estat_c, p_sens))
        sens = SENSIBILITAT.get(_ascii(sens_raw))
        if sens is None:
            raise ValueError(f"Sensibilitat no suportada per {cid}: {sens_raw}")
        cultius[cid] = CultiuOntologic(cid, tipus_candidates[0], sens)

        pids: list[str] = []
        for pu in sorted(g.objects(su, te_panell), key=lambda x: _natural(_local(x))):
            pid = _local(pu)
            if pid in panells:
                raise ValueError(f"El panell {pid} apareix assignat a mes d'un sector")
            estat = _objecte_unic(g, pu, te_estat_panell)
            disp = _literal(g, estat, p_disp)
            pids.append(pid)
            panells[pid] = PanellOntologic(
                id=pid,
                sector=sid,
                angle=float(_literal(g, estat, p_angle)),
                angle_optim_produccio=float(_literal(g, estat, p_angle_obj)),
                disponible="si" if bool(disp) else "no",
                estat_mecanic=str(_literal(g, estat, p_mec)),
            )

        sensor_types: list[str] = []
        for se in sorted(g.objects(su, te_sensor), key=lambda x: _natural(_local(x))):
            classes = [_ascii(t) for t in _tipus_individu(g, se)]
            mapped = [TIPUS_SENSOR.get(t) for t in classes if TIPUS_SENSOR.get(t)]
            if len(mapped) != 1:
                raise ValueError(f"No es pot determinar el tipus del sensor {_local(se)}: {_tipus_individu(g, se)}")
            sensor_types.append(mapped[0])

        if not pids:
            raise ValueError(f"{sid} no te cap panell a l'ontologia")
        if not sensor_types:
            raise ValueError(f"{sid} no te sensors a l'ontologia")
        sectors[sid] = SectorOntologic(sid, cid, tuple(pids), tuple(sorted(sensor_types)))

    model = ModelOntologic(fitxer, fitxer_domini, validacio_domini, sectors, cultius, panells)
    valida_model(model)
    return model


def valida_model(model: ModelOntologic) -> None:
    if len(model.sectors) < 3:
        raise ValueError(f"El model ha de tenir com a minim 3 sectors; en te {len(model.sectors)}")
    if len(model.panells) != len(set(model.panells)):
        raise ValueError("Hi ha identificadors de panell duplicats")
    sensors_requerits = set(TIPUS_SENSOR.values())
    for sid in model.ids_sectors:
        s = model.sectors[sid]
        if s.cultiu not in model.cultius:
            raise ValueError(f"{sid} referencia un cultiu no carregat: {s.cultiu}")
        actuals = set(s.sensors)
        if actuals != sensors_requerits:
            falten = sorted(sensors_requerits - actuals)
            sobren = sorted(actuals - sensors_requerits)
            raise ValueError(f"Sensors incomplets a {sid}: falten={falten}, sobren={sobren}")


def fets_clips(model: ModelOntologic) -> list[str]:
    """Converteix la topologia/estat inicial de l'ontologia en fets CLIPS."""
    fets: list[str] = []
    for sid in model.ids_sectors:
        s = model.sectors[sid]
        c = model.cultius[s.cultiu]
        fets.append(f"(sector (id {sid}) (cultiu {c.id}))")
        fets.append(
            f"(cultiu (id {c.id}) (tipus {c.tipus}) (fase desconeguda) (sensibilitat {c.sensibilitat}))"
        )
        for pid in s.panells:
            p = model.panells[pid]
            fets.append(
                f"(panell (id {p.id}) (sector {p.sector}) (angle {p.angle}) "
                f"(angle-optim-produccio {p.angle_optim_produccio}) "
                f"(disponible {p.disponible}) (estat-mecanic {p.estat_mecanic}))"
            )
        for tp in s.sensors:
            fets.append(
                f"(estat-sensor (sector {sid}) (tipus {tp}) (operatiu si) "
                f"(qualitat valida) (cicle-ultima-lectura 0))"
            )
    return fets


def deffacts_clips(model: ModelOntologic) -> str:
    """La mateixa projeccio com a deffacts, per carregar-la des de CLIPS pur (run_proves.clp).
    Es un fitxer GENERAT a partir del RDF: no s'ha d'editar ni versionar."""
    cos = "\n".join("  " + f for f in fets_clips(model))
    return ("; GENERAT per ontology_loader.py a partir de " + os.path.basename(str(model.fitxer)) +
            ". No l'editeu.\n(deffacts DOMINI::topologia-rdf\n" + cos + ")\n")


def injecta_model(env, model: ModelOntologic) -> int:
    """Projecta els fets sobre un Environment clipspy ja carregat i resetejat."""
    env.eval("(set-current-module DOMINI)")
    n = 0
    for fet in fets_clips(model):
        env.assert_string(fet)
        n += 1
    return n


def resum(model: ModelOntologic) -> str:
    linies = [
        f"Ontologia domini: {model.fitxer_domini}",
        f"Ontologia model: {model.fitxer}",
        f"Validacio domini: {model.validacio_domini}",
        f"Sectors: {len(model.sectors)}",
        f"Panells: {len(model.panells)}",
    ]
    for sid in model.ids_sectors:
        s = model.sectors[sid]
        c = model.cultius[s.cultiu]
        linies.append(f"- {sid}: {c.tipus} ({c.id}), {len(s.panells)} panells, sensors={','.join(s.sensors)}")
    return "\n".join(linies)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Valida i mostra la projeccio RDF -> CLIPS del model agrovoltaic")
    ap.add_argument("rdf", nargs="?", default=str(ONTOLOGIA_MODEL_DEFECTE), help="ontologia de model (ABox)")
    ap.add_argument("--domini", default=str(ONTOLOGIA_DOMINI_DEFECTE), help="ontologia de domini (TBox)")
    ap.add_argument("--fets", action="store_true", help="mostra els fets CLIPS generats")
    ap.add_argument("--clp", metavar="FITXER", help="escriu la projeccio com a deffacts (per a run_proves.clp)")
    args = ap.parse_args()
    m = carrega_model(args.rdf, args.domini)
    print(resum(m))
    if args.fets:
        print("\nFets CLIPS:")
        print("\n".join(fets_clips(m)))
    if args.clp:
        with open(args.clp, "w", encoding="utf-8", newline="\n") as f:
            f.write(deffacts_clips(m))
        print(f"\nDeffacts escrit a {args.clp}")
