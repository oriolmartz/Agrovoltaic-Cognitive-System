# Fonts de dades

Totes les dades son de l'any 2023 i es van descarregar a mà des de la web de cada servei
(octubre 2026). `dades.py` les llegeix i les fusiona en una taula horària en hora local.

| Fitxer | Font | Lloc | Període | Resolució | Llicència |
|---|---|---|---|---|---|
| `openmeteo_ribera-sio_abr-set2023.json` | Open-Meteo Historical Weather API (reanàlisi ERA5) — archive-api.open-meteo.com/v1/archive | 41.8032 N, 0.9097 E | 1/4–30/9/2023 | horària, hora local | CC BY 4.0 |
| `openmeteo_cantallops_gen-abr2023.json` | Open-Meteo Historical Weather API | 42.4198 N, 2.9413 E | 25/1–30/4/2023 | horària, hora local | CC BY 4.0 |
| `xmscat_ribera-sio_abr-set2023.csv` | ICGC, Xarxa de Mesura de la humitat del Sòl (XMS-Cat) — visors.icgc.cat/mesurasols | estació Ribera de Sió (RDS), Balaguer, 283 m | 1/4–30/9/2023 | 30 min, **UTC** | CC BY 4.0 (ICGC) |
| `xmscat_cantallops_gen-abr2023.csv` | ICGC XMS-Cat | estació Cantallops (CLLP), 179 m | 25/1–30/4/2023 | 30 min, **UTC** | CC BY 4.0 (ICGC) |
| `pvgis_ribera-sio_2023.json` | PVGIS 5.3 (JRC), `seriescalc`, SARAH3, seguidor d'un eix horitzontal N-S, 1 kWp, 14 % pèrdues | 41.8032 N, 0.9097 E | 2023 | horària, **UTC** | © Unió Europea |
| `pvgis_cantallops_2023.json` | PVGIS 5.3 (JRC), mateixa configuració | 42.4198 N, 2.9413 E | 2023 | horària, **UTC** | © Unió Europea |

## Propietats del sòl (fitxes de les estacions XMS-Cat, 0–30 cm)

| Estació | Sòl | Textura | CC (−33 kPa) | PM (−1500 kPa) | Densitat aparent suposada |
|---|---|---|---|---|---|
| Ribera de Sió | Haplic Regosol | 44 % argila | 27 % (grav.) | 13 % (grav.) | 1,3 g/cm³ |
| Cantallops | Skeletic Fluvisol | 63 % sorra (franca-arenosa) | 14 % (grav.) | 7 % (grav.) | 1,5 g/cm³ |

La densitat no surt a la fitxa: s'ha pres un valor típic per a cada textura.

## Què s'agafa de cada font

| Variable del simulador | Font | Per què |
|---|---|---|
| temperatura, radiació global, ratxa de vent, pluja, ET0 | Open-Meteo | sèrie horària completa, sense forats |
| humitat del sòl (mode `mesurada`, i valor inicial) | XMS-Cat (20 cm) | és mesura real; Open-Meteo és model |
| relació radiació → producció del seguidor | PVGIS | calibra el guany del seguidor i les pèrdues |

**Validació creuada Open-Meteo vs XMS-Cat** (per a l'informe):

| | Ribera de Sió | Cantallops |
|---|---|---|
| correlació humitat del sòl 0–7 cm vs 5 cm | 0,41 | 0,60 |
| correlació humitat del sòl 7–28 cm vs 20 cm | 0,56 | 0,86 |
| biaix a 20 cm (model − estació) | −0,033 (model més sec) | +0,058 (model més humit) |
| pluja total Open-Meteo / estació | 269 / 199 mm | 104 / 87 mm |

L'hora de XMS-Cat es va comprovar creuant la pluja amb Open-Meteo: la correlació és màxima
desplaçant l'estació +2 h a l'estiu, és a dir, l'estació escriu en UTC.
