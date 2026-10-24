# Històric de CLIPS

Aquesta carpeta conserva snapshots antics sense formar part del nucli actiu.

- `simulator/`: versions monolítiques utilitzades pels experiments i per E1 (v1_5--v1_8), amb els seus `run_soar_*`. **No s'han modificat**; els scripts de regressió i comparació apunten aquí.
  - `soar_v1_9.clp` i `run_soar_v1_9.clp` (24/10): la v1_9 (la v1_6, la correcció de `nivell-hidric` i el reg) en un sol fitxer **autònom**, amb la topologia al `deffacts`, perquè es pugui executar amb CLIPS sol (`clips -f run_soar_v1_9.clp`, 79 proves). El nucli canònic té el mateix coneixement, però la topologia la carrega de l'ontologia.
- `legacy-root/`: primera línia de desenvolupament que abans era a l'arrel del repositori (v1_2--v1_7, demos i `soar.clp`/`run_soar.clp` previs al simulador). Es conserva només per traçabilitat.

El nucli canònic actual és `../../simulador/clips_core/soar.clp`, generat a partir dels mòduls de `../../simulador/clips_core/modules.txt`.
