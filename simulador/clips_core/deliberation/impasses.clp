(defmodule IMPAS
  (import DOMINI ?ALL)
  (import DELIBERACIO deffunction ?ALL)
  (import APRENENTATGE deffunction ?ALL)
  (import REFORC deffunction ?ALL)
  (export ?ALL))

;  IMPAS ---------------------------------------------------------------------

; --- resolucio dels impasses -------------------------------------------------

; Empat: criteri secundari = ordre de prioritats entre objectius.
; Si cap dels dos preval, es tria el mes reversible (el que mou menys el panel).
; El subobjectiu declara el que ha consultat i el chunk es genera a partir d'aixo.
(defrule resol-empat
  (declare (auto-focus TRUE))
  (fase (nom impas))
  ?i <- (impas (tipus empat) (sector ?s) (cicle ?c) (operadors ?a ?b))
  ?g <- (subobjectiu (id ?gid) (sector ?s) (tipus resoldre-empat) (estat actiu))
  ?fa <- (operador (sector ?s) (cicle ?c) (nom ?a) (estat proposat))
  ?fb <- (operador (sector ?s) (cicle ?c) (nom ?b) (estat proposat))
  =>
  (bind ?oa (id-objectiu (objectiu-operador ?a)))
  (bind ?ob (id-objectiu (objectiu-operador ?b)))
  (bind ?per-prioritat TRUE)
  (if (preval ?oa ?ob) then
     (bind ?guanya ?a) (bind ?perd ?b) (bind ?og ?oa) (bind ?op ?ob)
     (bind ?criteri (str-cat ?oa " te prioritat sobre " ?ob))
   else (if (preval ?ob ?oa) then
     (bind ?guanya ?b) (bind ?perd ?a) (bind ?og ?ob) (bind ?op ?oa)
     (bind ?criteri (str-cat ?ob " te prioritat sobre " ?oa))
   else
     (bind ?per-prioritat FALSE)
     (if (<= (moviment-operador ?s ?a ?c) (moviment-operador ?s ?b ?c))
      then (bind ?guanya ?a) (bind ?perd ?b)
      else (bind ?guanya ?b) (bind ?perd ?a))
     (bind ?criteri "mateixa prioritat; es tria el que mou menys el panell")))
  (printout t "[IMPAS] " ?s ": subobjectiu resoldre-empat. " ?criteri " -> " ?guanya
              " millor que " ?perd "." crlf)
  ; --- registre de dependencies (el que ha mirat el subobjectiu) ---
  (inicia-aprenentatge ?gid ?s ?c)
  (bind ?fg (if (eq ?guanya ?a) then ?fa else ?fb))
  (bind ?fp (if (eq ?guanya ?a) then ?fb else ?fa))
  (if ?per-prioritat then
     (dep-fet guanya ?fg (create$ sector cicle nom estat) (create$))
     (dep-fet perd ?fp (create$ sector cicle nom estat) (create$))
     ; id-objectiu ha llegit aquests fets per passar d'operador a objectiu
     (do-for-fact ((?o objectiu)) (eq ?o:id ?og) (dep-fet og ?o (create$ id tipus) (create$)))
     (do-for-fact ((?o objectiu)) (eq ?o:id ?op) (dep-fet op ?o (create$ id tipus) (create$)))
     (bind ?k 0)
     (progn$ (?pf (cadena-prioritat ?og ?op))
       (bind ?k (+ ?k 1))
       (dep-fet (sym-cat prio ?k) ?pf (create$ major menor) (create$)))
   else
     (dep-fet guanya ?fg (create$ sector cicle nom estat angle-objectiu) (create$))
     (dep-fet perd ?fp (create$ sector cicle nom estat angle-objectiu) (create$))
     (do-for-fact ((?p panell)) (eq ?p:sector ?s)
       (dep-fet pn ?p (create$ sector angle) (create$)))
     (dep-neg "(not (panell (sector ?s) (angle ?pn-altre&:(neq ?pn-altre ?pn-angle))))")
     (dep-test (str-cat "(" (if (eq ?guanya ?a) then "<=" else "<") " (abs (- ?guanya-angle-objectiu ?pn-angle))"
                        " (abs (- ?perd-angle-objectiu ?pn-angle)))")))
  ; --- resultat ---
  ; La decisio d'ara sempre es un millor-que. Sense reforç, aquest es el resultat que
  ; apren el chunk. Amb reforç, el chunk apren una preferencia rl (una rajola amb
  ; valor inicial 'prior') que l'experiencia podra reforçar o afeblir, com els chunks
  ; que son regles RL a Soar.
  (bind ?pf (assert (preferencia (op ?guanya) (sector ?s) (cicle ?c) (tipus millor-que)
                                 (op2 ?perd) (font IMPAS-prioritat))))
  (if (rl-actiu)
   then (bind ?prl (assert (preferencia (op ?guanya) (sector ?s) (cicle ?c) (tipus rl)
                                        (op2 ?perd) (font IMPAS-prioritat))))
        (dep-resultat ?prl)
   else (dep-resultat ?pf))
  (assert (traca (pas ?c) (fase impas)
                 (missatge (str-cat ?s ": empat resolt, " ?criteri ", " ?guanya " millor que " ?perd))))
  (bind ?nom (crea-chunk empat (str-cat "situacio coneguda, " ?guanya " millor que " ?perd
                                        (if (rl-actiu) then " (valor ajustable pel reforç)" else ""))))
  ; la rajola d'aquest cicle ja es la del chunk (o no n'hi ha si no s'ha apres)
  (if (rl-actiu) then
     (if ?nom then (modify ?prl (font ?nom)) else (retract ?prl)))
  (modify ?g (estat resolt))
  (retract ?i))

