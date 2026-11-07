"""Mesura neta del temps per cicle (un sol proces, sense res mes en marxa).

Per a cada configuracio de memoria d'E20 simula els primers N dies seguits del 2023 (Ribera de Sio)
i desa, per dia: ms de CLIPS per cicle (columna 'ms' del simulador), temps de paret del dia sencer
(simulacio fisica + pont Python-CLIPS + CLIPS) i mida de la memoria episodica.
Amb aixo es veu quant creix el cost amb la memoria i es pot extrapolar a 1-3 anys.

Us: python verificacio/temps_cicle.py [--dies 365] [--config NOM ...]
Cada configuracio es desa a resultats/temps_cicle/dies_<config>.csv (es poden fer per separat) i el
resum (temps_resum.csv) es refa amb totes les que hi hagi.
"""
import argparse
import os
import sys
import time

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
import experiments as X  # noqa: E402
import simulador as S  # noqa: E402

SORTIDA = os.path.join(os.path.dirname(AQUI), "resultats", "temps_cicle")


def mesura(nom, cfg, dies):
    sim = S.Simulacio(cfg, 0)
    ctrl = S.ControladorSOAR(cfg, sim.domini)
    files = []
    for d in dies:
        t0 = time.perf_counter()
        df = sim.executa([d], controlador=ctrl, etiqueta=nom)
        paret = time.perf_counter() - t0
        ms = df["ms"][df["ms"] > 0]
        n_ep = sim.fotos[-1].get("n_epmem", np.nan) if sim.fotos else np.nan
        files.append({"config": nom, "dia": str(d), "cicles": len(ms),
                      "ms_clips_per_cicle": round(ms.mean(), 2) if len(ms) else 0.0,
                      "s_paret_dia": round(paret, 2), "n_epmem": n_ep})
        print(f"  {nom} {d}: {files[-1]['ms_clips_per_cicle']} ms/cicle, {paret:.1f} s/dia", flush=True)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dies", type=int, default=365)
    ap.add_argument("--config", nargs="*", default=None)
    a = ap.parse_args()
    os.makedirs(SORTIDA, exist_ok=True)
    feines = X._feines_e20(1)
    for nom, cfg, dies, e in feines:
        if a.config and nom not in a.config:
            continue
        pd.DataFrame(mesura(nom, cfg, dies[:a.dies])).to_csv(os.path.join(SORTIDA, f"dies_{nom}.csv"), index=False)
    fets = [os.path.join(SORTIDA, f"dies_{f[0]}.csv") for f in feines]
    t = pd.concat([pd.read_csv(f) for f in fets if os.path.isfile(f)], ignore_index=True)
    resum = []
    for nom, g in t.groupby("config", sort=False):
        x = np.arange(len(g))
        pend = np.polyfit(x, g["ms_clips_per_cicle"], 1)[0] if len(g) > 1 else 0.0
        resum.append({"config": nom, "dies": len(g),
                      "ms_clips_primera_setmana": round(g["ms_clips_per_cicle"].head(7).mean(), 1),
                      "ms_clips_ultima_setmana": round(g["ms_clips_per_cicle"].tail(7).mean(), 1),
                      "creixement_ms_per_dia": round(pend, 3),
                      "s_paret_per_dia_mitja": round(g["s_paret_dia"].mean(), 1),
                      "minuts_paret_total": round(g["s_paret_dia"].sum() / 60, 1),
                      "n_epmem_final": g["n_epmem"].iloc[-1]})
    r = pd.DataFrame(resum)
    r.to_csv(os.path.join(SORTIDA, "temps_resum.csv"), index=False)
    print(r.to_string(index=False))


if __name__ == "__main__":
    main()
