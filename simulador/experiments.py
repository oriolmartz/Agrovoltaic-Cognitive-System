"""Experiments (vegeu README, seccio "Experiments").

Cada experiment = una llista de configuracions x una llista de dies x llavors.
Disseny aparellat: totes les configuracions veuen exactament els mateixos dies i
la mateixa llavor (mateix soroll, mateixes fallades), aixi la diferencia nomes ve
del controlador.

    python experiments.py E7 --dies 48
    python experiments.py E4
    python experiments.py llista
"""

from __future__ import annotations

import argparse
import json
import os
import time

import pandas as pd

import dades
import estadistica as st
import paralel
import metriques as M
import simulador as S

ARREL = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(ARREL, "resultats")
PROCESSOS = [None]   # --processos
TRACA = [False]
NOM_EXP = [""]      # --traca: desa la traca del CLIPS (com run_soar) a resultats/<E>/traca/


def carpeta(nom: str) -> str:
    """resultats/E7/ per a 'E7_referencies', resultats/E12/ per a 'E12_model'..."""
    d = os.path.join(RES, nom.split("_")[0])
    os.makedirs(d, exist_ok=True)
    return d


def _amb_traca(cfg: dict, nom_exp: str) -> dict:
    if TRACA[0]:
        cfg = {**cfg, "traca_dir": os.path.join(carpeta(nom_exp), "traca")}
    return cfg


# ============================================================================ execucio en paral·lel

def _treball(arg):
    nom, cfg, dies, llavor = arg
    sim = S.Simulacio(cfg, llavor)
    return sim.executa(dies, etiqueta=nom)


def executa(configs: dict[str, dict], dies: list[str], llavors=(0,), processos=None,
            experiment: str = "") -> pd.DataFrame:
    """configs: nom -> escenari (dict que es fusiona amb config.json). Dies independents."""
    feines = []
    for nom, esc in configs.items():
        cfg = _amb_traca(S.carrega_config(esc), experiment)
        for ll in llavors:
            # un dia per feina: es reparteix be entre processos
            feines += [(nom, cfg, [d], ll) for d in dies]
    dfs = paralel.mapa(_treball, feines, processos or PROCESSOS[0], titol="simulant dies")
    return pd.concat(dfs, ignore_index=True)


def analitza(df: pd.DataFrame, metriques: list[str], nom: str) -> dict:
    pd_dia = M.per_dia(df)
    pd_dia["config"] = pd_dia["etiqueta"]
    res = [st.compara_multiples(pd_dia, m) for m in metriques]
    taula = st.taula_parelles(res)
    resum = M.resum(df)
    os.makedirs(RES, exist_ok=True)
    df.to_csv(os.path.join(carpeta(nom), f"{nom}_horari.csv"), index=False)
    pd_dia.to_csv(os.path.join(carpeta(nom), f"{nom}_per_dia.csv"), index=False)
    taula.to_csv(os.path.join(carpeta(nom), f"{nom}_tests.csv"), index=False)
    resum.to_csv(os.path.join(carpeta(nom), f"{nom}_resum.csv"))
    return {"resum": resum, "tests": taula, "per_dia": pd_dia}


def _mostra(r: dict):
    pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 40)
    print(r["resum"].to_string())
    if len(r["tests"]):
        print()
        print(r["tests"].to_string(index=False) if r["tests"].index.name is None else r["tests"].to_string())


# ============================================================================ experiments

BASE = {"controlador": {"tipus": "soar"}}
CONTROLADORS_REF = {"soar": {"controlador": {"tipus": "soar"}},
                    "seguidor": {"controlador": {"tipus": "seguidor"}},
                    "fix": {"controlador": {"tipus": "fix"}}}


