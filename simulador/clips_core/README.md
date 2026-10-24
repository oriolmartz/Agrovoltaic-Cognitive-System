# Nucli CLIPS modular

La font de treball està separada per responsabilitats cognitives. `soar.clp` és un artefacte generat per concatenació perquè `clipspy` i les eines d'experimentació puguin carregar un únic fitxer.

## Estructura

```text
clips_core/
├── core/
│   ├── domini.clp              # DOMINI: templates + coneixement operacional estàtic
│   └── main.clp                # MAIN
├── memory/
│   ├── episodic.clp            # MEMORIA: epmem
│   ├── reinforcement.clp       # REFORC: Q / RL
│   └── chunking.clp            # APRENENTATGE: chunking procedural
├── reasoning/
│   ├── deliberacio.clp         # percepció, elaboració, proposta, avaluació
│   └── decisio.clp             # selecció i detecció d'impasses
├── deliberation/
│   └── impasses.clp            # resolució de subobjectius/impasses
├── action/
│   └── accio.clp               # aplicació, explicació i monitoratge
├── modules.txt                 # ordre de build
├── build_clips.py
├── soar.clp                    # GENERAT, punt d'entrada de clipspy
└── run_soar.clp                # smoke test manual; no carrega RDF
```

## RDF i `domini.clp`

La topologia concreta **no** s'instancia a `domini.clp`. `../../ontologia_model.rdf` importa `../../ontologia_domini.rdf` i només conté l'ABox de la planta; no redeclara classes ni propietats. Abans d'injectar res, `../ontology_loader.py` carrega les dues ontologies, valida l'import, el vocabulari i els `domain/range`. Després de `(reset)`, la instanciació del model es projecta a `sector`, `cultiu`, `panell` i `estat-sensor`.

`domini.clp` conserva els `deftemplate` i el coneixement operacional que el RDF actual encara no instancia: llindars agronòmics, objectius, prioritats, conflictes i activacions.

Això evita tenir dues fonts de veritat per a la planta sense traslladar cap decisió a Python.

## Regla de treball

Editeu els fitxers modulars i després regenereu el monòlit:

```bash
python clips_core/build_clips.py
python clips_core/build_clips.py --check-generated
```

La v1.8 original es conserva intacta a `../../history/clips/simulator/`. `--check-baseline` continua disponible com a comparació històrica, però des de la integració RDF és normal que doni `DIFERENT`.

Per comprovar el mapping RDF abans de provar el controlador:

```bash
python verificacio/e0_ontologia.py
```
