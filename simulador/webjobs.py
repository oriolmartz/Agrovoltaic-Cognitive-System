"""Simulacions llargues (mesos) en segon pla, en processos, amb progres i cancel·lacio.

Un treball es reparteix en tasques (un controlador i una llista de dies) que s'executen en
processos fills (`spawn`, tambe a Windows). Cada tasca desa el seu resultat en un pickle; en
acabar tot, el pare agrega una taula DIARIA (el que viatja al navegador) i guarda els registres
horaris, que el navegador demana dia a dia. Aixi la web escala amb el nombre de dies.

Modes (el que es reparteix entre processos):
  independents  cada dia comença de nou (disseny dels experiments E1-E7): tros de dies, en paral·lel
  mensual       un bloc continu per mes natural (disseny d'E14/E15): un bloc per proces, en paral·lel
  sequencial    una sola execucio continua per controlador (l'aigua i l'aprenentatge passen de dia en dia)
"""

from __future__ import annotations

import math
import multiprocessing as mp
import os
import shutil
import tempfile
import threading
import time
import traceback
import uuid
from pathlib import Path

import pandas as pd

import webcore
from webcore import WebError

CTX = mp.get_context("spawn")
BASE_DIR = Path(tempfile.gettempdir()) / "acs_jobs"
MAX_JOBS = 6
JOBS: dict[str, "Job"] = {}
_LOCK = threading.Lock()


# ----------------------------------------------------------------------------- proces fill
def _silencia() -> None:
    """Els fills no escriuen res util per pantalla (com paralel._init_treballador)."""
    try:
        nul = os.open(os.devnull, os.O_WRONLY)
        os.dup2(nul, 1)
        os.dup2(nul, 2)
        import clips_bridge
        clips_bridge.SORTIDA_SILENCIADA = True
    except Exception:
        pass


def _tasca(spec: dict, out_path: str, progress, slot: int, cancel) -> None:
    _silencia()
    try:
        from simulador import CONTROLADORS, Simulacio
        params, nom, dies, mode = spec["params"], spec["controller"], spec["days"], spec["mode"]
        cfg = webcore.build_cfg(params, nom)
        cfg["mode_dies"] = mode
        use_data = params.get("soil_init") == "dades"
        pct0 = cfg["humitat"]["inicial_pct"]
        if use_data and mode == "sequencial":
            # el bloc comença amb la humitat real mesurada el primer dia
            from simulador import Simulacio as _S  # noqa: F401  (import local: evita carregar-ho al pare)
            cfg["humitat"]["inicial_pct"] = _inicial_real(cfg, dies[0], pct0)
        sim = Simulacio(cfg, int(params.get("seed", 0)))
        ctrl = CONTROLADORS[nom](cfg, sim.domini) if mode == "sequencial" else None
        parts, fotos = [], []
        for i, dia in enumerate(dies):
            if cancel.is_set():
                progress[slot] = -2
                return
            if use_data and mode == "independents":
                sim.cfg["humitat"]["inicial_pct"] = webcore.initial_soil_pct(sim, dia) or pct0
            parts.append(sim.executa([dia], controlador=ctrl))
            fotos += sim.fotos
            progress[slot] = i + 1
        df = webcore.enriquir(pd.concat(parts, ignore_index=True), sim, cfg)
        pd.to_pickle({"df": df, "fotos": fotos}, out_path)
    except BaseException:  # noqa: BLE001 - es comunica al pare
        Path(out_path + ".err").write_text(traceback.format_exc(), encoding="utf-8")
        progress[slot] = -1


def _inicial_real(cfg: dict, dia: str, per_defecte: float) -> float:
    import dades
    m = dades.carrega(cfg["lloc"]).loc[f"{dia} 05:00":f"{dia} 08:00", "aigua_pct"].dropna()
    return float(min(100.0, max(5.0, m.mean()))) if len(m) else per_defecte


