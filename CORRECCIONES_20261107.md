# Ajustos de tancament — 07/11/2026

Aquest ZIP parteix de `Agrovoltaic-Cognitive-System(20261107-195014).zip`. **No s'han modificat els mòduls ni les regles CLIPS, les ontologies ni els valors científics dels experiments.** Tampoc no s'ha editat la memòria LaTeX.

## Correccions incloses

1. **Mode Defensa:** `webcore.py` activa `vigila_regles` quan la UI sol·licita `demo`; `clips_bridge.py` llegeix els valors de preferències, angles-objectiu i alternatives/preferències del reg; `simulador.py` els envia en el camp `demo`. La captura de dades addicionals només es fa quan `captura_demo` és activa; no afegeix aquest treball a E2/E11/E23 ni a les simulacions habituals.
2. **CP01:** `simulador/CASOS_PROVA.md` s'ha sincronitzat amb `resultats/casos_prova/CASOS_PROVA.md` (19/19). El fitxer anterior es conserva a `simulador/historic/CASOS_PROVA_13_de_14_historic.md`. El generador ara actualitza tots dos documents.
3. **E1/E2:** s'han restaurat des de `HEAD` del Git inclòs al ZIP el resum complet E1 (versió actual i cinc versions històriques) i la campanya E2 completa (24.500 casos, 73.500 decisions). La campanya E2 ràpida posterior es conserva com a `_rapid_20261107`. Des d'ara, E1 parcial i E2 ràpid escriuen resultats amb noms separats per no perdre les campanyes completes.
4. **Verificació automàtica:** `casos_prova.py`, `e2_graella.py` i `e3_llindars.py` retornen un codi de sortida no-zero quan hi ha fallades de les comprovacions corresponents.
5. **README:** arquitectura amb tres ontologies i dos actuadors, xifres 19/19 i 85/85, distinció de campanyes històriques, ús de Mode Defensa i explicació de CP01 corregits.

## Comprovacions efectuades en aquest entorn

- E0 ontologies: OK.
- `build_clips.py --check-generated`: OK, 10 mòduls.
- Compilació sintàctica de Python: OK.
- Verificació estàtica de la UI i sintaxi JS: OK.
- Contracte de dades de Mode Defensa i activació en configuració: OK mitjançant dades sintètiques i dobles de prova.
- E1 restaurat: `actual` 90/90, històrics 46/46, 55/55, 59/59, 59/59 i 79/79; E2 complet sense violacions. **Són resultats guardats, no noves execucions CLIPS en aquest entorn.**

## Per verificar en Windows (amb clipspy instal·lat)

Des de `simulador/`:

```powershell
python verificacio/e0_ontologia.py
python clips_core/build_clips.py --check-generated
python verificacio/e1_regressio.py actual
python verificacio/casos_prova.py
python verificacio/e3_llindars.py
python verificacio/e2_graella.py --rapid --processos 4
python verificacio/ui_frontend.py
python webapp.py
```

Per comprovar el Mode Defensa, obriu `http://127.0.0.1:8000`, activeu-lo i executeu **un dia** amb el controlador SOAR. Comproveu que la traca de regles, preferències numèriques, candidats i alternatives de reg es mostren amb dades reals; després feu un assaig amb un escenari modificat. La prova funcional CLIPS/UI no s'ha pogut executar aquí perquè no hi havia `clipspy`.

**Important:** una execució E1 parcial crea `e1_regressio_actual.json`; la completa és `e1_regressio.json`. Una E2 ràpida nova crea `e2_graella_soar_rapid.csv/.json` i `e2_reg_soar_rapid.csv`; els informes de la campanya completa no se sobreescriuen.