def E4(n_dies=None, llavors=(0,)):
    """Seguretat amb vent real: tots els dies de Cantallops (tramuntana). SOAR vs seguidor."""
    cfg = S.carrega_config({"lloc": "cantallops"})
    dies = S.selecciona_dies(cfg, n_dies)
    configs = {k: {"lloc": "cantallops", **v} for k, v in CONTROLADORS_REF.items() if k != "fix"}
    df = executa(configs, dies, llavors, experiment=NOM_EXP[0])
    r = analitza(df, ["violacions", "exposicions", "energia_kwh", "moviment_graus"], "E4_vent_real")
    files = []
    for nom, g in df.groupby("etiqueta"):
        perill = g[g["vent_real"] >= 16]
        v = int(g["violacio_seguretat"].sum())
        files.append({"config": nom, "cicles_sector": len(g), "cicles_amb_ratxa>=16": len(perill),
                      "violacions": v,
                      "taxa_violacio_en_perill": v / max(1, len(perill)),
                      "cota_sup_95%": st.cota_superior_taxa(v, len(perill)),
                      "invariants_ko": int((g["invariants_ko"].fillna("") != "").sum())})
    r["seguretat"] = pd.DataFrame(files)
    r["seguretat"].to_csv(os.path.join(carpeta("E4"), "E4_vent_real_seguretat.csv"), index=False)
    return r


def E5(n_dies=40, llavors=(0, 1, 2)):
    """Sensor de vent que falla amb probabilitat 0 %, 5 % i 20 %, dies de vent de Cantallops."""
    cfg = S.carrega_config({"lloc": "cantallops"})
    dies = S.selecciona_dies(cfg, n_dies, filtre=lambda g: g["vent"].max() >= 12)
    configs = {}
    for p in (0.0, 0.05, 0.20):
        for ct in ("soar", "seguidor"):
            configs[f"{ct}_p{int(100 * p)}"] = {"lloc": "cantallops", "controlador": {"tipus": ct},
                                                "sensors": {"p_absent": {"vent": p}}}
    df = executa(configs, dies, llavors, experiment=NOM_EXP[0])
    return analitza(df, ["violacions", "exposicions", "energia_kwh", "impasses"], "E5_sensor_vent")


def E6(n_dies=40, llavors=(0, 1, 2)):
    """Fallades d'actuador aleatories (p = 5 % per panell i cicle). Detecta i reacciona?"""
    cfg = S.carrega_config({})
    dies = S.selecciona_dies(cfg, n_dies, llavor=6)
    configs = {"soar_sense_fallades": {}, "soar_fallades_5": {"actuadors": {"p_fallada": 0.05}}}
    df = executa(configs, dies, llavors, experiment=NOM_EXP[0])
    return analitza(df, ["energia_kwh", "violacions", "invariants_ko", "canvis_operador"], "E6_actuadors")


def E7(n_dies=48, llavors=(0,)):
    """SOAR vs controladors de referencia en dies reals de Ribera de Sio (abril-setembre)."""
    cfg = S.carrega_config({})
    dies = S.selecciona_dies(cfg, n_dies, llavor=7)
    df = executa(CONTROLADORS_REF, dies, llavors, experiment=NOM_EXP[0])
    return analitza(df, ["energia_kwh", "h_estres_rad", "h_estres_calor", "h_calor_critica",
                         "moviment_graus", "exposicions"], "E7_referencies")


# ============================================================================ sensibilitat

def _sector_gcr(g):
    return {"sectors": {s: {"gcr": g} for s in ("Sector_1", "Sector_2", "Sector_3")}}


VARIACIONS_MODEL = {
    # parametre: (valors, com es posa a l'escenari). El valor del mig es el de config.json.
    "gcr": ([0.2, 0.4, 0.6], _sector_gcr),
    "k_rad": ([0.003, 0.006, 0.012], lambda v: {"model": {"k_rad": v}}),
    "k_sec": ([1.0, 2.0, 4.0], lambda v: {"model": {"k_sec": v}}),
}
VARIACIONS_PREVISIO = {
    "previsio_vent_sigma": ([0.15, 0.4, 0.8], lambda v: {"soroll": {"previsio_vent_sigma": v}}),
    "p_previsio_absent": ([0.0, 0.2, 0.5], lambda v: {"sensors": {"p_previsio_absent": v}}),
}


