"""Casos de prova documentats (enunciat: "un minim de vuit casos de prova, amb entrades, traca
rellevant, sortida i explicacio").

Cada cas es un escenari curt, de 1 a 5 cicles, amb entrades controlades. El resultat ESPERAT
s'escriu ABANS d'executar, a partir del coneixement del domini (no del codi). Per a cada cas es
genera:
  - les entrades de cada cicle,
  - el resultat esperat i l'obtingut, amb el veredicte i les discrepancies,
  - la traca rellevant del CLIPS (les linies del sector afectat, impasses i chunking),
  - l'explicacio que dona el mateix sistema (fet 'explicacio').

Cobertura que demana la rubrica: normalitat, limits, dades absents, fallades, canvis temporals,
casos no vistos, seguretat i conflicte.

    python verificacio/casos_prova.py            -> resultats/casos_prova/CASOS_PROVA.md (+ traces)
"""

from __future__ import annotations

import argparse
import os
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)
from clips_bridge import SECTORS, SENSORS, ControladorCLIPS  # noqa: E402

S1, S2, S3 = SECTORS    # tomaquet, enciam, vinya
CULTIU = {S1: "tomàquet", S2: "enciam", S3: "vinya"}
ABS = "absent"

BASE = {
    S1: {"radiacio": 300.0, "temperatura-aire": 20.0, "temperatura-cultiu": 22.0, "humitat-sol": 90.0, "vent": 3.0, "pluja": 0.0},
    S2: {"radiacio": 150.0, "temperatura-aire": 15.0, "temperatura-cultiu": 16.0, "humitat-sol": 90.0, "vent": 3.0, "pluja": 0.0},
    S3: {"radiacio": 400.0, "temperatura-aire": 22.0, "temperatura-cultiu": 24.0, "humitat-sol": 90.0, "vent": 3.0, "pluja": 0.0},
}
PRED = {"radiacio": 300.0, "temperatura": 20.0, "vent": 3.0, "pluja": 0.0}
ENERGIA = {"produccio": 15.0, "demanda": 12.0}


def cicle(obs=None, pred=None, energia=None, falla=(), hora=12, **esperat):
    """obs/pred/energia: {sector: {camp: valor}} que sobreescriuen la base.
    falla: panells que NO es mouen despres d'aquest cicle (fallada d'actuador).
    hora: hora local del cicle (v1_9: el reg te en compte les hores fresques).
    esperat: {sector: {accio, accio_no, riscos{tipus: nivell|None}, impas, chunk, candidat, rebutjat,
                       reg, dosi, reg_rebutjat}}"""
    return {"obs": obs or {}, "pred": pred or {}, "energia": energia or {}, "falla": set(falla), "hora": hora,
            "esperat": esperat}


