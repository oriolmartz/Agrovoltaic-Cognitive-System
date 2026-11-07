"""E23: el temps per cicle de cada estrategia d'oblit contra la linia base A (sense oblit).

E23 nomes posa a prova l'energia, l'estres, la fidelitat i els episodis examinats. Aquest script hi
afegeix el temps: per a cada (dia, llavor) es compara el ms per cicle d'A amb el de cada braç
(Wilcoxon aparellat, correccio de Holm sobre els 18 braços). Cal que E23 s'hagi executat sol
(--processos 1) perque els temps siguin comparables.

Us: python verificacio/e23_temps.py   ->  resultats/E23/E23_temps_tests.csv
"""
import os
import sys

import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
import estadistica as st  # noqa: E402

DIR = os.path.join(os.path.dirname(AQUI), "resultats", "E23")


def main():
    d = pd.read_csv(os.path.join(DIR, "E23_per_dia.csv"))
    ample = d.pivot_table(index=["dia", "llavor"], columns="etiqueta", values="ms_per_cicle")
    files = []
    for braç in [c for c in ample.columns if c != "A_sense_oblit"]:
        r = st.compara_aparellat(ample["A_sense_oblit"], ample[braç], "A", braç, "ms_per_cicle")
        files.append({"braç": braç, "n": r["n"], "ms_A": round(r["mitjana_A"], 1), "ms_braç": round(r["mitjana_B"], 1),
                      "canvi_pct": round(100 * (r["mitjana_B"] / r["mitjana_A"] - 1), 1),
                      "IC95_A-braç": r["IC95_dif"], "p": r["p_wilcoxon"], "efecte": round(r["efecte_rb"], 2)})
    t = pd.DataFrame(files)
    t["p (Holm)"] = [f"{x:.2g}" for x in st.holm(t["p"].tolist())]
    t = t.drop(columns="p")
    t.to_csv(os.path.join(DIR, "E23_temps_tests.csv"), index=False)
    print(t.to_string(index=False))


if __name__ == "__main__":
    main()
