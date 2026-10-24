# Històric de CLIPS

Aquesta carpeta conserva snapshots antics sense formar part del nucli actiu.

- `simulator/`: versions monolítiques utilitzades pels experiments i per E1 (v1_5--v1_8), amb els seus `run_soar_*`. **No s'han modificat**; els scripts de regressió i comparació apunten aquí.
- `legacy-root/`: primera línia de desenvolupament que abans era a l'arrel del repositori (v1_2--v1_7, demos i `soar.clp`/`run_soar.clp` previs al simulador). Es conserva només per traçabilitat.

El nucli canònic actual és `../../simulador/clips_core/soar.clp`, generat a partir dels mòduls de `../../simulador/clips_core/modules.txt`.
