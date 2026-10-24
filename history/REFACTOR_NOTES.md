# Refactor CLIPS v1.8

Objectiu: separar el monòlit CLIPS per responsabilitats sense canviar el comportament.

## Canvis

- `history/clips/simulator/soar_v1_8.clp` es conserva intacte com a baseline històrica.
- La font de treball es divideix en 9 mòduls sota `simulador/clips_core/{core,memory,reasoning,deliberation,action}`.
- `simulador/clips_core/build_clips.py` concatena els mòduls segons `modules.txt` i genera `simulador/clips_core/soar.clp`.
- `config.json`, E2, E3 i els casos de prova apunten ara al `soar.clp` canònic.
- E1 i els `run_soar_v1_x.clp` històrics es mantenen intactes.
- `simulador/clips_core/run_soar.clp` és un run manual mínim: carrega, reset i run.

## Garantia del refactor inicial

`soar.clp` generat i `history/clips/simulator/soar_v1_8.clp` són byte a byte idèntics:

`SHA256 8ee49d35aaf97af8788bb5c678d3bd023f89cbc994eabe8b928609ba9ec27da1`

Això permet començar la següent iteració (p. ex. v1.9) editant fitxers petits i tornar a executar tota la bateria de regressió.

## v1.9 sobre l'estructura modular (24/10)

- Els mòduls de `clips_core/` passen a contenir la **v1_9**: la v1_6 (l'equip descarta les parelles de la v1_7), la correcció de `nivell-hidric` de la v1_8 i la decisió de **reg**. El repartiment entre mòduls és el mateix: els blocs nous del reg són a `core/domini.clp` (plantilles), `reasoning/deliberacio.clp` (elaboració, proposta i avaluació), `reasoning/decisio.clp` (selecció) i `action/accio.clp` (aplicació i explicació). `memory/reinforcement.clp` torna a la versió de la v1_6 (sense parelles).
- `history/clips/simulator/soar_v1_9.clp` i `run_soar_v1_9.clp` són la v1_9 en un fitxer autònom (amb la topologia al `deffacts`, com les versions anteriors). Després de la integració RDF, el nucli canònic carrega la topologia de l'ontologia; `--check-baseline` continua comparant amb la v1_8 i ha de donar `DIFERENT`.
- `clips_core/run_proves.clp`: proves de la versió canònica (79). E1 les executa com a `actual`: primer projecta la topologia del RDF a `clips_core/topologia_rdf.clp` (generat, ignorat per git) i comprova que `soar.clp` està al dia amb els mòduls.
