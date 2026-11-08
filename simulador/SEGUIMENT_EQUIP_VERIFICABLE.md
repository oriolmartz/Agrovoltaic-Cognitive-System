# Seguiment setmanal reconstruït a partir del registre existent

Aquest document és una **síntesi retrospectiva** de `REGISTRE_ITERACIONS.md` i de l'historial Git; no és una acta de reunions, ni prova d'objectius pactats abans de cada setmana, ni atribueix tasques individuals que no estan registrades. El repartiment de responsables i revisors s'ha declarat a l'Annex F de la memòria.

| Període del registre | Fites tècniques observables | Evidència consultable |
|---|---|---|
| 16–22 d'octubre de 2026 | Chunks, gestió de dades de vent, primeres comparatives E2/E3 i experimentació de reforç | Iteracions 0–10 de `REGISTRE_ITERACIONS.md`; snapshots CLIPS històriques |
| 23–29 d'octubre de 2026 | Detecció i correcció de límits del simulador, agenda i control de salience; revisió de mètriques i traçabilitat | Iteracions datades del registre i resultats d'E4–E15 |
| 30 d'octubre–5 de novembre de 2026 | Integració RDF, reg i verificació ampliada; correccions de CP01 i control de regressió | Iteracions datades de `REGISTRE_ITERACIONS.md`, ontologies RDF i E0/E1/CP |
| 6–8 de novembre de 2026 | E1 90/90, memòries, E11b, CP20–CP26, E17 109/112 i E23 anual | Iteracions 37–43, commits `8c6ad6a`, `cf24769`, `f00a619` i `resultats/` |

## Decisions i incidències verificables

- CP01: evitar proposar producció si l'angle ja és l'òptim (iteració 30).
- E1: reparar casos que truncaven la bateria i comprovar-ne la finalització explícita (iteració 37).
- Refresc CLIPS: evitar l'acumulació de latència, conservant decisions (iteració 39).
- E23: repetir temporitzacions amb llavors i sense competència de processos (iteració 40).
- E11b: separar especificitat, estratègia i salience (iteració 42).
- E17: ampliar casos i comprovacions per reduir mutants no detectats (iteració 43).

## Informació que ha de validar el grup

No hi ha registres verificables de **reunions per setmana, assistència, dates de revisió per persona, incidències de coordinació personal ni objectius pactats a priori**. Aquests detalls s'han d'afegir només quan algun membre els pugui acreditar. L'historial de Git acredita canvis en fitxers, però no permet deduir automàticament qui va revisar o decidir cada part.
