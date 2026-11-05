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

## Dades de 2022–2023 (afegides el 04/11/2026)

| Fitxer | Font | Lloc | Període | Resolució |
|---|---|---|---|---|
| `openmeteo_ribera-sio_2022-2023.json` | Open-Meteo Historical Weather API (ERA5), mateixos camps que els fitxers de 2023 | 41.8032 N, 0.9097 E | 1/1/2022–31/12/2023 | horària (desfasament fix d'hivern, `utc_offset_seconds` = 3600) |
| `openmeteo_cantallops_2022-2023.json` | Open-Meteo Historical Weather API (ERA5) | 42.4198 N, 2.9413 E | 1/1/2022–31/12/2023 | horària |
| `xmscat_ribera-sio_2022-2023_ismn.csv` | XMS-Cat (ICGC) via **International Soil Moisture Network** (ISMN, ismn.earth), xarxa XMS-CAT, estació Ribera de Sió: humitat a 5 i 20 cm (Campbell CS655) i pluja | estació RDS | 1/1/2022–31/12/2023 (17.497 hores) | horària, UTC |
| `xmscat_cantallops_2022-2023_ismn.csv` | ISMN, xarxa XMS-CAT, estació Cantallops | estació CLLP | **1/2/2023**–31/12/2023 (l'estació no té dades del 2022) | horària, UTC |

- El visor de l'ICGC no funcionava; les mateixes dades es van baixar de l'ISMN (format "Header+values"), i s'han convertit al format dels CSV de l'ICGC. Es descarten només els valors amb marca de qualitat `C` (fora de rang).
- **Comprovació:** al període que ja teníem (2023), l'ISMN i l'ICGC donen exactament els mateixos valors (diferència màxima 0, correlació 1) i la mateixa pluja total.
- Els dies sense dades de l'estació (Cantallops 2022) es fan servir igualment: l'aigua del sòl la calcula el balanç hídric del simulador.
- **Calibració de la producció (iteració 25):** el factor de PVGIS es calcula **mes a mes** amb tot el 2023 (PVGIS i Open-Meteo d'aquell any), i cada dia fa servir el del seu mes, sigui del 2022 o del 2023. Els llocs `ribera` i `cantallops` es calibren amb les dades dels llocs de 2022–2023, que coincideixen amb les seves al període comú.
- Cal citar l'ISMN i la xarxa XMS-CAT (condicions d'ús de l'ISMN).

## Model físic del cultiu (bloc 1, 05/11/2026)

### Temperatura de la coberta: balanç d'energia (`fisica.temperatura_coberta`)

`Tc = Ta + ra·(Rn − G − λE)/(ρ·cp)`. Totes les peces surten de les fonts següents; el model **no té cap coeficient ajustat a mà**:

| Peça | Font | Què se n'agafa |
|---|---|---|
| Forma del balanç i relació Tc − Ta | Jackson, R.D., Idso, S.B., Reginato, R.J. & Pinter, P.J. (1981). Canopy temperature as a crop water stress indicator. *Water Resources Research* 17, 1133–1138 | La coberta s'escalfa per sobre de l'aire amb l'energia que no es fa servir per transpirar |
| λE (transpiració) | FAO-56 (Allen, Pereira, Raes & Smith 1998), *Crop evapotranspiration*, FAO Irrigation and Drainage Paper 56 | ETc = ET0·Kc·Ks del mateix balanç hídric del simulador: el reg i la falta d'aigua canvien la temperatura del cultiu |
| Radiació neta, G, ra, vent a 2 m | FAO-56, eq. 4, 11, 37–39, 45–47 | albedo 0,23; ona llarga amb el factor de núvols; G = 0,1·Rn de dia i 0,5·Rn de nit; d = 2/3·h, zom = 0,123·h, zoh = 0,1·zom |
| Versió horària | Snyder, R.L. & Eching, S. (2002, rev. 2008). *Penman-Monteith (hourly) reference evapotranspiration equations*. UC Davis / California DWR | el factor de núvols de nit és el de l'última hora amb el sol a més de 17,2°; vent mínim de 0,5 m/s |
| Estabilitat de l'aire | Choudhury, B.J., Reginato, R.J. & Idso, S.B. (1986). An analysis of infrared temperature observations over wheat and calculation of latent heat flux. *Agricultural and Forest Meteorology* 37, 75–88 | ra/(1+Ri)^0,75 amb aire inestable i ra/(1+Ri)^2 amb aire estable |
| Humitat relativa i vent mitjà | Open-Meteo (ja als fitxers) | dèficit de pressió de vapor i resistència aerodinàmica |

**Suposició pròpia:** sota el panell, l'ona llarga que el cultiu perd cap al cel es multiplica per la fracció de cel que es veu (la mateixa transmissió del panell). El panell és a prop de la temperatura de l'aire i torna radiació cap avall.

**Validació** (`verificacio/v_temperatura_coberta.py`, tot el 2023 a Ribera, comparat amb Marrou, H. et al. (2013). Microclimate under agrivoltaic systems: Is crop growth rate affected in the partial shade of solar panels? *Agricultural and Forest Meteorology* 177, 117–132):

| | Model (enciam / tomàquet / vinya) | Marrou et al. 2013 (mesurat) |
|---|---|---|
| Sota el panell − a ple sol, migdia | −4,5 / −4,9 / −1,4 °C | −5 a −5,7 °C (enciam, cogombre), −3 °C (blat) |
| Sota el panell − a ple sol, nit (21–01 h) | +5,8 / +3,3 / +0,6 °C | fins a +4,3 °C (enciam), +2 °C (blat) |
| Fórmula d'abans (0,006·llum), migdia | −1,7 °C per a tots | — |

La fórmula anterior donava unes tres vegades menys efecte de l'ombra que el mesurat. La vinya en surt poc afectada perquè és alta i ben ventilada (ra petita).

### Calendari de cultiu i fase fenològica (`fenologia.py`)

| Cultiu | Calendari | Font |
|---|---|---|
| Enciam | 3 plantacions seguides: 1/2 (140 dies), 21/6 (75 dies), 4/9 (105 dies); sense cultiu del 18/12 al 31/1 | Durades: FAO-56, taula 11 (files mediterrànies de febrer, abril i novembre-gener). Època: horta de Lleida, "sempre menys el desembre i el gener" (Paeria, *L'hort a la tardor*) |
| Tomàquet | Trasplantament l'1/5, 145 dies (fins al 22/9) | FAO-56, taula 11 (abril-maig, Mediterrània) |
| Vinya | Brotada l'1/4, 210 dies; repòs del 28/10 al 31/3 | FAO-56, taula 11 (vi, latituds mitjanes, abril). Floració a finals de maig - mitjan juny, verol a finals de juliol i verema cap a mitjan setembre: unes dues setmanes abans que a Ribera del Duero (Ramos, Jones & Yuste: floració 16/6, verol 12/8 de mitjana; Universitat de Lleida). A Raimat (Costers del Segre), el 2022 la verema del chardonnay va començar el 29/7 (Nació Digital, 2/8/2022) |
| Kc i alçada | Corba de FAO-56 (fig. 25) amb els Kc i les alçades màximes de la taula 12. Sense cultiu, Kc = 0,30 (evaporació del sòl) | FAO-56 |

| Fase de més sensibilitat | Per què | Font |
|---|---|---|
| Tomàquet en floració | el quallat falla amb calor moderada continuada (32/26 °C dia/nit) | Sato, S., Peet, M.M. & Thomas, J.F. (2000). *Plant, Cell and Environment* 23, 719–726 |
| Enciam formant el cabdell i a prop de la collita | la calor fa que s'espigui i amargui | criteri agronòmic general (fitxes de cultiu) |
| Vinya en floració | calor i falta d'aigua redueixen el quallat; la resta del cicle, sensibilitat baixa (reg deficitari controlat, ja suposat a la base de coneixement, AWRI) | — |

**Limitacions:** les dates són fixes cada any (no depenen dels graus-dia); la profunditat d'arrels és constant; l'enciam es torna a plantar el mateix dia que es cull.
