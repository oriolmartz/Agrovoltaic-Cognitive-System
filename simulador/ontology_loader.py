"""Carrega el model ontologic RDF i el projecta a fets CLIPS.

L'ontologia de domini actua com a TBox/contracte del vocabulari operacional.
L'ontologia de model n'es la ABox/instanciacio i es la font canonica de la topologia
estatica de la planta: sectors, cultius, panells, sensors i estats inicials.
Python valida TBox -> ABox i fa exclusivament adaptacio RDF -> fets; no pren decisions.

Els deftemplate, les regles, preferencies, impasses i la seleccio final continuen
dins del nucli CLIPS.

L'ontologia de reg (`ontologia_reg.rdf`, OntologiaReg) es un tercer modul: importa el
domini, hi afegeix el vocabulari del segon actuador (el reg per degoteig) i instancia
el coneixement estatic del reg: la configuracio (`reg-config`), l'objectiu d'estalvi
d'aigua amb la seva prioritat i conflicte, i el cataleg de fonts de preferencia.
Aquest coneixement ja no es duplica a `domini.clp`: es projecta des del RDF, com la
topologia.
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
ONTOLOGIA_REG_DEFECTE = (ARREL.parent / "ontologia_reg.rdf").resolve()
ONTOLOGIA_REG_IRI = URIRef("http://www.semanticweb.org/maxvi/ontologies/2026/8/OntologiaReg")


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

# Vocabulari de OntologiaReg que consumeix el runtime.
CLASSES_REG_OPERACIONALS = {
    "Configuracio_Reg", "Objectiu_Estalvi_Aigua", "Valvula_Reg", "Font_Preferencia_Reg",
}
PROPIETATS_OBJECTE_REG_OPERACIONALS = {"te_valvula_reg", "serveix_objectiu"}
PROPIETATS_DADES_REG_OPERACIONALS = {
    "Anticipacio", "Pluja_Anulla_Mm", "Pluja_Minima_Mm", "Hora_Fresca_Mati", "Hora_Fresca_Tarda",
    "Codi_Font", "Valor_Fix", "Exempta_Per_Nivell",
}
# Propietats del domini que l'ontologia de reg usa per situar el seu objectiu.
PROPIETATS_OBJECTIU_DOMINI = ("te_prioritat", "entra_conflicte", "Tipus_Restriccio")


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


def valida_contra_domini(g_model: Graph, g_domini: Graph, g_reg: Graph | None = None) -> dict[str, int]:
    """Valida el contracte ontologic abans de projectar l'ABox a CLIPS.

    `ontologia_domini.rdf` es l'esquema autoritatiu. `ontologia_model.rdf`
    importa aquest esquema i conte les instancies concretes de la planta.
    No s'executa un reasoner OWL complet: es validen imports, separacio
    esquema/instancies, vocabulari consumit pel runtime i domain/range
    de les propietats operacionals.

    Si es passa `g_reg` (OntologiaReg), el vocabulari permes a l'ABox es el del domini
    mes el del reg, i les relacions del reg que l'ABox usa (te_valvula_reg) es validen
    contra l'esquema combinat. El model nomes ha d'importar el reg si en fa servir termes.
    """
    domini_iri = _iri_ontologia(g_domini)
    model_iri = _iri_ontologia(g_model)
    if domini_iri != ONTOLOGIA_DOMINI_IRI:
        raise ValueError(f"IRI inesperat per a l'ontologia de domini: {domini_iri}")
    if model_iri != ONTOLOGIA_MODEL_IRI:
        raise ValueError(f"IRI inesperat per a l'ontologia de model: {model_iri}")
    if domini_iri not in set(g_model.objects(model_iri, OWL.imports)):
        raise ValueError("ontologia_model.rdf ha d'importar explicitament ontologia_domini.rdf amb owl:imports")

    esquema = g_domini
    if g_reg is not None:
        esquema = Graph()
        esquema += g_domini
        esquema += g_reg
        usa_reg = any(
            isinstance(t, URIRef) and str(t).startswith(str(ONTOLOGIA_REG_IRI) + "#")
            for triple in g_model for t in triple
        )
        if usa_reg and ONTOLOGIA_REG_IRI not in set(g_model.objects(model_iri, OWL.imports)):
            raise ValueError("ontologia_model.rdf usa termes de OntologiaReg: ha d'importar ontologia_reg.rdf amb owl:imports")

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
    classes_domini = {s for s in esquema.subjects(RDF.type, OWL.Class) if isinstance(s, URIRef)}
    for individu in g_model.subjects(RDF.type, OWL.NamedIndividual):
        for tipus in g_model.objects(individu, RDF.type):
            if isinstance(tipus, URIRef) and tipus != OWL.NamedIndividual and tipus not in classes_domini:
                raise ValueError(f"{_local(individu)} utilitza una classe no declarada a l'esquema: {tipus}")

    # Qualsevol propietat de negoci usada per l'ABox ha d'estar declarada al domini.
    propietats_domini = {
        s for tipus in (OWL.ObjectProperty, OWL.DatatypeProperty)
        for s in esquema.subjects(RDF.type, tipus) if isinstance(s, URIRef)
    }
    for s, p, o in g_model:
        if p in (RDF.type, OWL.imports):
            continue
        if s == model_iri:
            continue
        if isinstance(p, URIRef) and str(p).startswith((str(RDF), str(RDFS), str(OWL))):
            continue
        if isinstance(p, URIRef) and p not in propietats_domini:
            raise ValueError(f"L'ABox utilitza una propietat no declarada a l'esquema: {p}")

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

    relacions_reg = 0
    if g_reg is not None:
        te_valvula = _terme_esquema(g_reg, "te_valvula_reg", OWL.ObjectProperty)
        dominis = [x for x in esquema.objects(te_valvula, RDFS.domain) if isinstance(x, URIRef)]
        rangs = [x for x in esquema.objects(te_valvula, RDFS.range) if isinstance(x, URIRef)]
        for s, o in g_model.subject_objects(te_valvula):
            if not isinstance(s, URIRef) or not isinstance(o, URIRef):
                raise ValueError("te_valvula_reg: s'esperava una relacio entre individus URI")
            if dominis and not any(_individu_compatible(g_model, esquema, s, d) for d in dominis):
                raise ValueError(f"te_valvula_reg: {_local(s)} no es compatible amb el domini")
            if rangs and not any(_individu_compatible(g_model, esquema, o, r) for r in rangs):
                raise ValueError(f"te_valvula_reg: {_local(o)} no es compatible amb el rang")
            relacions_reg += 1

    return {
        "classes_operacionals": len(classes),
        "propietats_objecte": len(obj_props),
        "propietats_dades": len(data_props),
        "relacions_validades": relacions,
        "literals_validats": literals,
        "relacions_reg_validades": relacions_reg,
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



# ---------------------------------------------------------------------------
# OntologiaReg: segon actuador (reg per degoteig)
# ---------------------------------------------------------------------------

TIPUS_OBJECTIU_REG = {"objectiu_estalvi_aigua": "estalvi-aigua"}
RESTRICCIO_OBJECTIU = {"tova": "tova", "dura": "dura"}


@dataclass(frozen=True)
class ConfigReg:
    anticipacio: float
    pluja_anulla: float
    pluja_minima: float
    hora_fresca_mati: int
    hora_fresca_tarda: int


@dataclass(frozen=True)
class ObjectiuReg:
    id: str
    tipus: str
    restriccio: str
    prioritats: tuple[tuple[str, str], ...]   # (major, menor)
    conflictes: tuple[tuple[str, str], ...]   # (objectiu-1, objectiu-2), sense duplicats


@dataclass(frozen=True)
class FontReg:
    id: str
    codi: str                          # el simbol `font` que posa la regla CLIPS
    valor_fix: float | None
    objectiu: str | None
    exempta_per_nivell: str | None


@dataclass(frozen=True)
class ReglesReg:
    fitxer: Path
    validacio: dict[str, int]
    config: ConfigReg
    objectius: tuple[ObjectiuReg, ...]
    fonts: tuple[FontReg, ...]

    @property
    def codis_font(self) -> tuple[str, ...]:
        return tuple(sorted(f.codi for f in self.fonts))


def _termes_declarats(g: Graph) -> set[URIRef]:
    return {
        s for t in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty)
        for s in g.subjects(RDF.type, t) if isinstance(s, URIRef)
    }


def _valors_enumerats(g: Graph, prop: URIRef):
    """Valors permesos si el rang de la propietat es un owl:oneOf; None si no n'hi ha."""
    for r in g.objects(prop, RDFS.range):
        llista = g.value(r, OWL.oneOf) if not isinstance(r, URIRef) else None
        if llista is None:
            continue
        valors = []
        while llista is not None and llista != RDF.nil:
            valors.append(str(g.value(llista, RDF.first)))
            llista = g.value(llista, RDF.rest)
        return set(valors)
    return None


