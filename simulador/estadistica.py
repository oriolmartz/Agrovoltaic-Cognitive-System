"""Eines estadistiques per als experiments (nomes numpy + scipy).

Disseny per defecte: APARELLAT. Totes les configuracions es proven amb els mateixos
dies i les mateixes llavors, de manera que cada dia es un bloc i es comparen
diferencies dins del bloc (elimina la variabilitat entre dies: un dia de juliol i
un d'abril no es comparen entre ells).

  2 configuracions  -> Wilcoxon de rangs amb signe (no suposa normalitat)
                       + mida de l'efecte (correlacio biserial de rangs aparellada)
                       + IC 95 % bootstrap de la diferencia de mitjanes
  k > 2             -> Friedman, i despres Wilcoxon per parelles amb correccio de Holm
  0 esdeveniments   -> regla de tres / Clopper-Pearson (cota superior de la taxa)
  quants dies       -> potencia d'un t aparellat (aproximacio per a Wilcoxon: x1/0.955)
"""

from __future__ import annotations

import itertools
import math

import numpy as np
import pandas as pd
from scipy import stats


# ----------------------------------------------------------------------------- 2 configuracions

def bootstrap_ic(x: np.ndarray, estadistic=np.mean, b: int = 10000, alfa: float = 0.05, llavor: int = 0):
    rng = np.random.default_rng(llavor)
    x = np.asarray(x, dtype=float)
    if len(x) == 0:
        return (math.nan, math.nan)
    mostres = rng.choice(x, size=(b, len(x)), replace=True)
    v = np.apply_along_axis(estadistic, 1, mostres)
    return float(np.quantile(v, alfa / 2)), float(np.quantile(v, 1 - alfa / 2))


def rank_biserial_aparellat(d: np.ndarray) -> float:
    """Mida de l'efecte per a Wilcoxon (correlacio biserial de rangs, Kerby 2014):
    (R+ - R-) / suma de tots els rangs. Els empats (diferencia 0) compten al denominador,
    aixi que si gairebe tots els dies son iguals l'efecte surt petit encara que els pocs
    dies diferents vagin tots cap al mateix costat. Entre -1 i 1."""
    d = np.asarray(d, float)
    if len(d) == 0 or np.allclose(d, 0):
        return 0.0
    r = stats.rankdata(np.abs(d))
    rp, rn = r[d > 0].sum(), r[d < 0].sum()
    return float((rp - rn) / r.sum())


def magnitud(r: float) -> str:
    a = abs(r)
    return "negligible" if a < 0.1 else "petit" if a < 0.3 else "mitja" if a < 0.5 else "gran"


def compara_aparellat(a, b, nom_a="A", nom_b="B", metrica="") -> dict:
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = a - b
    if np.allclose(d, 0):
        p = 1.0
    else:
        p = float(stats.wilcoxon(a, b, zero_method="wilcox").pvalue)
    r = rank_biserial_aparellat(d)
    lo, hi = bootstrap_ic(d)
    return {"metrica": metrica, "A": nom_a, "B": nom_b, "n": len(d),
            "mitjana_A": float(a.mean()), "mitjana_B": float(b.mean()),
            "dif_mitjana": float(d.mean()), "IC95_dif": (round(lo, 3), round(hi, 3)),
            "mediana_dif": float(np.median(d)), "p_wilcoxon": p,
            "efecte_rb": r, "magnitud": magnitud(r)}


# ----------------------------------------------------------------------------- k configuracions

def holm(pvals: list[float]) -> list[float]:
    m = len(pvals)
    ordre = np.argsort(pvals)
    ajust = np.empty(m)
    acc = 0.0
    for k, i in enumerate(ordre):
        acc = max(acc, (m - k) * pvals[i])
        ajust[i] = min(1.0, acc)
    return ajust.tolist()


def compara_multiples(per_dia: pd.DataFrame, metrica: str, col_config: str = "config",
                      blocs=("dia", "llavor")) -> dict:
    """per_dia: una fila per (config, bloc). Retorna Friedman + parelles amb Holm."""
    ample = per_dia.pivot_table(index=list(blocs), columns=col_config, values=metrica, aggfunc="mean").dropna()
    configs = list(ample.columns)
    out = {"metrica": metrica, "n_blocs": len(ample), "configs": configs,
           "mitjanes": ample.mean().round(3).to_dict()}
    if len(configs) > 2:
        if np.allclose(ample.values, ample.values[:, :1]):
            out["p_friedman"] = 1.0
        else:
            out["p_friedman"] = float(stats.friedmanchisquare(*[ample[c] for c in configs]).pvalue)
    parelles = [compara_aparellat(ample[x], ample[y], x, y, metrica) for x, y in itertools.combinations(configs, 2)]
    for p, ph in zip(parelles, holm([p["p_wilcoxon"] for p in parelles])):
        p["p_holm"] = ph
    out["parelles"] = parelles
    return out


def taula_parelles(resultats: list[dict]) -> pd.DataFrame:
    files = []
    for r in resultats:
        for p in r["parelles"]:
            files.append({"metrica": p["metrica"], "A": p["A"], "B": p["B"], "n": p["n"],
                          "mitjana A": round(p["mitjana_A"], 2), "mitjana B": round(p["mitjana_B"], 2),
                          "A-B": round(p["dif_mitjana"], 2), "IC95": p["IC95_dif"],
                          "p (Holm)": f"{p['p_holm']:.2g}", "efecte": f"{p['efecte_rb']:+.2f} ({p['magnitud']})",
                          "Friedman p": f"{r['p_friedman']:.2g}" if "p_friedman" in r else "-"})
    return pd.DataFrame(files)


# ----------------------------------------------------------------------------- esdeveniments rars

def cota_superior_taxa(x: int, n: int, confianca: float = 0.95) -> float:
    """Cota superior (Clopper-Pearson) de la probabilitat d'un esdeveniment vist x cops en n.
    Amb x = 0 es practicament la 'regla de tres': 3/n."""
    if n == 0:
        return 1.0
    if x >= n:
        return 1.0
    return float(stats.beta.ppf(confianca, x + 1, n - x))


# ----------------------------------------------------------------------------- mida de mostra

def potencia_t_aparellat(n: int, d: float, alfa: float = 0.05) -> float:
    gl = n - 1
    tcrit = stats.t.ppf(1 - alfa / 2, gl)
    nc = d * math.sqrt(n)
    return float(1 - stats.nct.cdf(tcrit, gl, nc) + stats.nct.cdf(-tcrit, gl, nc))


def mida_mostra(d: float, alfa: float = 0.05, potencia: float = 0.8, wilcoxon: bool = True) -> int:
    """Dies (parelles) necessaris per detectar un efecte d (Cohen) amb la potencia donada.
    Per a Wilcoxon s'aplica l'eficiencia relativa asimptotica (0.955) respecte del t."""
    n = 3
    while potencia_t_aparellat(n, d, alfa) < potencia:
        n += 1
    return math.ceil(n / 0.955) if wilcoxon else n


if __name__ == "__main__":
    for d in (0.3, 0.5, 0.8):
        print(f"d={d}: {mida_mostra(d)} dies (Wilcoxon), {mida_mostra(d, wilcoxon=False)} (t aparellat);"
              f" amb Holm per 3 comparacions (alfa=0.0167): {mida_mostra(d, alfa=0.05/3)}")
    for n in (500, 2000, 5000):
        print(f"0 violacions en {n} cicles -> taxa <= {100 * cota_superior_taxa(0, n):.3f} % (95 %)")
