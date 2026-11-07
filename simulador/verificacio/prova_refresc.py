"""Comprova que refrescar l'entorn CLIPS (ControladorSOAR._refresca) no canvia cap decisio.

Per a cada configuracio de memoria d'E20 simula N dies seguits dues vegades: sense refrescar mai i
refrescant cada R cicles (per defecte 20, mes sovint que en les execucions normals, per provar-ho
mes vegades). Compara totes les columnes de decisio hora a hora i el coneixement final.

Us: python verificacio/prova_refresc.py [--dies 30] [--refresc 20] [--config NOM ...]
"""
import argparse
import copy
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
import experiments as X  # noqa: E402
import simulador as S  # noqa: E402

COLUMNES = ("accio", "angle", "motiu", "impas", "us_chunk", "us_rl", "us_memoria", "us_smem",
            "riscos", "reg", "reg_motiu", "invariants", "energia_kwh")


def executa(cfg, dies, refresc):
    cfg = copy.deepcopy(cfg)
    cfg["controlador"]["refresc_cicles"] = refresc
    sim = S.Simulacio(cfg, 0)
    ctrl = S.ControladorSOAR(cfg, sim.domini)
    t0 = time.perf_counter()
    df = sim.executa(list(dies), controlador=ctrl, etiqueta="prova")
    return df, ctrl.coneixement(), time.perf_counter() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dies", type=int, default=30)
    ap.add_argument("--refresc", type=int, default=20)
    ap.add_argument("--config", nargs="*", default=None)
    a = ap.parse_args()
    ko = 0
    for nom, cfg, dies, _ in X._feines_e20(1):
        if a.config and nom not in a.config:
            continue
        d0, k0, t0 = executa(cfg, dies[:a.dies], 0)
        d1, k1, t1 = executa(cfg, dies[:a.dies], a.refresc)
        cols = [c for c in COLUMNES if c in d0]
        dif = int((d0[cols].astype(str) != d1[cols].astype(str)).any(axis=1).sum())
        kdif = [k for k in k0 if str(k0[k]) != str(k1.get(k))]
        ok = dif == 0 and not kdif
        ko += not ok
        print(f"{nom}: {len(d0)} files, {dif} diferents, coneixement diferent: {kdif or 'cap'}"
              f" | {t0:.0f} s sense refrescar, {t1:.0f} s refrescant -> {'OK' if ok else 'FALLA'}", flush=True)
    sys.exit(1 if ko else 0)


if __name__ == "__main__":
    main()