def _sensibilitat(variacions, lloc, metriques, n_dies, llavors, nom, filtre=None):
    """Un parametre cada cop (OAT). Per a cada valor, SOAR i el seguidor comercial veuen els
    mateixos dies i llavors; es compara la diferencia SOAR - seguidor. Si el signe i la
    significacio no canvien en tot el rang, la conclusio d'E7/E4 es robusta a aquell parametre."""
    cfg = S.carrega_config({"lloc": lloc})
    dies = S.selecciona_dies(cfg, n_dies, llavor=12, filtre=filtre)
    configs = {}
    for par, (valors, f) in variacions.items():
        for v in valors:
            for ct in ("soar", "seguidor"):
                configs[f"{par}={v}|{ct}"] = S._fusiona({"lloc": lloc, "controlador": {"tipus": ct}}, f(v))
    df = executa(configs, dies, llavors, experiment=NOM_EXP[0])
    pd_dia = M.per_dia(df)
    pd_dia["variacio"] = pd_dia["etiqueta"].str.split("|").str[0]
    pd_dia["ctrl"] = pd_dia["etiqueta"].str.split("|").str[1]
    files = []
    for var, g in pd_dia.groupby("variacio", sort=False):
        par, val = var.split("=")
        ample = g.pivot_table(index=["dia", "llavor"], columns="ctrl", values=metriques)
        for m in metriques:
            a, b = ample[(m, "soar")], ample[(m, "seguidor")]
            r = st.compara_aparellat(a, b, "soar", "seguidor", m)
            files.append({"parametre": par, "valor": float(val), "metrica": m, "n": r["n"],
                          "soar": round(r["mitjana_A"], 2), "seguidor": round(r["mitjana_B"], 2),
                          "soar-seguidor": round(r["dif_mitjana"], 2), "IC95": r["IC95_dif"],
                          "p": r["p_wilcoxon"], "efecte": round(r["efecte_rb"], 2)})
    t = pd.DataFrame(files)
    # Holm dins de cada metrica (tantes comparacions com valors x parametres)
    t["p (Holm)"] = 1.0
    for m, g in t.groupby("metrica"):
        t.loc[g.index, "p (Holm)"] = st.holm(g["p"].tolist())
    t["p (Holm)"] = t["p (Holm)"].map(lambda x: f"{x:.2g}")
    t = t.drop(columns="p")
    # robustesa: el signe de la diferencia es el mateix per a tots els valors d'un parametre?
    rob = (t.groupby(["parametre", "metrica"])["soar-seguidor"]
           .agg(lambda x: "sí" if (x > 0).all() or (x < 0).all() or (x == 0).all() else "NO").rename("signe_estable")
           .reset_index())
    os.makedirs(RES, exist_ok=True)
    t.to_csv(os.path.join(carpeta(nom), f"{nom}.csv"), index=False)
    rob.to_csv(os.path.join(carpeta(nom), f"{nom}_robustesa.csv"), index=False)
    return {"resum": t.set_index(["parametre", "valor", "metrica"]), "tests": rob}


def E12(n_dies=30, llavors=(0,)):
    """Sensibilitat (un parametre cada cop): constants del model a Ribera de Sio i qualitat
    de la previsio de vent a Cantallops. Comprova si les conclusions d'E7 i E4 aguanten."""
    a = _sensibilitat(VARIACIONS_MODEL, "ribera", ["energia_kwh", "h_estres_rad", "h_estres_calor"],
                      n_dies, llavors, "E12_model")
    b = _sensibilitat(VARIACIONS_PREVISIO, "cantallops", ["violacions", "exposicions", "energia_kwh"],
                      n_dies, llavors, "E12_previsio", filtre=lambda g: g["vent"].max() >= 12)
    return {"resum": pd.concat([a["resum"], b["resum"]]), "tests": pd.concat([a["tests"], b["tests"]])}


# ============================================================================ E10: interaccions (reforç)

ESTATS_E10 = [("mitja", "mitja"), ("mitja", "alt"), ("alt", "mitja"), ("alt", "alt")]   # (calor, radiacio)
TASQUES_E10 = {
    # quan convé fer ombra (si no, convé produir). AND es linealment separable; XOR no.
    "AND": lambda t, r: t == "alt" and r == "alt",
    "XOR": lambda t, r: (t == "alt") != (r == "alt"),
}