def valida_reg_contra_domini(g_reg: Graph, g_domini: Graph) -> dict[str, int]:
    """Valida OntologiaReg (mòdul) contra OntologiaDomini (contracte).

    Regles, paral.leles a les de model -> domini:
      * IRI propi i `owl:imports` explicit del domini;
      * el reg no redefineix cap classe/propietat del domini. Les declaracions buides
        (nomes `rdf:type`, restes d'importar el domini des d'un editor) es toleren i es
        compten; qualsevol axioma afegit a un terme del domini es un error;
      * sobre individus del domini nomes pot afegir `te_prioritat` i `entra_conflicte`
        (aixi es penja l'objectiu d'estalvi d'aigua del sistema d'objectius);
      * vocabulari, domain/range i enumeracions dels individus del reg.
    """
    domini_iri = _iri_ontologia(g_domini)
    reg_iri = _iri_ontologia(g_reg)
    if reg_iri != ONTOLOGIA_REG_IRI:
        raise ValueError(f"IRI inesperat per a l'ontologia de reg: {reg_iri}")
    if domini_iri not in set(g_reg.objects(reg_iri, OWL.imports)):
        raise ValueError("ontologia_reg.rdf ha d'importar explicitament ontologia_domini.rdf amb owl:imports")

    esquema = Graph()
    esquema += g_domini
    esquema += g_reg

    termes_domini = _termes_declarats(g_domini)
    individus_domini = {s for s in g_domini.subjects(RDF.type, OWL.NamedIndividual) if isinstance(s, URIRef)}
    ns_domini = str(ONTOLOGIA_DOMINI_IRI) + "#"
    ns_reg = str(ONTOLOGIA_REG_IRI) + "#"

    stubs = 0
    permesos_individu = {RDF.type} | {
        _terme_esquema(g_domini, n, OWL.ObjectProperty) for n in ("te_prioritat", "entra_conflicte")
    }
    for terme in sorted(_termes_declarats(g_reg) | {s for s in g_reg.subjects() if isinstance(s, URIRef)}, key=str):
        if not str(terme).startswith(ns_domini):
            continue
        if terme in termes_domini:
            extra = [(p, o) for p, o in g_reg.predicate_objects(terme)
                     if not (p == RDF.type and o in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty))]
            if extra:
                raise ValueError(f"El reg afegeix axiomes a un terme d'esquema del domini: {_local(terme)}")
            stubs += 1
        elif terme in individus_domini:
            for p, o in g_reg.predicate_objects(terme):
                if p not in permesos_individu:
                    raise ValueError(f"El reg modifica l'individu del domini {_local(terme)} amb {_local(p)}")
                if p == RDF.type and o != OWL.NamedIndividual:
                    raise ValueError(f"El reg retipa l'individu del domini {_local(terme)}")
        else:
            raise ValueError(f"El reg fa servir un terme del namespace del domini que el domini no declara: {_local(terme)}")

    classes = {n: _terme_esquema(g_reg, n, OWL.Class) for n in sorted(CLASSES_REG_OPERACIONALS)}
    obj_props = {n: _terme_esquema(g_reg, n, OWL.ObjectProperty) for n in sorted(PROPIETATS_OBJECTE_REG_OPERACIONALS)}
    data_props = {n: _terme_esquema(g_reg, n, OWL.DatatypeProperty) for n in sorted(PROPIETATS_DADES_REG_OPERACIONALS)}

    classes_esquema = {s for s in esquema.subjects(RDF.type, OWL.Class) if isinstance(s, URIRef)}
    propietats_esquema = {
        s for t in (OWL.ObjectProperty, OWL.DatatypeProperty)
        for s in esquema.subjects(RDF.type, t) if isinstance(s, URIRef)
    }
    for individu in g_reg.subjects(RDF.type, OWL.NamedIndividual):
        if not isinstance(individu, URIRef) or str(individu).startswith(ns_domini):
            continue
        tipus = [t for t in g_reg.objects(individu, RDF.type) if t != OWL.NamedIndividual]
        if not tipus:
            raise ValueError(f"{_local(individu)} no te cap classe")
        for t in tipus:
            if t not in classes_esquema:
                raise ValueError(f"{_local(individu)} utilitza una classe no declarada: {t}")
        for p, o in g_reg.predicate_objects(individu):
            if p == RDF.type or str(p).startswith((str(RDF), str(RDFS), str(OWL))):
                continue
            if p not in propietats_esquema:
                raise ValueError(f"{_local(individu)} utilitza una propietat no declarada: {p}")

    relacions = 0
    literals = 0
    for individu in {s for s in g_reg.subjects() if isinstance(s, URIRef)}:
        for p, o in g_reg.predicate_objects(individu):
            if p == RDF.type or p not in propietats_esquema:
                continue
            tipus_p = set(esquema.objects(p, RDF.type))
            if str(individu).startswith(ns_domini) and not isinstance(o, URIRef):
                continue
            dominis = [x for x in esquema.objects(p, RDFS.domain) if isinstance(x, URIRef)]
            if dominis and not any(_individu_compatible(esquema, esquema, individu, d) for d in dominis):
                raise ValueError(
                    f"{_local(p)}: {_local(individu)} no es compatible amb el domini "
                    f"{', '.join(_local(d) for d in dominis)}"
                )
            if OWL.ObjectProperty in tipus_p:
                if not isinstance(o, URIRef):
                    raise ValueError(f"{_local(p)}: el valor de {_local(individu)} hauria de ser un individu")
                rangs = [x for x in esquema.objects(p, RDFS.range) if isinstance(x, URIRef)]
                if rangs and not any(_individu_compatible(esquema, esquema, o, r) for r in rangs):
                    raise ValueError(
                        f"{_local(p)}: {_local(o)} no es compatible amb el rang "
                        f"{', '.join(_local(r) for r in rangs)}"
                    )
                relacions += 1
            else:
                if not isinstance(o, Literal):
                    raise ValueError(f"{_local(p)}: el valor de {_local(individu)} hauria de ser un literal")
                permesos = _valors_enumerats(esquema, p)
                if permesos is not None and str(o) not in permesos:
                    raise ValueError(f"{_local(p)}: valor '{o}' fora de l'enumeracio {sorted(permesos)}")
                literals += 1

    return {
        "classes_reg_operacionals": len(classes),
        "propietats_objecte_reg": len(obj_props),
        "propietats_dades_reg": len(data_props),
        "relacions_reg_validades": relacions,
        "literals_reg_validats": literals,
        "declaracions_buides_domini": stubs,
    }


