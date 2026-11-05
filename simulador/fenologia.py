"""Calendari de cultiu i fase fenologica (dades d'entrada, no decisio).

El simulador diu al CLIPS en quina fase es cada cultiu i quina sensibilitat te; el CLIPS hi
raona (elaboracio de riscos). Tambe dona el Kc i l'alcada de la coberta per al balanc
d'aigua i d'energia.

Fonts (vegeu dades_reals/FONTS.md):
- Durada de les etapes (inicial, desenvolupament, mitja, final), Kc i alcada maxima:
  FAO-56 (Allen et al. 1998), taules 11 i 12, files mediterranies. Kc segons la corba de
  FAO-56 (fig. 25): constant a l'etapa inicial, lineal fins a Kc mitja, constant, i lineal
  fins a Kc final.
- Enciam: plantacions esglaonades durant l'any excepte desembre i gener (horta de Lleida,
  Paeria). Tres plantacions seguides a la mateixa parcel·la, cadascuna amb la durada de la
  fila FAO-56 de la seva epoca (febrer 140 dies, abril 75, novembre-gener 105).
- Tomaquet: plantacio d'abril-maig a la Mediterrania, 145 dies (FAO-56).
- Vinya (vi, latituds mitjanes): 210 dies des de la brotada d'abril (FAO-56); la resta de
  l'any en repos.
- Sensibilitat de cada fase: tomaquet sensible a la calor durant la floracio (quallat;
  Sato et al. 2000); vinya sensible a la floracio (la resta, reg deficitari); enciam sensible a la
  calor quan forma el cabdell i a prop de la collita (espigat). Vegeu FONTS.md.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

# Kc fora del cicle: parcel·la sense cultiu (o vinya sense fulles). Nomes evaporacio del sol;
# es el Kc inicial de la vinya a FAO-56 (taula 12), que correspon sobretot a sol nu.
KC_SENSE_CULTIU = 0.30
H_SENSE_CULTIU = 0.10        # m, rugositat de sol nu (com el codi FAO-56 de sol nu)

# etapes: (inicial, desenvolupament, mitja, final) en dies. fases: fase del CLIPS i
# sensibilitat a cada etapa. h_min: alcada al principi (fraccio de la maxima).
CULTIUS = {
    "enciam": {
        "kc": (0.70, 1.00, 0.95), "h_max": 0.30, "h_ini": 0.10,
        "plantacions": [("02-01", (35, 50, 45, 10)),     # FAO-56: febrer, Mediterrania
                        ("06-21", (20, 30, 15, 10)),     # FAO-56: abril, Mediterrania (cicle curt)
                        ("09-04", (30, 40, 25, 10))],    # FAO-56: novembre-gener, Mediterrania
        "fases": [("vegetativa", "mitja"), ("vegetativa", "mitja"),
                  ("maduracio", "alt"), ("maduracio", "alt")],
    },
    "tomaquet": {
        "kc": (0.60, 1.15, 0.80), "h_max": 0.60, "h_ini": 0.15,
        "plantacions": [("05-01", (30, 40, 45, 30))],    # FAO-56: abril-maig, Mediterrania
        # La floracio comenca unes 4 setmanes despres del trasplantament i dura fins a mitjan
        # etapa mitja (els rams floreixen esglaonats); despres quallat i maduracio.
        "fases_dies": [(30, "vegetativa", "mitja"), (75, "floracio", "alt"),
                       (115, "fructificacio", "mitja"), (145, "maduracio", "mitja")],
    },
    "vinya": {
        "kc": (0.30, 0.70, 0.45), "h_max": 1.50, "h_ini": 1.0,   # cep i espatllera: alcada fixa
        "plantacions": [("04-01", (30, 60, 40, 80))],    # FAO-56: vi, latituds mitjanes, abril
        # Brotada a l'abril, floracio a finals de maig - mitjan juny, verol a finals de juliol i
        # verema cap a mitjan setembre (Lleida, unes dues setmanes abans que Ribera del Duero:
        # Ramos et al., floracio 16/6 i verol 12/8 de mitjana). Despres de la verema la vinya
        # conserva les fulles fins a la tardor, sense raim: sensibilitat baixa.
        # Sensibilitat alta nomes a la floracio (calor i aigua afecten el quallat). La resta, baixa:
        # entre el quallat i la verema un estres moderat es el reg deficitari controlat (AWRI),
        # com ja suposava la base de coneixement (la vinya no anticipa el reg).
        "fases_dies": [(54, "vegetativa", "baix"), (75, "floracio", "alt"),
                       (115, "fructificacio", "baix"), (162, "maduracio", "baix"),
                       (210, "vegetativa", "baix")],
    },
}


@dataclass(frozen=True)
class EstatCultiu:
    actiu: bool          # hi ha cultiu (amb fulles) a la parcel·la
    fase: str            # simbol del CLIPS: vegetativa floracio fructificacio maduracio repos
    sensibilitat: str    # baix mitja alt critic
    etapa: str           # etapa FAO-56: inicial desenvolupament mitja final fora
    dia_cicle: int       # dies des de la plantacio (o -1)
    kc: float
    h: float             # alcada de la coberta (m)


def _plantacions(tipus: str, any_: int):
    """Inici i final de cada plantacio que pot tocar l'any (inclou la de l'any anterior)."""
    c = CULTIUS[tipus]
    for a in (any_ - 1, any_):
        for inici, etapes in c["plantacions"]:
            d0 = dt.date.fromisoformat(f"{a}-{inici}")
            yield d0, etapes


def estat(tipus: str, data: dt.date | str) -> EstatCultiu:
    if isinstance(data, str):
        data = dt.date.fromisoformat(data[:10])
    c = CULTIUS[tipus]
    for d0, etapes in _plantacions(tipus, data.year):
        n = (data - d0).days
        if 0 <= n < sum(etapes):
            ini, dev, mid, fi = etapes
            kci, kcm, kcf = c["kc"]
            hmax = c["h_max"]
            hini = c["h_ini"] * hmax if c["h_ini"] < 1 else hmax
            if n < ini:
                i, kc, h = 0, kci, hini
            elif n < ini + dev:
                x = (n - ini) / dev
                i, kc, h = 1, kci + x * (kcm - kci), hini + x * (hmax - hini)
            elif n < ini + dev + mid:
                i, kc, h = 2, kcm, hmax
            else:
                x = (n - ini - dev - mid) / fi
                i, kc, h = 3, kcm + x * (kcf - kcm), hmax
            if "fases_dies" in c:
                fase, sens = next((f, s) for fi_, f, s in c["fases_dies"] if n < fi_)
            else:
                fase, sens = c["fases"][i]
            etapa = ("inicial", "desenvolupament", "mitja", "final")[i]
            return EstatCultiu(True, fase, sens, etapa, n, round(kc, 3), round(h, 3))
    h = c["h_max"] if c["h_ini"] >= 1 else H_SENSE_CULTIU
    return EstatCultiu(False, "repos", "baix", "fora", -1, KC_SENSE_CULTIU, h)


if __name__ == "__main__":          # resum del calendari d'un any
    for tp in CULTIUS:
        ant = None
        for k in range(365):
            d = dt.date(2023, 1, 1) + dt.timedelta(days=k)
            e = estat(tp, d)
            if (e.fase, e.sensibilitat, e.etapa) != ant:
                print(f"{tp:9s} {d}  {e.etapa:15s} {e.fase:13s} sens {e.sensibilitat:5s} kc {e.kc}")
                ant = (e.fase, e.sensibilitat, e.etapa)
