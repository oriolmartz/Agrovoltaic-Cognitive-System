"""Prova dels punts de control d'E16: N dies seguits d'una tirada han de donar exactament el mateix
que N/2 dies, desar l'estat (pickle), crear un controlador i una simulacio nous, restaurar i fer la
resta. Es comparen totes les columnes de resultats excepte el temps de calcul (ms).

    python verificacio/prova_punt_control.py [dies] [lloc]
"""
import os
import pickle
import sys

import pandas as pd

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)
import simulador as S  # noqa: E402


def main(n=6, lloc="ribera_2022_2023"):
    # amb lloc=cantallops el sensor de vent falla un 15 %: hi ha impasses i chunks al punt de control
    esc = {"lloc": lloc, "mode_dies": "sequencial", "controlador": {"epmem": True}}
    if lloc == "cantallops":
        esc["sensors"] = {"p_absent": {"vent": 0.15}}
    cfg = S.carrega_config(esc)
    dies = S.selecciona_dies(cfg)[:n]
    # de cop
    sim = S.Simulacio(cfg, 0)
    ctrl = S.ControladorSOAR(cfg, sim.domini)
    a = pd.concat([sim.executa([d], controlador=ctrl) for d in dies], ignore_index=True)
    # amb punt de control a la meitat
    sim = S.Simulacio(cfg, 0)
    ctrl = S.ControladorSOAR(cfg, sim.domini)
    m = n // 2
    b1 = [sim.executa([d], controlador=ctrl) for d in dies[:m]]
    agenda = list(ctrl.c.env.activations())
    print("al punt de control:", {k: (len(v) if isinstance(v, list) else v) for k, v in ctrl.coneixement().items()})
    est = pickle.dumps({"sim": sim.desa_estat(), "ctrl": ctrl.desa_estat()})
    del sim, ctrl
    est = pickle.loads(est)
    sim = S.Simulacio(cfg, 0)
    ctrl = S.ControladorSOAR(cfg, sim.domini)
    sim.restaura_estat(est["sim"])
    ctrl.restaura_estat(est["ctrl"])
    agenda2 = list(ctrl.c.env.activations())
    b = pd.concat(b1 + [sim.executa([d], controlador=ctrl) for d in dies[m:]], ignore_index=True)
    cols = [c for c in a.columns if c not in ("ms", "ms_cicle", "ms_per_cicle")]
    print(f"agenda abans de desar: {len(agenda)} activacions; despres de restaurar: {len(agenda2)}")
    dif = pd.DataFrame({c: ~((a[c] == b[c]) | (a[c].isna() & b[c].isna())) for c in cols})
    print(f"{len(a)} files, {len(cols)} columnes; files diferents: {int(dif.any(axis=1).sum())}")
    if dif.any().any():
        print("columnes diferents:", list(dif.columns[dif.any()]))
        i = dif.any(axis=1).idxmax()
        print(pd.DataFrame({"de_cop": a.loc[i, cols], "amb_punt": b.loc[i, cols]})[dif.loc[i]])
        print(a.loc[i, ["dia", "hora", "sector"]].tolist(), "primer dia despres del punt:", dies[m])
        sys.exit(1)
    print("IDENTIC")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 6, *sys.argv[2:3])
