"""Pont entre Python i el controlador SOAR escrit en CLIPS (clipspy).

Aquest fitxer NO conte coneixement del domini: nomes sap el contracte de memoria
de treball de soar_v1_x.clp (plantilles observacio, prediccio, energia,
estat-sensor, panell, fase, cicle; sortides operador-seleccionat, ordre-actuador,
explicacio, risc, impas, fragment-apres, preferencia).

Un cicle de decisio des de Python:
    1. escriure l'estat dels panells (angle real, angle optim, disponibilitat)
    2. afegir observacio / prediccio / energia del cicle i l'estat dels sensors
    3. passar la fase de 'espera' a 'percepcio' i fer (run)
    4. llegir les ordres, l'explicacio i el que ha passat (impasses, chunks...)
    5. esborrar els fets de cicles vells (el CLIPS mira com a molt 2 cicles enrere)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import clips

SECTORS = ("Sector_1", "Sector_2", "Sector_3")
SENSORS = ("humitat-sol", "pluja", "radiacio", "temperatura-aire", "temperatura-cultiu", "vent")

# Fets lligats a un cicle que el sistema ja no consulta passats 2 cicles.
# (episodi i rl-traca es consulten a c-1 i c-2; epmem-episodi, rl-valor i
#  fragment-apres son memoria a llarg termini i NO s'esborren mai.)
FETS_DE_CICLE = ("observacio", "prediccio", "energia", "risc", "operador", "preferencia",
                 "operador-seleccionat", "impas", "ordre-actuador", "explicacio",
                 "episodi", "rl-traca")
MARGE_NETEJA = 3
SORTIDA_SILENCIADA = False   # paralel.py ho posa a True als processos fills
TIPUS_IMPAS = {"resoldre-dades": "dades-insuficients", "resoldre-empat": "empat",
               "resoldre-sense-candidat": "sense-canvi"}


class _Captura(clips.Router):
    """Captura tot el que el CLIPS escriu (printout t, watch, avisos)."""

    def __init__(self):
        super().__init__("captura-python", 30)
        self.linies: list[str] = []
        self.actiu = True

    def query(self, name):
        return name in ("stdout", "t", "wtrace", "wdisplay", "wwarning", "werror", "wdialog")

    def write(self, name, message):
        if self.actiu:
            self.linies.append(message)

    def buida(self) -> str:
        txt = "".join(self.linies)
        self.linies.clear()
        return txt


def _sym(v):
    """Valor Python -> text CLIPS (numeros com a FLOAT, None com a 'absent')."""
    if v is None:
        return "absent"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return repr(float(v))
    return str(v)


@dataclass
class ResultatCicle:
    cicle: int
    ordres: dict = field(default_factory=dict)        # sector -> (accio, angle)
    seleccionat: dict = field(default_factory=dict)   # sector -> (operador, motiu)
    explicacio: dict = field(default_factory=dict)    # sector -> text
    riscos: dict = field(default_factory=dict)        # sector -> [(tipus, nivell)]
    impasses: list = field(default_factory=list)      # [(tipus, sector)]
    chunks_nous: list = field(default_factory=list)   # [(nom, impas-origen)]
    fonts_pref: dict = field(default_factory=dict)    # sector -> {font, ...} (chunk-*, RL...)
    candidats: dict = field(default_factory=dict)     # sector -> {op: estat}
    rebutjats: dict = field(default_factory=dict)     # sector -> {op}
    regles_disparades: int = 0
    regles: list = field(default_factory=list)        # noms de regles disparades (si watch)
    sortida: str = ""
    fase_final: str = ""


class ControladorCLIPS:
    """Una instancia = un entorn CLIPS independent (memoria i chunks propis)."""

    def __init__(self, fitxer_clp: str, *, reforc: bool | None = None, parelles: bool | None = None,
                 chunking: bool | None = None, epmem: bool | None = None,
                 estrategia: str | None = None, vigila_regles: bool = False,
                 conserva_sortida: bool = False, neteja: bool = True):
        self.fitxer = os.path.abspath(fitxer_clp)
        self.env = clips.Environment()
        self.cap = _Captura()
        self.env.add_router(self.cap)
        self.vigila_regles = vigila_regles
        self.conserva_sortida = conserva_sortida
        self.neteja = neteja
        self._chunks_coneguts: set[str] = set()

        dir_abans = os.getcwd()
        os.chdir(os.path.dirname(self.fitxer))   # el .clp pot carregar fitxers relatius
        try:
            self.env.load(self.fitxer)
        finally:
            os.chdir(dir_abans)
        self._instal_la_funcions()
        self.cap.buida()

        self.env.eval("(set-dynamic-constraint-checking TRUE)")
        if estrategia:
            self.env.eval(f"(set-strategy {estrategia})")
        if vigila_regles:
            self.env.eval("(watch rules)")
        self._interruptors = {"reforc": reforc, "parelles": parelles, "chunking": chunking, "epmem": epmem}
        self.reinicia()

    def reinicia(self):
        """Torna l'entorn a l'estat inicial sense tornar a carregar el .clp (molt mes rapid).
        Compte: les regles creades per chunking NO s'esborren amb (reset); per a execucions
        independents amb chunking, millor crear un ControladorCLIPS nou."""
        self.env.reset()
        self.mecanismes = {}
        for nom, funcio in (("reforc", "REFORC::activa-reforc"), ("parelles", "REFORC::activa-parelles"),
                            ("chunking", "APRENENTATGE::activa-chunking"),
                            ("epmem", "MEMORIA::epmem-aprenentatge")):
            valor = self._interruptors[nom]
            if valor is None:
                continue
            try:
                # activa-chunking espera TRUE/FALSE; la resta, on/off
                arg = ("TRUE" if valor else "FALSE") if nom == "chunking" else ("on" if valor else "off")
                self.env.eval(f"({funcio} {arg})")
                self.mecanismes[nom] = valor
            except clips.CLIPSError:
                # versio sense aquest mecanisme (p. ex. v1_5 no te REFORC)
                self.mecanismes[nom] = None
        # el deffacts de l'escenari porta dades del cicle 1: les treiem, les posa el simulador
        self.env.eval("(PYTHON::py-treu-entrades)")
        self.env.eval("(set-current-module DOMINI)")   # els asserts de Python van a DOMINI
        self.primer = True
        self._chunks_coneguts = set()
        self.cap.buida()

    def __del__(self):
        # En destruir l'entorn, CLIPS de vegades avisa "[ENVRNMNT8] Environment data not fully
        # deallocated" (memoria interna, sobretot de la memoria episodica; inofensiu) i ho escriu
        # directament a la consola. Als processos fills la sortida ja esta silenciada; al proces
        # principal (Linux/Mac) la silenciem nomes durant la destruccio.
        try:
            self.cap.delete()
        except Exception:
            pass
        env = self.__dict__.pop("env", None)
        if env is None:
            return
        if SORTIDA_SILENCIADA or os.name == "nt":
            del env
            return
        try:
            import sys
            sys.stdout.flush()
            sys.stderr.flush()
            nul = os.open(os.devnull, os.O_WRONLY)
            desats = (os.dup(1), os.dup(2))
            os.dup2(nul, 1)
            os.dup2(nul, 2)
            try:
                del env
            finally:
                os.dup2(desats[0], 1)
                os.dup2(desats[1], 2)
                for fd in (*desats, nul):
                    os.close(fd)
        except Exception:
            pass

    # ------------------------------------------------------------------ utilitats
    def _fets(self, plantilla: str):
        return [f for f in self.env.facts() if f.template.name == plantilla]

    def _retracta(self, cond):
        for f in list(self.env.facts()):
            if cond(f):
                f.retract()

    def cicle_actual(self) -> int:
        return int(self._fets("cicle")[0]["numero"])

    def fase(self) -> str:
        fs = self._fets("fase")
        return str(fs[0]["nom"]) if fs else ""

    @staticmethod
    def _py(v):
        """Valor de CLIPS -> tipus Python pur (no ha de quedar cap referencia a l'entorn)."""
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v) if isinstance(v, float) else int(v)
        return str(v)

    def panells(self) -> dict:
        return {str(p["id"]): {k: self._py(p[k]) for k in ("sector", "angle", "angle-optim-produccio",
                                                  "angle-ombra", "disponible", "estat-mecanic",
                                                  "angle-minim", "angle-maxim", "angle-seguretat",
                                                  "vent-avis", "vent-maxim", "tolerancia-angle")}
                for p in self._fets("panell")}

    def llindars(self) -> dict:
        cultiu_sector = {str(s["id"]): str(s["cultiu"]) for s in self._fets("sector")}
        tipus = {str(c["id"]): str(c["tipus"]) for c in self._fets("cultiu")}
        ll = {str(l["tipus"]): {k: float(l[k]) for k in ("temp-optima-min", "temp-optima-max",
                                                          "temp-absoluta-min", "temp-absoluta-max",
                                                          "fraccio-esgotament-p",
                                                          "radiacio-optima-max", "radiacio-estres")}
              for l in self._fets("llindars-cultiu")}
        return {s: {"cultiu": tipus[c], **ll[tipus[c]]} for s, c in cultiu_sector.items()}

    # ------------------------------------------------------------------ entrada
    # Les modificacions es fan amb funcions CLIPS (modul PYTHON) i no amb Fact.modify_slots:
    # modificar fets des de Python i despres tornar-los a recorrer fa que clipspy deixi
    # memoria mal comptada i, en destruir l'entorn, CLIPS ho avisa (ENVRNMNT8) a la consola.
    _FUNCIONS_PY = (
        "(defmodule PYTHON (import DOMINI ?ALL) (export ?ALL))",
        "(deffunction PYTHON::py-panell (?id ?a ?opt ?omb ?disp ?mec)"
        "  (do-for-fact ((?p panell)) (eq ?p:id ?id)"
        "    (modify ?p (angle (if (eq ?a nil) then ?p:angle else ?a))"
        "               (angle-optim-produccio (if (eq ?opt nil) then ?p:angle-optim-produccio else ?opt))"
        "               (angle-ombra (if (eq ?omb nil) then ?p:angle-ombra else ?omb))"
        "               (disponible (if (eq ?disp nil) then ?p:disponible else ?disp))"
        "               (estat-mecanic (if (eq ?mec nil) then ?p:estat-mecanic else ?mec))))"
        "  TRUE)",
        "(deffunction PYTHON::py-treu-entrades ()"
        "  (do-for-all-facts ((?f observacio)) TRUE (retract ?f))"
        "  (do-for-all-facts ((?f prediccio)) TRUE (retract ?f))"
        "  (do-for-all-facts ((?f energia)) TRUE (retract ?f))"
        "  TRUE)",
        "(deffunction PYTHON::py-sensor (?s ?tp ?op ?q ?c)"
        "  (do-for-fact ((?f estat-sensor)) (and (eq ?f:sector ?s) (eq ?f:tipus ?tp))"
        "    (if (eq ?q valida)"
        "     then (modify ?f (operatiu ?op) (qualitat ?q) (cicle-ultima-lectura ?c))"
        "     else (modify ?f (operatiu ?op) (qualitat ?q))))"
        "  TRUE)",
    )

    def _instal_la_funcions(self):
        for codi in self._FUNCIONS_PY:
            self.env.build(codi)
        # py-neteja nomes amb les plantilles que te aquesta versio (p. ex. v1_5 no te rl-traca)
        self.env.eval("(set-current-module DOMINI)")      # les plantilles son de DOMINI
        existents = {t.name for t in self.env.templates()}
        assert "observacio" in existents, "no es troben les plantilles de DOMINI"
        cos = "".join(f"(do-for-all-facts ((?f {t})) (<= ?f:cicle ?limit) (retract ?f))"
                      for t in FETS_DE_CICLE if t in existents)
        self.env.build(
            "(deffunction PYTHON::py-neteja (?limit) " + cos +
            " (do-for-all-facts ((?f traca)) (<= ?f:pas ?limit) (retract ?f))"
            " (do-for-all-facts ((?f subobjectiu)) (eq ?f:estat resolt)"
            "   (bind ?num (str-cat ?f:id))"
            "   (while (neq (str-index \"-\" ?num) FALSE)"
            "     (bind ?num (sub-string (+ (str-index \"-\" ?num) 1) (str-length ?num) ?num)))"
            "   (bind ?n (string-to-field ?num))"
            "   (if (and (integerp ?n) (<= ?n ?limit)) then (retract ?f)))"
            " TRUE)")

    def escriu_panell(self, id_panell: str, **slots):
        ordre = ("angle", "angle-optim-produccio", "angle-ombra", "disponible", "estat-mecanic")
        desconeguts = set(slots) - set(ordre)
        if desconeguts:
            raise KeyError(f"slots de panell no suportats: {desconeguts}")
        vals = []
        for k in ordre:
            v = slots.get(k)
            vals.append("nil" if v is None else (str(v) if isinstance(v, str) else _sym(v)))
        self.env.eval(f"(PYTHON::py-panell {id_panell} {' '.join(vals)})")

    def escriu_sensor(self, sector: str, tipus: str, operatiu: bool, qualitat: str, c: int):
        self.env.eval(f"(PYTHON::py-sensor {sector} {tipus} {'si' if operatiu else 'no'} {qualitat} {int(c)})")

    def afegeix_entrades(self, c: int, sector: str, obs: dict | None, pred: dict | None,
                         energia: dict | None):
        if obs is not None:
            self.env.assert_string(
                f"(observacio (sector {sector}) (cicle {c})"
                f" (radiacio {_sym(obs.get('radiacio'))})"
                f" (temperatura-aire {_sym(obs.get('temperatura-aire'))})"
                f" (temperatura-cultiu {_sym(obs.get('temperatura-cultiu'))})"
                f" (humitat-sol {_sym(obs.get('humitat-sol'))})"
                f" (vent {_sym(obs.get('vent'))})"
                f" (pluja {_sym(obs.get('pluja'))}))")
        if pred is not None:
            self.env.assert_string(
                f"(prediccio (sector {sector}) (cicle {c})"
                f" (radiacio {_sym(pred.get('radiacio'))})"
                f" (temperatura {_sym(pred.get('temperatura'))})"
                f" (vent {_sym(pred.get('vent'))})"
                f" (pluja {_sym(pred.get('pluja'))}))")
        if energia is not None:
            self.env.assert_string(
                f"(energia (sector {sector}) (cicle {c})"
                f" (produccio-actual {_sym(energia['produccio'])})"
                f" (demanda {_sym(energia['demanda'])}))")

    def injecta(self, text_fet: str):
        """Per a proves: afegir un fet arbitrari (p. ex. una preferencia que forci un empat)."""
        self.env.assert_string(text_fet)

    # ------------------------------------------------------------------ execucio
    def executa_cicle(self) -> ResultatCicle:
        c = self.cicle_actual()
        if not self.primer:
            fs = self._fets("fase")
            # Si el cicle anterior no ha acabat a 'espera' (p. ex. una variant amb la salience
            # canviada a l'experiment E11), no aturem la simulacio: l'invariant I6 ja ho registra.
            self.fase_anterior_incorrecta = not (fs and str(fs[0]["nom"]) == "espera")
            for f in fs:
                f.retract()
            self.env.assert_string("(fase (nom percepcio))")
        self.primer = False
        n = self.env.run(100000)   # limit de seguretat contra bucles infinits
        self.env.eval("(set-current-module DOMINI)")
        txt = self.cap.buida()
        res = self._llegeix(c)
        res.regles_disparades = n
        res.fase_final = self.fase()
        if self.vigila_regles:
            res.regles = re.findall(r"FIRE\s+\d+\s+([^:\s]+(?:::[^:\s]+)?):", txt)
        if self.conserva_sortida:
            res.sortida = txt
        if self.neteja:
            self._neteja(c)
        return res

    def _llegeix(self, c: int) -> ResultatCicle:
        r = ResultatCicle(cicle=c)
        for f in self.env.facts():
            t = f.template.name
            if t in ("ordre-actuador", "operador-seleccionat", "explicacio", "risc", "impas",
                     "preferencia", "operador") and int(f["cicle"]) != c:
                continue
            if t == "ordre-actuador":
                r.ordres.setdefault(str(f["sector"]), []).append((str(f["accio"]), float(f["angle-objectiu"])))
            elif t == "operador-seleccionat":
                r.seleccionat.setdefault(str(f["sector"]), []).append((str(f["nom"]), str(f["motiu"])))
            elif t == "explicacio":
                r.explicacio[str(f["sector"])] = str(f["missatge"])
            elif t == "risc":
                r.riscos.setdefault(str(f["sector"]), []).append((str(f["tipus"]), str(f["nivell"])))
            elif t == "subobjectiu":
                # els fets 'impas' es retiren quan es resolen; el subobjectiu queda (id G-<sector>-<cicle>)
                if str(f["id"]).endswith(f"-{c}"):
                    r.impasses.append((TIPUS_IMPAS.get(str(f["tipus"]), str(f["tipus"])), str(f["sector"])))
            elif t == "preferencia":
                r.fonts_pref.setdefault(str(f["sector"]), set()).add((str(f["font"]), str(f["tipus"]), str(f["op"])))
                if str(f["tipus"]) in ("rebuig", "prohibida"):
                    r.rebutjats.setdefault(str(f["sector"]), set()).add(str(f["op"]))
            elif t == "operador":
                r.candidats.setdefault(str(f["sector"]), {})[str(f["nom"])] = str(f["estat"])
            elif t == "fragment-apres":
                nom = str(f["nom"])
                if nom not in self._chunks_coneguts:
                    self._chunks_coneguts.add(nom)
                    r.chunks_nous.append((nom, str(f["impas-origen"])))
        return r

    def _neteja(self, c: int):
        limit = c - MARGE_NETEJA
        if limit >= 1:
            self.env.eval(f"(PYTHON::py-neteja {limit})")

    # ------------------------------------------------------------------ memoria
    def n_fets(self) -> int:
        return len(list(self.env.facts()))

    def coneixement_apres(self) -> dict:
        """Foto del que s'ha apres (per a la verificacio del coneixement que evoluciona)."""
        chunks = [{k: (str(f[k]) if k != "cicle" else int(f[k])) for k in
                   ("nom", "impas-origen", "cicle", "codi", "signatura")}
                  for f in self._fets("fragment-apres")]
        q = [{"tret": str(f["tret"]), "op": str(f["op"]), "q": float(f["q"]), "n": int(f["n"])}
             for f in self._fets("rl-valor")]
        ep = len(self._fets("epmem-episodi"))
        regles_chunk = [str(r) for r in self.env.eval("(get-defrule-list DELIBERACIO)")
                        if str(r).startswith("chunk-")]
        return {"chunks": chunks, "rl": q, "n_epmem": ep, "regles_chunk": regles_chunk}