def _carrega_reg_graf(g_reg: Graph, g_domini: Graph, fitxer: Path) -> ReglesReg:
    validacio = valida_reg_contra_domini(g_reg, g_domini)
    esquema = Graph()
    esquema += g_domini
    esquema += g_reg
    ns_reg = str(ONTOLOGIA_REG_IRI) + "#"

    # configuracio: exactament un individu de Configuracio_Reg
    classe_config = _terme_esquema(g_reg, "Configuracio_Reg", OWL.Class)
    configs = sorted(set(g_reg.subjects(RDF.type, classe_config)), key=str)
    if len(configs) != 1:
        raise ValueError(f"S'esperava exactament un individu de Configuracio_Reg i n'hi ha {len(configs)}")
    cfg = configs[0]

    def dada(nom: str, obligatori: bool = True):
        return _literal(g_reg, cfg, _terme_esquema(g_reg, nom, OWL.DatatypeProperty), obligatori=obligatori)

    config = ConfigReg(
        anticipacio=float(dada("Anticipacio")),
        pluja_anulla=float(dada("Pluja_Anulla_Mm")),
        pluja_minima=float(dada("Pluja_Minima_Mm")),
        hora_fresca_mati=int(dada("Hora_Fresca_Mati")),
        hora_fresca_tarda=int(dada("Hora_Fresca_Tarda")),
    )
    if not 0.0 < config.anticipacio <= 1.0:
        raise ValueError(f"Anticipacio fora de (0, 1]: {config.anticipacio}")
    if config.pluja_minima > config.pluja_anulla:
        raise ValueError("Pluja_Minima_Mm no pot superar Pluja_Anulla_Mm")
    if not (0 <= config.hora_fresca_mati < config.hora_fresca_tarda <= 23):
        raise ValueError("Hores fresques incoherents (mati < tarda, 0-23)")

    # objectius definits pel reg (individus de subclasses d'Objectiu al namespace del reg)
    classe_objectiu = _terme_esquema(g_domini, "Objectiu", OWL.Class)
    te_prioritat = _terme_esquema(g_domini, "te_prioritat", OWL.ObjectProperty)
    entra_conflicte = _terme_esquema(g_domini, "entra_conflicte", OWL.ObjectProperty)
    tipus_restriccio = _terme_esquema(g_domini, "Tipus_Restriccio", OWL.DatatypeProperty)
    propis = sorted(
        {s for s in g_reg.subjects(RDF.type, OWL.NamedIndividual)
         if isinstance(s, URIRef) and str(s).startswith(ns_reg)
         and _individu_compatible(esquema, esquema, s, classe_objectiu)},
        key=str,
    )
    ids_propis = {_local(x) for x in propis}
    objectius: list[ObjectiuReg] = []
    for o in propis:
        classes = [TIPUS_OBJECTIU_REG.get(_ascii(t)) for t in _tipus_individu(g_reg, o)]
        classes = [c for c in classes if c]
        if len(classes) != 1:
            raise ValueError(f"No es pot determinar el tipus de l'objectiu {_local(o)}: {_tipus_individu(g_reg, o)}")
        restr = RESTRICCIO_OBJECTIU.get(_ascii(str(_literal(g_reg, o, tipus_restriccio))))
        if restr is None:
            raise ValueError(f"Tipus_Restriccio no suportat a {_local(o)}")
        prioritats = sorted({
            (_local(a), _local(b))
            for a, b in g_reg.subject_objects(te_prioritat)
            if isinstance(a, URIRef) and isinstance(b, URIRef) and o in (a, b)
        })
        parelles = {
            frozenset((_local(a), _local(b)))
            for a, b in g_reg.subject_objects(entra_conflicte)
            if isinstance(a, URIRef) and isinstance(b, URIRef) and o in (a, b)
        }
        conflictes = []
        for par in sorted(parelles, key=lambda x: sorted(x)):
            ordenats = sorted(par, key=lambda x: (x in ids_propis, x))   # el del domini primer
            conflictes.append((ordenats[0], ordenats[1]))
        objectius.append(ObjectiuReg(_local(o), classes[0], restr, tuple(prioritats), tuple(conflictes)))
    if not objectius:
        raise ValueError("L'ontologia de reg no defineix cap objectiu propi")

    # cataleg de fonts de preferencia
    classe_font = _terme_esquema(g_reg, "Font_Preferencia_Reg", OWL.Class)
    p_codi = _terme_esquema(g_reg, "Codi_Font", OWL.DatatypeProperty)
    p_valor = _terme_esquema(g_reg, "Valor_Fix", OWL.DatatypeProperty)
    p_exempta = _terme_esquema(g_reg, "Exempta_Per_Nivell", OWL.DatatypeProperty)
    p_serveix = _terme_esquema(g_reg, "serveix_objectiu", OWL.ObjectProperty)
    fonts: list[FontReg] = []
    for f in sorted(set(g_reg.subjects(RDF.type, classe_font)), key=lambda x: _natural(_local(x))):
        valor = _literal(g_reg, f, p_valor, obligatori=False)
        obj = _objecte_unic(g_reg, f, p_serveix, obligatori=False)
        exempta = _literal(g_reg, f, p_exempta, obligatori=False)
        fonts.append(FontReg(
            id=_local(f), codi=str(_literal(g_reg, f, p_codi)),
            valor_fix=None if valor is None else float(valor),
            objectiu=None if obj is None else _local(obj),
            exempta_per_nivell=None if exempta is None else str(exempta),
        ))
    codis = [f.codi for f in fonts]
    if len(codis) != len(set(codis)):
        raise ValueError("Hi ha Codi_Font duplicats a l'ontologia de reg")

    return ReglesReg(fitxer, validacio, config, tuple(objectius), tuple(fonts))


