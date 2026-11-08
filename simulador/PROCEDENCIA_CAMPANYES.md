# Proveniència de les campanyes i estat de reproducció

Aquest document distingeix **identitat del codi CLIPS** i **data/commit del protocol o dels resultats**. No s'ha tornat a executar el motor CLIPS per generar aquesta correcció documental: les xifres corresponen als resultats guardats al ZIP aportat el 08/11/2026.

## Nucli de control

`simulador/clips_core/soar.clp` és **idèntic byte a byte** a `8c6ad6a`, `cf24769` i `f00a619` (verificat amb `git show` i SHA-256).

`8fbb6ad664ddac8bbaf488d883cecd92830a88c473087c8cc2eaba825fd7bf46`

Aquest resultat permet comparar protocols que comparteixen regles de producció, però **no** equival a assegurar que els scripts de verificació, les dades d'entrada, les llavors o els arxius CSV siguin idèntics entre commits. L'últim HEAD de Git de la còpia rebuda és `f00a619`; els canvis documentals lliurats en aquesta carpeta no s'han comès a Git.

## Fites documentades

| Fita | Referència Git | Què es pot acreditar al repositori | Limitació |
|---|---|---|---|
| Campanya principal amb refresc CLIPS | `8c6ad6a` (07/11/2026) | Resultats principals regenerats a la campanya documentada, amb E1 90/90, E3 85/85 i resultats d'E4--E24 guardats | E2 conserva una campanya històrica amb denominador 88; els experiments que comparen versions anteriors no són executats necessàriament sobre el mateix nucli |
| Ablació d'especificitat E11b | `cf24769` (08/11/2026) | `verificacio/e11_especificitat.py`, 9 files a `resultats/E11/E11_especificitat.csv` i seqüències de dispar a `.md` | El ZIP original no incloïa nou fitxers de traça sencers; el script actualitzat els genera en una nova execució real |
| Casos CP20--CP26, E17 i E23 anual | `f00a619` (08/11/2026) | 26 casos documentats, E17 109/112 (3 mutants equivalents segons anàlisi), resultats E23 d'un any a `resultats/E23/any_2023/` | El conjunt de proves canvia respecte de la campanya principal, encara que el CLIPS canònic no canvia |
| Versions històriques / E9, E10 | `history/clips/` i `REGISTRE_ITERACIONS.md` | Snapshots conservats intencionadament per comparar política i representació | No es poden sumar resultats com si fossin execucions del mateix executable |

## Reproduir i auditar E11b

Amb dependències instal·lades i des de `simulador/`:

```bash
python clips_core/build_clips.py --check-generated
python verificacio/e0_ontologia.py
python verificacio/e11_especificitat.py
```

El script guarda 9 sortides `watch rules` + `watch activations` a `resultats/E11/traces_watch/`, i `resultats/E11/E11b_manifest_traces.json` amb el SHA-256 del nucli, de cada variant i de cada traça. Les traces no es consideren generades fins a executar el script correctament.

## Condicions per a la defensa

1. Instal·lar el projecte en l'equip real i executar E0, E1, CP01--CP26, E3 i E11b.
2. Comprovar que la visualització web (Mode Defensa) mostra fets, riscos, operadors, preferències, regles disparades, ordres i efecte físic als casos triats.
3. Assajar CP05 i CP06, el canvi d'escenari de vent i la intervenció explicativa dels quatre membres.
4. Només consignar data, sistema operatiu, navegador i resultat com a **assaig realitzat** després de completar-lo.

La integritat d'arxius i les comprovacions estàtiques no substitueixen la reproducció del motor CLIPS ni de la UI.
