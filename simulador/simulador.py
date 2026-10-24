"""Simulador de la planta agrovoltaica per provar el controlador SOAR (CLIPS).

Cada cicle de decisio es una hora. A l'hora h:
  1. el controlador VEU el que han mesurat els sensors l'hora anterior (h-1) i la
     previsio per a l'hora h (valor real + soroll);
  2. decideix i ordena un angle per sector;
  3. els actuadors mouen els panells (o fallen);
  4. el simulador calcula el que PASSA de debo durant l'hora h amb l'angle real:
     energia, llum i temperatura del cultiu, aigua al sol, i si el panell estava
     exposat a una ratxa perillosa.

Us rapid:
    python simulador.py escenaris/dia_normal.json
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

import dades
import fisica
from clips_bridge import SECTORS, SENSORS, ControladorCLIPS
from ontology_loader import carrega_model

ARREL = os.path.dirname(os.path.abspath(__file__))


# ============================================================================ configuracio

def _fusiona(base: dict, extra: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _fusiona(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def ruta_ontologia(cfg: dict) -> str:
    p = cfg["ontologia_model"]
    return p if os.path.isabs(p) else os.path.abspath(os.path.join(ARREL, p))


def ontologia_per_clp(cfg: dict) -> str | None:
    """Les snapshots històriques conserven el seu deffacts original.

    El nucli actiu i les variants experimentals derivades del nucli actiu carreguen RDF.
    """
    clp = os.path.abspath(os.path.join(ARREL, cfg["clp"]))
    if "history" in os.path.normpath(clp).split(os.sep):
        return None
    return ruta_ontologia(cfg)


def carrega_config(escenari: dict | str | None = None) -> dict:
    base = json.load(open(os.path.join(ARREL, "config.json"), encoding="utf-8"))
    if isinstance(escenari, str):
        escenari = json.load(open(escenari, encoding="utf-8"))
    cfg = _fusiona(base, escenari or {})

    # La topologia (sectors i panells) ve de l'ontologia, no del JSON. El JSON
    # nomes aporta parametres fisics de simulacio per a cada sector.
    model = carrega_model(ruta_ontologia(cfg))
    sectors_rdf = set(model.ids_sectors)
    sectors_cfg = set(cfg["sectors"])
    if sectors_cfg != sectors_rdf:
        falten = sorted(sectors_rdf - sectors_cfg)
        sobren = sorted(sectors_cfg - sectors_rdf)
        raise ValueError(f"config.json i ontologia_model.rdf no concorden en sectors: falten={falten}, sobren={sobren}")
    for sid in model.ids_sectors:
        cfg["sectors"][sid]["panells"] = list(model.sectors[sid].panells)
    return cfg


def coneixement_domini(clp: str, ontologia: str | None) -> dict:
    """Coneixement operacional del controlador seleccionat.

    El nucli actiu combina topologia RDF amb llindars CLIPS; una snapshot històrica
    es llegeix exactament com va ser congelada, sense injectar-hi el model nou.
    """
    c = ControladorCLIPS(clp, fitxer_ontologia=ontologia)
    return {"llindars": c.llindars(), "panells": c.panells()}


# ============================================================================ controladors

@dataclass
class Entrada:
    cicle: int
    obs: dict           # sector -> {sensor: valor | None}
    pred: dict          # sector -> {...} | None
    energia: dict       # sector -> {produccio, demanda}
    panells: dict       # id -> {angle, angle-optim-produccio, disponible, estat-mecanic}
    sensors: dict       # sector -> {sensor: True si la lectura ha arribat}


class ControladorSOAR:
    """El sistema basat en regles. Cada instancia te el seu entorn CLIPS."""

    nom = "soar"

    def __init__(self, cfg: dict, domini: dict):
        cc = cfg["controlador"]
        self.clp = os.path.join(ARREL, cfg["clp"])
        self.c = ControladorCLIPS(self.clp, fitxer_ontologia=ontologia_per_clp(cfg),
                                  reforc=cc.get("reforc"), parelles=cc.get("parelles"),
                                  chunking=cc.get("chunking"), epmem=cc.get("epmem"),
                                  estrategia=cc.get("estrategia"),
                                  vigila_regles=cc.get("vigila_regles", False),
                                  conserva_sortida=bool(cfg.get("traca_dir")))
        if cc.get("llavor_clips") is not None:     # per a l'estrategia 'random' de l'agenda
            self.c.env.eval(f"(seed {int(cc['llavor_clips'])})")
        self.domini = domini
        self.primer_cicle = None

    def decideix(self, e: Entrada) -> dict:
        c = self.c
        if self.primer_cicle is None:
            self.primer_cicle = e.cicle
        # El CLIPS porta el seu propi comptador (tanca-cicle). Si no coincideix amb el del
        # simulador, el cicle anterior no s'ha tancat be (nomes passa amb variants trencades,
        # p. ex. a E11): ho registrem com a invariant i fem servir el numero del CLIPS.
        n = c.cicle_actual()
        self._cicle_desquadrat = n != e.cicle
        for pid, p in e.panells.items():
            c.escriu_panell(pid, **p)
        for s in SECTORS:
            for tp in SENSORS:
                ok = e.sensors[s][tp]
                c.escriu_sensor(s, tp, operatiu=True, qualitat="valida" if ok else "absent", c=n)
            c.afegeix_entrades(n, s, e.obs[s], e.pred.get(s), e.energia[s])
        t0 = time.perf_counter()
        r = c.executa_cicle()
        ms = 1000 * (time.perf_counter() - t0)
        out = {}
        for s in SECTORS:
            ordres = r.ordres.get(s, [])
            sel = r.seleccionat.get(s, [])
            fonts = r.fonts_pref.get(s, set())
            out[s] = {
                "accio": ordres[0][0] if ordres else None,
                "angle": ordres[0][1] if ordres else None,
                "motiu": sel[0][1] if sel else "",
                "impas": ",".join(sorted(t for t, ss in r.impasses if ss == s)),
                "us_chunk": any(f.startswith("chunk-") for f, _, _ in fonts),
                "us_rl": any(f == "RL" for f, _, _ in fonts),
                "riscos": ";".join(f"{t}={n}" for t, n in sorted(r.riscos.get(s, []))),
                "invariants": self._invariants(e, r, s),
            }
        out["_cicle"] = {"regles": r.regles_disparades, "ms": ms, "sortida": r.sortida,
                         "chunks_nous": [n for n, _ in r.chunks_nous],
                         "chunks_nous_tipus": [t for _, t in r.chunks_nous],
                         "fase_final": r.fase_final, "fets": c.n_fets(),
                         "regles_noms": r.regles}
        return out

    def _invariants(self, e: Entrada, r, s: str) -> str:
        """Verificacio en temps d'execucio: propietats que s'han de complir SEMPRE."""
        ko = []
        pan = next(p for p in self.domini["panells"].values() if p["sector"] == s)
        if len(r.seleccionat.get(s, [])) != 1:
            ko.append("I1-un-operador")
        if len(r.ordres.get(s, [])) != 1:
            ko.append("I2-una-ordre")
        if r.ordres.get(s):
            acc, ang = r.ordres[s][0]
            if not (pan["angle-minim"] - 1e-6 <= ang <= pan["angle-maxim"] + 1e-6):
                ko.append("I3-limits")
            if acc in r.rebutjats.get(s, set()):
                ko.append("I4-rebutjat")
            v = e.obs[s].get("vent")
            pv = (e.pred.get(s) or {}).get("vent")
            perill = (v is not None and v >= pan["vent-maxim"]) or (pv is not None and pv >= pan["vent-maxim"])
            if perill and acc != "posicio-seguretat":
                ko.append("I7-seguretat-vent")
            if v is None and pv is not None and pv >= pan["vent-avis"] and acc != "posicio-seguretat":
                ko.append("I8-previsio-sense-sensor")
        if s not in r.explicacio:
            ko.append("I5-explicacio")
        if r.fase_final != "espera":
            ko.append("I6-fase")
        if getattr(self, "_cicle_desquadrat", False):
            ko.append("I9-cicle-no-tancat")
        return ",".join(ko)

    def coneixement(self) -> dict:
        return self.c.coneixement_apres()


class _Basic:
    """Controladors de referencia (sense regles): mateixa interficie que SOAR."""

    nom = "basic"

    def __init__(self, cfg, domini):
        self.domini = domini

    def angle(self, s, e: Entrada, pan) -> tuple[str, float]:
        raise NotImplementedError

    def decideix(self, e: Entrada) -> dict:
        out = {}
        for s in SECTORS:
            pid = next(k for k, p in self.domini["panells"].items() if p["sector"] == s)
            pan = {**self.domini["panells"][pid], **e.panells[pid]}
            acc, ang = self.angle(s, e, pan)
            out[s] = {"accio": acc, "angle": ang, "motiu": self.nom, "impas": "", "us_chunk": False,
                      "us_rl": False, "riscos": "", "invariants": ""}
        out["_cicle"] = {"regles": 0, "ms": 0.0, "chunks_nous": [], "chunks_nous_tipus": [],
                         "fase_final": "", "fets": 0, "regles_noms": []}
        return out

    def coneixement(self):
        return {}


class SeguidorEstandard(_Basic):
    """El que fa un seguidor comercial: segueix el sol i va a seguretat amb ratxa >= vent-maxim
    (o si perd el sensor de vent: mode a prova de fallades)."""

    nom = "seguidor"

    def angle(self, s, e, pan):
        v = e.obs[s].get("vent")
        if v is None or v >= pan["vent-maxim"]:
            return "posicio-seguretat", pan["angle-seguretat"]
        return "orientar-produccio", pan["angle-optim-produccio"]


class PanellFix(_Basic):
    nom = "fix"

    def angle(self, s, e, pan):
        return "mantenir-posicio", 0.0


CONTROLADORS = {"soar": ControladorSOAR, "seguidor": SeguidorEstandard, "fix": PanellFix}


# ============================================================================ simulacio

class Simulacio:
    def __init__(self, cfg: dict, llavor: int = 0, domini: dict | None = None):
        self.cfg = cfg
        self.rng = np.random.default_rng(llavor)
        self.llavor = llavor
        self.lloc = dades.LLOCS[cfg["lloc"]]
        self.meteo = dades.carrega(cfg["lloc"])
        self.ratio = dades.ratio_pvgis(cfg["lloc"])
        self.domini = domini or coneixement_domini(os.path.join(ARREL, cfg["clp"]), ontologia_per_clp(cfg))
        self.ll = self.domini["llindars"]
        self.pan0 = self.domini["panells"]
        sc = cfg["sectors"]
        self.taw = {s: fisica.taw_mm(self.lloc.theta_cc, self.lloc.theta_pm, sc[s]["zr_m"]) for s in SECTORS}
        self._reinicia_planta()

    # ------------------------------------------------------------------ estat
    def _reinicia_planta(self):
        hcfg = self.cfg["humitat"]
        self.angle = {pid: 0.0 for pid in self.pan0}                # angle real de cada panell
        self.aigua_mm = {s: self.taw[s] * hcfg["inicial_pct"] / 100 for s in SECTORS}
        self.ultima = None                                          # l'hora anterior (el que veuen els sensors)
        self.cicle = 1

    def _fila(self, t: pd.Timestamp) -> dict:
        m = self.cfg["modificadors"]
        f = self.meteo.loc[t]
        return {"temp": float(f["temp"]) + m["temp_delta"], "vent": float(f["vent"]) * m["vent_factor"],
                "ghi": max(0.0, float(f["ghi"]) * m["rad_factor"]), "pluja": float(f["pluja"]) * m["pluja_factor"],
                "et0": float(f["et0"]), "aigua_xms": float(f["aigua_pct"]) if not math.isnan(f["aigua_pct"]) else None}

    def _aigua_pct(self, s, fila=None):
        if self.cfg["humitat"]["mode"] == "mesurada" and fila is not None and fila["aigua_xms"] is not None:
            return fila["aigua_xms"]
        return 100.0 * self.aigua_mm[s] / self.taw[s]

    def _angle_sector(self, s):
        ps = self.cfg["sectors"][s]["panells"]
        return sum(self.angle[p] for p in ps) / len(ps)

    # ------------------------------------------------------------------ una hora fisica (sense decisio)
    def _hora_fisica(self, t, fila, s_angles=None) -> dict:
        """Avanca l'estat de la planta una hora amb els angles actuals. Retorna el que ha passat."""
        lat, lon = self.lloc.lat, self.lloc.lon
        elev, az = fisica.sol_interval(lat, lon, t.to_pydatetime())
        opt = fisica.angle_seguiment(elev, az)
        out = {"angle_optim": opt, "sectors": {}}
        hcfg = self.cfg["humitat"]
        for s in SECTORS:
            sc = self.cfg["sectors"][s]
            a = self._angle_sector(s)
            tau = fisica.transmissio(a, sc["gcr"])
            rad_c = fila["ghi"] * tau
            p = fisica.produccio_kw(fila["ghi"], a, opt, sc["kwp"], self.ratio)
            p_opt = fisica.produccio_kw(fila["ghi"], opt, opt, sc["kwp"], self.ratio)
            aigua_abans = self._aigua_pct(s, fila)
            mod = self.cfg.get("model", {})
            t_c = fisica.temperatura_cultiu(fila["temp"], rad_c, aigua_abans,
                                            k_rad=mod.get("k_rad", 0.006), k_sec=mod.get("k_sec", 2.0))
            if hcfg["mode"] == "balanc":
                self.aigua_mm[s] = fisica.pas_balanc_hidric(self.aigua_mm[s], self.taw[s], fila["et0"],
                                                            sc["kc"], fila["pluja"], tau, sc["gcr"])
                reg = hcfg["reg"]
                if reg["actiu"] and t.hour == reg["hora"] and self._aigua_pct(s) < reg["llindar_pct"]:
                    self.aigua_mm[s] = self.taw[s] * reg["fins_pct"] / 100
            out["sectors"][s] = {"angle": a, "rad_cultiu": rad_c, "t_cultiu": t_c, "P_kw": p,
                                 "P_opt_kw": p_opt, "aigua_pct": self._aigua_pct(s, fila)}
        return out

    # ------------------------------------------------------------------ percepcio (el que veu el controlador)
    def _sensors(self, s):
        sc = self.cfg["sensors"]
        ok = {tp: bool(self.rng.random() >= sc["p_absent"].get(tp, 0.0)) for tp in SENSORS}
        for f in sc["forcats"]:
            if f.get("sector", s) == s and f["des_de_cicle"] <= self.cicle <= f.get("fins_a_cicle", f["des_de_cicle"]):
                ok[f["sensor"]] = False
        return ok

    def _entrada(self, t, fila) -> Entrada:
        sn = self.cfg["soroll"]
        prev = self.ultima
        opt_ara = fisica.angle_seguiment(*fisica.sol_interval(self.lloc.lat, self.lloc.lon, t.to_pydatetime()))
        obs, pred, ene, sens = {}, {}, {}, {}
        for s in SECTORS:
            sc = self.cfg["sectors"][s]
            ok = self._sensors(s)
            sens[s] = ok
            ps = prev["sectors"][s] if prev else None
            pf = prev["fila"] if prev else fila
            o = {
                "radiacio": max(0.0, (ps["rad_cultiu"] if ps else pf["ghi"]) * (1 + self.rng.normal(0, sn["sensor_rad_sigma"]))),
                "temperatura-aire": pf["temp"] + self.rng.normal(0, sn["sensor_temp_sigma"]),
                "temperatura-cultiu": (ps["t_cultiu"] if ps else pf["temp"]) + self.rng.normal(0, sn["sensor_temp_sigma"]),
                "humitat-sol": self._aigua_pct(s, fila),
                "vent": max(0.0, pf["vent"] + self.rng.normal(0, sn["sensor_vent_sigma"])),
                "pluja": pf["pluja"],
            }
            obs[s] = {k: (round(v, 2) if ok[k] else None) for k, v in o.items()}
            if self.rng.random() < self.cfg["sensors"]["p_previsio_absent"]:
                pred[s] = None
            else:
                lnv = lambda sig: float(np.exp(self.rng.normal(0, sig)))
                pred[s] = {"radiacio": round(fila["ghi"] * lnv(sn["previsio_rad_sigma"]), 1),
                           "temperatura": round(fila["temp"] + self.rng.normal(0, sn["previsio_temp_sigma"]), 1),
                           "vent": round(fila["vent"] * lnv(sn["previsio_vent_sigma"]), 1),
                           "pluja": round(fila["pluja"], 1)}
            hora = t.hour - 0.5
            ene[s] = {"produccio": round(ps["P_kw"], 2) if ps else 0.0,
                      "demanda": round(fisica.demanda_kw(hora, sc["demanda_base_kw"], sc["demanda_pic_kw"]), 2)}
        panells = {}
        for pid in self.pan0:
            s = self.pan0[pid]["sector"]
            disp, mec = "si", "normal"
            if self.cfg["actuadors"]["informa_avaria"] and self._panell_avariat(pid):
                disp, mec = "no", "avariat"
            panells[pid] = {"angle": round(self.angle[pid], 2), "angle-optim-produccio": round(opt_ara, 1),
                            "disponible": disp, "estat-mecanic": mec}
        return Entrada(self.cicle, obs, pred, ene, panells, sens)

    # ------------------------------------------------------------------ actuadors
    def _panell_avariat(self, pid):
        for f in self.cfg["actuadors"]["fallades"]:
            if f["panell"] == pid and f["des_de_cicle"] <= self.cicle <= f.get("fins_a_cicle", 10**9):
                return True
        return False

    def _actua(self, decisio):
        moviment = {}
        for pid, p0 in self.pan0.items():
            s = p0["sector"]
            objectiu = decisio[s]["angle"]
            abans = self.angle[pid]
            if objectiu is None or self._panell_avariat(pid) or self.rng.random() < self.cfg["actuadors"]["p_fallada"]:
                nou = abans
            else:
                nou = max(p0["angle-minim"], min(p0["angle-maxim"], float(objectiu)))
            self.angle[pid] = nou
            moviment[pid] = abs(nou - abans)
        return moviment

    # ------------------------------------------------------------------ bucle
    def executa(self, dies: list[str], controlador=None, fabrica=None, etiqueta: str = "") -> pd.DataFrame:
        """Simula una llista de dies. mode_dies='independents' crea un controlador nou cada dia
        (cada dia es una repeticio independent); 'sequencial' en fa servir un per a tots (aprenentatge)."""
        h0, h1 = self.cfg["hores"]
        fabrica = fabrica or CONTROLADORS[self.cfg["controlador"]["tipus"]]
        independents = self.cfg["mode_dies"] == "independents"
        files, self.fotos = [], []
        ctrl = controlador
        for dia in dies:
            if independents or ctrl is None:
                if independents:
                    self._reinicia_planta()      # planta i comptador de cicles nous
                ctrl = fabrica(self.cfg, self.domini)
            # Soroll propi de cada dia: llavor + data. Aixi cada dia te fallades i soroll diferents,
            # pero el mateix dia amb la mateixa llavor es identic per a tots els controladors
            # (disseny aparellat) i no depen de l'ordre ni de com es reparteixen les feines.
            self.rng = np.random.default_rng([self.llavor, int(dia.replace("-", ""))])
            traca = self._obre_traca(dia, etiqueta, ctrl)
            # nit anterior: el sol s'asseca (balanc) fins a l'hora d'inici
            ts = pd.date_range(f"{dia} 00:00", f"{dia} 23:00", freq="h")
            for t in ts:
                if t not in self.meteo.index:
                    continue
                fila = self._fila(t)
                if not (h0 <= t.hour <= h1):
                    fis = self._hora_fisica(t, fila)
                    self.ultima = {"fila": fila, **fis}
                    continue
                ent = self._entrada(t, fila)
                dec = ctrl.decideix(ent)
                if traca:
                    self._escriu_traca(traca, t, ent, dec)
                mov = self._actua(dec)
                fis = self._hora_fisica(t, fila)
                files += self._registres(dia, t, fila, ent, dec, fis, mov, ctrl, etiqueta)
                self.ultima = {"fila": fila, **fis}
                self.cicle += 1
            if traca:
                traca.close()
            if hasattr(ctrl, "coneixement"):
                self.fotos.append({"dia": dia, "cicle": self.cicle, **ctrl.coneixement()})
        return pd.DataFrame(files)

    # ------------------------------------------------------------------ traca del CLIPS
    def _obre_traca(self, dia, etiqueta, ctrl):
        """Un fitxer de text per dia amb tot el que escriu el CLIPS (com run_soar)."""
        d = self.cfg.get("traca_dir")
        if not d or not isinstance(ctrl, ControladorSOAR):
            return None
        os.makedirs(d, exist_ok=True)
        nom = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in (etiqueta or "simulacio"))
        f = open(os.path.join(d, f"{nom}_{dia}_llavor{self.llavor}.txt"), "w", encoding="utf-8")
        f.write(f"# Traca del CLIPS ({os.path.basename(self.cfg['clp'])}) - {etiqueta} - {dia} - "
                f"{self.lloc.nom} - llavor {self.llavor}\n")
        return f

    def _escriu_traca(self, f, t, ent, dec):
        f.write("\n" + "#" * 78 + "\n")
        f.write(f"# {t:%Y-%m-%d %H:%M}  CICLE {ent.cicle}\n")
        for s in SECTORS:
            o = ent.obs[s]
            p = ent.pred.get(s) or {}
            f.write(f"#   {s} entrada: vent={o['vent']} (previsio {p.get('vent')}) radiacio={o['radiacio']} "
                    f"temp-cultiu={o['temperatura-cultiu']} humitat={o['humitat-sol']}\n")
        f.write("#" * 78 + "\n")
        f.write(dec["_cicle"].get("sortida", ""))

    def _registres(self, dia, t, fila, ent, dec, fis, mov, ctrl, etiqueta):
        files = []
        info = dec["_cicle"]
        for s in SECTORS:
            pan = next(p for p in self.pan0.values() if p["sector"] == s)
            ll = self.ll[s]
            fs = fis["sectors"][s]
            d = dec[s]
            estowat = abs(fs["angle"] - pan["angle-seguretat"]) <= pan["tolerancia-angle"]
            files.append({
                "etiqueta": etiqueta, "controlador": ctrl.nom, "llavor": self.llavor, "lloc": self.cfg["lloc"],
                "dia": dia, "hora": t.hour, "cicle": ent.cicle, "sector": s, "cultiu": ll["cultiu"],
                "accio": d["accio"], "angle_ordre": d["angle"], "angle_real": fs["angle"],
                "angle_optim": fis["angle_optim"],
                "moviment": sum(mov[p] for p in self.cfg["sectors"][s]["panells"]) / 2,
                "ghi": fila["ghi"], "temp_aire": fila["temp"], "vent_real": fila["vent"],
                "vent_obs": ent.obs[s]["vent"], "vent_prev": (ent.pred.get(s) or {}).get("vent"),
                "sensors_absents": ",".join(k for k, v in ent.sensors[s].items() if not v),
                "P_kw": fs["P_kw"], "P_opt_kw": fs["P_opt_kw"], "demanda_kw": ent.energia[s]["demanda"],
                "rad_cultiu": fs["rad_cultiu"], "t_cultiu": fs["t_cultiu"], "aigua_pct": fs["aigua_pct"],
                "estres_rad": fs["rad_cultiu"] > ll["radiacio-estres"],
                "estres_calor": fs["t_cultiu"] > ll["temp-optima-max"],
                "calor_critica": fs["t_cultiu"] > ll["temp-absoluta-max"],
                "estres_aigua": fs["aigua_pct"] < 100 * (1 - ll["fraccio-esgotament-p"]),
                "violacio_seguretat": (fila["vent"] >= pan["vent-maxim"]) and not estowat,
                "exposicio_vent": (fila["vent"] >= pan["vent-avis"]) and not estowat,
                "riscos": d["riscos"], "impas": d["impas"], "us_chunk": d["us_chunk"], "us_rl": d["us_rl"],
                "motiu": d["motiu"], "invariants_ko": d["invariants"],
                "chunks_nous": len(info["chunks_nous"]) if s == SECTORS[0] else 0,
                "regles": info["regles"] if s == SECTORS[0] else 0,
                "ms": info["ms"] if s == SECTORS[0] else 0.0,
                "fets_mt": info["fets"],
            })
        return files


