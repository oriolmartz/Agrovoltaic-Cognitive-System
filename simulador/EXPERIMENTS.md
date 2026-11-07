# Catàleg d'experiments

Cada experiment respon una pregunta concreta i està situat dins del marc de V&V. L'eix és
Menzies & Pecheur (2005), amb Batarseh & Gonzalez (2015), Rashid et al. (2019) i Tsai, Vishnuvajjala & Zhang (1999) com a complement.
Els resultats de cada experiment queden a `resultats/<E>/`.

**Verificació** = el sistema està ben construït. Es mira per dins, i el resultat és passa o no passa.
**Validació** = el sistema fa el que ha de fer. Es mira el que fa a la planta, amb estadística.

## Què queda fora i per què

- **Model checking** (Menzies & Pecheur 2005): no hi ha un model formal del CLIPS que un verificador de models pugui explorar, i traduir-lo a mà seria un altre sistema que caldria verificar. N'ocupen el lloc, de manera limitada, la graella exhaustiva d'E2 (totes les combinacions discretitzades d'entrades, un cicle) i la verificació en temps d'execució (invariants i E18). No cobreix seqüències llargues de cicles.
- **Validació amb un expert** (Batarseh & Gonzalez): no hem tingut cap agrònom ni enginyer que revisés decisions. Se substitueix per sistemes de referència (seguidor comercial, panell fix, reg FAO-56 i de finca) i per fonts publicades per als llindars (`dades_reals/FONTS.md`). És una limitació: els resultats diuen que el sistema millora respecte d'aquestes referències, no que un expert hi estaria d'acord.

## Disseny estadístic comú

- **Unitat de repetició: un dia.** Cada dia comença amb una planta nova i un controlador nou, de
  manera que els dies són independents. A E8, E9 i E13, que són d'aprenentatge, la unitat és una
  execució de molts dies seguits.
- **Disseny aparellat.** Totes les configuracions veuen els mateixos dies i el mateix soroll: el
  soroll de cada dia surt de la llavor i de la data. Es comparen diferències dins de cada dia.
- **Experiments d'aigua (E14 sequera i E15): la unitat és un mes sencer de dies seguits.** L'aigua
  del sòl passa d'un dia a l'altre, així que els dies d'un mateix mes no són independents. Es
  comparen mesos (bloc = mes i llavor).
- **Tests:**

  | Cas | Test |
  |---|---|
  | 2 configuracions | Wilcoxon de rangs amb signe |
  | Més de 2 | Friedman i, després, Wilcoxon per parelles amb correcció de Holm (el procediment que recomana Demšar 2006 per comparar diversos sistemes sobre els mateixos casos) |
  | Esdeveniments que no passen mai (violacions de seguretat) | Cota superior de Clopper-Pearson; amb 0 casos, la "regla de tres" (≈ 3/n) |

  A totes les comparacions es dona també la mida de l'efecte (correlació biserial de rangs, que
  compta els empats) i un interval de confiança del 95 % de la diferència, per bootstrap.
- **Mida de la mostra** (`python estadistica.py`): per detectar un efecte mitjà (d = 0,5) amb una
  potència de 0,8 calen 36 dies, i 48 si hi ha 3 comparacions amb Holm. Per això E7 en fa servir 48.
- **Reproduïbilitat:** el mateix experiment ha de donar exactament els mateixos números en un altre
  ordinador i un altre sistema operatiu. Es va comprovar entre Linux i Windows amb la v1_8 (E1–E7 i
  E10–E13: dades per dia idèntiques). Amb la v1_9 encara no s'ha tornat a comprovar a Windows.

## Verificació