def carrega_reg(
    path: str | Path = ONTOLOGIA_REG_DEFECTE,
    domini_path: str | Path = ONTOLOGIA_DOMINI_DEFECTE,
) -> ReglesReg:
    """Valida OntologiaReg contra OntologiaDomini i en retorna la part projectable."""
    fitxer = Path(path).resolve()
    if not fitxer.is_file():
        raise FileNotFoundError(f"No es troba l'ontologia de reg: {fitxer}")
    g_domini = Graph()
    g_domini.parse(Path(domini_path).resolve())
    g_reg = Graph()
    g_reg.parse(fitxer)
    return _carrega_reg_graf(g_reg, g_domini, fitxer)


def fets_reg(reg: ReglesReg) -> list[str]:
    """Coneixement estatic del reg com a fets CLIPS (abans eren `deffacts` a domini.clp)."""
    c = reg.config
    fets: list[str] = []
    for o in reg.objectius:
        fets.append(f"(objectiu (id {o.id}) (tipus {o.tipus}) (restriccio {o.restriccio}) (estat inactiu))")
    for o in reg.objectius:
        for major, menor in o.prioritats:
            fets.append(f"(prioritat (major {major}) (menor {menor}))")
    for o in reg.objectius:
        for a, b in o.conflictes:
            fets.append(f"(conflicte (objectiu-1 {a}) (objectiu-2 {b}))")
    fets.append(
        f"(reg-config (anticipacio {c.anticipacio}) (pluja-anulla {c.pluja_anulla}) "
        f"(pluja-minima {c.pluja_minima}) (hora-fresca-mati {c.hora_fresca_mati}) "
        f"(hora-fresca-tarda {c.hora_fresca_tarda}))"
    )
    return fets


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
    valvula: str | None = None        # vàlvula de reg (OntologiaReg: te_valvula_reg), si el model en declara