# ============================================================================ seleccio de dies

def selecciona_dies(cfg: dict, n: int | None = None, llavor: int = 0, filtre=None) -> list[str]:
    """Dies disponibles (opcionalment filtrats) i, si n, una mostra aleatoria reproduible."""
    dies = dades.dies_disponibles(cfg["lloc"])
    if "dies" in cfg:
        d = cfg["dies"]
        if isinstance(d, dict):
            dies = [x for x in dies if d.get("des_de", "0") <= x <= d.get("fins_a", "9")]
        else:
            dies = [x for x in d if x in dies]
    if filtre is not None:
        met = dades.carrega(cfg["lloc"])
        dies = [x for x in dies if filtre(met.loc[x])]
    if n is not None and n < len(dies):
        rng = np.random.default_rng(llavor)
        dies = sorted(rng.choice(dies, size=n, replace=False).tolist())
    return dies


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("escenari", nargs="?", help="fitxer JSON d'escenari (opcional)")
    ap.add_argument("--controlador", choices=list(CONTROLADORS), help="sobreescriu el de l'escenari")
    ap.add_argument("--dies", type=int, help="nombre de dies (mostra aleatoria)")
    ap.add_argument("--llavor", type=int, default=0)
    ap.add_argument("--sortida", help="CSV de resultats (per defecte resultats/simulacions/<escenari>.csv)")
    ap.add_argument("--sense-traca", action="store_true", help="no desis la traca del CLIPS")
    a = ap.parse_args()
    cfg = carrega_config(a.escenari)
    nom = os.path.splitext(os.path.basename(a.escenari or "per_defecte"))[0]
    dir_sim = os.path.join(ARREL, "resultats", "simulacions")
    if not a.sense_traca:
        cfg["traca_dir"] = os.path.join(dir_sim, "traca")
    if a.controlador:
        cfg["controlador"]["tipus"] = a.controlador
    dies = selecciona_dies(cfg, a.dies, a.llavor)
    sim = Simulacio(cfg, a.llavor)
    df = sim.executa(dies, etiqueta=cfg.get("nom", ""))
    sortida = a.sortida or os.path.join(dir_sim, f"{nom}_{cfg['controlador']['tipus']}.csv")
    os.makedirs(os.path.dirname(sortida), exist_ok=True)
    df.to_csv(sortida, index=False)
    import metriques
    print(metriques.resum(df).to_string())
    print(f"\n{len(df)} registres -> {sortida}")
    if cfg.get("traca_dir") and cfg["controlador"]["tipus"] == "soar":
        print(f"Traca del CLIPS -> {cfg['traca_dir']}")


if __name__ == "__main__":
    main()
