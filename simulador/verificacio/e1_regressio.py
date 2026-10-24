"""E1 - Proves de regressio: executa el run_soar_v1_x.clp de cada versio i en recull el resultat.

Cada versio s'executa en un proces nou (entorn CLIPS net). Es el pas que s'ha de
repetir despres de CADA canvi al .clp (validacio incremental, Batarseh 2015).

    python verificacio/e1_regressio.py            # totes les versions historiques
    python verificacio/e1_regressio.py v1_7       # nomes una
"""

from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIPS = os.path.abspath(os.path.join(ARREL, "..", "history", "clips", "simulator"))

CODI = r"""
import clips, sys
e = clips.Environment()
class R(clips.Router):
    def __init__(s): super().__init__('r', 30)
    def query(s, n): return n in ('stdout', 't', 'wwarning', 'werror', 'wdisplay')
    def write(s, n, m): sys.stdout.write(m)
r = R(); e.add_router(r)
try:
    e.batch_star(sys.argv[1])
except Exception as x:
    print('ERROR_PYTHON', x)
r.delete()
"""


def executa(versio: str) -> dict:
    run = os.path.join(CLIPS, f"run_soar_{versio}.clp")
    t0 = time.time()
    p = subprocess.run([sys.executable, "-c", CODI, os.path.basename(run)], cwd=CLIPS,
                       capture_output=True, text=True, timeout=600)
    sortida = p.stdout + p.stderr
    passes = re.findall(r"\[PASS\] (.*)", sortida)
    fails = re.findall(r"\[FAIL\] (.*)", sortida)
    errors = [l for l in sortida.splitlines() if re.search(r"\[[A-Z]+\d+\]|ERROR", l)]
    d = os.path.join(ARREL, "resultats", "E1")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"traca_run_soar_{versio}.txt"), "w", encoding="utf-8") as f:
        f.write(sortida)
    for f in ("epmem_prova.dat", "chunks_prova.dat"):
        try:
            os.remove(os.path.join(CLIPS, f))
        except FileNotFoundError:
            pass
    return {"versio": versio, "pass": len(passes), "fail": len(fails), "fallades": fails,
            "errors_clips": errors[:20], "segons": round(time.time() - t0, 2)}


def main():
    versions = sys.argv[1:] or sorted(re.search(r"run_soar_(v[\d_]+)\.clp", f).group(1)
                                      for f in glob.glob(os.path.join(CLIPS, "run_soar_v*.clp")))
    res = [executa(v) for v in versions]
    print(f"{'versio':8} {'pass':>5} {'fail':>5} {'errors':>7} {'s':>6}")
    for r in res:
        print(f"{r['versio']:8} {r['pass']:5} {r['fail']:5} {len(r['errors_clips']):7} {r['segons']:6}")
        for f in r["fallades"]:
            print("    FAIL:", f)
        for e in r["errors_clips"]:
            print("    CLIPS:", e)
    os.makedirs(os.path.join(ARREL, "resultats", "E1"), exist_ok=True)
    json.dump(res, open(os.path.join(ARREL, "resultats", "E1", "e1_regressio.json"), "w"), indent=2, ensure_ascii=False)
    sys.exit(1 if any(r["fail"] or r["errors_clips"] for r in res) else 0)


if __name__ == "__main__":
    main()
