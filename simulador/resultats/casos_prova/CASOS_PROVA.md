# Casos de prova (soar)

Generat per `python verificacio/casos_prova.py`. El resultat esperat de cada cas s'ha escrit abans d'executar-lo, a partir del domini. La traça completa de cada cas és a `resultats/casos_prova/CPxx_traca.txt`.

| Cas | Títol | Cobertura | Cicles | Resultat |
|---|---|---|---|---|
| CP01 | Operació normal | normalitat | 2 | ❌ discrepància |
| CP02 | Vent crític | seguretat | 1 | ✅ correcte |
| CP03 | Seguretat anticipada per previsió | seguretat | 1 | ✅ correcte |
| CP04 | Límit del vent: 15,9 contra 16,0 m/s | límits | 2 | ✅ correcte |
| CP05 | Conflicte cultiu contra energia (impasse d'empat i chunking) | conflicte | 2 | ✅ correcte |
| CP06 | Sensor de vent caigut, sense indicis de perill | dades absents | 2 | ✅ correcte |
| CP07 | Sensor de vent caigut després d'una ratxa crítica (historial) | dades absents + historial | 2 | ✅ correcte |
| CP08 | Fallada d'actuador | fallades | 2 | ✅ correcte |
| CP09 | Vent que puja i baixa al llarg de 5 hores | canvis temporals | 5 | ✅ correcte |
| CP10 | Estrès hídric de l'enciam | protecció del cultiu | 1 | ✅ correcte |
| CP11 | Radiació i calor alhora al tomàquet | protecció del cultiu + elaboració | 1 | ✅ correcte |
| CP12 | Reg a primera hora | protecció del cultiu (reg) | 2 | ✅ correcte |
| CP13 | No es rega perquè plourà | conflicte cultiu contra estalvi d'aigua (reg) | 1 | ✅ correcte |
| CP14 | Reg deficitari de la vinya al llindar | límits (reg) | 3 | ✅ correcte |

**13 de 14 casos correctes.** Hi ha un cas més amb dades reals de dies que no es van fer servir durant el desenvolupament: és `escenaris/cas_no_vist_tramuntana.json` (vegeu el README).

## CP01 – Operació normal

**Cobertura:** normalitat. **Objectiu i resultat esperat:** Sense cap risc, el sistema ha de seguir el sol i, quan ja hi és, no moure's.

| Cicle | Sector | Entrada (vent / previsió / T cultiu / aigua / radiació) | Esperat | Obtingut | |
|---|---|---|---|---|---|
| 1 | Sector_1 (tomàquet) | 3.0 / 3.0 / 22.0 / 90.0 / 300.0 | accio = orientar-produccio; risc mecanic = cap; risc temperatura = cap | orientar-produccio (30.0°) | ✅ |
| 1 | Sector_3 (vinya) | 3.0 / 3.0 / 24.0 / 90.0 / 400.0 | accio = orientar-produccio | orientar-produccio (30.0°) | ✅ |
| 2 | Sector_1 (tomàquet) | 3.0 / 3.0 / 22.0 / 90.0 / 300.0 | accio = mantenir-posicio | orientar-produccio (30.0°) | ❌ acció esperada mantenir-posicio, obtinguda orientar-produccio |
| 2 | Sector_3 (vinya) | 3.0 / 3.0 / 24.0 / 90.0 / 400.0 | accio = mantenir-posicio | orientar-produccio (30.0°) | ❌ acció esperada mantenir-posicio, obtinguda orientar-produccio |

**Anàlisi de la discrepància** (feta a mà): Al cicle 2 el sistema torna a triar orientar-produccio (7 punts: energia 3 + estabilitat 2, perquè és el que va fer el cicle anterior, + memòria episòdica 2, perquè va funcionar bé) i no mantenir-posicio (4 punts: ja és a l'angle òptim 3 + sense moviment 1). L'angle ordenat és el mateix (30°) i el panell no es mou: el comportament és el correcte i l'expectativa estava massa especificada (fixava el nom de l'operador). El que mostra és interessant: l'estabilitat i la memòria episòdica fan que el sistema repeteixi el que li ha anat bé.

**Explicació que dona el sistema** (fet `explicacio`):

- Cicle 1, Sector_1: orientar-produccio a 30.0 graus. Riscos: cap. Candidats: mantenir-posicio(1) orientar-produccio(3). Descartats: cap. Criteri: maxima valoracio (3 punts).
- Cicle 1, Sector_3: orientar-produccio a 30.0 graus. Riscos: cap. Candidats: mantenir-posicio(1) orientar-produccio(3). Descartats: cap. Criteri: maxima valoracio (3 punts).
- Cicle 2, Sector_1: orientar-produccio a 30.0 graus. Riscos: cap. Candidats: mantenir-posicio(4) orientar-produccio(7.0). Descartats: cap. Criteri: maxima valoracio (7.0 punts).
- Cicle 2, Sector_3: orientar-produccio a 30.0 graus. Riscos: cap. Candidats: mantenir-posicio(4) orientar-produccio(7.0). Descartats: cap. Criteri: maxima valoracio (7.0 punts).

<details><summary>Traça rellevant del CLIPS</summary>

```
--- cicle 1 ---
[PROPOSTA] Sector_3: mantenir-posicio (20.0 graus).
[PROPOSTA] Sector_3: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_1: mantenir-posicio (20.0 graus).
[PROPOSTA] Sector_1: orientar-produccio (30.0 graus).
[AVALUACIO] Sector_1: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_3: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_1: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_3: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_1: no-regar +1 (estalvi d'aigua).
[AVALUACIO] Sector_3: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_1: es selecciona orientar-produccio. Criteri: maxima valoracio (3 punts).
[SELECCIO] Sector_3: es selecciona orientar-produccio. Criteri: maxima valoracio (3 punts).
[SELECCIO] Sector_1: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO] Sector_3: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_3: ORDRE orientar-produccio -> 30.0 graus.
[APLICACIO] Sector_1: ORDRE orientar-produccio -> 30.0 graus.
[EXPLICACIO] Sector_1, cicle 1
[EXPLICACIO] Sector_3, cicle 1
[EPMEM] NOU EPISODI #1: Sector_1, cicle 1, orientar-produccio.
[EPMEM] NOU EPISODI #3: Sector_3, cicle 1, orientar-produccio.
--- cicle 2 ---
[EPMEM] Sector_3: l'episodi #3 (orientar-produccio) es valora 'bona' (resultat correcte, risc 0 -> 0).
[EPMEM] Sector_1: l'episodi #1 (orientar-produccio) es valora 'bona' (resultat correcte, risc 0 -> 0).
[PROPOSTA] Sector_3: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_3: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_1: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_1: orientar-produccio (30.0 graus).
[AVALUACIO] Sector_1: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_3: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_1: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_3: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_1: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_3: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_3: orientar-produccio +2 (es el que es va fer el cicle anterior).
[AVALUACIO] Sector_1: orientar-produccio +2 (es el que es va fer el cicle anterior).
[AVALUACIO] Sector_1: orientar-produccio 2.0 (memoria: a l'episodi #1, cicle 1, va funcionar be, similitud 1.0).
[AVALUACIO] Sector_3: orientar-produccio 2.0 (memoria: a l'episodi #3, cicle 1, va funcionar be, similitud 1.0).
[AVALUACIO] Sector_1: no-regar +1 (estalvi d'aigua).
[AVALUACIO] Sector_3: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_1: es selecciona orientar-produccio. Criteri: maxima valoracio (7.0 punts).
[REFORC] Sector_3: orientar-produccio del cicle 1 -> recompensa 1.0 (bona), error 1.0, 4 rajoles actualitzades.
[REFORC] Sector_2: orientar-produccio del cicle 1 -> recompensa 1.0 (bona), error 0.85, 4 rajoles actualitzades.
[REFORC] Sector_1: orientar-produccio del cicle 1 -> recompensa 1.0 (bona), error 0.72, 4 rajoles actualitzades.
[SELECCIO] Sector_3: es selecciona orientar-produccio. Criteri: maxima valoracio (7.0 punts).
[SELECCIO] Sector_1: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO] Sector_3: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_3: ORDRE orientar-produccio -> 30.0 graus.
[APLICACIO] Sector_1: ORDRE orientar-produccio -> 30.0 graus.
[EXPLICACIO] Sector_1, cicle 2
[EXPLICACIO] Sector_3, cicle 2
[EPMEM] NOU EPISODI #4: Sector_1, cicle 2, orientar-produccio.
[EPMEM] NOU EPISODI #6: Sector_3, cicle 2, orientar-produccio.
```

</details>

## CP02 – Vent crític

**Cobertura:** seguretat. **Objectiu i resultat esperat:** Amb una ratxa de 18 m/s (≥ 16, el màxim del fabricant), el panell ha d'anar a la posició de seguretat, i la resta d'opcions han de quedar rebutjades. Els altres sectors no se n'han de veure afectats.

| Cicle | Sector | Entrada (vent / previsió / T cultiu / aigua / radiació) | Esperat | Obtingut | |
|---|---|---|---|---|---|
| 1 | Sector_1 (tomàquet) | 18.0 / 3.0 / 22.0 / 90.0 / 300.0 | accio = posicio-seguretat; risc mecanic = critic; rebutjat = orientar-produccio | posicio-seguretat (0.0°); riscos: mecanic=critic | ✅ |
| 1 | Sector_2 (enciam) | 3.0 / 3.0 / 16.0 / 90.0 / 150.0 | acció ≠ posicio-seguretat | mantenir-posicio (30.0°) | ✅ |

**Explicació que dona el sistema** (fet `explicacio`):

- Cicle 1, Sector_1: posicio-seguretat a 0.0 graus. Riscos: mecanic=critic. Candidats: posicio-seguretat(0). Descartats: mantenir-posicio orientar-produccio. Criteri: unica opcio que compleix les restriccions dures.
- Cicle 1, Sector_2: mantenir-posicio a 30.0 graus. Riscos: cap. Candidats: mantenir-posicio(4) orientar-produccio(3). Descartats: cap. Criteri: maxima valoracio (4 punts).

<details><summary>Traça rellevant del CLIPS</summary>

```
--- cicle 1 ---
[ELABORACIO] Sector_1: vent 18.0 m/s (previsio 3.0) >= 16.0 m/s. Risc mecanic critic.
[ELABORACIO] El risc mecanic de Sector_1 activa l'objectiu Obj_Seguretat.
[PROPOSTA] Sector_2: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_2: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_1: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_1: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_1: posicio-seguretat (0.0 graus).
[AVALUACIO] Sector_1: REBUIG de orientar-produccio (vent critic, restriccio de seguretat).
[AVALUACIO] Sector_1: REBUIG de mantenir-posicio (vent critic, restriccio de seguretat).
[AVALUACIO] Sector_1: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_2: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_1: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_2: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_1: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_2: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_1: no-regar +1 (estalvi d'aigua).
[AVALUACIO] Sector_2: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_1: orientar-produccio queda descartat (AV1-vent-critic).
[SELECCIO] Sector_1: mantenir-posicio queda descartat (AV1-vent-critic).
[SELECCIO] Sector_1: es selecciona posicio-seguretat. Criteri: unica opcio que compleix les restriccions dures.
[SELECCIO] Sector_2: es selecciona mantenir-posicio. Criteri: maxima valoracio (4 punts).
[SELECCIO] Sector_1: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO] Sector_2: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_2: ORDRE mantenir-posicio -> 30.0 graus.
[APLICACIO] Sector_1: ORDRE posicio-seguretat -> 0.0 graus.
[EXPLICACIO] Sector_1, cicle 1
[EXPLICACIO] Sector_2, cicle 1
[EPMEM] NOU EPISODI #1: Sector_1, cicle 1, posicio-seguretat.
[EPMEM] NOU EPISODI #2: Sector_2, cicle 1, mantenir-posicio.
```

</details>

## CP03 – Seguretat anticipada per previsió

**Cobertura:** seguretat. **Objectiu i resultat esperat:** El vent ara és de 6 m/s, però la previsió per a la propera hora és de 17 m/s. El sistema s'ha d'avançar i posar el panell en seguretat.

| Cicle | Sector | Entrada (vent / previsió / T cultiu / aigua / radiació) | Esperat | Obtingut | |
|---|---|---|---|---|---|
| 1 | Sector_1 (tomàquet) | 6.0 / 17.0 / 22.0 / 90.0 / 300.0 | accio = posicio-seguretat; risc mecanic = critic | posicio-seguretat (0.0°); riscos: mecanic=critic | ✅ |

**Explicació que dona el sistema** (fet `explicacio`):

- Cicle 1, Sector_1: posicio-seguretat a 0.0 graus. Riscos: mecanic=critic. Candidats: posicio-seguretat(0). Descartats: mantenir-posicio orientar-produccio. Criteri: unica opcio que compleix les restriccions dures.

<details><summary>Traça rellevant del CLIPS</summary>

```
--- cicle 1 ---
[ELABORACIO] Sector_1: vent 6.0 m/s (previsio 17.0) >= 16.0 m/s. Risc mecanic critic.
[ELABORACIO] El risc mecanic de Sector_1 activa l'objectiu Obj_Seguretat.
[PROPOSTA] Sector_1: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_1: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_1: posicio-seguretat (0.0 graus).
[AVALUACIO] Sector_1: REBUIG de orientar-produccio (vent critic, restriccio de seguretat).
[AVALUACIO] Sector_1: REBUIG de mantenir-posicio (vent critic, restriccio de seguretat).
[AVALUACIO] Sector_1: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_1: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_1: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_1: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_1: orientar-produccio queda descartat (AV1-vent-critic).
[SELECCIO] Sector_1: mantenir-posicio queda descartat (AV1-vent-critic).
[SELECCIO] Sector_1: es selecciona posicio-seguretat. Criteri: unica opcio que compleix les restriccions dures.
[SELECCIO] Sector_1: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_1: ORDRE posicio-seguretat -> 0.0 graus.
[EXPLICACIO] Sector_1, cicle 1
[EPMEM] NOU EPISODI #1: Sector_1, cicle 1, posicio-seguretat.
```

</details>

## CP04 – Límit del vent: 15,9 contra 16,0 m/s

**Cobertura:** límits. **Objectiu i resultat esperat:** A 15,9 m/s el risc és alt: la posició de seguretat és candidata, però no obligatòria. A 16,0 m/s el risc és crític i la seguretat és obligatòria.

| Cicle | Sector | Entrada (vent / previsió / T cultiu / aigua / radiació) | Esperat | Obtingut | |
|---|---|---|---|---|---|
| 1 | Sector_1 (tomàquet) | 15.9 / 15.9 / 22.0 / 90.0 / 300.0 | risc mecanic = alt; candidat = posicio-seguretat | posicio-seguretat (0.0°); riscos: mecanic=alt | ✅ |
| 2 | Sector_1 (tomàquet) | 16.0 / 16.0 / 22.0 / 90.0 / 300.0 | accio = posicio-seguretat; risc mecanic = critic; rebutjat = orientar-produccio | posicio-seguretat (0.0°); riscos: mecanic=critic | ✅ |

**Explicació que dona el sistema** (fet `explicacio`):

- Cicle 1, Sector_1: posicio-seguretat a 0.0 graus. Riscos: mecanic=alt. Candidats: mantenir-posicio(4) orientar-produccio(3) posicio-seguretat(10). Descartats: cap. Criteri: maxima valoracio (10 punts).
- Cicle 2, Sector_1: posicio-seguretat a 0.0 graus. Riscos: mecanic=critic. Candidats: posicio-seguretat(3.5). Descartats: mantenir-posicio orientar-produccio. Criteri: unica opcio que compleix les restriccions dures.

<details><summary>Traça rellevant del CLIPS</summary>

```
--- cicle 1 ---
[ELABORACIO] Sector_1: vent 15.9 m/s (previsio 15.9) >= 12.0 m/s. Risc mecanic alt.
[ELABORACIO] El risc mecanic de Sector_1 activa l'objectiu Obj_Seguretat.
[PROPOSTA] Sector_1: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_1: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_1: posicio-seguretat (0.0 graus).
[AVALUACIO] Sector_1: posicio-seguretat +10 (seguretat, vent alt).
[AVALUACIO] Sector_1: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_1: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_1: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_1: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_1: es selecciona posicio-seguretat. Criteri: maxima valoracio (10 punts).
[SELECCIO] Sector_1: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_1: ORDRE posicio-seguretat -> 0.0 graus.
[EXPLICACIO] Sector_1, cicle 1
[EPMEM] NOU EPISODI #1: Sector_1, cicle 1, posicio-seguretat.
--- cicle 2 ---
[ELABORACIO] Sector_1: vent 16.0 m/s (previsio 16.0) >= 16.0 m/s. Risc mecanic critic.
[ELABORACIO] El risc mecanic de Sector_1 activa l'objectiu Obj_Seguretat.
[EPMEM] Sector_1: l'episodi #1 (posicio-seguretat) es valora 'bona' (resultat correcte, risc 0 -> 0).
[PROPOSTA] Sector_1: mantenir-posicio (0.0 graus).
[PROPOSTA] Sector_1: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_1: posicio-seguretat (0.0 graus).
[AVALUACIO] Sector_1: REBUIG de orientar-produccio (vent critic, restriccio de seguretat).
[AVALUACIO] Sector_1: REBUIG de mantenir-posicio (vent critic, restriccio de seguretat).
[AVALUACIO] Sector_1: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_1: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_1: posicio-seguretat +2 (es el que es va fer el cicle anterior).
[AVALUACIO] Sector_1: posicio-seguretat 1.5 (memoria: a l'episodi #1, cicle 1, va funcionar be, similitud 0.75).
[AVALUACIO] Sector_1: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_1: orientar-produccio queda descartat (AV1-vent-critic).
[SELECCIO] Sector_1: mantenir-posicio queda descartat (AV1-vent-critic).
[SELECCIO] Sector_1: es selecciona posicio-seguretat. Criteri: unica opcio que compleix les restriccions dures.
[REFORC] Sector_3: mantenir-posicio del cicle 1 -> recompensa 1.0 (bona), error 1.0, 4 rajoles actualitzades.
[REFORC] Sector_2: mantenir-posicio del cicle 1 -> recompensa 1.0 (bona), error 0.85, 4 rajoles actualitzades.
[REFORC] Sector_1: posicio-seguretat del cicle 1 -> recompensa 1.0 (bona), error 1.0, 5 rajoles actualitzades.
[SELECCIO] Sector_1: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_1: ORDRE posicio-seguretat -> 0.0 graus.
[EXPLICACIO] Sector_1, cicle 2
[EPMEM] NOU EPISODI #4: Sector_1, cicle 2, posicio-seguretat.
```

</details>

## CP05 – Conflicte cultiu contra energia (impasse d'empat i chunking)

**Cobertura:** conflicte. **Objectiu i resultat esperat:** L'enciam és a 26,5 °C (risc de temperatura alt) i la producció no cobreix la demanda. Fer ombra (cultiu) i seguir el sol (energia) valen el mateix: hi ha d'haver un impasse d'empat. S'ha de resoldre a favor del cultiu, perquè té més prioritat, i s'ha d'aprendre un chunk. Al cicle següent, en la mateixa situació, el chunk ha de decidir sense impasse.

| Cicle | Sector | Entrada (vent / previsió / T cultiu / aigua / radiació) | Esperat | Obtingut | |
|---|---|---|---|---|---|
| 1 | Sector_2 (enciam) | 2.0 / 3.0 / 26.5 / 84.0 / 30.0 | accio = orientar-ombra; impasse = empat; risc temperatura = alt | orientar-ombra (0.0°); riscos: temperatura=alt; impasse empat; chunk | ✅ |
| 2 | Sector_2 (enciam) | 2.0 / 3.0 / 26.5 / 84.0 / 30.0 | accio = orientar-ombra; impasse = cap; decideix un chunk | orientar-ombra (0.0°); riscos: temperatura=alt; chunk | ✅ |

**Explicació que dona el sistema** (fet `explicacio`):

- Cicle 1, Sector_2: orientar-ombra a 0.0 graus. Riscos: temperatura=alt. Candidats: mantenir-posicio(1) orientar-produccio(6) orientar-ombra(6). Descartats: cap. Criteri: empat amb orientar-produccio desfet per IMPAS-prioritat.
- Cicle 2, Sector_2: orientar-ombra a 0.0 graus. Riscos: temperatura=alt. Candidats: mantenir-posicio(1) orientar-produccio(6) orientar-ombra(10.0). Descartats: cap. Criteri: maxima valoracio (10.0 punts).

<details><summary>Traça rellevant del CLIPS</summary>

```
--- cicle 1 ---
[ELABORACIO] Sector_2: enciam a 26.5 C (optim fins a 21.0, maxim 30.0). Risc de temperatura alt.
[ELABORACIO] El risc temperatura de Sector_2 activa l'objectiu Obj_Produccio_Cultiu.
[PROPOSTA] Sector_2: mantenir-posicio (0.0 graus).
[PROPOSTA] Sector_2: orientar-produccio (-55.0 graus).
[PROPOSTA] Sector_2: orientar-ombra (0.0 graus), hi ha risc per al cultiu.
[AVALUACIO] Sector_2: orientar-ombra +6 (cultiu, risc temperatura alt).
[AVALUACIO] Sector_2: orientar-produccio +6 (energia, produccio 0.5 / demanda 6.6).
[AVALUACIO] Sector_2: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_2: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_2: IMPAS D'EMPAT entre orientar-ombra i orientar-produccio (tots dos 6 punts).
[SELECCIO] Sector_2: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> IMPAS]
[IMPAS] Sector_2: subobjectiu resoldre-empat. Obj_Produccio_Cultiu te prioritat sobre Obj_Produccio_Energia -> orientar-ombra millor que orientar-produccio.
[CHUNKING] Nova regla chunk-1: situacio coneguda, orientar-ombra millor que orientar-produccio (valor ajustable pel reforç).
[IMPAS -> SELECCIO]
[SELECCIO] Sector_2: es selecciona orientar-ombra. Criteri: empat amb orientar-produccio desfet per IMPAS-prioritat.
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_2: ORDRE orientar-ombra -> 0.0 graus.
[EXPLICACIO] Sector_2, cicle 1
   Criteri:    empat amb orientar-produccio desfet per IMPAS-prioritat
[EPMEM] NOU EPISODI #3: Sector_2, cicle 1, orientar-ombra.
--- cicle 2 ---
[ELABORACIO] Sector_2: enciam a 26.5 C (optim fins a 21.0, maxim 30.0). Risc de temperatura alt.
[ELABORACIO] El risc temperatura de Sector_2 activa l'objectiu Obj_Produccio_Cultiu.
[EPMEM] Sector_2: l'episodi #3 (orientar-ombra) es valora 'bona' (resultat correcte, risc 2 -> 2).
[PROPOSTA] Sector_2: mantenir-posicio (0.0 graus).
[PROPOSTA] Sector_2: orientar-produccio (-55.0 graus).
[PROPOSTA] Sector_2: orientar-ombra (0.0 graus), hi ha risc per al cultiu.
[AVALUACIO] Sector_2: orientar-ombra +6 (cultiu, risc temperatura alt).
[AVALUACIO] Sector_2: orientar-produccio +6 (energia, produccio 0.5 / demanda 6.6).
[AVALUACIO] Sector_2: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_2: orientar-ombra +2 (es el que es va fer el cicle anterior).
[AVALUACIO] Sector_2: orientar-ombra 2.0 (memoria: a l'episodi #3, cicle 1, va funcionar be, similitud 1.0).
[AVALUACIO] Sector_2: no-regar +1 (estalvi d'aigua).
[chunk-1] Sector_2: situacio coneguda, orientar-ombra millor que orientar-produccio (valor ajustable pel reforç).
[SELECCIO] Sector_2: es selecciona orientar-ombra. Criteri: maxima valoracio (10.0 punts).
[REFORC] Sector_2: orientar-ombra del cicle 1 -> recompensa 1.0 (bona), error 0.5, 6 rajoles actualitzades.
[REFORC] Sector_3: orientar-produccio del cicle 1 -> recompensa 1.0 (bona), error 1.0, 4 rajoles actualitzades.
[REFORC] Sector_1: orientar-produccio del cicle 1 -> recompensa 1.0 (bona), error 0.85, 4 rajoles actualitzades.
[SELECCIO] Sector_2: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_2: ORDRE orientar-ombra -> 0.0 graus.
[EXPLICACIO] Sector_2, cicle 2
[EPMEM] NOU EPISODI #4: Sector_2, cicle 2, orientar-ombra.
```

</details>

## CP06 – Sensor de vent caigut, sense indicis de perill

**Cobertura:** dades absents. **Objectiu i resultat esperat:** No arriba la lectura de vent de l'enciam i la previsió és tranquil·la. No es pot garantir la seguretat, però tampoc no hi ha cap motiu per moure el panell: impasse de dades → demanar dades i mantenir l'angle. Al cicle següent, el chunk ho ha de resoldre sense impasse.

| Cicle | Sector | Entrada (vent / previsió / T cultiu / aigua / radiació) | Esperat | Obtingut | |
|---|---|---|---|---|---|
| 1 | Sector_2 (enciam) | absent / 3.0 / 16.0 / 90.0 / 150.0 | accio = sollicitar-dades; impasse = dades-insuficients; risc dades = critic | sollicitar-dades (30.0°); riscos: dades=critic; impasse dades-insuficients | ✅ |
| 2 | Sector_2 (enciam) | absent / 3.0 / 16.0 / 90.0 / 150.0 | accio = sollicitar-dades; impasse = cap; decideix un chunk | sollicitar-dades (30.0°); riscos: dades=critic; chunk | ✅ |

**Explicació que dona el sistema** (fet `explicacio`):

- Cicle 1, Sector_2: sollicitar-dades a 30.0 graus. Riscos: dades=critic. Candidats: mantenir-posicio(4) orientar-produccio(3) sollicitar-dades(1000). Descartats: cap. Criteri: preferencia requerida (IMPAS-dades).
- Cicle 2, Sector_2: sollicitar-dades a 30.0 graus. Riscos: dades=critic. Candidats: mantenir-posicio(4) orientar-produccio(3) sollicitar-dades(1004.0). Descartats: cap. Criteri: preferencia requerida (chunk-1).

<details><summary>Traça rellevant del CLIPS</summary>

```
--- cicle 1 ---
[PERCEPCIO] Sector_2: falten lectures (vent=absent, temp-cultiu=16.0, humitat=90.0, radiacio=150.0). Risc de dades critic.
[PROPOSTA] Sector_2: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_2: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_2: sollicitar-dades (no es mou el panell).
[AVALUACIO] Sector_2: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_2: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_2: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_2: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_2: IMPAS DE DADES INSUFICIENTS. Sense lectura fiable de vent no es pot saber si moure el panell es segur.
[SELECCIO] Sector_2: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> IMPAS]
[IMPAS] Sector_2: subobjectiu resoldre-dades. Falta la lectura de vent i ni la previsio ni l'historial indiquen vent fort. Es demanen dades i es mante la posicio.
[CHUNKING] Nova regla chunk-1: sense lectura de vent i res no indica vent fort, sollicitar-dades requerida i panell en hold.
[IMPAS -> SELECCIO]
[SELECCIO] Sector_2: es selecciona sollicitar-dades. Criteri: preferencia requerida (IMPAS-dades).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_2: ORDRE sollicitar-dades -> 30.0 graus.
[EXPLICACIO] Sector_2, cicle 1
   Criteri:    preferencia requerida (IMPAS-dades)
[EPMEM] NOU EPISODI #3: Sector_2, cicle 1, sollicitar-dades.
[MONITORATGE] Sector_2: cal demanar al simulador les lectures que falten (risc de dades critic).
--- cicle 2 ---
[PERCEPCIO] Sector_2: falten lectures (vent=absent, temp-cultiu=16.0, humitat=90.0, radiacio=150.0). Risc de dades critic.
[EPMEM] Sector_2: l'episodi #3 (sollicitar-dades) es valora 'bona' (resultat correcte, risc 0 -> 0).
[PROPOSTA] Sector_2: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_2: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_2: sollicitar-dades (no es mou el panell).
[AVALUACIO] Sector_2: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_2: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_2: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_2: sollicitar-dades +2 (es el que es va fer el cicle anterior).
[AVALUACIO] Sector_2: sollicitar-dades 2.0 (memoria: a l'episodi #3, cicle 1, va funcionar be, similitud 1.0).
[AVALUACIO] Sector_2: no-regar +1 (estalvi d'aigua).
[chunk-1] Sector_2: sense lectura de vent i res no indica vent fort, sollicitar-dades requerida i panell en hold.
[SELECCIO] Sector_2: es selecciona sollicitar-dades. Criteri: preferencia requerida (chunk-1).
[REFORC] Sector_2: sollicitar-dades del cicle 1 -> recompensa 1.0 (bona), error 1.0, 5 rajoles actualitzades.
[REFORC] Sector_3: mantenir-posicio del cicle 1 -> recompensa 1.0 (bona), error 1.0, 4 rajoles actualitzades.
[REFORC] Sector_1: mantenir-posicio del cicle 1 -> recompensa 1.0 (bona), error 0.85, 4 rajoles actualitzades.
[SELECCIO] Sector_2: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_2: ORDRE sollicitar-dades -> 30.0 graus.
[EXPLICACIO] Sector_2, cicle 2
[EPMEM] NOU EPISODI #4: Sector_2, cicle 2, sollicitar-dades.
[MONITORATGE] Sector_2: cal demanar al simulador les lectures que falten (risc de dades critic).
```

</details>

## CP07 – Sensor de vent caigut després d'una ratxa crítica (historial)

**Cobertura:** dades absents + historial. **Objectiu i resultat esperat:** Al cicle 1 hi ha una ratxa de 18 m/s. Al cicle 2 el sensor deixa de respondre: com que l'última lectura era perillosa, el sistema s'ha de quedar en seguretat (no fiar-se'n).

| Cicle | Sector | Entrada (vent / previsió / T cultiu / aigua / radiació) | Esperat | Obtingut | |
|---|---|---|---|---|---|
| 1 | Sector_1 (tomàquet) | 18.0 / 3.0 / 22.0 / 90.0 / 300.0 | accio = posicio-seguretat | posicio-seguretat (0.0°); riscos: mecanic=critic | ✅ |
| 2 | Sector_1 (tomàquet) | absent / 3.0 / 22.0 / 90.0 / 300.0 | accio = posicio-seguretat; risc dades = critic | posicio-seguretat (0.0°); riscos: dades=critic; impasse dades-insuficients | ✅ |

**Explicació que dona el sistema** (fet `explicacio`):

- Cicle 1, Sector_1: posicio-seguretat a 0.0 graus. Riscos: mecanic=critic. Candidats: posicio-seguretat(0). Descartats: mantenir-posicio orientar-produccio. Criteri: unica opcio que compleix les restriccions dures.
- Cicle 2, Sector_1: posicio-seguretat a 0.0 graus. Riscos: dades=critic. Candidats: mantenir-posicio(1) orientar-produccio(3) sollicitar-dades(0) posicio-seguretat(1000). Descartats: cap. Criteri: preferencia requerida (IMPAS-dades).

<details><summary>Traça rellevant del CLIPS</summary>

```
--- cicle 1 ---
[ELABORACIO] Sector_1: vent 18.0 m/s (previsio 3.0) >= 16.0 m/s. Risc mecanic critic.
[ELABORACIO] El risc mecanic de Sector_1 activa l'objectiu Obj_Seguretat.
[PROPOSTA] Sector_1: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_1: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_1: posicio-seguretat (0.0 graus).
[AVALUACIO] Sector_1: REBUIG de orientar-produccio (vent critic, restriccio de seguretat).
[AVALUACIO] Sector_1: REBUIG de mantenir-posicio (vent critic, restriccio de seguretat).
[AVALUACIO] Sector_1: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_1: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_1: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_1: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_1: orientar-produccio queda descartat (AV1-vent-critic).
[SELECCIO] Sector_1: mantenir-posicio queda descartat (AV1-vent-critic).
[SELECCIO] Sector_1: es selecciona posicio-seguretat. Criteri: unica opcio que compleix les restriccions dures.
[SELECCIO] Sector_1: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_1: ORDRE posicio-seguretat -> 0.0 graus.
[EXPLICACIO] Sector_1, cicle 1
[EPMEM] NOU EPISODI #1: Sector_1, cicle 1, posicio-seguretat.
--- cicle 2 ---
[PERCEPCIO] Sector_1: falten lectures (vent=absent, temp-cultiu=22.0, humitat=90.0, radiacio=300.0). Risc de dades critic.
[EPMEM] Sector_1: l'episodi #1 (posicio-seguretat) es valora 'bona' (resultat correcte, risc 0 -> 0).
[PROPOSTA] Sector_1: mantenir-posicio (0.0 graus).
[PROPOSTA] Sector_1: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_1: sollicitar-dades (no es mou el panell).
[AVALUACIO] Sector_1: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_1: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_1: no-regar +1 (estalvi d'aigua).
[REFORC] Sector_3: mantenir-posicio del cicle 1 -> recompensa 1.0 (bona), error 1.0, 4 rajoles actualitzades.
[REFORC] Sector_2: mantenir-posicio del cicle 1 -> recompensa 1.0 (bona), error 0.85, 4 rajoles actualitzades.
[REFORC] Sector_1: posicio-seguretat del cicle 1 -> recompensa 1.0 (bona), error 1.0, 5 rajoles actualitzades.
[SELECCIO] Sector_1: IMPAS DE DADES INSUFICIENTS. Sense lectura fiable de vent no es pot saber si moure el panell es segur.
[SELECCIO] Sector_1: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> IMPAS]
[IMPAS] Sector_1: subobjectiu resoldre-dades. Falta la lectura de vent, pero el cicle anterior ja hi havia risc mecanic. Opcio segura: posicio de seguretat.
[IMPAS] Sector_1: la deliberacio proposa posicio-seguretat (0.0 graus).
[CHUNKING] Nova regla chunk-1: sense lectura de vent i vent fort el cicle anterior, posicio-seguretat requerida.
[IMPAS -> SELECCIO]
[SELECCIO] Sector_1: es selecciona posicio-seguretat. Criteri: preferencia requerida (IMPAS-dades).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_1: ORDRE posicio-seguretat -> 0.0 graus.
[EXPLICACIO] Sector_1, cicle 2
   Criteri:    preferencia requerida (IMPAS-dades)
[EPMEM] NOU EPISODI #6: Sector_1, cicle 2, posicio-seguretat.
[MONITORATGE] Sector_1: cal demanar al simulador les lectures que falten (risc de dades critic).
```

</details>

## CP08 – Fallada d'actuador

**Cobertura:** fallades. **Objectiu i resultat esperat:** Al cicle 1 la vinya ha d'anar de 20° a 30°, però l'actuador no es mou. Al cicle 2 el sistema ho ha de detectar (risc de fallada), no ha de tornar a enviar ordres de seguiment i ha d'avisar manteniment.

| Cicle | Sector | Entrada (vent / previsió / T cultiu / aigua / radiació) | Esperat | Obtingut | |
|---|---|---|---|---|---|
| 1 | Sector_3 (vinya) | 3.0 / 3.0 / 24.0 / 90.0 / 400.0 | accio = orientar-produccio | orientar-produccio (30.0°) | ✅ |
| 2 | Sector_3 (vinya) | 3.0 / 3.0 / 24.0 / 90.0 / 400.0 | risc fallada-actuador = alt; rebutjat = orientar-produccio; acció ≠ orientar-produccio | mantenir-posicio (20.0°); riscos: fallada-actuador=alt | ✅ |

**Explicació que dona el sistema** (fet `explicacio`):

- Cicle 1, Sector_3: orientar-produccio a 30.0 graus. Riscos: cap. Candidats: mantenir-posicio(1) orientar-produccio(3). Descartats: cap. Criteri: maxima valoracio (3 punts).
- Cicle 2, Sector_3: mantenir-posicio a 20.0 graus. Riscos: fallada-actuador=alt. Candidats: mantenir-posicio(1). Descartats: orientar-produccio. Criteri: unica opcio que compleix les restriccions dures.

<details><summary>Traça rellevant del CLIPS</summary>

```
--- cicle 1 ---
[PROPOSTA] Sector_3: mantenir-posicio (20.0 graus).
[PROPOSTA] Sector_3: orientar-produccio (30.0 graus).
[AVALUACIO] Sector_3: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_3: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_3: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_3: es selecciona orientar-produccio. Criteri: maxima valoracio (3 punts).
[SELECCIO] Sector_3: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_3: ORDRE orientar-produccio -> 30.0 graus.
[EXPLICACIO] Sector_3, cicle 1
[EPMEM] NOU EPISODI #3: Sector_3, cicle 1, orientar-produccio.
--- cicle 2 ---
[PERCEPCIO] Sector_3: Panell_3_2 es a 20.0 graus pero se li va ordenar 30.0 (orientar-produccio). Fallada d'actuacio.
[ELABORACIO] El risc fallada-actuador de Sector_3 activa l'objectiu Obj_Seguretat.
[EPMEM] Sector_3: l'episodi #3 (orientar-produccio) es valora 'dolenta' (resultat fallada, risc 0 -> 0).
[PROPOSTA] Sector_3: mantenir-posicio (20.0 graus).
[PROPOSTA] Sector_3: orientar-produccio (30.0 graus).
[AVALUACIO] Sector_3: REBUIG de orientar-produccio (l'actuador no respon).
[AVALUACIO] Sector_3: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_3: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_3: orientar-produccio +2 (es el que es va fer el cicle anterior).
[AVALUACIO] Sector_3: orientar-produccio -1.5 (memoria: a l'episodi #3, cicle 1, va funcionar malament, similitud 0.75).
[AVALUACIO] Sector_3: no-regar +1 (estalvi d'aigua).
[REFORC] Sector_3: orientar-produccio del cicle 1 -> recompensa -1.0 (dolenta), error -1.0, 4 rajoles actualitzades.
[REFORC] Sector_2: orientar-produccio del cicle 1 -> recompensa 1.0 (bona), error 1.15, 4 rajoles actualitzades.
[REFORC] Sector_1: orientar-produccio del cicle 1 -> recompensa 1.0 (bona), error 0.98, 4 rajoles actualitzades.
[SELECCIO] Sector_3: orientar-produccio queda descartat (AV9-fallada).
[SELECCIO] Sector_3: es selecciona mantenir-posicio. Criteri: unica opcio que compleix les restriccions dures.
[SELECCIO] Sector_3: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_3: ORDRE mantenir-posicio -> 20.0 graus.
[EXPLICACIO] Sector_3, cicle 2
[EPMEM] NOU EPISODI #6: Sector_3, cicle 2, mantenir-posicio.
[MONITORATGE] Sector_3: l'actuador no ha respost. Cal revisio de manteniment.
```

</details>

## CP09 – Vent que puja i baixa al llarg de 5 hores

**Cobertura:** canvis temporals. **Objectiu i resultat esperat:** El vent fa 6 → 13 → 18 → 18 → 8 m/s, amb la previsió de l'hora següent. El sistema ha d'anar a seguretat quan la ratxa observada o prevista arriba a 16 m/s, quedar-s'hi mentre duri i tornar a produir quan passa.

| Cicle | Sector | Entrada (vent / previsió / T cultiu / aigua / radiació) | Esperat | Obtingut | |
|---|---|---|---|---|---|
| 1 | Sector_1 (tomàquet) | 6.0 / 13.0 / 22.0 / 90.0 / 300.0 | risc mecanic = alt | posicio-seguretat (0.0°); riscos: mecanic=alt | ✅ |
| 2 | Sector_1 (tomàquet) | 13.0 / 18.0 / 22.0 / 90.0 / 300.0 | accio = posicio-seguretat | posicio-seguretat (0.0°); riscos: mecanic=critic | ✅ |
| 3 | Sector_1 (tomàquet) | 18.0 / 18.0 / 22.0 / 90.0 / 300.0 | accio = posicio-seguretat | posicio-seguretat (0.0°); riscos: mecanic=critic | ✅ |
| 4 | Sector_1 (tomàquet) | 18.0 / 8.0 / 22.0 / 90.0 / 300.0 | accio = posicio-seguretat | posicio-seguretat (0.0°); riscos: mecanic=critic | ✅ |
| 5 | Sector_1 (tomàquet) | 8.0 / 6.0 / 22.0 / 90.0 / 300.0 | accio = orientar-produccio; risc mecanic = cap | orientar-produccio (30.0°) | ✅ |

**Explicació que dona el sistema** (fet `explicacio`):

- Cicle 1, Sector_1: posicio-seguretat a 0.0 graus. Riscos: mecanic=alt. Candidats: mantenir-posicio(4) orientar-produccio(3) posicio-seguretat(10). Descartats: cap. Criteri: maxima valoracio (10 punts).
- Cicle 2, Sector_1: posicio-seguretat a 0.0 graus. Riscos: mecanic=critic. Candidats: posicio-seguretat(3.5). Descartats: mantenir-posicio orientar-produccio. Criteri: unica opcio que compleix les restriccions dures.
- Cicle 3, Sector_1: posicio-seguretat a 0.0 graus. Riscos: mecanic=critic. Candidats: posicio-seguretat(4.0). Descartats: mantenir-posicio orientar-produccio. Criteri: unica opcio que compleix les restriccions dures.
- Cicle 4, Sector_1: posicio-seguretat a 0.0 graus. Riscos: mecanic=critic. Candidats: posicio-seguretat(4.0). Descartats: mantenir-posicio orientar-produccio. Criteri: unica opcio que compleix les restriccions dures.
- Cicle 5, Sector_1: orientar-produccio a 30.0 graus. Riscos: cap. Candidats: mantenir-posicio(1) orientar-produccio(3). Descartats: cap. Criteri: maxima valoracio (3 punts).

<details><summary>Traça rellevant del CLIPS</summary>

```
--- cicle 1 ---
[ELABORACIO] Sector_1: vent 6.0 m/s (previsio 13.0) >= 12.0 m/s. Risc mecanic alt.
[ELABORACIO] El risc mecanic de Sector_1 activa l'objectiu Obj_Seguretat.
[PROPOSTA] Sector_1: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_1: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_1: posicio-seguretat (0.0 graus).
[AVALUACIO] Sector_1: posicio-seguretat +10 (seguretat, vent alt).
[AVALUACIO] Sector_1: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_1: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_1: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_1: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_1: es selecciona posicio-seguretat. Criteri: maxima valoracio (10 punts).
[SELECCIO] Sector_1: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_1: ORDRE posicio-seguretat -> 0.0 graus.
[EXPLICACIO] Sector_1, cicle 1
[EPMEM] NOU EPISODI #1: Sector_1, cicle 1, posicio-seguretat.
--- cicle 2 ---
[ELABORACIO] Sector_1: vent 13.0 m/s (previsio 18.0) >= 16.0 m/s. Risc mecanic critic.
[ELABORACIO] El risc mecanic de Sector_1 activa l'objectiu Obj_Seguretat.
[EPMEM] Sector_1: l'episodi #1 (posicio-seguretat) es valora 'bona' (resultat correcte, risc 0 -> 0).
[PROPOSTA] Sector_1: mantenir-posicio (0.0 graus).
[PROPOSTA] Sector_1: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_1: posicio-seguretat (0.0 graus).
[AVALUACIO] Sector_1: REBUIG de orientar-produccio (vent critic, restriccio de seguretat).
[AVALUACIO] Sector_1: REBUIG de mantenir-posicio (vent critic, restriccio de seguretat).
[AVALUACIO] Sector_1: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_1: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_1: posicio-seguretat +2 (es el que es va fer el cicle anterior).
[AVALUACIO] Sector_1: posicio-seguretat 1.5 (memoria: a l'episodi #1, cicle 1, va funcionar be, similitud 0.75).
[AVALUACIO] Sector_1: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_1: orientar-produccio queda descartat (AV1-vent-critic).
[SELECCIO] Sector_1: mantenir-posicio queda descartat (AV1-vent-critic).
[SELECCIO] Sector_1: es selecciona posicio-seguretat. Criteri: unica opcio que compleix les restriccions dures.
[REFORC] Sector_3: mantenir-posicio del cicle 1 -> recompensa 1.0 (bona), error 1.0, 4 rajoles actualitzades.
[REFORC] Sector_2: mantenir-posicio del cicle 1 -> recompensa 1.0 (bona), error 0.85, 4 rajoles actualitzades.
[REFORC] Sector_1: posicio-seguretat del cicle 1 -> recompensa 1.0 (bona), error 1.0, 5 rajoles actualitzades.
[SELECCIO] Sector_1: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_1: ORDRE posicio-seguretat -> 0.0 graus.
[EXPLICACIO] Sector_1, cicle 2
[EPMEM] NOU EPISODI #4: Sector_1, cicle 2, posicio-seguretat.
--- cicle 3 ---
[ELABORACIO] Sector_1: vent 18.0 m/s (previsio 18.0) >= 16.0 m/s. Risc mecanic critic.
[ELABORACIO] El risc mecanic de Sector_1 activa l'objectiu Obj_Seguretat.
[EPMEM] Sector_1: l'episodi #4 (posicio-seguretat) es valora 'bona' (resultat correcte, risc 0 -> 0).
[PROPOSTA] Sector_1: mantenir-posicio (0.0 graus).
[PROPOSTA] Sector_1: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_1: posicio-seguretat (0.0 graus).
[AVALUACIO] Sector_1: REBUIG de orientar-produccio (vent critic, restriccio de seguretat).
[AVALUACIO] Sector_1: REBUIG de mantenir-posicio (vent critic, restriccio de seguretat).
[AVALUACIO] Sector_1: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_1: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_1: posicio-seguretat +2 (es el que es va fer el cicle anterior).
[AVALUACIO] Sector_1: posicio-seguretat 2.0 (memoria: a l'episodi #4, cicle 2, va funcionar be, similitud 1.0).
[AVALUACIO] Sector_1: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_1: orientar-produccio queda descartat (AV1-vent-critic).
[SELECCIO] Sector_1: mantenir-posicio queda descartat (AV1-vent-critic).
[SELECCIO] Sector_1: es selecciona posicio-seguretat. Criteri: unica opcio que compleix les restriccions dures.
[REFORC] Sector_3: mantenir-posicio del cicle 2 -> recompensa 1.0 (bona), error 0.57, 4 rajoles actualitzades.
[REFORC] Sector_2: mantenir-posicio del cicle 2 -> recompensa 1.0 (bona), error 0.51, 4 rajoles actualitzades.
[REFORC] Sector_1: posicio-seguretat del cicle 2 -> recompensa 1.0 (bona), error 0.76, 5 rajoles actualitzades.
[SELECCIO] Sector_1: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_1: ORDRE posicio-seguretat -> 0.0 graus.
[EXPLICACIO] Sector_1, cicle 3
[EPMEM] NOU EPISODI #7: Sector_1, cicle 3, posicio-seguretat.
--- cicle 4 ---
[ELABORACIO] Sector_1: vent 18.0 m/s (previsio 8.0) >= 16.0 m/s. Risc mecanic critic.
[ELABORACIO] El risc mecanic de Sector_1 activa l'objectiu Obj_Seguretat.
[EPMEM] Sector_1: l'episodi #7 (posicio-seguretat) es valora 'bona' (resultat correcte, risc 0 -> 0).
[PROPOSTA] Sector_1: mantenir-posicio (0.0 graus).
[PROPOSTA] Sector_1: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_1: posicio-seguretat (0.0 graus).
[AVALUACIO] Sector_1: REBUIG de orientar-produccio (vent critic, restriccio de seguretat).
[AVALUACIO] Sector_1: REBUIG de mantenir-posicio (vent critic, restriccio de seguretat).
[AVALUACIO] Sector_1: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_1: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_1: posicio-seguretat +2 (es el que es va fer el cicle anterior).
[AVALUACIO] Sector_1: posicio-seguretat 2.0 (memoria: a l'episodi #7, cicle 3, va funcionar be, similitud 1.0).
[AVALUACIO] Sector_1: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_1: orientar-produccio queda descartat (AV1-vent-critic).
[SELECCIO] Sector_1: mantenir-posicio queda descartat (AV1-vent-critic).
[SELECCIO] Sector_1: es selecciona posicio-seguretat. Criteri: unica opcio que compleix les restriccions dures.
[REFORC] Sector_3: mantenir-posicio del cicle 3 -> recompensa 1.0 (bona), error 0.32, 4 rajoles actualitzades.
[REFORC] Sector_2: mantenir-posicio del cicle 3 -> recompensa 1.0 (bona), error 0.31, 4 rajoles actualitzades.
[REFORC] Sector_1: posicio-seguretat del cicle 3 -> recompensa 1.0 (bona), error 0.53, 5 rajoles actualitzades.
[SELECCIO] Sector_1: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_1: ORDRE posicio-seguretat -> 0.0 graus.
[EXPLICACIO] Sector_1, cicle 4
[EPMEM] NOU EPISODI #10: Sector_1, cicle 4, posicio-seguretat.
--- cicle 5 ---
[EPMEM] Sector_1: l'episodi #10 (posicio-seguretat) es valora 'bona' (resultat correcte, risc 0 -> 0).
[PROPOSTA] Sector_1: mantenir-posicio (0.0 graus).
[PROPOSTA] Sector_1: orientar-produccio (30.0 graus).
[AVALUACIO] Sector_1: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_1: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_1: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_1: es selecciona orientar-produccio. Criteri: maxima valoracio (3 punts).
[REFORC] Sector_3: mantenir-posicio del cicle 4 -> recompensa 1.0 (bona), error 0.18, 4 rajoles actualitzades.
[REFORC] Sector_2: mantenir-posicio del cicle 4 -> recompensa 1.0 (bona), error 0.19, 4 rajoles actualitzades.
[REFORC] Sector_1: posicio-seguretat del cicle 4 -> recompensa 1.0 (bona), error 0.37, 5 rajoles actualitzades.
[SELECCIO] Sector_1: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_1: ORDRE orientar-produccio -> 30.0 graus.
[EXPLICACIO] Sector_1, cicle 5
[EPMEM] NOU EPISODI #13: Sector_1, cicle 5, orientar-produccio.
```

</details>

## CP10 – Estrès hídric de l'enciam

**Cobertura:** protecció del cultiu. **Objectiu i resultat esperat:** Només queda un 20 % d'aigua disponible a l'enciam (p = 0,30): l'estrès és crític i fer ombra ha de ser candidat (redueix l'evapotranspiració).

| Cicle | Sector | Entrada (vent / previsió / T cultiu / aigua / radiació) | Esperat | Obtingut | |
|---|---|---|---|---|---|
| 1 | Sector_2 (enciam) | 3.0 / 3.0 / 16.0 / 20.0 / 150.0 | risc estres-hidric = critic; candidat = orientar-ombra | orientar-ombra (0.0°); riscos: estres-hidric=critic | ✅ |

**Explicació que dona el sistema** (fet `explicacio`):

- Cicle 1, Sector_2: orientar-ombra a 0.0 graus. Riscos: estres-hidric=critic. Candidats: mantenir-posicio(4) orientar-produccio(3) orientar-ombra(9). Descartats: cap. Criteri: maxima valoracio (9 punts).

<details><summary>Traça rellevant del CLIPS</summary>

```
--- cicle 1 ---
[ELABORACIO] Sector_2: queda un 20.0% d'aigua disponible (enciam tolera esgotar fins al 30.0%). Estres hidric critic.
[ELABORACIO] El risc estres-hidric de Sector_2 activa l'objectiu Obj_Produccio_Cultiu.
[ELABORACIO] Sector_2: s'ha gastat el 80.0% de l'aigua disponible (enciam tolera 30.0%). Necessitat de reg critic.
[PROPOSTA] Sector_2: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_2: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_2: orientar-ombra (0.0 graus), hi ha risc per al cultiu.
[PROPOSTA] Sector_2: regar-complet (+80.0% de l'aigua disponible) i regar-parcial (+65.0%), hi ha estres hidric.
[AVALUACIO] Sector_2: orientar-ombra +9 (cultiu, risc estres-hidric critic).
[AVALUACIO] Sector_2: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_2: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_2: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_2: regar-parcial +12 (cultiu, necessitat de reg critic).
[AVALUACIO] Sector_2: regar-complet +12 (cultiu, necessitat de reg critic).
[AVALUACIO] Sector_2: regar-complet +2 (enciam, sensibilitat alt).
[AVALUACIO] Sector_2: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_2: es selecciona orientar-ombra. Criteri: maxima valoracio (9 punts).
[SELECCIO] Sector_2: reg regar-complet. Criteri: maxima valoracio (14 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_2: ORDRE orientar-ombra -> 0.0 graus.
[APLICACIO] Sector_2: ORDRE DE REG regar-complet -> +80.0% de l'aigua disponible.
[EXPLICACIO] Sector_2, cicle 1
[EXPLICACIO REG] Sector_2, cicle 1
[EPMEM] NOU EPISODI #1: Sector_2, cicle 1, orientar-ombra.
```

</details>

## CP11 – Radiació i calor alhora al tomàquet

**Cobertura:** protecció del cultiu + elaboració. **Objectiu i resultat esperat:** 500 W/m² (radiació alta) i 33 °C (calor alta) alhora: la combinació ha d'agreujar el risc de radiació a crític, i el sistema ha de fer ombra.

| Cicle | Sector | Entrada (vent / previsió / T cultiu / aigua / radiació) | Esperat | Obtingut | |
|---|---|---|---|---|---|
| 1 | Sector_1 (tomàquet) | 3.0 / 3.0 / 33.0 / 90.0 / 500.0 | risc exces-radiacio = critic; risc temperatura = alt; accio = orientar-ombra | orientar-ombra (0.0°); riscos: exces-radiacio=critic, temperatura=alt | ✅ |

**Explicació que dona el sistema** (fet `explicacio`):

- Cicle 1, Sector_1: orientar-ombra a 0.0 graus. Riscos: temperatura=alt exces-radiacio=critic. Candidats: mantenir-posicio(4) orientar-produccio(3) orientar-ombra(15). Descartats: cap. Criteri: maxima valoracio (15 punts).

<details><summary>Traça rellevant del CLIPS</summary>

```
--- cicle 1 ---
[ELABORACIO] Sector_1: tomaquet a 33.0 C (optim fins a 27.0, maxim 35.0). Risc de temperatura alt.
[ELABORACIO] El risc temperatura de Sector_1 activa l'objectiu Obj_Produccio_Cultiu.
[ELABORACIO] Sector_1: radiacio 500.0 W/m2 (tomaquet: optim fins a 350.0, estres des de 435.0). Risc de radiacio alt.
[ELABORACIO] Sector_1: radiacio alta amb calor alta. El risc de radiacio passa a critic.
[PROPOSTA] Sector_1: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_1: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_1: orientar-ombra (0.0 graus), hi ha risc per al cultiu.
[AVALUACIO] Sector_1: orientar-ombra +9 (cultiu, risc exces-radiacio critic).
[AVALUACIO] Sector_1: orientar-ombra +6 (cultiu, risc temperatura alt).
[AVALUACIO] Sector_1: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_1: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_1: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_1: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_1: es selecciona orientar-ombra. Criteri: maxima valoracio (15 punts).
[SELECCIO] Sector_1: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_1: ORDRE orientar-ombra -> 0.0 graus.
[EXPLICACIO] Sector_1, cicle 1
[EPMEM] NOU EPISODI #1: Sector_1, cicle 1, orientar-ombra.
```

</details>

## CP12 – Reg a primera hora

**Cobertura:** protecció del cultiu (reg). **Objectiu i resultat esperat:** A les 7 h, l'enciam té un 65 % d'aigua (ha gastat el 35 %, més que el seu p = 30 %): hi ha estrès i s'ha de regar fins a capacitat de camp (+35 %). El tomàquet és al 66 % (ha gastat el 34 %, a prop del seu p = 40 %): és hora fresca i és un cultiu sensible, així que s'ha d'anticipar (+34 %). La vinya és al 62 %: no s'anticipa (reg deficitari). El panell decideix a part. A les 8 h, amb el sòl ple, ja no s'ha de regar.

| Cicle | Sector | Entrada (vent / previsió / T cultiu / aigua / radiació) | Esperat | Obtingut | |
|---|---|---|---|---|---|
| 1 | Sector_1 (tomàquet) | 3.0 / 3.0 / 22.0 / 66.0 / 300.0 (7 h) | reg = regar-complet; dosi = 34.0 | mantenir-posicio (30.0°); reg regar-complet (+34.0 %) | ✅ |
| 1 | Sector_2 (enciam) | 3.0 / 3.0 / 16.0 / 65.0 / 150.0 (7 h) | reg = regar-complet; dosi = 35.0 | mantenir-posicio (30.0°); riscos: estres-hidric=mitja; reg regar-complet (+35.0 %) | ✅ |
| 1 | Sector_3 (vinya) | 3.0 / 3.0 / 24.0 / 62.0 / 400.0 (7 h) | reg = no-regar | mantenir-posicio (30.0°); reg no-regar | ✅ |
| 2 | Sector_1 (tomàquet) | 3.0 / 3.0 / 22.0 / 100.0 / 300.0 (8 h) | reg = no-regar | mantenir-posicio (30.0°); reg no-regar | ✅ |
| 2 | Sector_2 (enciam) | 3.0 / 3.0 / 16.0 / 100.0 / 150.0 (8 h) | reg = no-regar | mantenir-posicio (30.0°); reg no-regar | ✅ |
| 2 | Sector_3 (vinya) | 3.0 / 3.0 / 24.0 / 62.0 / 400.0 (8 h) | reg = no-regar | mantenir-posicio (30.0°); reg no-regar | ✅ |

**Explicació que dona el sistema** (fet `explicacio`):

- Cicle 1, Sector_1: mantenir-posicio a 30.0 graus. Riscos: cap. Candidats: mantenir-posicio(4) orientar-produccio(3). Descartats: cap. Criteri: maxima valoracio (4 punts).
  - Reg: regar-complet (+34.0%). Necessitat: anticipada (esgotat 34.0%). Candidats: no-regar(1) regar-complet(5) regar-parcial(4). Descartats: cap. Criteri: maxima valoracio (5 punts).
- Cicle 1, Sector_2: mantenir-posicio a 30.0 graus. Riscos: estres-hidric=mitja. Candidats: mantenir-posicio(4) orientar-produccio(3) orientar-ombra(3). Descartats: cap. Criteri: maxima valoracio (4 punts).
  - Reg: regar-complet (+35.0%). Necessitat: mitja (esgotat 35.0%). Candidats: no-regar(1) regar-complet(9) regar-parcial(7). Descartats: cap. Criteri: maxima valoracio (9 punts).
- Cicle 1, Sector_3: mantenir-posicio a 30.0 graus. Riscos: cap. Candidats: mantenir-posicio(4) orientar-produccio(3). Descartats: cap. Criteri: maxima valoracio (4 punts).
  - Reg: no-regar (+0%). Necessitat: anticipada (esgotat 38.0%). Candidats: no-regar(1). Descartats: cap. Criteri: maxima valoracio (1 punts).
- Cicle 2, Sector_1: mantenir-posicio a 30.0 graus. Riscos: cap. Candidats: mantenir-posicio(8.0) orientar-produccio(3). Descartats: cap. Criteri: maxima valoracio (8.0 punts).
  - Reg: no-regar (+0%). Necessitat: cap. Candidats: no-regar(1). Descartats: cap. Criteri: maxima valoracio (1 punts).
- Cicle 2, Sector_2: mantenir-posicio a 30.0 graus. Riscos: cap. Candidats: mantenir-posicio(8.0) orientar-produccio(3). Descartats: cap. Criteri: maxima valoracio (8.0 punts).
  - Reg: no-regar (+0%). Necessitat: cap. Candidats: no-regar(1). Descartats: cap. Criteri: maxima valoracio (1 punts).
- Cicle 2, Sector_3: mantenir-posicio a 30.0 graus. Riscos: cap. Candidats: mantenir-posicio(8.0) orientar-produccio(3). Descartats: cap. Criteri: maxima valoracio (8.0 punts).
  - Reg: no-regar (+0%). Necessitat: anticipada (esgotat 38.0%). Candidats: no-regar(1). Descartats: cap. Criteri: maxima valoracio (1 punts).

<details><summary>Traça rellevant del CLIPS</summary>

```
--- cicle 1 ---
[ELABORACIO] Sector_3: s'ha gastat el 38.0% de l'aigua disponible (vinya tolera 45.0%). Necessitat de reg anticipada.
[ELABORACIO] Sector_2: queda un 65.0% d'aigua disponible (enciam tolera esgotar fins al 30.0%). Estres hidric mitja.
[ELABORACIO] Sector_2: s'ha gastat el 35.0% de l'aigua disponible (enciam tolera 30.0%). Necessitat de reg mitja.
[ELABORACIO] Sector_1: s'ha gastat el 34.0% de l'aigua disponible (tomaquet tolera 40.0%). Necessitat de reg anticipada.
[PROPOSTA] Sector_3: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_3: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_2: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_2: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_1: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_1: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_2: orientar-ombra (0.0 graus), hi ha risc per al cultiu.
[PROPOSTA] Sector_2: regar-complet (+35.0% de l'aigua disponible) i regar-parcial (+20.0%), hi ha estres hidric.
[PROPOSTA] Sector_1: regar-complet (+34.0% de l'aigua disponible) i regar-parcial (+14.0%), a prop del llindar i hora fresca.
[AVALUACIO] Sector_2: orientar-ombra +3 (cultiu, risc estres-hidric mitja).
[AVALUACIO] Sector_1: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_2: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_3: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_1: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_2: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_3: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_1: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_2: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_3: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_1: regar-parcial +3 (cultiu, necessitat de reg anticipada).
[AVALUACIO] Sector_1: regar-complet +3 (cultiu, necessitat de reg anticipada).
[AVALUACIO] Sector_2: regar-parcial +6 (cultiu, necessitat de reg mitja).
[AVALUACIO] Sector_2: regar-complet +6 (cultiu, necessitat de reg mitja).
[AVALUACIO] Sector_2: regar-complet +2 (enciam, sensibilitat alt).
[AVALUACIO] Sector_1: regar-complet +1 (tomaquet, sensibilitat mitja).
[AVALUACIO] Sector_1: regar-parcial +1 (hora fresca).
[AVALUACIO] Sector_1: regar-complet +1 (hora fresca).
[AVALUACIO] Sector_2: regar-parcial +1 (hora fresca).
[AVALUACIO] Sector_2: regar-complet +1 (hora fresca).
[AVALUACIO] Sector_1: no-regar +1 (estalvi d'aigua).
[AVALUACIO] Sector_2: no-regar +1 (estalvi d'aigua).
[AVALUACIO] Sector_3: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_1: es selecciona mantenir-posicio. Criteri: maxima valoracio (4 punts).
[SELECCIO] Sector_2: es selecciona mantenir-posicio. Criteri: maxima valoracio (4 punts).
[SELECCIO] Sector_3: es selecciona mantenir-posicio. Criteri: maxima valoracio (4 punts).
[SELECCIO] Sector_1: reg regar-complet. Criteri: maxima valoracio (5 punts).
[SELECCIO] Sector_2: reg regar-complet. Criteri: maxima valoracio (9 punts).
[SELECCIO] Sector_3: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_3: ORDRE mantenir-posicio -> 30.0 graus.
[APLICACIO] Sector_2: ORDRE mantenir-posicio -> 30.0 graus.
[APLICACIO] Sector_1: ORDRE mantenir-posicio -> 30.0 graus.
[APLICACIO] Sector_2: ORDRE DE REG regar-complet -> +35.0% de l'aigua disponible.
[APLICACIO] Sector_1: ORDRE DE REG regar-complet -> +34.0% de l'aigua disponible.
[EXPLICACIO] Sector_1, cicle 1
[EXPLICACIO] Sector_2, cicle 1
[EXPLICACIO] Sector_3, cicle 1
[EXPLICACIO REG] Sector_1, cicle 1
[EXPLICACIO REG] Sector_2, cicle 1
[EPMEM] NOU EPISODI #1: Sector_1, cicle 1, mantenir-posicio.
[EPMEM] NOU EPISODI #2: Sector_2, cicle 1, mantenir-posicio.
[EPMEM] NOU EPISODI #3: Sector_3, cicle 1, mantenir-posicio.
--- cicle 2 ---
[ELABORACIO] Sector_3: s'ha gastat el 38.0% de l'aigua disponible (vinya tolera 45.0%). Necessitat de reg anticipada.
[EPMEM] Sector_3: l'episodi #3 (mantenir-posicio) es valora 'bona' (resultat correcte, risc 0 -> 0).
[EPMEM] Sector_2: l'episodi #2 (mantenir-posicio) es valora 'bona' (resultat correcte, risc 1 -> 0).
[EPMEM] Sector_1: l'episodi #1 (mantenir-posicio) es valora 'bona' (resultat correcte, risc 0 -> 0).
[PROPOSTA] Sector_3: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_3: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_2: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_2: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_1: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_1: orientar-produccio (30.0 graus).
[AVALUACIO] Sector_1: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_2: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_3: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_1: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_2: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_3: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_1: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_2: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_3: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_3: mantenir-posicio +2 (es el que es va fer el cicle anterior).
[AVALUACIO] Sector_2: mantenir-posicio +2 (es el que es va fer el cicle anterior).
[AVALUACIO] Sector_1: mantenir-posicio +2 (es el que es va fer el cicle anterior).
[AVALUACIO] Sector_1: mantenir-posicio 2.0 (memoria: a l'episodi #1, cicle 1, va funcionar be, similitud 1.0).
[AVALUACIO] Sector_2: mantenir-posicio 2.0 (memoria: a l'episodi #2, cicle 1, va funcionar be, similitud 1.0).
[AVALUACIO] Sector_3: mantenir-posicio 2.0 (memoria: a l'episodi #3, cicle 1, va funcionar be, similitud 1.0).
[AVALUACIO] Sector_1: no-regar +1 (estalvi d'aigua).
[AVALUACIO] Sector_2: no-regar +1 (estalvi d'aigua).
[AVALUACIO] Sector_3: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_1: es selecciona mantenir-posicio. Criteri: maxima valoracio (8.0 punts).
[REFORC] Sector_3: mantenir-posicio del cicle 1 -> recompensa 1.0 (bona), error 1.0, 4 rajoles actualitzades.
[REFORC] Sector_2: mantenir-posicio del cicle 1 -> recompensa 1.0 (bona), error 0.85, 5 rajoles actualitzades.
[REFORC] Sector_1: mantenir-posicio del cicle 1 -> recompensa 1.0 (bona), error 0.75, 4 rajoles actualitzades.
[SELECCIO] Sector_2: es selecciona mantenir-posicio. Criteri: maxima valoracio (8.0 punts).
[SELECCIO] Sector_3: es selecciona mantenir-posicio. Criteri: maxima valoracio (8.0 punts).
[SELECCIO] Sector_1: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO] Sector_2: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO] Sector_3: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_3: ORDRE mantenir-posicio -> 30.0 graus.
[APLICACIO] Sector_2: ORDRE mantenir-posicio -> 30.0 graus.
[APLICACIO] Sector_1: ORDRE mantenir-posicio -> 30.0 graus.
[EXPLICACIO] Sector_1, cicle 2
[EXPLICACIO] Sector_2, cicle 2
[EXPLICACIO] Sector_3, cicle 2
[EPMEM] NOU EPISODI #4: Sector_1, cicle 2, mantenir-posicio.
[EPMEM] NOU EPISODI #5: Sector_2, cicle 2, mantenir-posicio.
[EPMEM] NOU EPISODI #6: Sector_3, cicle 2, mantenir-posicio.
```

</details>

## CP13 – No es rega perquè plourà

**Cobertura:** conflicte cultiu contra estalvi d'aigua (reg). **Objectiu i resultat esperat:** A les 19 h, el tomàquet té estrès (55 %), però es preveuen 15 mm de pluja en les pròximes 12 h (≥ 10 mm, Diputació de Barcelona): regar queda rebutjat i no es rega. L'enciam, en canvi, és al 20 % (estrès crític): no pot esperar i es rega igualment, però només en part (+65 %, en lloc d'omplir el sòl), perquè la pluja l'acabarà d'omplir.

| Cicle | Sector | Entrada (vent / previsió / T cultiu / aigua / radiació) | Esperat | Obtingut | |
|---|---|---|---|---|---|
| 1 | Sector_1 (tomàquet) | 3.0 / 3.0 / 22.0 / 55.0 / 300.0 (19 h) | reg = no-regar; reg_rebutjat = regar-complet | mantenir-posicio (30.0°); riscos: estres-hidric=mitja; reg no-regar | ✅ |
| 1 | Sector_2 (enciam) | 3.0 / 3.0 / 16.0 / 20.0 / 150.0 (19 h) | reg = regar-parcial; dosi = 65.0 | orientar-ombra (0.0°); riscos: estres-hidric=critic; reg regar-parcial (+65.0 %) | ✅ |

**Explicació que dona el sistema** (fet `explicacio`):

- Cicle 1, Sector_1: mantenir-posicio a 30.0 graus. Riscos: estres-hidric=mitja. Candidats: mantenir-posicio(4) orientar-produccio(3) orientar-ombra(3). Descartats: cap. Criteri: maxima valoracio (4 punts).
  - Reg: no-regar (+0%). Necessitat: mitja (esgotat 45.0%). Candidats: no-regar(1). Descartats: regar-complet regar-parcial. Criteri: unica opcio que compleix les restriccions dures.
- Cicle 1, Sector_2: orientar-ombra a 0.0 graus. Riscos: estres-hidric=critic. Candidats: mantenir-posicio(4) orientar-produccio(3) orientar-ombra(9). Descartats: cap. Criteri: maxima valoracio (9 punts).
  - Reg: regar-parcial (+65.0%). Necessitat: critic (esgotat 80.0%). Candidats: no-regar(1) regar-complet(12) regar-parcial(13). Descartats: cap. Criteri: maxima valoracio (13 punts).

<details><summary>Traça rellevant del CLIPS</summary>

```
--- cicle 1 ---
[ELABORACIO] Sector_2: queda un 20.0% d'aigua disponible (enciam tolera esgotar fins al 30.0%). Estres hidric critic.
[ELABORACIO] El risc estres-hidric de Sector_2 activa l'objectiu Obj_Produccio_Cultiu.
[ELABORACIO] Sector_2: s'ha gastat el 80.0% de l'aigua disponible (enciam tolera 30.0%). Necessitat de reg critic.
[ELABORACIO] Sector_1: queda un 55.0% d'aigua disponible (tomaquet tolera esgotar fins al 40.0%). Estres hidric mitja.
[ELABORACIO] Sector_1: s'ha gastat el 45.0% de l'aigua disponible (tomaquet tolera 40.0%). Necessitat de reg mitja.
[PROPOSTA] Sector_2: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_2: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_1: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_1: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_1: orientar-ombra (0.0 graus), hi ha risc per al cultiu.
[PROPOSTA] Sector_2: orientar-ombra (0.0 graus), hi ha risc per al cultiu.
[PROPOSTA] Sector_1: regar-complet (+45.0% de l'aigua disponible) i regar-parcial (+25.0%), hi ha estres hidric.
[PROPOSTA] Sector_2: regar-complet (+80.0% de l'aigua disponible) i regar-parcial (+65.0%), hi ha estres hidric.
[AVALUACIO] Sector_1: orientar-ombra +3 (cultiu, risc estres-hidric mitja).
[AVALUACIO] Sector_2: orientar-ombra +9 (cultiu, risc estres-hidric critic).
[AVALUACIO] Sector_1: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_2: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_1: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_2: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_1: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_2: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_1: REBUIG de regar-parcial (es preveuen 15.0 mm de pluja).
[AVALUACIO] Sector_1: REBUIG de regar-complet (es preveuen 15.0 mm de pluja).
[AVALUACIO] Sector_2: regar-complet -3 (es preveuen 15.0 mm de pluja).
[AVALUACIO] Sector_1: regar-complet -3 (es preveuen 15.0 mm de pluja).
[AVALUACIO] Sector_1: regar-parcial +6 (cultiu, necessitat de reg mitja).
[AVALUACIO] Sector_1: regar-complet +6 (cultiu, necessitat de reg mitja).
[AVALUACIO] Sector_2: regar-parcial +12 (cultiu, necessitat de reg critic).
[AVALUACIO] Sector_2: regar-complet +12 (cultiu, necessitat de reg critic).
[AVALUACIO] Sector_2: regar-complet +2 (enciam, sensibilitat alt).
[AVALUACIO] Sector_1: regar-complet +1 (tomaquet, sensibilitat mitja).
[AVALUACIO] Sector_2: regar-parcial +1 (hora fresca).
[AVALUACIO] Sector_2: regar-complet +1 (hora fresca).
[AVALUACIO] Sector_1: regar-parcial +1 (hora fresca).
[AVALUACIO] Sector_1: regar-complet +1 (hora fresca).
[AVALUACIO] Sector_1: no-regar +1 (estalvi d'aigua).
[AVALUACIO] Sector_2: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_2: es selecciona orientar-ombra. Criteri: maxima valoracio (9 punts).
[SELECCIO] Sector_1: es selecciona mantenir-posicio. Criteri: maxima valoracio (4 punts).
[SELECCIO] Sector_2: reg regar-parcial. Criteri: maxima valoracio (13 punts).
[SELECCIO] Sector_1: regar-parcial queda descartat (AVR1-pluja-prevista).
[SELECCIO] Sector_1: regar-complet queda descartat (AVR1-pluja-prevista).
[SELECCIO] Sector_1: reg no-regar. Criteri: unica opcio que compleix les restriccions dures.
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_1: ORDRE mantenir-posicio -> 30.0 graus.
[APLICACIO] Sector_2: ORDRE orientar-ombra -> 0.0 graus.
[APLICACIO] Sector_2: ORDRE DE REG regar-parcial -> +65.0% de l'aigua disponible.
[EXPLICACIO] Sector_2, cicle 1
[EXPLICACIO] Sector_1, cicle 1
[EXPLICACIO REG] Sector_2, cicle 1
[EXPLICACIO REG] Sector_1, cicle 1
[EPMEM] NOU EPISODI #1: Sector_2, cicle 1, orientar-ombra.
[EPMEM] NOU EPISODI #2: Sector_1, cicle 1, mantenir-posicio.
```

</details>

## CP14 – Reg deficitari de la vinya al llindar

**Cobertura:** límits (reg). **Objectiu i resultat esperat:** La vinya (p = 0,45) amb un 55,0 % d'aigua és just al llindar sense estrès: no es rega (la vinya no s'anticipa). Amb un 54,9 % ja hi ha estrès: es rega en part, fins a la meitat de p (+22,6 %). Al migdia, si continua amb estrès, també es rega.

| Cicle | Sector | Entrada (vent / previsió / T cultiu / aigua / radiació) | Esperat | Obtingut | |
|---|---|---|---|---|---|
| 1 | Sector_3 (vinya) | 3.0 / 3.0 / 24.0 / 55.0 / 400.0 (7 h) | reg = no-regar; risc estres-hidric = cap | mantenir-posicio (30.0°); reg no-regar | ✅ |
| 2 | Sector_3 (vinya) | 3.0 / 3.0 / 24.0 / 54.9 / 400.0 (7 h) | reg = regar-parcial; dosi = 22.6; risc estres-hidric = mitja | mantenir-posicio (30.0°); riscos: estres-hidric=mitja; reg regar-parcial (+22.6 %) | ✅ |
| 3 | Sector_3 (vinya) | 3.0 / 3.0 / 24.0 / 54.9 / 400.0 (13 h) | reg = regar-parcial | mantenir-posicio (30.0°); riscos: estres-hidric=mitja; reg regar-parcial (+22.6 %) | ✅ |

**Explicació que dona el sistema** (fet `explicacio`):

- Cicle 1, Sector_3: mantenir-posicio a 30.0 graus. Riscos: cap. Candidats: mantenir-posicio(4) orientar-produccio(3). Descartats: cap. Criteri: maxima valoracio (4 punts).
  - Reg: no-regar (+0%). Necessitat: anticipada (esgotat 45.0%). Candidats: no-regar(1). Descartats: cap. Criteri: maxima valoracio (1 punts).
- Cicle 2, Sector_3: mantenir-posicio a 30.0 graus. Riscos: estres-hidric=mitja. Candidats: mantenir-posicio(4.5) orientar-produccio(3) orientar-ombra(3). Descartats: cap. Criteri: maxima valoracio (4.5 punts).
  - Reg: regar-parcial (+22.6%). Necessitat: mitja (esgotat 45.1%). Candidats: no-regar(1) regar-complet(7) regar-parcial(9). Descartats: cap. Criteri: maxima valoracio (9 punts).
- Cicle 3, Sector_3: mantenir-posicio a 30.0 graus. Riscos: estres-hidric=mitja. Candidats: mantenir-posicio(8.0) orientar-produccio(3) orientar-ombra(3). Descartats: cap. Criteri: maxima valoracio (8.0 punts).
  - Reg: regar-parcial (+22.6%). Necessitat: mitja (esgotat 45.1%). Candidats: no-regar(1) regar-complet(6) regar-parcial(8). Descartats: cap. Criteri: maxima valoracio (8 punts).

<details><summary>Traça rellevant del CLIPS</summary>

```
--- cicle 1 ---
[ELABORACIO] Sector_3: s'ha gastat el 45.0% de l'aigua disponible (vinya tolera 45.0%). Necessitat de reg anticipada.
[PROPOSTA] Sector_3: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_3: orientar-produccio (30.0 graus).
[AVALUACIO] Sector_3: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_3: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_3: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_3: no-regar +1 (estalvi d'aigua).
[SELECCIO] Sector_3: es selecciona mantenir-posicio. Criteri: maxima valoracio (4 punts).
[SELECCIO] Sector_3: reg no-regar. Criteri: maxima valoracio (1 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_3: ORDRE mantenir-posicio -> 30.0 graus.
[EXPLICACIO] Sector_3, cicle 1
[EPMEM] NOU EPISODI #3: Sector_3, cicle 1, mantenir-posicio.
--- cicle 2 ---
[ELABORACIO] Sector_3: queda un 54.9% d'aigua disponible (vinya tolera esgotar fins al 45.0%). Estres hidric mitja.
[ELABORACIO] El risc estres-hidric de Sector_3 activa l'objectiu Obj_Produccio_Cultiu.
[ELABORACIO] Sector_3: s'ha gastat el 45.1% de l'aigua disponible (vinya tolera 45.0%). Necessitat de reg mitja.
[EPMEM] Sector_3: l'episodi #3 (mantenir-posicio) es valora 'dolenta' (resultat correcte, risc 0 -> 1).
[PROPOSTA] Sector_3: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_3: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_3: orientar-ombra (0.0 graus), hi ha risc per al cultiu.
[PROPOSTA] Sector_3: regar-complet (+45.1% de l'aigua disponible) i regar-parcial (+22.6%), hi ha estres hidric.
[AVALUACIO] Sector_3: orientar-ombra +3 (cultiu, risc estres-hidric mitja).
[AVALUACIO] Sector_3: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_3: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_3: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_3: mantenir-posicio +2 (es el que es va fer el cicle anterior).
[AVALUACIO] Sector_3: mantenir-posicio -1.5 (memoria: a l'episodi #3, cicle 1, va funcionar malament, similitud 0.75).
[AVALUACIO] Sector_3: regar-parcial +6 (cultiu, necessitat de reg mitja).
[AVALUACIO] Sector_3: regar-complet +6 (cultiu, necessitat de reg mitja).
[AVALUACIO] Sector_3: regar-parcial +2 (vinya, sensibilitat baix).
[AVALUACIO] Sector_3: regar-parcial +1 (hora fresca).
[AVALUACIO] Sector_3: regar-complet +1 (hora fresca).
[AVALUACIO] Sector_3: no-regar +1 (estalvi d'aigua).
[REFORC] Sector_3: mantenir-posicio del cicle 1 -> recompensa -1.0 (dolenta), error -1.0, 4 rajoles actualitzades.
[REFORC] Sector_2: mantenir-posicio del cicle 1 -> recompensa 1.0 (bona), error 1.15, 4 rajoles actualitzades.
[REFORC] Sector_1: mantenir-posicio del cicle 1 -> recompensa 1.0 (bona), error 0.98, 4 rajoles actualitzades.
[SELECCIO] Sector_3: es selecciona mantenir-posicio. Criteri: maxima valoracio (4.5 punts).
[SELECCIO] Sector_3: reg regar-parcial. Criteri: maxima valoracio (9 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_3: ORDRE mantenir-posicio -> 30.0 graus.
[APLICACIO] Sector_3: ORDRE DE REG regar-parcial -> +22.6% de l'aigua disponible.
[EXPLICACIO] Sector_3, cicle 2
[EXPLICACIO REG] Sector_3, cicle 2
[EPMEM] NOU EPISODI #6: Sector_3, cicle 2, mantenir-posicio.
--- cicle 3 ---
[ELABORACIO] Sector_3: queda un 54.9% d'aigua disponible (vinya tolera esgotar fins al 45.0%). Estres hidric mitja.
[ELABORACIO] El risc estres-hidric de Sector_3 activa l'objectiu Obj_Produccio_Cultiu.
[ELABORACIO] Sector_3: s'ha gastat el 45.1% de l'aigua disponible (vinya tolera 45.0%). Necessitat de reg mitja.
[EPMEM] Sector_3: l'episodi #6 (mantenir-posicio) es valora 'bona' (resultat correcte, risc 1 -> 1).
[PROPOSTA] Sector_3: mantenir-posicio (30.0 graus).
[PROPOSTA] Sector_3: orientar-produccio (30.0 graus).
[PROPOSTA] Sector_3: orientar-ombra (0.0 graus), hi ha risc per al cultiu.
[PROPOSTA] Sector_3: regar-complet (+45.1% de l'aigua disponible) i regar-parcial (+22.6%), hi ha estres hidric.
[AVALUACIO] Sector_3: orientar-ombra +3 (cultiu, risc estres-hidric mitja).
[AVALUACIO] Sector_3: orientar-produccio +3 (energia, produccio 15.0 / demanda 12.0).
[AVALUACIO] Sector_3: mantenir-posicio +3 (ja es a l'angle optim, 30.0 vs 30.0).
[AVALUACIO] Sector_3: mantenir-posicio +1 (sense moviment).
[AVALUACIO] Sector_3: mantenir-posicio +2 (es el que es va fer el cicle anterior).
[AVALUACIO] Sector_3: mantenir-posicio 2.0 (memoria: a l'episodi #6, cicle 2, va funcionar be, similitud 1.0).
[AVALUACIO] Sector_3: regar-parcial +6 (cultiu, necessitat de reg mitja).
[AVALUACIO] Sector_3: regar-complet +6 (cultiu, necessitat de reg mitja).
[AVALUACIO] Sector_3: regar-parcial +2 (vinya, sensibilitat baix).
[AVALUACIO] Sector_3: no-regar +1 (estalvi d'aigua).
[REFORC] Sector_3: mantenir-posicio del cicle 2 -> recompensa 1.0 (bona), error 0.98, 5 rajoles actualitzades.
[REFORC] Sector_2: mantenir-posicio del cicle 2 -> recompensa 1.0 (bona), error 0.54, 4 rajoles actualitzades.
[REFORC] Sector_1: mantenir-posicio del cicle 2 -> recompensa 1.0 (bona), error 0.49, 4 rajoles actualitzades.
[SELECCIO] Sector_3: es selecciona mantenir-posicio. Criteri: maxima valoracio (8.0 punts).
[SELECCIO] Sector_3: reg regar-parcial. Criteri: maxima valoracio (8 punts).
[SELECCIO -> APLICACIO]
[APLICACIO] Sector_3: ORDRE mantenir-posicio -> 30.0 graus.
[APLICACIO] Sector_3: ORDRE DE REG regar-parcial -> +22.6% de l'aigua disponible.
[EXPLICACIO] Sector_3, cicle 3
[EXPLICACIO REG] Sector_3, cicle 3
[EPMEM] NOU EPISODI #9: Sector_3, cicle 3, mantenir-posicio.
```

</details>
