# Paquete Agrovoltaic corregido (2026-11-07)

Este ZIP ligero incluye el proyecto y las correcciones verificadas del paquete original, incluyendo el código CLIPS/Python, la UI/Mode Defensa, las tres ontologías, los scripts, README y los resúmenes y trazas de experimentos.

Para reducir el peso se excluyeron SOLO:
- Historial Git (.git/); el proyecto sigue siendo ejecutable y los archivos .gitignore/.gitattributes se conservan.
- CSV de resultados horarios (nombres que contienen "horari") de simulador/resultats, conservados sin alteración en los tres ZIP de evidencias adicionales.

Si necesitas todos los datos experimentales originales, descomprime los ZIP de evidencias adicionales encima de este proyecto, manteniendo la misma estructura de carpetas. Los resultados agregados, metadatos y scripts permanecen en el ZIP ligero.

El paquete no incluye un entorno Python instalado ni reemplaza la validación funcional con clipspy en el ordenador de destino.
