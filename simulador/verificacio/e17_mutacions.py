"""E17 - Mutation testing: com de bones son les nostres proves?

Tsai, Vishnuvajjala & Zhang (1999), sec. 6.1.1: s'introdueixen errors a proposit al sistema
("mutants"), un cada cop, i es mira si les proves els detecten ("maten"). El percentatge de mutants
morts mesura l'adequacio de les proves. Els mutants que sobreviuen s'han de mirar un per un: o les
proves tenen un forat, o el mutant es equivalent (el canvi no altera cap comportament observable,
p. ex. esborrar una regla que no es dispara mai).

Mutants, sobre clips_core/soar.clp (el .clp canonic NO es toca; els mutants van a resultats/E17/):
  - esborrar una regla (una per mutant, totes les defrule);
  - canviar un llindar del domini (vent, p de cada cultiu, temperatura, radiacio, reg);
  - canviar un pes d'objectiu;
  - canviar un operador relacional als llindars (<= per <, >= per >);
  - treure la salience -10 de les transicions de fase.

Proves que es passen a cada mutant (les mateixes de la regressio):
  P1 clips_core/run_proves.clp (79 proves, CLIPS pur)
  P2 E3, 75 casos als llindars
  P3 els 14 casos de prova (un mutant el mata si canvia quins casos fallen respecte de l'original)

    python verificacio/e17_mutacions.py [--processos N] [--nomes-llindars]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

import pandas as pd

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)
sys.path.insert(0, os.path.join(ARREL, "verificacio"))
import paralel  # noqa: E402

CORE = os.path.join(ARREL, "clips_core")
DIR = os.path.join(ARREL, "resultats", "E17")

# (id, descripcio, text original (ha d'apareixer exactament el nombre de vegades indicat), text nou, vegades)
SUBSTITUCIONS = [
    ("L01", "vent d'avis 12 -> 13 m/s", "(slot vent-avis (type FLOAT) (default 12.0))", "(slot vent-avis (type FLOAT) (default 13.0))", 1),
    ("L02", "vent maxim 16 -> 17 m/s", "(slot vent-maxim (type FLOAT) (default 16.0))", "(slot vent-maxim (type FLOAT) (default 17.0))", 1),
    ("L03", "p del tomaquet 0,40 -> 0,50", "(fraccio-esgotament-p 0.40)", "(fraccio-esgotament-p 0.50)", 1),
    ("L04", "p de l'enciam 0,30 -> 0,40", "(fraccio-esgotament-p 0.30)", "(fraccio-esgotament-p 0.40)", 1),
    ("L05", "p de la vinya 0,45 -> 0,55", "(fraccio-esgotament-p 0.45)", "(fraccio-esgotament-p 0.55)", 1),
    ("L06", "temperatura optima maxima del tomaquet 27 -> 29", "(temp-optima-max 27.0)", "(temp-optima-max 29.0)", 1),
    ("L07", "temperatura optima maxima de l'enciam 21 -> 23", "(temp-optima-max 21.0)", "(temp-optima-max 23.0)", 1),
    ("L08", "temperatura optima maxima de la vinya 30 -> 32", "(temp-optima-max 30.0)", "(temp-optima-max 32.0)", 1),
    ("L09", "radiacio optima maxima del tomaquet 350 -> 400", "(radiacio-optima-max 350.0)", "(radiacio-optima-max 400.0)", 1),
    ("L10", "reg: anticipacio al 75 % -> 90 % de p", "(slot anticipacio (type FLOAT) (default 0.75))", "(slot anticipacio (type FLOAT) (default 0.90))", 1),
    ("L11", "reg: pluja que anul.la el reg 10 -> 15 mm", "(slot pluja-anulla (type FLOAT) (default 10.0))", "(slot pluja-anulla (type FLOAT) (default 15.0))", 1),
    ("L12", "reg: hora fresca del mati fins a les 8 -> 9 h", "(slot hora-fresca-mati (type INTEGER) (default 8))", "(slot hora-fresca-mati (type INTEGER) (default 9))", 1),
    ("W01", "pes de la seguretat 5 -> 1", "(case seguretat then 5)", "(case seguretat then 1)", 1),
    ("W02", "pes del cultiu 3 -> 2", "(case produccio-cultiu then 3)", "(case produccio-cultiu then 2)", 1),
    ("W03", "pes de l'energia 3 -> 4", "(case produccio-energia then 3)", "(case produccio-energia then 4)", 1),
    ("R01", "vent critic: >= maxim -> > maxim", "(if (>= ?v ?max) then critic", "(if (> ?v ?max) then critic", 1),
    ("R02", "vent alt: >= avis -> > avis", "(>= ?v ?avis) then alt", "(> ?v ?avis) then alt", 1),
    ("R03", "calor: <= optima -> < optima", "(if (<= ?t ?opt) then baix", "(if (< ?t ?opt) then baix", 1),
    ("R04", "aigua: <= p -> < p (sense el marge)", "(if (<= ?e (+ ?p ?eps)) then baix", "(if (< ?e ?p) then baix", 1),
    ("S01", "transicions de fase: salience -10 -> 0", "(salience -10)", "(salience 0)", 10),
]

CODI_RUN = r"""
import clips, sys
e = clips.Environment()
class R(clips.Router):
    def __init__(s): super().__init__('r', 30)
    def query(s, n): return n in ('stdout', 't', 'wwarning', 'werror', 'wdisplay')
    def write(s, n, m): sys.stdout.write(m)
