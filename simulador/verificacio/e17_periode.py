"""E17 - Simulacio de periodes llargs amb dades reals (capa web).

Comprova, sense navegador:
  1. el cataleg d'escenaris porta la durada en dies calculada de les dades reals;
  2. un lloc nou es registra amb un simple JSON a dades_reals/llocs/ i apareix sol al cataleg
     (escalabilitat quan s'afegeixen dades);
  3. un treball curt en processos (3 controladors, 3 dies) acaba amb la taula DIARIA, el progres,
     l'estadistica aparellada i els registres horaris de cada dia (el que consumeix el 3D).

Us:  python verificacio/e17_periode.py     (uns 20-40 s)
"""

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import dades  # noqa: E402
import webcore  # noqa: E402


def comprova_cataleg():
    cat = webcore.scenario_catalog()
    assert cat, "cataleg buit"
    for e in cat:
        assert e.get("days", 0) >= 1 and e["first_day"] <= e["last_day"], f"escenari sense durada: {e['id']}"
    per_dades = {e["location"]: e for e in cat if e["kind"] == "dades"}
    assert set(per_dades) == set(dades.LLOCS), "falta 'Totes les dades' d'algun lloc"
    for lloc, e in per_dades.items():
        assert e["days"] == len(dades.dies_disponibles(lloc)), f"durada incorrecta per a {lloc}"
    return cat


def comprova_lloc_nou():
    carpeta = ROOT / "dades_reals" / "llocs"
    carpeta.mkdir(exist_ok=True)
    fitxer = carpeta / "_e17_prova.json"
    base = dades.LLOCS["ribera"]
    fitxer.write_text(json.dumps({"id": "e17_prova", **{k: getattr(base, k) for k in base.__dataclass_fields__}}), encoding="utf-8")
    try:
        dades._registra_llocs_externs()
        cat = webcore.scenario_catalog()
        nou = next(e for e in cat if e["id"] == "data:e17_prova")
        assert nou["days"] == len(dades.dies_disponibles("ribera")), "el lloc nou no hereta les dades"
    finally:
        fitxer.unlink(missing_ok=True)
        dades.LLOCS.pop("e17_prova", None)


def comprova_treball():
    import webjobs
    job = webjobs.submit({"scenario": "data:ribera", "controller": "soar", "compare": True, "start": "2023-08-10", "end": "2023-08-12",
                          "mode": "independents", "seed": 0, "modifiers": {}})
    t0 = time.time()
    while job.state in ("queued", "running"):
        assert time.time() - t0 < 240, "el treball triga massa"
        time.sleep(0.5)
    assert job.state == "done", f"treball {job.state}: {job.error}"
    r = job.result
    assert r["controllers"] == ["soar", "seguidor", "fix"] and len(r["days"]) == 3
    for c in r["controllers"]:
        assert len(r["daily"][c]) == 3, f"taula diaria incompleta per a {c}"
        assert r["daily"][c][0]["energy_kwh"] > 0
    assert r["stats"] and r["stats"]["pairs"], "falta l'estadistica aparellada"
    assert job.status()["done_days"] == 3
    d = job.day_payload("soar", "2023-08-11")
    assert d["day"] == "2023-08-11" and len(d["records"]) == 14 * 3, "registres horaris del dia incorrectes"
    return r


def main():
    cat = comprova_cataleg()
    print(f"cataleg: {len(cat)} escenaris, durades:", ", ".join(f"{e['id']}={e['days']}d" for e in cat if e['days'] > 1))
    comprova_lloc_nou()
    print("lloc nou registrat per JSON: ok")
    r = comprova_treball()
    print(f"treball en processos ({os.cpu_count()} CPU): {r['elapsed_s']} s, {len(r['stats']['pairs'])} comparacions aparellades")
    print("E17 OK - periodes llargs amb dades reals: cataleg amb durada, lloc nou per JSON, treball en processos i estadistica")


if __name__ == "__main__":      # necessari perque els processos fills (spawn) funcionin tambe a Windows
    main()
