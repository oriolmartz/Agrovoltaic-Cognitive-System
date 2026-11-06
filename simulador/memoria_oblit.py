"""Politiques d'oblit de la memòria episòdica per a l'experiment E23."""

from __future__ import annotations

import math
import os
import random


class GestorOblit:
    MODES = {"none", "window", "random", "oldest", "episode_activation", "group_activation",
             "group_unprotected"}

    def __init__(self, config: dict):
        self.mode = config["mode"]
        if self.mode not in self.MODES:
            raise ValueError(f"mode d'oblit desconegut: {self.mode}")
        self.capacitat_max = int(config["capacitat_max"])
        self.capacitat_objectiu = int(config["capacitat_objectiu"])
        self.d = float(config.get("d", 0.5))
        self.gracia = int(config.get("gracia_cicles", 98))
        self.k = int(config.get("k_representatius", 3))
        self.finestra = int(config.get("finestra_cicles", 98))
        self.arxiu = config.get("arxiu", "")
        self.rng = random.Random(int(config.get("llavor", 0)))
        if self.capacitat_max < 1 or not 0 <= self.capacitat_objectiu < self.capacitat_max:
            raise ValueError("capacitat_objectiu ha de ser >= 0 i menor que capacitat_max")
        if self.d <= 0 or self.gracia < 0 or self.k < 0 or self.finestra < 0:
            raise ValueError("d, gracia_cicles, k_representatius i finestra_cicles han de ser vàlids")
        self.usos_grup: dict[tuple, list[int]] = {}
        self.usos_episodi: dict[int, list[int]] = {}
        self.episodis_oblidats = 0
        self.episodis_escanejats = 0
        self.consultes = 0
        self.consultes_encertades = 0
        self.similitud_total = 0.0
        self.similitud_n = 0

    @staticmethod
    def _grup(f):
        return str(f["sector"]), str(f["operador"]), tuple(map(str, f["clau"]))

    @staticmethod
    def _activacio(usos: list[int], cicle: int, d: float) -> float:
        if not usos:
            return float("-inf")
        return math.log(sum(max(1, cicle - t) ** -d for t in usos))

    def aplica(self, fets, env, cicle: int, resultat) -> dict:
        episodis = fets("epmem-episodi")
        per_id = {int(f["id"]): f for f in episodis}
        per_operador: dict[str, int] = {}
        for f in episodis:
            op = str(f["operador"])
            per_operador[op] = per_operador.get(op, 0) + 1

        consultes = [f for f in fets("epmem-consulta")
                     if int(f["cicle"]) == cicle and str(f["tipus"]) == "query"]
        config_index = fets("epmem-config")
        index_actiu = not config_index or str(config_index[0]["index"]) == "si"
        escanejats = 0
        for q in consultes:
            op = next((str(t).removeprefix("operador=") for t in q["requereix"]
                       if str(t).startswith("operador=")), None)
            escanejats += per_operador.get(op, 0) if index_actiu and op else len(episodis)
        self.consultes += len(consultes)
        self.episodis_escanejats += escanejats

        resultats = [f for f in fets("epmem-resultat")
                     if int(f["cicle"]) == cicle and str(f["exit"]) == "si"]
        self.consultes_encertades += len(resultats)
        for f in resultats:
            similitud = float(f["normalitzada"])
            self.similitud_total += similitud
            self.similitud_n += 1
            eid = int(f["memoria-id"])
            record = per_id.get(eid)
            if record is None:
                continue
            self.usos_episodi.setdefault(eid, []).append(cicle)
            self.usos_grup.setdefault(self._grup(record), []).append(cicle)

        claus = {str(f["sector"]): tuple(map(str, f["clau"]))
                 for f in fets("smem-situacio") if int(f["cicle"]) == cicle}
        for sector, fonts in resultat.fonts_pref.items():
            for font, _, op in fonts:
                if font == "AV11-memoria-semantica" and sector in claus:
                    grup = (sector, op, claus[sector])
                    self.usos_grup.setdefault(grup, []).append(cicle)

        abans = len(episodis)
        eliminats = []
        activa_oblit = (self.mode == "window" and abans > self.capacitat_objectiu) or (
            self.mode not in ("none", "window") and abans > self.capacitat_max)
        if activa_oblit:
            resums = {(str(f["sector"]), str(f["operador"]), tuple(map(str, f["situacio"]))): int(f["n"])
                      for f in fets("smem-resum")}
            cfg_smem = fets("smem-config")
            minim = int(cfg_smem[0]["minim-casos"]) if cfg_smem else 3
            sense_proteccions = self.mode == "group_unprotected"
            espera = self.finestra if self.mode == "window" else self.gracia
            elegibles = []
            for f in episodis:
                grup = self._grup(f)
                edat = cicle - int(f["cicle"])
                if resums.get(grup, 0) < minim:
                    continue
                if not sense_proteccions and edat <= espera:
                    continue
                elegibles.append(f)

            if self.mode == "random":
                self.rng.shuffle(elegibles)
            elif self.mode == "oldest" or self.mode == "window":
                elegibles.sort(key=lambda f: (int(f["cicle"]), int(f["id"])))
            elif self.mode == "episode_activation":
                elegibles.sort(key=lambda f: (
                    self._activacio(self.usos_episodi.get(int(f["id"]), []), cicle, self.d),
                    int(f["cicle"]), int(f["id"])))
            else:
                elegibles.sort(key=lambda f: (
                    self._activacio(self.usos_grup.get(self._grup(f), []), cicle, self.d),
                    0 if str(f["valoracio"]) == "neutra" else 1,
                    int(f["cicle"]), int(f["id"])))

            nombre_grup = {}
            informatius_grup = {}
            for f in episodis:
                grup = self._grup(f)
                nombre_grup[grup] = nombre_grup.get(grup, 0) + 1
                if str(f["valoracio"]) in ("bona", "dolenta"):
                    informatius_grup[grup] = informatius_grup.get(grup, 0) + 1

            a_retirar = abans - self.capacitat_objectiu
            for f in elegibles:
                if len(eliminats) >= a_retirar:
                    break
                grup = self._grup(f)
                valoracio = str(f["valoracio"])
                if not sense_proteccions:
                    if valoracio in ("bona", "dolenta"):
                        if informatius_grup.get(grup, 0) <= self.k:
                            continue
                    elif nombre_grup.get(grup, 0) <= self.k:
                        continue
                eliminats.append(f)
                nombre_grup[grup] -= 1
                if valoracio in ("bona", "dolenta"):
                    informatius_grup[grup] -= 1

            ids = ",".join(str(int(f["id"])) for f in eliminats)
            if eliminats and self.arxiu:
                os.makedirs(os.path.dirname(os.path.abspath(self.arxiu)), exist_ok=True)
                with open(self.arxiu, "a", encoding="utf-8") as fitxer:
                    for f in eliminats:
                        fitxer.write(f"{f}\n")
            for f in eliminats:
                self.usos_episodi.pop(int(f["id"]), None)
                f.retract()
            if eliminats:
                env.eval("(MEMORIA::epmem-idx-invalida)")
                self.episodis_oblidats += len(eliminats)

        else:
            ids = ""
        return {
            "n_epmem": len(episodis) - len(eliminats),
            "n_smem": len(fets("smem-resum")),
            "oblidats": len(eliminats),
            "oblidats_total": self.episodis_oblidats,
            "escanejats": escanejats,
            "escanejats_total": self.episodis_escanejats,
            "consultes": len(consultes),
            "encerts": len(resultats),
            "similitud_mitjana": (sum(float(f["normalitzada"]) for f in resultats) / len(resultats)
                                   if resultats else 0.0),
            "ids_oblidats": ids,
            "registre": (f"[OBLIT] cicle={cicle} mode={self.mode} abans={abans} "
                         f"despres={abans - len(eliminats)} ids={ids}\n" if eliminats else ""),
        }

    def foto(self) -> dict:
        return {"epmem_oblidats": self.episodis_oblidats,
                "epmem_oblidats_total": self.episodis_oblidats,
                "epmem_escanejats": self.episodis_escanejats,
                "epmem_escanejats_total": self.episodis_escanejats,
                "epmem_consultes": self.consultes,
                "epmem_consultes_total": self.consultes,
                "epmem_consultes_encertades": self.consultes_encertades,
                "epmem_similitud_mitjana": (self.similitud_total / self.similitud_n
                                            if self.similitud_n else 0.0)}

    def estat(self) -> dict:
        return {"usos_grup": self.usos_grup, "usos_episodi": self.usos_episodi,
                "episodis_oblidats": self.episodis_oblidats,
                "episodis_escanejats": self.episodis_escanejats,
                "consultes": self.consultes, "consultes_encertades": self.consultes_encertades,
                "similitud_total": self.similitud_total, "similitud_n": self.similitud_n}

    def restaura(self, estat: dict):
        self.usos_grup = estat["usos_grup"]
        self.usos_episodi = estat["usos_episodi"]
        self.episodis_oblidats = estat["episodis_oblidats"]
        self.episodis_escanejats = estat["episodis_escanejats"]
        self.consultes = estat["consultes"]
        self.consultes_encertades = estat["consultes_encertades"]
        self.similitud_total = estat["similitud_total"]
        self.similitud_n = estat["similitud_n"]
