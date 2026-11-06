# E23 — Comparativa de estrategias de olvido

## Resumen

E23 compara una línea base sin olvido con seis estrategias de gestión de la
memoria episódica (EpMem), a tres límites de capacidad. Este informe resume
los resultados disponibles en los CSV de esta carpeta.

**Conclusión del piloto:** reducir EpMem redujo también el número de episodios
examinados en las consultas. En esta ejecución, las decisiones, la energía y
las métricas de estrés coincidieron con la línea base. Los datos no bastan para
concluir que las estrategias se comportarán igual con más días, otras semillas
u otros escenarios.

## Escenario y configuración

- **Datos:** escenario secuencial de Ribera, del 1 de enero al 1 de marzo de
  2023 (60 días).
- **Repeticiones:** una semilla (`0`). Cada brazo se compara con la misma
  semilla y los mismos días.
- **Línea base:** 2.520 decisiones/episodios y 50 resúmenes semánticos al
  finalizar.
- **Capacidades:** 75 %, 50 % y 25 % de los episodios previstos en la línea
  base. El objetivo de retención es el 80 % de la capacidad máxima; las
  protecciones de grupos pueden hacer que algunos brazos retengan más que ese
  objetivo.
- **Archivo:** habilitado. Los episodios retirados se guardan para que el
  olvido sea reversible.

## Qué significa cada brazo

| Brazo | Estrategia | Qué hace |
|---|---|---|
| **A — Sin olvido** | Control | Mantiene los episodios en EpMem; sirve como referencia. |
| **B — Ventana** | Ventana temporal | Aplica la política temporal existente y conserva episodios recientes o aún no consolidados. |
| **C — Aleatorio** | Selección aleatoria | Elige al azar entre los episodios elegibles para retirar. |
| **D — Antigüedad** | FIFO | Retira primero los episodios elegibles más antiguos. |
| **E — Activación de episodio** | Uso individual | Prioriza para el olvido episodios con menor activación/recuperación episódica. |
| **F — Activación de grupo** | Uso del grupo | Prioriza grupos menos activados y, dentro del grupo, episodios neutros y antiguos; conserva representantes y aplica período de gracia. |
| **G — Grupo sin protecciones** | Variante de F | Usa activación de grupo, pero omite el período de gracia y el mínimo de representantes. Mantiene el requisito de consolidación semántica. |

En esta implementación, B se activa al superar el objetivo de retención de la
ventana; las políticas C–G comienzan a retirar episodios al superar la
capacidad máxima y tratan de volver al objetivo. Por tanto, B no tiene
exactamente el mismo disparador que C–G.

## Resultados por capacidad

“Examinados” es el total de episodios recorridos por las consultas de EpMem
durante la simulación. La reducción se calcula respecto a los **407.311**
examinados por A. “Finales” es el número de episodios que quedaban en EpMem al
final. La fidelidad fue del **100 % en los 18 casos con olvido** (2.520 de
2.520 decisiones coincidieron con A), por lo que se indica una sola vez en la
tabla.

### Capacidad máxima del 25 %

| Brazo | Episodios finales | Episodios examinados | Reducción de examinados | Fidelidad |
|---|---:|---:|---:|---:|
| A — Sin olvido | 2.520 | 407.311 | — | Referencia |
| B — Ventana | 504 | 117.864 | 71,1 % | 100 % |
| C — Aleatorio | 585 | 133.526 | 67,2 % | 100 % |
| D — Antigüedad | 585 | 132.657 | 67,4 % | 100 % |
| E — Activación de episodio | 585 | 132.255 | 67,5 % | 100 % |
| F — Activación de grupo | 585 | 149.662 | 63,3 % | 100 % |
| G — Grupo sin protecciones | 585 | 203.998 | 49,9 % | 100 % |

### Capacidad máxima del 50 %

