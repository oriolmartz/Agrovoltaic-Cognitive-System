# Registre d'iteracions

El professor demana que l'experimentació no es faci només al final: cada resultat ha de servir
per revisar la implementació. Aquest registre recull cada iteració amb el mateix format, que és
el cicle de validació incremental de Batarseh & Gonzalez (2015):

**hipòtesi o pregunta → experiment → resultat → canvi → regressió (E1 + E2) → es torna a mesurar**

Les iteracions de la 0 a la 2 són d'abans del simulador. Es van detectar amb els fitxers
`run_soar` i van canviar el CLIPS directament.

| # | Data | Què es va observar | Experiment | Canvi | Comprovació | Estat |
|---|---|---|---|---|---|---|
| 0 | 16/10 | El chunk no es construïa: `implode$` generava `mitja alt critic` en lloc de `mitja\|alt\|critic` | `run_chunking` | funció `alternatives` i comprovació del `build` | el chunk es crea i es reutilitza | tancat |
| 1 | 16/10 | Sense lectura de vent i amb una previsió de 20 m/s, el panell es quedava a 15,5° | `run_soar_v1_1` | v1_2: regla `elabora-risc-mecanic-per-previsio` i resolució de l'impasse de dades per previsió o per historial | `run_chunking_v1_2` | tancat |
| 2 | 22/10 | v1_7 (parelles de trets) no millora la v1_6 | proves de l'equip | — | va donar lloc a la iteració 4 | tancat |
| 3 | 22/10 | L'enciam amb un 70 % d'aigua (el límit exacte) donava estrès "mitja" | **E3**, cas A07 | **v1_8**: marge de 1e-9 a `nivell-hidric` (coma flotant) | E1 59/59, E2 sense violacions, E3 de 56/57 a **57/57**, E7 idèntic | tancat |
| 4 | 22/10 | **Hipòtesi:** les parelles no milloren perquè el reforç gairebé no decideix. Mesura: decideix 1,3–1,5 de les 42 decisions diàries | **E9** pilot | — | **E10:** amb el reforç aïllat, les parelles SÍ que aprenen la tasca XOR (100 % contra 50 %, p = 1e-6). El problema no és la representació, sinó que el reforç només actua en empats exactes | obert (decisió de l'equip) |
| 5 | 22/10 | SOAR canvia molt d'operador: 8,2 canvis i 1,1 oscil·lacions al dia a Cantallops (seguidor comercial: 1,0 i 0,1); 8,0 canvis/dia a Ribera de Sió. **Revisat el 23/10 (iteració 15):** el 25–28 % d'aquests canvis no mouen el panell, i comptant per angle real les oscil·lacions són 0,49/dia a Cantallops i 0,19/dia a Ribera | **E4**, **E7** | — | — | obert (decisió de l'equip), però més petit del que semblava |
| 6 | 22/10 | El temps per cicle creix de 13 a 63–71 ms després de 20 dies (la memòria episòdica es recorre sencera a cada consulta) | **E9** pilot | — | — | obert |
| 7 | 22/10 | Hi ha 5 regles, agrupades en 4 casos, que no es disparen en cap dels 24.500 casos: `percep-dades-vent-critic`, `percep-sensor-no-valid`, `detecta-impas-sense-candidat`/`resol-sense-candidat`, `avalua-rebuig-fora-de-limits` | **E2** (cobertura) | — | — | obert: decidir si són inabastables (Preece: "unusable") o regles de protecció que es volen mantenir |
| 8 | 22/10 | L'ombra gairebé no redueix l'estrès per calor, i no depèn de les constants del model | **E7**, **E12** | — | — | obert: al migdia, l'angle de producció ja és gairebé pla, que és el que fa més ombra. Cal justificar-ho a l'informe o revisar el supòsit "pla = ombra" |
| 9 | 22/10 | (simulador) Els experiments de dies independents repetien el mateix soroll cada dia, i amb una probabilitat de fallada del 5 % no fallava mai cap sensor | E5 | el soroll de cada dia surt de llavor + data | E5 amb el 5 %: 1,35 impasses/dia (abans 0,03); s'han tornat a executar tots els experiments | tancat |
| 10 | 22/10 | (simulador) `chunking: false` no apagava el chunking (la funció espera TRUE/FALSE, no on/off) | E8 donava els mateixos números amb chunking i sense | corregit al pont | E8: sense chunking 0,73 impasses/dia, amb chunking 0,03 | tancat |
| 11 | 23/10 | Mesura de la memòria episòdica: amb epmem el temps per cicle passa d'11 a 22, 38 i 75 ms els dies 1, 10, 20 i 40 (uns +1,6 ms per dia, lineal). Sense epmem es manté entre 11 i 15 ms. Per a un cicle d'una hora no és cap problema, però creix sense límit perquè `epmem-cerca` recorre tots els episodis | mesura directa (40 dies seguits, amb epmem i sense) | — | — | obert: proposta de finestra (últims N episodis) o d'índex per sector i cultiu |
| 12 | 23/10 | El risc `meteorologic-advers` és a la plantilla, a l'ontologia i a `activa`, però cap regla el genera. La pluja (observada i prevista) no la fa servir cap regla | E14 i revisió del codi | — | — | obert: afegir una regla d'elaboració (pluja o calamarsa → risc meteorològic) o treure'l |
| 13 | 23/10 | Amb l'estratègia `random` de l'agenda, 1 decisió de 252 (pilot de 6 dies, 22/08 a les 12 h, vinya) va ser diferent: un empat entre `orientar-ombra` i `mantenir-posicio` desfet pel reforç cap a l'altre costat. Amb 20 dies, 0 de 840. **Hipòtesi:** l'ordre de disparament canvia l'ordre en què es guarden els episodis i, per tant, quin episodi "més recent" retorna la memòria i com evoluciona la Q. Les decisions sense memòria ni reforç no depenen mai de l'ordre | **E11** | — | — | obert: comprovar-ho amb E11 amb la memòria episòdica apagada |
| 14 | 23/10 | Si les transicions de fase no tenen salience −10, el cicle es trenca (21,9 % de decisions diferents amb `depth`, cap cicle tancat amb `breadth`) | **E11** (variants de salience) | — | Confirma que la salience −10 és necessària i que no s'ha d'usar per a res més | tancat (justifica el disseny) |
| 15 | 23/10 | (mètrica) El cas CP01 va mostrar que `orientar-produccio` i `mantenir-posicio` donen el mateix angle quan el panell ja és a l'òptim. Per tant, "canvis d'operador" i "oscil·lacions" comptaven canvis de nom sense moviment: el 25 % dels canvis (E7) i el 28 % (E4) no mouen el panell | **CP01**, E4, E7 | nova mètrica `oscillacions_angle` (A → B → A d'angle real) | Oscil·lacions per nom → per angle: E7 0,48 → **0,19**/dia, E4 1,06 → **0,49**/dia. Seguidor comercial: 0 i 0,12 | tancat. **Proposta a l'equip:** no proposar `orientar-produccio` si el panell ja és a l'angle òptim (dins de la tolerància), o marcar-los com a indiferents |
| 16 | 24/10 | El nucli `soar_v1_8.clp` era monolític i dificultava iterar sense barrejar responsabilitats | refactor estructural + comparació byte a byte | separació en 9 mòduls sota `clips_core/`; `soar.clp` es genera amb `build_clips.py` | SHA-256 idèntic a v1_8 (`8ee49d...27da1`); `CP02`–`CP11` continuen passant i `CP01` conserva la discrepància coneguda | tancat, sense canvi funcional |
| 17 | 24/10 | La topologia estava duplicada entre `ontologia_model.rdf`, `domini.clp` i la llista de panells de `config.json` | revisió arquitectònica + **E0** | `ontology_loader.py` carrega RDF amb RDFLib i projecta `sector`, `cultiu`, `panell` i `estat-sensor`; s’eliminen les instàncies duplicades del `deffacts` i `config.json` deixa d’enumerar panells | E0: 3 sectors, 3 cultius, 6 panells i 18 estats de sensor; CP 10/11 amb només CP01 (discrepància ja present a v1.8); E2 ràpid 5.670 decisions, 0 violacions i 0 violacions de monotonia; E3 57/57; E1 històric sense errors | tancat |
| 18 | 24/10 | `ontologia_domini.rdf` encara no participava en temps d’execució i el model conservava noms antics (`Estat_Panel`, `Angle_Objectiu`, accents en termes canònics) | ampliació d’**E0** + validació TBox→ABox | `ontology_loader.py` carrega també `ontologia_domini.rdf`, valida 15 classes, 5 propietats d’objecte, 5 propietats de dades i els `domain/range`; `ontologia_model.rdf` s’alinea amb el vocabulari canònic (`Estat_Panell`, `Angle_Optim_Produccio`, etc.) | E0 valida 36 relacions i 27 literals abans de projectar 3 sectors, 3 cultius, 6 panells i 18 estats de sensor | tancat a nivell estructural; repetir CP/E2/E3 al Windows després del merge |
| 19 | 24/10 | Domini i model compartien encara el mateix IRI i l’ABox redeclarava classes/propietats | revisió OWL + **E0** | `ontologia_domini.rdf` passa a `OntologiaDomini`; `ontologia_model.rdf` manté `OntologiaModel`, importa el domini amb `owl:imports` i conserva només les 43 instàncies de planta; el domini elimina aquestes instàncies duplicades i manté només 5 objectius canònics requerits per restriccions OWL | E0 comprova IRI, import, absència d’esquema duplicat i manté la mateixa projecció de 3 sectors, 3 cultius, 6 panells i 18 estats de sensor | tancat estructuralment; regressió funcional pendent de repetir al Windows |

## Com afegir una iteració

1. Apunteu què s'ha observat i amb quin experiment (amb la carpeta de `resultats/`).
2. Feu el canvi als **mòduls canònics** de `clips_core/`. Quan congeleu una fita per comparar-la, deseu-ne el snapshot monolític i el `run` a `../history/clips/simulator/`.
3. Regenereu `clips_core/soar.clp` i executeu la regressió:
   ```bash
   python verificacio/e0_ontologia.py
   python clips_core/build_clips.py
   python clips_core/build_clips.py --check-generated
   python verificacio/e1_regressio.py
   python verificacio/e2_graella.py --rapid --clp clips_core/soar.clp
   python verificacio/e3_llindars.py --clp clips_core/soar.clp
   ```
4. Torneu a executar l'experiment que va detectar el problema, mantenint `"clp": "clips_core/soar.clp"` a `config.json` o indicant explícitament el CLIPS canònic.
5. Apunteu el resultat (abans → després) i tanqueu la fila.
