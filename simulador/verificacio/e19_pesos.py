"""E19 - Justificacio i sensibilitat dels numeros de la valoracio (pesos, nivells, estabilitat, requerida).

Els numeros que es van triar a ma son:
  pes-objectiu       seguretat 5, cultiu 3, energia 3, estabilitat 2, moviment 1 (estalvi d'aigua 1, reg)
  nivell-a-numero    baix 0, mitja 1, alt 2, critic 3
  estabilitat        +pes d'estabilitat (2) a l'operador del cicle anterior (AV8)
  puntuacio          requerida +1000, millor +100, pitjor -100

Tres parts:
  A. Analitica: per a cada parella d'operadors on un serveix un objectiu de mes prioritat, el marge
     minim de puntuacio en totes les situacions possibles (amb i sense la preferencia de memoria,
     que val com a molt +-pes-memoria). Diu quines desigualtats compleixen els numeros i quines no.
  B. Sensibilitat a la graella d'E2 (rapida, un cicle, sense memoria): cada variant del .clp contra
     la base. Concordanca de decisions i violacions de seguretat.
  C. Sensibilitat en dies reals (Ribera de Sio i dies de vent de Cantallops, amb memoria): concordanca
     de decisions, energia, estres, exposicio al vent, violacions, impasses i canvis d'operador.

Les variants es fan sobre una copia del soar.clp generat (com E17 i E18), a
resultats/E19/variants/<nom>/clips_core/soar.clp perque el pont hi injecti l'ontologia.

    python verificacio/e19_pesos.py [--dies N] [--processos P] [--nomes-analitica]
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import re
import sys

import pandas as pd

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paralel  # noqa: E402

DIR = os.path.join(ARREL, "resultats", "E19")
BASE = dict(seguretat=5, cultiu=3, energia=3, estabilitat=2, moviment=1)
NIVELLS = dict(baix=0, mitja=1, alt=2, critic=3)
REQUERIDA = 1000
PES_MEMORIA = 2.0

# --------------------------------------------------------------------------- A. analitica

OBJ = {"posicio-seguretat": 0, "orientar-ombra": 1, "orientar-produccio": 2, "mantenir-posicio": 2}
NOM_OBJ = {0: "seguretat", 1: "cultiu", 2: "energia"}


def puntuacions(w, L, vent, riscos, cob, optim, prev):
    """Puntuacio numerica de cada operador proposat, tal com la calculen les regles AV3-AV8."""
    # des de l'iteracio 30, orientar-produccio nomes es proposa si el panell no es a l'angle optim
    ops = {"mantenir-posicio": (w["energia"] * L[cob] if optim else 0) + w["moviment"]}
    if not optim:
        ops["orientar-produccio"] = w["energia"] * L[cob]
    if any(n != "baix" for n in riscos):
        ops["orientar-ombra"] = sum(w["cultiu"] * L[n] for n in riscos if n != "baix")
    if vent == "alt":
        ops["posicio-seguretat"] = w["seguretat"] * L["alt"]
    if prev in ops:
        ops[prev] += w["estabilitat"]
    return ops


def analitica(w=BASE, L=NIVELLS, pm=PES_MEMORIA):
    """Marge minim (mes prioritari - menys prioritari) en totes les situacions."""
    pitjor = {}
    niv = ["baix", "mitja", "alt", "critic"]
    for vent, t, r, h, cob, optim, prev in itertools.product(
            ["baix", "alt"], niv, niv, niv, ["alt", "mitja"], [False, True],
            [None, "orientar-produccio", "orientar-ombra", "mantenir-posicio", "posicio-seguretat"]):
        ops = puntuacions(w, L, vent, (t, r, h), cob, optim, prev)
        for a, b in itertools.permutations(ops, 2):
            if OBJ[a] >= OBJ[b]:
                continue
            for amb_memoria in (False, True):
                marge = ops[a] - ops[b] - (2 * pm if amb_memoria else 0)
                k = (a, b, amb_memoria)
                if k not in pitjor or marge < pitjor[k][0]:
                    pitjor[k] = (marge, dict(vent=vent, temperatura=t, radiacio=r, hidric=h, cobertura=cob,
                                             a_l_optim=optim, anterior=prev))
    files = [{"guanya_si_es_respecta": a, "objectiu": NOM_OBJ[OBJ[a]], "contra": b,
              "objectiu_contra": NOM_OBJ[OBJ[b]], "amb_memoria": m, "marge_minim": v,
              "es_respecta_sempre": v > 0, "situacio_pitjor": json.dumps(ex, ensure_ascii=False)}
             for (a, b, m), (v, ex) in sorted(pitjor.items())]
    return pd.DataFrame(files)


def fites_requerida(w=BASE, L=NIVELLS, pm=PES_MEMORIA):
    """La preferencia requerida ha de guanyar qualsevol suma de preferencies numeriques."""
    max_num = 3 * w["cultiu"] * L["critic"] + w["estabilitat"] + pm          # ombra amb 3 riscos critics
    max_num = max(max_num, w["energia"] * L["alt"] + w["moviment"] + w["estabilitat"] + pm,
                  w["seguretat"] * L["alt"] + w["estabilitat"] + pm)
    min_req = -pm                                                               # requerida amb memoria dolenta
    return {"max_puntuacio_numerica": max_num, "min_operador_requerit": min_req,
            "requerida_minima_necessaria": max_num - min_req, "requerida": REQUERIDA,
            "factor_de_seguretat": round(REQUERIDA / (max_num - min_req), 1)}


# --------------------------------------------------------------------------- variants del .clp

def variants():
    v = {"base": {}}
    for k, vals in {"seguretat": [3, 4, 7, 10], "cultiu": [2, 4], "energia": [2, 4],
                    "estabilitat": [0, 1, 3, 4], "moviment": [0, 2]}.items():
        for x in vals:
            v[f"pes_{k}_{x}"] = {"pesos": {k: x}}
    v["pesos_tots_1"] = {"pesos": {k: 1 for k in BASE}}
    for nom, niv in {"nivells_0124": (0, 1, 2, 4), "nivells_0149": (0, 1, 4, 9),
                     "nivells_0234": (0, 2, 3, 4), "nivells_0136": (0, 1, 3, 6)}.items():
        v[nom] = {"nivells": dict(zip(NIVELLS, niv))}
    for x in (0, 10, 34, 100):
        v[f"requerida_{x}"] = {"requerida": x}
    # la memoria tambe puntua (fins a +-pes-memoria): nomes compta als dies reals (a la graella esta apagada)
    for x in (0, 1):
        v[f"pes_memoria_{x}"] = {"pes_memoria": x}
    return v


def escriu_variant(nom, canvis) -> str:
    text = open(os.path.join(ARREL, "clips_core", "soar.clp"), encoding="utf-8").read()
    noms_clp = {"seguretat": "seguretat", "cultiu": "produccio-cultiu", "energia": "produccio-energia",
                "estabilitat": "estabilitat", "moviment": "minimitzar-moviment"}
    for k, x in canvis.get("pesos", {}).items():
        patro = rf"(\(deffunction pes-objectiu .*?\(case {noms_clp[k]} then )\d+(\))"
        text, n = re.subn(patro, rf"\g<1>{x}\g<2>", text, count=1, flags=re.S)
        assert n == 1, (nom, k)
    for k, x in canvis.get("nivells", {}).items():
        patro = rf"(\(deffunction nivell-a-numero .*?\(case {k} then )\d+(\))"
        text, n = re.subn(patro, rf"\g<1>{x}\g<2>", text, count=1, flags=re.S)
        assert n == 1, (nom, k)
    if "pes_memoria" in canvis:
        vell = "(slot pes-memoria (type NUMBER) (default 2))"
        assert text.count(vell) == 1, nom
        text = text.replace(vell, f"(slot pes-memoria (type NUMBER) (default {canvis['pes_memoria']}))")
    if "requerida" in canvis:
        vell = "(case requerida then (bind ?total (+ ?total 1000)))"
        assert text.count(vell) == 1, nom
        text = text.replace(vell, f"(case requerida then (bind ?total (+ ?total {canvis['requerida']})))")
    d = os.path.join(DIR, "variants", nom, "clips_core")
    os.makedirs(d, exist_ok=True)
    f = os.path.join(d, "soar.clp")
    with open(f, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return f


# --------------------------------------------------------------------------- B. graella

def _graella(arg):
    """Una variant a la graella. Es desa a resultats/E19/graella/<variant>.csv: si s'interromp, es continua."""
    nom, clp = arg
    fet = os.path.join(DIR, "graella", f"{nom}.csv.gz")
    if os.path.isfile(fet):
        return pd.read_csv(fet).to_dict("records")
    import e2_graella as E
    E._init(clp)
    casos = [dict(zip(E.GRAELLA_RAPIDA, vals)) for vals in itertools.product(*E.GRAELLA_RAPIDA.values())]
    files = []
    for cas in casos:
        for f in E._un_cas(cas):
            f.pop("regles", None)
            files.append({"variant": nom, **f})
    os.makedirs(os.path.dirname(fet), exist_ok=True)
    pd.DataFrame(files).to_csv(fet + ".tmp", index=False, compression="gzip")
    os.replace(fet + ".tmp", fet)
    return files


