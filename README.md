# Agrovoltaic-Cognitive-System

Sistema basat en regles per a una instal·lació agrovoltaica, amb un nucli cognitiu inspirat en SOAR implementat en CLIPS i una capa Python per a simulació, dades, integració RDF i experimentació.

## Arquitectura

```text
ontologia_domini.rdf
        │  esquema autoritatiu: classes, propietats, domain/range
        │
        └──── owl:imports ◄──── ontologia_model.rdf
                              │  ABox: només instàncies de planta
                              ▼
simulador/ontology_loader.py
        │  RDFLib: validació TBox→ABox + projecció
        ▼
fets CLIPS de topologia
(sector, cultiu, panell, estat-sensor)
        │
        ▼
clips_core/soar.clp
        │  elaboració, candidats, preferències,
        │  impasses, selecció, aplicació i memòria
        ▼
ordre-actuador + explicació
```

`ontologia_domini.rdf` és el **contracte conceptual autoritatiu**: té un IRI propi (`OntologiaDomini`), defineix classes, propietats, jerarquies i `domain/range`, i conserva només cinc individus canònics d'objectiu que formen part del vocabulari del domini. `ontologia_model.rdf` té un IRI diferent (`OntologiaModel`), l'importa explícitament amb `owl:imports` i conté només les instàncies concretes de la planta. `ontology_loader.py` valida aquesta separació i només després projecta l'ABox a fets CLIPS. Python no avalua candidats ni selecciona accions: **la decisió continua íntegrament dins de CLIPS**.

Els llindars agronòmics i els objectius de control continuen explícits a CLIPS perquè l'ontologia actual encara no n'instancia els valors operacionals.

## Estructura

```text
.
├── ontologia_domini.rdf       # esquema del domini + objectius canònics
├── ontologia_model.rdf        # ABox: instàncies de planta; importa el domini
├── history/                   # snapshots CLIPS monolítics congelats
└── simulador/
    ├── ontology_loader.py     # RDF -> model Python -> fets CLIPS
    ├── clips_bridge.py        # contracte Python <-> CLIPS
    ├── clips_core/            # font CLIPS modular activa
    ├── verificacio/           # E0-E3 i casos de prova
    ├── dades_reals/
    ├── escenaris/
    ├── resultats/
    ├── simulador.py
    └── experiments.py
```

La documentació completa del simulador i dels experiments és a [`simulador/README.md`](simulador/README.md).

## Instal·lació

Es recomana Python **3.11, 3.12 o 3.13**.

```bash
cd simulador
python -m venv venv
```

Windows:

```powershell
venv\Scripts\activate
python -m pip install -r requirements.txt
```

Linux/macOS:

```bash
source venv/bin/activate
python -m pip install -r requirements.txt
```

## Integració ontològica

Per validar el RDF i veure la projecció:

```bash
python ontology_loader.py
python ontology_loader.py --fets
python verificacio/e0_ontologia.py
```

`E0` comprova que:

- `ontologia_domini.rdf` i `ontologia_model.rdf` tenen IRI propis i es poden interpretar;
- `ontologia_model.rdf` importa explícitament `ontologia_domini.rdf` i no redeclara classes ni propietats;
- el model utilitza el vocabulari operacional canònic del domini;
- les relacions del model respecten els `domain/range` definits al domini;
- hi ha almenys tres sectors;
- sectors, cultius, panells i sensors es projecten als fets esperats;
- `config.json` no duplica la llista de panells;
- `clips_core/core/domini.clp` no torna a instanciar manualment la topologia.

## Nucli CLIPS

La font canònica és modular i es troba a `simulador/clips_core/`. `soar.clp` és generat a partir de `modules.txt`:

```bash
python clips_core/build_clips.py
python clips_core/build_clips.py --check-generated
```

Les versions monolítiques es conserven a `history/clips/` (de la v1_5 a la v1_9). Des de la integració RDF el nucli actiu **divergeix intencionalment** de v1.8 a nivell de representació: s'ha eliminat la topologia duplicada del `deffacts`. Per tant, `--check-baseline` ja no és una prova de pre-push; només serveix per comparar amb la fita històrica.


## Verificació ràpida abans d'un push

Des de `simulador/`:

```bash
python verificacio/e0_ontologia.py
python clips_core/build_clips.py --check-generated
python verificacio/casos_prova.py
python verificacio/e2_graella.py --rapid
python verificacio/e3_llindars.py
python verificacio/e1_regressio.py
```

Amb la v1_9, E1 ha de donar fail 0: també la versió canònica (`actual`, 79 proves), que es prova amb la topologia de `ontologia_model.rdf` (E1 la projecta a `clips_core/topologia_rdf.clp`, un fitxer generat). Les snapshots històriques es reprodueixen sense injectar l'ontologia. E0 ha de sortir OK, E3 75/75 i els casos de prova 13/14: `CP01` és una discrepància coneguda i analitzada, i `CP02`–`CP14` passen.

## Regla d'iteració

1. Canviar el vocabulari/esquema general a `ontologia_domini.rdf` només si canvia el domini.
2. Canviar la topologia o les instàncies estàtiques a `ontologia_model.rdf`, sempre usant el vocabulari canònic del domini.
3. Canviar regles/plantilles/llindars operacionals als mòduls de `simulador/clips_core/`.
4. Regenerar `soar.clp` amb `build_clips.py`.
5. Executar E0 + regressió + casos de prova.
6. Documentar qualsevol canvi funcional a `simulador/REGISTRE_ITERACIONS.md`.
7. No modificar els snapshots de `history/`.
