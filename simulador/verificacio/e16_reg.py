"""E16: verificacio del segon actuador (reg) i del balanc hidric v1.9.

Comprova propietats fisques sense CLIPS i, si clipspy es disponible, executa
una simulacio seca amb el controlador actiu per verificar que CLIPS genera
ordres de reg i que el balanc hidric no supera la capacitat del sector.
"""
from __future__ import annotations

from pathlib import Path
import copy
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import fisica

# 1) propietats del balanc hidric
b = fisica.balanc_hidric_detall(40.0, 100.0, et0=1.0, kc=1.0, pluja=0.0, transm=1.0)
assert 38.9 <= b["aigua_mm"] <= 39.1, b
assert b["et_c_mm"] > 0

pluja = fisica.balanc_hidric_detall(40.0, 100.0, et0=1.0, kc=1.0, pluja=5.0, transm=1.0)
assert pluja["aigua_mm"] > b["aigua_mm"]

ombra = fisica.balanc_hidric_detall(40.0, 100.0, et0=1.0, kc=1.0, pluja=0.0, transm=0.6)
assert ombra["et_c_mm"] < b["et_c_mm"]

saturat = fisica.balanc_hidric_detall(99.0, 100.0, et0=0.0, kc=1.0, pluja=5.0, transm=1.0)
assert saturat["aigua_mm"] == 100.0 and saturat["drenatge_mm"] == 4.0

# 2) contracte CLIPS present
core = (ROOT / "clips_core" / "core" / "domini.clp").read_text(encoding="utf-8")
accio = (ROOT / "clips_core" / "action" / "accio.clp").read_text(encoding="utf-8")
assert "(deftemplate reg-config" in core
assert "(deftemplate ordre-reg" in core
assert "(defrule aplica-reg" in accio

# 3) integracio completa si clipspy es disponible
try:
    import clips  # noqa: F401
except Exception:
    print("E16 PARTIAL OK - fisica i contracte de reg validats; clipspy no disponible en aquest entorn")
    raise SystemExit(0)

from simulador import Simulacio, carrega_config, selecciona_dies

cfg = carrega_config(str(ROOT / "escenaris" / "dia_normal.json"))
cfg = copy.deepcopy(cfg)
cfg["humitat"]["mode"] = "balanc"
cfg["humitat"]["inicial_pct"] = 25.0
cfg["humitat"]["reg"]["mode"] = "soar"
cfg["mode_dies"] = "independents"
dies = selecciona_dies(cfg, n=1, llavor=16)
assert dies, "sense dies disponibles"

df = Simulacio(cfg, llavor=16).executa(dies, etiqueta="E16-reg")
assert not df.empty
assert "reg_net_mm" in df.columns and "reg_dosi_pct" in df.columns
assert (df["reg_dosi_pct"].fillna(0) > 0).any(), "CLIPS no ha generat cap ordre de reg sota estres hidric"
assert (df["reg_dosi_pct"].fillna(0) <= 100.0 + 1e-9).all()
assert (df["aigua_pct"] <= 100.0 + 1e-9).all()
assert (df["aigua_pct"] >= -1e-9).all()

print("E16 OK - CLIPS decideix el reg i el simulador aplica un balanc hidric coherent")
