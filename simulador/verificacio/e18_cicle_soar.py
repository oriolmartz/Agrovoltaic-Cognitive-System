"""E18 - Verificacio del cicle SOAR: les fases passen en l'ordre correcte?

Els invariants de cada simulacio ja comproven que cada sector acaba el cicle amb exactament un
operador seleccionat i una ordre (I1, I2) i que el cicle es tanca a 'espera' (I6, I9). Aqui es
comprova, a mes, el RECORREGUT de cada cicle, a partir de les regles que es disparen (watch rules):

  C1 Ordre de les fases. Les transicions han de ser exactament
       percepcio -> elaboracio -> proposta -> avaluacio -> seleccio
       [-> impas -> seleccio]*  -> aplicacio -> explicacio -> monitoratge -> espera
     (cada fase un sol cop, i el bucle seleccio -> impas -> seleccio nomes si hi ha impasses).
  C2 Cap regla es dispara fora de la seva fase: cada regla que te '(fase (nom X))' a la condicio
     nomes es pot disparar mentre la fase actual es X.
  C3 Una sola decisio per sector i actuador: exactament un operador seleccionat, una ordre al panell
     i (v1_9) una ordre de reg per sector (invariants I1, I2, I10).

Les fases de cada regla i les transicions es llegeixen del mateix soar.clp (la regla que fa
'(assert (fase (nom Y)))' i te '(fase (nom X))' a la condicio es la transicio X -> Y).

Control negatiu: el mateix comprovador sobre una copia del .clp on les regles de transicio tenen
salience 0 en lloc de -10 (el mutant S01 d'E17). Aleshores una transicio pot passar abans que
acabin les regles de la fase. Com que cada regla de fase demana el fet (fase (nom X)), l'ordre C1/C2
no es pot trencar (la regla que arriba tard ja no troba la seva fase), pero hi ha regles que no
arriben a disparar-se: el comprovador ho ha de detectar per C3 (decisions que falten o sobren).

Dies: 10 dies de Ribera de Sio i 10 dies de vent de Cantallops amb el sensor de vent que falla un
10 % de les vegades (perque hi hagi impasses i chunks i el bucle d'impasse quedi provat).

    python verificacio/e18_cicle_soar.py
"""

from __future__ import annotations

import json
import os
import re
import sys

import pandas as pd

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)
import simulador as S  # noqa: E402

DIR = os.path.join(ARREL, "resultats", "E18")
ORDRE = ["percepcio", "elaboracio", "proposta", "avaluacio", "seleccio", "aplicacio", "explicacio",
         "monitoratge", "espera"]


def regles_i_fases(clp: str):
    """{regla: fase on es dispara} i {regla de transicio: (de, a)} llegits del .clp."""
    text = open(clp, encoding="utf-8").read()
    fase, trans = {}, {}
    for m in re.finditer(r"^\(defrule\s+(\S+)(.*?)(?=^\(def|\Z)", text, flags=re.M | re.S):
        nom, cos = m.group(1), m.group(2)
        lhs, _, rhs = cos.partition("=>")
        f = re.search(r"\(fase \(nom (\w+)\)\)", lhs)
        a = re.search(r"\(assert \(fase \(nom (\w+)\)\)\)", rhs)
        if f:
            fase[nom] = f.group(1)
            if a:
                trans[nom] = (f.group(1), a.group(1))
    return fase, trans


def recorregut_valid(fases: list[str]) -> bool:
    """percepcio elaboracio proposta avaluacio seleccio (impas seleccio)* aplicacio explicacio monitoratge espera"""
    s = " ".join(fases)
    return re.fullmatch(r"percepcio elaboracio proposta avaluacio seleccio( impas seleccio)* aplicacio "
                        r"explicacio monitoratge espera", s) is not None


class Enregistrador(S.ControladorSOAR):
    """El controlador SOAR normal, pero guarda les regles disparades de cada cicle."""

    def __init__(self, cfg, domini):
        cfg = S._fusiona(cfg, {"controlador": {"vigila_regles": True}})
        super().__init__(cfg, domini)
        self.cicles = []

    def decideix(self, e):
        out = super().decideix(e)
        self.cicles.append({"cicle": e.cicle, "hora": e.hora, "regles": out["_cicle"]["regles_noms"],
                            "invariants": {s: out[s]["invariants"] for s in S.SECTORS},
                            "impas": any(out[s]["impas"] for s in S.SECTORS)})
        return out


def comprova(cicles, fase_de, trans):
    files = []
    for c in cicles:
        actual, fases, fora = "percepcio", ["percepcio"], []
        desconegudes = 0
        for r in c["regles"]:
            nom = r.split("::")[-1]
            if nom in trans:
                de, a = trans[nom]
                if de != actual:
                    fora.append(nom)
                actual = a
                fases.append(a)
            elif nom in fase_de:
                if fase_de[nom] != actual:
                    fora.append(f"{nom}@{actual}")
            else:
                desconegudes += 1          # regles sense fase a la condicio (memoria, reforç, chunks)
        inv = [k for v in c["invariants"].values() for k in v.split(",") if k]
        c3 = [k for k in inv if k.split("-")[0] in ("I1", "I2", "I10")]
        files.append({"dia": c.get("dia"), "hora": c["hora"], "cicle": c["cicle"], "impas": c["impas"],
                      "recorregut": " > ".join(fases), "C1_ordre_ok": recorregut_valid(fases),
                      "C2_fora_de_fase": ",".join(fora), "C3_decisions_ko": ",".join(sorted(set(c3))),
                      "regles": len(c["regles"]), "regles_sense_fase": desconegudes})
    return pd.DataFrame(files)


