# Simulador i banc de proves del controlador SOAR (CLIPS + clipspy)

Aquest directori connecta el sistema basat en regles (`clips_core/soar.clp` (generat des dels mòduls)) amb un model
de la planta alimentat amb dades meteorològiques reals de 2023, i conté les eines de
verificació, validació i experimentació.

## Instal·lació (des d'un entorn net)

Calen **Python 3.11, 3.12 o 3.13**. Des de la carpeta `simulador`:

```
python -m venv venv
venv\Scripts\activate            (Windows)   ·   source venv/bin/activate   (Linux/Mac)
python -m pip install -r requirements.txt
python verificacio/e1_regressio.py      # comprovació: totes les versions han de sortir amb fail 0
```


## Nucli CLIPS modular

La versió de treball ja no s'edita com un monòlit. Les regles estan separades per
responsabilitat cognitiva i `clips_core/soar.clp` es genera automàticament:

```
python clips_core/build_clips.py
python clips_core/build_clips.py --check-baseline   # només per al refactor inicial
```

El `run_soar.clp` nou és només un punt d'entrada manual mínim. Les versions i els `run_soar_v1_x.clp` històrics es conserven fora del nucli actiu, a `../history/clips/simulator/`, per a E1 i la reproducció històrica.

## Executar-ho tot

Amb 12 nuclis triga uns 10 minuts. Amb 2, uns 40 (E8 i E9 són els més llargs):

```
python verificacio/e1_regressio.py          # E1  regressió de totes les versions del CLIPS
python verificacio/e2_graella.py            # E2  graella exhaustiva (--rapid: versió reduïda)
python verificacio/e3_llindars.py           # E3  57 casos als llindars
python verificacio/casos_prova.py           # 11 casos de prova documentats -> CASOS_PROVA.md
python simulador.py escenaris/dia_normal.json                  # un dia, amb la traça del CLIPS
python simulador.py escenaris/cas_no_vist_tramuntana.json      # cas no vist (dades reals)
python experiments.py E4                    # seguretat amb vent real (Cantallops)
python experiments.py E5                    # sensor de vent que falla
python experiments.py E6                    # fallades d'actuador
python experiments.py E7 --dies 48          # SOAR contra el seguidor comercial i el panell fix
python experiments.py E8 --dies 10          # chunking (aprenentatge, ~10 execucions)
python experiments.py E9 --dies 10          # reforç v1_5 / v1_6 / v1_7
python experiments.py E10                   # capacitat de la funció Q (AND / XOR)
python experiments.py E11                   # agenda: estratègies, especificitat i salience
python experiments.py E12                   # sensibilitat del model i de la previsió
python experiments.py E13                   # consistència del coneixement après
python experiments.py E14                   # escenaris extrems: calor, sequera i vent
```

Opcions: `--processos N` (per defecte, tots els nuclis), `--traca` (desa la traça del CLIPS) i
`--clp ../history/clips/simulator/soar_v1_x.clp` (a E2 i E3, per provar una versió històrica). Per a les simulacions, la
versió del CLIPS es tria a `config.json` (`"clp"`).

Cada experiment desa els resultats a la seva carpeta: `resultats/E1/`, `resultats/E2/`… i les
simulacions soltes a `resultats/simulacions/`.

**Traça del CLIPS** (el mateix que es veu amb `run_soar`: percepció, elaboració, proposta,
avaluació, selecció, impasses, explicació…):
- `simulador.py` la desa sempre a `resultats/simulacions/traca/`, un fitxer per dia (`--sense-traca` per no desar-la);
- `experiments.py` la desa només si s'hi afegeix `--traca`, a `resultats/<E>/traca/`
  (per exemple `python experiments.py E7 --dies 48 --traca`). Ocupa uns 80 kB per dia;
- E1 desa la sortida completa de cada `run_soar_v1_x.clp` a `resultats/E1/traca_run_soar_v1_x.txt`.

## Fitxers

