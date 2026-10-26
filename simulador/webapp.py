"""Interfície web per al simulador agrovoltaic.

La UI és només una capa de presentació/integració. No replica cap política de
control: quan s'executa una simulació, la decisió SOAR (angle dels panells i, des
de la v1_9, també el reg) continua dins de CLIPS.

Execució:
    python webapp.py
    # o bé
    uvicorn webapp:app --reload --port 8000
"""

from __future__ import annotations

import dataclasses
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ontology_loader import carrega_model, fets_reg

ARREL = Path(__file__).resolve().parent
FRONTEND = ARREL / "frontend"
ESCENARIS = ARREL / "escenaris"

app = FastAPI(title="Agrovoltaic Cognitive System", version="1.1")
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


class PeticioSimulacio(BaseModel):
    scenario: str = "dia_normal.json"
    controller: str = "soar"
    day: str | None = None
    seed: int = Field(default=0, ge=0, le=2_147_483_647)
    compare: bool = False


def _jsonable(v: Any) -> Any:
    """Converteix valors pandas/numpy i NaN a JSON net."""
    if v is None:
        return None
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_jsonable(x) for x in v]
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    if hasattr(v, "item"):
        try:
            v = v.item()
        except Exception:
            pass
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if pd.isna(v):
        return None
    return v


def _scenario_path(name: str) -> Path:
    if name in ("", "default", "per_defecte"):
        return Path()
    # Impedeix escapar d'escenaris/ amb ../
    p = (ESCENARIS / Path(name).name).resolve()
    if p.parent != ESCENARIS.resolve() or not p.is_file() or p.suffix.lower() != ".json":
        raise HTTPException(status_code=404, detail="Escenari no trobat")
    return p


def _cfg_for_scenario(name: str):
    # Import diferit: permet que la portada i la validació RDF funcionin fins i
    # tot si clipspy encara no s'ha instal·lat a l'entorn.
    try:
        from simulador import carrega_config
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No es pot carregar el simulador/clipspy: {exc}") from exc
    p = _scenario_path(name)
    return carrega_config(str(p) if p else None)