CASOS = [
    {"id": "CP01", "titol": "Operació normal", "cobertura": "normalitat",
     "objectiu": "Sense cap risc, el sistema ha de seguir el sol i, quan ja hi és, no moure's.",
     "angle_inicial": 20.0,
     "analisi": "Al cicle 2 el sistema torna a triar orientar-produccio (7 punts: energia 3 + estabilitat 2, "
                "perquè és el que va fer el cicle anterior, + memòria episòdica 2, perquè va funcionar bé) i no "
                "mantenir-posicio (4 punts: ja és a l'angle òptim 3 + sense moviment 1). L'angle ordenat és el "
                "mateix (30°) i el panell no es mou: el comportament és el correcte i l'expectativa estava massa "
                "especificada (fixava el nom de l'operador). El que mostra és interessant: l'estabilitat i la "
                "memòria episòdica fan que el sistema repeteixi el que li ha anat bé.",
     "cicles": [
         cicle(**{S1: {"accio": "orientar-produccio", "riscos": {"mecanic": None, "temperatura": None}},
                  S3: {"accio": "orientar-produccio"}}),
         cicle(**{S1: {"accio": "mantenir-posicio"}, S3: {"accio": "mantenir-posicio"}}),
     ]},
    {"id": "CP02", "titol": "Vent crític", "cobertura": "seguretat",
     "objectiu": "Amb una ratxa de 18 m/s (≥ 16, el màxim del fabricant), el panell ha d'anar a la posició "
                 "de seguretat, i la resta d'opcions han de quedar rebutjades. Els altres sectors no se n'han de veure afectats.",
     "cicles": [
         cicle(obs={S1: {"vent": 18.0}},
               **{S1: {"accio": "posicio-seguretat", "riscos": {"mecanic": "critic"}, "rebutjat": "orientar-produccio"},
                  S2: {"accio_no": "posicio-seguretat"}}),
     ]},
    {"id": "CP03", "titol": "Seguretat anticipada per previsió", "cobertura": "seguretat",
     "objectiu": "El vent ara és de 6 m/s, però la previsió per a la propera hora és de 17 m/s. "
                 "El sistema s'ha d'avançar i posar el panell en seguretat.",
     "cicles": [cicle(obs={S1: {"vent": 6.0}}, pred={S1: {"vent": 17.0}},
                      **{S1: {"accio": "posicio-seguretat", "riscos": {"mecanic": "critic"}}})]},
    {"id": "CP04", "titol": "Límit del vent: 15,9 contra 16,0 m/s", "cobertura": "límits",
     "objectiu": "A 15,9 m/s el risc és alt: la posició de seguretat és candidata, però no obligatòria. "
                 "A 16,0 m/s el risc és crític i la seguretat és obligatòria.",
     "cicles": [
         cicle(obs={S1: {"vent": 15.9}}, pred={S1: {"vent": 15.9}},
               **{S1: {"riscos": {"mecanic": "alt"}, "candidat": "posicio-seguretat"}}),
         cicle(obs={S1: {"vent": 16.0}}, pred={S1: {"vent": 16.0}},
               **{S1: {"accio": "posicio-seguretat", "riscos": {"mecanic": "critic"}, "rebutjat": "orientar-produccio"}}),
     ]},
    {"id": "CP05", "titol": "Conflicte cultiu contra energia (impasse d'empat i chunking)", "cobertura": "conflicte",
     "objectiu": "L'enciam és a 26,5 °C (risc de temperatura alt) i la producció no cobreix la demanda. "
                 "Fer ombra (cultiu) i seguir el sol (energia) valen el mateix: hi ha d'haver un impasse "
                 "d'empat. S'ha de resoldre a favor del cultiu, perquè té més prioritat, i s'ha d'aprendre "
                 "un chunk. Al cicle següent, en la mateixa situació, el chunk ha de decidir sense impasse.",
     "angle_inicial": 0.0, "angle_optim": -55.0,
     "cicles": [
         cicle(obs={S: {"radiacio": 30.0, "temperatura-aire": 18.0, "temperatura-cultiu": 19.0, "humitat-sol": 84.0,
                        "vent": 2.0} for S in SECTORS} | {S2: {"radiacio": 30.0, "temperatura-aire": 18.0,
                                                               "temperatura-cultiu": 26.5, "humitat-sol": 84.0, "vent": 2.0}},
               energia={S: {"produccio": 0.5, "demanda": 6.6} for S in SECTORS},
               **{S2: {"accio": "orientar-ombra", "impas": "empat", "riscos": {"temperatura": "alt"}}}),
         cicle(obs={S: {"radiacio": 30.0, "temperatura-aire": 18.0, "temperatura-cultiu": 19.0, "humitat-sol": 84.0,
                        "vent": 2.0} for S in SECTORS} | {S2: {"radiacio": 30.0, "temperatura-aire": 18.0,
                                                               "temperatura-cultiu": 26.5, "humitat-sol": 84.0, "vent": 2.0}},
               energia={S: {"produccio": 0.5, "demanda": 6.6} for S in SECTORS},
               **{S2: {"accio": "orientar-ombra", "impas": None, "chunk": True}}),
     ]},
    {"id": "CP06", "titol": "Sensor de vent caigut, sense indicis de perill", "cobertura": "dades absents",
     "objectiu": "No arriba la lectura de vent de l'enciam i la previsió és tranquil·la. No es pot garantir "
                 "la seguretat, però tampoc no hi ha cap motiu per moure el panell: impasse de dades → demanar "
                 "dades i mantenir l'angle. Al cicle següent, el chunk ho ha de resoldre sense impasse.",
     "cicles": [
         cicle(obs={S2: {"vent": ABS}}, **{S2: {"accio": "sollicitar-dades", "impas": "dades-insuficients",
                                                 "riscos": {"dades": "critic"}}}),
         cicle(obs={S2: {"vent": ABS}}, **{S2: {"accio": "sollicitar-dades", "impas": None, "chunk": True}}),
     ]},
    {"id": "CP07", "titol": "Sensor de vent caigut després d'una ratxa crítica (historial)", "cobertura": "dades absents + historial",
     "objectiu": "Al cicle 1 hi ha una ratxa de 18 m/s. Al cicle 2 el sensor deixa de respondre: com que "
                 "l'última lectura era perillosa, el sistema s'ha de quedar en seguretat (no fiar-se'n).",
     "cicles": [
         cicle(obs={S1: {"vent": 18.0}}, **{S1: {"accio": "posicio-seguretat"}}),
         cicle(obs={S1: {"vent": ABS}}, **{S1: {"accio": "posicio-seguretat", "riscos": {"dades": "critic"}}}),
     ]},
    {"id": "CP08", "titol": "Fallada d'actuador", "cobertura": "fallades",
     "objectiu": "Al cicle 1 la vinya ha d'anar de 20° a 30°, però l'actuador no es mou. Al cicle 2 el "
                 "sistema ho ha de detectar (risc de fallada), no ha de tornar a enviar ordres de seguiment "
                 "i ha d'avisar manteniment.",
     "angle_inicial": 20.0,
     "cicles": [
         cicle(falla={"Panell_3_1", "Panell_3_2"}, **{S3: {"accio": "orientar-produccio"}}),
         cicle(**{S3: {"riscos": {"fallada-actuador": "alt"}, "rebutjat": "orientar-produccio",
                       "accio_no": "orientar-produccio"}}),
     ]},
    {"id": "CP09", "titol": "Vent que puja i baixa al llarg de 5 hores", "cobertura": "canvis temporals",
     "objectiu": "El vent fa 6 → 13 → 18 → 18 → 8 m/s, amb la previsió de l'hora següent. El sistema ha d'anar "
                 "a seguretat quan la ratxa observada o prevista arriba a 16 m/s, quedar-s'hi mentre duri i "
                 "tornar a produir quan passa.",
     "cicles": [
         cicle(obs={S1: {"vent": 6.0}}, pred={S1: {"vent": 13.0}}, **{S1: {"riscos": {"mecanic": "alt"}}}),
         cicle(obs={S1: {"vent": 13.0}}, pred={S1: {"vent": 18.0}}, **{S1: {"accio": "posicio-seguretat"}}),
         cicle(obs={S1: {"vent": 18.0}}, pred={S1: {"vent": 18.0}}, **{S1: {"accio": "posicio-seguretat"}}),
         cicle(obs={S1: {"vent": 18.0}}, pred={S1: {"vent": 8.0}}, **{S1: {"accio": "posicio-seguretat"}}),
         cicle(obs={S1: {"vent": 8.0}}, pred={S1: {"vent": 6.0}},
               **{S1: {"accio": "orientar-produccio", "riscos": {"mecanic": None}}}),
     ]},
    {"id": "CP10", "titol": "Estrès hídric de l'enciam", "cobertura": "protecció del cultiu",
     "objectiu": "Només queda un 20 % d'aigua disponible a l'enciam (p = 0,30): l'estrès és crític i fer ombra "
                 "ha de ser candidat (redueix l'evapotranspiració).",
     "cicles": [cicle(obs={S2: {"humitat-sol": 20.0}},
                      **{S2: {"riscos": {"estres-hidric": "critic"}, "candidat": "orientar-ombra"}})]},
    {"id": "CP11", "titol": "Radiació i calor alhora al tomàquet", "cobertura": "protecció del cultiu + elaboració",
     "objectiu": "500 W/m² (radiació alta) i 33 °C (calor alta) alhora: la combinació ha d'agreujar el risc "
                 "de radiació a crític, i el sistema ha de fer ombra.",
     "cicles": [cicle(obs={S1: {"radiacio": 500.0, "temperatura-cultiu": 33.0}},
                      **{S1: {"riscos": {"exces-radiacio": "critic", "temperatura": "alt"}, "accio": "orientar-ombra"}})]},
    # ------------------------------------------------------------------ v1_9: reg
    {"id": "CP12", "titol": "Reg a primera hora", "cobertura": "protecció del cultiu (reg)", "reg": True,
     "objectiu": "A les 7 h, l'enciam té un 65 % d'aigua (ha gastat el 35 %, més que el seu p = 30 %): hi ha "
                 "estrès i s'ha de regar fins a capacitat de camp (+35 %). El tomàquet és al 66 % (ha gastat el "
                 "34 %, a prop del seu p = 40 %): és hora fresca i és un cultiu sensible, així que s'ha d'anticipar "
                 "(+34 %). La vinya és al 62 %: no s'anticipa (reg deficitari). El panell decideix a part. A les 8 h, "
                 "amb el sòl ple, ja no s'ha de regar.",
     "cicles": [
         cicle(hora=7, obs={S1: {"humitat-sol": 66.0}, S2: {"humitat-sol": 65.0}, S3: {"humitat-sol": 62.0}},
               **{S1: {"reg": "regar-complet", "dosi": 34.0}, S2: {"reg": "regar-complet", "dosi": 35.0},
                  S3: {"reg": "no-regar"}}),
         cicle(hora=8, obs={S1: {"humitat-sol": 100.0}, S2: {"humitat-sol": 100.0}, S3: {"humitat-sol": 62.0}},
               **{S1: {"reg": "no-regar"}, S2: {"reg": "no-regar"}, S3: {"reg": "no-regar"}}),
     ]},
    {"id": "CP13", "titol": "No es rega perquè plourà", "cobertura": "conflicte cultiu contra estalvi d'aigua (reg)",
     "reg": True,
     "objectiu": "A les 19 h, el tomàquet té estrès (55 %), però es preveuen 15 mm de pluja en les pròximes 12 h "
                 "(≥ 10 mm, Diputació de Barcelona): regar queda rebutjat i no es rega. L'enciam, en canvi, és al "
                 "20 % (estrès crític): no pot esperar i es rega igualment, però només en part (+65 %, en lloc d'omplir "
                 "el sòl), perquè la pluja l'acabarà d'omplir.",
     "cicles": [
         cicle(hora=19, obs={S1: {"humitat-sol": 55.0}, S2: {"humitat-sol": 20.0}},
               pred={S: {"pluja": 15.0} for S in SECTORS},
               **{S1: {"reg": "no-regar", "reg_rebutjat": "regar-complet"},
                  S2: {"reg": "regar-parcial", "dosi": 65.0}}),
     ]},
    {"id": "CP14", "titol": "Reg deficitari de la vinya al llindar", "cobertura": "límits (reg)", "reg": True,
     "objectiu": "La vinya (p = 0,45) amb un 55,0 % d'aigua és just al llindar sense estrès: no es rega (la vinya "
                 "no s'anticipa). Amb un 54,9 % ja hi ha estrès: es rega en part, fins a la meitat de p "
                 "(+22,6 %). Al migdia, si continua amb estrès, també es rega.",
     "cicles": [
         cicle(hora=7, obs={S3: {"humitat-sol": 55.0}}, **{S3: {"reg": "no-regar", "riscos": {"estres-hidric": None}}}),
         cicle(hora=7, obs={S3: {"humitat-sol": 54.9}}, **{S3: {"reg": "regar-parcial", "dosi": 22.6,
                                                                "riscos": {"estres-hidric": "mitja"}}}),
         cicle(hora=13, obs={S3: {"humitat-sol": 54.9}}, **{S3: {"reg": "regar-parcial"}}),
     ]},
]