def _e10_una(arg):
    """Entrena la funcio Q del CLIPS (REFORC) amb mostres sintetiques i mesura si la politica
    voraç (escollir l'operador amb mes Q) es la correcta als 4 estats."""
    clp, parelles, tasca, n_mostres, llavor = arg
    import numpy as np
    from clips_bridge import ControladorCLIPS
    rng = np.random.default_rng(llavor)
    c = ControladorCLIPS(os.path.join(ARREL, clp), reforc=True, parelles=parelles, chunking=False, epmem=False)
    e = c.env
    bona = TASQUES_E10[tasca]

    def posa_estat(k, t, r):
        e.assert_string(f"(risc (sector Sector_1) (cicle {k}) (tipus temperatura) (nivell {t}) (font e10))")
        e.assert_string(f"(risc (sector Sector_1) (cicle {k}) (tipus exces-radiacio) (nivell {r}) (font e10))")
        e.assert_string(f"(energia (sector Sector_1) (cicle {k}) (produccio-actual 10.0) (demanda 12.0))")

    corba = []
    punts = sorted({n for n in (10, 25, 50, 100, 200, 400) if n <= n_mostres} | {n_mostres})
    for i in range(1, n_mostres + 1):
        k = 1000 + i
        t, r = ESTATS_E10[rng.integers(4)]
        posa_estat(k, t, r)
        op = "orientar-ombra" if rng.random() < 0.5 else "orientar-produccio"   # exploracio uniforme
        recompensa = 1.0 if (op == "orientar-ombra") == bona(t, r) else -1.0
        e.eval(f"(REFORC::rl-actualitza (REFORC::rl-trets Sector_1 {op} {k}) {op} {recompensa})")
        e.eval(f"(PYTHON::py-neteja {k})")
        if i in punts:
            encerts = 0
            for j, (t2, r2) in enumerate(ESTATS_E10):
                kk = 900000 + i * 10 + j
                posa_estat(kk, t2, r2)
                qo = float(e.eval(f"(REFORC::rl-valor-op Sector_1 orientar-ombra {kk})"))
                qp = float(e.eval(f"(REFORC::rl-valor-op Sector_1 orientar-produccio {kk})"))
                encerts += int((qo > qp) == bona(t2, r2))
            e.eval(f"(PYTHON::py-neteja {900000 + i * 10 + 9})")
            corba.append({"mostres": i, "encert_pct": 100 * encerts / 4})
    del c
    return [{"llavor": llavor, "tasca": tasca, **x} for x in corba]


def E10(n_execucions=30, n_mostres=400):
    """Pot la funcio Q del reforç aprendre interaccions entre trets? Test de capacitat (caixa
    blanca) sobre les funcions REFORC del CLIPS amb una tasca AND i una XOR."""
    configs = {"v1_6 (trets sols)": ("../history/clips/simulator/soar_v1_6.clp", None),
               "v1_8 parelles off": ("../history/clips/simulator/soar_v1_8.clp", False),
               "v1_8 parelles on": ("../history/clips/simulator/soar_v1_8.clp", True)}
    feines, noms = [], []
    for nom, (clp, par) in configs.items():
        for tasca in TASQUES_E10:
            for ll in range(n_execucions):
                feines.append((clp, par, tasca, n_mostres, ll))
                noms.append(nom)
    res = paralel.mapa(_e10_una, feines, PROCESSOS[0], titol="E10 reforç")
    df = pd.DataFrame([{**x, "config": nom} for nom, xs in zip(noms, res) for x in xs])
    d = carpeta("E10")
    df.to_csv(os.path.join(d, "E10_corbes.csv"), index=False)
    corbes = df.groupby(["tasca", "config", "mostres"])["encert_pct"].agg(["mean", "std"]).round(1).unstack("mostres")
    corbes.to_csv(os.path.join(d, "E10_corbes_resum.csv"))
    final = df[df["mostres"] == n_mostres]
    tests = []
    for tasca, g in final.groupby("tasca"):
        g = g.rename(columns={"llavor": "dia"}).assign(llavor=0)
        r = st.compara_multiples(g, "encert_pct", col_config="config")
        tests.append(r)
    taula = st.taula_parelles(tests)
    taula.insert(0, "tasca", [t for t, g in final.groupby("tasca") for _ in range(3)])
    taula.to_csv(os.path.join(d, "E10_tests.csv"), index=False)
    return {"resum": corbes, "tests": taula}