# ----------------------------------------------------------------------------- planificacio
def plan_tasks(controllers: list[str], days: list[str], mode: str, workers: int) -> list[dict]:
    tasques = []
    if mode == "sequencial":
        for c in controllers:
            tasques.append({"controller": c, "days": days, "mode": "sequencial"})
    elif mode == "mensual":
        blocs: dict[str, list[str]] = {}
        for d in days:
            blocs.setdefault(d[:7], []).append(d)
        for c in controllers:
            for b in blocs.values():
                tasques.append({"controller": c, "days": b, "mode": "sequencial"})
    else:
        objectiu = max(workers * 2, len(controllers))
        per_ctrl = max(1, objectiu // len(controllers))
        mida = max(1, math.ceil(len(days) / per_ctrl))
        for c in controllers:
            for i in range(0, len(days), mida):
                tasques.append({"controller": c, "days": days[i:i + mida], "mode": "independents"})
    return tasques


def day_cost(i: int) -> float:
    """Cost relatiu del dia i-esim d'un bloc continu (el controlador aprèn i es fa mes lent)."""
    p = webcore.perf_model()
    return p["seq_s_start"] + p["seq_s_slope"] * i


def estimate_seconds(n_days: int, n_controllers: int, mode: str, workers: int, days: list[str] | None = None) -> float:
    p = webcore.perf_model()
    if mode == "independents":
        cost = n_days * n_controllers * p["indep_s_per_day"]
        return p["startup_s"] + cost / max(1, workers)
    if mode == "mensual" and days:
        blocs: dict[str, int] = {}
        for d in days:
            blocs[d[:7]] = blocs.get(d[:7], 0) + 1
        tasques = sorted((sum(day_cost(i) for i in range(n)) for n in blocs.values()), reverse=True) * n_controllers
    else:
        tasques = [sum(day_cost(i) for i in range(n_days))] * n_controllers
    # planificacio simple (LPT) sobre `workers` processos
    carrega = [0.0] * max(1, min(workers, len(tasques)))
    for t in sorted(tasques, reverse=True):
        j = carrega.index(min(carrega))
        carrega[j] += t
    return p["startup_s"] + max(carrega)


# ----------------------------------------------------------------------------- treball
class Job:
    def __init__(self, params: dict, controllers: list[str], days: list[str], mode: str, cfg_meta: dict):
        self.id = uuid.uuid4().hex[:10]
        self.params, self.controllers, self.days, self.mode = params, controllers, days, mode
        self.meta = cfg_meta
        self.workers = webcore.perf_model()["workers"]
        self.tasks = plan_tasks(controllers, days, mode, self.workers)
        self.dir = BASE_DIR / self.id
        self.dir.mkdir(parents=True, exist_ok=True)
        for k, t in enumerate(self.tasks):
            t["slot"] = k
            t["out"] = str(self.dir / f"t{k}.pkl")
        self.progress = CTX.Array("i", len(self.tasks))
        self.cancel = CTX.Event()
        self.state = "queued"
        self.error = ""
        self.t0 = time.time()
        self.t1: float | None = None
        self.result: dict | None = None
        self.frames: dict[str, pd.DataFrame] = {}
        self.estimate_s = estimate_seconds(len(days), len(controllers), mode, self.workers, days)
        self._procs: dict[int, mp.Process] = {}

    # --- progres
    def _weights(self):
        """(fet, total) en 'unitats de cost' de cada dia: pondera el cost creixent dels blocs continus."""
        fet = total = 0.0
        for t in self.tasks:
            n = len(t["days"])
            w = [1.0] * n if t["mode"] == "independents" else [day_cost(i) for i in range(n)]
            total += sum(w)
            d = max(0, int(self.progress[t["slot"]]))
            fet += sum(w[:d])
        return fet, total

    def status(self) -> dict:
        per = {c: 0 for c in self.controllers}
        for t in self.tasks:
            per[t["controller"]] += max(0, int(self.progress[t["slot"]]))
        total_days = len(self.days)
        fet, total = self._weights()
        now = self.t1 or time.time()
        elapsed = now - self.t0
        eta = None
        if self.state == "running" and fet > 0:
            eta = elapsed * max(0.0, total - fet) / fet
        elif self.state == "running":
            eta = self.estimate_s
        done_days = min(per.values()) if per else 0
        return {
            "id": self.id, "state": self.state, "error": self.error, "mode": self.mode,
            "controllers": self.controllers, "total_days": total_days, "done_days": done_days,
            "done_by_controller": per, "fraction": (fet / total) if total else 0.0,
            "elapsed_s": round(elapsed, 1), "eta_s": None if eta is None else round(eta, 1),
            "estimate_s": round(self.estimate_s, 1), "tasks": len(self.tasks), "workers": self.workers,
        }

    # --- execucio
    def start(self) -> None:
        self.state = "running"
        threading.Thread(target=self._run, daemon=True, name=f"job-{self.id}").start()

    def _terminate_all(self) -> None:
        for p in self._procs.values():
            if p.is_alive():
                p.terminate()
        for p in self._procs.values():
            p.join(timeout=2)

    def _run(self) -> None:
        try:
            pendents = sorted(self.tasks, key=lambda t: -len(t["days"]) ** (1 if t["mode"] == "independents" else 2))
            while pendents or self._procs:
                if self.cancel.is_set():
                    self._terminate_all()
                    self.state, self.t1 = "cancelled", time.time()
                    return
                while pendents and len(self._procs) < self.workers:
                    t = pendents.pop(0)
                    p = CTX.Process(target=_tasca, args=({"params": self.params, "controller": t["controller"], "days": t["days"], "mode": t["mode"]},
                                                         t["out"], self.progress, t["slot"], self.cancel), daemon=True)
                    p.start()
                    self._procs[t["slot"]] = p
                time.sleep(0.25)
                for slot, p in list(self._procs.items()):
                    if p.is_alive():
                        continue
                    p.join()
                    del self._procs[slot]
                    task = self.tasks[slot]
                    err = Path(task["out"] + ".err")
                    if self.progress[slot] == -1 or err.exists():
                        raise RuntimeError(err.read_text(encoding="utf-8")[-1500:] if err.exists() else "un proces de simulacio ha fallat")
                    if self.progress[slot] == -2:
                        continue
                    if not Path(task["out"]).exists():
                        raise RuntimeError(f"el proces de la tasca {slot} ha acabat sense resultat (codi {p.exitcode})")
            if self.cancel.is_set():
                self.state, self.t1 = "cancelled", time.time()
                return
            self._finalize()
            self.state, self.t1 = "done", time.time()
        except Exception as exc:  # noqa: BLE001
            self._terminate_all()
            self.state, self.error, self.t1 = "error", str(exc), time.time()

    def _finalize(self) -> None:
        daily, kpis = {}, {}
        for c in self.controllers:
            parts, fotos = [], []
            for t in sorted((t for t in self.tasks if t["controller"] == c), key=lambda t: t["days"][0]):
                r = pd.read_pickle(t["out"])
                parts.append(r["df"])
                fotos += r["fotos"]
            df = pd.concat(parts, ignore_index=True).sort_values(["dia", "cicle", "sector"], kind="stable").reset_index(drop=True)
            self.frames[c] = df
            daily[c] = webcore.daily_table(df, fotos)
            kpis[c] = webcore.summarize(df)
        for t in self.tasks:
            Path(t["out"]).unlink(missing_ok=True)
        stats = webcore.paired_stats(daily, self.mode != "independents") if len(self.controllers) > 1 else None
        self.result = {
            "id": self.id, "scenario": self.meta, "mode": self.mode, "controllers": self.controllers,
            "days": self.days, "first_day": self.days[0], "last_day": self.days[-1],
            "daily": daily, "kpis": kpis, "stats": stats, "elapsed_s": round(time.time() - self.t0, 1),
            "soil_init": self.params.get("soil_init"), "modifiers": self.params.get("modifiers") or {},
        }

    def day_payload(self, controller: str, dia: str) -> dict:
        if controller not in self.frames:
            raise WebError("Controlador no disponible en aquest treball", 404)
        sub = self.frames[controller]
        sub = sub[sub["dia"] == dia]
        if sub.empty:
            raise WebError(f"El dia {dia} no es al treball", 404)
        return webcore.run_payload(sub, controller, self.meta["cfg"], self.params.get("scenario", ""))


# ----------------------------------------------------------------------------- API interna
def _prune() -> None:
    with _LOCK:
        vells = sorted(JOBS.values(), key=lambda j: j.t0)
        while len(vells) > MAX_JOBS:
            j = vells.pop(0)
            if j.state == "running":
                continue
            JOBS.pop(j.id, None)
            shutil.rmtree(j.dir, ignore_errors=True)


def submit(params: dict) -> Job:
    """Valida, planifica i arrenca un treball. Un treball nou substitueix el que estigui en marxa."""
    controladors = list(webcore.CONTROLADORS_WEB) if params.get("compare") else [params.get("controller") or "soar"]
    cfg = webcore.build_cfg(params, controladors[0])
    dies = webcore.resolve_days(cfg, params)
    mode = params.get("mode") or webcore.web_mode(cfg)
    if mode not in ("independents", "mensual", "sequencial"):
        raise WebError("Mode de dies desconegut")
    if len(dies) == 1:
        mode = "independents"
    params = {**params, "mode": mode,
              "soil_init": params.get("soil_init") or ("config" if webcore.scenario_defines_initial_soil(params.get("scenario", "")) else "dades")}
    with _LOCK:
        for j in JOBS.values():
            if j.state in ("queued", "running"):
                j.cancel.set()
    meta = {"name": cfg.get("nom"), "id": params.get("scenario"), "location": cfg["lloc"], "cfg": None}
    import dades
    meta.update({"location_name": dades.LLOCS[cfg["lloc"]].nom, "n_days": len(dies)})
    job = Job(params, controladors, dies, mode, {**meta, "cfg": cfg})
    with _LOCK:
        JOBS[job.id] = job
    job.start()
    _prune()
    return job


def get(job_id: str) -> Job:
    j = JOBS.get(job_id)
    if not j:
        raise WebError("Treball no trobat (potser ha caducat)", 404)
    return j
