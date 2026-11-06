# Estratègia d'oblit per a la memòria episòdica i semàntica

Aquest document defineix una estratègia d'oblit per al controlador CLIPS
inspirat en SOAR i el disseny d'un experiment per comparar-la amb la
situació sense oblit. La implementació experimental és E23, a
`experiments.py`; aquest document conserva el disseny, les decisions i els
resultats inicials.

## 1. Objectiu

Fer que la cerca en memòria sigui més ràpida evitant que s'acumulin massa
episodis (`epmem-episodi`), sense perdre qualitat en les decisions. L'oblit ha
de ser:

- **Controlable:** amb paràmetres a la configuració.
- **Segur:** no pot esborrar l'única experiència d'una situació poc coneguda.
- **Mesurable:** cada decisió d'oblit s'ha de poder auditar i comparar amb una
  línia base sense oblit.

## 2. Punt de partida

### Estat actual del repositori

- `epmem-episodi` són registres a llarg termini amb identificador creixent. La
  recuperació és una cerca per semblança sobre trets plans, amb índex per
  operador.
- `smem-resum` agrega els episodis valorats per sector, operador i clau de
  situació, amb recomptes de casos bons, neutres i dolents.
- Quan un resum arriba al mínim de casos (3 per defecte), el controlador el
  consulta en comptes d'EpMem per aquell operador i situació.
- Amb `smem_finestra > 0`, els episodis consolidats antics poden sortir de la
  memòria de treball només si el resum corresponent ja té el mínim de casos.
  Si hi ha `smem_arxiu`, s'hi afegeixen en format `load-facts`.
- Els resums no s'obliden mai i els comptadors no decauen.

### Què diu la literatura

- Derbinsky i Laird gestionen la memòria de treball de Soar amb **activació de
  nivell base**: l'activació és `ln(Σ tᵢ^−d)`, on `tᵢ` és el temps des de cada
  reforç i `d` el paràmetre de decaïment. Cada ús reforça l'element i amb el
  temps l'activació cau; els elements amb activació baixa són candidats a
  eliminar.
