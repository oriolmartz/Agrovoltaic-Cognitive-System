# Agrovoltaic-Cognitive-System

Sistema basat en regles per a una instal·lació agrovoltaica, amb un nucli cognitiu inspirat en SOAR implementat en CLIPS i una capa Python per a simulació, dades i experimentació.

## Estructura

```text
.
├── ontologia_domini.rdf
├── ontologia_model.rdf
├── history/                  # snapshots CLIPS monolítics congelats
└── simulador/
    ├── clips_core/           # font CLIPS modular activa
    ├── verificacio/          # E1-E3 i casos de prova
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

## Nucli CLIPS

La font canònica és modular i es troba a `simulador/clips_core/`. El fitxer `soar.clp` és un artefacte generat a partir de `modules.txt`:

```bash
python clips_core/build_clips.py
```

Per comprovar que el refactor inicial continua sent byte a byte equivalent a la baseline v1.8:

```bash
python clips_core/build_clips.py --check-baseline
```

Les versions monolítiques antigues es conserven a [`history/clips/`](history/clips/) exclusivament per regressió i traçabilitat.

## Verificació ràpida abans d'un push

Des de `simulador/`:

```bash
python clips_core/build_clips.py --check-baseline
python verificacio/casos_prova.py
python verificacio/e2_graella.py --rapid
python verificacio/e3_llindars.py
python verificacio/e1_regressio.py
```

En la baseline v1.8, `CP01` és una discrepància coneguda i analitzada; `CP02`--`CP11` passen. Quan es comencin a introduir canvis funcionals post-v1.8, és normal que `--check-baseline` deixi de donar `IDENTIC`.

## Regla d'iteració

1. Editar només els mòduls de `simulador/clips_core/`.
2. Regenerar `soar.clp` amb `build_clips.py`.
3. Executar la regressió i els casos de prova.
4. Documentar qualsevol canvi funcional a `simulador/REGISTRE_ITERACIONS.md`.
5. No modificar els snapshots de `history/`.