# ============================================================================ E14: escenaris extrems

def E14(n_dies=20, llavors=(0, 1, 2)):
    """Escenaris adversos (estres del sistema): onada de calor, sequera sense reg i temporal
    de vent. SOAR contra el seguidor comercial i el panell fix, aparellat per dia i llavor."""
    met_r = dades.carrega("ribera")
    met_c = dades.carrega("cantallops")
    tmax = met_r.groupby(met_r.index.date)["temp"].max()
    calents = sorted(str(d) for d in tmax.sort_values(ascending=False).index[:n_dies])
    vmax = met_c.groupby(met_c.index.date)["vent"].max()
    ventosos = sorted(str(d) for d in vmax.sort_values(ascending=False).index[:n_dies])
    secs = S.selecciona_dies({**S.carrega_config({}), "dies": {"des_de": "2023-07-01", "fins_a": "2023-08-31"}},
                             n_dies, llavor=14)
    escenaris = {
        # els 20 dies mes calorosos de Ribera de Sio (Tmax 36-42 °C) i encara +3 °C
        "calor": ({"lloc": "ribera", "modificadors": {"temp_delta": 3.0}}, calents,
                  ["h_estres_calor", "h_calor_critica", "h_estres_rad", "energia_kwh"]),
        # juliol-agost sense reg: l'ombra hauria de reduir l'evapotranspiracio i deixar mes aigua al sol
        "sequera": ({"lloc": "ribera", "humitat": {"inicial_pct": 75.0, "reg": {"actiu": False}}}, secs,
                    ["aigua_final_pct", "h_estres_aigua", "energia_kwh"]),
        # els 20 dies amb mes vent de Cantallops, amb les ratxes un 30 % mes fortes
        "vent": ({"lloc": "cantallops", "modificadors": {"vent_factor": 1.3}}, ventosos,
                 ["violacions", "exposicions", "energia_kwh"]),
    }
    resums, tests = [], []
    for nom, (esc, dies, mets) in escenaris.items():
        configs = {f"{nom}|{ct}": S._fusiona(esc, {"controlador": {"tipus": ct}}) for ct in ("soar", "seguidor", "fix")}
        df = executa(configs, dies, llavors, experiment="E14")
        pd_dia = M.per_dia(df)
        pd_dia["config"] = pd_dia["etiqueta"].str.split("|").str[1]
        r = [st.compara_multiples(pd_dia, m) for m in mets]
        t = st.taula_parelles(r)
        t.insert(0, "escenari", nom)
        tests.append(t)
        res = M.resum(df)
        res.columns = [c.split("|")[1].split(" / ")[0] for c in res.columns]
        res.insert(0, "escenari", nom)
        resums.append(res.loc[["n_dies"] + mets])
        df.to_csv(os.path.join(carpeta("E14"), f"E14_{nom}_horari.csv"), index=False)
        pd_dia.to_csv(os.path.join(carpeta("E14"), f"E14_{nom}_per_dia.csv"), index=False)
    resum = pd.concat(resums)
    taula = pd.concat(tests, ignore_index=True)
    resum.to_csv(os.path.join(carpeta("E14"), "E14_resum.csv"))
    taula.to_csv(os.path.join(carpeta("E14"), "E14_tests.csv"), index=False)
    return {"resum": resum, "tests": taula}


# ============================================================================ E11: agenda

def _variants_salience() -> dict[str, str]:
    """Copies del .clp per defecte amb la salience canviada (nomes a resultats/E11/variants/,
    el codi de l'equip no es toca)."""
    import re
    base = S.carrega_config({})["clp"]
    txt = open(os.path.join(ARREL, base), encoding="utf-8").read()
    d = os.path.join(carpeta("E11"), "variants")
    os.makedirs(d, exist_ok=True)
    variants = {
        # les 10 regles de canvi de fase passen de -10 a 0: competeixen amb les de la fase
        "transicions_salience_0": txt.replace("(salience -10)", "(salience 0)"),
        # cap salience: tot depen de l'estrategia de l'agenda
        "sense_salience": re.sub(r"\(salience -?\d+\)\s*", "", txt),
    }
    out = {}
    for nom, t in variants.items():
        p = os.path.join(d, f"{nom}.clp")
        with open(p, "w", encoding="utf-8") as f:
            f.write(t)
        out[nom] = p
    return out


