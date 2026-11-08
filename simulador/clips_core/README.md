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
│   ├── chunking.clp            # APRENENTATGE: chunking procedural
│   └── semantic.clp            # SEMANTICA: consolidació d'episodis (smem), apagada per defecte
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
├── run_proves.clp              # proves de la versio canonica (E1 les executa)
├── topologia_rdf.clp           # GENERAT per E1 a partir del RDF (no es versiona)
└── run_soar.clp                # smoke test manual; no carrega RDF
```

## RDF i `domini.clp`

La topologia concreta **no** s'instancia a `domini.clp`. `../../ontologia_model.rdf` importa `../../ontologia_domini.rdf` i `../../ontologia_reg.rdf`; l'ontologia de reg importa el domini. El carregador `../ontology_loader.py` valida les **tres ontologies**, els imports, el vocabulari i els `domain/range`. Després de `(reset)` projecta els fets de topologia (`sector`, `cultiu`, `panell`, `estat-sensor`) i de reg (`reg-config`, objectius, prioritats i conflictes).

`domini.clp` conserva els `deftemplate`, llindars agronòmics o mecànics que no provenen de RDF i les produccions de decisió. Les preferències i la selecció dels operadors continuen dins de CLIPS; RDF només aporta coneixement declaratiu estable.

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

Per passar les proves de la versió canònica (90), executeu E1, que primer projecta la topologia del RDF a
`topologia_rdf.clp` i avisa si `soar.clp` no està al dia amb els mòduls:

```bash
python verificacio/e1_regressio.py actual
```

Un cop generat `topologia_rdf.clp`, també es pot fer a mà: `cd clips_core && clips -f run_proves.clp`.
