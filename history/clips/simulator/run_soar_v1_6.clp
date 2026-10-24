; ============================================================================
; run_soar_v1_6.clp  -  prova funcional de soar_v1_6.clp
;
; Ús:  clips -f run_soar_v1_6.clp
;      (els dos fitxers han d'estar al mateix directori)
;
; Escenari (5 cicles):
;   C1  operacio normal                    -> operadors per defecte + memoria episodica
;   C2  operacio normal, panells a l'angle -> valoracio dels episodis (resultat correcte)
;   C3  vent critic a Sector_1             -> restriccio dura + posicio-seguretat
;   C4  sense lectura de vent a Sector_2   -> impasse dades-insuficients + CHUNK
;   C5  mateixa situacio que C4            -> el chunk resol sense impasse
;   C6  empat forcat a Sector_3            -> impasse d'empat + chunk (amb els objectius)
;   C7  sense empat a Sector_3             -> el chunk dispara pero el motiu no parla d'empat
;   C8  vent critic a Sector_1             -> posicio-seguretat
;   C9  Sector_1 sense lectura de vent     -> impasse, branca historial: el chunk PROPOSA un operador
;   C10 vent critic a Sector_1
;   C11 Sector_1 sense lectura de vent     -> el chunk proposa posicio-seguretat sense impasse
; Despres:
;   - persistencia dels chunks (undefrule + reconstruccio des del fitxer)
;   - persistencia de la memoria episodica (retract + carrega-epmem)
;   - consultes epmem: query per contingut i previous (temporal)
; Tot l'anterior s'executa AMB EL REFORÇ DESACTIVAT (comportament de la v1_5).
; Despres, sessio nova amb el reforç activat (i la memoria episodica desactivada):
;   R1-R2  operacio normal                 -> recompenses i rajoles Q actualitzades
;   R3     empat forcat a Sector_3         -> el reforç el desfa sense impasse
;   R4     empat forcat, epsilon enorme    -> Q no decideix: impasse + chunk RL (valor inicial prior)
;   R5     el panell de Sector_3 no arriba -> recompensa -1: el valor del chunk baixa
;
; Els chunks es busquen per impas-origen i cicle, no pel nom (chunk-N depen de l'ordre).
; ============================================================================

(remove "epmem_prova.dat")
(remove "chunks_prova.dat")

(load "soar_v1_6.clp")

(defmodule PROVA
  (import DOMINI ?ALL)
  (import MEMORIA deffunction ?ALL)
  (import APRENENTATGE deffunction ?ALL)
  (import DELIBERACIO deffunction ?ALL)
  (import REFORC deffunction ?ALL))

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

; Nom del chunk apres en un impasse d'un tipus i cicle (o FALSE).
(deffunction chunk-de (?impas ?c)
  (bind ?r FALSE)
  (do-for-fact ((?f fragment-apres)) (and (eq ?f:impas-origen ?impas) (eq ?f:cicle ?c))
    (bind ?r ?f:nom))
  ?r)

(deffunction codi-de (?nom)
  (bind ?r "")
  (do-for-fact ((?f fragment-apres)) (eq ?f:nom ?nom) (bind ?r ?f:codi))
  ?r)

(deffunction motiu-de (?s ?c)
  (bind ?r "")
  (do-for-fact ((?o operador-seleccionat)) (and (eq ?o:sector ?s) (eq ?o:cicle ?c))
    (bind ?r ?o:motiu))
  ?r)

(deffunction parla-d-empat (?s ?c)
  (neq (str-index "empat" (motiu-de ?s ?c)) FALSE))

(deffunction fitxer-existeix (?f)
  (if (open ?f fx-prova "r") then (close fx-prova) TRUE else FALSE))

; --- simulador (simulat a mma) --------------------------------------------------

(deffunction mou-panell (?id ?angle)
  (do-for-fact ((?p panell)) (eq ?p:id ?id)
    (modify ?p (angle ?angle))))

; Simulador d'actuadors: cada panell arriba a l'angle que se li ha ordenat al cicle ?c.
(deffunction aplica-ordres (?c)
  (do-for-all-facts ((?o ordre-actuador)) (eq ?o:cicle ?c)
    (do-for-all-facts ((?p panell)) (eq ?p:sector ?o:sector)
      (modify ?p (angle ?o:angle-objectiu))))
  TRUE)

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
  (assert (epmem-consulta (id P-prova) (sector ?s) (cicle 99)
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
(activa-reforc off)

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
(defglobal ?*chunk-dades* = FALSE)
(bind ?*chunk-dades* (chunk-de dades-insuficients 4))
(prova "C4 la regla del chunk de dades existeix"
       (and ?*chunk-dades* (member$ ?*chunk-dades* (get-defrule-list DELIBERACIO))))
(prova "C4 el vent de C3 no penalitza l'episodi de C2 (credit) -> cap empat a Sector_1"
       (and (any-factp ((?e epmem-episodi))
              (and (eq ?e:sector Sector_1) (eq ?e:cicle 2) (eq ?e:valoracio bona)))
            (not (chunk-de empat 4))))
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
(prova "C5 preferencia requerida generada pel chunk de dades"
       (any-factp ((?p preferencia))
         (and (eq ?p:sector Sector_2) (eq ?p:cicle 5) (eq ?p:tipus requerida)
              (eq ?p:font ?*chunk-dades*))))

; --- C6 -----------------------------------------------------------------------
(printout t crlf "=== C6: empat forcat a Sector_3 ===" crlf)
(aplica-ordres 5)
(nou-cicle)
(dades-ciclo 6 4.0 4.0 4.0)
; A C5 Sector_3 tenia orientar-produccio 7.0 i mantenir-posicio 4: +3 a mantenir-posicio = empat.
(assert (preferencia (op mantenir-posicio) (sector Sector_3) (cicle 6) (tipus numerica)
                     (valor 3.0) (font prova)))
(run)
(set-current-module PROVA)
(defglobal ?*chunk-empat* = FALSE)
(bind ?*chunk-empat* (chunk-de empat 6))
(prova "C6 impasse d'empat a Sector_3 i chunk apres" (neq ?*chunk-empat* FALSE))
(prova "C6 el chunk d'empat inclou els objectius consultats"
       (neq (str-index "(objectiu " (codi-de ?*chunk-empat*)) FALSE))
(prova "C6 Sector_3 selecciona orientar-produccio (energia preval)"
       (seleccionat Sector_3 6 orientar-produccio))
(prova "C6 el motiu explica l'empat" (parla-d-empat Sector_3 6))

; --- C7 -----------------------------------------------------------------------
(printout t crlf "=== C7: sense empat a Sector_3 (el chunk dispara igualment) ===" crlf)
(aplica-ordres 6)
(nou-cicle)
(dades-ciclo 7 4.0 4.0 4.0)
(run)
(set-current-module PROVA)
(prova "C7 el chunk d'empat ha generat la preferencia millor-que"
       (any-factp ((?p preferencia))
         (and (eq ?p:sector Sector_3) (eq ?p:cicle 7) (eq ?p:tipus millor-que)
              (eq ?p:font ?*chunk-empat*))))
(prova "C7 Sector_3 selecciona orientar-produccio" (seleccionat Sector_3 7 orientar-produccio))
(prova "C7 sense empat real, el motiu no parla d'empat" (not (parla-d-empat Sector_3 7)))

; --- C8 / C9: branca historial ------------------------------------------------
(printout t crlf "=== C8: vent critic a Sector_1 ===" crlf)
(aplica-ordres 7)
(nou-cicle)
(dades-ciclo 8 18.0 4.0 4.0)
(run)
(set-current-module PROVA)
(prova "C8 Sector_1 selecciona posicio-seguretat" (seleccionat Sector_1 8 posicio-seguretat))

(printout t crlf "=== C9: Sector_1 sense lectura de vent (historial) ===" crlf)
(aplica-ordres 8)
(nou-cicle)
(dades-ciclo 9 absent 4.0 4.0)
(run)
(set-current-module PROVA)
(defglobal ?*chunk-historial* = FALSE)
(bind ?*chunk-historial* (chunk-de dades-insuficients 9))
(prova "C9 el chunk de dades (hold) no dispara: el cicle anterior hi havia vent"
       (not (any-factp ((?p preferencia))
              (and (eq ?p:sector Sector_1) (eq ?p:cicle 9) (eq ?p:font ?*chunk-dades*)))))
(prova "C9 impasse resolt per historial: nou chunk" (neq ?*chunk-historial* FALSE))
(prova "C9 Sector_1 selecciona posicio-seguretat" (seleccionat Sector_1 9 posicio-seguretat))

(printout t crlf "=== C10: vent critic a Sector_1 ===" crlf)
(aplica-ordres 9)
(nou-cicle)
(dades-ciclo 10 18.0 4.0 4.0)
(run)
(set-current-module PROVA)

(printout t crlf "=== C11: Sector_1 sense lectura de vent (ha d'actuar el chunk) ===" crlf)
(aplica-ordres 10)
(nou-cicle)
(dades-ciclo 11 absent 4.0 4.0)
(run)
(set-current-module PROVA)
(prova "C11 Sector_1 sense impasse" (not (any-factp ((?g subobjectiu)) (eq ?g:id G-Sector_1-11))))
(prova "C11 el chunk proposa posicio-seguretat amb el mateix id que la proposta normal"
       (any-factp ((?o operador))
         (and (eq ?o:sector Sector_1) (eq ?o:cicle 11) (eq ?o:id Sector_1-seguretat-11))))
(prova "C11 Sector_1 selecciona posicio-seguretat" (seleccionat Sector_1 11 posicio-seguretat))

; --- persistencia de chunks -------------------------------------------------------
(printout t crlf "=== Persistencia dels chunks ===" crlf)
(defglobal ?*n-chunks* = 0)
(bind ?*n-chunks* (length$ (find-all-facts ((?f fragment-apres)) TRUE)))
(do-for-all-facts ((?f fragment-apres)) TRUE
  (undefrule (sym-cat DELIBERACIO:: ?f:nom))
  (retract ?f))
(prova "chunks eliminats de memoria"
       (not (member$ ?*chunk-dades* (get-defrule-list DELIBERACIO))))
(prova "tots els chunks reconstruits des del fitxer"
       (= (activa-persistencia "chunks_prova.dat") ?*n-chunks*))
(prova "el chunk de dades torna a ser present amb el mateix nom"
       (member$ ?*chunk-dades* (get-defrule-list DELIBERACIO)))

; --- persistencia de memoria episodica --------------------------------------------
(printout t crlf "=== Persistencia de la memoria episodica ===" crlf)
(prova-persistencia-epmem)

; --- consultes a la memoria episodica ---------------------------------------------
(printout t crlf "=== Consultes a la memoria episodica ===" crlf)
(assert (epmem-consulta (id Q-prova-1) (sector Sector_1) (cicle 99)
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

;; =============================================================================
; REFORÇ
; =============================================================================

; R2, R3 i R4 son la mateixa situacio a Sector_3: amb les puntuacions de R2 (sense
; injeccio) s'iguala mantenir-posicio a orientar-produccio.
(deffunction empata-sector-3 (?c)
  (bind ?d (- (puntuacio Sector_3 orientar-produccio 2)
              (puntuacio Sector_3 mantenir-posicio 2)))
  (assert (preferencia (op mantenir-posicio) (sector Sector_3) (cicle ?c) (tipus numerica)
                       (valor ?d) (font prova))))

(deffunction q-de (?tret ?op)
  (bind ?r FALSE)
  (do-for-fact ((?v rl-valor)) (and (eq ?v:tret ?tret) (eq ?v:op ?op)) (bind ?r ?v))
  ?r)

(printout t crlf "=== REFORC: sessio nova amb el reforç activat ===" crlf)
; els chunks de la sessio anterior no han de condicionar aquesta
(progn$ (?r (get-defrule-list DELIBERACIO))
  (if (eq (str-index "chunk-" (str-cat ?r)) 1) then (undefrule (sym-cat DELIBERACIO:: ?r))))
(set-reset-globals FALSE)   ; conserva els comptadors de proves
(reset)
(set-current-module PROVA)
(activa-persistencia "")    ; sense fitxer de chunks en aquesta sessio
(activa-reforc on)
(epmem-aprenentatge off)
(run)
(set-current-module PROVA)
(prova "R1 traca del reforç per als 3 sectors"
       (= 3 (length$ (find-all-facts ((?t rl-traca)) (eq ?t:cicle 1)))))

(aplica-ordres 1)
(nou-cicle)
(dades-ciclo 2 4.0 4.0 4.0)
(run)
(set-current-module PROVA)
(prova "R2 recompenses del cicle 1 aplicades"
       (= 3 (length$ (find-all-facts ((?t rl-traca)) (and (eq ?t:cicle 1) (eq ?t:estat fet))))))
(prova "R2 la rajola 'tot' d'orientar-produccio ha pujat (recompensa +1)"
       (and (q-de tot orientar-produccio) (> (fact-slot-value (q-de tot orientar-produccio) q) 0)))

(aplica-ordres 2)
(nou-cicle)
(dades-ciclo 3 4.0 4.0 4.0)
(empata-sector-3 3)
(run)
(set-current-module PROVA)
(prova "R3 l'empat de Sector_3 el desfa el reforç, sense impasse"
       (and (not (any-factp ((?g subobjectiu)) (eq ?g:id G-Sector_3-3)))
            (any-factp ((?p preferencia))
              (and (eq ?p:sector Sector_3) (eq ?p:cicle 3) (eq ?p:tipus millor-que) (eq ?p:font RL)))))
(prova "R3 el motiu ho explica" (neq (str-index "desfet per RL" (motiu-de Sector_3 3)) FALSE))

(aplica-ordres 3)
(nou-cicle)
(dades-ciclo 4 4.0 4.0 4.0)
(empata-sector-3 4)
(do-for-all-facts ((?k rl-config)) TRUE (modify ?k (epsilon 1000)))
(run)
(set-current-module PROVA)
(do-for-all-facts ((?k rl-config)) TRUE (modify ?k (epsilon 0.05)))
(defglobal ?*chunk-rl* = FALSE)
(bind ?*chunk-rl* (chunk-de empat 4))
(prova "R4 sense prou diferencia de Q hi ha impasse i s'apren un chunk" (neq ?*chunk-rl* FALSE))
(prova "R4 el chunk apren una preferencia rl, no un millor-que fix"
       (and (neq (str-index "(tipus rl)" (codi-de ?*chunk-rl*)) FALSE)
            (eq (str-index "(tipus millor-que)" (codi-de ?*chunk-rl*)) FALSE)))
(prova "R4 la rajola del chunk comença amb el valor prior"
       (= (rl-q ?*chunk-rl* orientar-produccio) 0.5))

; el simulador falla: el panell de Sector_3 no arriba a l'angle ordenat
(aplica-ordres 4)
(mou-panell Panell_3_1 5.0)
(mou-panell Panell_3_2 5.0)
(nou-cicle)
(dades-ciclo 5 4.0 4.0 4.0)
(run)
(set-current-module PROVA)
(prova "R5 recompensa -1: el valor del chunk baixa per sota del prior"
       (and ?*chunk-rl* (< (rl-q ?*chunk-rl* orientar-produccio) 0.5)))

(printout t crlf "=== RESUM: " ?*ok* " correctes, " ?*ko* " incorrectes ===" crlf)