# --------------------------------------------------------------------------- C. dies reals

def _dies(arg):
    nom, clp, lloc, dies = arg
    import simulador as S
    esc = {"clp": clp} if nom != "base" else {}
    if lloc != "ribera":
        esc["lloc"] = lloc
    cfg = S.carrega_config(esc)
    df = S.Simulacio(cfg, 0).executa(dies, etiqueta=nom)
    df["variant"] = nom
    return df[["variant", "lloc", "dia", "hora", "sector", "accio", "angle_ordre", "P_kw", "estres_rad",
               "estres_calor", "estres_aigua", "violacio_seguretat", "exposicio_vent", "impas", "invariants_ko"]]


def resum_dies(df):
    base = df[df["variant"] == "base"].set_index(["lloc", "dia", "hora", "sector"])["accio"]
    base_ang = df[df["variant"] == "base"].set_index(["lloc", "dia", "hora", "sector"])["angle_ordre"]
    files = []
    for nom, g in df.groupby("variant", sort=False):
        a = g.set_index(["lloc", "dia", "hora", "sector"])["accio"]
        ang = g.set_index(["lloc", "dia", "hora", "sector"])["angle_ordre"]
        comuns = a.index.intersection(base.index)
        canvis = (g.sort_values(["lloc", "dia", "sector", "hora"])
                  .groupby(["lloc", "dia", "sector"])["accio"].apply(lambda s: (s != s.shift()).sum() - 1).sum())
        ndies = g.groupby(["lloc", "dia"]).ngroups
        files.append({"variant": nom,
                      "concordanca_pct": round(100 * (a.loc[comuns] == base.loc[comuns]).mean(), 2),
                      "mateix_angle_pct": round(100 * ((ang.loc[comuns] - base_ang.loc[comuns]).abs() < 0.5).mean(), 2),
                      "energia_kwh_dia": round(g["P_kw"].sum() / ndies, 1),
                      "h_estres_rad_dia": round(g["estres_rad"].sum() / ndies, 2),
                      "h_estres_calor_dia": round(g["estres_calor"].sum() / ndies, 2),
                      "exposicio_vent_h_dia": round(g["exposicio_vent"].sum() / ndies, 3),
                      "violacions": int(g["violacio_seguretat"].sum()),
                      "impasses_dia": round((g["impas"].fillna("") != "").sum() / ndies, 2),
                      "canvis_operador_dia": round(canvis / ndies, 2),
                      "invariants_ko": int((g["invariants_ko"].fillna("") != "").sum())})
    return pd.DataFrame(files)


