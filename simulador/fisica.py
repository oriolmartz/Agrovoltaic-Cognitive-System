"""Model fisic simplificat de la planta (el "mon" que el controlador no veu per dins).

Tot el que hi ha aqui son simplificacions documentades: l'objectiu es que les accions
del controlador tinguin conseqüencies coherents i mesurables, no fer un model
agronomic o elèctric exacte.

Convencio d'angles (com al CLIPS): seguidor d'un eix horitzontal nord-sud,
0° = panell horitzontal, negatiu = mira a l'est (mati), positiu = a l'oest (tarda).
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ZONA = ZoneInfo("Europe/Madrid")

# ----------------------------------------------------------------------------- sol

def posicio_solar(lat: float, lon: float, t_local: datetime) -> tuple[float, float]:
    """(elevacio, azimut) en graus. Formules NOAA simplificades (error < 1°)."""
    t_utc = t_local.replace(tzinfo=ZONA).astimezone(ZoneInfo("UTC"))
    n = t_utc.timetuple().tm_yday
    h = t_utc.hour + t_utc.minute / 60 + t_utc.second / 3600
    g = 2 * math.pi / 365 * (n - 1 + (h - 12) / 24)
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                    - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
            - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
            - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    tst = h * 60 + eqt + 4 * lon                  # temps solar vertader (min)
    ha = math.radians(tst / 4 - 180)              # angle horari
    phi = math.radians(lat)
    cosz = math.sin(phi) * math.sin(decl) + math.cos(phi) * math.cos(decl) * math.cos(ha)
    cosz = max(-1.0, min(1.0, cosz))
    zen = math.acos(cosz)
    elev = 90 - math.degrees(zen)
    az = math.degrees(math.atan2(math.sin(ha), math.cos(ha) * math.sin(phi) - math.tan(decl) * math.cos(phi))) + 180
    return elev, az % 360


def angle_seguiment(elev: float, az: float, limit: float = 55.0) -> float:
    """Angle de maxima captacio d'un seguidor N-S horitzontal (sense backtracking)."""
    if elev <= 0:
        return 0.0
    e, a = math.radians(elev), math.radians(az)
    sx = math.cos(e) * math.sin(a)          # component est (+) / oest (-)
    sz = math.sin(e)
    # el sol a l'est (sx>0) demana panell mirant a l'est = angle negatiu
    ang = -math.degrees(math.atan2(sx, sz))
    return max(-limit, min(limit, ang))


def sol_interval(lat, lon, t_fi: datetime):
    """Posicio del sol a la meitat de l'interval (t-1h, t] d'una fila horaria."""
    return posicio_solar(lat, lon, t_fi - timedelta(minutes=30))


# ----------------------------------------------------------------------------- energia

FRACCIO_DIFUSA = 0.25   # part de la radiacio que no depen gaire de l'orientacio


def factor_orientacio(angle: float, angle_optim: float) -> float:
    """Fraccio de la produccio maxima segons com d'allunyat es l'angle de l'optim."""
    d = math.radians(angle - angle_optim)
    return FRACCIO_DIFUSA + (1 - FRACCIO_DIFUSA) * max(0.0, math.cos(d))


def produccio_kw(ghi: float, angle: float, angle_optim: float, kwp: float, ratio: float) -> float:
    """ratio = W per kWp amb seguidor optim per cada W/m² de GHI (calibrat amb PVGIS)."""
    return kwp * ratio * max(ghi, 0.0) / 1000.0 * factor_orientacio(angle, angle_optim)


def demanda_kw(hora: float, base: float, pic: float, hora_pic: float = 14.0, ample: float = 4.0) -> float:
    """Demanda del sector: consum base + pic de tarda (bombes, refrigeracio)."""
    return base + pic * math.exp(-((hora - hora_pic) / ample) ** 2)


# ----------------------------------------------------------------------------- cultiu

def transmissio(angle: float, gcr: float) -> float:
    """Fraccio de la radiacio que arriba al cultiu sota els panells.

    Model de coberta: la projeccio horitzontal del panell es GCR*cos(angle). Panell pla
    (0°) = mes ombra; com mes inclinat, mes llum passa entre files. Es el supòsit del
    CLIPS (angle-ombra = 0°).
    """
    return 1.0 - gcr * abs(math.cos(math.radians(angle)))


def temperatura_cultiu(t_aire: float, rad_cultiu: float, aigua_pct: float,
                       k_rad: float = 0.006, k_sec: float = 2.0) -> float:
    """Temperatura de la coberta: aire + escalfament per radiacio + menys transpiracio si es sec."""
    return t_aire + k_rad * max(rad_cultiu, 0.0) + k_sec * (1 - aigua_pct / 100.0)


# ----------------------------------------------------------------------------- aigua

def taw_mm(theta_cc: float, theta_pm: float, zr_m: float) -> float:
    """Aigua total disponible a la zona d'arrels (FAO-56, eq. 82)."""
    return 1000.0 * (theta_cc - theta_pm) * zr_m


def pas_balanc_hidric(aigua_mm: float, taw: float, et0: float, kc: float, pluja: float,
                      transm: float, gcr: float, p: float | None = None) -> tuple[float, float, float]:
    """Una hora de balanc hidric (bucket, FAO-56 eq. 85). L'ombra redueix l'evapotranspiracio.

    ETc = ET0 * Kc * f_ombra * Ks, amb f_ombra = transmissio relativa a la de ple sol entre
    files i Ks el coeficient d'estres hidric (FAO-56 eq. 84): Ks = 1 mentre l'esgotament no
    passa de RAW = p*TAW; despres Ks = (TAW - Dr) / ((1 - p) TAW), que en funcio de l'aigua
    que queda es aigua / ((1 - p) TAW). Sense p (versions antigues) Ks = 1.
    L'aigua que passa de capacitat de camp es perd per percolacio.
    Retorna (aigua nova, percolacio, ETc real), tot en mm.
    """
    f_ombra = 0.3 + 0.7 * transm          # sota ombra total encara hi ha ~30 % d'ET (difusa, vent)
    ks = 1.0
    if p is not None and taw > 0:
        ks = max(0.0, min(1.0, aigua_mm / ((1.0 - p) * taw)))
    etc = max(et0, 0.0) * kc * f_ombra * ks
    nou = aigua_mm + max(pluja, 0.0) - etc
    perc = max(0.0, nou - taw)
    etc_real = etc if nou >= 0 else etc + nou
    return max(0.0, min(taw, nou)), perc, etc_real
