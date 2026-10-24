"""E1 - Proves de regressio: executa el run_soar_v1_x.clp de cada versio i en recull el resultat.

Cada versio s'executa en un proces nou (entorn CLIPS net). Es el pas que s'ha de
repetir despres de CADA canvi al .clp (validacio incremental, Batarseh 2015).

    python verificacio/e1_regressio.py            # la versio canonica (clips_core) i totes les historiques
    python verificacio/e1_regressio.py v1_7       # nomes una
    python verificacio/e1_regressio.py actual     # nomes la canonica

La versio canonica es clips_core/soar.clp (generat dels moduls amb build_clips.py) i les seves
proves son clips_core/run_proves.clp. Abans d'executar-la es comprova que soar.clp esta al dia
amb els moduls: si algu ha editat un modul i no ha regenerat soar.clp, E1 falla.
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
CORE = os.path.join(ARREL, "clips_core")


def soar_al_dia() -> bool:
    """TRUE si clips_core/soar.clp es exactament la concatenacio dels moduls de modules.txt."""
    moduls = [x.strip() for x in open(os.path.join(CORE, "modules.txt"), encoding="utf-8").read().splitlines()
              if x.strip() and not x.lstrip().startswith("#")]
    cont = "".join(open(os.path.join(CORE, m), encoding="utf-8", newline="").read() for m in moduls)
    return open(os.path.join(CORE, "soar.clp"), encoding="utf-8", newline="").read() == cont

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
    carpeta = CORE if versio == "actual" else CLIPS
    run = os.path.join(CORE, "run_proves.clp") if versio == "actual" else os.path.join(CLIPS, f"run_soar_{versio}.clp")
    t0 = time.time()
    p = subprocess.run([sys.executable, "-c", CODI, os.path.basename(run)], cwd=carpeta,
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
            os.remove(os.path.join(carpeta, f))
        except FileNotFoundError:
            pass
    return {"versio": versio, "pass": len(passes), "fail": len(fails), "fallades": fails,
            "errors_clips": errors[:20], "segons": round(time.time() - t0, 2)}


def main():
    versions = sys.argv[1:] or (["actual"] + sorted(re.search(r"run_soar_(v[\d_]+)\.clp", f).group(1)
                                                    for f in glob.glob(os.path.join(CLIPS, "run_soar_v*.clp"))))
    al_dia = True
    if "actual" in versions:
        # la topologia de la versio canonica ve del RDF: es projecta a un deffacts per a run_proves.clp
        sys.path.insert(0, ARREL)
        from ontology_loader import ONTOLOGIA_MODEL_DEFECTE, carrega_model, deffacts_clips
        with open(os.path.join(CORE, "topologia_rdf.clp"), "w", encoding="utf-8", newline="\n") as f:
            f.write(deffacts_clips(carrega_model(ONTOLOGIA_MODEL_DEFECTE)))
        al_dia = soar_al_dia()
        if not al_dia:
            print("ERROR: clips_core/soar.clp no coincideix amb els moduls. Executa: python clips_core/build_clips.py")
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
    sys.exit(1 if not al_dia or any(r["fail"] or r["errors_clips"] for r in res) else 0)


if __name__ == "__main__":
    main()