| Fitxer | Què fa |
|---|---|
| `clips_core/soar.clp` | Punt d'entrada canònic del simulador. Es genera a partir dels mòduls de `clips_core/modules.txt`. |
| `clips_core/core/`, `memory/`, `reasoning/`, `deliberation/`, `action/` | Font CLIPS modular, separada per responsabilitats cognitives. |
| `../history/clips/simulator/soar_v1_8.clp` | Baseline monolítica congelada per a regressió i comparació. |
| `clips_core/build_clips.py` | Regenera `soar.clp` i pot comprovar equivalència amb la baseline v1_8. |
| `clips_bridge.py` | Pont Python ↔ CLIPS. Només coneix el contracte de memòria de treball, no el domini. |
| `dades.py` | Llegeix i fusiona Open-Meteo, XMS-Cat i PVGIS (vegeu `dades_reals/FONTS.md`). |
| `fisica.py` | Model físic simplificat: sol, producció, llum i temperatura del cultiu, aigua al sòl. |
| `simulador.py` | Bucle horari, sensors, previsió amb soroll, actuadors i fallades, controladors de referència, invariants. |
| `metriques.py` | Mètriques per dia (energia, hores d'estrès, seguretat, moviments, impasses, chunks…). |
| `estadistica.py` | Wilcoxon, Friedman + Holm, mida de l'efecte, IC bootstrap, cota de taxes rares, mida de mostra. |
| `experiments.py` | Experiments E4–E14. |
| `paralel.py` | Execució en paral·lel amb progrés, Ctrl+C i detecció de processos penjats. |
| `escenaris/` | Escenaris JSON per a `simulador.py` (dia normal i cas no vist). |
| `dades_reals/` | Dades de 2023 (Open-Meteo, XMS-Cat, PVGIS) i `FONTS.md`. |
| `CASOS_PROVA.md` | Els casos de prova documentats (es regenera amb `verificacio/casos_prova.py`). |
| `EXPERIMENTS.md` | Catàleg: pregunta, perspectiva de V&V, disseny, test i ordre de cada experiment. |
| `REGISTRE_ITERACIONS.md` | Registre d'iteracions (observació → experiment → canvi → regressió). |
| `verificacio/` | E1 (regressió), E2 (graella exhaustiva: anomalies de Preece, seguretat, monotonia, cobertura), E3 (casos als llindars) i els casos de prova documentats (`casos_prova.py`). |
| `config.json` | Paràmetres per defecte. Un escenari JSON pot sobreescriure qualsevol clau. |

## Contracte amb el CLIPS (el que NO es pot canviar sense avisar)

El simulador només escriu i llegeix aquests fets. Si es canvia un nom de plantilla o de
slot, cal tocar `clips_bridge.py`.

| Direcció | Fets |
|---|---|
| Python → CLIPS | `observacio`, `prediccio`, `energia` (amb el `cicle`), `estat-sensor` (modifica `operatiu`, `qualitat`, `cicle-ultima-lectura`), `panell` (modifica `angle`, `angle-optim-produccio`, `disponible`, `estat-mecanic`), `fase` (`espera` → `percepcio`) |
| CLIPS → Python | `ordre-actuador`, `operador-seleccionat`, `explicacio`, `risc`, `preferencia` (per saber si ha decidit un chunk o el reforç), `operador`, `subobjectiu` (impasses), `fragment-apres`, `rl-valor`, `epmem-episodi` |
| Control | `cicle` (el CLIPS l'incrementa a `tanca-cicle`), `fase` final ha de ser `espera` |
| Interruptors | `REFORC::activa-reforc`, `REFORC::activa-parelles`, `APRENENTATGE::activa-chunking`, `MEMORIA::epmem-aprenentatge` |

El `deffacts escenari-1` porta dades del cicle 1: el pont les esborra i hi posa les del simulador.
El pont també **esborra els fets de cicles vells** (més de 3 cicles enrere): el CLIPS mai no mira
més enllà de `c-2`, i així la memòria de treball no creix. La memòria a llarg termini
(`epmem-episodi`, `rl-valor`, `fragment-apres`) no es toca.

## Com funciona una hora (un cicle)

1. El controlador **veu** el que els sensors han mesurat l'hora anterior i una **previsió** per a
   l'hora que ve (valor real + soroll: ×lognormal σ=0,15 per al vent i la radiació, ±1 °C).
2. Decideix un operador i un angle per sector.
3. Els actuadors mouen els panells, o no (fallada aleatòria o programada).
4. El simulador calcula què **passa de debò** durant l'hora amb l'angle real.

La ratxa que fa mal al seguidor és `wind_gusts_10m` d'Open-Meteo. Es simulen les hores 7–20
(14 cicles per dia); de nit només avança el balanç hídric.

## Model físic (simplificacions que cal dir a l'informe)

| Què | Com | Paràmetre |
|---|---|---|
| Angle òptim | seguidor N-S d'un eix, posició solar NOAA, límit ±55° | — |
| Producció | `kWp · ratio · GHI/1000 · f(angle)`, amb `f = 0,25 + 0,75·cos(angle − òptim)` | `ratio` calibrat amb PVGIS: 1,04 (Ribera de Sió), 1,15 (Cantallops) |
| Llum al cultiu | `GHI · (1 − GCR·|cos(angle)|)`: panell pla = més ombra (supòsit del CLIPS, `angle-ombra = 0`) | GCR = 0,4 |
| Temperatura del cultiu | aire + 0,006·llum + 2·(1 − aigua) | — |
| Aigua al sòl | balanç horari FAO-56: `ETc = ET0·Kc·(0,3 + 0,7·llum relativa)`, pluja, reg a les 7 h si < 45 % | Kc i Zr per cultiu; CC/PM de la fitxa XMS-Cat |
| Demanda | base + pic de tarda (bombes, refrigeració) | 6 + 8 kW per sector |

Amb `"humitat": {"mode": "mesurada"}` la humitat és la de XMS-Cat (dada real), però llavors
l'ombra no hi pot influir.

**Atenció (validesa del domini).** En un seguidor real, la màxima ombra a terra es fa quan el panell
és perpendicular al sol, que és també la posició de màxima producció. El model segueix el
supòsit del CLIPS (pla = ombra) perquè és el que permet que hi hagi conflicte entre cultiu i energia.
S'ha de justificar a l'informe com a simplificació.

## Verificació i validació (marc de Menzies & Pecheur 2005)

| Característica del sistema | Prova | On |
|---|---|---|
| Model declaratiu | Anomalies de Preece: deficiència, regles en conflicte, regles mai disparades, monotonia | E2 |
| Executable aviat | Regressió a cada versió i registre d'iteracions | E1 |
| Nivell de coneixement | Casos positius i negatius als llindars, amb el resultat esperat escrit abans; casos de prova | E3, casos de prova |
| No determinista | Llavors de soroll, sensors i fallades; estratègies de l'agenda i salience | E5, E6, E11 |
| Complex | Invariants a cada cicle (`invariants_ko`); escenaris extrems; escalabilitat de la memòria | totes les simulacions, E14 |
| Adaptatiu | Aprendre en uns dies i mesurar-ho en uns altres (validesa externa); capacitat de la funció Q; consistència del que s'aprèn (Rashid) | E8, E9, E10, E13 |
| Comparació amb una referència (Batarseh) | Seguidor comercial i panell fix amb els mateixos dies | E4, E5, E7, E14 |
| Sensibilitat (Batarseh) | Un paràmetre del model cada cop | E12 |

## Resultats (23/10/2026, v1_8)

Detalls a `resultats/<E>/`. El catàleg complet (pregunta, perspectiva, disseny i test de cada
experiment) és a `EXPERIMENTS.md`, i les iteracions a `REGISTRE_ITERACIONS.md`.

### Verificació

| | Resultat |
|---|---|
| **E1** regressió | v1_5 46/46 · v1_6 55/55 · v1_7 59/59 · v1_8 59/59 |
| **E2** graella (24.500 casos × 3 sectors) | 0 violacions de seguretat, deficiència o conflicte · 0 casos no monòtons amb el vent · cobertura 39/63 regles (61,9 %) |
| **E3** llindars (57 casos) | v1_7 56/57 (l'A07 falla per coma flotant) → **v1_8 57/57** |
| **E11** agenda (20 dies) | Estratègies `depth`, `breadth`, `lex` i `mea`, especificitat (`simplicity` i `complexity`) i `random` amb 5 llavors: **0 decisions diferents** de 840. Al pilot de 6 dies, `random_2` en va canviar 1 de 252: un empat desfet pel reforç (vegeu el registre, iteració 13). **Salience:** si les transicions de fase passen de −10 a 0, amb `depth` canvia el **21,9 %** de les decisions, perquè les fases s'acaben abans que s'avaluïn tots els operadors. Amb `breadth` no es tanca **cap** cicle: 0 ordres i tots els invariants trencats. La salience −10 de les transicions és imprescindible, i és l'únic que garanteix les fases |
| **E13** coneixement après (5 execucions × 20 dies) | 0 problemes a les 8 restriccions (K1–K8), en 100 fotos. En acabar: 2–4 chunks, 190–230 rajoles Q (\|Q\| ≤ 0,47) i 840 episodis (exactament 1 per sector i cicle) |
| **Invariants** | 0 violacions en totes les simulacions |

Les regles que E2 no dispara mai són de tres menes:
- **Aprenentatge o memòria**, que a la graella està apagat.
- **Les que necessiten més d'un cicle:** `percep-fallada-actuador`, `avalua-estabilitat`, `detecta-oscillacio`…
- **Potser inabastables (cal revisar-les):**
  - `percep-dades-vent-critic`, gairebé sempre tapada per `percep-lectura-absent`, que ja posa crític quan falta el vent;
  - `percep-sensor-no-valid`, que només es dispara amb un sensor incoherent i una lectura que sí que arriba;
  - `detecta-impas-sense-candidat` i `resol-sense-candidat`, perquè amb vent crític sempre queda `posicio-seguretat`;
  - `avalua-rebuig-fora-de-limits`, perquè l'angle òptim sempre és dins dels límits.

### Casos de prova documentats (11 + 1 cas no vist)

`python verificacio/casos_prova.py` → `resultats/casos_prova/CASOS_PROVA.md`, amb les entrades,
el resultat esperat (escrit abans), l'obtingut, l'explicació del sistema i la traça rellevant de
cada cas.

- **10 de 11 correctes.**
- **CP01 té una discrepància analitzada:** al segon cicle el sistema repeteix `orientar-produccio`
  en lloc de `mantenir-posicio`. Ho fa per l'estabilitat i per la memòria episòdica. L'angle és el
  mateix i el panell no es mou, així que el comportament és correcte, però l'expectativa estava
  massa especificada.
- **Cas no vist (tramuntana del 27/03/2023 a Cantallops):** SOAR, 0 violacions i 2 h d'exposició.
  Seguidor comercial, 3 violacions i 9 h d'exposició.

### Validació

**E4 – vent real a Cantallops** (95 dies, 567 hores-sector amb ratxa ≥ 16 m/s):

| | Hores en posició de treball amb ratxa ≥ 16 m/s | Cota superior 95 % | Energia |
|---|---|---|---|
| Seguidor comercial | 56 (9,9 %) | 12,2 % | 277 kWh/dia |
| SOAR | **0** | **0,53 %** | 263 kWh/dia (−5 %) |

**E5 – el sensor de vent falla** (40 dies de vent × 3 llavors):

| Lectures que no arriben | 0 % | 5 % | 20 % |
|---|---|---|---|
| Violacions/dia, seguidor comercial | 1,23 | 1,16 | 0,91 |
| Violacions/dia, SOAR | 0 | 0 | 0 |
| Impasses de dades/dia, SOAR | 0,05 | 1,35 | 2,61 |

Amb el sensor caigut, SOAR fa servir la previsió i l'historial, i perd 1,2 kWh al dia amb un 20 % de lectures perdudes.

**E6 – fallades d'actuador** (5 % per panell i cicle, 40 dies × 3 llavors):
- 0 violacions i 0 invariants trencats.
- Només perd 0,9 kWh al dia.
- Canvia més d'operador: 9,2 canvis/dia contra 7,9 (p = 9e-13).

**E7 – Ribera de Sió, 48 dies** (Friedman i Wilcoxon amb Holm):

| | Panell fix | Seguidor comercial | SOAR |
|---|---|---|---|
| Energia (kWh/dia) | 341 | 397 | 368 (−7,3 % respecte del seguidor) |
| Estrès per radiació (h/dia) | 12,6 | 15,0 | 13,7 |
| Estrès per calor (h/dia) | 22,9 | 23,4 | 23,3 |
| Exposició a vent ≥ 12 m/s (h/dia) | 0 | 1,79 | 0,15 |
| Canvis d'operador/dia | 0 | 0,2 | 8,0 (el 25 % sense moure el panell) |
| Oscil·lacions reals (angle A → B → A)/dia | 0 | 0 | 0,19 |

**E8 – chunking** (pilot de 3 execucions; s'aprèn en 20 dies i es mesura en 10 de no vistos):
- **Amb chunking:** 0,03 impasses/dia, i els chunks prenen 35 decisions al dia.
- **Sense chunking:** 0,73 impasses/dia.
- **Les decisions finals són idèntiques** (energia, estrès…). Els chunks reprodueixen exactament el que hauria decidit el subobjectiu, que és el que ha de fer el chunking a Soar.
- **No acceleren:** cada cicle triga 2,5 ms més. Les regles noves tenen un cost de *matching* (el "problema de la utilitat").

**E9 – reforç** (pilot de 2 execucions):
- **El reforç decideix 1,3–1,5 de les 42 decisions diàries.**
- **Energia i estrès són iguals** entre v1_5, v1_6 i v1_7.
- **El temps per cicle creix fins a 63–71 ms** després de 20 dies. La causa és la memòria episòdica.

**E10 – capacitat de la funció Q** (30 llavors, 400 mostres; encert de la política a 4 estats):

| | Tasca AND | Tasca XOR |
|---|---|---|
| v1_6 (trets sols) | 100 % | 50 % (com a l'atzar) |
| v1_8 sense parelles | 100 % | 50 % |
| v1_8 amb parelles | 100 % | **100 %** (p = 1e-6) |

Les parelles sí que aprenen interaccions que els trets sols no poden representar. Si a E9 no milloren
res, és perquè **el reforç gairebé no arriba a decidir**, no perquè la representació falli.

**E14 – escenaris extrems** (20 dies × 3 llavors per escenari):

| Escenari | Mètrica | Panell fix | Seguidor comercial | SOAR |
|---|---|---|---|---|
| **Calor** (els 20 dies més calorosos de Ribera, +3 °C) | Calor crítica (h/dia) | 30,9 | 31,3 | 31,0 |
| | Estrès per radiació (h/dia) | 14,1 | 16,3 | 14,2 |
| | Energia (kWh/dia) | 370 | 432 | 382 |
| **Sequera** (juliol–agost, sense reg) | Aigua al final del dia (%) | 70,8 | 70,5 | 70,7 |
| | Estrès hídric (h/dia) | 5,4 | 5,6 | 5,5 |
| **Vent** (els 20 dies amb més vent de Cantallops, ratxes +30 %) | Violacions/dia | 0 | 1,07 | **0** |
| | Exposició a vent ≥ 12 m/s (h/dia) | 0 | 3,4 | 0,13 |

- **Amb vent extrem**, SOAR continua sense cap violació, i en conserva el 98 % de l'energia.
- **Amb calor extrema**, SOAR treu 2 h d'estrès per radiació, però la calor crítica gairebé no baixa (−0,3 h, p = 8e-5). És el mateix límit del domini que a E7 i E12.
- **Amb sequera**, l'ombra estalvia una mica d'aigua (+0,3 punts al final del dia, p = 5e-11). La diferència és significativa però molt petita.
- **El risc "meteorològic advers" no surt mai:** la plantilla `risc` el preveu i l'ontologia també, però cap regla el genera. La pluja que arriba als sensors no la fa servir cap regla. És una deficiència de Preece: manca una regla.

**E12 – sensibilitat** (un paràmetre cada cop, 30 dies, SOAR − seguidor comercial):
- Totes les diferències mantenen el signe en tot el rang. Les conclusions d'E4 i d'E7 no depenen
  d'aquestes constants.
- La diferència d'estrès per calor no és significativa amb cap valor (p ≥ 0,18), ni doblant
  `k_rad`. La causa és el domini: al migdia, l'angle de màxima producció ja és gairebé pla, que és
  el que fa més ombra.
- La seguretat aguanta una previsió molt sorollosa (σ = 0,8) o sense previsió la meitat de les hores:
  0–0,03 violacions/dia per a SOAR, contra 1,4–1,5 del seguidor.

## Pendent

- **E8 i E9 complets** (10–30 execucions): quan l'equip tanqui el reforç.
- **E12, part de pesos i `alfa`:** són dins del CLIPS i no es poden variar des del simulador sense tocar el `.clp`.
- **Tornar-ho a executar tot** amb la versió final del CLIPS: les ordres són a `EXPERIMENTS.md`.