| | Pregunta | Perspectiva | Com | Ordre |
|---|---|---|---|---|
| **E0** | El model RDF és coherent amb l’ontologia de domini i es pot convertir sense duplicació en la topologia que consumeix CLIPS? | Verificació de representació i consistència d’artefactes | Comprova que domini i model tenen IRI diferents, que el model importa el domini amb `owl:imports` i no redeclara l'esquema; valida vocabulari + `domain/range`, genera els fets CLIPS i comprova que ni `domini.clp` ni `config.json` reintrodueixen la topologia manualment | `python verificacio/e0_ontologia.py` |
| **E1** | Un canvi trenca res que abans funcionava? | Regressió; validació incremental (Batarseh) | Executa el `run_soar_v1_x.clp` de cada versió i compta quantes proves passen | `python verificacio/e1_regressio.py` |
| **E2** | Hi ha anomalies a la base de regles? | Anomalies de Preece (Menzies §2): deficiència, conflicte, regles mai disparades. A més, proves metamòrfiques de monotonia | 24.500 combinacions d'entrades × 3 cultius, un cicle cadascuna: seguretat, monotonia amb el vent i cobertura de regles. A la v1_9, una segona graella per al **reg** (1.680 combinacions d'humitat, pluja prevista, hora i dèficit d'energia) amb 7 propietats (R1–R7) i la monotonia de la dosi | `python verificacio/e2_graella.py` (`--rapid`: 1.890 casos + la graella del reg) |
| **E3** | Les conclusions són correctes als llindars? | Casos positius i negatius amb el resultat esperat escrit abans (VVR de Zlatareva, a Batarseh). Anàlisi de valors límit | 57 casos: just a sota, al llindar i just a sobre de cada llindar de les fonts (vent, temperatura, aigua, radiació). A la v1_9, 18 més de **reg** (G01–G18): anticipació al 75 % de p, hores fresques, la vinya, 2 i 10 mm de pluja prevista, estrès crític, sensor absent | `python verificacio/e3_llindars.py` |
| **E11** | La decisió depèn de l'ordre en què es disparen les regles? Per a què serveix la salience? | Agenda de CLIPS (enunciat, apartat 3.7.2) i no determinisme (Menzies §5) | Els mateixos 20 dies amb: (1) les estratègies `depth`, `breadth`, `lex` i `mea`; (2) `simplicity` i `complexity`, que ordenen per **especificitat**; (3) `random` amb 5 llavors; (4) dues variants del `.clp` amb la **salience** canviada: les transicions de fase a 0 en lloc de −10, o cap salience. Es compara cada decisió amb la de `depth` | `python experiments.py E11` |
| **E13** | El coneixement que s'aprèn és consistent i complet? | Bases de coneixement que evolucionen (Rashid): restriccions d'integritat i completesa entre versions | 5 execucions de 20 dies seguits. Al final de cada dia es fa una foto dels chunks, els valors Q i els episodis, i es comproven 9 restriccions (K1–K8) | `python experiments.py E13` |
| **E17** | Les proves detecten els errors que es poden cometre al CLIPS? | Adequació de les proves: *mutation testing* (Tsai et al. 1999) | 99 mutants del `soar.clp`: 20 substitucions (llindars, pesos, operadors relacionals, salience de les transicions) i 79 eliminacions d'una regla. Cada mutant passa per la regressió (`run_proves.clp`), E3 i els casos de prova; un mutant és **mort** si alguna prova canvia respecte de l'original. Resultat: percentatge de mutants morts i quins sobreviuen | `python verificacio/e17_mutacions.py` |
| **E18** | El cicle SOAR passa per les fases en l'ordre correcte i fa una sola acció per sector? | Verificació del motor (Tsai: "tot el sistema, no només la base de coneixement"); verificació en temps d'execució | Amb `watch rules`, a cada cicle de 10 dies de Ribera i 10 dies de vent de Cantallops (sensor de vent que falla un 10 %, perquè hi hagi impasses) es reconstrueix el recorregut de fases a partir de les regles de transició llegides del `.clp`. C1: l'ordre és percepció → elaboració → proposta → avaluació → selecció → (impasse → selecció)* → aplicació → explicació → monitoratge → espera; C2: cap regla es dispara fora de la seva fase; C3: un sol operador, una ordre de panell i una de reg per sector. Control negatiu: les transicions a salience 0 (el comprovador ho ha de detectar) | `python verificacio/e18_cicle_soar.py` |
| **E19** | Els números de la valoració (pesos, nivells, estabilitat, requerida) estan justificats? Fan el que han de fer? | Sensibilitat (Batarseh) i comprovació que els pesos implementen l'ordre de prioritats (verificació del coneixement de control) | **A. Analítica:** per a cada parella d'operadors d'objectius diferents, el marge mínim de puntuació en totes les situacions (vent, 3 riscos del cultiu, cobertura, panell a l'òptim, operador anterior), amb la memòria i sense; i la cota que ha de superar la preferència requerida. **B. Graella** d'E2 (ràpida) amb cada variant del `.clp`. **C. Dies reals:** 20 de Ribera i 20 de vent de Cantallops, 25 variants (cada pes ×½ i ×2, tots iguals, 4 escales de nivells, requerida 0–100, pes de memòria 0 i 1). Concordança de decisions, energia, estrès, exposició al vent, violacions i impasses | `python verificacio/e19_pesos.py` |
| **Invariants** | Es compleixen sempre les propietats bàsiques? | Verificació en temps d'execució (Menzies §6.1.2) | A cada cicle de qualsevol simulació: una ordre per sector, angle dins dels límits, mai un operador rebutjat, seguretat amb vent, fase final correcta. Amb la v1_9, també: una ordre de reg per sector (I10), dosi no més gran del que falta (I11) i mai un reg rebutjat (I12) | columna `invariants_ko` de tots els resultats |