def E11(n_dies=20, llavors_random=5):
    """Agenda de CLIPS: (1) estrategies de resolucio de conflictes (depth, breadth, lex, mea,
    i simplicity/complexity, que ordenen per especificitat), (2) random amb llavors i (3) variants
    amb la salience canviada. La decisio no hauria de dependre de l'ordre de disparament."""
    configs = {e: {"controlador": {"estrategia": e}} for e in
               ("depth", "breadth", "lex", "mea", "simplicity", "complexity")}
    for k in range(llavors_random):
        configs[f"random_{k}"] = {"controlador": {"estrategia": "random", "llavor_clips": k}}
    for nom, p in _variants_salience().items():
        for e in ("depth", "breadth"):
            configs[f"{nom}_{e}"] = {"clp": p, "controlador": {"estrategia": e}}
    cfg = S.carrega_config({})
    dies = S.selecciona_dies(cfg, n_dies, llavor=11)
    df = executa(configs, dies, (0,), experiment=NOM_EXP[0])
    clau = ["dia", "hora", "sector"]
    ref = df[df["etiqueta"] == "depth"].set_index(clau)[["accio", "angle_ordre"]]
    files = []
    for nom, g in df.groupby("etiqueta", sort=False):
        g = g.set_index(clau)
        j = g[["accio", "angle_ordre"]].join(ref.add_suffix("_depth"))
        dif = (j["accio"] != j["accio_depth"]) | ((j["angle_ordre"] - j["angle_ordre_depth"]).abs() > 1e-6)
        files.append({"estrategia": nom, "decisions": len(j), "diferents_de_depth": int(dif.sum()),
                      "pct_diferents": round(100 * dif.mean(), 2),
                      "invariants_ko": int((g["invariants_ko"].fillna("") != "").sum()),
                      "energia_kwh_dia": round(g.groupby("dia")["P_kw"].sum().mean(), 2)})
    t = pd.DataFrame(files)
    d = carpeta("E11")
    t.to_csv(os.path.join(d, "E11_concordanca.csv"), index=False)
    df.to_csv(os.path.join(d, "E11_horari.csv"), index=False)
    # quines decisions canvien (per anar a mirar la traca)
    ex = []
    for nom, g in df[df["etiqueta"] != "depth"].groupby("etiqueta"):
        j = g.set_index(clau)[["accio", "motiu"]].join(ref[["accio"]].add_suffix("_depth"))
        ex.append(j[j["accio"] != j["accio_depth"]].reset_index().assign(estrategia=nom))
    if ex:
        pd.concat(ex).to_csv(os.path.join(d, "E11_decisions_diferents.csv"), index=False)
    return {"resum": t.set_index("estrategia"), "tests": pd.DataFrame()}


# ============================================================================ E13: coneixement après

def _comprova_foto(f: dict) -> dict:
    """Restriccions d'integritat sobre una foto del coneixement apres (a l'estil de Rashid 2019)."""
    chunks = f.get("chunks", [])
    regles = set(f.get("regles_chunk", []))
    noms = [c["nom"] for c in chunks]
    sigs = [c["signatura"] for c in chunks]
    lhs = {}
    conflictes = 0
    for c in chunks:
        esq, _, dre = c["signatura"].partition(" =>")
        if esq in lhs and lhs[esq] != dre:
            conflictes += 1
        lhs.setdefault(esq, dre)
    q = f.get("rl", [])
    claus = [(x["tret"], x["op"]) for x in q]
    return {
        "chunks": len(chunks), "rajoles_q": len(q), "episodis": f.get("n_epmem", 0),
        "K1_fet_sense_regla": sum(1 for n in noms if n not in regles),
        "K2_regla_sense_fet": sum(1 for r in regles if r not in set(noms)),
        "K3_signatures_duplicades": len(sigs) - len(set(sigs)),
        "K4_mateixa_condicio_accio_diferent": conflictes,
        "K5_rajola_q_duplicada": len(claus) - len(set(claus)),
        "K6_q_fora_de_rang": sum(1 for x in q if abs(x["q"]) > 2.0),
        "q_max_abs": round(max((abs(x["q"]) for x in q), default=0.0), 3),
    }


