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

## Reg (v1_9)

El coneixement del reg que hi ha al CLIPS (`soar_v1_9.clp`, plantilla `reg-config` i regles
`*-reg*`) i el model d'aigua del simulador surten d'aquestes fonts:

| Coneixement | Valor | Font |
|---|---|---|
| Quan es comença a patir: s'ha gastat la fracció p de l'aigua disponible (RAW = p·TAW) | tomàquet 0,40 · enciam 0,30 · vinya (de vi) 0,45 (ja eren al CLIPS) | FAO-56 (Allen et al. 1998), cap. 8, eq. 83 i taula 22 — fao.org/4/x0490e/x0490e0e.htm |
| Quan s'ha de regar: "abans o en el moment" que s'esgota la RAW | s'anticipa a partir del 75 % de p | FAO-56, cap. 8. El 75 % és un criteri de disseny nostre |
| Quanta aigua posar: la dosi neta no pot passar del que falta per arribar a capacitat de camp (la resta es perd per percolació) | `regar-complet` = el que falta; `regar-parcial` = fins a la meitat de p | FAO-56, cap. 8. La dosi parcial és un criteri de disseny nostre |
| Estrès hídric i evapotranspiració: amb l'esgotament per sobre de RAW, l'ET baixa (coeficient Ks) | `Ks = aigua / ((1 − p)·TAW)` | FAO-56, eq. 84 (al simulador, `fisica.pas_balanc_hidric`) |
| Hora de regar: a primera hora del matí o a última hora de la tarda | hores fresques ≤ 8 h o ≥ 19 h | Diputació de Barcelona, *Gestió de l'aigua als horts* (dossier de la sessió 3) — xarxaenxarxa.diba.cat |
| L'ET màxima és de 10 a 16 h, i de dia es perd més aigua (sobretot per aspersió) | — | Clemson Cooperative Extension, *Landscape irrigation management, part 5: time of day* |
| Amb degoteig, l'hora del dia importa poc; si el cultiu necessita aigua, es pot regar a qualsevol hora | amb estrès es rega a qualsevol hora | Penn State Extension, *Does it matter what time of day you irrigate with drip irrigation?* |
| Si es preveu pluja de 10 mm o més, s'anul·la el reg | restricció dura, llevat d'estrès crític | Diputació de Barcelona (mateix dossier) |
| La pluja petita (< ~0,2·ET0) s'evapora i no compta | 2 mm | FAO-56, cap. 8 |
| Eficiència del degoteig | 0,85 | Diputació de Barcelona (mateix dossier) |
| Vinya: un estrès moderat redueix el vigor i la mida del gra amb poca pèrdua de collita (reg deficitari controlat) | la vinya no s'anticipa i es rega en part | AWRI, *An introduction to Regulated Deficit Irrigation* — awri.com.au. FAO-56 també preveu un llindar de gestió (MAD) per sobre de RAW quan l'estrès és volgut |
| Energia de la bomba (reg a pressió: degoteig i aspersió) | 0,28–0,68 kWh/m³; s'agafa 0,48 | Hardy & Garrido, *Challenges and opportunities related to the Spanish water-energy nexus*, cap. 14 de *Water, Agriculture and the Environment in Spain* (Fundación Botín) |

Supòsits nostres, sense font, que s'han de dir a l'informe:
- **El reg de la finca** (línia base `finca`): a les 7 h, si l'aigua és per sota del 45 %, s'omple fins al 90 %.
- **La superfície de cada sector:** 250 m². Surt de 20 kWp, uns 100 m² de mòduls i GCR = 0,4.
- **La previsió de pluja** és la pluja real de les pròximes 12 h, amb un soroll lognormal de σ = 0,3.