Les restriccions d'E13:

| | Comprova que… |
|---|---|
| K1 | cada fet `fragment-apres` té la seva regla |
| K2 | cada regla `chunk-N` té el seu fet |
| K3 | no hi ha dues signatures iguals |
| K4 | no hi ha dues regles amb la mateixa condició i una acció diferent |
| K5 | cada parella (tret, operador) té una sola rajola Q |
| K6 | cap Q passa de 2 en valor absolut |
| K7 | hi ha un episodi per sector i cicle |
| K8 | no es perden chunks ni rajoles d'un dia a l'altre |

Les propietats del reg a E2 (v1_9), per a cada sector:

| | Comprova que… |
|---|---|
| R1 | hi ha exactament una ordre de reg |
| R2 | la dosi no passa del que falta per arribar a capacitat de camp (FAO-56) |
| R3 | amb 10 mm o més de pluja prevista, i sense estrès crític, no es rega |
| R4 | sense lectura d'humitat, no es rega |
| R5 | sense necessitat (menys del 75 % de p), no es rega |
| R6 | amb estrès hídric i menys de 10 mm previstos, sempre es rega |
| R7 | la vinya no s'anticipa (sense estrès, no es rega) |
| Monotonia | amb menys aigua al sòl, i la resta igual, la dosi no baixa |

## Validació

