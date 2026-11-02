# Afegir un lloc o més dades

Cada fitxer `*.json` d'aquesta carpeta registra un lloc a `dades.LLOCS`. No cal tocar el
codi: la web (`python webapp.py`) mostra automàticament l'escenari **«Totes les dades»** del lloc
nou, amb la durada en dies calculada a partir de les dades.

1. Deixa a `dades_reals/` els tres fitxers del lloc (vegeu `FONTS.md`): Open-Meteo (`.json`),
   XMS-Cat (`.csv`) i PVGIS (`.json`).
2. Copia `exemple.json.plantilla` com a `<id>.json` (l'`id` és el nom del lloc als escenaris,
   camp `"lloc"`) i omple els camps.
3. Comprova-ho: `python dades.py` (taula de cobertura) i `python verificacio/e17_periode.py`.

Per **ampliar un lloc existent** (més mesos al mateix període) n'hi ha prou amb substituir els
fitxers de dades per versions més llargues i actualitzar el nom del fitxer a `dades.LLOCS` o al
JSON del lloc. Els escenaris que no fixen `"dies"` agafen tots els dies disponibles, així que
creixen sols.
