# Nucli CLIPS modular

La font de treball està separada per responsabilitats cognitives. `soar.clp`
és un artefacte generat per concatenació, mantingut perquè `clipspy`, els
experiments i les eines de verificació puguin carregar un únic fitxer sense
canviar el comportament.

## Estructura

```text
clips_core/
├── core/
│   ├── domini.clp              # DOMINI: templates, fets inicials i contracte WM
│   └── main.clp                # MAIN
├── memory/
│   ├── episodic.clp            # MEMORIA: epmem
│   ├── reinforcement.clp       # REFORC: Q / RL
│   └── chunking.clp            # APRENENTATGE: chunking procedural
├── reasoning/
│   ├── deliberacio.clp         # percepcio, elaboracio, proposta, avaluacio
│   └── decisio.clp             # seleccio i deteccio d'impasses
├── deliberation/
│   └── impasses.clp            # resolucio dels subobjectius/impasses
├── action/
│   └── accio.clp               # aplicacio, explicacio i monitoratge
├── modules.txt                 # ordre de build
├── build_clips.py
├── soar.clp                    # GENERAT, punt d'entrada de clipspy
└── run_soar.clp                # execucio manual minima
```

## Regla de treball

Editeu els fitxers modulars i després regenereu el monòlit:

```bash
python clips_core/build_clips.py
```

Per comprovar que el refactor inicial és exactament equivalent a v1_8:

```bash
python clips_core/build_clips.py --check-baseline
```

En el refactor inicial, `soar.clp` és byte a byte idèntic a
`../../history/clips/simulator/soar_v1_8.clp`. A partir de la següent iteració, és normal que deixi de ser-ho.

`../../history/clips/simulator/run_soar_v1_8.clp` es conserva intacte perquè E1 pugui continuar reproduint la regressió històrica de la v1_8.