- Nuxoll, Tecuci, Ho i Wang (2010) van comparar tres algorismes d'oblit per a
  memòria episòdica: aleatori, el més antic, i el de menor activació (segons
  freqüència i recència d'ús). L'aleatori i el per antiguitat van donar
  resultats semblants, i l'activació va seleccionar millor els records de menys
  utilitat i va millorar el rendiment de l'agent.
- El grup de Laird parla de **retenció que preserva la competència** i d'una
  gestió de la memòria de treball que aprofita la memòria semàntica per
  millorar l'escalabilitat de l'episòdica. *(Detall no verificat: només s'ha
  consultat una diapositiva d'un informe; convé revisar l'article de 2013
  abans de citar-ne el mecanisme exacte.)*
- Oblidar estalvia recursos de cerca, però pot perdre coneixement útil (Li i
  Laird).

## 3. Un problema de disseny a resoldre

Si l'activació es calcula només amb les recuperacions episòdiques, apareix una
degeneració: els episodis que la regla actual permet retirar són justament els
que ja no es recuperen, perquè el resum corresponent ja respon per ells. Sense
reforços, l'activació d'aquests episodis no es diferencia de la seva
antiguitat, i el criteri acaba sent equivalent a l'oblit per antiguitat.

Per això es proposa una activació a dos nivells. *(Decisió de disseny pròpia;
no ve d'un article.)*

## 4. Estratègia proposada: oblit per grups amb retenció que preserva la competència

### 4.1 Unitat d'activació: el grup

Un **grup** és la combinació sector + operador + clau de situació, és a dir, la
mateixa clau que identifica els `smem-resum`.

- Cada vegada que s'utilitza un grup (es consulta el seu resum o es recupera
  un dels seus episodis), el grup rep un reforç.
- L'activació del grup és `ln(Σ tᵢ^−d)`, amb el temps mesurat en **cicles
  horaris**.
- Valor inicial de `d`: 0,5 (valor per defecte d'ACT-R). S'ha d'ajustar
  experimentalment.

### 4.2 Quan s'activa

Quan el nombre d'`epmem-episodi` supera una **capacitat màxima**, es retiren
episodis fins arribar a una **capacitat objectiu** inferior (per exemple, el
80% de la màxima). Així l'oblit no s'executa a cada cicle.

### 4.3 Què es pot retirar

Un episodi només és elegible si compleix totes aquestes condicions:

1. Està consolidat en un resum que té el mínim de casos (condició que ja
   existeix al codi actual).
2. Té més de *H* hores d'antiguitat (**període de gràcia**), de manera que
   mai es retiren els episodis recents.
3. El grup conserva almenys *K* episodis representatius després de l'oblit.
   Entre els representatius es prioritzen els valorats com a `bona` o
   `dolenta`, perquè són els únics que generen preferència. Els neutres no en
   generen.

### 4.4 En quin ordre

1. Es processen primer els grups de **menor activació**.
2. Dins de cada grup, primer els episodis **neutres** i després els més
   **antics**.

### 4.5 On van els episodis retirats

- Per defecte, s'**arxiven** a `smem_arxiu`, de manera que l'oblit és
  reversible.
- Hi ha una variant d'**eliminació real** (sense arxivar) per mesurar l'efecte
  de l'oblit sense xarxa de seguretat.

### 4.6 Què no s'oblida

Els `smem-resum` no s'obliden en el primer experiment. El seu nombre està
acotat per la discretització de la clau, però es mesura igualment la seva mida
(vegeu la secció 7).

## 5. Braços de l'experiment

Tots els braços comparteixen la mateixa capacitat màxima i objectiu. Només
canvia el criteri de selecció.

| Braç | Descripció |
|---|---|
| **A. Sense oblit** | Línia base |
| **B. Finestra actual** | `smem_finestra` actual (per antiguitat, amb condició de resum) |
| **C. Aleatori** | Aleatori entre els episodis elegibles |
| **D. Per antiguitat** | El més antic dels elegibles (FIFO) |
| **E. Activació d'episodi** | Activació només amb recuperacions episòdiques (mostra la degeneració de la secció 3) |
| **F. Activació de grup** | L'estratègia proposada (secció 4) |
| **G. F sense proteccions** | Com F, sense el mínim *K* ni el període de gràcia, per mesurar quant aporten les proteccions |

L'estructura aleatori / antiguitat / activació segueix la comparació de Nuxoll
et al. (2010). Els braços E, F i G són l'aportació específica d'aquest cas.

## 6. Disseny experimental

- **Escenari:** `mode_dies: "sequencial"`, EpMem i SMem activades. Cal una
  finestra llarga (com a mínim 60–120 dies); deu dies no acumulen prou
  episodis perquè l'oblit tingui efecte. Si hi ha més d'un lloc o estació
  disponibles, repetir-ho en cadascun.
- **Capacitat:** es fixa com a fracció del nombre final d'episodis de la línia
  base (per exemple, 75%, 50% i 25%), de manera que els resultats siguin
  comparables entre escenaris.
- **Repeticions:** el braç aleatori necessita diverses llavors (per exemple,
  5). Si la resta del sistema és determinista, una execució per braç és
  suficient; cal comprovar-ho.
- **Control:** només varien els paràmetres d'oblit. La resta de la
  configuració és idèntica entre braços.

## 7. Mètriques

### Cost (l'objectiu de l'oblit)

- Nombre d'`epmem-episodi` i de `smem-resum` al llarg del temps (corba
  d'acumulació).
- Temps de la fase d'avaluació per cicle. És sorollós: s'ha d'usar la mediana
  de diverses execucions.
- Una mesura independent de la màquina: nombre d'episodis escanejats per
  consulta.

### Qualitat

- Els resultats de simulació que ja surten al CSV (cobertura, riscos, fallades
  d'actuador, impassos). Cal confirmar les columnes exactes.
- **Fidelitat respecte de la línia base:** percentatge de decisions (per sector
  i hora) en què l'operador triat coincideix amb el del braç A. És la mesura
  més directa de l'efecte de l'oblit.
- **Ús de la memòria:** taxa d'`us_memoria` i `us_smem`, proporció de
  consultes que troben un record per sobre del llindar de similitud, i
  similitud mitjana.

### Resultat final

Una gràfica de cost respecte de qualitat per braç i per capacitat, que mostri
quin és el pitjor compromís acceptable.

## 8. Hipòtesis

- **H1:** sense oblit, el cost de cerca creix amb el nombre d'episodis; amb
  oblit, s'estabilitza.
- **H2:** el braç F és igual o millor que C, D i E en fidelitat, a igual
  capacitat (anàleg del resultat de Nuxoll et al. 2010).
- **H3:** el braç G degrada més que F, cosa que justificaria les proteccions
  (compromís conegut entre estalvi de cerca i pèrdua de coneixement útil).

## 9. Riscos

- **Risc principal: l'oblit pot no accelerar res.** Quan un resum està
  consolidat, el sistema gairebé només consulta SMem, de manera que el cost
  de cerca pot venir d'altres parts (percepció, Python, regles) i no d'EpMem.
  E23 registra el nombre d'episodis examinats per consulta i la mediana del
  temps del cicle CLIPS. Aquesta última és una mesura aproximada, no el temps
  aïllat de la fase d'avaluació; la interpretació del temps necessita diverses
  repeticions i una màquina no saturada.
- **Pèrdua de coneixement útil:** controlada amb les proteccions de la secció
  4.3 i mesurada amb la fidelitat.
- **Sorolls de mesura de temps:** mitigats amb la mètrica independent de la
  màquina i amb repeticions.

## 10. Extensió (fase 2)

Els comptadors dels resums no decauen, de manera que l'experiència antiga pesa
igual que la recent. Si es vol provar un entorn no estacionari (canvi
d'estació o de clima), el pas següent seria afegir un **decaïment als
comptadors** i comprovar si l'oblit millora l'adaptació en lloc d'empitjorar-la.
Es deixa fora del primer experiment per no barrejar efectes.

## 11. Implementació i execució

L'experiment està integrat com a **E23**. Des de `simulador/`:

```powershell
python experiments.py E23 --dies 60 --llavors 5 --processos 4
```

`--dies` limita les simulacions als primers N dies de 2023; sense `--dies`
s'utilitza tot l'any. `--llavors 5` executa cinc repeticions aparellades,
incloent-hi cinc llavors per al braç aleatori. Per fer eliminació real en lloc
d'arxivar els episodis:

```powershell
python experiments.py E23 --dies 60 --llavors 5 --sense-arxiu
```

Les tasques acabades queden desades a `resultats/E23/parts/`, de manera que es
poden reprendre sense repetir-les. `--part N` executa una única tasca (índex
de `0` a `19 × nombre_de_llavors - 1`). Les capacitats màximes són el 75 %, el
50 % i el 25 % del nombre esperat d'episodis de la línia base; l'objectiu de
retenció és el 80 % de la capacitat màxima. Els braços B–G comparteixen el
mínim de casos semàntics; E i F també fan servir el període de gràcia i la
retenció de representants. G n'omet les dues proteccions. B aplica la finestra
temporal existent i s'activa quan supera l'objectiu; els altres braços esperen
a superar la capacitat màxima.

L'estat `controlador.oblit` de `config.json` és opcional (`null` per defecte);
E23 el configura per cada braç. Es pot veure un registre `[OBLIT]` a la traça
CLIPS quan s'activa `--traca`; l'CSV `E23_oblit_auditoria.csv` desa els
identificadors retirats. Per defecte, els episodis es copien a fitxers `.facts`
a `resultats/E23/arxiu/` abans de retirar-los.

Resultats:

- `E23_comparativa.csv`: energia, estrès, fidelitat a A, mida final de memòria,
  episodis examinats, encerts de recuperació i mediana del temps de cicle.
- `E23_tests.csv`: comparacions aparellades amb A, Wilcoxon i ajust de Holm.
- `E23_evolucio.csv`: fotos diàries del nombre d'episodis/resums i comptadors.
- `E23_compromis.svg`: gràfica d'episodis finals respecte de fidelitat.
- `E23_oblit_auditoria.csv`: cicles i identificadors dels episodis retirats.

## 12. Resultat pilot

Pilot executat amb `--dies 60 --llavors 1` (1 de gener–1 de març de 2023):
2.520 episodis a la línia base. A capacitat del 25 %, tots els braços
van coincidir amb la línia base en les 2.520 decisions i van donar la mateixa
energia mitjana diària (211,39 kWh). Els resultats de cerca:

| Braç (25 %) | Episodis finals | Episodis examinats | Reducció d'exàmens vs A | Fidelitat |
|---|---:|---:|---:|---:|
| A. Sense oblit | 2.520 | 407.311 | — | 100 % |
| B. Finestra | 504 | 117.864 | 71,1 % | 100 % |
| C. Aleatori | 585 | 133.526 | 67,2 % | 100 % |
| D. Antiguitat | 585 | 132.657 | 67,4 % | 100 % |
| E. Activació episòdica | 585 | 132.255 | 67,5 % | 100 % |
| F. Activació de grup | 585 | 149.662 | 63,3 % | 100 % |
| G. Grup sense proteccions | 585 | 203.998 | 49,9 % | 100 % |

En aquest període curt, la cerca es va reduir, però no hi va haver diferències
de decisions, energia ni estrès; les comparacions aparellades d'energia i
fidelitat van donar `p = 1`. Això no valida encara H2 ni H3: cal executar més
dies i llavors. Els temps de cicle del pilot no s'han d'interpretar com una
acceleració, perquè les feines es van executar en paral·lel i la mediana és
sensible a la càrrega de la màquina. L'indicador més sòlid d'aquest pilot és
el nombre d'episodis examinats.

## 13. Referències

- Nuxoll, A. M., Tecuci, D., Ho, Wang (2010). *Comparing Forgetting
  Algorithms for Artificial Episodic Memory Systems.* Symposium "Remembering
  Who We Are – Human Memory for Artificial Agents", AISB 2010.
- Nuxoll, A. M., Laird, J. E. (2012). *Enhancing intelligent agents with
  episodic memory.* Cognitive Systems Research, 17–18, 34–48.
- Nuxoll, A. M., Laird, J. E. (2007). *Extending Cognitive Architecture with
  Episodic Memory.* AAAI 2007.
- Derbinsky, N., Laird, J. E. (2009). *Efficiently implementing episodic
  memory.* ICCBR 2009.
- Derbinsky, N., Laird, J. E. (2013). *Effective and efficient forgetting of
  learned knowledge in Soar's working and procedural memories.* Cognitive
  Systems Research, 24, 104–113.
- Gorski, N. A., Laird, J. E. (2009). *Learning to Use Episodic Memory.* ICCM
  2009.
- Chong (2004). Treball sobre l'aplicació de l'aprenentatge de nivell base
  d'ACT-R a les regles apreses per chunking en l'arquitectura EASE. ICCM 2004.
  *(Títol i autoria completa per verificar.)*
- Li, J., Laird, J. E. *Preemptive Strategies for Overcoming the Forgetting of
  Goals.* AAAI.
- Plewnia, J., Peller-Konrad, F., Asfour, T. (2024). *Forgetting in Robotic
  Episodic Long-Term Memory.* KIT.
