; Execucio de demostracio: dos cicles de decisio.
; Entre cicle i cicle, aquest fitxer fa de simulador: mou els panells
; i envia les lectures noves. Mes endavant ho fara Python.

; (clear) esborra el que hi hagi d'una execucio anterior (inclosos els chunks apresos)
(clear)
(load "soar_v1_2.clp")
(unwatch all)
(set-dynamic-constraint-checking TRUE)
(reset)
(set-current-module DOMINI)

(printout t crlf "============================================================" crlf)
(printout t "  PLANTA AGROVOLTAICA - CICLE 1" crlf)
(printout t "  Sector_1: tomaquet a 30 C. Sector_3: sense lectura de vent (hold + sollicitar dades)." crlf)
(printout t "============================================================" crlf crlf)

(do-for-fact ((?o observacio)) (eq ?o:sector Sector_1) (modify ?o (temperatura-cultiu 30.0)))
(do-for-fact ((?o observacio)) (eq ?o:sector Sector_3) (modify ?o (vent absent)))
(run)
(set-current-module DOMINI)


; --- simulador: aplica les ordres del cicle 1 ---
; El Sector_1 simula una fallada: els seus panells no es mouen.
(foreach ?ord (find-all-facts ((?x ordre-actuador)) (eq ?x:cicle 1))
  (if (neq (fact-slot-value ?ord sector) Sector_1) then
    (foreach ?p (find-all-facts ((?y panell)) (eq ?y:sector (fact-slot-value ?ord sector)))
      (modify ?p (angle (float (fact-slot-value ?ord angle-objectiu)))))))

; --- simulador: lectures del cicle 2 ---
(assert (energia (sector Sector_1) (cicle 2) (produccio-actual 17.0) (demanda 12.0)))
(assert (energia (sector Sector_2) (cicle 2) (produccio-actual 16.0) (demanda 11.5)))
(assert (energia (sector Sector_3) (cicle 2) (produccio-actual 15.0) (demanda 13.0)))
(assert (observacio (sector Sector_1) (cicle 2)
  (radiacio 300.0) (temperatura-aire 23.0) (temperatura-cultiu 24.0)
  (humitat-sol 72.0) (vent 4.0) (pluja 0.0)))
(assert (prediccio (sector Sector_1) (cicle 2)
  (radiacio 320.0) (temperatura 24.0) (vent 5.0) (pluja 0.0)))
(assert (observacio (sector Sector_2) (cicle 2)
  (radiacio 150.0) (temperatura-aire 17.0) (temperatura-cultiu 18.0)
  (humitat-sol 78.0) (vent 4.0) (pluja 0.0)))
(assert (prediccio (sector Sector_2) (cicle 2)
  (radiacio 160.0) (temperatura 18.0) (vent 5.0) (pluja 0.0)))
(assert (observacio (sector Sector_3) (cicle 2)
  (radiacio 500.0) (temperatura-aire 31.0) (temperatura-cultiu 33.0)
  (humitat-sol 68.0) (vent 4.0) (pluja 0.0)))
(assert (prediccio (sector Sector_3) (cicle 2)
  (radiacio 520.0) (temperatura 33.0) (vent 5.0) (pluja 0.0)))

(printout t "============================================================" crlf)
(printout t "  PLANTA AGROVOLTAICA - CICLE 2" crlf)
(printout t "  Sector_1: l'actuador no s'ha mogut. Sector_3: vinya a 33 C." crlf)
(printout t "============================================================" crlf crlf)

(do-for-fact ((?f fase)) TRUE (retract ?f))
(assert (fase (nom percepcio)))
(run)