| Brazo | Episodios finales | Episodios examinados | Reducción de examinados | Fidelidad |
|---|---:|---:|---:|---:|
| A — Sin olvido | 2.520 | 407.311 | — | Referencia |
| B — Ventana | 1.008 | 224.001 | 45,0 % | 100 % |
| C — Aleatorio | 1.245 | 249.080 | 38,8 % | 100 % |
| D — Antigüedad | 1.245 | 248.023 | 39,1 % | 100 % |
| E — Activación de episodio | 1.245 | 246.288 | 39,5 % | 100 % |
| F — Activación de grupo | 1.245 | 305.770 | 24,9 % | 100 % |
| G — Grupo sin protecciones | 1.245 | 310.639 | 23,7 % | 100 % |

### Capacidad máxima del 75 %

| Brazo | Episodios finales | Episodios examinados | Reducción de examinados | Fidelidad |
|---|---:|---:|---:|---:|
| A — Sin olvido | 2.520 | 407.311 | — | Referencia |
| B — Ventana | 1.512 | 318.213 | 21,9 % | 100 % |
| C — Aleatorio | 1.758 | 351.158 | 13,8 % | 100 % |
| D — Antigüedad | 1.758 | 350.283 | 14,0 % | 100 % |
| E — Activación de episodio | 1.758 | 349.057 | 14,3 % | 100 % |
| F — Activación de grupo | 1.758 | 371.689 | 8,7 % | 100 % |
| G — Grupo sin protecciones | 1.758 | 376.326 | 7,6 % | 100 % |

Los valores finales de C–G superan el objetivo de retención en algunos casos:
los grupos semánticos protegidos deben conservar suficientes episodios
representativos. El número de resúmenes semánticos fue 50 en todos los casos.

## Calidad de las decisiones y estadística

En los CSV, todos los brazos muestran la misma media de energía (**211,394
kWh/día**) y las mismas medias de estrés por radiación (**3,1 h/día**), calor
(**0,4 h/día**) y agua (**0 h/día**). También registran cero violaciones y
cero impasses en este piloto.

`E23_tests.csv` compara cada brazo/capacidad con A mediante pruebas apareadas
por día y ajuste de Holm:

- Energía, estrés, violaciones, impasses y fidelidad: `p (Holm) = 1` en todas
  las comparaciones, coherente con los resultados coincidentes.
- Episodios examinados: las comparaciones muestran diferencias tras el ajuste
  (valores `p (Holm)` entre `9,7 × 10⁻⁶` y `0,00727`).

La unidad de repetición de esta ejecución es solo una semilla; los 60 días son
observaciones de una misma simulación secuencial, no 60 semillas independientes.
Por ello, estos valores estadísticos describen este piloto y no sustituyen
repeticiones con más semillas y escenarios.

El tiempo mediano del ciclo CLIPS también se guarda en la comparativa, pero no
debe interpretarse como una medición limpia de aceleración: no aísla la fase de
búsqueda y puede verse afectado por la carga de ejecución.

## Archivos de resultados

- [`E23_comparativa.csv`](./E23_comparativa.csv): resumen por brazo y capacidad.
- [`E23_tests.csv`](./E23_tests.csv): pruebas apareadas y ajuste de Holm.
- [`E23_compromis.svg`](./E23_compromis.svg): episodios finales frente a
  fidelidad.
- [`E23_evolucio.csv`](./E23_evolucio.csv) y [`E23_memoria.csv`](./E23_memoria.csv):
  evolución temporal y fotos de memoria.
- [`E23_per_dia.csv`](./E23_per_dia.csv) y [`E23_horari.csv.gz`](./E23_horari.csv.gz):
  métricas agregadas por día y por hora.
- `E23_oblit_auditoria.csv`: auditoría de episodios retirados.
- `arxiu/`: episodios archivados por las políticas de olvido.

## Reproducir o ampliar el experimento

Desde la carpeta `simulador`:

```powershell
python experiments.py E23 --dies 60 --llavors 5 --processos 4
```

Para simular todo 2023, omite `--dies 60`. Para probar el borrado irreversible,
añade `--sense-arxiu`. La documentación del diseño completo está en
[`../../estrategia_oblit.md`](../../estrategia_oblit.md).
