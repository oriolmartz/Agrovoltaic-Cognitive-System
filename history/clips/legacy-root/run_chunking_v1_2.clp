; Demostracio del chunking (versio v1_2): impasses, regles noves i reutilitzacio.
;
; Cicle 1: dues situacions noves
;   - Sector_1 (tomaquet a 30 C): ombra i produccio empaten           -> impasse, chunk-1
;   - Sector_3: sense lectura de vent, previsio de vent suau          -> impasse, chunk-2 (hold)
; Cicle 2: dues situacions conegudes i una de nova
;   - Sector_3 (vinya a 33 C): el mateix empat                        -> chunk-1, sense impasse
;   - Sector_2: sense vent, previsio suau                             -> chunk-2, sense impasse
;   - Sector_1: sense vent, previsio de tempesta (20 m/s)             -> impasse, chunk-3 (seguretat)
; Cicle 3: el que s'ha apres es reutilitza i surt l'ultim cas
;   - Sector_2: sense vent, previsio de 18 m/s                        -> chunk-3, sense impasse
;   - Sector_1: sense vent, previsio suau, pero el cicle anterior
;               hi havia risc mecanic (historial)                     -> impasse, chunk-4 (seguretat)

(clear)
(load "soar_v1_2.clp")
(unwatch all)
(set-dynamic-constraint-checking TRUE)
(reset)
(set-current-module DOMINI)

(deffunction DOMINI::simula-actuadors (?c)
  ; tots els panells arriben a l'angle ordenat al cicle ?c
  (foreach ?ord (find-all-facts ((?x ordre-actuador)) (eq ?x:cicle ?c))
    (foreach ?p (find-all-facts ((?y panell)) (eq ?y:sector (fact-slot-value ?ord sector)))
      (modify ?p (angle (float (fact-slot-value ?ord angle-objectiu)))))))

(deffunction DOMINI::comenca-cicle ()
  (do-for-fact ((?f fase)) TRUE (retract ?f))
  (assert (fase (nom percepcio))))

; ---------------------------------------------------------------------------
(printout t crlf "============================================================" crlf)
(printout t "  CICLE 1: dues situacions noves" crlf)
(printout t "============================================================" crlf crlf)

(do-for-fact ((?o observacio)) (eq ?o:sector Sector_1) (modify ?o (temperatura-cultiu 30.0)))
(do-for-fact ((?o observacio)) (eq ?o:sector Sector_3) (modify ?o (vent absent)))
(run)
(set-current-module DOMINI)

; ---------------------------------------------------------------------------
(simula-actuadors 1)
(assert (energia (sector Sector_1) (cicle 2) (produccio-actual 17.0) (demanda 12.0)))
(assert (energia (sector Sector_2) (cicle 2) (produccio-actual 16.0) (demanda 11.5)))
(assert (energia (sector Sector_3) (cicle 2) (produccio-actual 15.0) (demanda 13.0)))
; Sector_1: sense lectura de vent, previsio de tempesta
(assert (observacio (sector Sector_1) (cicle 2)
  (radiacio 300.0) (temperatura-aire 23.0) (temperatura-cultiu 24.0) (humitat-sol 72.0) (pluja 0.0)))
(assert (prediccio (sector Sector_1) (cicle 2) (radiacio 320.0) (temperatura 24.0) (vent 20.0) (pluja 0.0)))
; Sector_2: sense lectura de vent, previsio suau
(assert (observacio (sector Sector_2) (cicle 2)
  (radiacio 150.0) (temperatura-aire 17.0) (temperatura-cultiu 18.0) (humitat-sol 78.0) (pluja 0.0)))
(assert (prediccio (sector Sector_2) (cicle 2) (radiacio 160.0) (temperatura 18.0) (vent 5.0) (pluja 0.0)))
; Sector_3: vinya a 33 C
(assert (observacio (sector Sector_3) (cicle 2)
  (radiacio 500.0) (temperatura-aire 31.0) (temperatura-cultiu 33.0) (humitat-sol 68.0) (vent 4.0) (pluja 0.0)))
(assert (prediccio (sector Sector_3) (cicle 2) (radiacio 520.0) (temperatura 33.0) (vent 5.0) (pluja 0.0)))

(printout t "============================================================" crlf)
(printout t "  CICLE 2: dues situacions conegudes i una de nova" crlf)
(printout t "============================================================" crlf crlf)
(comenca-cicle)
(run)
(set-current-module DOMINI)

; ---------------------------------------------------------------------------
(simula-actuadors 2)
(assert (energia (sector Sector_1) (cicle 3) (produccio-actual 10.0) (demanda 12.0)))
(assert (energia (sector Sector_2) (cicle 3) (produccio-actual 16.0) (demanda 11.5)))
(assert (energia (sector Sector_3) (cicle 3) (produccio-actual 15.0) (demanda 13.0)))
; Sector_1: sense lectura de vent, previsio suau (pero el cicle 2 hi havia risc mecanic)
(assert (observacio (sector Sector_1) (cicle 3)
  (radiacio 300.0) (temperatura-aire 23.0) (temperatura-cultiu 24.0) (humitat-sol 72.0) (pluja 0.0)))
(assert (prediccio (sector Sector_1) (cicle 3) (radiacio 320.0) (temperatura 24.0) (vent 6.0) (pluja 0.0)))
; Sector_2: sense lectura de vent, previsio de 18 m/s
(assert (observacio (sector Sector_2) (cicle 3)
  (radiacio 150.0) (temperatura-aire 17.0) (temperatura-cultiu 18.0) (humitat-sol 78.0) (pluja 0.0)))
(assert (prediccio (sector Sector_2) (cicle 3) (radiacio 160.0) (temperatura 18.0) (vent 18.0) (pluja 0.0)))
; Sector_3: normal
(assert (observacio (sector Sector_3) (cicle 3)
  (radiacio 500.0) (temperatura-aire 24.0) (temperatura-cultiu 25.0) (humitat-sol 70.0) (vent 4.0) (pluja 0.0)))
(assert (prediccio (sector Sector_3) (cicle 3) (radiacio 520.0) (temperatura 25.0) (vent 5.0) (pluja 0.0)))

(printout t "============================================================" crlf)
(printout t "  CICLE 3: reutilitzacio i un cas per historial" crlf)
(printout t "============================================================" crlf crlf)
(comenca-cicle)
(run)
(set-current-module DOMINI)

; ---------------------------------------------------------------------------
(printout t "============================================================" crlf)
(printout t "  RESUM" crlf)
(printout t "============================================================" crlf)
(printout t "Impasses (subobjectius creats):" crlf)
(do-for-all-facts ((?g subobjectiu)) TRUE
  (printout t "   " ?g:id " " ?g:tipus " (" ?g:estat ")" crlf))
(printout t "Regles apreses:" crlf)
(do-for-all-facts ((?f fragment-apres)) TRUE
  (printout t "   " ?f:nom " (de l'impasse " ?f:impas-origen ", cicle " ?f:cicle ")" crlf))
(printout t "Decisions preses per un chunk (sense impasse):" crlf)
(do-for-all-facts ((?p preferencia)) (str-index "chunk" ?p:font)
  (printout t "   cicle " ?p:cicle ", " ?p:sector ": " ?p:op " " ?p:tipus " (" ?p:font ")" crlf))
(printout t "Ordres:" crlf)
(do-for-all-facts ((?o ordre-actuador)) TRUE
  (printout t "   cicle " ?o:cicle ", " ?o:sector ": " ?o:accio " a " ?o:angle-objectiu " graus" crlf))
