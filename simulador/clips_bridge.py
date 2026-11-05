"""Pont entre Python i el controlador SOAR escrit en CLIPS (clipspy).

Aquest fitxer NO conte regles de decisio del domini: coneix el contracte de memoria
de treball i delega la projeccio RDF a ontology_loader.py (plantilles observacio, prediccio, energia,
estat-sensor, panell, fase, cicle; sortides operador-seleccionat, ordre-actuador,
explicacio, risc, impas, fragment-apres, preferencia). A partir de v1_9, tambe
l'entrada 'moment' (hora del cicle) i les sortides ordre-reg i explicacio-reg.

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

from ontology_loader import ONTOLOGIA_MODEL_DEFECTE, carrega_model, injecta_model

# La topologia no es duplica en Python: es deriva de l'ontologia de model.
_MODEL_DEFECTE = carrega_model(ONTOLOGIA_MODEL_DEFECTE)
SECTORS = _MODEL_DEFECTE.ids_sectors
SENSORS = _MODEL_DEFECTE.tipus_sensors

# Fets lligats a un cicle que el sistema ja no consulta passats 2 cicles.
# (episodi i rl-traca es consulten a c-1 i c-2; epmem-episodi, rl-valor i
#  fragment-apres son memoria a llarg termini i NO s'esborren mai.)
FETS_DE_CICLE = ("observacio", "prediccio", "energia", "risc", "operador", "preferencia",
                 "operador-seleccionat", "impas", "ordre-actuador", "explicacio",
                 "episodi", "rl-traca", "smem-situacio",
                 # v1_9: decisio de reg
                 "moment", "necessitat-reg", "operador-reg", "preferencia-reg", "reg-seleccionat",
                 "ordre-reg", "explicacio-reg",
                 # iteracio 35: lectures no fiables i comprovacio del reg
                 "lectura-estimada", "lectura-incoherent", "reg-pendent")
MARGE_NETEJA = 3
LIMIT_REGLES = 100000   # si s'hi arriba, el cicle no ha acabat (bucle de regles)
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
    reg: dict = field(default_factory=dict)           # sector -> [(accio, dosi %, motiu)]   (v1_9)
    reg_explicacio: dict = field(default_factory=dict)
    reg_rebutjats: dict = field(default_factory=dict)  # sector -> {op}
    consultes_epmem: dict = field(default_factory=dict)  # sector -> consultes a la memoria episodica
    n_epmem: int = 0                                  # episodis a la memoria de treball
    n_smem: int = 0                                   # resums de la memoria semantica
    regles_disparades: int = 0
    regles: list = field(default_factory=list)        # noms de regles disparades (si watch)
    sortida: str = ""
    fase_final: str = ""


class ControladorCLIPS:
    """Una instancia = un entorn CLIPS independent (memoria i chunks propis)."""

    def __init__(self, fitxer_clp: str, *, fitxer_ontologia: str | None = None,
                 reforc: bool | None = None, parelles: bool | None = None,
                 chunking: bool | None = None, epmem: bool | None = None,
                 smem: bool | None = None, smem_finestra: int = 0, smem_arxiu: str = "",
                 estrategia: str | None = None, vigila_regles: bool = False,
                 conserva_sortida: bool = False, neteja: bool = True):
        self.fitxer = os.path.abspath(fitxer_clp)
        # Per compatibilitat, el CLP actiu usa automàticament l'ontologia de model.
        # Les snapshots historiques no la reben: així E1 continua reproduint-les tal com eren.
        if fitxer_ontologia is None and os.path.basename(self.fitxer) == "soar.clp" and "clips_core" in os.path.normpath(self.fitxer).split(os.sep):
            fitxer_ontologia = str(ONTOLOGIA_MODEL_DEFECTE)
        self.fitxer_ontologia = os.path.abspath(fitxer_ontologia) if fitxer_ontologia else None
        self.model_ontologic = carrega_model(self.fitxer_ontologia) if self.fitxer_ontologia else None
        self.env = clips.Environment()
        self.cap = _Captura()
        self._plantilles = None   # nom -> MODUL::nom, per a _fets
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
        self._smem = (smem, int(smem_finestra or 0), smem_arxiu or "")
        self.reinicia()

    def reinicia(self):
        """Torna l'entorn a l'estat inicial sense tornar a carregar el .clp (molt mes rapid).
        Compte: les regles creades per chunking NO s'esborren amb (reset); per a execucions
        independents amb chunking, millor crear un ControladorCLIPS nou."""
        self.env.reset()
        # La topologia estàtica del model (sectors, cultius, panells i sensors)
        # prové del RDF, no d'un deffacts duplicat.
        if self.model_ontologic is not None:
            injecta_model(self.env, self.model_ontologic)
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
        smem, finestra, arxiu = self._smem
        if smem is not None:
            try:
                self.env.eval(f'(SEMANTICA::smem-configura {"on" if smem else "off"} {finestra} "{arxiu}")')
                self.mecanismes["smem"] = smem
            except clips.CLIPSError:
                self.mecanismes["smem"] = None   # versio sense memoria semantica
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
        """Fets d'una plantilla, en l'ordre de la llista de fets. Es demana al CLIPS nomes la plantilla
        (GetNextFactInTemplate) en lloc de recorrer tots els fets des de Python: amb milers d'episodis de
        memoria episodica, recorrer-los tots a cada consulta era el que feia lent el simulador (E16)."""
        if self._plantilles is None:
            self._plantilles = {}
            for q in self.env.eval("(get-deftemplate-list *)"):
                self._plantilles.setdefault(str(q).rpartition("::")[2], self.env.find_template(str(q)))
        t = self._plantilles.get(plantilla)
        return list(t.facts()) if t is not None else []

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
        self.te_reg = "ordre-reg" in existents          # v1_9: el sistema tambe decideix el reg
        # fase fenologica i sensibilitat del cultiu (dades del calendari de cultiu del simulador)
        self.te_fase = "cultiu" in existents and any(
            sl.name == "fase" for sl in self.env.find_template("cultiu").slots)
        if self.te_fase:
            self.env.build(
                "(deffunction PYTHON::py-cultiu (?s ?fase ?sens)"
                "  (do-for-fact ((?x sector)) (eq ?x:id ?s)"
                "    (do-for-fact ((?k cultiu)) (eq ?k:id ?x:cultiu)"
                "      (if (or (neq ?k:fase ?fase) (neq ?k:sensibilitat ?sens))"
                "       then (modify ?k (fase ?fase) (sensibilitat ?sens)))))"
                "  TRUE)")
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

    def escriu_cultiu(self, sector: str, fase: str, sensibilitat: str):
        """Fase fenologica i sensibilitat del cultiu del sector (calendari de cultiu)."""
        if self.te_fase:
            self.env.eval(f"(PYTHON::py-cultiu {sector} {fase} {sensibilitat})")

    def escriu_moment(self, c: int, hora: int):
        """Hora local del cicle (nomes les versions amb reg la fan servir)."""
        if self.te_reg:
            self.env.assert_string(f"(moment (cicle {int(c)}) (hora {int(hora)}))")

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
        n = self.env.run(LIMIT_REGLES)   # limit de seguretat contra bucles infinits
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

    LLEGITS = ("ordre-actuador", "operador-seleccionat", "explicacio", "risc", "subobjectiu", "preferencia",
               "operador", "ordre-reg", "explicacio-reg", "preferencia-reg", "fragment-apres", "epmem-consulta")

    def _llegeix(self, c: int) -> ResultatCicle:
        r = ResultatCicle(cicle=c)
        # cada plantilla omple les seves pròpies estructures: llegir-les plantilla per plantilla dona el
        # mateix resultat que recorrer tota la llista de fets
        for f in (f for t in self.LLEGITS for f in self._fets(t)):
            t = f.template.name
            if t in ("ordre-actuador", "operador-seleccionat", "explicacio", "risc", "impas",
                     "preferencia", "operador", "ordre-reg", "explicacio-reg",
                     "preferencia-reg") and int(f["cicle"]) != c:
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
            elif t == "ordre-reg":
                r.reg.setdefault(str(f["sector"]), []).append((str(f["accio"]), float(f["dosi"]), str(f["motiu"])))
            elif t == "explicacio-reg":
                r.reg_explicacio[str(f["sector"])] = str(f["missatge"])
            elif t == "preferencia-reg":
                if str(f["tipus"]) == "rebuig":
                    r.reg_rebutjats.setdefault(str(f["sector"]), set()).add(str(f["op"]))
            elif t == "epmem-consulta":
                if int(f["cicle"]) == c and str(f["tipus"]) == "query":
                    r.consultes_epmem[str(f["sector"])] = r.consultes_epmem.get(str(f["sector"]), 0) + 1
            elif t == "fragment-apres":
                nom = str(f["nom"])
                if nom not in self._chunks_coneguts:
                    self._chunks_coneguts.add(nom)
                    r.chunks_nous.append((nom, str(f["impas-origen"])))
        # la memoria pot tenir desenes de milers d'episodis: es compten al CLIPS, no des de Python
        r.n_epmem, r.n_smem = self.compta("epmem-episodi"), self.compta("smem-resum")
        return r

    def compta(self, plantilla: str) -> int:
        """Nombre de fets d'una plantilla de DOMINI, comptat dins del CLIPS."""
        if self._plantilles is None:
            self._fets(plantilla)
        if plantilla not in self._plantilles:
            return 0
        m = self.env.eval("(get-current-module)")
        self.env.eval("(set-current-module DOMINI)")
        n = int(self.env.eval(f"(length$ (find-all-facts ((?f {plantilla})) TRUE))"))
        self.env.eval(f"(set-current-module {m})")
        return n

    def _neteja(self, c: int):
        limit = c - MARGE_NETEJA
        if limit >= 1:
            self.env.eval(f"(PYTHON::py-neteja {limit})")

    # ------------------------------------------------------------------ punts de control
    # Per a execucions mes llargues que el temps que pot durar un proces (E16: dos anys seguits).
    # Es desa tot l'estat del CLIPS (fets en ordre, regles apreses i defglobals) i es restaura sobre
    # un controlador nou. Es comprova a verificacio/prova_punt_control.py que el resultat es identic.
    def desa_estat(self) -> dict:
        fets = []
        for f in sorted(self.env.facts(), key=lambda f: f.index):
            assert not f.template.implied, f"fet ordenat sense plantilla: {f}"
            # valors de Python (Symbol, str, int, float, tuple): str(f) no escapa les cometes
            fets.append((f"{f.template.module.name}::{f.template.name}", dict(f)))
        # env.rules() nomes veu el modul actual: les regles apreses son a DELIBERACIO
        regles = [str(self.env.find_rule(f"DELIBERACIO::{r}"))
                  for r in self.env.eval("(get-defrule-list DELIBERACIO)") if str(r).startswith("chunk-")]
        assert len(regles) == len(self._fets("fragment-apres")), "no es troben totes les regles apreses"
        glob = []
        for nom in self.env.eval("(get-defglobal-list *)"):
            v = self.env.find_global(str(nom)).value
            glob.append((str(nom), "sym" if isinstance(v, clips.Symbol) else type(v).__name__, str(v)))
        return {"fets": fets, "regles": regles, "globals": glob, "primer": self.primer,
                "chunks_coneguts": sorted(self._chunks_coneguts), "mecanismes": dict(self.mecanismes),
                "modul": str(self.env.eval("(get-current-module)")),
                "focus": [str(m) for m in self.env.eval("(get-focus-stack)")]}

    def restaura_estat(self, est: dict):
        for f in list(self.env.facts()):
            f.retract()
        plantilles = {}
        for nom, slots in est["fets"]:
            if nom not in plantilles:
                plantilles[nom] = self.env.find_template(nom)
            plantilles[nom].assert_fact(**slots)
        self.env.eval("(set-current-module DELIBERACIO)")
        for r in est["regles"]:
            self.env.build(r)
        conv = {"sym": clips.Symbol, "int": int, "float": float, "str": str}
        for nom, tipus, v in est["globals"]:
            self.env.find_global(nom).value = conv.get(tipus, clips.Symbol)(v)
        self.primer = est["primer"]
        self._chunks_coneguts = set(est["chunks_coneguts"])
        self.mecanismes = dict(est["mecanismes"])
        # en restaurar, les regles auto-focus apilen moduls al focus: es deixa com estava
        self.env.eval("(clear-focus-stack)")
        for m in reversed(est["focus"]):
            self.env.eval(f"(focus {m})")
        self.env.eval(f"(set-current-module {est['modul']})")
        self.cap.buida()

    # ------------------------------------------------------------------ memoria
    def n_fets(self) -> int:
        return int(self.env.eval("(length$ (get-fact-list *))"))

    def coneixement_apres(self) -> dict:
        """Foto del que s'ha apres (per a la verificacio del coneixement que evoluciona)."""
        chunks = [{k: (str(f[k]) if k != "cicle" else int(f[k])) for k in
                   ("nom", "impas-origen", "cicle", "codi", "signatura")}
                  for f in self._fets("fragment-apres")]
        q = [{"tret": str(f["tret"]), "op": str(f["op"]), "q": float(f["q"]), "n": int(f["n"])}
             for f in self._fets("rl-valor")]
        ep = self.compta("epmem-episodi")
        regles_chunk = [str(r) for r in self.env.eval("(get-defrule-list DELIBERACIO)")
                        if str(r).startswith("chunk-")]
        return {"chunks": chunks, "rl": q, "n_epmem": ep, "n_smem": self.compta("smem-resum"),
                "regles_chunk": regles_chunk}
