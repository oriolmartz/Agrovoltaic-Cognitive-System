# Agrovoltaic-Cognitive-System

Sistema basat en regles per a una instal·lació agrovoltaica, amb un nucli cognitiu inspirat en SOAR implementat en CLIPS i una capa Python per a simulació, dades, integració RDF i experimentació.

## Arquitectura

```text
ontologia_domini.rdf
        │  esquema autoritatiu: classes, propietats, domain/range
        │
        └──── owl:imports ◄──── ontologia_model.rdf
                              │  ABox: només instàncies de planta
                              ▼
simulador/ontology_loader.py
        │  RDFLib: validació TBox→ABox + projecció
        ▼
fets CLIPS de topologia
(sector, cultiu, panell, estat-sensor)
        │
        ▼
clips_core/soar.clp
        │  elaboració, candidats, preferències,
        │  impasses, selecció, aplicació i memòria
        ▼
ordre-actuador + explicació
```

`ontologia_domini.rdf` és el **contracte conceptual autoritatiu**: té un IRI propi (`OntologiaDomini`), defineix classes, propietats, jerarquies i `domain/range`, i conserva només cinc individus canònics d'objectiu que formen part del vocabulari del domini. `ontologia_model.rdf` té un IRI diferent (`OntologiaModel`), l'importa explícitament amb `owl:imports` i conté només les instàncies concretes de la planta. `ontology_loader.py` valida aquesta separació i només després projecta l'ABox a fets CLIPS. Python no avalua candidats ni selecciona accions: **la decisió continua íntegrament dins de CLIPS**.

Els llindars agronòmics i els objectius de control continuen explícits a CLIPS perquè l'ontologia actual encara no n'instancia els valors operacionals.

## Estructura

```text
.
├── ontologia_domini.rdf       # esquema del domini + objectius canònics
├── ontologia_model.rdf        # ABox: instàncies de planta; importa el domini
├── history/                   # snapshots CLIPS monolítics congelats
└── simulador/
    ├── ontology_loader.py     # RDF -> model Python -> fets CLIPS
    ├── clips_bridge.py        # contracte Python <-> CLIPS
    ├── clips_core/            # font CLIPS modular activa
    ├── verificacio/           # E0-E3 i casos de prova
    ├── dades_reals/
    ├── escenaris/
    ├── resultats/
    ├── simulador.py
    └── experiments.py
```

La documentació completa del simulador i dels experiments és a [`simulador/README.md`](simulador/README.md).

## Instal·lació

Es recomana Python **3.11, 3.12 o 3.13**.

```bash
cd simulador
python -m venv venv
```

Windows:

```powershell
venv\Scripts\activate
python -m pip install -r requirements.txt
```

Linux/macOS:

```bash
source venv/bin/activate
python -m pip install -r requirements.txt
```

## Integració ontològica

Per validar el RDF i veure la projecció:

```bash
python ontology_loader.py
python ontology_loader.py --fets
python verificacio/e0_ontologia.py
```

`E0` comprova que:

- `ontologia_domini.rdf` i `ontologia_model.rdf` tenen IRI propis i es poden interpretar;
- `ontologia_model.rdf` importa explícitament `ontologia_domini.rdf` i no redeclara classes ni propietats;
- el model utilitza el vocabulari operacional canònic del domini;
- les relacions del model respecten els `domain/range` definits al domini;
- hi ha almenys tres sectors;
- sectors, cultius, panells i sensors es projecten als fets esperats;
- `config.json` no duplica la llista de panells;
- `clips_core/core/domini.clp` no torna a instanciar manualment la topologia.

## Nucli CLIPS

La font canònica és modular i es troba a `simulador/clips_core/`. `soar.clp` és generat a partir de `modules.txt`:

```bash
python clips_core/build_clips.py
python clips_core/build_clips.py --check-generated
```

Les versions monolítiques es conserven a `history/clips/` (de la v1_5 a la v1_9). Des de la integració RDF el nucli actiu **divergeix intencionalment** de v1.8 a nivell de representació: s'ha eliminat la topologia duplicada del `deffacts`. Per tant, `--check-baseline` ja no és una prova de pre-push; només serveix per comparar amb la fita històrica.


## Verificació ràpida abans d'un push

Des de `simulador/`:

```bash
python verificacio/e0_ontologia.py
python clips_core/build_clips.py --check-generated
python verificacio/casos_prova.py
python verificacio/e2_graella.py --rapid
python verificacio/e3_llindars.py
python verificacio/e1_regressio.py
```

Amb la v1_9, E1 ha de donar fail 0: també la versió canònica (`actual`, 91 proves), que es prova amb la topologia de `ontologia_model.rdf` (E1 la projecta a `clips_core/topologia_rdf.clp`, un fitxer generat). Les snapshots històriques es reprodueixen sense injectar l'ontologia. E0 ha de sortir OK, E3 75/75 i els casos de prova 14/14: 

