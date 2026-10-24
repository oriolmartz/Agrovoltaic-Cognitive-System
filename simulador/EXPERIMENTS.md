# Catàleg d'experiments

Cada experiment respon una pregunta concreta i està situat dins del marc de V&V. L'eix és
Menzies & Pecheur (2005), amb Batarseh & Gonzalez (2015) i Rashid et al. (2019) com a complement.
Els resultats de cada experiment queden a `resultats/<E>/`.

**Verificació** = el sistema està ben construït. Es mira per dins, i el resultat és passa o no passa.
**Validació** = el sistema fa el que ha de fer. Es mira el que fa a la planta, amb estadística.

## Disseny estadístic comú

- **Unitat de repetició: un dia.** Cada dia comença amb una planta nova i un controlador nou, de
  manera que els dies són independents. A E8, E9 i E13, que són d'aprenentatge, la unitat és una
  execució de molts dies seguits.
- **Disseny aparellat.** Totes les configuracions veuen els mateixos dies i el mateix soroll: el
  soroll de cada dia surt de la llavor i de la data. Es comparen diferències dins de cada dia.
- **Tests:**

  | Cas | Test |
  |---|---|
  | 2 configuracions | Wilcoxon de rangs amb signe |
  | Més de 2 | Friedman i, després, Wilcoxon per parelles amb correcció de Holm |
  | Esdeveniments que no passen mai (violacions de seguretat) | Cota superior de Clopper-Pearson; amb 0 casos, la "regla de tres" (≈ 3/n) |

  A totes les comparacions es dona també la mida de l'efecte (correlació biserial de rangs, que
  compta els empats) i un interval de confiança del 95 % de la diferència, per bootstrap.
- **Mida de la mostra** (`python estadistica.py`): per detectar un efecte mitjà (d = 0,5) amb una
  potència de 0,8 calen 36 dies, i 48 si hi ha 3 comparacions amb Holm. Per això E7 en fa servir 48.
- **Reproduïbilitat:** el mateix experiment dona exactament els mateixos números en un altre
  ordinador i un altre sistema operatiu. Comprovat entre Linux i Windows per a E1–E7 i E10–E13: les dades per dia són idèntiques.

## Verificació

| | Pregunta | Perspectiva | Com | Ordre |
|---|---|---|---|---|
| **E1** | Un canvi trenca res que abans funcionava? | Regressió; validació incremental (Batarseh) | Executa el `run_soar_v1_x.clp` de cada versió i compta quantes proves passen | `python verificacio/e1_regressio.py` |
| **E2** | Hi ha anomalies a la base de regles? | Anomalies de Preece (Menzies §2): deficiència, conflicte, regles mai disparades. A més, una prova metamòrfica de monotonia | 24.500 combinacions d'entrades × 3 cultius, un cicle cadascuna. Es comproven propietats de seguretat, monotonia amb el vent i cobertura de regles | `python verificacio/e2_graella.py` (`--rapid`: 1.890 casos) |
| **E3** | Les conclusions són correctes als llindars? | Casos positius i negatius amb el resultat esperat escrit abans (VVR de Zlatareva, a Batarseh). Anàlisi de valors límit | 57 casos: just a sota, al llindar i just a sobre de cada llindar de les fonts (vent, temperatura, aigua, radiació) | `python verificacio/e3_llindars.py` |
| **E11** | La decisió depèn de l'ordre en què es disparen les regles? Per a què serveix la salience? | Agenda de CLIPS (enunciat, apartat 3.7.2) i no determinisme (Menzies §5) | Els mateixos 20 dies amb: (1) les estratègies `depth`, `breadth`, `lex` i `mea`; (2) `simplicity` i `complexity`, que ordenen per **especificitat**; (3) `random` amb 5 llavors; (4) dues variants del `.clp` amb la **salience** canviada: les transicions de fase a 0 en lloc de −10, o cap salience. Es compara cada decisió amb la de `depth` | `python experiments.py E11` |
| **E13** | El coneixement que s'aprèn és consistent i complet? | Bases de coneixement que evolucionen (Rashid): restriccions d'integritat i completesa entre versions | 5 execucions de 20 dies seguits. Al final de cada dia es fa una foto dels chunks, els valors Q i els episodis, i es comproven 8 restriccions (K1–K8) | `python experiments.py E13` |
| **Invariants** | Es compleixen sempre les propietats bàsiques? | Verificació en temps d'execució (Menzies §6.1.2) | A cada cicle de qualsevol simulació: una ordre per sector, angle dins dels límits, mai un operador rebutjat, seguretat amb vent, fase final correcta | columna `invariants_ko` de tots els resultats |

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

