# Agrovoltaic-Cognitive-System

Sistema basat en regles per a una instal·lació agrovoltaica, amb un nucli cognitiu inspirat en SOAR implementat en CLIPS i una capa Python per a simulació, dades, integració RDF i experimentació.

## Arquitectura

```text
ontologia_domini.rdf
        │  TBox: vocabulari, jerarquia i domain/range
        ▼
validació del model
        ▲
        │
ontologia_model.rdf
        │  ABox: instàncies i estat estàtic inicial
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

`ontologia_domini.rdf` és el **contracte conceptual executable** (TBox): defineix les classes i propietats que consumeix el runtime i les seves relacions `domain/range`. `ontologia_model.rdf` és la **instanciació concreta** (ABox) i la font canònica de la topologia estàtica: sectors, cultius, panells, sensors i estat inicial dels panells. `ontology_loader.py` valida primer el model contra el domini i només després el projecta a fets CLIPS. Python no avalua candidats ni selecciona accions: **la decisió continua íntegrament dins de CLIPS**.

Els llindars agronòmics i els objectius de control continuen explícits a CLIPS perquè l'ontologia actual encara no n'instancia els valors operacionals.

## Estructura

```text
.
├── ontologia_domini.rdf       # TBox: esquema/contracte del domini, carregat per validar
├── ontologia_model.rdf        # ABox: instanciació concreta carregada en temps d'execució
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

- `ontologia_domini.rdf` i `ontologia_model.rdf` es poden interpretar;
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

La v1.8 monolítica original es conserva a `history/clips/`. Des de la integració RDF el nucli actiu **divergeix intencionalment** de v1.8 a nivell de representació: s'ha eliminat la topologia duplicada del `deffacts`. Per tant, `--check-baseline` ja no és una prova de pre-push; només serveix per comparar amb la fita històrica.

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

`E1` continua reproduint les snapshots històriques sense injectar la integració ontològica nova. Les proves sobre `clips_core/soar.clp` carreguen primer `ontologia_domini.rdf` per validar el contracte i després `ontologia_model.rdf` per instanciar la topologia abans de decidir.

## Regla d'iteració

1. Canviar el vocabulari/esquema general a `ontologia_domini.rdf` només si canvia el domini.
2. Canviar la topologia o les instàncies estàtiques a `ontologia_model.rdf`, sempre usant el vocabulari canònic del domini.
3. Canviar regles/plantilles/llindars operacionals als mòduls de `simulador/clips_core/`.
4. Regenerar `soar.clp` amb `build_clips.py`.
5. Executar E0 + regressió + casos de prova.
6. Documentar qualsevol canvi funcional a `simulador/REGISTRE_ITERACIONS.md`.
7. No modificar els snapshots de `history/`.
