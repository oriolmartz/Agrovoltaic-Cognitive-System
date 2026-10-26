"""E15: comprovacions estàtiques del dashboard i del bessó digital WebGL."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    ROOT / "webapp.py",
    ROOT / "frontend" / "index.html",
    ROOT / "frontend" / "styles.css",
    ROOT / "frontend" / "app.js",
    ROOT / "frontend" / "twin3d.js",
]
missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
if missing:
    raise SystemExit(f"E15 KO - falten: {', '.join(missing)}")

html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
twin_js = (ROOT / "frontend" / "twin3d.js").read_text(encoding="utf-8")
# La escena 3D es reparteix entre twin3d.js i els moduls de frontend/scene/.
scene_js = "\n".join(p.read_text(encoding="utf-8") for p in sorted((ROOT / "frontend" / "scene").glob("*.js")))
twin_js = twin_js + "\n" + scene_js
py = (ROOT / "webapp.py").read_text(encoding="utf-8")
combined_js = app_js + "\n" + twin_js

checks = {
    "UI carrega API": "/api/bootstrap" in app_js and "/api/simulate" in app_js,
    "API exposa simulacio": '@app.post("/api/simulate")' in py,
    "ontologia visible": "OntologiaDomini" in html and "OntologiaModel" in html,
    "sense logica decisio JS": "orientar-produccio" not in combined_js and "posicio-seguretat" not in combined_js,
    "WebGL Three.js": "THREE.WebGLRenderer" in twin_js and "three.module.js" in html,
    "camera orbital": "OrbitControls" in twin_js and 'data-camera="overview"' in html,
    "ombres reals": "shadowMap.enabled = true" in twin_js and "castShadow = true" in twin_js,
    "moviment continu": "requestAnimationFrame" in app_js and "interpolateFrames" in app_js,
    "panells volumetrics": "BoxGeometry(5.45" in twin_js and "solar-panel" in twin_js,
    "cultius 3D": "lettucePlant" in twin_js and "tomatoPlant" in twin_js and "vinePlant" in twin_js,
    "clima 3D": "createCloud" in twin_js and "rainPoints" in twin_js and "sunLight" in twin_js,
    "reg 3D": "createIrrigation" in twin_js and "reg_mm" in app_js,
    "reg CLIPS visible": "OntologiaReg" in html and "reg_dosi_pct" in app_js,
    "sense CDN": "cdn.jsdelivr" not in html and "unpkg" not in html,
}
ko = [k for k, ok in checks.items() if not ok]
if ko:
    raise SystemExit("E15 KO - " + ", ".join(ko))
print("E15 OK - dashboard WebGL 3D present i separat de la logica de decisio")