def resum_graella(df):
    base = df[df["variant"] == "base"].reset_index(drop=True)
    files = []
    for nom, g in df.groupby("variant", sort=False):
        g = g.reset_index(drop=True)
        files.append({"variant": nom, "decisions": len(g),
                      "concordanca_pct": round(100 * (g["accio"].fillna("") == base["accio"].fillna("")).mean(), 2),
                      "violacions": int((g["ko"].fillna("") != "").sum()),
                      "impasses": int((g["impas"].fillna("") != "").sum())})
    return pd.DataFrame(files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dies", type=int, default=20, help="dies de cada lloc")
    ap.add_argument("--processos", type=int, default=os.cpu_count())
    ap.add_argument("--nomes-analitica", action="store_true")
    ap.add_argument("--part", choices=["graella", "dies", "totes"], default="totes")
    a = ap.parse_args()
    os.makedirs(DIR, exist_ok=True)

    an = analitica()
    an.to_csv(os.path.join(DIR, "E19_analitica.csv"), index=False)
    req = fites_requerida()
    print(an[["guanya_si_es_respecta", "contra", "amb_memoria", "marge_minim", "es_respecta_sempre"]].to_string())
    print("requerida:", req)
    # sensibilitat analitica: quins pesos de seguretat fan que guanyi sempre a l'energia
    llindar = []
    for ws in range(3, 13):
        t = analitica({**BASE, "seguretat": ws})
        e = t[(t["objectiu"] == "seguretat") & (t["objectiu_contra"] == "energia")]
        llindar.append({"pes_seguretat": ws, "marge_sense_memoria": e[~e["amb_memoria"]]["marge_minim"].min(),
                        "marge_amb_memoria": e[e["amb_memoria"]]["marge_minim"].min()})
    llindar = pd.DataFrame(llindar)
    llindar.to_csv(os.path.join(DIR, "E19_llindar_seguretat.csv"), index=False)
    print(llindar.to_string())
    json.dump(req, open(os.path.join(DIR, "E19_requerida.json"), "w"), indent=2)
    if a.nomes_analitica:
        return

    vs = variants()
    clps = {nom: (escriu_variant(nom, c) if c else os.path.join(ARREL, "clips_core", "soar.clp"))
            for nom, c in vs.items()}
    json.dump(vs, open(os.path.join(DIR, "E19_variants.json"), "w"), indent=2)

    if a.part in ("graella", "totes"):
        _part_graella(clps, a)
    if a.part in ("dies", "totes"):
        _part_dies(clps, a)


def _part_graella(clps, a):
    # a la graella la memoria esta apagada: les variants del pes de memoria hi donarien el mateix que la base
    feines = [(n, c) for n, c in clps.items() if not n.startswith("pes_memoria")]
    res = paralel.mapa(_graella, feines, a.processos, titol="E19 graella", cada=1, mida=1, espera_maxima=1800)
    gr = pd.DataFrame([f for fs in res for f in fs])
    gr.to_csv(os.path.join(DIR, "E19_graella_detall.csv.gz"), index=False)
    rg = resum_graella(gr)
    rg.to_csv(os.path.join(DIR, "E19_graella.csv"), index=False)
    print(rg.to_string())


def _part_dies(clps, a):
    import simulador as S
    rib = S.selecciona_dies(S.carrega_config({}), a.dies, llavor=19)
    can = S.selecciona_dies(S.carrega_config({"lloc": "cantallops"}), a.dies, llavor=19,
                            filtre=lambda g: g["vent"].max() >= 12)
    feines = [(nom, clp, lloc, dies) for nom, clp in clps.items() for lloc, dies in (("ribera", rib), ("cantallops", can))]
    res = paralel.mapa(_dies, feines, a.processos, titol="E19 dies reals", cada=1, mida=1, espera_maxima=3600)
    df = pd.concat(res, ignore_index=True)
    df.to_csv(os.path.join(DIR, "E19_dies_detall.csv.gz"), index=False)
    rd = resum_dies(df)
    rd.to_csv(os.path.join(DIR, "E19_dies.csv"), index=False)
    print(rd.to_string())


if __name__ == "__main__":
    main()