; Dades insuficients. La deliberacio decideix segons el que se sap:
;   1. la previsio de vent supera el llindar d'avis -> posicio-seguretat
;   2. l'historial diu que el cicle anterior hi havia risc mecanic -> posicio-seguretat
;   3. res no indica vent fort -> sollicitar-dades i mantenir l'angle (hold)
; Si cal la posicio de seguretat i no s'havia proposat, la deliberacio la proposa.
(defrule resol-dades-insuficients
  (declare (auto-focus TRUE))
  (fase (nom impas))
  ?i <- (impas (tipus dades-insuficients) (sector ?s) (cicle ?c))
  ?g <- (subobjectiu (id ?gid) (sector ?s) (tipus resoldre-dades) (estat actiu))
  ?rd <- (risc (sector ?s) (cicle ?c) (tipus dades) (nivell critic))
  ?pn <- (panell (sector ?s) (vent-avis ?avis) (angle-seguretat ?as))
  =>
  (bind ?pv (previsio-vent-sector ?s ?c))
  (bind ?fpr (find-fact ((?p prediccio)) (and (eq ?p:sector ?s) (eq ?p:cicle ?c))))
  (bind ?fep (find-fact ((?e episodi))
      (and (eq ?e:sector ?s) (eq ?e:cicle (- ?c 1))
           (or (member$ mecanic-alt ?e:riscos) (member$ mecanic-critic ?e:riscos)))))
  (if (and (numberp ?pv) (>= ?pv ?avis)) then
     (bind ?mode previsio)
     (bind ?motiu (str-cat "la previsio de vent es de " ?pv " m/s (avis a " ?avis ")"))
   else (if (> (length$ ?fep) 0) then
     (bind ?mode historial)
     (bind ?motiu "el cicle anterior ja hi havia risc mecanic")
   else
     (bind ?mode hold)
     (bind ?motiu "ni la previsio ni l'historial indiquen vent fort")))
  ; --- registre de dependencies comunes ---
  (inicia-aprenentatge ?gid ?s ?c)
  (dep-fet rd ?rd (create$ sector cicle tipus nivell) (create$))
  (bind ?neg-previsio (str-cat "(not (and (prediccio (sector ?s) (cicle ?c) (vent ?npv&:(numberp ?npv)))"
                               " (panell (sector ?s) (vent-avis ?nav&:(>= ?npv ?nav)))))"))
  (bind ?neg-historial "(not (episodi (cicle =(- ?c 1)) (sector ?s) (riscos $? mecanic-alt|mecanic-critic $?)))")
  (if (eq ?mode hold) then
     (printout t "[IMPAS] " ?s ": subobjectiu resoldre-dades. Falta la lectura de vent i " ?motiu
                 ". Es demanen dades i es mante la posicio." crlf)
     (dep-fet sd (nth$ 1 (find-fact ((?o operador))
                  (and (eq ?o:sector ?s) (eq ?o:cicle ?c) (eq ?o:nom sollicitar-dades))))
              (create$ sector cicle nom estat) (create$))
     (dep-neg ?neg-previsio)
     (dep-neg ?neg-historial)
     (dep-neg "(not (preferencia (sector ?s) (cicle ?c) (tipus requerida)))")
     (bind ?pf (assert (preferencia (op sollicitar-dades) (sector ?s) (cicle ?c) (tipus requerida)
                                    (font IMPAS-dades))))
     (dep-resultat ?pf)
     (assert (traca (pas ?c) (fase impas)
                    (missatge (str-cat ?s ": dades insuficients, " ?motiu ", sollicitar-dades i hold"))))
     (crea-chunk dades-insuficients
                 "sense lectura de vent i res no indica vent fort, sollicitar-dades requerida i panell en hold")
   else
     (printout t "[IMPAS] " ?s ": subobjectiu resoldre-dades. Falta la lectura de vent, pero " ?motiu
                 ". Opcio segura: posicio de seguretat." crlf)
     (if (not (any-factp ((?o operador)) (and (eq ?o:sector ?s) (eq ?o:cicle ?c) (eq ?o:nom posicio-seguretat))))
      then
       (printout t "[IMPAS] " ?s ": la deliberacio proposa posicio-seguretat (" ?as " graus)." crlf)
       (assert (operador (id (sym-cat ?s -seguretat- ?c)) (cicle ?c) (sector ?s)
                         (nom posicio-seguretat) (angle-objectiu ?as) (estat proposat)))
       (assert (preferencia (op posicio-seguretat) (sector ?s) (cicle ?c) (tipus acceptable)
                            (font IMPAS-dades))))
     (dep-fet pn ?pn (create$ sector vent-avis angle-seguretat) (create$))
     (if (eq ?mode previsio) then
        (dep-fet pr (nth$ 1 ?fpr) (create$ sector cicle vent) (create$))
        (dep-test "(>= ?pr-vent ?pn-vent-avis)")
      else
        (dep-fet ep (nth$ 1 ?fep) (create$ sector cicle) (create$ riscos "$? mecanic-alt|mecanic-critic $?"))
        (dep-neg ?neg-previsio))
     (dep-neg "(not (preferencia (sector ?s) (cicle ?c) (tipus requerida)))")
     (dep-resultat (nth$ 1 (find-fact ((?o operador))
                    (and (eq ?o:sector ?s) (eq ?o:cicle ?c) (eq ?o:nom posicio-seguretat)))))
     (bind ?pf (assert (preferencia (op posicio-seguretat) (sector ?s) (cicle ?c) (tipus requerida)
                                    (font IMPAS-dades))))
     (dep-resultat ?pf)
     (assert (traca (pas ?c) (fase impas)
                    (missatge (str-cat ?s ": dades insuficients, " ?motiu ", posicio-seguretat requerida"))))
     (crea-chunk dades-insuficients
                 (if (eq ?mode previsio)
                  then "sense lectura de vent i previsio de vent fort, posicio-seguretat requerida"
                  else "sense lectura de vent i vent fort el cicle anterior, posicio-seguretat requerida")))
  (modify ?g (estat resolt))
  (retract ?i))