def _apliqua(base, extra):
    out = {s: dict(v) for s, v in base.items()}
    for s, v in extra.items():
        out[s].update(v)
    return out


def executa_cas(clp, cas):
    c = ControladorCLIPS(clp, conserva_sortida=True)
    a0 = cas.get("angle_inicial", 30.0)
    opt = cas.get("angle_optim", 30.0)
    for pid in c.panells():
        c.escriu_panell(pid, angle=a0, **{"angle-optim-produccio": opt})
    files, traca, ok_total = [], [], True
    for k, cy in enumerate(cas["cicles"], 1):
        n = c.cicle_actual()
        obs = _apliqua(BASE, cy["obs"])
        pred = _apliqua({s: PRED for s in SECTORS}, cy["pred"])
        ene = _apliqua({s: ENERGIA for s in SECTORS}, cy["energia"])
        for s in SECTORS:
            o = {kk: (None if v == ABS else v) for kk, v in obs[s].items()}
            p = {kk: (None if v == ABS else v) for kk, v in pred[s].items()}
            for tp in SENSORS:
                c.escriu_sensor(s, tp, True, "valida" if o.get(tp) is not None else "absent", n)
            c.afegeix_entrades(n, s, o, p, ene[s])
        c.escriu_moment(n, cy["hora"])
        r = c.executa_cicle()
        traca.append((k, r.sortida))
        for s, esp in cy["esperat"].items():
            accio = r.ordres[s][0][0] if r.ordres.get(s) else None
            angle = r.ordres[s][0][1] if r.ordres.get(s) else None
            riscos = dict(r.riscos.get(s, []))
            imp = next((t for t, ss in r.impasses if ss == s), None)
            chunk = any(f.startswith("chunk-") for f, _, _ in r.fonts_pref.get(s, set()))
            cand = set(r.candidats.get(s, {}))
            disc = []
            if "accio" in esp and accio != esp["accio"]:
                disc.append(f"acció esperada {esp['accio']}, obtinguda {accio}")
            if "accio_no" in esp and accio == esp["accio_no"]:
                disc.append(f"l'acció no havia de ser {accio}")
            for t, nv in esp.get("riscos", {}).items():
                if riscos.get(t) != nv:
                    disc.append(f"risc {t}: esperat {nv or 'cap'}, obtingut {riscos.get(t) or 'cap'}")
            if "impas" in esp and imp != esp["impas"]:
                disc.append(f"impasse esperat {esp['impas'] or 'cap'}, obtingut {imp or 'cap'}")
            if "chunk" in esp and chunk != esp["chunk"]:
                disc.append("havia de decidir un chunk" if esp["chunk"] else "no havia de decidir cap chunk")
            if "candidat" in esp and esp["candidat"] not in cand:
                disc.append(f"{esp['candidat']} havia de ser candidat")
            if "rebutjat" in esp and esp["rebutjat"] not in r.rebutjats.get(s, set()):
                disc.append(f"{esp['rebutjat']} havia de quedar rebutjat")
            reg = r.reg.get(s, [(None, None, "")])[0]
            if "reg" in esp and reg[0] != esp["reg"]:
                disc.append(f"reg esperat {esp['reg']}, obtingut {reg[0]}")
            if "dosi" in esp and (reg[1] is None or abs(reg[1] - esp["dosi"]) > 1e-6):
                disc.append(f"dosi esperada {esp['dosi']} %, obtinguda {reg[1]}")
            if "reg_rebutjat" in esp and esp["reg_rebutjat"] not in r.reg_rebutjats.get(s, set()):
                disc.append(f"{esp['reg_rebutjat']} havia de quedar rebutjat")
            ok_total &= not disc
            files.append({"cicle": k, "sector": s, "entrada": {kk: obs[s][kk] for kk in ("vent", "temperatura-cultiu", "humitat-sol", "radiacio")},
                          "previsio_vent": pred[s]["vent"], "esperat": esp, "accio": accio, "angle": angle,
                          "riscos": riscos, "impas": imp, "chunk": chunk, "motiu": r.seleccionat.get(s, [("", "")])[0][1],
                          "explicacio": r.explicacio.get(s, ""), "reg": reg[0], "dosi": reg[1],
                          "explicacio_reg": r.reg_explicacio.get(s, ""), "hora": cy["hora"], "discrepancies": disc})
        # actuadors: cada panell va a l'angle ordenat, llevat dels que fallen
        for pid, p in c.panells().items():
            if pid in cy["falla"]:
                continue
            o = r.ordres.get(p["sector"])
            if o:
                c.escriu_panell(pid, angle=o[0][1])
    del c
    return files, traca, ok_total


