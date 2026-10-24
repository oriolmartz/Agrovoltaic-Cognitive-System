"""E3 - Casos de prova als llindars, amb el resultat esperat escrit ABANS d'executar.

Mètode VVR de Zlatareva (Batarseh & Gonzalez 2015): cada cas te una entrada, el resultat
ESPERAT (tret de les fonts del domini, no del codi CLIPS) i el resultat OBTINGUT.
  - casos POSITIUS: el sistema ha de concloure X        (p. ex. vent 16 m/s -> seguretat)
  - casos NEGATIUS: el sistema NO ha de concloure X     (p. ex. vent 11,9 m/s -> cap risc mecanic)
Els valors es posen just a sota, just al llindar i just a sobre (analisi de valors limit).

Fonts dels llindars (les mateixes que l'ontologia):
  vent           fabricant del seguidor: avis 12 m/s, posicio de seguretat obligatoria >= 16 m/s
  temperatura    FAO / fitxes de cultiu: optima maxima i maxima absoluta de cada cultiu;
                 mitja = fins a mig cami entre les dues, alt = fins a l'absoluta, critic = per sobre
  aigua          FAO-56: fraccio esgotable sense estres p (tomaquet 0,40, enciam 0,30, vinya 0,45);
                 la resta (1-p) es parteix en tres trams iguals: mitja, alt, critic
  radiacio       radiacio optima maxima i radiacio d'estres de cada cultiu
  reg (v1_9)     FAO-56: regar abans o en el moment d'esgotar p; s'anticipa a partir del 75 % de p,
                 nomes a hores fresques (<= 8 h o >= 19 h, Diputacio de Barcelona) i no a la vinya
                 (reg deficitari, AWRI); >= 10 mm de pluja prevista anul.la el reg (Diputacio), llevat
                 d'estres critic; >= 2 mm previstos fan preferir la dosi parcial (FAO-56: pluja efectiva)

    python verificacio/e3_llindars.py [--clp ../history/clips/simulator/soar_v1_7.clp]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import pandas as pd

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)
from clips_bridge import SECTORS, SENSORS, ControladorCLIPS  # noqa: E402

S1, S2, S3 = SECTORS          # tomaquet, enciam, vinya

# Entrada "tranquil·la" per a cada cultiu: tot dins de l'optim, sense vent.
BASE = {
    S1: {"radiacio": 100.0, "temperatura-aire": 20.0, "temperatura-cultiu": 22.0, "humitat-sol": 95.0, "vent": 3.0, "pluja": 0.0},
    S2: {"radiacio": 100.0, "temperatura-aire": 15.0, "temperatura-cultiu": 16.0, "humitat-sol": 95.0, "vent": 3.0, "pluja": 0.0},
    S3: {"radiacio": 100.0, "temperatura-aire": 22.0, "temperatura-cultiu": 24.0, "humitat-sol": 95.0, "vent": 3.0, "pluja": 0.0},
}
PRED_BASE = {"radiacio": 100.0, "temperatura": 20.0, "vent": 3.0, "pluja": 0.0}

ABS = "absent"   # marca d'una lectura que no arriba


def cas(id, descripcio, sector, obs=None, pred=None, panell=None, hora=12, **esperat):
    """esperat: risc_<tipus>=nivell|None, accio=, accio_no=, candidat=, no_candidat=, rebutjat=,
    reg=, reg_no=, dosi= (v1_9)"""
    return {"id": id, "descripcio": descripcio, "sector": sector, "obs": obs or {}, "pred": pred or {},
            "panell": panell or {}, "hora": hora, "esperat": esperat}


CASOS = [
    # ------------------------------------------------------------------ vent (tots els cultius igual)
    cas("V01", "vent 11,9: just sota l'avis", S1, {"vent": 11.9}, risc_mecanic=None, no_candidat="posicio-seguretat"),
    cas("V02", "vent 12,0: avis", S1, {"vent": 12.0}, risc_mecanic="alt", candidat="posicio-seguretat"),
    cas("V03", "vent 15,9: just sota el maxim", S1, {"vent": 15.9}, risc_mecanic="alt", candidat="posicio-seguretat"),
    cas("V04", "vent 16,0: maxim, seguretat obligatoria", S1, {"vent": 16.0}, risc_mecanic="critic",
        accio="posicio-seguretat", rebutjat="orientar-produccio"),
    cas("V05", "vent 4 pero previsio 16: mana la pitjor", S1, {"vent": 4.0}, {"vent": 16.0},
        risc_mecanic="critic", accio="posicio-seguretat"),
    cas("V06", "vent 4 i previsio 12: avis per previsio", S1, {"vent": 4.0}, {"vent": 12.0}, risc_mecanic="alt"),
    cas("V07", "sense lectura de vent i previsio tranquil·la: demanar dades", S1, {"vent": ABS}, {"vent": 3.0},
        risc_dades="critic", accio="sollicitar-dades", accio_no="orientar-produccio"),
    cas("V08", "sense lectura de vent i previsio 16: seguretat", S1, {"vent": ABS}, {"vent": 16.0},
        accio="posicio-seguretat"),
    cas("V09", "sense lectura de vent i previsio 12: seguretat (requisit de disseny)", S1, {"vent": ABS}, {"vent": 12.0},
        accio="posicio-seguretat"),
    cas("V10", "sense lectura ni previsio de vent: no s'orienta a produccio", S1, {"vent": ABS}, {"vent": ABS},
        risc_dades="critic", accio_no="orientar-produccio"),

    # ------------------------------------------------------------------ temperatura: tomaquet (27 / 35)
    cas("T01", "tomaquet 27,0: optima maxima", S1, {"temperatura-cultiu": 27.0}, risc_temperatura=None),
    cas("T02", "tomaquet 27,1", S1, {"temperatura-cultiu": 27.1}, risc_temperatura="mitja"),
    cas("T03", "tomaquet 31,0: mig cami", S1, {"temperatura-cultiu": 31.0}, risc_temperatura="mitja"),
    cas("T04", "tomaquet 31,1", S1, {"temperatura-cultiu": 31.1}, risc_temperatura="alt"),
    cas("T05", "tomaquet 35,0: maxima absoluta", S1, {"temperatura-cultiu": 35.0}, risc_temperatura="alt"),
    cas("T06", "tomaquet 35,1", S1, {"temperatura-cultiu": 35.1}, risc_temperatura="critic", candidat="orientar-ombra"),
    # enciam (21 / 30)
    cas("T07", "enciam 21,0", S2, {"temperatura-cultiu": 21.0}, risc_temperatura=None),
    cas("T08", "enciam 21,1", S2, {"temperatura-cultiu": 21.1}, risc_temperatura="mitja"),
    cas("T09", "enciam 25,5: mig cami", S2, {"temperatura-cultiu": 25.5}, risc_temperatura="mitja"),
    cas("T10", "enciam 25,6", S2, {"temperatura-cultiu": 25.6}, risc_temperatura="alt"),
    cas("T11", "enciam 30,0", S2, {"temperatura-cultiu": 30.0}, risc_temperatura="alt"),
    cas("T12", "enciam 30,1", S2, {"temperatura-cultiu": 30.1}, risc_temperatura="critic"),
    # vinya (30 / 38)
    cas("T13", "vinya 30,0", S3, {"temperatura-cultiu": 30.0}, risc_temperatura=None),
    cas("T14", "vinya 30,1", S3, {"temperatura-cultiu": 30.1}, risc_temperatura="mitja"),
    cas("T15", "vinya 34,0: mig cami", S3, {"temperatura-cultiu": 34.0}, risc_temperatura="mitja"),
    cas("T16", "vinya 34,1", S3, {"temperatura-cultiu": 34.1}, risc_temperatura="alt"),
    cas("T17", "vinya 38,0", S3, {"temperatura-cultiu": 38.0}, risc_temperatura="alt"),
    cas("T18", "vinya 38,1", S3, {"temperatura-cultiu": 38.1}, risc_temperatura="critic"),

    # ------------------------------------------------------------------ aigua: tomaquet p = 0,40 (trams de 0,20)
    cas("A01", "tomaquet 60 % d'aigua: limit sense estres", S1, {"humitat-sol": 60.0}, risc_estres_hidric=None),
    cas("A02", "tomaquet 59,9 %", S1, {"humitat-sol": 59.9}, risc_estres_hidric="mitja"),
    cas("A03", "tomaquet 40 %", S1, {"humitat-sol": 40.0}, risc_estres_hidric="mitja"),
    cas("A04", "tomaquet 39,9 %", S1, {"humitat-sol": 39.9}, risc_estres_hidric="alt"),
    cas("A05", "tomaquet 20 %", S1, {"humitat-sol": 20.0}, risc_estres_hidric="alt"),
    cas("A06", "tomaquet 19,9 %", S1, {"humitat-sol": 19.9}, risc_estres_hidric="critic"),
    # enciam p = 0,30 (trams de 0,2333)
    cas("A07", "enciam 70 %", S2, {"humitat-sol": 70.0}, risc_estres_hidric=None),
    cas("A08", "enciam 69,9 %", S2, {"humitat-sol": 69.9}, risc_estres_hidric="mitja"),
    cas("A09", "enciam 46,7 %", S2, {"humitat-sol": 46.7}, risc_estres_hidric="mitja"),
    cas("A10", "enciam 46,6 %", S2, {"humitat-sol": 46.6}, risc_estres_hidric="alt"),
    cas("A11", "enciam 23,4 %", S2, {"humitat-sol": 23.4}, risc_estres_hidric="alt"),
    cas("A12", "enciam 23,3 %", S2, {"humitat-sol": 23.3}, risc_estres_hidric="critic"),
    # vinya p = 0,45
    cas("A13", "vinya 55 %", S3, {"humitat-sol": 55.0}, risc_estres_hidric=None),
    cas("A14", "vinya 54,9 %", S3, {"humitat-sol": 54.9}, risc_estres_hidric="mitja"),

    # ------------------------------------------------------------------ radiacio
    cas("R01", "tomaquet 350 W/m2: optima maxima", S1, {"radiacio": 350.0}, risc_exces_radiacio=None,
        no_candidat="orientar-ombra"),
    cas("R02", "tomaquet 350,1", S1, {"radiacio": 350.1}, risc_exces_radiacio="mitja", candidat="orientar-ombra"),
    cas("R03", "tomaquet 435: llindar d'estres", S1, {"radiacio": 435.0}, risc_exces_radiacio="mitja"),
    cas("R04", "tomaquet 435,1", S1, {"radiacio": 435.1}, risc_exces_radiacio="alt"),
    cas("R05", "enciam 170", S2, {"radiacio": 170.0}, risc_exces_radiacio=None),
    cas("R06", "enciam 170,1 (optim = estres)", S2, {"radiacio": 170.1}, risc_exces_radiacio="alt"),
    cas("R07", "vinya 610", S3, {"radiacio": 610.0}, risc_exces_radiacio=None),
    cas("R08", "vinya 610,1", S3, {"radiacio": 610.1}, risc_exces_radiacio="mitja"),
    cas("R09", "vinya 780,1", S3, {"radiacio": 780.1}, risc_exces_radiacio="alt"),

    # ------------------------------------------------------------------ combinacions i altres
    cas("C01", "tomaquet: radiacio alta + calor alta -> radiacio critica", S1,
        {"radiacio": 500.0, "temperatura-cultiu": 33.0}, risc_exces_radiacio="critic", risc_temperatura="alt"),
    cas("C02", "tomaquet: radiacio alta + calor nomes mitja -> no s'agreuja", S1,
        {"radiacio": 500.0, "temperatura-cultiu": 29.0}, risc_exces_radiacio="alt", risc_temperatura="mitja"),
    cas("C03", "tot tranquil: cap risc i no es proposa ombra", S1, {}, risc_mecanic=None, risc_temperatura=None,
        risc_estres_hidric=None, risc_exces_radiacio=None, risc_dades=None, no_candidat="orientar-ombra"),
    cas("C04", "panell avariat i informat: no es proposa seguir el sol", S1, {}, panell={"estat-mecanic": "avariat",
        "disponible": "no"}, no_candidat="orientar-produccio"),
    cas("C05", "sense lectura de temperatura del cultiu: risc de dades alt", S1, {"temperatura-cultiu": ABS},
        risc_dades="alt"),
    cas("C06", "vent critic i calor critica alhora: mana la seguretat", S1,
        {"vent": 18.0, "temperatura-cultiu": 36.0, "radiacio": 600.0}, accio="posicio-seguretat",
        rebutjat="orientar-ombra"),

    # ------------------------------------------------------------------ reg (v1_9)
    # enciam p = 0,30: s'anticipa des d'un esgotament de 0,225 (77,5 % d'aigua)
    cas("G01", "enciam 77,5 % a les 7 h: 75 % de p, s'anticipa", S2, {"humitat-sol": 77.5}, hora=7,
        reg="regar-complet", dosi=22.5),
    cas("G02", "enciam 77,6 % a les 7 h: encara no", S2, {"humitat-sol": 77.6}, hora=7, reg="no-regar"),
    cas("G03", "enciam 77,5 % a les 13 h: no s'anticipa al migdia", S2, {"humitat-sol": 77.5}, hora=13, reg="no-regar"),
    cas("G04", "enciam 77,5 % a les 8 h: encara es hora fresca", S2, {"humitat-sol": 77.5}, hora=8, reg_no="no-regar"),
    cas("G05", "enciam 77,5 % a les 9 h: ja no", S2, {"humitat-sol": 77.5}, hora=9, reg="no-regar"),
    cas("G06", "enciam 77,5 % a les 18 h: encara no", S2, {"humitat-sol": 77.5}, hora=18, reg="no-regar"),
    cas("G07", "enciam 77,5 % a les 19 h: hora fresca", S2, {"humitat-sol": 77.5}, hora=19, reg_no="no-regar"),
    # tomaquet p = 0,40: s'anticipa des de 0,30 (70 %)
    cas("G08", "tomaquet 70 % a les 7 h: s'anticipa", S1, {"humitat-sol": 70.0}, hora=7, reg="regar-complet", dosi=30.0),
    cas("G09", "tomaquet 70,1 % a les 7 h: encara no", S1, {"humitat-sol": 70.1}, hora=7, reg="no-regar"),
    # vinya p = 0,45: no s'anticipa
    cas("G10", "vinya 55 % a les 7 h: al llindar, no es rega", S3, {"humitat-sol": 55.0}, hora=7, reg="no-regar"),
    cas("G11", "vinya 54,9 %: estres, reg parcial", S3, {"humitat-sol": 54.9}, reg="regar-parcial", dosi=22.6),
    # pluja prevista (tomaquet amb estres, 55 %)
    cas("G12", "tomaquet 55 % i 9,9 mm previstos: es rega, pero parcial", S1, {"humitat-sol": 55.0},
        {"pluja": 9.9}, hora=7, reg="regar-parcial"),
    cas("G13", "tomaquet 55 % i 10 mm previstos: no es rega", S1, {"humitat-sol": 55.0}, {"pluja": 10.0}, hora=7,
        reg="no-regar"),
    cas("G14", "tomaquet 55 % i 1,9 mm previstos: reg complet", S1, {"humitat-sol": 55.0}, {"pluja": 1.9}, hora=7,
        reg="regar-complet", dosi=45.0),
    cas("G15", "tomaquet 55 % i 2 mm previstos: reg parcial", S1, {"humitat-sol": 55.0}, {"pluja": 2.0}, hora=7,
        reg="regar-parcial", dosi=25.0),
    # estres critic de l'enciam (esgotament > 0,7667: menys del 23,33 %)
    cas("G16", "enciam 23,3 % (critic) i 30 mm previstos: es rega igualment", S2, {"humitat-sol": 23.3},
        {"pluja": 30.0}, reg_no="no-regar"),
    cas("G17", "enciam 23,4 % (alt) i 30 mm previstos: no es rega", S2, {"humitat-sol": 23.4}, {"pluja": 30.0},
        reg="no-regar"),
    cas("G18", "sense lectura d'humitat: no es rega", S2, {"humitat-sol": ABS}, hora=7, reg="no-regar"),
]


def executa_cas(clp: str, c: dict) -> dict:
    ctrl = ControladorCLIPS(clp, reforc=False, chunking=False, epmem=False)
    for pid, p in ctrl.panells().items():
        extra = c["panell"] if p["sector"] == c["sector"] else {}
        ctrl.escriu_panell(pid, angle=30.0, **{"angle-optim-produccio": 30.0}, **extra)
    for s in SECTORS:
        obs = dict(BASE[s])
        pred = dict(PRED_BASE)
        if s == c["sector"]:
            obs.update(c["obs"])
            pred.update(c["pred"])
        obs = {k: (None if v == ABS else v) for k, v in obs.items()}
        pred = {k: (None if v == ABS else v) for k, v in pred.items()}
        for tp in SENSORS:
            ctrl.escriu_sensor(s, tp, True, "valida" if obs.get(tp) is not None else "absent", 1)
        ctrl.afegeix_entrades(1, s, obs, pred, {"produccio": 10.0, "demanda": 12.0})
    ctrl.escriu_moment(1, c["hora"])
    r = ctrl.executa_cicle()
    s = c["sector"]
    riscos = dict(r.riscos.get(s, []))
    accio = r.ordres[s][0][0] if r.ordres.get(s) else None
    candidats = set(r.candidats.get(s, {}))
    rebutjats = r.rebutjats.get(s, set())
    reg, dosi = (r.reg[s][0][0], r.reg[s][0][1]) if r.reg.get(s) else (None, None)
    if any(k in c["esperat"] for k in ("reg", "reg_no", "dosi")) and not ctrl.te_reg:
        del ctrl
        return None                      # versio sense reg: el cas no s'aplica
    fallades = []
    for k, v in c["esperat"].items():
        if k.startswith("risc_"):
            tipus = k[5:].replace("_", "-")
            if riscos.get(tipus) != v:
                fallades.append(f"risc {tipus}: esperat {v or 'cap'}, obtingut {riscos.get(tipus) or 'cap'}")
        elif k == "accio" and accio != v:
            fallades.append(f"accio: esperada {v}, obtinguda {accio}")
        elif k == "accio_no" and accio == v:
            fallades.append(f"accio: NO havia de ser {v}")
        elif k == "candidat" and v not in candidats:
            fallades.append(f"{v} havia de ser candidat")
        elif k == "no_candidat" and v in candidats:
            fallades.append(f"{v} NO havia de ser candidat")
        elif k == "rebutjat" and v not in rebutjats:
            fallades.append(f"{v} havia de quedar rebutjat")
        elif k == "reg" and reg != v:
            fallades.append(f"reg: esperat {v}, obtingut {reg}")
        elif k == "reg_no" and reg == v:
            fallades.append(f"reg: NO havia de ser {v}")
        elif k == "dosi" and (dosi is None or abs(dosi - v) > 1e-6):
            fallades.append(f"dosi: esperada {v} %, obtinguda {dosi}")
    positiu = any(k in ("accio", "candidat", "rebutjat", "reg", "dosi") or (k.startswith("risc_") and v) for k, v in c["esperat"].items())
    negatiu = any(k in ("accio_no", "no_candidat", "reg_no") or (k.startswith("risc_") and not v) for k, v in c["esperat"].items())
    del ctrl
    return {"id": c["id"], "descripcio": c["descripcio"], "sector": s,
            "tipus": "+/-" if positiu and negatiu else ("+" if positiu else "-"),
            "esperat": "; ".join(f"{k}={v if v is not None else 'cap'}" for k, v in c["esperat"].items()),
            "obtingut": f"accio={accio}; riscos=" + (",".join(f"{t}={n}" for t, n in sorted(riscos.items())) or "cap")
                        + (f"; reg={reg} ({dosi} %)" if reg else ""),
            "resultat": "PASS" if not fallades else "FAIL", "discrepancia": " | ".join(fallades)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clp", default=os.path.join(ARREL, "clips_core", "soar.clp"))
    a = ap.parse_args()
    clp = os.path.abspath(a.clp)
    df = pd.DataFrame([x for x in (executa_cas(clp, c) for c in CASOS) if x is not None])
    versio = os.path.splitext(os.path.basename(clp))[0]
    os.makedirs(os.path.join(ARREL, "resultats", "E3"), exist_ok=True)
    out = os.path.join(ARREL, "resultats", "E3", f"e3_llindars_{versio}.csv")
    df.to_csv(out, index=False)
    pd.set_option("display.width", 220, "display.max_colwidth", 90)
    print(df[["id", "tipus", "resultat", "descripcio"]].to_string(index=False))
    ko = df[df["resultat"] == "FAIL"]
    print(f"\n{versio}: {len(df) - len(ko)}/{len(df)} casos correctes")
    for _, r in ko.iterrows():
        print(f"  {r['id']} ({r['descripcio']}): {r['discrepancia']}")
    json.dump({"versio": versio, "casos": len(df), "pass": int(len(df) - len(ko)), "fail": int(len(ko)),
               "fallades": ko[["id", "descripcio", "discrepancia"]].to_dict("records")},
              open(os.path.join(ARREL, "resultats", "E3", f"e3_llindars_{versio}.json"), "w"), indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