def clp_control() -> str:
    """Copia del soar.clp amb les transicions a salience 0 (resultats/E18/control/clips_core/soar.clp:
    el pont injecta l'ontologia quan el fitxer es diu aixi)."""
    text = open(os.path.join(ARREL, "clips_core", "soar.clp"), encoding="utf-8").read()
    assert "(salience -10)" in text
    d = os.path.join(DIR, "control", "clips_core")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "soar.clp"), "w", encoding="utf-8", newline="\n") as f:
        f.write(text.replace("(salience -10)", "(salience 0)"))
    return os.path.join(d, "soar.clp")


def executa(nom, esc, dies):
    cfg = S.carrega_config(esc)
    sim = S.Simulacio(cfg, 0)
    tots = []
    for d in dies:
        rec = []
        sim.executa([d], fabrica=lambda c, dom: rec.append(Enregistrador(c, dom)) or rec[-1], etiqueta=nom)
        for c in rec[-1].cicles:
            c["dia"] = d
        tots += rec[-1].cicles
    return tots


def main(n_dies: int = 10):
    cfg = S.carrega_config({})
    clp = os.path.join(ARREL, cfg["clp"])
    fase_de, trans = regles_i_fases(clp)
    esperades = {(a, b) for a, b in zip(ORDRE, ORDRE[1:])} | {("seleccio", "impas"), ("impas", "seleccio")}
    trobades = set(trans.values())
    print(f"{len(fase_de)} regles amb fase; transicions al .clp: {sorted(trobades)}")
    assert trobades == esperades, f"les transicions del .clp no son les del cicle: {trobades ^ esperades}"
    rib = S.selecciona_dies(cfg, n_dies, llavor=18)
    can_cfg = S.carrega_config({"lloc": "cantallops"})
    can = S.selecciona_dies(can_cfg, n_dies, llavor=18, filtre=lambda g: g["vent"].max() >= 12)
    cicles = executa("ribera", {}, rib) + executa(
        "cantallops_sensor_10", {"lloc": "cantallops", "sensors": {"p_absent": {"vent": 0.10}}}, can)
    df = comprova(cicles, fase_de, trans)
    os.makedirs(DIR, exist_ok=True)
    df.to_csv(os.path.join(DIR, "E18_cicles.csv"), index=False)
    resum = {
        "cicles": len(df), "cicles_amb_impasse": int(df["impas"].sum()),
        "C1_ordre_incorrecte": int((~df["C1_ordre_ok"]).sum()),
        "C2_cicles_amb_regles_fora_de_fase": int((df["C2_fora_de_fase"] != "").sum()),
        "C3_cicles_amb_mes_o_menys_d_una_decisio": int((df["C3_decisions_ko"] != "").sum()),
        "regles_disparades": int(df["regles"].sum()),
        "regles_sense_fase_a_la_condicio": int(df["regles_sense_fase"].sum()),
        "recorreguts_diferents": df["recorregut"].value_counts().to_dict(),
    }
    json.dump(resum, open(os.path.join(DIR, "E18_resum.json"), "w"), indent=2, ensure_ascii=False)
    print(json.dumps(resum, indent=2, ensure_ascii=False))
    ko = df[(~df["C1_ordre_ok"]) | (df["C2_fora_de_fase"] != "") | (df["C3_decisions_ko"] != "")]
    if len(ko):
        print("\nExemples de cicles incorrectes:\n", ko.head(10).to_string())
    # Control negatiu
    ctl = comprova(executa("control_salience_0", {"clp": clp_control()}, rib[:max(1, n_dies // 5)]),
                   fase_de, trans)
    ctl.to_csv(os.path.join(DIR, "E18_control_negatiu.csv"), index=False)
    det = int(((~ctl["C1_ordre_ok"]) | (ctl["C2_fora_de_fase"] != "") | (ctl["C3_decisions_ko"] != "")).sum())
    resum["control_negatiu"] = {"cicles": len(ctl), "cicles_detectats": det,
                                "C1_ordre_incorrecte": int((~ctl["C1_ordre_ok"]).sum()),
                                "C2_fora_de_fase": int((ctl["C2_fora_de_fase"] != "").sum()),
                                "C3_decisions_ko": int((ctl["C3_decisions_ko"] != "").sum()),
                                "cicles_amb_impasse": int(ctl["impas"].sum()),
                                "regles_per_cicle": round(float(ctl["regles"].mean()), 1)}
    resum["regles_per_cicle"] = round(float(df["regles"].mean()), 1)
    json.dump(resum, open(os.path.join(DIR, "E18_resum.json"), "w"), indent=2, ensure_ascii=False)
    print("control negatiu (transicions a salience 0):", resum["control_negatiu"])
    if det == 0:
        print("ATENCIO: el comprovador no detecta el control negatiu")
    sys.exit(1 if len(ko) or det == 0 else 0)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
