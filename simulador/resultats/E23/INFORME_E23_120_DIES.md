# E23 — Resultats de 120 dies

## Resum

Aquest informe recull l'execució d'E23 durant 120 dies seqüencials, de l'1 de
gener al 30 d'abril de 2023, amb una llavor (`0`). Es comparen la línia base
sense oblit (A) i sis estratègies d'oblit (B–G), cadascuna amb tres límits de
capacitat.

**Resultat principal:** els braços amb oblit van reduir entre un **7,2 % i un
73,4 %** els episodis examinats per EpMem respecte d'A. La fidelitat de les
decisions respecte de la línia base va ser **100 %** en tots els braços. La
mediana de temps per cicle, però, no va millorar de manera consistent: en
algunes configuracions va ser considerablement més alta que la línia base.

## Configuració

- **Període:** 120 dies seqüencials, de l'1 de gener al 30 d'abril de 2023.
- **Llavors:** una (`0`).
- **Decisions comparades:** 5.040 per braç (14 hores diàries × 3 sectors ×
  120 dies).
- **Línia base A:** 5.040 episodis a EpMem al final; 111 resums semàntics.
- **Capacitats:** 25 %, 50 % i 75 % del nombre d'episodis esperat a la línia
  base. L'objectiu de retenció és el 80 % de la capacitat màxima, subjecte a
  les proteccions de cada política.
- **Arxivament:** activat; els episodis retirats es desen a l'arxiu de l'E23.

## Què volen dir les mètriques

- **Fidelitat:** percentatge de decisions que trien la mateixa acció que A.
  No és una exactitud respecte d'una etiqueta externa; mesura coincidència
  amb la línia base.
- **Taxa d'encert de memòria:** consultes d'EpMem que retornen un resultat
  acceptable, com a percentatge del total de consultes.
- **Examinats:** episodis recorreguts per les consultes d'EpMem acumulats al
  llarg de l'execució. La reducció es calcula respecte d'A, que en va examinar
  3.255.377.
- **Temps per cicle:** `ms_cicle_mediana`, la mediana de les medianes diàries
  del temps del cicle CLIPS. Inclou el cicle complet i no només la cerca
  episòdica; pot variar amb la càrrega de l'ordinador.

## Resultats

### Capacitat del 25 %

| Braç | EpMem final | Examinats | Reducció vs A | Temps/cicle (ms) | Fidelitat | Encert memòria |
|---|---:|---:|---:|---:|---:|---:|
| A — Sense oblit | 5.040 | 3.255.377 | — | 27,96 | 100 % | 98,68 % |
| B — Finestra | 1.008 | 864.889 | 73,4 % | 105,59 | 100 % | 98,68 % |
| C — Aleatori | 1.215 | 995.177 | 69,4 % | 54,29 | 100 % | 98,68 % |
| D — Antiguitat | 1.215 | 979.736 | 69,9 % | 50,87 | 100 % | 98,68 % |
| E — Activació d'episodi | 1.215 | 986.007 | 69,7 % | 54,74 | 100 % | 98,68 % |
| F — Activació de grup | 1.215 | 1.231.983 | 62,2 % | 57,58 | 100 % | 98,68 % |
| G — Grup sense proteccions | 1.215 | 1.413.017 | 56,6 % | 44,34 | 100 % | 98,57 % |

### Capacitat del 50 %

| Braç | EpMem final | Examinats | Reducció vs A | Temps/cicle (ms) | Fidelitat | Encert memòria |
|---|---:|---:|---:|---:|---:|---:|
| A — Sense oblit | 5.040 | 3.255.377 | — | 27,96 | 100 % | 98,68 % |
| B — Finestra | 2.016 | 1.771.114 | 45,6 % | 82,10 | 100 % | 98,68 % |
| C — Aleatori | 2.505 | 2.040.366 | 37,3 % | 34,31 | 100 % | 98,68 % |
| D — Antiguitat | 2.505 | 1.991.959 | 38,8 % | 32,42 | 100 % | 98,68 % |
| E — Activació d'episodi | 2.505 | 1.985.880 | 39,0 % | 31,11 | 100 % | 98,68 % |
| F — Activació de grup | 2.505 | 2.271.524 | 30,2 % | 32,22 | 100 % | 98,68 % |
| G — Grup sense proteccions | 2.505 | 2.366.649 | 27,3 % | 53,50 | 100 % | 98,68 % |

### Capacitat del 75 %

