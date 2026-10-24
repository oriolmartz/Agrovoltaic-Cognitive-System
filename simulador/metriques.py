"""Metriques d'una simulacio (a partir del CSV horari que escriu simulador.py).

Unitat d'analisi = un DIA (una repeticio). Totes les metriques es calculen per dia
i despres es resumeixen; aixi els tests estadistics treballen amb mostres
independents (o aparellades si dues configuracions fan servir els mateixos dies).
"""

from __future__ import annotations

import pandas as pd

CLAU = ["etiqueta", "controlador", "llavor", "dia"]


def _oscillacions(acc: pd.Series) -> int:
    a = acc.tolist()
    return sum(1 for i in range(2, len(a)) if a[i] == a[i - 2] and a[i] != a[i - 1])


def per_dia(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila per (etiqueta, controlador, llavor, dia)."""
    df = df.copy()
    for col in ("reg_m3", "reg_net_mm", "bomba_kwh", "percolacio_mm"):   # CSV d'abans del reg (v1_9)
        if col not in df:
            df[col] = 0.0
    g = df.groupby(CLAU, sort=False)
    out = g.agg(
        energia_kwh=("P_kw", "sum"),
        energia_opt_kwh=("P_opt_kw", "sum"),
        h_estres_rad=("estres_rad", "sum"),
        h_estres_calor=("estres_calor", "sum"),
        h_calor_critica=("calor_critica", "sum"),
        h_estres_aigua=("estres_aigua", "sum"),
        violacions=("violacio_seguretat", "sum"),
        exposicions=("exposicio_vent", "sum"),
        h_vent_perillos=("vent_real", lambda v: int((v >= 16).sum())),
        moviment_graus=("moviment", "sum"),
        aigua_reg_m3=("reg_m3", "sum"),
        regs=("reg_net_mm", lambda x: int((x > 0).sum())),
        bomba_kwh=("bomba_kwh", "sum"),
        percolacio_mm=("percolacio_mm", "sum"),
        impasses=("impas", lambda x: int((x.fillna("") != "").sum())),
        chunks_nous=("chunks_nous", "sum"),
        decisions_chunk=("us_chunk", "sum"),
        decisions_rl=("us_rl", "sum"),
        invariants_ko=("invariants_ko", lambda x: int((x.fillna("") != "").sum())),
        regles_per_cicle=("regles", lambda x: x[x > 0].mean() if (x > 0).any() else 0.0),
        ms_per_cicle=("ms", lambda x: x[x > 0].mean() if (x > 0).any() else 0.0),
        cicles=("cicle", "nunique"),
    ).reset_index()
    out["energia_neta_kwh"] = out["energia_kwh"] - out["bomba_kwh"]
    out["rendiment_pct"] = 100 * out["energia_kwh"] / out["energia_opt_kwh"].where(out["energia_opt_kwh"] > 0)
    canvis = (df.sort_values("cicle").groupby(CLAU + ["sector"], sort=False)["accio"]
              .agg(lambda a: int((a != a.shift()).sum() - 1)).groupby(level=CLAU).sum())
    osc = (df.sort_values("cicle").groupby(CLAU + ["sector"], sort=False)["accio"]
           .agg(_oscillacions).groupby(level=CLAU).sum())
    out = out.merge(canvis.rename("canvis_operador").reset_index(), on=CLAU)
    out = out.merge(osc.rename("oscillacions").reset_index(), on=CLAU)
    # Oscil·lacions de debo: el panell va a un angle, en surt i hi torna (A -> B -> A d'angle).
    # El nom de l'operador pot canviar sense que el panell es mogui (orientar-produccio i
    # mantenir-posicio coincideixen quan ja es a l'angle optim), aixi que es compta tambe per angle.
    def _osc_angle(a):
        a = a.round(1).tolist()
        return sum(1 for i in range(2, len(a)) if a[i] == a[i - 2] and a[i] != a[i - 1])
    osc_a = (df.sort_values("cicle").groupby(CLAU + ["sector"], sort=False)["angle_real"]
             .agg(_osc_angle).groupby(level=CLAU).sum())
    out = out.merge(osc_a.rename("oscillacions_angle").reset_index(), on=CLAU)
    final = (df.sort_values("cicle").groupby(CLAU + ["sector"], sort=False)["aigua_pct"].last()
             .groupby(level=CLAU).mean())
    out = out.merge(final.rename("aigua_final_pct").reset_index(), on=CLAU)
    # Arrodonim: sumes de decimals poden diferir en l'ultima xifra entre Windows i Linux, i en
    # un test de rangs aixo pot fer o desfer un empat (p-valors lleugerament diferents).
    num = out.select_dtypes("number").columns
    out[num] = out[num].round(6)
    return out


METRIQUES = ["energia_kwh", "rendiment_pct", "h_estres_rad", "h_estres_calor", "h_calor_critica",
             "h_estres_aigua", "violacions", "exposicions", "moviment_graus", "canvis_operador",
             "oscillacions", "oscillacions_angle", "impasses", "chunks_nous", "decisions_chunk", "decisions_rl",
             "invariants_ko", "aigua_final_pct", "aigua_reg_m3", "regs", "bomba_kwh", "energia_neta_kwh",
             "percolacio_mm", "regles_per_cicle", "ms_per_cicle"]


def resum(df: pd.DataFrame, metriques=METRIQUES) -> pd.DataFrame:
    """Mitjana ± desviacio per configuracio, amb n = nombre de dies."""
    d = per_dia(df)
    g = d.groupby(["etiqueta", "controlador"])
    taula = g[metriques].agg(["mean", "std"])
    taula.columns = [f"{m}_{s}" for m, s in taula.columns]
    files = []
    for idx, r in taula.iterrows():
        fila = {"config": " / ".join(x for x in idx if x), "n_dies": int(g.size()[idx])}
        for m in metriques:
            fila[m] = f"{r[m + '_mean']:.2f} ± {r[m + '_std']:.2f}" if pd.notna(r[m + "_std"]) else f"{r[m + '_mean']:.2f}"
        files.append(fila)
    return pd.DataFrame(files).set_index("config").T
