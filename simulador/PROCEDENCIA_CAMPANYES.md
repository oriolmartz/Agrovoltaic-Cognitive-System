# Procedència de les campanyes

Tots els resultats de l'informe s'han obtingut executant el mateix nucli CLIPS. `simulador/clips_core/soar.clp`
és idèntic byte a byte a tots els commits citats (SHA-256
`8fbb6ad664ddac8bbaf488d883cecd92830a88c473087c8cc2eaba825fd7bf46`).

## Fites

| Fita | Commit | Què s'hi va executar | Observacions |
|---|---|---|---|
| Execució completa de la versió final | `8c6ad6a` (07/11/2026) | E0–E24 (inclosos E2 complet, 24.500 casos, i E17), casos de prova, mesura del temps per cicle; un sol procés i amb el refresc de l'entorn CLIPS | Respecte de l'execució anterior, cap decisió, energia, estrès ni impasse va canviar; només els temps |
| Ablació de l'especificitat (E11b) | `cf24769` (07/11/2026) | `verificacio/e11_especificitat.py`: 9 execucions | Tornada a executar al commit final amb la captura de traces: `resultats/E11/traces_watch/` i `E11b_manifest_traces.json` (SHA-256 del nucli, de cada variant i de cada traça). Els ordres de dispar coincideixen amb la primera execució |
| Casos CP20–CP26, E17 i E23 d'un any | `f00a619` (08/11/2026) | 26 casos, E17 (109/112) i E23 amb 364 dies | Les proves noves amplien el conjunt de proves; el nucli CLIPS no canvia |
| Verificació al commit final | posterior a `9554497` (09/11/2026) | E0, generació del `.clp`, E1 (90/90), E3 (85/85), casos (26/26) i E11b | Comprovació que el lliurament final reprodueix els resultats |

## Notes

- **E2** fa servir 88 regles com a denominador de cobertura perquè compta els mòduls de decisió: les 4 regles de
  `SEMANTICA` no s'activen a la graella, on la memòria està apagada. No és una campanya antiga.
- **E9 i E10** comparen versions anteriors del nucli (`history/clips/`) a propòsit: el seu objectiu és comparar
  representacions del reforç.
- Els temps per cicle varien un 5–15 % entre execucions; només es comparen configuracions mesurades dins d'una
  mateixa execució.

## Reproduir E11b

```bash
python clips_core/build_clips.py --check-generated
python verificacio/e0_ontologia.py
python verificacio/e11_especificitat.py
```
