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


# ----------------------------------------------------------------------------- balanc d'energia de la coberta
# Temperatura de la coberta pel balanc d'energia (Jackson et al. 1981):
#     Rn - G = H + lambda*E,   H = rho*cp*(Tc - Ta)/ra   =>   Tc = Ta + ra*(Rn - G - lambda*E)/(rho*cp)
# La lambda*E es l'evapotranspiracio real del balanc d'aigua (ETc = ET0*Kc*Ks*ombra), de manera que
# el reg i l'ombra refreden el cultiu amb el mateix model que fa servir el balanc hidric.
# Components de FAO-56 (Allen et al. 1998) i de la versio horaria ASCE (Snyder & Eching 2002):
# radiacio neta (eq. 38-39, amb el factor de nuvolositat de la nit igual al de l'ultima hora de dia),
# flux de calor del sol (eq. 45-46), resistencia aerodinamica (eq. 4) i vent a 2 m (eq. 47).
# Correccio d'estabilitat de ra amb el nombre de Richardson (Choudhury, Reginato & Idso 1986).

SIGMA = 5.670e-8           # W m-2 K-4
RHO_CP = 1.20 * 1013.0     # J m-3 K-1 (aire a ~20 C)
LAMBDA = 2.45e6            # J kg-1 (calor latent, FAO-56)
ALBEDO = 0.23              # FAO-56 eq. 38
GSC = 1367.0               # W m-2, constant solar


def pressio_vapor_sat(t: float) -> float:
    """kPa (FAO-56 eq. 11)."""
    return 0.6108 * math.exp(17.27 * t / (t + 237.3))


def vent_2m(u10: float) -> float:
    """Vent a 2 m a partir del de 10 m (FAO-56 eq. 47), amb el minim de 0,5 m/s de l'ASCE."""
    return max(0.5, u10 * 4.87 / math.log(67.8 * 10 - 5.42))


def factor_nuvolositat(rs: float, elev_graus: float, altitud_m: float) -> float | None:
    """f = 1,35 Rs/Rso - 0,35 (FAO-56 eq. 39). Nomes amb el sol prou alt (> 17,2 graus, ASCE);
    si no, None i es fa servir l'ultim valor de dia."""
    if elev_graus <= 17.2:
        return None
    rso = (0.75 + 2e-5 * altitud_m) * GSC * math.sin(math.radians(elev_graus))   # eq. 37
    r = min(1.0, max(0.3, rs / rso)) if rso > 0 else 0.5
    return 1.35 * r - 0.35


def radiacio_neta(rs_cultiu: float, t_aire: float, hr: float, f_nuvol: float, vista_cel: float) -> float:
    """Radiacio neta a la coberta (W/m2). L'ona curta es la que arriba al cultiu; l'ona llarga
    que es perd cap al cel es redueix en la part del cel que tapa el panell (el panell, a prop
    de la temperatura de l'aire, torna radiacio cap avall): per aixo de nit el cultiu sota el
    panell queda mes calent (Marrou et al. 2013)."""
    ea = pressio_vapor_sat(t_aire) * max(0.0, min(100.0, hr)) / 100.0
    rnl = SIGMA * (t_aire + 273.15) ** 4 * (0.34 - 0.14 * math.sqrt(ea)) * f_nuvol
    return (1 - ALBEDO) * max(rs_cultiu, 0.0) - rnl * vista_cel


def resistencia_aerodinamica(h: float, u2: float, z: float = 2.0) -> float:
    """ra (s/m) en condicions neutres (FAO-56 eq. 4): d = 2/3 h, zom = 0,123 h, zoh = 0,1 zom."""
    h = max(h, 0.05)
    d, zom = 2 * h / 3, 0.123 * h
    zoh = 0.1 * zom
    z = max(z, d + 0.5)       # mesura per sobre de la coberta (vinya alta)
    return math.log((z - d) / zom) * math.log((z - d) / zoh) / (0.41 ** 2 * u2)


def temperatura_coberta(t_aire: float, rn: float, et_mm_h: float, h: float, u2: float,
                        estabilitat: bool = True) -> float:
    """Tc pel balanc d'energia, amb G de FAO-56 (eq. 45-46) i ra corregida per estabilitat
    (estabilitat=False: ra neutra, per a l'analisi de sensibilitat)."""
    g = 0.1 * rn if rn > 0 else 0.5 * rn
    le = LAMBDA * max(et_mm_h, 0.0) / 3600.0          # W/m2
    disp = rn - g - le                                  # energia que escalfa l'aire (H)
    ra0 = resistencia_aerodinamica(h, u2)
    ra, dt = ra0, 0.0
    if not estabilitat:
        return t_aire + ra0 * disp / RHO_CP
    for _ in range(20):                                 # Choudhury et al. (1986), punt fix amortit
        ri = 5 * 9.81 * 2.0 * dt / ((t_aire + 273.15) * u2 ** 2)
        if ri >= 0:
            ra = ra0 / (1 + ri) ** 0.75                 # inestable: la convecció baixa ra
        else:
            ra = ra0 / (1 + max(ri, -0.5)) ** 2         # estable (nit): ra puja
        nou = ra * disp / RHO_CP
        if abs(nou - dt) < 0.01:
            dt = nou
            break
        dt = 0.5 * (dt + nou)
    return t_aire + dt


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


def balanc_hidric_detall(aigua_mm: float, taw: float, et0: float, kc: float, pluja: float,
                         transm: float, gcr: float = 0.0,
                         p: float | None = None) -> dict[str, float]:
    """Calcula el balanc hidric i retorna els resultats amb noms de camp."""
    aigua_nova, drenatge, et_c = pas_balanc_hidric(
        aigua_mm, taw, et0, kc, pluja, transm, gcr, p
    )
    return {
        "aigua_mm": aigua_nova,
        "drenatge_mm": drenatge,
        "et_c_mm": et_c,
    }
