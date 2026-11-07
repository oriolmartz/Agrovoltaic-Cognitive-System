"""E11b: ablacio de l'especificitat a l'agenda de CLIPS.

E11 mostra que les decisions no depenen de l'estrategia de l'agenda, pero no aïlla l'efecte de
l'especificitat sobre l'ordre de dispar. Aquest script ho fa amb un sol cicle controlat:

  - Entrada: el cas CP04 amb vent de 18 m/s al sector del tomaquet (risc mecanic critic), la resta
    de sectors normals. Mateixos fets i mateixa salience en totes les execucions.
  - Parella de regles estudiada: `avalua-rebuig-per-vent-critic` i `avalua-moviment`. Totes dues
    tenen salience 0 i auto-focus, i s'activen alhora a la fase d'avaluacio.
  - Manipulacio (copia experimental del .clp, el codi de l'equip no es toca): s'afegeixen k
    condicions neutres `(test (integerp ?c))` a `avalua-moviment`. ?c es sempre un enter (numero
    de cicle), de manera que el conjunt de fets que casen no canvia; nomes canvia l'especificitat.
    k = 0 es l'original; amb k = 2 les dues regles tenen la mateixa especificitat (es comprova:
    simplicity i complexity les disparen en el mateix ordre); amb k = 3 l'especificitat s'inverteix.
  - Estrategies: simplicity i complexity (ordenen per especificitat) i depth com a referencia.

Per a cada execucio es registra l'ordre de dispar a l'avaluacio, les activacions creades per regla
(`watch activations`) i la decisio final dels tres sectors. Quan dues activacions tenen la mateixa
especificitat, l'ordre entre elles el decideix el desempat de CLIPS (recencia); no se li atribueix
cap significat.

Us: python verificacio/e11_especificitat.py  ->  resultats/E11/E11_especificitat.csv i .md
"""
import collections
import os
import re
import sys

import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
ARREL = os.path.dirname(AQUI)
sys.path.insert(0, ARREL)
sys.path.insert(0, AQUI)
import casos_prova as CP  # noqa: E402
import clips_bridge as B  # noqa: E402

S1 = B.SECTORS[0]
R_VENT, R_MOV = "avalua-rebuig-per-vent-critic", "avalua-moviment"
ANCORA = ("  (operador (sector ?s) (cicle ?c) (nom mantenir-posicio))\n"
          "  (not (preferencia (op mantenir-posicio) (sector ?s) (cicle ?c) (font AV7-moviment)))")
VARIANTS = {0: "original", 2: "especificitat igualada", 3: "especificitat invertida"}
ESTRATEGIES = ("simplicity", "complexity", "depth")
DIR = os.path.join(ARREL, "resultats", "E11")


def variant(k: int) -> str:
    txt = open(os.path.join(ARREL, "clips_core", "soar.clp"), encoding="utf-8").read()
    assert txt.count(ANCORA) == 1, "la regla avalua-moviment ha canviat: cal revisar l'ablacio"
    neutres = "".join("  (test (integerp ?c))\n" for _ in range(k))
    txt = txt.replace(ANCORA, ANCORA.replace("  (not", neutres + "  (not", 1))
    d = os.path.join(DIR, "variants")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"especificitat_k{k}.clp")
    with open(p, "w", encoding="utf-8") as f:
        f.write(txt)
    return p


def executa(clp: str, estrategia: str):
    """Un cicle del cas amb vent de 18 m/s; retorna el ResultatCicle."""
    original = B.ControladorCLIPS.__init__

    def init(self, *a, **kw):
        kw.update(estrategia=estrategia, vigila_regles=True,
                  fitxer_ontologia=str(B.ONTOLOGIA_MODEL_DEFECTE))
        original(self, *a, **kw)
        self.env.eval("(watch activations)")

    B.ControladorCLIPS.__init__ = init
    CP.ControladorCLIPS = B.ControladorCLIPS
    out = []
    cas = {"cicles": [CP.cicle(obs={S1: {"vent": 18.0}}, pred={S1: {"vent": 18.0}},
                               **{S1: {"accio": "posicio-seguretat"}})]}
    try:
        CP.executa_cas(clp, cas, captura=lambda k, o, p, e, r: out.append(r))
    finally:
        B.ControladorCLIPS.__init__ = original
    return out[0]


def main():
    files, ordres = [], {}
    for k, nom in VARIANTS.items():
        clp = variant(k)
        for e in ESTRATEGIES:
            r = executa(clp, e)
            i0 = r.regles.index("proposta-a-avaluacio")
            i1 = r.regles.index("avaluacio-a-seleccio")
            aval = r.regles[i0 + 1:i1]
            parella = [x for x in aval if x in (R_VENT, R_MOV)]
            activ = collections.Counter(re.findall(r"==> Activation\s+\S+\s+([^:\s]+):", r.sortida))
            decisio = {s: r.ordres[s][0] if r.ordres.get(s) else None for s in B.SECTORS}
            ordres[(k, e)] = aval
            files.append({
                "variant": nom, "k_condicions_neutres": k, "estrategia": e,
                "ordre_parella": " > ".join("vent-critic" if x == R_VENT else "moviment" for x in parella),
                "posicio_vent_critic": parella.index(R_VENT) + 1,
                "dispars_avaluacio": len(aval),
                "activacions_totals": sum(activ.values()),
                "activacions_vent_critic": activ[R_VENT], "activacions_moviment": activ[R_MOV],
                "regles_disparades_cicle": r.regles_disparades,
                "cicle_complet": r.fase_final == "espera",
                **{f"decisio_{s}": f"{d[0]} {d[1]:g}" if d else "" for s, d in decisio.items()},
                "_multiset": tuple(sorted(r.regles)),
            })
    t = pd.DataFrame(files)
    ref = t["_multiset"].iloc[0]
    t["mateixes_regles_que_original"] = t["_multiset"].apply(lambda m: m == ref)
    t = t.drop(columns="_multiset")
    os.makedirs(DIR, exist_ok=True)
    t.to_csv(os.path.join(DIR, "E11_especificitat.csv"), index=False)

    with open(os.path.join(DIR, "E11_especificitat.md"), "w", encoding="utf-8") as f:
        f.write("# E11b: ablació de l'especificitat\n\n"
                "Generat per `verificacio/e11_especificitat.py`. Un cicle amb vent de 18 m/s al sector "
                "del tomàquet; k condicions neutres `(test (integerp ?c))` afegides a `avalua-moviment`.\n\n")
        f.write(t.to_markdown(index=False))
        f.write("\n\n## Ordre de dispar a la fase d'avaluació\n\n")
        for (k, e), seq in ordres.items():
            f.write(f"- **k = {k} ({VARIANTS[k]}), {e}:** " + ", ".join(seq) + "\n")
    print(t.drop(columns=[c for c in t.columns if c.startswith("decisio_")]).to_string(index=False))
    print(t[["variant", "estrategia"] + [c for c in t.columns if c.startswith("decisio_")]].to_string(index=False))


if __name__ == "__main__":
    main()