## Validació

| | Pregunta | Perspectiva | Com | Ordre |
|---|---|---|---|---|
| **E4** | És segur amb vent real? | Proves de camp per simulació; comparació amb un sistema de referència (Batarseh) | Tots els 95 dies de Cantallops (tramuntana). SOAR contra el seguidor comercial | `python experiments.py E4` |
| **E5** | I si falla el sensor de vent? | Robustesa (no determinisme) | El sensor no dona lectura un 0, 5 o 20 % de les vegades. 40 dies de vent × 3 llavors | `python experiments.py E5` |
| **E6** | Detecta i gestiona les fallades d'actuador? | Robustesa | Cada panell té un 5 % de probabilitat de no moure's. 40 dies × 3 llavors | `python experiments.py E6` |
| **E7** | Què guanya i què perd SOAR respecte d'un seguidor normal? | Comparació amb sistemes de referència, a falta d'un expert humà (Batarseh) | SOAR, el seguidor comercial i el panell fix, amb 48 dies reals de Ribera de Sió | `python experiments.py E7 --dies 48` |
| **E8** | El chunking fa la seva feina? | Sistemes adaptatius: validesa externa (Menzies §7.2.2) | Amb chunking i sense, sense reforç. S'aprèn durant 20 dies d'abril a juny i es mesura en 10 dies de juliol a setembre (no vistos) | `python experiments.py E8 --dies 10` |
| **E9** | El reforç millora el sistema? | Sistemes adaptatius: validesa externa | v1_5 (sense reforç), v1_6 (trets sols) i v1_7 (parelles), amb el mateix protocol que E8 | `python experiments.py E9 --dies 10` |
| **E10** | La funció Q pot aprendre interaccions entre trets? | Prova de capacitat de caixa blanca d'un component adaptatiu | Les funcions `REFORC` del CLIPS s'entrenen amb mostres sintètiques d'una tasca AND i d'una tasca XOR. 30 llavors, de 10 a 400 mostres | `python experiments.py E10` |
| **E14** | I en condicions extremes? | Proves d'estrès (escenaris adversos) amb dades reals modificades | Tres escenaris, SOAR contra el seguidor comercial i el panell fix, 20 dies × 3 llavors cadascun. **Calor:** els 20 dies més calorosos de Ribera de Sió (36–42 °C) amb +3 °C. **Sequera:** juliol i agost sense reg. **Vent:** els 20 dies amb més vent de Cantallops, amb les ratxes un 30 % més fortes | `python experiments.py E14` |
| **E12** | Les conclusions depenen dels números que vam triar a dit? | Anàlisi de sensibilitat (Batarseh) | Un paràmetre cada cop: GCR, `k_rad`, `k_sec`, el soroll i la disponibilitat de la previsió. Es mira si el signe de la diferència entre SOAR i el seguidor es manté | `python experiments.py E12` |

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
| Cas no vist | Un dia real de tramuntana a Cantallops (27/03/2023) que no es va fer servir per desenvolupar les regles: `python simulador.py escenaris/cas_no_vist_tramuntana.json` (i `--controlador seguidor` per comparar) | casos no vistos |

## Opcions comunes

- `--processos N`: quants processos fer servir en paral·lel. Per defecte, tots els nuclis.
- `--traca`: desa la traça del CLIPS (com `run_soar`) a `resultats/<E>/traca/`.
- `--dies N`: a E4, E5, E6, E7, E11, E12 i E14, nombre de dies. A E8, E9, E10 i E13, nombre d'execucions.