@dataclass(frozen=True)
class ModelOntologic:
    fitxer: Path
    fitxer_domini: Path
    validacio_domini: dict[str, int]
    sectors: dict[str, SectorOntologic]
    cultius: dict[str, CultiuOntologic]
    panells: dict[str, PanellOntologic]
    reg: ReglesReg | None = None

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
    reg_path: str | Path | None = ONTOLOGIA_REG_DEFECTE,
) -> ModelOntologic:
    """Valida model contra domini (i reg) i retorna la part projectada operacionalment.

    `reg_path=None` desactiva OntologiaReg: el model es carrega com abans, sense coneixement
    de reg (la v1_9 del nucli CLIPS en necessita els fets, vegeu `fets_reg`).
    """
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
    g_reg = None
    reg = None
    if reg_path is not None:
        fitxer_reg = Path(reg_path).resolve()
        if not fitxer_reg.is_file():
            raise FileNotFoundError(f"No es troba l'ontologia de reg: {fitxer_reg}")
        g_reg = Graph()
        g_reg.parse(fitxer_reg)
        reg = _carrega_reg_graf(g_reg, g_domini, fitxer_reg)
    validacio_domini = valida_contra_domini(g, g_domini, g_reg)
    if reg is not None:
        validacio_domini = {**validacio_domini, **{f"reg:{k}": v for k, v in reg.validacio.items()}}
    te_valvula_reg = _terme_esquema(g_reg, "te_valvula_reg", OWL.ObjectProperty) if g_reg is not None else None

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
        valvula = None
        if te_valvula_reg is not None:
            vv = list(g.objects(su, te_valvula_reg))
            if len(vv) > 1:
                raise ValueError(f"{sid} te {len(vv)} vàlvules de reg; se n'espera com a màxim 1")
            if vv:
                valvula = _local(vv[0])
        sectors[sid] = SectorOntologic(sid, cid, tuple(pids), tuple(sorted(sensor_types)), valvula)

    model = ModelOntologic(fitxer, fitxer_domini, validacio_domini, sectors, cultius, panells, reg)
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
    # Vàlvules de reg: opcionals (soar.clp no en té cap fet), pero si un sector en te, tots n'han de tenir
    # i cap vàlvula no es pot compartir entre sectors.
    valvules = [model.sectors[sid].valvula for sid in model.ids_sectors]
    if any(valvules) and not all(valvules):
        sense = [sid for sid in model.ids_sectors if not model.sectors[sid].valvula]
        raise ValueError(f"Hi ha sectors amb vàlvula de reg i d'altres sense: {sense}")
    if len([v for v in valvules if v]) != len({v for v in valvules if v}):
        raise ValueError("Una vàlvula de reg no pot servir més d'un sector")