def _scenario_catalog() -> list[dict[str, Any]]:
    out = []
    for p in sorted(ESCENARIS.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            d = {}
        out.append({
            "id": p.name,
            "label": d.get("nom") or p.stem.replace("_", " ").title(),
            "location": d.get("lloc") or "ribera",
        })
    return out


def _ontology_status() -> dict[str, Any]:
    """Estat de les tres ontologies (domini, model i reg) i dels fets que se'n projecten."""
    model = carrega_model()
    n_sensors = sum(len(s.sensors) for s in model.sectors.values())
    facts = {
        "sector": len(model.sectors),
        "cultiu": len(model.cultius),
        "panell": len(model.panells),
        "estat_sensor": n_sensors,
    }
    reg = None
    if model.reg is not None:
        r = model.reg
        facts["reg"] = len(fets_reg(r))
        reg = {
            "file": r.fitxer.name,
            "validation": dict(r.validacio),
            "config": dataclasses.asdict(r.config),
            "objectives": len(r.objectius),
            "sources": len(r.fonts),
            "valves": sum(1 for s in model.sectors.values() if s.valvula),
        }
    facts["total"] = sum(facts.values())
    base_validation = {k: v for k, v in model.validacio_domini.items() if ":" not in k and not k.endswith("_reg_validades")}
    return {
        "valid": True,
        "domain": model.fitxer_domini.name,
        "model": model.fitxer.name,
        "validation": base_validation,
        "facts": facts,
        "reg": reg,
    }


def _run_one(scenario: str, controller: str, day: str | None, seed: int):
    try:
        from simulador import Simulacio, selecciona_dies
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No es pot carregar el motor CLIPS: {exc}") from exc

    cfg = _cfg_for_scenario(scenario)
    if controller not in {"soar", "seguidor", "fix"}:
        raise HTTPException(status_code=400, detail="Controlador desconegut")
    cfg["controlador"]["tipus"] = controller
    # La UI no escriu traces per defecte. Les traces completes continuen
    # disponibles amb el CLI i els experiments.
    cfg.pop("traca_dir", None)

    available = selecciona_dies(cfg)
    if not available:
        raise HTTPException(status_code=400, detail="No hi ha dies disponibles per a aquest escenari")
    chosen = day or available[0]
    if chosen not in available:
        raise HTTPException(status_code=400, detail=f"El dia {chosen} no és disponible per a l'escenari")

    sim = Simulacio(cfg, seed)
    df = sim.executa([chosen], etiqueta=cfg.get("nom", Path(scenario).stem))
    return _enriquir(df, sim, cfg), cfg


def _enriquir(df: pd.DataFrame, sim, cfg: dict) -> pd.DataFrame:
    """Afegeix magnituds NOMÉS de presentació que el bessó 3D necessita.

    Posició solar, nuvolositat estimada i pluja real de l'hora es deriven de la mateixa
    física i meteorologia que fa servir el simulador; no es pren cap decisió aquí.
    """
    import fisica

    if df.empty:
        return df
    mod = cfg["modificadors"]
    lat, lon = sim.lloc.lat, sim.lloc.lon
    cache: dict[tuple[str, int], tuple[float, float, float, float]] = {}

    def sol(dia: str, hora: int):
        key = (dia, int(hora))
        if key not in cache:
            t = pd.Timestamp(f"{dia} {int(hora):02d}:00")
            elev, az = fisica.sol_interval(lat, lon, t.to_pydatetime())
            met = sim.meteo.loc[t]
            ghi = max(0.0, float(met["ghi"]) * mod["rad_factor"])
            clar = 1000.0 * max(math.sin(math.radians(elev)), 0.0) ** 0.78
            nub = 0.0 if (elev <= 0 or clar <= 1e-9) else max(0.0, min(1.0, 1.0 - ghi / clar))
            cache[key] = (float(elev), float(az), nub, float(met["pluja"]) * mod["pluja_factor"])
        return cache[key]

    vals = [sol(d, h) for d, h in zip(df["dia"], df["hora"])]
    df = df.copy()
    df["elevacio_solar"] = [v[0] for v in vals]
    df["azimut_solar"] = [v[1] for v in vals]
    df["nubolositat"] = [v[2] for v in vals]
    df["pluja_mm"] = [v[3] for v in vals]
    df["reg_mm"] = df["reg_net_mm"]          # aigua neta que arriba al sòl
    return df


def _summarize(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {}
    energy = float(df["P_kw"].sum())
    pump = float(df["bomba_kwh"].sum())
    optimum = float(df["P_opt_kw"].sum())
    ms = df.loc[df["ms"] > 0, "ms"]
    rain = float(df.groupby(["dia", "hora"])["pluja_mm"].first().sum())
    modes = df["reg_mode"].dropna()
    return {
        "energy_kwh": round(energy, 2),
        "net_energy_kwh": round(energy - pump, 2),
        "efficiency_pct": round(100 * energy / optimum, 1) if optimum > 0 else None,
        "safety_violations": int(df["violacio_seguretat"].sum()),
        "wind_exposure_h": int(df["exposicio_vent"].sum()),
        "impasses": int((df["impas"].fillna("") != "").sum()),
        "invariants_ko": int((df["invariants_ko"].fillna("") != "").sum()),
        "avg_ms": round(float(ms.mean()), 2) if not ms.empty else 0.0,
        "rules_per_cycle": round(float(df.loc[df["regles"] > 0, "regles"].mean()), 1) if (df["regles"] > 0).any() else 0.0,
        "chunk_decisions": int(df["us_chunk"].sum()),
        "rl_decisions": int(df["us_rl"].sum()),
        "irrigation_mm": round(float(df["reg_net_mm"].sum()), 2),
        "irrigation_m3": round(float(df["reg_m3"].sum()), 2),
        "irrigation_events": int((df["reg_net_mm"] > 1e-9).sum()),
        "irrigation_mode": str(modes.mode().iloc[0]) if not modes.empty else "cap",
        "percolation_mm": round(float(df["percolacio_mm"].sum()), 2),
        "pump_kwh": round(pump, 2),
        "rain_mm": round(rain, 2),
        "water_stress_cycles": int(df["estres_aigua"].sum()),
        "heat_stress_h": int(df["estres_calor"].sum()),
        "radiation_stress_h": int(df["estres_rad"].sum()),
        "critical_heat_h": int(df["calor_critica"].sum()),
        "cycles": max(1, int(df["cicle"].nunique())),
    }


def _sector_snapshot(df: pd.DataFrame) -> list[dict[str, Any]]:
    out = []
    for sector, g in df.sort_values(["cicle", "sector"]).groupby("sector", sort=True):
        r = g.iloc[-1]
        out.append({
            "sector": sector,
            "crop": r["cultiu"],
            "action": r["accio"],
            "angle": round(float(r["angle_real"]), 1),
            "optimal_angle": round(float(r["angle_optim"]), 1),
            "water_pct": round(float(r["aigua_pct"]), 1),
            "crop_temp": round(float(r["t_cultiu"]), 1),
            "radiation": round(float(r["rad_cultiu"]), 0),
            "power_kw": round(float(r["P_kw"]), 2),
            "irrigation_mm": round(float(g["reg_net_mm"].sum()), 2),
            "irrigation_events": int((g["reg_net_mm"] > 1e-9).sum()),
            "irrigation_action": r.get("reg_accio"),
            "risks": r["riscos"] or "",
            "impasse": r["impas"] or "",
            "reason": r["motiu"] or "",
        })
    return out


RECORD_COLUMNS = [
    "dia", "hora", "cicle", "sector", "cultiu", "accio", "angle_ordre", "angle_real", "angle_optim",
    "elevacio_solar", "azimut_solar", "nubolositat",
    "P_kw", "P_opt_kw", "demanda_kw", "vent_real", "vent_obs", "vent_prev", "ghi", "temp_aire", "pluja_mm", "pluja_prevista",
    "rad_cultiu", "t_cultiu", "aigua_pct",
    "estres_rad", "estres_calor", "estres_aigua",
    "reg_mode", "reg_accio", "reg_dosi_pct", "reg_motiu", "reg_mm", "reg_brut_mm", "reg_m3", "bomba_kwh", "percolacio_mm",
    "riscos", "impas", "us_chunk", "us_rl", "motiu", "invariants_ko", "regles", "ms", "sensors_absents",
]


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    cols = [c for c in RECORD_COLUMNS if c in df.columns]
    return [_jsonable(r) for r in df[cols].sort_values(["cicle", "sector"]).to_dict(orient="records")]


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")


@app.get("/api/bootstrap")
def bootstrap():
    try:
        return {
            "ontology": _ontology_status(),
            "scenarios": _scenario_catalog(),
            "controllers": [
                {"id": "soar", "label": "SOAR / CLIPS"},
                {"id": "seguidor", "label": "Seguidor comercial"},
                {"id": "fix", "label": "Panell fix"},
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/days")
def days(scenario: str = "dia_normal.json"):
    cfg = _cfg_for_scenario(scenario)
    try:
        from simulador import selecciona_dies
        available = selecciona_dies(cfg)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"days": available, "location": cfg["lloc"], "name": cfg.get("nom", scenario)}


@app.post("/api/simulate")
def simulate(req: PeticioSimulacio):
    controllers = ["soar", "seguidor", "fix"] if req.compare else [req.controller]
    runs = []
    for controller in controllers:
        df, cfg = _run_one(req.scenario, controller, req.day, req.seed)
        runs.append({
            "controller": controller,
            "kpis": _summarize(df),
            "sectors": _sector_snapshot(df),
            "records": _records(df),
            "day": str(df["dia"].iloc[0]),
            "location": cfg["lloc"],
            "scenario_name": cfg.get("nom", Path(req.scenario).stem),
        })
    return {"runs": runs, "ontology": _ontology_status()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("webapp:app", host="127.0.0.1", port=8000, reload=False)
