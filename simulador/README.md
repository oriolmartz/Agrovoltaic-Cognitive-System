# Simulador i banc de proves del controlador SOAR (CLIPS + clipspy)

Aquest directori connecta el sistema basat en regles (`clips_core/soar.clp`, generat des dels mòduls) amb un model
de la planta alimentat amb dades meteorològiques reals de 2023, i conté les eines de
verificació, validació i experimentació.

## Instal·lació (des d'un entorn net)

Calen **Python 3.11, 3.12 o 3.13**. Des de la carpeta `simulador`:

```
python -m venv venv
venv\Scripts\activate            (Windows)   ·   source venv/bin/activate   (Linux/Mac)
python -m pip install -r requirements.txt
python verificacio/e0_ontologia.py      # RDF carregable i topologia no duplicada
python verificacio/e1_regressio.py      # snapshots històriques: fail 0
```


## Ontologies com a entrada executable

`../ontologia_domini.rdf` i `../ontologia_model.rdf` formen part del runtime i són ontologies diferents. `ontologia_domini.rdf` és l'esquema autoritatiu (`OntologiaDomini`): defineix el vocabulari, les jerarquies i els `domain/range` i només conserva els cinc individus canònics d'objectiu necessaris per a algunes restriccions OWL. `ontologia_model.rdf` és l'ABox (`OntologiaModel`), importa explícitament el domini amb `owl:imports`, no redeclara l'esquema i aporta exclusivament les instàncies concretes de la planta. Només després d'aquesta validació RDFLib projecta els fets estàtics `sector`, `cultiu`, `panell` i `estat-sensor` a CLIPS. La capa Python no avalua candidats ni selecciona accions: aquesta responsabilitat continua dins de CLIPS.

`config.json` conserva els paràmetres físics del simulador per sector, però **no enumera els panells**. La llista de panells i la relació sector--cultiu provenen de `ontologia_model.rdf`; el vocabulari que pot utilitzar aquesta projecció queda governat per `ontologia_domini.rdf`.

Per inspeccionar o validar la projecció RDF → CLIPS:

```
python ontology_loader.py --fets
python verificacio/e0_ontologia.py
```

Els llindars agronòmics, objectius, prioritats i conflictes encara són coneixement operacional CLIPS perquè la versió actual del RDF no n'instancia els valors necessaris.

## Nucli CLIPS modular

La versió de treball ja no s'edita com un monòlit. Les regles estan separades per
responsabilitat cognitiva i `clips_core/soar.clp` es genera automàticament:

```
python clips_core/build_clips.py
python clips_core/build_clips.py --check-generated
```

`--check-baseline` es conserva només com a comparació històrica amb v1.8. Des de la integració RDF s'espera que indiqui `DIFERENT`, perquè el `deffacts` ja no duplica sectors, cultius, panells ni sensors.


Les proves de la versió canònica són a `clips_core/run_proves.clp` (79 proves), i E1 les executa com a `actual`. Abans, E1 projecta la topologia de l'ontologia a `clips_core/topologia_rdf.clp` (generat, no es versiona) i comprova que `soar.clp` està al dia amb els mòduls. `clips_core/run_soar.clp` és només un smoke test manual. Les versions i els `run_soar_v1_x.clp` històrics es conserven fora del nucli actiu, a `../history/clips/simulator/`, per a E1 i la reproducció històrica.

## Executar-ho tot

Amb 12 nuclis triga uns 15 minuts. Amb 2, més d'una hora (E2, E8, E9 i E15 són els més llargs):

```
python verificacio/e0_ontologia.py          # E0  domini -> validació model -> topologia CLIPS
python verificacio/e1_regressio.py          # E1  regressió: la versió canònica i totes les històriques
python verificacio/e2_graella.py            # E2  graella exhaustiva (--rapid: versió reduïda)
python verificacio/e3_llindars.py           # E3  75 casos als llindars (18 de reg)
python verificacio/casos_prova.py           # 14 casos de prova documentats -> CASOS_PROVA.md
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
python experiments.py E14                   # escenaris extrems: calor, vent i sequera (mesos seguits)
python experiments.py E15                   # reg: SOAR contra el reg fix, el reg FAO i sense reg
```