def fets_clips(model: ModelOntologic) -> list[str]:
    """Converteix la topologia/estat inicial i el coneixement estatic del reg en fets CLIPS."""
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
    if model.reg is not None:
        fets.extend(fets_reg(model.reg))
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
    if model.reg is not None:
        linies.insert(1, f"Ontologia reg: {model.reg.fitxer}")
    for sid in model.ids_sectors:
        s = model.sectors[sid]
        c = model.cultius[s.cultiu]
        valv = f", vàlvula={s.valvula}" if s.valvula else ""
        linies.append(f"- {sid}: {c.tipus} ({c.id}), {len(s.panells)} panells, sensors={','.join(s.sensors)}{valv}")
    if model.reg is not None:
        r = model.reg
        linies.append(f"Reg: config={r.config}")
        for o in r.objectius:
            linies.append(f"- objectiu {o.id} ({o.tipus}, {o.restriccio}); prioritats={list(o.prioritats)}; conflictes={list(o.conflictes)}")
        linies.append(f"- fonts de preferència ({len(r.fonts)}): {', '.join(r.codis_font)}")
    return "\n".join(linies)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Valida i mostra la projeccio RDF -> CLIPS del model agrovoltaic i del reg")
    ap.add_argument("rdf", nargs="?", default=str(ONTOLOGIA_MODEL_DEFECTE), help="ontologia de model (ABox)")
    ap.add_argument("--domini", default=str(ONTOLOGIA_DOMINI_DEFECTE), help="ontologia de domini (TBox)")
    ap.add_argument("--reg", default=str(ONTOLOGIA_REG_DEFECTE), help="ontologia de reg (mòdul; 'cap' la desactiva)")
    ap.add_argument("--fets", action="store_true", help="mostra els fets CLIPS generats")
    ap.add_argument("--clp", metavar="FITXER", help="escriu la projeccio com a deffacts (per a run_proves.clp)")
    args = ap.parse_args()
    m = carrega_model(args.rdf, args.domini, None if args.reg == "cap" else args.reg)
    print(resum(m))
    if args.fets:
        print("\nFets CLIPS:")
        print("\n".join(fets_clips(m)))
    if args.clp:
        with open(args.clp, "w", encoding="utf-8", newline="\n") as f:
            f.write(deffacts_clips(m))
        print(f"\nDeffacts escrit a {args.clp}")
