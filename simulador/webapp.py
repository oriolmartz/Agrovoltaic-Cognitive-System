"""Interfície web per al simulador agrovoltaic.

La UI és només una capa de presentació/integració. No replica cap política de control:
l'angle dels panells i, des de la v1_9, també el reg es decideixen dins de CLIPS.

Un dia es simula a la mateixa petició (/api/simulate). Els períodes llargs (mesos) són treballs
en segon plà (/api/jobs): es reparteixen en processos, informen del progrés i el navegador
en demana els registres dia a dia (escala amb el nombre de dies de dades).

Execució:
    python webapp.py
    # o bé
    uvicorn webapp:app --reload --port 8000
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import webcore
import webjobs
from webcore import WebError

ARREL = Path(__file__).resolve().parent
FRONTEND = ARREL / "frontend"

app = FastAPI(title="Agrovoltaic Cognitive System", version="1.2")
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


@app.exception_handler(WebError)
async def _web_error(_, exc: WebError):
    return JSONResponse(status_code=exc.status, content={"detail": exc.detail})


class Modificadors(BaseModel):
    temp_delta: float | None = None
    vent_factor: float | None = None
    rad_factor: float | None = None
    pluja_factor: float | None = None


class PeticioSimulacio(BaseModel):
    scenario: str = "dia_normal.json"
    controller: str = "soar"
    day: str | None = None
    start: str | None = None          # inici del rang (periodes)
    end: str | None = None
    seed: int = Field(default=0, ge=0, le=2_147_483_647)
    compare: bool = False
    mode: str | None = None           # independents | mensual | sequencial (per defecte, el de l'escenari)
    soil_init: str | None = None      # dades | config
    modifiers: Modificadors | None = None

    def as_params(self) -> dict:
        d = self.model_dump()
        d["modifiers"] = {k: v for k, v in (d.get("modifiers") or {}).items() if v is not None}
        return d


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")


@app.get("/api/bootstrap")
def bootstrap():
    try:
        return {
            "ontology": webcore.ontology_status(),
            "scenarios": webcore.scenario_catalog(),
            "controllers": [
                {"id": "soar", "label": "SOAR / CLIPS"},
                {"id": "seguidor", "label": "Seguidor comercial"},
                {"id": "fix", "label": "Panell fix"},
            ],
            "perf": webcore.perf_model(),
        }
    except WebError:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/days")
def days(scenario: str = "dia_normal.json"):
    cfg = webcore.cfg_for_scenario(scenario)
    from simulador import selecciona_dies
    return {"days": selecciona_dies(cfg), "location": cfg["lloc"], "name": cfg.get("nom", scenario),
            "mode": webcore.web_mode(cfg)}


@app.post("/api/simulate")
def simulate(req: PeticioSimulacio):
    """Un dia, a la mateixa petició. Per a rangs de mes d'un dia, vegeu /api/jobs."""
    params = req.as_params()
    controllers = list(webcore.CONTROLADORS_WEB) if req.compare else [req.controller]
    runs = []
    for c in controllers:
        cfg = webcore.build_cfg(params, c)
        dies = webcore.resolve_days(cfg, params)
        if len(dies) != 1:
            raise WebError("Aquest rang té més d'un dia: fes servir /api/jobs", 400)
        cfg["mode_dies"] = "independents"
        from simulador import Simulacio
        sim = Simulacio(cfg, req.seed)
        if params.get("soil_init") == "dades":
            sim.cfg["humitat"]["inicial_pct"] = webcore.initial_soil_pct(sim, dies[0]) or cfg["humitat"]["inicial_pct"]
        df = webcore.enriquir(sim.executa(dies, etiqueta=cfg.get("nom", "")), sim, cfg)
        runs.append(webcore.run_payload(df, c, cfg, req.scenario))
    return {"runs": runs, "ontology": webcore.ontology_status()}


# ------------------------------------------------------------------ períodes llargs
@app.post("/api/jobs")
def create_job(req: PeticioSimulacio):
    job = webjobs.submit(req.as_params())
    return job.status()


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    return webjobs.get(job_id).status()


@app.get("/api/jobs/{job_id}/result")
def job_result(job_id: str):
    job = webjobs.get(job_id)
    if job.state != "done" or job.result is None:
        raise WebError("El treball encara no ha acabat", 409)
    return {**job.result, "scenario": {k: v for k, v in job.result["scenario"].items() if k != "cfg"}}


@app.get("/api/jobs/{job_id}/day")
def job_day(job_id: str, date: str, controller: str = "soar"):
    job = webjobs.get(job_id)
    if job.state != "done":
        raise WebError("El treball encara no ha acabat", 409)
    return job.day_payload(controller, date)


@app.delete("/api/jobs/{job_id}")
def cancel_job(job_id: str):
    job = webjobs.get(job_id)
    job.cancel.set()
    return job.status()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("webapp:app", host="127.0.0.1", port=8000, reload=False)