; Sense candidat: es recupera mantenir-posicio i s'avisa que cal supervisio.
(defrule resol-sense-candidat
  (declare (auto-focus TRUE))
  (fase (nom impas))
  ?i <- (impas (tipus sense-canvi) (sector ?s) (cicle ?c))
  ?g <- (subobjectiu (sector ?s) (tipus resoldre-sense-candidat) (estat actiu))
  ?o <- (operador (sector ?s) (cicle ?c) (nom mantenir-posicio))
  =>
  (printout t "[IMPAS] " ?s ": cap opcio valida. No es mou el panell i cal supervisio humana." crlf)
  (modify ?o (estat proposat))
  (assert (preferencia (op mantenir-posicio) (sector ?s) (cicle ?c) (tipus requerida)
                       (font IMPAS-sense-candidat)))
  (assert (traca (pas ?c) (fase impas)
                 (missatge (str-cat ?s ": sense candidats, es mante la posicio i es demana supervisio"))))
  (modify ?g (estat resolt))
  (retract ?i))

(defrule impas-a-seleccio
  (declare (salience -10) (auto-focus TRUE))
  ?f <- (fase (nom impas))
  (not (impas))
  =>
  (printout t "[IMPAS -> SELECCIO]" crlf)
  (retract ?f)
  (assert (fase (nom seleccio))))


