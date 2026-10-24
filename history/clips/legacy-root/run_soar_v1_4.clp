; ============================================================================
; run_soar_v1_4.clp  -  prova funcional de soar_v1_4.clp
;
; Ús:  clips -f run_soar_v1_4.clp
;      (els dos fitxers han d'estar al mateix directori)
;
; Escenari (5 cicles):
;   C1  operacio normal                    -> operadors per defecte + memoria episodica
;   C2  operacio normal, panells a l'angle -> valoracio dels episodis (resultat correcte)
;   C3  vent critic a Sector_1             -> restriccio dura + posicio-seguretat
;   C4  sense lectura de vent a Sector_2   -> impasse dades-insuficients + CHUNK
;   C5  mateixa situacio que C4            -> el chunk resol sense impasse
; Despres:
;   - persistencia dels chunks (undefrule + reconstruccio des del fitxer)
;   - persistencia de la memoria episodica (retract + carrega-epmem)
;   - consultes epmem: query per contingut i previous (temporal)
;
; NOTA: els resultats esperats s'han deduit llegint el codi, no executant-lo.
; ============================================================================

(remove "epmem_prova.dat")
(remove "chunks_prova.dat")

(load "soar_v1_4.clp")

(defmodule PROVA
  (import DOMINI ?ALL)
  (import MEMORIA deffunction ?ALL)
  (import APRENENTATGE deffunction ?ALL))

(defglobal ?*ok* = 0 ?*ko* = 0)

; --- utilitats de prova ---------------------------------------------------------

(deffunction prova (?nom ?cond)
  (if ?cond
   then (bind ?*ok* (+ ?*ok* 1)) (printout t "  [PASS] " ?nom crlf)
   else (bind ?*ko* (+ ?*ko* 1)) (printout t "  [FAIL] " ?nom crlf))
  ?cond)

(deffunction seleccionat (?s ?c ?op)
  (any-factp ((?o operador-seleccionat))
    (and (eq ?o:sector ?s) (eq ?o:cicle ?c) (eq ?o:nom ?op))))

(deffunction ordre-de-accio (?s ?c ?acc)
  (any-factp ((?o ordre-actuador))
    (and (eq ?o:sector ?s) (eq ?o:cicle ?c) (eq ?o:accio ?acc))))

(deffunction rebuig (?s ?c ?op)
  (any-factp ((?p preferencia))
    (and (eq ?p:sector ?s) (eq ?p:cicle ?c) (eq ?p:op ?op) (eq ?p:tipus rebuig))))

(deffunction risc-de (?s ?c ?tipus ?nivell)
  (any-factp ((?r risc))
    (and (eq ?r:sector ?s) (eq ?r:cicle ?c) (eq ?r:tipus ?tipus) (eq ?r:nivell ?nivell))))

(deffunction n-episodis ()
  (length$ (find-all-facts ((?e epmem-episodi)) TRUE)))

(deffunction fitxer-existeix (?f)
  (if (open ?f fx-prova "r") then (close fx-prova) TRUE else FALSE))

; --- simulador (simulat a mma) --------------------------------------------------

(deffunction mou-panell (?id ?angle)
  (do-for-fact ((?p panell)) (eq ?p:id ?id)
    (modify ?p (angle ?angle))))

; El controlador de la capa Python ha de fer aquest pas: tornar a percepcio.
(deffunction nou-cicle ()
  (do-for-all-facts ((?f fase)) TRUE (retract ?f))
  (assert (fase (nom percepcio)))
  TRUE)

(deffunction dades-ciclo (?c ?v1 ?v2 ?v3)
  (assert (observacio (sector Sector_1) (cicle ?c) (radiacio 300.0) (temperatura-aire 23.0)
                      (temperatura-cultiu 24.0) (humitat-sol 75.0) (vent ?v1) (pluja 0.0)))
  (assert (observacio (sector Sector_2) (cicle ?c) (radiacio 150.0) (temperatura-aire 17.0)
                      (temperatura-cultiu 18.0) (humitat-sol 80.0) (vent ?v2) (pluja 0.0)))
  (assert (observacio (sector Sector_3) (cicle ?c) (radiacio 500.0) (temperatura-aire 24.0)
                      (temperatura-cultiu 25.0) (humitat-sol 70.0) (vent ?v3) (pluja 0.0)))
  (assert (prediccio (sector Sector_1) (cicle ?c) (radiacio 320.0) (temperatura 24.0)
                     (vent 5.0) (pluja 0.0)))
  (assert (prediccio (sector Sector_2) (cicle ?c) (radiacio 160.0) (temperatura 18.0)
                     (vent 5.0) (pluja 0.0)))
  (assert (prediccio (sector Sector_3) (cicle ?c) (radiacio 520.0) (temperatura 25.0)
                     (vent 5.0) (pluja 0.0)))
  (assert (energia (sector Sector_1) (cicle ?c) (produccio-actual 18.5) (demanda 12.0)))
  (assert (energia (sector Sector_2) (cicle ?c) (produccio-actual 16.2) (demanda 11.5)))
  (assert (energia (sector Sector_3) (cicle ?c) (produccio-actual 21.8) (demanda 13.0)))
  TRUE)

; --- memoria episodica ------------------------------------------------------------

(deffunction id-maxim (?s)
  (bind ?m 0)
  (do-for-all-facts ((?e epmem-episodi)) (eq ?e:sector ?s)
    (if (> ?e:id ?m) then (bind ?m ?e:id)))
  ?m)

(deffunction consulta-anterior (?s ?ref)
  (assert (epmem-consulta (id P-prova) (sector ?s) (cicle 6)
                          (tipus previous) (ref ?ref))))

(deffunction prova-persistencia-epmem ()
  (bind ?abans (n-episodis))
  (do-for-all-facts ((?e epmem-episodi)) TRUE (retract ?e))
  (bind ?carregats (carrega-epmem "epmem_prova.dat"))
  (prova "epmem: episodis recarregats = els que hi havia" (= ?carregats ?abans))
  (prova "epmem: el fitxer conte episodis" (> ?carregats 0))
  TRUE)

; =============================================================================
; EXECUCIO
; =============================================================================

(printout t crlf "=== INICI ===" crlf)
(reset)
(set-current-module PROVA)
(activa-epmem "epmem_prova.dat")
(activa-persistencia "chunks_prova.dat")

; --- C1 -----------------------------------------------------------------------
(printout t crlf "=== C1: operacio normal ===" crlf)
(run)
(set-current-module PROVA)
(prova "C1 Sector_1 selecciona orientar-produccio" (seleccionat Sector_1 1 orientar-produccio))
(prova "C1 Sector_2 selecciona mantenir-posicio (ja es a l'angle optim)"
       (seleccionat Sector_2 1 mantenir-posicio))
(prova "C1 Sector_3 selecciona orientar-produccio" (seleccionat Sector_3 1 orientar-produccio))
(prova "C1 cap risc elaborat" (not (any-factp ((?r risc)) (eq ?r:cicle 1))))
(prova "C1 tres episodis a la memoria de treball"
       (= 3 (length$ (find-all-facts ((?e episodi)) (eq ?e:cicle 1)))))
(prova "C1 tres episodis a la memoria a llarg termini" (= 3 (n-episodis)))
(prova "C1 fitxer epmem desat" (fitxer-existeix "epmem_prova.dat"))

; --- C2 -----------------------------------------------------------------------
(printout t crlf "=== C2: operacio normal, panells arriben a l'angle ===" crlf)
(mou-panell Panell_1_1 30.0)
(mou-panell Panell_1_2 30.0)
(mou-panell Panell_3_1 20.0)
(mou-panell Panell_3_2 20.0)
(nou-cicle)
(dades-ciclo 2 4.0 4.0 4.0)
(run)
(set-current-module PROVA)
(prova "C2 S1: episodi del cicle 1 = correcte"
       (any-factp ((?e episodi))
         (and (eq ?e:cicle 1) (eq ?e:sector Sector_1) (eq ?e:resultat correcte))))
(prova "C2 S3: episodi del cicle 1 = correcte"
       (any-factp ((?e episodi))
         (and (eq ?e:cicle 1) (eq ?e:sector Sector_3) (eq ?e:resultat correcte))))
(prova "C2 valoracio feta als 3 episodis del cicle 1"
       (= 3 (length$ (find-all-facts ((?e epmem-episodi))
                       (and (eq ?e:cicle 1) (neq ?e:valoracio pendent))))))
(prova "C2 Sector_2 manté selecciona mantenir-posicio"
       (seleccionat Sector_2 2 mantenir-posicio))

; --- C3 -----------------------------------------------------------------------
(printout t crlf "=== C3: vent critic a Sector_1 ===" crlf)
(nou-cicle)
(dades-ciclo 3 18.0 4.0 4.0)
(run)
(set-current-module PROVA)
(prova "C3 risc mecanic critic a Sector_1" (risc-de Sector_1 3 mecanic critic))
(prova "C3 orientar-produccio rebutjat (restriccio dura)" (rebuig Sector_1 3 orientar-produccio))
(prova "C3 Sector_1 selecciona posicio-seguretat" (seleccionat Sector_1 3 posicio-seguretat))
(prova "C3 ordre d'actuador posicio-seguretat a Sector_1"
       (ordre-de-accio Sector_1 3 posicio-seguretat))
(prova "C3 Sector_2 no es veu afectat" (seleccionat Sector_2 3 mantenir-posicio))

; --- C4 -----------------------------------------------------------------------
(printout t crlf "=== C4: Sector_2 sense lectura de vent (impasse de dades) ===" crlf)
; el simulador ha mogut el panell de Sector_1 a l'angle de seguretat (0 graus)
(mou-panell Panell_1_1 0.0)
(mou-panell Panell_1_2 0.0)
(nou-cicle)
(dades-ciclo 4 4.0 absent 4.0)
(run)
(set-current-module PROVA)
(prova "C4 risc de dades critic a Sector_2" (risc-de Sector_2 4 dades critic))
(prova "C4 Sector_2 selecciona sollicitar-dades (resolucio d'impasse)"
       (seleccionat Sector_2 4 sollicitar-dades))
(prova "C4 chunk creat per l'impasse dades-insuficients"
       (any-factp ((?f fragment-apres))
         (and (eq ?f:impas-origen dades-insuficients) (eq ?f:cicle 4))))
(prova "C4 regla chunk-1 existeix" (member$ chunk-1 (get-defrule-list DELIBERACIO)))
(prova "C4 chunk escrit al fitxer" (fitxer-existeix "chunks_prova.dat"))

; --- C5 -----------------------------------------------------------------------
(printout t crlf "=== C5: mateixa situacio que C4 (ha d'actuar el chunk) ===" crlf)
(nou-cicle)
(dades-ciclo 5 4.0 absent 4.0)
(run)
(set-current-module PROVA)
(prova "C5 Sector_2 sense impasse (no es crea subobjectiu)"
       (not (any-factp ((?g subobjectiu)) (eq ?g:id G-Sector_2-5))))
(prova "C5 Sector_2 selecciona sollicitar-dades" (seleccionat Sector_2 5 sollicitar-dades))
(prova "C5 preferencia requerida generada pel chunk"
       (any-factp ((?p preferencia))
         (and (eq ?p:sector Sector_2) (eq ?p:cicle 5) (eq ?p:tipus requerida))))

; --- persistencia de chunks -------------------------------------------------------
(printout t crlf "=== Persistencia dels chunks ===" crlf)
(undefrule DELIBERACIO::chunk-1)
(prova "chunk-1 eliminat de memoria"
       (not (member$ chunk-1 (get-defrule-list DELIBERACIO))))
(prova "chunk-1 reconstruit des del fitxer"
       (> (activa-persistencia "chunks_prova.dat") 0))
(prova "chunk-1 present despres de recarregar"
       (member$ chunk-1 (get-defrule-list DELIBERACIO)))

; --- persistencia de memoria episodica --------------------------------------------
(printout t crlf "=== Persistencia de la memoria episodica ===" crlf)
(prova-persistencia-epmem)

; --- consultes a la memoria episodica ---------------------------------------------
(printout t crlf "=== Consultes a la memoria episodica ===" crlf)
(assert (epmem-consulta (id Q-prova-1) (sector Sector_1) (cicle 6)
                        (etiqueta orientar-produccio)
                        (cue sector=Sector_1 cultiu=tomaquet operador=orientar-produccio)
                        (requereix operador=orientar-produccio)))
(run)
(set-current-module PROVA)
(prova "query: recupera un episodi de Sector_1 amb orientar-produccio"
       (any-factp ((?r epmem-resultat))
         (and (eq ?r:consulta Q-prova-1) (eq ?r:exit si) (> ?r:memoria-id 0))))

(consulta-anterior Sector_1 (id-maxim Sector_1))
(run)
(set-current-module PROVA)
(prova "previous: troba l'episodi anterior de Sector_1"
       (any-factp ((?r epmem-resultat))
         (and (eq ?r:consulta P-prova) (eq ?r:exit si))))
(epmem-imprimeix (id-maxim Sector_1))

(printout t crlf "=== RESUM: " ?*ok* " correctes, " ?*ko* " incorrectes ===" crlf)
