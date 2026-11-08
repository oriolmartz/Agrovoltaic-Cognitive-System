"""Comprova els recursos locals imprescindibles del bessó digital 3D.

Ús (dins de simulador): python verificacio/verificar_assets_web.py
No requereix cap dependència externa.
"""
from pathlib import Path
import sys

frontend = Path(__file__).resolve().parents[1] / "frontend"
assets = (
    "vendor/three/build/three.module.js",
    "vendor/three/build/three.core.js",
    "vendor/three/addons/controls/OrbitControls.js",
    "vendor/three/addons/renderers/CSS2DRenderer.js",
    "vendor/three/addons/utils/BufferGeometryUtils.js",
    "vendor/three/addons/environments/RoomEnvironment.js",
)
missing = [p for p in assets if not (frontend / p).is_file() or (frontend / p).stat().st_size == 0]
for name in assets:
    path = frontend / name
    print(f"{'ERROR' if name in missing else 'OK':5}  {name}")
if missing:
    print("Falten recursos 3D: comproveu el contingut del ZIP i les regles de .gitignore.")
    sys.exit(1)
print("OK: Three.js local complet. Engegueu amb python webapp.py.")
