"""Carrega i fusiona les dades reals (vegeu dades_reals/FONTS.md).

Resultat: un DataFrame horari en HORA LOCAL (Europe/Madrid, sense zona), una fila per
interval (t-1h, t] amb l'etiqueta t, que es el conveni d'Open-Meteo:

    temp       temperatura de l'aire a 2 m (°C)                   Open-Meteo
    hr         humitat relativa (%)                                Open-Meteo
    pluja      precipitacio (mm/h)                                 Open-Meteo
    vent       ratxa maxima a 10 m (m/s)  <- la que fa mal al seguidor   Open-Meteo
    vent_mitja vent mitja a 10 m (m/s)                             Open-Meteo
    ghi        radiacio global horitzontal (W/m², mitjana de l'hora)     Open-Meteo
    et0        evapotranspiracio de referencia FAO-56 (mm/h)       Open-Meteo
    vwc20      humitat volumetrica a 20 cm (m³/m³), mitjana de l'hora    XMS-Cat (ICGC)
    aigua_pct  aigua disponible al sol (%) calculada de vwc20      XMS-Cat + fitxa de l'estacio
    aigua_pct_camp  igual pero amb limits de camp (percentils 2-98) XMS-Cat
    pluja_xms  pluja del pluviometre de l'estacio (mm/h)           XMS-Cat
    pv_w_kwp   produccio PVGIS d'1 kWp amb seguidor N-S (W)        PVGIS (nomes per calibrar)

XMS-Cat i PVGIS donen l'hora en UTC; aqui es passa a hora local.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dades_reals")
ZONA = "Europe/Madrid"


@dataclass(frozen=True)
class Lloc:
    nom: str
    lat: float
    lon: float
    altitud: float
    # sol (fitxa de l'estacio XMS-Cat, 0-30 cm). CC i PM gravimetrics -> volumetrics amb densitat aparent
    cc_grav: float
    pm_grav: float
    densitat: float            # g/cm³ (suposada: no la dona la fitxa)
    textura: str
    fitxer_xms: str
    fitxer_om: str
    fitxer_pvgis: str

    @property
    def theta_cc(self):
        return self.cc_grav * self.densitat

    @property
    def theta_pm(self):
        return self.pm_grav * self.densitat


LLOCS = {
    "ribera": Lloc("Ribera de Sió (Balaguer)", 41.8032, 0.9097, 283, 0.27, 0.13, 1.30,
                   "argilosa (44 % argila, Haplic Regosol)",
                   "xmscat_ribera-sio_abr-set2023.csv", "openmeteo_ribera-sio_abr-set2023.json",
                   "pvgis_ribera-sio_2023.json"),
    "cantallops": Lloc("Cantallops (Alt Empordà)", 42.4198, 2.9413, 179, 0.14, 0.07, 1.50,
                       "franca-arenosa (63 % sorra, Skeletic Fluvisol)",
                       "xmscat_cantallops_gen-abr2023.csv", "openmeteo_cantallops_gen-abr2023.json",
                       "pvgis_cantallops_2023.json"),
}


def _utc_a_local(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return idx.tz_localize("UTC").tz_convert(ZONA).tz_localize(None)


def _open_meteo(lloc: Lloc) -> pd.DataFrame:
    d = json.load(open(os.path.join(DIR, lloc.fitxer_om)))
    h = pd.DataFrame(d["hourly"])
    h["time"] = pd.to_datetime(h["time"])
    h = h.set_index("time").rename(columns={
        "temperature_2m": "temp", "relative_humidity_2m": "hr", "precipitation": "pluja",
        "wind_gusts_10m": "vent", "wind_speed_10m": "vent_mitja", "shortwave_radiation": "ghi",
        "et0_fao_evapotranspiration": "et0",
        "soil_moisture_0_to_7cm": "sm_om_0_7", "soil_moisture_7_to_28cm": "sm_om_7_28"})
    # amb DST, l'hora local de la tardor es repeteix: ens quedem amb la primera
    return h[~h.index.duplicated(keep="first")]


def _xms(lloc: Lloc) -> pd.DataFrame:
    x = pd.read_csv(os.path.join(DIR, lloc.fitxer_xms), parse_dates=["TmStamp"])
    x = x.set_index("TmStamp").sort_index()
    x.index = _utc_a_local(x.index)
    x = x[~x.index.duplicated(keep="first")]
    for c in ("Pluja_Tot", "VWC_005", "VWC_020", "VWC_050", "VWC_100"):
        x[c] = pd.to_numeric(x[c], errors="coerce")
    # interval (t-1h, t]: mateix conveni que Open-Meteo
    r = x.resample("1h", label="right", closed="right")
    out = pd.DataFrame({"vwc20": r["VWC_020"].mean(), "vwc05": r["VWC_005"].mean(),
                        "pluja_xms": r["Pluja_Tot"].sum(min_count=1)})
    out["aigua_pct"] = (100 * (out["vwc20"] - lloc.theta_pm) / (lloc.theta_cc - lloc.theta_pm)).clip(0, 100)
    # Alternativa "de camp": els limits es treuen de la propia serie (percentils 2 i 98).
    # A Cantallops el sensor llegeix per sota del PM de laboratori (x densitat suposada) i amb
    # la fitxa el sol sortiria sec la meitat del temps; amb els limits de camp no.
    lo, hi = out["vwc20"].quantile(0.02), out["vwc20"].quantile(0.98)
    out["aigua_pct_camp"] = (100 * (out["vwc20"] - lo) / (hi - lo)).clip(0, 100)
    return out


def _pvgis(lloc: Lloc) -> pd.Series:
    d = json.load(open(os.path.join(DIR, lloc.fitxer_pvgis)))
    rows = d["outputs"]["hourly"]
    t = pd.to_datetime([r["time"] for r in rows], format="%Y%m%d:%H%M")
    p = pd.Series([float(r["P"]) for r in rows], index=_utc_a_local(t), name="pv_w_kwp")
    # PVGIS marca HH:10; l'arrodonim a l'hora seguent per casar amb l'interval (t-1h, t]
    p.index = p.index.floor("h") + pd.Timedelta(hours=1)
    return p[~p.index.duplicated(keep="first")]


@lru_cache(maxsize=None)
def carrega(nom_lloc: str) -> pd.DataFrame:
    lloc = LLOCS[nom_lloc]
    om = _open_meteo(lloc)
    df = om.join(_xms(lloc), how="left").join(_pvgis(lloc), how="left")
    return df


@lru_cache(maxsize=None)
def ratio_pvgis(nom_lloc: str) -> float:
    """W produits per kWp de seguidor N-S per cada W/m² de GHI d'Open-Meteo.

    Es calcula com sum(P_pvgis)/sum(GHI_open-meteo) sobre les hores amb sol del periode
    disponible (PVGIS es de SARAH3 i Open-Meteo d'ERA5: hora a hora no casen, pero en
    mitjana si). Incorpora el guany del seguidor i les perdues del sistema (14 %).
    """
    df = carrega(nom_lloc)
    m = (df["ghi"] > 50) & df["pv_w_kwp"].notna()
    return float(df.loc[m, "pv_w_kwp"].sum() / df.loc[m, "ghi"].sum())


def dies_disponibles(nom_lloc: str, complets_xms: bool = True) -> list[str]:
    """Dies amb les 24 hores d'Open-Meteo (i amb humitat XMS-Cat al mati, si cal)."""
    df = carrega(nom_lloc)
    dies = []
    for dia, g in df.groupby(df.index.date):
        if len(g) < 23:
            continue
        if complets_xms and g.between_time("05:00", "08:00")["vwc20"].isna().all():
            continue
        dies.append(str(dia))
    return dies


def resum_fonts() -> pd.DataFrame:
    """Taula per a l'informe: cobertura i estadistiques basiques de cada lloc."""
    files = []
    for k, ll in LLOCS.items():
        df = carrega(k)
        files.append({
            "lloc": ll.nom, "des_de": df.index.min(), "fins_a": df.index.max(), "hores": len(df),
            "dies_utilitzables": len(dies_disponibles(k)),
            "ratxa_max_ms": df["vent"].max(), "hores_ratxa>=16": int((df["vent"] >= 16).sum()),
            "temp_max": df["temp"].max(), "pluja_om_mm": df["pluja"].sum(),
            "pluja_xms_mm": df["pluja_xms"].sum(), "aigua_pct_min": df["aigua_pct"].min(),
            "aigua_pct_max": df["aigua_pct"].max(),
            "ratio_pvgis_W_per_kWp_per_Wm2": ratio_pvgis(k),
        })
    return pd.DataFrame(files)


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    print(resum_fonts().T)