def _treball_e13(arg):
    cfg, dies, llavor = arg
    sim = S.Simulacio(cfg, llavor)
    df = sim.executa(dies, etiqueta="E13")
    files = []
    prev = None
    for f in sim.fotos:
        r = {"execucio": llavor, "dia": f["dia"], "cicle": f["cicle"], **_comprova_foto(f)}
        # completesa: un episodi per sector i cicle; el coneixement no es perd d'un dia a l'altre
        r["K7_episodis_esperats"] = 3 * (f["cicle"] - 1)
        r["K7_falten_episodis"] = r["K7_episodis_esperats"] - r["episodis"]
        r["K8_chunks_perduts"] = max(0, (prev["chunks"] if prev else 0) - r["chunks"])
        r["K8_rajoles_perdudes"] = max(0, (prev["rajoles_q"] if prev else 0) - r["rajoles_q"])
        files.append(r)
        prev = r
    return files


def E13(n_execucions=5, n_dies=20):
    """Consistencia i completesa del coneixement que el sistema apren mentre funciona
    (chunks, valors del reforç, memoria episodica), comprovades al final de cada dia."""
    base = S.carrega_config({"mode_dies": "sequencial", "sensors": {"p_absent": {"vent": 0.05}}})
    feines = []
    import numpy as np
    pool_dies = S.selecciona_dies(base)
    for e in range(n_execucions):
        dies = sorted(np.random.default_rng(500 + e).choice(pool_dies, n_dies, replace=False).tolist())
        feines.append((_amb_traca(base, "E13"), dies, e))
    res = paralel.mapa(_treball_e13, feines, PROCESSOS[0], titol="E13 execucions", cada=1)
    t = pd.DataFrame([x for xs in res for x in xs])
    d = carpeta("E13")
    t.to_csv(os.path.join(d, "E13_fotos.csv"), index=False)
    ks = [c for c in t.columns if c.startswith("K") and c != "K7_episodis_esperats"]
    resum = pd.DataFrame({"comprovacio": ks, "fotos": len(t), "fotos_amb_problema": [int((t[k] > 0).sum()) for k in ks],
                          "total": [int(t[k].sum()) for k in ks]})
    resum.to_csv(os.path.join(d, "E13_resum.csv"), index=False)
    creix = t.groupby("execucio").last()[["cicle", "chunks", "rajoles_q", "episodis", "q_max_abs"]]
    return {"resum": resum.set_index("comprovacio"), "tests": creix}


# ============================================================================ aprenentatge

def _treball_seq(arg):
    nom, cfg, dies_ent, dies_prova, llavor = arg
    sim = S.Simulacio(cfg, llavor)
    df = sim.executa(dies_ent + dies_prova, etiqueta=nom)
    df["fase_exp"] = df["dia"].map(lambda d: "entrenament" if d in set(dies_ent) else "prova")
    df["execucio"] = llavor
    fotos = [{"config": nom, "execucio": llavor, "dia": f["dia"], "cicle": f["cicle"],
              "n_chunks": len(f.get("chunks", [])), "n_rajoles": len(f.get("rl", [])),
              "n_epmem": f.get("n_epmem", 0)} for f in sim.fotos]
    return df, fotos


