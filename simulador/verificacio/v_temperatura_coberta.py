"""Validacio del model de temperatura de la coberta (balanc d'energia) amb mesures reals.

Referencia: Marrou et al. (2013), Agricultural and Forest Meteorology 177:117-132. A Montpeller,
sota panells fotovoltaics (densitat completa i mitja densitat) respecte de ple sol:
  - de dia, el cultiu estava ~3 C (blat) i ~5-5,7 C (enciam, cogombre) mes fresc;
  - de nit, l'enciam estava fins a ~4 C mes calent (20-01 h), el blat ~2 C;
  - la temperatura de l'aire no canviava.

Aqui es calcula, amb el temps real de tot el 2023 (Ribera de Sio), la temperatura del cultiu a
ple sol i sota el panell pla (transmissio 1 - GCR = 0,6), ben regat, amb el mateix model que fa
servir el simulador. Tambe es compara amb la formula simple anterior (aire + 0,006*llum + 2*sec).

    python verificacio/v_temperatura_coberta.py
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dades       # noqa: E402
import fenologia   # noqa: E402
import fisica      # noqa: E402

GCR = 0.4
TAU_OMBRA = 1 - GCR          # panell pla


def calcula(lloc="ribera_2022_2023", any_=2023) -> pd.DataFrame:
    l = dades.LLOCS[lloc]
    m = dades.carrega(lloc)
    m = m[m.index.year == any_]
    files, f_nuvol = [], 0.6
    for t, f in m.iterrows():
        elev, _ = fisica.sol_interval(l.lat, l.lon, t.to_pydatetime())
        fn = fisica.factor_nuvolositat(f["ghi"], elev, l.altitud)
        f_nuvol = fn if fn is not None else f_nuvol
        u2 = fisica.vent_2m(f["vent_mitja"])
        for cultiu in ("enciam", "tomaquet", "vinya"):
            e = fenologia.estat(cultiu, t.date())
            if not e.actiu:
                continue
            fila = {"t": t, "hora": t.hour, "cultiu": cultiu, "ghi": f["ghi"], "ta": f["temp"]}
            for nom, tau in (("sol", 1.0), ("ombra", TAU_OMBRA)):
                for reg, ks in (("regat", 1.0), ("sec", 0.2)):
                    et = f["et0"] * e.kc * (0.3 + 0.7 * tau) * ks
                    rn = fisica.radiacio_neta(f["ghi"] * tau, f["temp"], f["hr"], f_nuvol, tau)
                    fila[f"tc_{nom}_{reg}"] = fisica.temperatura_coberta(f["temp"], rn, et, e.h, u2)
                fila[f"simple_{nom}"] = fisica.temperatura_cultiu(f["temp"], f["ghi"] * tau, 90.0)
            files.append(fila)
    return pd.DataFrame(files)


def resum(d: pd.DataFrame) -> pd.DataFrame:
    dia = d[(d.hora >= 11) & (d.hora <= 15) & (d.ghi > 500)]
    nit = d[(d.hora >= 21) | (d.hora <= 1)]
    out = []
    for c, g in dia.groupby("cultiu"):
        n = nit[nit.cultiu == c]
        out.append({
            "cultiu": c,
            "hores_migdia": len(g),
            "Tc-Ta sol regat (migdia)": (g.tc_sol_regat - g.ta).mean(),
            "Tc-Ta sol sec (migdia)": (g.tc_sol_sec - g.ta).mean(),
            "ombra - sol, migdia (balanc)": (g.tc_ombra_regat - g.tc_sol_regat).mean(),
            "ombra - sol, migdia (formula simple)": (g.simple_ombra - g.simple_sol).mean(),
            "ombra - sol, nit 21-01 h (balanc)": (n.tc_ombra_regat - n.tc_sol_regat).mean(),
            "regat - sec, migdia": (g.tc_sol_regat - g.tc_sol_sec).mean(),
        })
    return pd.DataFrame(out).set_index("cultiu").round(2)


if __name__ == "__main__":
    r = resum(calcula())
    d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resultats", "validacio")
    os.makedirs(d, exist_ok=True)
    r.to_csv(os.path.join(d, "temperatura_coberta.csv"))
    pd.set_option("display.width", 200)
    print(r.T.to_string())
    print("\nMarrou et al. 2013 (mesurat): ombra - sol de dia -3 (blat) a -5,7 C (enciam); "
          "de nit fins a +4 C (enciam) i +2 C (blat).")