| | Pregunta | Perspectiva | Com | Ordre |
|---|---|---|---|---|
| **E4** | És segur amb vent real? | Proves de camp per simulació; comparació amb un sistema de referència (Batarseh) | Tots els 95 dies de Cantallops (tramuntana). SOAR contra el seguidor comercial | `python experiments.py E4` |
| **E5** | I si falla el sensor de vent? | Robustesa (no determinisme) | El sensor no dona lectura un 0, 5 o 20 % de les vegades. 40 dies de vent × 3 llavors | `python experiments.py E5` |
| **E6** | Detecta i gestiona les fallades d'actuador? | Robustesa | Cada panell té un 5 % de probabilitat de no moure's. 40 dies × 3 llavors | `python experiments.py E6` |
| **E7** | Què guanya i què perd SOAR respecte d'un seguidor normal? | Comparació amb sistemes de referència, a falta d'un expert humà (Batarseh) | SOAR, el seguidor comercial i el panell fix, amb 48 dies reals de Ribera de Sió | `python experiments.py E7 --dies 48` |
| **E8** | El chunking fa la seva feina? | Sistemes adaptatius: validesa externa (Menzies §7.2.2) | Amb chunking i sense, sense reforç (versió per defecte, v1_9). S'aprèn durant 20 dies d'abril a juny i es mesura en 10 dies de juliol a setembre (no vistos) | `python experiments.py E8 --dies 10` |
| **E9** | El reforç millora el sistema? | Sistemes adaptatius: validesa externa | v1_5 (sense reforç), v1_6 (trets sols) i v1_7 (parelles), amb el mateix protocol que E8 | `python experiments.py E9 --dies 10` |
| **E10** | La funció Q pot aprendre interaccions entre trets? | Prova de capacitat de caixa blanca d'un component adaptatiu | Les funcions `REFORC` del CLIPS s'entrenen amb mostres sintètiques d'una tasca AND i d'una tasca XOR. 30 llavors, de 10 a 400 mostres | `python experiments.py E10` |
| **E14** | I en condicions extremes? | Proves d'estrès (escenaris adversos) amb dades reals modificades | Tres escenaris, SOAR contra el seguidor comercial i el panell fix. **Calor:** els 20 dies més calorosos de Ribera de Sió (36–42 °C) amb +3 °C, × 3 llavors. **Vent:** els 20 dies amb més vent de Cantallops, amb les ratxes un 30 % més fortes, × 3 llavors. **Sequera:** de juny a setembre, cada mes sencer amb els dies seguits i **sense aigua de reg per a ningú** (només hi ha l'ombra dels panells), × 3 llavors | `python experiments.py E14` |
| **E15** | El reg que decideix el sistema és millor que un reg fix? | Comparació amb sistemes de referència (Batarseh) i extensió avaluada amb hipòtesi i línia base (enunciat, apartat 3.9) | **Hipòtesi:** SOAR gasta menys aigua que un reg de llibre amb el mateix estrès o menys. Els mateixos panells (v1_9) amb 4 maneres de regar: **soar** (les ordres del CLIPS), **fao** (FAO-56 de llibre: cada dia a les 7 h, si s'ha esgotat la RAW, s'omple el sòl), **finca** (a les 7 h, si és per sota del 45 %, s'omple fins al 90 %) i **cap**. De l'abril al setembre a Ribera de Sió, cada mes amb els dies seguits, × 4 llavors (24 blocs) | `python experiments.py E15` |
| **E16** | La memòria episòdica serveix a llarg termini? | Sistemes adaptatius: validesa externa amb un any d'entrenament i un altre de prova (Menzies §7.2.2); consistència del que s'aprèn (Rashid) i escalabilitat | Ribera de Sió 2022–2023 (Open-Meteo i XMS-Cat), dies seguits. Tres configuracions: **memòria dels dos anys** (s'aprèn tot el 2022 i es continua el 2023), **sense memòria** i **memòria només el 2023** (comença de zero l'1 de gener). Es mesura tot el 2023; bloc = (mes, execució), 3 execucions. També es fa una foto del coneixement cada dia (K1–K6). Les execucions duren hores: es fan per trams amb punts de control (`--part k --minuts-tram N`) | `python experiments.py E16` |
| **E20** | La memòria semàntica (iteració 29) decideix millor que l'episòdica? Evita que la memòria creixi sense límit? | Sistemes adaptatius (validesa externa) i escalabilitat | Tot el 2023 de Ribera de Sió, dies seguits, 2 execucions: sense memòria, només episòdica, episòdica + semàntica, i semàntica amb finestra (els episodis ja resumits de fa més d'una setmana surten de la memòria de treball). Bloc = (mes, execució). Decisions de cada memòria, concordança amb l'episòdica, episodis a la memòria de treball, temps per cicle i restriccions K1–K6 | `python experiments.py E20` |
| **E21** | Amb un model físic validat (temperatura de la coberta per balanç d'energia, calendari de cultiu), SOAR protegeix el cultiu de la calor? | Validesa del model de simulació (Batarseh: el banc de proves ha de ser realista) i comparació amb referències | 48 dies del 2023 a Ribera (4 per mes). SOAR, seguidor comercial i panell fix, amb el model físic de la v1_9 i amb el nou. Mateixos dies i llavors (aparellat). SOAR − seguidor dins de cada model (Wilcoxon). La validació del model amb mesures reals és a `verificacio/v_temperatura_coberta.py` | `python experiments.py E21` |
| **E22** | El sistema aguanta lectures absents, impossibles o de sensors avariats? Detecta que el reg no ha arribat al sòl? | Robustesa (Menzies §5) i monitoratge de l'efecte de les accions (enunciat, pas 8 del cicle) | A: 30 dies de Ribera × 2 llavors amb errors de sensors, amb l'historial (última lectura vàlida) i sense; B: juny-agost 2023 seguits amb la vàlvula que falla el 30 % de les vegades. Sensibilitat i falses alarmes de la detecció | `python experiments.py E22` |
| **E23** | Quina estratègia d'oblit manté la memòria episòdica acotada sense empitjorar les decisions? Redueix el cost de cerca? | Sistemes adaptatius i escalabilitat; línia base sense oblit i braços de comparació com Nuxoll et al. (2010); activació de nivell base i retenció que preserva la competència (Derbinsky & Laird 2013) | 120 dies seguits del 2023 a Ribera, 3 llavors. A sense oblit; B finestra; C aleatori; D antiguitat (FIFO); E activació d'episodi; F activació de grup amb període de gràcia i mínim d'episodis; G com F sense proteccions. Tres capacitats (25, 50 i 75 % dels episodis de A). Fidelitat de decisions respecte d'A, episodis examinats per les consultes, temps per cicle i taxa d'encert. Detall a `estrategia_oblit.md` i `resultats/E23/` | `python experiments.py E23 --dies 120 --llavors 3` |
| **E24** | L'índex de la memòria episòdica redueix el cost de recuperació? Com depèn de la quantitat i la distribució dels episodis? | Escalabilitat; Soar també indexa per reduir aquest cost (Laird 2022; Derbinsky, Li & Laird 2012) | Episodis amb els trets d'una simulació real (60 dies del 2023 a Ribera). 1.000, 5.000, 15.000 i 30.000 episodis × 3 repartiments entre operadors (real, uniforme, 90 % en un de sol) × 3 llavors; 100 consultes iguals amb índex i amb cerca exhaustiva. Ms per consulta, pendent i si es recupera el mateix episodi | `python experiments.py E24` |
| **E12** | Les conclusions depenen dels números que vam triar a dit? | Anàlisi de sensibilitat (Batarseh) | Un paràmetre cada cop: GCR, `k_rad`, `k_sec`, el soroll i la disponibilitat de la previsió. Es mira si el signe de la diferència entre SOAR i el seguidor es manté | `python experiments.py E12` |
| **E12reg** | La conclusió d'E15 (SOAR deixa el cultiu sense estrès amb la mateixa aigua que el reg FAO) depèn dels paràmetres del reg que vam triar? | Anàlisi de sensibilitat (Batarseh) | Un paràmetre cada cop: anticipació (0,6/0,75/0,9 de p), pluja que anul·la el reg (5/10/15 mm), hores fresques del matí (7/8/9 h) i de la tarda (18/19/20 h) i soroll de la previsió de pluja. Protocol d'E15 (abril–setembre, mesos seguits × 2 llavors). SOAR − FAO per a cada valor i si el signe es manté | `python experiments.py E12reg` |

## Casos de prova documentats

L'enunciat demana "un mínim de vuit casos de prova, amb entrades, traça rellevant, sortida i
explicació". Són a `python verificacio/casos_prova.py`, que genera `resultats/casos_prova/CASOS_PROVA.md`
i la traça completa de cada cas:

| Cas | Què prova | Cobertura |
|---|---|---|
| CP01 | Operació normal (2 cicles) | normalitat |
| CP02 | Vent crític de 18 m/s | seguretat |
| CP03 | Vent de 6 m/s però previsió de 17 m/s | seguretat anticipada |
| CP04 | 15,9 contra 16,0 m/s | límits |
| CP05 | Enciam calent i poca producció: impasse d'empat → prioritat → chunk → reutilització | conflicte de domini |
| CP06 | Sensor de vent caigut sense indicis de perill → impasse de dades → chunk | dades absents |
| CP07 | Sensor de vent caigut després d'una ratxa crítica | dades absents + historial |
| CP08 | Actuador que no es mou | fallades |
| CP09 | Vent 6 → 13 → 18 → 18 → 8 m/s en 5 hores | canvis temporals |
| CP10 | Enciam amb un 20 % d'aigua | protecció del cultiu |
| CP11 | Tomàquet amb radiació i calor altes alhora | elaboració combinada |
| CP12 | Reg a primera hora: l'enciam amb estrès i el tomàquet a prop del llindar; la vinya no s'anticipa | reg |
| CP13 | No es rega perquè es preveuen 15 mm, llevat de l'enciam amb estrès crític | conflicte (reg) |
| CP14 | Vinya al llindar exacte (55,0 %) i just a sota (54,9 %): reg deficitari | límits (reg) |
| CP15 | Sensor d'humitat que deixa de respondre | dades absents + historial |
| CP16 | Lectura impossible i sensor avariat | dades incoherents + fallades |
| CP17 | Reg que no arriba al sòl | fallades (reg) + efecte observat |
| CP18 | Vent crític amb l'actuador avariat (restriccions incompatibles) | seguretat + fallades + impasse |
| CP19 | La memòria episòdica recorda una situació repetida | historial (memòria) |
| Cas no vist | Un dia real de tramuntana a Cantallops (27/03/2023) que no es va fer servir per desenvolupar les regles: `python simulador.py escenaris/cas_no_vist_tramuntana.json` (i `--controlador seguidor` per comparar) | casos no vistos |

## Opcions comunes

- `--processos N`: quants processos fer servir en paral·lel. Per defecte, tots els nuclis.
- `--traca`: desa la traça completa del CLIPS a `resultats/<E>/traca/`.
- `--dies N`: a E4, E5, E6, E7, E11, E12 i E14, nombre de dies. A E8, E9, E10 i E13, nombre d'execucions. A E15, nombre de dies de cada mes (per a una prova ràpida).

## Referències

- Batarseh, F. A. & Gonzalez, A. J. (2015). Validation of knowledge-based systems: a reassessment of the field. *Artificial Intelligence Review*, 43(4), 485–500.
- Demšar, J. (2006). Statistical comparisons of classifiers over multiple data sets. *Journal of Machine Learning Research*, 7, 1–30.
- Derbinsky, N. & Laird, J. E. (2013). Effective and efficient forgetting of learned knowledge in Soar's working and procedural memories. *Cognitive Systems Research*, 24, 104–113.
- Derbinsky, N., Li, J. & Laird, J. E. (2012). A multi-domain evaluation of scaling in a general episodic memory. *AAAI 2012*.
- Laird, J. E. (2022). Introduction to the Soar cognitive architecture. arXiv:2205.03854.
- Menzies, T. & Pecheur, C. (2005). Verification and validation and artificial intelligence. *Advances in Computers*, 65, 153–201.
- Nuxoll, A., Tecuci, D., Ho, W. C. & Wang, N. (2010). Comparing forgetting algorithms for artificial episodic memory systems. *AISB 2010*.
- Rashid, M., Torchiano, M., Rizzo, G., Mihindukulasooriya, N. & Corcho, O. (2019). A quality assessment approach for evolving knowledge bases. *Semantic Web*, 10(2), 349–383.
- Tsai, W.-T., Vishnuvajjala, R. & Zhang, D. (1999). Verification and validation of knowledge-based systems. *IEEE Transactions on Knowledge and Data Engineering*, 11(1), 202–212.