r = R(); e.add_router(r)
try:
    e.batch_star('run_proves.clp')
except Exception as x:
    print('ERROR_PYTHON', x)
r.delete()
"""


def _constructes(text: str):
    """Posicions (inici, fi, nom) de cada (defrule ...) de nivell superior."""
    out = []
    for m in re.finditer(r"^\(defrule\s+(\S+)", text, flags=re.M):
        i, d, instr, k = m.start(), 0, False, m.start()
        while k < len(text):
            ch = text[k]
            if instr:
                if ch == "\\":
                    k += 2
                    continue
                if ch == '"':
                    instr = False
            elif ch == '"':
                instr = True
            elif ch == ";":
                k = text.find("\n", k)
                if k < 0:
                    break
                continue
            elif ch == "(":
                d += 1
            elif ch == ")":
                d -= 1
                if d == 0:
                    out.append((i, k + 1, m.group(1)))
                    break
            k += 1
    return out


def mutants(text: str) -> list[dict]:
    llista = []
    for ident, desc, vell, nou, n in SUBSTITUCIONS:
        assert text.count(vell) == n, f"{ident}: '{vell}' apareix {text.count(vell)} vegades"
        llista.append({"id": ident, "tipus": "llindar" if ident[0] == "L" else {"W": "pes", "R": "operador",
                                                                              "S": "salience"}[ident[0]],
                       "descripcio": desc, "text": text.replace(vell, nou)})
    for k, (i, f, nom) in enumerate(_constructes(text), 1):
        llista.append({"id": f"D{k:02d}", "tipus": "regla esborrada", "descripcio": f"sense la regla {nom}",
                       "text": text[:i] + f"; MUTANT: regla {nom} esborrada\n" + text[f:]})
    return llista


def _prova(m: dict) -> dict:
    """Escriu el mutant i hi passa P1, P2 i P3."""
    import casos_prova
    import e3_llindars
    # el pont injecta l'ontologia quan el fitxer es diu soar.clp dins d'una carpeta clips_core
    d = os.path.join(DIR, "mutants", m["id"], "clips_core")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "soar.clp"), "w", encoding="utf-8", newline="\n") as f:
        f.write(m["text"])
    for fx in ("run_proves.clp", "topologia_rdf.clp"):
        shutil.copy(os.path.join(CORE, fx), d)
    clp = os.path.join(d, "soar.clp")
    t0 = time.time()
    # P1
    try:
        p = subprocess.run([sys.executable, "-c", CODI_RUN], cwd=d, capture_output=True, text=True, timeout=300)
        sortida = p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        sortida = "TIMEOUT"
    p1_pass = len(re.findall(r"\[PASS\]", sortida))
    p1_fail = len(re.findall(r"\[FAIL\]", sortida))
    p1_err = bool(re.search(r"ERROR|TIMEOUT|\[[A-Z]+\d+\]", sortida)) and "ENVRNMNT8" not in sortida
    p1 = p1_fail > 0 or p1_err or p1_pass < BASE["p1_pass"]
    # P2
    try:
        res = [x for x in (e3_llindars.executa_cas(clp, c) for c in e3_llindars.CASOS) if x is not None]
        p2_fail = sum(r["resultat"] == "FAIL" for r in res)
        p2 = p2_fail > BASE["p2_fail"]
    except Exception:
        p2_fail, p2 = -1, True
    # P3
    try:
        ko = sorted(cas["id"] for cas in casos_prova.CASOS if not casos_prova.executa_cas(clp, cas)[2])
        p3 = ko != BASE["p3_ko"]
    except Exception:
        ko, p3 = ["ERROR"], True
    for fx in ("epmem_prova.dat", "chunks_prova.dat"):
        try:
            os.remove(os.path.join(d, fx))
        except FileNotFoundError:
            pass
    return {"id": m["id"], "tipus": m["tipus"], "descripcio": m["descripcio"],
            "P1_run_proves": f"{p1_pass} pass, {p1_fail} fail" + (", error" if p1_err else ""),
            "P2_E3_fallades": p2_fail, "P3_casos_que_fallen": ",".join(ko),
            "mort_per": ",".join(n for n, k in (("P1", p1), ("P2", p2), ("P3", p3)) if k),
            "mort": p1 or p2 or p3, "segons": round(time.time() - t0, 1)}


BASE = {}


def _init(base):
    BASE.update(base)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--processos", type=int, default=os.cpu_count())
    ap.add_argument("--nomes-llindars", action="store_true", help="sense els mutants de regla esborrada")
    a = ap.parse_args()
    # la topologia de l'ontologia per a run_proves.clp (com fa E1)
    from ontology_loader import ONTOLOGIA_MODEL_DEFECTE, carrega_model, deffacts_clips
    with open(os.path.join(CORE, "topologia_rdf.clp"), "w", encoding="utf-8", newline="\n") as f:
        f.write(deffacts_clips(carrega_model(ONTOLOGIA_MODEL_DEFECTE)))
    text = open(os.path.join(CORE, "soar.clp"), encoding="utf-8", newline="").read()
    shutil.rmtree(os.path.join(DIR, "mutants"), ignore_errors=True)
    # l'original ha de passar-ho tot (P3: nomes CP01, la discrepancia coneguda)
    _init({"p1_pass": 10 ** 9, "p2_fail": 10 ** 9, "p3_ko": None})
    orig = _prova({"id": "ORIGINAL", "tipus": "-", "descripcio": "sense mutacio", "text": text})
    base = {"p1_pass": int(orig["P1_run_proves"].split()[0]), "p2_fail": orig["P2_E3_fallades"],
            "p3_ko": orig["P3_casos_que_fallen"].split(",") if orig["P3_casos_que_fallen"] else []}
    print("Original:", orig["P1_run_proves"], "| E3 fallades:", base["p2_fail"], "| casos que fallen:", base["p3_ko"])
    llista = mutants(text)
    if a.nomes_llindars:
        llista = [m for m in llista if m["tipus"] != "regla esborrada"]
    res = paralel.mapa(_prova, llista, a.processos, initializer=_init, initargs=(base,), titol="E17 mutants", cada=5)
    df = pd.DataFrame(res)
    shutil.rmtree(os.path.join(DIR, "mutants"), ignore_errors=True)
    os.makedirs(DIR, exist_ok=True)
    df.to_csv(os.path.join(DIR, "E17_mutants.csv"), index=False)
    resum = (df.groupby("tipus").agg(mutants=("id", "size"), morts=("mort", "sum")).assign(
        pct_morts=lambda x: (100 * x["morts"] / x["mutants"]).round(1)))
    resum.loc["TOTAL"] = [len(df), int(df["mort"].sum()), round(100 * df["mort"].mean(), 1)]
    resum.to_csv(os.path.join(DIR, "E17_resum.csv"))
    per_prova = {p: int(df["mort_per"].str.contains(p).sum()) for p in ("P1", "P2", "P3")}
    json.dump({"original": orig, "per_prova": per_prova}, open(os.path.join(DIR, "E17_original.json"), "w"),
              indent=2, ensure_ascii=False, default=str)
    pd.set_option("display.width", 220, "display.max_colwidth", 70)
    print(resum.to_string())
    print("Mutants detectats per cada prova:", per_prova)
    viu = df[~df["mort"]]
    if len(viu):
        print(f"\nMutants vius ({len(viu)}):")
        print(viu[["id", "tipus", "descripcio"]].to_string(index=False))


if __name__ == "__main__":
    main()
