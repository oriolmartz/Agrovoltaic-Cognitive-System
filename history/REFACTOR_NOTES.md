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