def _linies_rellevants(txt, sectors):
    claus = ("IMPAS", "CHUNKING", "[chunk-", "SELECCIO ->", "REFORC", "EXPLICACIO REG")
    out = []
    for l in txt.splitlines():
        if any(s in l for s in sectors) or any(k in l for k in claus):
            if l.strip():
                out.append(l.rstrip())
    return out


def _fmt_esperat(e):
    parts = []
    for k, v in e.items():
        if k == "riscos":
            parts += [f"risc {t} = {n or 'cap'}" for t, n in v.items()]
        elif k == "accio_no":
            parts.append(f"acció ≠ {v}")
        elif k == "chunk":
            parts.append("decideix un chunk" if v else "cap chunk")
        elif k == "impas":
            parts.append(f"impasse = {v or 'cap'}")
        else:
            parts.append(f"{k} = {v}")
    return "; ".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clp", default=os.path.join(ARREL, "clips_core", "soar.clp"))
    a = ap.parse_args()
    clp = os.path.abspath(a.clp)
    d = os.path.join(ARREL, "resultats", "casos_prova")
    os.makedirs(d, exist_ok=True)
    versio = os.path.splitext(os.path.basename(clp))[0]
    md = [f"# Casos de prova ({versio})", "",
          "Generat per `python verificacio/casos_prova.py`. El resultat esperat de cada cas s'ha escrit "
          "abans d'executar-lo, a partir del domini. La traça completa de cada cas és a "
          "`resultats/casos_prova/CPxx_traca.txt`.", "",
          "| Cas | Títol | Cobertura | Cicles | Resultat |", "|---|---|---|---|---|"]
    detall, resum = [], []
    for cas in CASOS:
        files, traca, ok = executa_cas(clp, cas)
        with open(os.path.join(d, f"{cas['id']}_traca.txt"), "w", encoding="utf-8") as f:
            for k, t in traca:
                f.write(f"\n{'#' * 70}\n# {cas['id']} - cicle {k}\n{'#' * 70}\n{t}")
        resum.append((cas, ok, len(cas["cicles"])))
        sectors = sorted({x["sector"] for x in files})
        dd = [f"## {cas['id']} – {cas['titol']}", "", f"**Cobertura:** {cas['cobertura']}. "
              f"**Objectiu i resultat esperat:** {cas['objectiu']}", "",
              "| Cicle | Sector | Entrada (vent / previsió / T cultiu / aigua / radiació) | Esperat | Obtingut | |",
              "|---|---|---|---|---|---|"]
        for x in files:
            e = x["entrada"]
            ent = f"{e['vent']} / {x['previsio_vent']} / {e['temperatura-cultiu']} / {e['humitat-sol']} / {e['radiacio']}"
            if cas.get("reg"):
                ent += f" ({x['hora']} h)"
            obt = f"{x['accio']} ({x['angle']}°)" + (f"; riscos: " + ", ".join(f"{t}={n}" for t, n in sorted(x['riscos'].items())) if x["riscos"] else "") \
                + (f"; impasse {x['impas']}" if x["impas"] else "") + ("; chunk" if x["chunk"] else "") \
                + (f"; reg {x['reg']}" + (f" (+{x['dosi']} %)" if x["reg"] != "no-regar" else "") if cas.get("reg") else "")
            dd.append(f"| {x['cicle']} | {x['sector']} ({CULTIU[x['sector']]}) | {ent} | {_fmt_esperat(x['esperat'])} | {obt} | "
                      f"{'✅' if not x['discrepancies'] else '❌ ' + '; '.join(x['discrepancies'])} |")
        if not ok and cas.get("analisi"):
            dd += ["", f"**Anàlisi de la discrepància** (feta a mà): {cas['analisi']}"]
        dd += ["", "**Explicació que dona el sistema** (fet `explicacio`):", ""]
        for x in files:
            dd.append(f"- Cicle {x['cicle']}, {x['sector']}: {x['explicacio']}")
            if cas.get("reg") and x["explicacio_reg"]:
                dd.append(f"  - Reg: {x['explicacio_reg']}")
        dd += ["", "<details><summary>Traça rellevant del CLIPS</summary>", "", "```"]
        for k, t in traca:
            dd.append(f"--- cicle {k} ---")
            dd += _linies_rellevants(t, sectors)
        dd += ["```", "", "</details>", ""]
        detall += dd
    for cas, ok, n in resum:
        md.append(f"| {cas['id']} | {cas['titol']} | {cas['cobertura']} | {n} | {'✅ correcte' if ok else '❌ discrepància'} |")
    n_ok = sum(ok for _, ok, _ in resum)
    md += ["", f"**{n_ok} de {len(resum)} casos correctes.** Hi ha un cas més amb dades reals de dies que no "
           "es van fer servir durant el desenvolupament: és `escenaris/cas_no_vist_tramuntana.json` "
           "(vegeu el README).", ""] + detall
    with open(os.path.join(d, "CASOS_PROVA.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    for cas, ok, n in resum:
        print(f"{cas['id']} {'OK ' if ok else 'KO '} {cas['titol']}")
    print(f"\n{n_ok}/{len(resum)} casos correctes -> {os.path.join(d, 'CASOS_PROVA.md')}")


if __name__ == "__main__":
    main()