| Braç | EpMem final | Examinats | Reducció vs A | Temps/cicle (ms) | Fidelitat | Encert memòria |
|---|---:|---:|---:|---:|---:|---:|
| A — Sense oblit | 5.040 | 3.255.377 | — | 27,96 | 100 % | 98,68 % |
| B — Finestra | 3.024 | 2.573.475 | 20,9 % | 25,59 | 100 % | 98,68 % |
| C — Aleatori | 3.522 | 2.834.330 | 12,9 % | 28,16 | 100 % | 98,68 % |
| D — Antiguitat | 3.522 | 2.803.312 | 13,9 % | 27,68 | 100 % | 98,68 % |
| E — Activació d'episodi | 3.522 | 2.802.072 | 13,9 % | 27,87 | 100 % | 98,68 % |
| F — Activació de grup | 3.522 | 2.966.869 | 8,9 % | 28,24 | 100 % | 98,68 % |
| G — Grup sense proteccions | 3.522 | 3.021.415 | 7,2 % | 28,26 | 100 % | 98,68 % |

## Lectura dels resultats

1. **Reducció de la cerca:** totes les polítiques van examinar menys episodis
   que A. L'estalvi va ser més marcat amb la capacitat del 25 % i més modest
   amb la del 75 %.
2. **Qualitat de decisió:** els 18 casos amb oblit van coincidir amb A en les
   5.040 decisions comparades (fidelitat del 100 %).
3. **Recuperació de memòria:** la taxa d'encert va ser del 98,68 % en gairebé
   tots els casos; G al 25 % va donar 98,57 %.
4. **Temps per cicle:** no segueix de manera simple el nombre d'episodis
   examinats. Per exemple, B al 25 % va tenir menys episodis examinats que A,
   però una mediana de cicle més alta (105,59 ms davant de 27,96 ms). Per tant,
   aquest pilot no demostra una acceleració del cicle complet.
5. **Estadística:** les comparacions aparellades per dia a `E23_tests.csv`
   donen `p (Holm) = 1` per energia, estrès, violacions, impasses i fidelitat.
   Per als episodis examinats, les diferències respecte d'A són significatives
   després de l'ajust de Holm (`p` ajustat entre aproximadament
   `1,44 × 10⁻¹⁴` i `8,6 × 10⁻⁶`).

L'experiment només té una llavor. Els 120 dies formen una mateixa simulació
seqüencial, de manera que les observacions diàries no són 120 repeticions
independents. Els valors estadístics descriuen aquesta execució i no són
substitut d'executar més llavors. Els temps per cicle són particularment
sensibles a la càrrega i no s'han d'interpretar com una comparació de
rendiment controlada.

## Descripció dels braços

| Braç | Criteri |
|---|---|
| **A — Sense oblit** | Línia base; no retira episodis. |
| **B — Finestra** | Retira episodis antics amb la política temporal existent. |
| **C — Aleatori** | Tria a l'atzar entre episodis elegibles. |
| **D — Antiguitat** | Prioritza els episodis elegibles més antics (FIFO). |
| **E — Activació d'episodi** | Prioritza episodis amb activació/ús episòdic més baix. |
| **F — Activació de grup** | Prioritza grups menys activats; aplica període de gràcia i conserva representants. |
| **G — Grup sense proteccions** | Com F, però sense període de gràcia ni mínim de representants; conserva el requisit de consolidació semàntica. |

B s'activa en superar el seu objectiu de retenció; C–G s'activen en superar
la capacitat màxima i retiren episodis per acostar-se a l'objectiu. Els detalls
de les polítiques són a [`../../estrategia_oblit.md`](../../estrategia_oblit.md).

## Fitxers d'origen

- [`E23_comparativa.csv`](./E23_comparativa.csv): taula resum emprada per a les comparatives.
- [`E23_tests.csv`](./E23_tests.csv): proves aparellades per dia i correcció de Holm.
- [`E23_compromis.svg`](./E23_compromis.svg): memòria final respecte de fidelitat.
- [`E23_per_dia.csv`](./E23_per_dia.csv): mètriques diàries.
- [`E23_horari.csv.gz`](./E23_horari.csv.gz): dades horàries completes.
- [`E23_memoria.csv`](./E23_memoria.csv) i [`E23_evolucio.csv`](./E23_evolucio.csv): evolució de la memòria.
- [`E23_oblit_auditoria.csv`](./E23_oblit_auditoria.csv): episodis retirats.
