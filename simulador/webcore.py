"""Logica de la web compartida entre el servidor (webapp.py) i els processos que simulen
(webjobs.py). No depen de FastAPI, aixi els processos fills arrenquen rapid.

Principi: aqui no es decideix res. Les decisions (angle i reg) les pren CLIPS; aquest modul
nomes prepara la configuracio, agrega resultats i fa estadistica sobre el que ja s'ha simulat.
"""

from __future__ import annotations

import dataclasses
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ARREL = Path(__file__).resolve().parent
ESCENARIS = ARREL / "escenaris"
CONTROLADORS_WEB = ("soar", "seguidor", "fix")
MODES_DIES = ("independents", "sequencial")
PREFIX_DADES = "data:"

# Rangs acceptats per als modificadors del clima (what-if sobre dades reals).
MODIFICADORS = {"temp_delta": (-10.0, 10.0), "vent_factor": (0.2, 3.0), "rad_factor": (0.3, 1.5), "pluja_factor": (0.0, 3.0)}


class WebError(Exception):
    def __init__(self, detail: str, status: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status = status


def jsonable(v: Any) -> Any:
    """Converteix valors pandas/numpy i NaN a JSON net."""
    if v is None:
        return None
    if isinstance(v, dict):
        return {str(k): jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [jsonable(x) for x in v]
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    if hasattr(v, "item"):
        try:
            v = v.item()
        except Exception:
            pass
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v


def _r(x: Any, d: int = 3):
    x = jsonable(x)
    return round(x, d) if isinstance(x, float) else x


# ------------------------------------------------------------------ escenaris i configuracio
def scenario_path(name: str) -> Path | None:
    if name in ("", "default", "per_defecte"):
        return None
    # Impedeix escapar d'escenaris/ amb ../
    p = (ESCENARIS / Path(name).name).resolve()
    if p.parent != ESCENARIS.resolve() or not p.is_file() or p.suffix.lower() != ".json":
        raise WebError("Escenari no trobat", 404)
    return p


def cfg_for_scenario(name: str) -> dict:
    """Config d'un escenari: un fitxer d'escenaris/ o 'data:<lloc>' (totes les dades d'un lloc)."""
    try:
        import dades
        from simulador import carrega_config
    except Exception as exc:
        raise WebError(f"No es pot carregar el simulador/clipspy: {exc}", 500) from exc
    if name.startswith(PREFIX_DADES):
        lloc = name[len(PREFIX_DADES):]
        if lloc not in dades.LLOCS:
            raise WebError(f"Lloc desconegut: {lloc}", 404)
        return carrega_config({"nom": f"Totes les dades · {dades.LLOCS[lloc].nom}", "lloc": lloc, "mode_dies": "sequencial", "blocs": "mes"})
    p = scenario_path(name)
    return carrega_config(str(p) if p else None)


def build_cfg(params: dict, controlador: str) -> dict:
    """Config final d'una execucio: escenari + controlador + sobreescriptures de la UI."""
    cfg = cfg_for_scenario(params.get("scenario") or "dia_normal.json")
    if controlador not in CONTROLADORS_WEB:
        raise WebError("Controlador desconegut")
    cfg["controlador"]["tipus"] = controlador
    cfg["demo_trace"] = bool(params.get("demo", False)) and controlador == "soar"
    # Captura de regles exclusivament per a la demostracio, no per a simulacions habituals.
    if cfg["demo_trace"]:
        cfg["controlador"]["vigila_regles"] = True
    # La UI no escriu fitxers de traça per defecte; les traces del CLI continuen separades.
    cfg.pop("traca_dir", None)
    mode = params.get("mode")
    if mode:
        if mode not in ("independents", "mensual", "sequencial"):
            raise WebError("Mode de dies desconegut")
        cfg["mode_dies"] = "independents" if mode == "independents" else "sequencial"
        cfg["blocs"] = "mes" if mode == "mensual" else None
    for k, v in (params.get("modifiers") or {}).items():
        if k not in MODIFICADORS or v is None:
            continue
        lo, hi = MODIFICADORS[k]
        cfg["modificadors"][k] = float(min(hi, max(lo, float(v))))
    return cfg


def scenario_defines_initial_soil(name: str) -> bool:
    """True si l'escenari fixa explicitament la humitat inicial (llavors no es toca amb la mesura real)."""
    if name.startswith(PREFIX_DADES):
        return False
    p = scenario_path(name)
    if not p:
        return False
    try:
        return "inicial_pct" in (json.loads(p.read_text(encoding="utf-8")).get("humitat") or {})
    except Exception:
        return False


def initial_soil_pct(sim, dia: str) -> float | None:
    """Aigua disponible mesurada a l'estacio XMS-Cat a primera hora del dia (dada real)."""
    try:
        m = sim.meteo.loc[f"{dia} 05:00":f"{dia} 08:00", "aigua_pct"].dropna()
    except Exception:
        return None
    return float(min(100.0, max(5.0, m.mean()))) if len(m) else None


def web_mode(cfg: dict) -> str:
    """Mode de dies que veu la UI: independents | mensual | sequencial."""
    if cfg.get("blocs") == "mes":
        return "mensual"
    return "independents" if cfg.get("mode_dies") == "independents" else "sequencial"


def resolve_days(cfg: dict, params: dict) -> list[str]:
    from simulador import selecciona_dies
    disponibles = selecciona_dies(cfg)
    if not disponibles:
        raise WebError("No hi ha dies disponibles per a aquest escenari")
    dia = params.get("day")
    if dia:
        if dia not in disponibles:
            raise WebError(f"El dia {dia} no es disponible per a l'escenari")
        return [dia]
    ini, fi = params.get("start"), params.get("end")
    dies = [d for d in disponibles if (not ini or d >= ini) and (not fi or d <= fi)]
    if not dies:
        raise WebError("El rang de dates no conte cap dia disponible")
    return dies


def _resum_escenari(ident: str, etiqueta: str, kind: str, cfg: dict, extra: dict | None = None) -> dict:
    import dades
    from simulador import selecciona_dies
    dies = selecciona_dies(cfg)
    base = {
        "id": ident, "label": etiqueta, "kind": kind,
        "location": cfg["lloc"], "location_name": dades.LLOCS[cfg["lloc"]].nom,
        "days": len(dies), "first_day": dies[0] if dies else None, "last_day": dies[-1] if dies else None,
        "mode": web_mode(cfg), "humidity_mode": cfg["humitat"]["mode"],
        "modifiers": {k: v for k, v in cfg["modificadors"].items() if v not in (0.0, 1.0)},
    }
    base.update(extra or {})
    return base


def scenario_catalog() -> list[dict]:
    """Escenaris de escenaris/*.json i, per a cada lloc de dades.LLOCS, 'Totes les dades'.

    La durada en dies surt de les dades reals: si s'amplien, el catalog creix sol.
    """
    import dades
    from simulador import carrega_config
    out = []
    for p in sorted(ESCENARIS.glob("*.json")):
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            cfg = carrega_config(str(p))
            out.append(_resum_escenari(p.name, raw.get("nom") or p.stem.replace("_", " "), "escenari", cfg,
                                       {"description": raw.get("descripcio", "")}))
        except Exception as exc:  # un escenari mal escrit no ha de tombar la portada
            out.append({"id": p.name, "label": p.stem, "kind": "escenari", "days": 0, "error": str(exc)})
    for lloc, info in dades.LLOCS.items():
        cfg = carrega_config({"nom": f"Totes les dades · {info.nom}", "lloc": lloc, "mode_dies": "sequencial", "blocs": "mes"})
        out.append(_resum_escenari(PREFIX_DADES + lloc, f"Totes les dades · {info.nom}", "dades", cfg,
                                   {"description": "Tot el període de dades reals disponible; creix quan s'afegeixen dades."}))
    return out


def ontology_status() -> dict[str, Any]:
    """Estat de les tres ontologies (domini, model i reg) i dels fets que se'n projecten."""
    from ontology_loader import carrega_model, fets_reg
    model = carrega_model()
    n_sensors = sum(len(s.sensors) for s in model.sectors.values())
    facts = {
        "sector": len(model.sectors), "cultiu": len(model.cultius),
        "panell": len(model.panells), "estat_sensor": n_sensors,
    }
    reg = None
    if model.reg is not None:
        r = model.reg
        facts["reg"] = len(fets_reg(r))
        reg = {
            "file": r.fitxer.name, "validation": dict(r.validacio), "config": dataclasses.asdict(r.config),
            "objectives": len(r.objectius), "sources": len(r.fonts),
            "valves": sum(1 for s in model.sectors.values() if s.valvula),
        }
    facts["total"] = sum(facts.values())
    base_validation = {k: v for k, v in model.validacio_domini.items() if ":" not in k and not k.endswith("_reg_validades")}
    return {"valid": True, "domain": model.fitxer_domini.name, "model": model.fitxer.name,
            "validation": base_validation, "facts": facts, "reg": reg}


# ------------------------------------------------------------------ enriquiment i resums
def enriquir(df: pd.DataFrame, sim, cfg: dict) -> pd.DataFrame:
    """Afegeix magnituds NOMES de presentacio que el bessó 3D necessita.

    Posicio solar, nuvolositat estimada i pluja real de l'hora es deriven de la mateixa
    fisica i meteorologia que fa servir el simulador; no es pren cap decisio aqui.
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
    df["reg_mm"] = df["reg_net_mm"]          # aigua neta que arriba al sol
    return df


def summarize(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {}
    energy = float(df["P_kw"].sum())
    pump = float(df["bomba_kwh"].sum())
    optimum = float(df["P_opt_kw"].sum())
    ms = df.loc[df["ms"] > 0, "ms"]
    rain = float(df.groupby(["dia", "hora"])["pluja_mm"].first().sum())
    modes = df["reg_mode"].dropna()
    ns = max(1, df["sector"].nunique())
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
        "irrigation_mm_avg": round(float(df["reg_net_mm"].sum()) / ns, 2),
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
        "days": int(df["dia"].nunique()),
        "sector_hours": int(len(df)),
    }


def sector_snapshot(df: pd.DataFrame) -> list[dict[str, Any]]:
    out = []
    for sector, g in df.sort_values(["cicle", "sector"]).groupby("sector", sort=True):
        r = g.iloc[-1]
        out.append({
            "sector": sector, "crop": r["cultiu"], "action": r["accio"],
            "angle": round(float(r["angle_real"]), 1), "optimal_angle": round(float(r["angle_optim"]), 1),
            "water_pct": round(float(r["aigua_pct"]), 1), "crop_temp": round(float(r["t_cultiu"]), 1),
            "radiation": round(float(r["rad_cultiu"]), 0), "power_kw": round(float(r["P_kw"]), 2),
            "irrigation_mm": round(float(g["reg_net_mm"].sum()), 2),
            "irrigation_events": int((g["reg_net_mm"] > 1e-9).sum()),
            "irrigation_action": r.get("reg_accio"),
            "risks": r["riscos"] or "", "impasse": r["impas"] or "", "reason": r["motiu"] or "",
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


def records(df: pd.DataFrame) -> list[dict[str, Any]]:
    cols = [c for c in RECORD_COLUMNS if c in df.columns]
    return [jsonable(r) for r in df[cols].sort_values(["cicle", "sector"]).to_dict(orient="records")]


def run_payload(df: pd.DataFrame, controlador: str, cfg: dict, scenario: str) -> dict:
    """Forma comuna d'una execucio d'un dia (la que consumeix el bessó 3D)."""
    return {
        "controller": controlador, "kpis": summarize(df), "sectors": sector_snapshot(df), "records": records(df),
        "day": str(df["dia"].iloc[0]), "location": cfg["lloc"],
        "scenario_name": cfg.get("nom", Path(scenario).stem),
    }


# ------------------------------------------------------------------ agregats del periode
def daily_table(df: pd.DataFrame, fotos: list[dict] | None = None) -> list[dict[str, Any]]:
    """Una fila per dia: es el que viatja al navegador (els registres horaris es demanen dia a dia)."""
    fot = {f["dia"]: f for f in (fotos or [])}
    out = []
    for dia, g in df.groupby("dia", sort=True):
        h = g.groupby("hora")
        e, o, pump = float(g["P_kw"].sum()), float(g["P_opt_kw"].sum()), float(g["bomba_kwh"].sum())
        ns = max(1, g["sector"].nunique())
        ms = g.loc[g["ms"] > 0, "ms"]
        row = {
            "day": str(dia),
            "energy_kwh": e, "optimum_kwh": o, "efficiency_pct": 100 * e / o if o > 0 else None,
            "pump_kwh": pump, "net_energy_kwh": e - pump,
            "irrigation_mm_avg": float(g["reg_net_mm"].sum()) / ns, "irrigation_m3": float(g["reg_m3"].sum()),
            "irrigation_events": int((g["reg_net_mm"] > 1e-9).sum()), "percolation_mm_avg": float(g["percolacio_mm"].sum()) / ns,
            "rain_mm": float(h["pluja_mm"].first().sum()), "ghi_kwh_m2": float(h["ghi"].first().sum()) / 1000,
            "temp_max": float(g["temp_aire"].max()), "crop_temp_max": float(g["t_cultiu"].max()),
            "cloud_mean": float(h["nubolositat"].first()[h["elevacio_solar"].first() > 0].mean()) if (g["elevacio_solar"] > 0).any() else 0.0,
            "wind_max": float(g["vent_real"].max()), "wind_exposure_h": int(g["exposicio_vent"].sum()),
            "safety_violations": int(g["violacio_seguretat"].sum()),
            "soil_mean": float(g["aigua_pct"].mean()), "soil_min": float(g["aigua_pct"].min()),
            "water_stress_h": int(g["estres_aigua"].sum()), "heat_stress_h": int(g["estres_calor"].sum()),
            "radiation_stress_h": int(g["estres_rad"].sum()),
            "impasses": int((g["impas"].fillna("") != "").sum()),
            "chunk_decisions": int(g["us_chunk"].sum()), "rl_decisions": int(g["us_rl"].sum()),
            "avg_ms": float(ms.mean()) if not ms.empty else 0.0,
            "rules_per_cycle": float(g.loc[g["regles"] > 0, "regles"].mean()) if (g["regles"] > 0).any() else 0.0,
            "by_sector": {
                sid: {"soil_mean": float(gs["aigua_pct"].mean()), "energy_kwh": float(gs["P_kw"].sum()),
                      "irrigation_mm": float(gs["reg_net_mm"].sum())}
                for sid, gs in g.groupby("sector")
            },
        }
        f = fot.get(dia)
        if f:
            row["knowledge"] = {"chunks": len(f.get("chunks", [])), "q": len(f.get("rl", [])), "epmem": int(f.get("n_epmem", 0))}
        out.append({k: (_r(v) if not isinstance(v, dict) else {kk: ({a: _r(b) for a, b in vv.items()} if isinstance(vv, dict) else _r(vv)) for kk, vv in v.items()}) for k, v in row.items()})
    return out


PAIRED_METRICS = [
    ("energy_kwh", "Producció (kWh)", "high"),
    ("net_energy_kwh", "Energia neta (kWh)", "high"),
    ("irrigation_m3", "Aigua bombejada (m³)", "low"),
    ("water_stress_h", "Estrès hídric (sector·h)", "low"),
    ("heat_stress_h", "Estrès tèrmic (sector·h)", "low"),
    ("safety_violations", "Violacions de seguretat", "low"),
    ("wind_exposure_h", "Exposició al vent (h)", "low"),
]


def paired_stats(daily: dict[str, list[dict]], sequential: bool) -> dict[str, Any]:
    """SOAR davant de cada referencia, dia a dia (disseny aparellat), amb estadistica.py del repo."""
    import estadistica
    base = {r["day"]: r for r in daily.get("soar", [])}
    out: list[dict] = []
    for ref, rows in daily.items():
        if ref == "soar" or not base:
            continue
        idx = {r["day"]: r for r in rows}
        dies = [d for d in base if d in idx]
        if len(dies) < 3:
            continue
        bloc: list[dict] = []
        for key, label, millor in PAIRED_METRICS:
            a = np.array([base[d][key] for d in dies], float)
            b = np.array([idx[d][key] for d in dies], float)
            try:
                res = estadistica.compara_aparellat(a, b, "soar", ref, label)
            except Exception as exc:
                res = {"metrica": label, "A": "soar", "B": ref, "n": len(dies), "error": str(exc)}
            d = a - b
            res.update({
                "key": key, "label": label, "better": millor, "ref": ref,
                "win_rate": float(np.mean(d > 0) if millor == "high" else np.mean(d < 0)),
                "loss_rate": float(np.mean(d < 0) if millor == "high" else np.mean(d > 0)),
                "tie_rate": float(np.mean(np.isclose(d, 0))),
            })
            bloc.append(res)
        ps = [r.get("p_wilcoxon", 1.0) for r in bloc]
        for r, ph in zip(bloc, estadistica.holm(ps)):
            r["p_holm"] = float(ph)
        out += bloc
    return {
        "pairs": jsonable(out),
        "independent_days": not sequential,
        "warning": ("Els dies seguits no són independents (l'aigua del sòl i l'aprenentatge passen d'un dia al següent): "
                    "els p-valors són orientatius. Els experiments d'aigua del repo (E14/E15) comparen mesos sencers.")
        if sequential else "",
    }


# ------------------------------------------------------------------ rendiment (per a l'estimacio de durada)
def perf_model() -> dict[str, Any]:
    """Mesures reals (clipspy, 1 nucli): ~0,8 s/dia amb dies independents. En una execucio
    continua el cost del dia i-esim creix linealment (~0,3 s + 0,043 s·i) perque el controlador
    aprèn chunks i episodis; per aixo el mode mensual (blocs d'un mes en paral·lel) compensa."""
    cpus = os.cpu_count() or 1
    return {"cpus": cpus, "workers": max(1, min(8, cpus - 1)) if cpus > 2 else cpus,
            "indep_s_per_day": 0.8, "seq_s_start": 0.3, "seq_s_slope": 0.043, "startup_s": 3.0}
