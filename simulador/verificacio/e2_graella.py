"""E2 - Verificacio exhaustiva sobre una graella d'entrades discretitzades.

Per a cada combinacio d'entrades (vent observat, previsio de vent, temperatura del
cultiu, humitat, radiacio, angle inicial, panell avariat) s'executa UN cicle en un
entorn CLIPS net, amb l'aprenentatge apagat (chunking, reforç i memoria episodica),
i es comprova sobre els tres sectors alhora (tres cultius):

  Deficiencia (Preece): cada sector acaba amb exactament una ordre.
  Seguretat:   S1 vent observat >= vent-maxim            -> posicio-seguretat
               S2 sense vent observat i previsio >= maxim -> posicio-seguretat
               S3 sense vent observat i previsio >= avis  -> posicio-seguretat (requisit de disseny)
               S4 l'angle ordenat es dins dels limits mecanics
               S5 no es tria mai un operador rebutjat
  Conflicte (Preece): dues preferencies 'requerida' per a operadors diferents.
  Monotonia (test metamorfic): si amb vent v es va a seguretat, amb vent v' > v
               (la resta igual) tambe.
  Cobertura:   regles disparades almenys un cop / regles de la base.

A partir de v1_9 hi ha una segona graella per al REG (humitat x pluja prevista x hora x
deficit d'energia), amb aquestes propietats per sector:
  R1 exactament una ordre de reg               R2 la dosi no passa del que falta (FAO-56)
  R3 amb >= 10 mm previstos i sense estres critic, no es rega
  R4 sense lectura d'humitat, no es rega       R5 sense necessitat (< 75 % de p), no es rega
  R6 amb estres hidric i menys de 10 mm previstos, es rega sempre
  R7 la vinya no s'anticipa (sense estres no es rega)
  Monotonia: amb menys aigua al sol (la resta igual), la dosi no baixa.

    python verificacio/e2_graella.py [--clp ../history/clips/simulator/soar_v1_7.clp] [--rapid]
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import time

import pandas as pd

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)
from clips_bridge import SECTORS, SENSORS, ControladorCLIPS  # noqa: E402
import paralel  # noqa: E402

GRAELLA = {
    "vent": [None, 0.0, 11.9, 12.0, 15.9, 16.0, 25.0],
    "previsio_vent": [None, 5.0, 12.0, 16.0, 25.0],
    "temp_cultiu": [None, 10.0, 22.0, 29.0, 33.0, 37.0, 42.0],
    "humitat": [None, 95.0, 65.0, 45.0, 20.0],
    "radiacio": [None, 100.0, 300.0, 500.0, 800.0],
    "angle_inicial": [0.0, 30.0],
    "avariat": [False, True],
}
GRAELLA_RAPIDA = {**GRAELLA, "temp_cultiu": [None, 22.0, 37.0], "humitat": [None, 95.0, 20.0],
                  "radiacio": [None, 100.0, 800.0], "angle_inicial": [30.0]}
GRAELLA_REG = {
    "humitat": [None, 100.0, 90.0, 80.0, 75.0, 70.0, 66.0, 65.0, 60.0, 55.0, 50.0, 40.0, 30.0, 20.0, 10.0],
    "pluja_prevista": [None, 0.0, 1.9, 2.0, 5.0, 9.9, 10.0, 30.0],
    "hora": [7, 8, 9, 13, 18, 19, 20],
    "deficit_energia": [False, True],
}
P_CULTIU = {"Sector_1": 0.40, "Sector_2": 0.30, "Sector_3": 0.45}   # FAO-56 (com al .clp)
ANGLE_OPTIM = 30.0
CLP = None


def _un_cas(cas: dict) -> list[dict]:
    c = ControladorCLIPS(CLP, reforc=False, chunking=False, epmem=False, vigila_regles=True)
    pan = c.panells()
    for pid in pan:
        extra = {"disponible": "no", "estat-mecanic": "avariat"} if cas["avariat"] else {}
        c.escriu_panell(pid, angle=cas["angle_inicial"], **{"angle-optim-produccio": ANGLE_OPTIM}, **extra)
    obs = {"radiacio": cas["radiacio"], "temperatura-aire": 20.0, "temperatura-cultiu": cas["temp_cultiu"],
           "humitat-sol": cas["humitat"], "vent": cas["vent"], "pluja": 0.0}
    pred = {"radiacio": 300.0, "temperatura": 22.0, "vent": cas["previsio_vent"], "pluja": 0.0}
    for s in SECTORS:
        for tp in SENSORS:
            ok = obs.get(tp, 0.0) is not None
            c.escriu_sensor(s, tp, operatiu=True, qualitat="valida" if ok else "absent", c=1)
        c.afegeix_entrades(1, s, obs, pred, {"produccio": 10.0, "demanda": 12.0})
    r = c.executa_cicle()
    p0 = next(iter(pan.values()))
    files = []
    for s in SECTORS:
        ordres = r.ordres.get(s, [])
        acc, ang = (ordres[0] if ordres else (None, None))
        ko = []
        if len(ordres) != 1 or len(r.seleccionat.get(s, [])) != 1:
            ko.append("D-deficiencia")
        v, pv = cas["vent"], cas["previsio_vent"]
        if v is not None and v >= p0["vent-maxim"] and acc != "posicio-seguretat":
            ko.append("S1-vent-observat")
        if v is None and pv is not None and pv >= p0["vent-maxim"] and acc != "posicio-seguretat":
            ko.append("S2-previsio-maxim")
        if v is None and pv is not None and pv >= p0["vent-avis"] and acc != "posicio-seguretat":
            ko.append("S3-previsio-avis")
        if ang is not None and not (p0["angle-minim"] <= ang <= p0["angle-maxim"]):
            ko.append("S4-limits")
        if acc in r.rebutjats.get(s, set()):
            ko.append("S5-rebutjat")
        req = {op for f, t, op in r.fonts_pref.get(s, set()) if t == "requerida"}
        if len(req) > 1:
            ko.append("C-conflicte-requerides")
        files.append({**cas, "sector": s, "accio": acc, "angle": ang,
                      "impas": ",".join(t for t, ss in r.impasses if ss == s),
                      "riscos": ";".join(f"{t}={n}" for t, n in sorted(r.riscos.get(s, []))),
                      "ko": ",".join(ko), "regles": "|".join(sorted(set(r.regles)))})
    del c
    return files


def _un_cas_reg(cas: dict) -> list[dict]:
    c = ControladorCLIPS(CLP, reforc=False, chunking=False, epmem=False, vigila_regles=True)
    for pid in c.panells():
        c.escriu_panell(pid, angle=30.0, **{"angle-optim-produccio": ANGLE_OPTIM})
    obs = {"radiacio": 300.0, "temperatura-aire": 20.0, "temperatura-cultiu": 20.0,
           "humitat-sol": cas["humitat"], "vent": 3.0, "pluja": 0.0}
    pred = {"radiacio": 300.0, "temperatura": 22.0, "vent": 3.0, "pluja": cas["pluja_prevista"]}
    ene = {"produccio": 10.0, "demanda": 12.0} if cas["deficit_energia"] else {"produccio": 14.0, "demanda": 12.0}
    for s in SECTORS:
        for tp in SENSORS:
            ok = obs.get(tp, 0.0) is not None
            c.escriu_sensor(s, tp, operatiu=True, qualitat="valida" if ok else "absent", c=1)
        c.afegeix_entrades(1, s, obs, pred, ene)
    c.escriu_moment(1, cas["hora"])
    r = c.executa_cicle()
    files = []
    h, pl = cas["humitat"], cas["pluja_prevista"]
    for s in SECTORS:
        regs = r.reg.get(s, [])
        acc, dosi = (regs[0][0], regs[0][1]) if regs else (None, None)
        ko = []
        if len(regs) != 1:
            ko.append("R1-una-ordre-reg")
        if len(r.ordres.get(s, [])) != 1:
            ko.append("D-deficiencia")
        p = P_CULTIU[s]
        if h is not None:
            e = 1 - h / 100
            tram = (1 - p) / 3
            critic = e > p + 2 * tram + 1e-9
            if dosi is not None and dosi > 100 - h + 1e-6:
                ko.append("R2-dosi-excessiva")
            if pl is not None and pl >= 10 and not critic and acc != "no-regar":
                ko.append("R3-pluja-prevista")
            if e < 0.75 * p - 1e-9 and acc != "no-regar":
                ko.append("R5-sense-necessitat")
            if e > p + 1e-9 and (pl is None or pl < 10) and acc == "no-regar":
                ko.append("R6-estres-sense-reg")
            if s == "Sector_3" and e <= p + 1e-9 and acc != "no-regar":
                ko.append("R7-vinya-anticipada")
        elif acc != "no-regar":
            ko.append("R4-sense-humitat")
        files.append({**cas, "sector": s, "reg": acc, "dosi": dosi, "ko": ",".join(ko),
                      "regles": "|".join(sorted(set(r.regles)))})
    del c
    return files


def monotonia_reg(df: pd.DataFrame) -> pd.DataFrame:
    """Casos on menys aigua al sol (resta igual) dona una dosi mes petita."""
    altres = [k for k in GRAELLA_REG if k != "humitat"] + ["sector"]
    num = df[df["humitat"].notna()].copy()
    dolents = []
    for _, g in num.groupby(altres, dropna=False):
        g = g.sort_values("humitat", ascending=False)
        d_ant = -1.0
        for _, r in g.iterrows():
            if r["dosi"] + 1e-9 < d_ant:
                dolents.append(r)
                break
            d_ant = r["dosi"]
    return pd.DataFrame(dolents)


def _init(clp):
    global CLP
    CLP = clp


def monotonia_vent(df: pd.DataFrame) -> pd.DataFrame:
    """Casos on mes vent (resta igual) deixa d'anar a seguretat."""
    altres = [k for k in GRAELLA if k != "vent"] + ["sector"]
    num = df[df["vent"].notna()].copy()
    dolents = []
    for _, g in num.groupby(altres, dropna=False):
        g = g.sort_values("vent")
        seg = False
        for _, r in g.iterrows():
            if r["accio"] == "posicio-seguretat":
                seg = True
            elif seg:
                dolents.append(r)
                break
    return pd.DataFrame(dolents)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clp", default=os.path.join(ARREL, "clips_core", "soar.clp"))
    ap.add_argument("--rapid", action="store_true", help="graella reduida (prova rapida)")
    ap.add_argument("--processos", type=int, default=os.cpu_count())
    a = ap.parse_args()
    graella = GRAELLA_RAPIDA if a.rapid else GRAELLA
    casos = [dict(zip(graella, vals)) for vals in itertools.product(*graella.values())]
    t0 = time.time()
    resultats = paralel.mapa(_un_cas, casos, a.processos, initializer=_init,
                             initargs=(os.path.abspath(a.clp),), titol="E2 graella")
    files = [f for fs in resultats for f in fs]
    df = pd.DataFrame(files)
    versio = os.path.splitext(os.path.basename(a.clp))[0]
    out = os.path.join(ARREL, "resultats", "E2", f"e2_graella_{versio}.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    df.to_csv(out, index=False)

    # regles de la base (sense chunks) i cobertura
    c = ControladorCLIPS(os.path.abspath(a.clp))
    totes = set()
    for m in ("MEMORIA", "DELIBERACIO", "REFORC", "DECISIO", "APRENENTATGE", "IMPAS", "ACCIO"):
        try:
            totes |= {f"{m}::{r}" if "::" not in str(r) else str(r) for r in c.env.eval(f"(get-defrule-list {m})")}
        except Exception:
            pass
    del c
    # v1_9: graella del reg
    resum_reg, df_reg = None, None
    if ControladorCLIPS(os.path.abspath(a.clp)).te_reg:
        casos_reg = [dict(zip(GRAELLA_REG, vals)) for vals in itertools.product(*GRAELLA_REG.values())]
        res_reg = paralel.mapa(_un_cas_reg, casos_reg, a.processos, initializer=_init,
                               initargs=(os.path.abspath(a.clp),), titol="E2 graella del reg")
        df_reg = pd.DataFrame([f for fs in res_reg for f in fs])
        df_reg.to_csv(os.path.join(ARREL, "resultats", "E2", f"e2_reg_{versio}.csv"), index=False)
        ko_r = df_reg[df_reg["ko"] != ""]
        mono_r = monotonia_reg(df_reg)
        resum_reg = {"casos": len(casos_reg), "decisions": len(df_reg),
                     "violacions_per_propietat": ko_r["ko"].str.split(",").explode().value_counts().to_dict(),
                     "violacions_monotonia_dosi": len(mono_r),
                     "decisions_per_accio": df_reg["reg"].value_counts(dropna=False).to_dict()}
        if len(ko_r):
            print("\nExemples de violacions (reg):\n", ko_r.drop(columns=["regles"]).drop_duplicates(subset=["ko", "sector"]).head(15).to_string())
        if len(mono_r):
            print("\nExemples de no-monotonia (reg):\n", mono_r.drop(columns=["regles"]).head(10).to_string())

    disparades = set()
    for x in list(df["regles"]) + (list(df_reg["regles"]) if df_reg is not None else []):
        disparades |= {r if "::" in r else r for r in x.split("|") if r}
    nom_curt = lambda r: r.split("::")[-1]
    disp_curt = {nom_curt(r) for r in disparades}
    no_disp = sorted(r for r in totes if nom_curt(r) not in disp_curt)

    ko = df[df["ko"] != ""]
    mono = monotonia_vent(df)
    resum = {
        "versio": versio, "casos": len(casos), "decisions": len(df), "segons": round(time.time() - t0, 1),
        "violacions_per_propietat": ko["ko"].str.split(",").explode().value_counts().to_dict(),
        "violacions_monotonia_vent": len(mono),
        "regles_total": len(totes), "regles_disparades": len(totes) - len(no_disp),
        "cobertura_regles_pct": round(100 * (len(totes) - len(no_disp)) / max(1, len(totes)), 1),
        "regles_no_disparades": no_disp,
        "decisions_per_accio": df["accio"].value_counts(dropna=False).to_dict(),
        "impasses": df["impas"].replace("", "cap").value_counts().to_dict(),
    }
    if resum_reg is not None:
        resum["reg"] = resum_reg
    json.dump(resum, open(os.path.join(ARREL, "resultats", "E2", f"e2_graella_{versio}.json"), "w"),
              indent=2, ensure_ascii=False, default=str)
    print(json.dumps(resum, indent=2, ensure_ascii=False, default=str))
    if len(ko):
        ex = ko.drop(columns=["regles"]).drop_duplicates(subset=["ko", "sector"]).head(15)
        print("\nExemples de violacions:\n", ex.to_string())
    if len(mono):
        print("\nExemples de no-monotonia:\n", mono.drop(columns=["regles"]).head(10).to_string())


if __name__ == "__main__":
    main()