## Regla d'iteració

1. Canviar el vocabulari/esquema general a `ontologia_domini.rdf` només si canvia el domini.
2. Canviar la topologia o les instàncies estàtiques a `ontologia_model.rdf`, sempre usant el vocabulari canònic del domini.
3. Canviar regles/plantilles/llindars operacionals als mòduls de `simulador/clips_core/`.
4. Regenerar `soar.clp` amb `build_clips.py`.
5. Executar E0 + regressió + casos de prova.
6. Documentar qualsevol canvi funcional a `simulador/REGISTRE_ITERACIONS.md`.
7. No modificar els snapshots de `history/`.

## Interfície web (bessó digital 3D)

```bash
cd simulador
python -m pip install -r requirements.txt
python webapp.py        # http://127.0.0.1:8000
```

La web és només una capa de presentació: l'angle dels panells i, des de la v1_9, també el reg es decideixen dins de CLIPS; `webapp.py` només executa el simulador i serveix les dades.

### Simular dies o mesos

Cada escenari mostra la **durada en dies** (calculada de les dades reals) i una estimació del temps. Un dia es simula a l'instant; un **període** (fins a mesos) es llança com a treball en segon pla amb progrés i cancel·lació:

| Mode | Què fa | Quan usar-lo |
|---|---|---|
| **Blocs mensuals** (per defecte en períodes) | un bloc continu per mes natural, repartit entre processos (com E14/E15) | sis mesos en ~1 minut amb diversos nuclis |
| **Dies independents** | cada dia comença de nou (com E1–E7), repartit entre processos | comparar dies, el més ràpid |
| **Continu** | una sola execució: l'aigua del sòl i l'aprenentatge passen de dia en dia | el més realista, però el cost per dia creix (~0,3 s + 0,043 s·dia) |

Amb **Comparar** s'executen també el seguidor comercial i el panell fix sobre els mateixos dies reals; la pestanya **Període** mostra l'experiment (diferència mitjana per dia, IC 95 %, p de Holm i magnitud, amb `estadistica.py`). A **Opcions** hi ha la humitat inicial del sòl (mesura real XMS-Cat o configuració) i *què passaria si…* (temperatura, vent, radiació i pluja modificats sobre les dades reals).

El navegador només rep una **taula diària**; els registres horaris d'un dia es demanen quan es clica (calendari, tira de dies, `[` `]`, «Dies seguits»). Així escala amb el nombre de dies. L'URL `?job=<id>` reobre un període ja simulat mentre el servidor segueixi en marxa.

### Afegir dades (escalable)

- **Més mesos d'un lloc**: substitueix els fitxers de `dades_reals/` per versions més llargues. Els escenaris que no fixen `"dies"` i l'escenari automàtic **«Totes les dades»** creixen sols.
- **Un lloc nou**: deixa-hi els seus tres fitxers i crea `dades_reals/llocs/<id>.json` (plantilla: `dades_reals/llocs/exemple.json.plantilla`). Apareix a la web sense tocar codi.
- **Un experiment**: un JSON a `escenaris/` amb `lloc`, `dies` (`des_de`/`fins_a`), `blocs: "mes"` i, si cal, `modificadors` (p. ex. `escenaris/ribera_estiu_menys_pluja.json`).

```text
simulador/
├── webapp.py            # API FastAPI (/api/bootstrap, /api/days, /api/simulate, /api/jobs…)
├── webcore.py           # escenaris, configuració, agregats diaris i estadística (sense FastAPI)
├── webjobs.py           # treballs llargs en processos (progrés, cancel·lació, estimació)
└── frontend/
    ├── index.html · styles.css · app.js     # sala de control, cinta de decisions, anàlisi
    ├── period.js · scenarios.js · jobs.js   # vista de període, durada d'escenaris, client de treballs
    ├── twin3d.js · scene/                   # escena Three.js (panells, sectors, reg, clima)
    ├── timeline.js · charts.js · ui.js      # cinta, gràfics SVG i vocabulari de presentació
    └── vendor/                              # Three.js r186 i tipografies en local (sense CDN)
```

- Escenaris de demostració d'un dia: `demo_sequera_reg` (el CLIPS decideix regar) i `demo_pluja_real`. De període: `ribera_6_mesos` (183 dies), `cantallops_hivern_primavera` (95) i `ribera_estiu_menys_pluja` (62, *what-if*).
- Comprovacions: `python verificacio/e15_frontend.py` (estàtica) i `python verificacio/e17_periode.py` (catàleg, lloc nou per JSON i treball en processos).