Opcions: `--processos N` (per defecte, tots els nuclis), `--traca` (desa la traça del CLIPS) i
`--clp ../history/clips/simulator/soar_v1_x.clp` (a E2 i E3, per provar una versió històrica). Per a les simulacions, la
versió del CLIPS es tria a `config.json` (`"clp"`).

Cada experiment desa els resultats a la seva carpeta: `resultats/E1/`, `resultats/E2/`… i les
simulacions soltes a `resultats/simulacions/`.

**Traça del CLIPS** (percepció, elaboració, proposta, avaluació, selecció, impasses i explicació):
- `simulador.py` la desa sempre a `resultats/simulacions/traca/`, un fitxer per dia (`--sense-traca` per no desar-la);
- `experiments.py` la desa només si s'hi afegeix `--traca`, a `resultats/<E>/traca/`
  (per exemple `python experiments.py E7 --dies 48 --traca`). Ocupa uns 80 kB per dia;
- E1 desa la sortida completa de cada `run_soar_v1_x.clp` a `resultats/E1/traca_run_soar_v1_x.txt`.

## Fitxers

| Fitxer | Què fa |
|---|---|
| `clips_core/soar.clp` | **Versió canònica (v1_9)**: la v1_6 amb la correcció de `nivell-hidric` i la decisió de **reg**, amb la topologia carregada de l'ontologia. És el punt d'entrada del simulador i es genera a partir dels mòduls de `clips_core/modules.txt`. |
| `clips_core/core/`, `memory/`, `reasoning/`, `deliberation/`, `action/` | Font CLIPS modular, separada per responsabilitats cognitives. Els blocs del reg porten l'etiqueta `v1_9`. |
| `clips_core/run_proves.clp` | Proves de la versió canònica (79: les 55 de la v1_6 i 24 de reg). Les executa E1. |
| `../history/clips/simulator/` | Versions monolítiques congelades: v1_5–v1_8 (per a E1, E9 i E10) i la v1_9 autònoma (amb la topologia al `deffacts`) amb el seu `run_soar_v1_9.clp`. |
| `clips_core/build_clips.py` | Regenera `soar.clp`, comprova que correspon als mòduls i permet comparar amb v1.8 com a referència històrica. |
| `ontology_loader.py` | Llegeix `../ontologia_domini.rdf` (TBox) i `../ontologia_model.rdf` (ABox), valida vocabulari + `domain/range` i projecta la instanciació a fets CLIPS. |
| `clips_bridge.py` | Pont Python ↔ CLIPS. Injecta la projecció ontològica al `reset` i gestiona el contracte de memòria de treball. |
| `dades.py` | Llegeix i fusiona Open-Meteo, XMS-Cat i PVGIS (vegeu `dades_reals/FONTS.md`). |
| `fisica.py` | Model físic simplificat: sol, producció, llum i temperatura del cultiu, aigua al sòl. |
| `simulador.py` | Bucle horari, sensors, previsió amb soroll, actuadors i fallades, controladors de referència, invariants. |
| `metriques.py` | Mètriques per dia (energia, hores d'estrès, seguretat, moviments, impasses, chunks…). |
| `estadistica.py` | Wilcoxon, Friedman + Holm, mida de l'efecte, IC bootstrap, cota de taxes rares, mida de mostra. |
| `experiments.py` | Experiments E4–E15. |
| `paralel.py` | Execució en paral·lel amb progrés, Ctrl+C i detecció de processos penjats. |
| `escenaris/` | Escenaris JSON per a `simulador.py` (dia normal i cas no vist). |
| `dades_reals/` | Dades de 2023 (Open-Meteo, XMS-Cat, PVGIS) i `FONTS.md`. |
| `CASOS_PROVA.md` | Els casos de prova documentats (es regenera amb `verificacio/casos_prova.py`). |
| `EXPERIMENTS.md` | Catàleg: pregunta, perspectiva de V&V, disseny, test i ordre de cada experiment. |
| `REGISTRE_ITERACIONS.md` | Registre d'iteracions (observació → experiment → canvi → regressió). |
| `verificacio/` | E0 (TBox→ABox→CLIPS), E1 (regressió històrica), E2 (graella exhaustiva), E3 (llindars) i casos de prova documentats. |
| `config.json` | Paràmetres físics i de simulació. La topologia no s'hi duplica: les llistes de panells es deriven del RDF. |

## Contracte amb el CLIPS (el que NO es pot canviar sense avisar)

El simulador només escriu i llegeix aquests fets. Si es canvia un nom de plantilla o de
slot, cal tocar `clips_bridge.py`.

| Direcció | Fets |
|---|---|
| RDF/Python → CLIPS al `reset` | `ontologia_domini.rdf` valida el contracte; `sector`, `cultiu`, `panell`, `estat-sensor` es generen des de `ontologia_model.rdf` |
| Python → CLIPS a cada cicle | `observacio`, `prediccio`, `energia`; actualitza `estat-sensor`, `panell` i `fase` |
| Python → CLIPS a cada cicle (v1_9) | `moment` (`cicle`, `hora` local) |
| CLIPS → Python | `ordre-actuador`, `operador-seleccionat`, `explicacio`, `risc`, `preferencia` (per saber si ha decidit un chunk o el reforç), `operador`, `subobjectiu` (impasses), `fragment-apres`, `rl-valor`, `epmem-episodi`. A partir de la v1_9, també `ordre-reg` (`accio`, `dosi` en % de l'aigua disponible), `explicacio-reg` i `preferencia-reg` (rebuigs) |
| Control | `cicle` (el CLIPS l'incrementa a `tanca-cicle`), `fase` final ha de ser `espera` |
| Interruptors | `REFORC::activa-reforc`, `REFORC::activa-parelles`, `APRENENTATGE::activa-chunking`, `MEMORIA::epmem-aprenentatge` |

El `deffacts coneixement-inicial` ja no conté la topologia ni entrades sintètiques. Conserva el control inicial, els llindars agronòmics i els objectius/relacions de control que encara no estan instanciats al RDF. Les observacions, prediccions i energia les posa sempre el simulador.

El pont també **esborra els fets de cicles vells** (més de 3 cicles enrere): el CLIPS mai no mira
més enllà de `c-2`, i així la memòria de treball no creix. La memòria a llarg termini
(`epmem-episodi`, `rl-valor`, `fragment-apres`) no es toca.

## Com funciona una hora (un cicle)

1. El controlador **veu** el que els sensors han mesurat l'hora anterior i una **previsió** per a
   l'hora que ve (valor real + soroll: ×lognormal σ=0,15 per al vent i la radiació, ±1 °C). La
   previsió de **pluja** és la de les pròximes 12 h (×lognormal σ=0,3).
2. Decideix un operador i un angle per sector, i (v1_9) si rega i quanta aigua posa.
3. Els actuadors mouen els panells, o no (fallada aleatòria o programada), i s'aplica el reg.
4. El simulador calcula què **passa de debò** durant l'hora amb l'angle real.

**Qui rega** (`config.json`, `humitat.reg.mode`):
- `auto`, per defecte: rega SOAR si la versió del CLIPS dona ordres de reg (v1_9). Si no (el seguidor comercial, el panell fix i les versions v1_5–v1_8), rega la finca.
- `soar`: les ordres del CLIPS.
- `finca`: a les 7 h, si l'aigua és per sota del 45 %, s'omple fins al 90 %.
- `fao`: el reg de llibre de FAO-56. A les 7 h, si s'ha esgotat la RAW, s'omple fins a capacitat de camp.
- `cap`: sense aigua de reg.

La ratxa que fa mal al seguidor és `wind_gusts_10m` d'Open-Meteo. Es simulen les hores 7–20
(14 cicles per dia); de nit només avança el balanç hídric.

## Model físic (simplificacions que cal dir a l'informe)

| Què | Com | Paràmetre |
|---|---|---|
| Angle òptim | seguidor N-S d'un eix, posició solar NOAA, límit ±55° | — |
| Producció | `kWp · ratio · GHI/1000 · f(angle)`, amb `f = 0,25 + 0,75·cos(angle − òptim)` | `ratio` calibrat amb PVGIS: 1,04 (Ribera de Sió), 1,15 (Cantallops) |
| Llum al cultiu | `GHI · (1 − GCR·|cos(angle)|)`: panell pla = més ombra (supòsit del CLIPS, `angle-ombra = 0`) | GCR = 0,4 |
| Temperatura del cultiu | aire + 0,006·llum + 2·(1 − aigua) | — |
| Aigua al sòl | balanç horari FAO-56: `ETc = ET0·Kc·Ks·(0,3 + 0,7·llum relativa)`, amb Ks (eq. 84) per sota de la RAW; pluja i reg; el que passa de capacitat de camp es perd per percolació | Kc i Zr per cultiu; CC/PM de la fitxa XMS-Cat; p del CLIPS |
| Reg | dosi neta = la que arriba al sòl; aigua bruta = neta / 0,85 (degoteig); bomba 0,48 kWh/m³; sector de 250 m² | fonts a `dades_reals/FONTS.md` |
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
| Complex | Invariants a cada cicle (`invariants_ko`, també del reg: I10–I12); escenaris extrems; escalabilitat de la memòria | totes les simulacions, E14 |
| Adaptatiu | Aprendre en uns dies i mesurar-ho en uns altres (validesa externa); capacitat de la funció Q; consistència del que s'aprèn (Rashid) | E8, E9, E10, E13 |
| Comparació amb una referència (Batarseh) | Seguidor comercial i panell fix amb els mateixos dies; el reg de SOAR contra un reg fix i el reg de llibre de FAO-56 | E4, E5, E7, E14, E15 |
| Sensibilitat (Batarseh) | Un paràmetre del model cada cop | E12 |

## Resultats (24/10/2026, v1_9)

Detalls a `resultats/<E>/`. El catàleg complet (pregunta, perspectiva, disseny i test de cada
experiment) és a `EXPERIMENTS.md`, i les iteracions a `REGISTRE_ITERACIONS.md`. Tot s'ha tornat a
executar amb la v1_9 (la v1_6, la correcció de `nivell-hidric` i el reg) i amb el balanç d'aigua
amb Ks (iteracions 20–22). E9 i E10 continuen comparant les versions antigues a propòsit.

### Verificació

| | Resultat |
|---|---|
| **E1** regressió | **canònica (v1_9) 79/79** (les 55 de la v1_6 i 24 de reg) · v1_5 46/46 · v1_6 55/55 · v1_7 59/59 · v1_8 59/59 · snapshot v1_9 79/79 |
| **E2** graella (24.500 casos × 3 sectors) | 0 violacions de seguretat, deficiència o conflicte · 0 casos no monòtons amb el vent · cobertura 55/79 regles (69,6 %). **Graella del reg** (1.680 casos × 3): 0 violacions de R1–R7 i 0 casos no monòtons de la dosi. Totes les regles del reg es disparen |
| **E3** llindars (75 casos) | 57/57 de la v1_8 + 18/18 de reg → **75/75** |
| **E11** agenda (20 dies) | Estratègies `depth`, `breadth`, `lex` i `mea`, especificitat (`simplicity` i `complexity`) i `random` amb 5 llavors: **0 decisions diferents** de 840 (ni del panell ni del reg). **Salience:** si les transicions de fase passen de −10 a 0, amb `depth` el panell canvia el **22,7 %** de les decisions i el reg **no arriba mai a decidir** (0 ordres de reg en 840 cicles: la fase passa abans que es pugui seleccionar). Amb `breadth` no es tanca **cap** cicle. La salience −10 de les transicions és imprescindible |
| **E13** coneixement après (5 execucions × 20 dies) | 0 problemes a les 9 restriccions (K1–K8), en 100 fotos. En acabar: 2–4 chunks, 73–75 rajoles Q (\|Q\| ≤ 0,68) i 840 episodis (exactament 1 per sector i cicle) |
| **Invariants** | 0 violacions en totes les simulacions, també les del reg (I10–I12) |

Les regles que E2 no dispara mai són de tres menes:
- **Aprenentatge o memòria**, que a la graella està apagat.
- **Les que necessiten més d'un cicle:** `percep-fallada-actuador`, `avalua-estabilitat`, `detecta-oscillacio`…
- **Potser inabastables (cal revisar-les):**
  - `percep-dades-vent-critic`, gairebé sempre tapada per `percep-lectura-absent`, que ja posa crític quan falta el vent;
  - `percep-sensor-no-valid`, que només es dispara amb un sensor incoherent i una lectura que sí que arriba;
  - `detecta-impas-sense-candidat` i `resol-sense-candidat`, perquè amb vent crític sempre queda `posicio-seguretat`;
  - `avalua-rebuig-fora-de-limits`, perquè l'angle òptim sempre és dins dels límits.

### Casos de prova documentats (14 + 1 cas no vist)

`python verificacio/casos_prova.py` → `resultats/casos_prova/CASOS_PROVA.md`, amb les entrades,
el resultat esperat (escrit abans), l'obtingut, l'explicació del sistema i la traça rellevant de
cada cas.

- **13 de 14 correctes.** Els tres de reg (CP12–CP14) passen.
- **CP01 té una discrepància analitzada:** al segon cicle el sistema repeteix `orientar-produccio`
  en lloc de `mantenir-posicio`. Ho fa per l'estabilitat i per la memòria episòdica. L'angle és el
  mateix i el panell no es mou, així que el comportament és correcte, però l'expectativa estava
  massa especificada.
- **Cas no vist (tramuntana del 27/03/2023 a Cantallops):** SOAR, 0 violacions i 2 h d'exposició.
  Seguidor comercial, 5 violacions i 11 h d'exposició.

### Validació

**E4 – vent real a Cantallops** (95 dies, 567 hores-sector amb ratxa ≥ 16 m/s):

| | Hores en posició de treball amb ratxa ≥ 16 m/s | Cota superior 95 % | Energia |
|---|---|---|---|
| Seguidor comercial | 58 (10,2 %) | 12,6 % | 277 kWh/dia |
| SOAR | **0** | **0,53 %** | 263 kWh/dia (−5 %) |

**E5 – el sensor de vent falla** (40 dies de vent × 3 llavors):

| Lectures que no arriben | 0 % | 5 % | 20 % |
|---|---|---|---|
| Violacions/dia, seguidor comercial | 1,28 | 1,24 | 1,04 |
| Violacions/dia, SOAR | 0 | 0 | 0 |
| Impasses de dades/dia, SOAR | 0,07 | 1,33 | 2,52 |

Amb el sensor caigut, SOAR fa servir la previsió i l'historial, i perd 1,1 kWh al dia amb un 20 % de lectures perdudes.

**E6 – fallades d'actuador** (5 % per panell i cicle, 40 dies × 3 llavors):
- 0 violacions i 0 invariants trencats.
- Només perd 1,3 kWh al dia.
- Canvia més d'operador: 9,4 canvis/dia contra 7,9 (p = 7e-14).

**E7 – Ribera de Sió, 48 dies** (Friedman i Wilcoxon amb Holm):

| | Panell fix | Seguidor comercial | SOAR |
|---|---|---|---|
| Energia (kWh/dia) | 341 | 397 | 368 (−7,3 % respecte del seguidor) |
| Estrès per radiació (h/dia) | 12,6 | 15,0 | 13,7 |
| Estrès per calor (h/dia) | 22,9 | 23,4 | 23,3 |
| Exposició a vent ≥ 12 m/s (h/dia) | 0 | 1,83 | 0,10 |
| Canvis d'operador/dia | 0 | 0,2 | 7,9 |
| Oscil·lacions reals (angle A → B → A)/dia | 0 | 0 | 0,12 |
| Estrès hídric (h/dia) | 0 | 0 | 0 |

El panell fix i el seguidor fan servir el reg de la finca, i SOAR el seu (0,3 regs/dia, 1,2 m³/dia).
En aquests dies cap dels tres arriba a tenir estrès hídric, i per això l'efecte del reg es mesura a part (E15).

**E8 – chunking** (10 execucions; s'aprèn en 20 dies i es mesura en 10 de no vistos):
- **Amb chunking:** 0,01 impasses/dia, i els chunks prenen 33 decisions al dia.
- **Sense chunking:** 0,47 impasses/dia (p = 4e-9).
- **Les decisions finals són idèntiques** (energia, estrès…). Els chunks reprodueixen exactament el que hauria decidit el subobjectiu, que és el que ha de fer el chunking a Soar.
- **No acceleren:** cada cicle triga 2,1 ms més. Les regles noves tenen un cost de *matching* (el "problema de la utilitat").

**E9 – reforç** (10 execucions; v1_5, v1_6 i v1_7, amb el reg de la finca):
- **El reforç decideix 0,6–0,7 de les 42 decisions diàries.**
- **Energia i estrès són pràcticament iguals** entre v1_5, v1_6 i v1_7 (diferències de menys d'1 kWh/dia).
- **El temps per cicle és de 37–39 ms** de mitjana als dies de prova, per la memòria episòdica (iteració 11).

**E10 – capacitat de la funció Q** (30 llavors, 400 mostres; encert de la política a 4 estats):

| | Tasca AND | Tasca XOR |
|---|---|---|
| v1_6 (trets sols) | 100 % | 50 % (com a l'atzar) |
| v1_8 sense parelles | 100 % | 50 % |
| v1_8 amb parelles | 100 % | **100 %** (p = 1e-6) |

Les parelles sí que aprenen interaccions que els trets sols no poden representar. Si a E9 no milloren
res, és perquè **el reforç gairebé no arriba a decidir**, no perquè la representació falli. Per això
l'equip es queda amb la v1_6, que és més simple (iteració 22).

**E14 – escenaris extrems:**

| Escenari | Mètrica | Panell fix | Seguidor comercial | SOAR |
|---|---|---|---|---|
| **Calor** (els 20 dies més calorosos de Ribera, +3 °C; × 3 llavors) | Calor crítica (h/dia) | 30,9 | 31,3 | 31,0 |
| | Estrès per radiació (h/dia) | 14,1 | 16,3 | 14,3 |
| | Energia (kWh/dia) | 370 | 432 | 382 |
| **Vent** (els 20 dies amb més vent de Cantallops, ratxes +30 %; × 3 llavors) | Violacions/dia | 0 | 1,13 | **0** |
| | Exposició a vent ≥ 12 m/s (h/dia) | 0 | 3,5 | 0,08 |
| **Sequera** (juny–setembre, mesos sencers de dies seguits, **sense aigua de reg per a ningú**; × 3 llavors) | Estrès hídric (h/mes, 3 sectors) | 617 | 660 | 629 |
| | Aigua al sòl a final de mes (%) | 58,8 | 56,3 | 58,2 |
| | Energia (kWh/mes) | 10.388 | 12.118 | 10.817 |

- **Amb vent extrem**, SOAR continua sense cap violació, i en conserva el 98 % de l'energia.
- **Amb calor extrema**, SOAR treu 2 h d'estrès per radiació, però la calor crítica gairebé no baixa (−0,3 h). És el mateix límit del domini que a E7 i E12.
- **Amb sequera i sense reg**, l'ombra només treu un 5 % de les hores d'estrès respecte del seguidor (p = 0,002), i a canvi es perd un 11 % d'energia. El panell fix ho fa una mica millor. **Amb només els panells no es pot protegir el cultiu de la falta d'aigua**: per això la v1_9 hi afegeix el reg (E15).
- **El risc "meteorològic advers" no surt mai:** la plantilla `risc` el preveu i l'ontologia també, però cap regla el genera. La pluja prevista sí que la fa servir el reg (v1_9).

**E12 – sensibilitat** (un paràmetre cada cop, 30 dies, SOAR − seguidor comercial):
- Totes les diferències mantenen el signe en tot el rang. Les conclusions d'E4 i d'E7 no depenen
  d'aquestes constants.
- La diferència d'estrès per calor no és significativa amb cap valor (p ≥ 0,10), ni doblant
  `k_rad`. La causa és el domini: al migdia, l'angle de màxima producció ja és gairebé pla, que és
  el que fa més ombra.
- La seguretat aguanta una previsió molt sorollosa (σ = 0,8) o sense previsió la meitat de les hores:
  0 violacions/dia per a SOAR, contra 1,4–1,6 del seguidor.

**E15 – reg** (els mateixos panells de la v1_9 amb 4 maneres de regar; d'abril a setembre a Ribera
de Sió, cada mes amb els dies seguits × 4 llavors = 24 blocs; Friedman i Wilcoxon amb Holm):

| Per mes (3 sectors) | Sense reg | Reg de la finca | Reg FAO-56 de llibre | **SOAR (v1_9)** |
|---|---|---|---|---|
| Aigua de reg (m³) | 0 | 46 | 68 | **67** |
| Hores d'estrès hídric | 679 | 385 | 44 | **0,6** |
| Aigua perduda per percolació (mm) | 6 | 10 | 28 | 25 |
| Regs | 0 | 4 | 7 | 11 |
| Energia de la bomba (kWh) | 0 | 22 | 33 | 32 |

- **Hipòtesi:** "SOAR gasta menys aigua que el reg de llibre amb el mateix estrès o menys". **Es compleix només a mitges.** SOAR gasta **la mateixa aigua** que el reg FAO (67 contra 68 m³/mes, p = 0,6), però deixa el cultiu **pràcticament sense estrès**: 0,6 h/mes contra 44 (p = 1e-4). Fa més regs, però més petits i abans que el cultiu pateixi. La majoria són a les 19 h, l'hora fresca de la tarda.
- **Per cultiu:**
  - **Vinya:** SOAR hi gasta la meitat d'aigua que el reg FAO (6,0 contra 12,2 m³/mes) amb menys estrès (0,5 contra 2,5 h). És el reg deficitari: la vinya no s'anticipa i es rega en part.
  - **Enciam i tomàquet:** SOAR hi gasta una mica més que el reg FAO (29,7 contra 27,1 i 31,7 contra 29,0 m³/mes), però amb 0 hores d'estrès contra 31 i 10.
- **El reg de la finca** gasta menys aigua, però el cultiu pateix 385 h/mes: el llindar del 45 % és massa baix per a l'enciam (p = 0,30) i el tomàquet.
- **L'energia de la bomba** és petita al costat de la producció (32 kWh de 11.000 al mes, un 0,3 %), i per això la preferència d'energia gairebé mai no canvia la decisió de regar.

## Pendent

- **Millores del reg (v1_9) que vam parlar:**
  - comprovar al cicle següent que el reg ha funcionat (fallada de la vàlvula);
  - fer servir l'última lectura si falta el sensor d'humitat (impasse de dades);
  - afegir a E12 els paràmetres de disseny del reg (75 % d'anticipació, dosi parcial, soroll de la previsió de pluja).

- **E12, part de pesos i `alfa`:** són dins del CLIPS i no es poden variar des del simulador sense tocar el `.clp`.
- **Tornar-ho a executar tot** amb la versió final del CLIPS: les ordres són a `EXPERIMENTS.md`.