def aprenentatge(configs: dict[str, dict], n_execucions=10, n_ent=20, n_prova=10, nom="E9",
                 processos=None):
    """Validesa externa (Menzies & Pecheur): s'apren en uns dies i es mesura en uns ALTRES.
    Entrenament: dies d'abril a juny en ordre aleatori (diferent a cada execucio).
    Prova: dies de juliol a setembre (els mateixos per a totes les configuracions)."""
    base = S.carrega_config({})
    ent_pool = S.selecciona_dies({**base, "dies": {"des_de": "2023-04-01", "fins_a": "2023-06-30"}})
    prova = S.selecciona_dies({**base, "dies": {"des_de": "2023-07-01", "fins_a": "2023-09-30"}}, n_prova, llavor=99)
    import numpy as np
    feines = []
    for e in range(n_execucions):
        rng = np.random.default_rng(1000 + e)
        ent = rng.choice(ent_pool, size=n_ent, replace=False).tolist()   # ordre aleatori
        for k, esc in configs.items():
            cfg = _amb_traca(S.carrega_config({**esc, "mode_dies": "sequencial"}), nom)
            feines.append((k, cfg, ent, prova, e))
    sortides = paralel.mapa(_treball_seq, feines, processos or PROCESSOS[0], titol="execucions d'aprenentatge", cada=1)
    df = pd.concat([d for d, _ in sortides], ignore_index=True)
    fotos = pd.DataFrame([f for _, fs in sortides for f in fs])
    os.makedirs(RES, exist_ok=True)
    fotos.to_csv(os.path.join(carpeta(nom), f"{nom}_coneixement.csv"), index=False)
    # analisi nomes sobre els dies de prova; bloc = (dia de prova, execucio)
    prova_df = df[df["fase_exp"] == "prova"].copy()
    prova_df["llavor"] = prova_df["execucio"]
    r = analitza(prova_df, ["energia_kwh", "h_estres_rad", "h_estres_calor", "impasses",
                            "decisions_chunk", "decisions_rl", "ms_per_cicle"], nom)
    df.to_csv(os.path.join(carpeta(nom), f"{nom}_horari_complet.csv"), index=False)
    r["coneixement"] = fotos
    return r


def E8(n_execucions=10):
    """Chunking: amb i sense (v1_7, reforç apagat). Impasses, us dels chunks i cost per cicle."""
    return aprenentatge({"amb_chunking": {"controlador": {"chunking": True, "reforc": False}},
                         "sense_chunking": {"controlador": {"chunking": False, "reforc": False}}},
                        n_execucions, nom="E8_chunking")


def E9(n_execucions=10):
    """Reforç: v1_5 (sense), v1_6 (rajoles soles) i v1_7 (amb parelles), mateixos dies."""
    return aprenentatge({"v1_5": {"clp": "../history/clips/simulator/soar_v1_5.clp"},
                         "v1_6": {"clp": "../history/clips/simulator/soar_v1_6.clp", "controlador": {"reforc": True}},
                         "v1_7": {"clp": "../history/clips/simulator/soar_v1_7.clp", "controlador": {"reforc": True, "parelles": True}}},
                        n_execucions, nom="E9_reforc")


EXPERIMENTS = {"E4": E4, "E5": E5, "E6": E6, "E7": E7, "E8": E8, "E9": E9, "E10": E10, "E11": E11,
               "E12": E12, "E13": E13, "E14": E14}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("experiment", choices=list(EXPERIMENTS) + ["llista"])
    ap.add_argument("--dies", type=int, default=None, help="nombre de dies (a E8, E9, E10 i E13: d'execucions)")
    ap.add_argument("--llavors", type=int, default=None, help="nombre de llavors (0..n-1)")
    ap.add_argument("--processos", type=int, default=None, help="processos en paral·lel (per defecte, tots els nuclis)")
    ap.add_argument("--traca", action="store_true",
                    help="desa la traca del CLIPS de cada dia (com run_soar) a resultats/<E>/traca/")
    a = ap.parse_args()
    if a.experiment == "llista":
        for k, f in EXPERIMENTS.items():
            print(f"{k}: {f.__doc__.strip().splitlines()[0]}")
        return
    kw = {}
    if a.dies is not None:
        kw["n_dies" if a.experiment not in ("E8", "E9", "E10", "E13") else "n_execucions"] = a.dies
    if a.llavors is not None:
        kw["llavors"] = tuple(range(a.llavors))
    if a.processos:
        PROCESSOS[0] = a.processos
    TRACA[0] = a.traca
    NOM_EXP[0] = a.experiment
    t0 = time.time()
    r = EXPERIMENTS[a.experiment](**kw)
    _mostra(r)
    if "seguretat" in r:
        print()
        print(r["seguretat"].to_string(index=False))
    print(f"\n[{a.experiment}] {time.time() - t0:.0f} s. Resultats a {os.path.join(RES, a.experiment)}")


if __name__ == "__main__":
    main()
