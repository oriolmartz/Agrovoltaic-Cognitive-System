(defmodule ACCIO
  (import DOMINI ?ALL)
  (import DELIBERACIO deffunction ?ALL)
  (export ?ALL))

;  ACCIO ---------------------------------------------------------------------
; Fases aplicacio, explicacio i monitoratge.
; CLIPS nomes genera l'ordre

; --- APLICACIO ---------------------------------------------------------------

(defrule aplica-operador
  (declare (auto-focus TRUE))
  (fase (nom aplicacio))
  (cicle (numero ?c))
  (operador-seleccionat (sector ?s) (cicle ?c) (nom ?op) (motiu ?m))
  ?o <- (operador (sector ?s) (cicle ?c) (nom ?op) (estat seleccionat) (angle-objectiu ?a))
  (not (ordre-actuador (sector ?s) (cicle ?c)))
  =>
  ; riscos presents, per guardar-los a l'historial
  (bind ?riscos (create$))
  (do-for-all-facts ((?r risc)) (and (eq ?r:sector ?s) (eq ?r:cicle ?c))
    (bind ?riscos (create$ ?riscos (sym-cat ?r:tipus - ?r:nivell))))
  (printout t "[APLICACIO] " ?s ": ORDRE " ?op " -> " ?a " graus." crlf)
  (modify ?o (estat aplicat))
  (assert (ordre-actuador (sector ?s) (cicle ?c) (accio ?op) (angle-objectiu ?a) (motiu ?m)))
  (assert (episodi (cicle ?c) (sector ?s) (operador ?op) (angle ?a) (riscos ?riscos)))
  (assert (traca (pas ?c) (fase aplicacio)
                 (missatge (str-cat ?s ": ordre " ?op " a " ?a " graus")))))

; v1_9: ordre a la valvula de reg.
(defrule aplica-reg
  (declare (auto-focus TRUE))
  (fase (nom aplicacio))
  (cicle (numero ?c))
  (reg-seleccionat (sector ?s) (cicle ?c) (nom ?op) (dosi ?d) (motiu ?m))
  ?o <- (operador-reg (sector ?s) (cicle ?c) (nom ?op) (estat seleccionat))
  (not (ordre-reg (sector ?s) (cicle ?c)))
  =>
  (if (neq ?op no-regar) then
    (printout t "[APLICACIO] " ?s ": ORDRE DE REG " ?op " -> +" ?d "% de l'aigua disponible." crlf))
  (modify ?o (estat aplicat))
  (assert (ordre-reg (sector ?s) (cicle ?c) (accio ?op) (dosi ?d) (motiu ?m)))
  (assert (traca (pas ?c) (fase aplicacio)
                 (missatge (str-cat ?s ": reg " ?op " " ?d "%")))))

(defrule aplicacio-a-explicacio
  (declare (salience -10) (auto-focus TRUE))
  ?f <- (fase (nom aplicacio))
  =>
  (printout t "[APLICACIO -> EXPLICACIO]" crlf)
  (retract ?f)
  (assert (fase (nom explicacio))))


; --- EXPLICACIO --------------------------------------------------------------
; Per cada sector: evidencies (riscos), candidats amb la seva valoracio,
; descartats i criteri que ha decidit.

(defrule explica-decisio
  (declare (auto-focus TRUE))
  (fase (nom explicacio))
  (cicle (numero ?c))
  (ordre-actuador (sector ?s) (cicle ?c) (accio ?op) (angle-objectiu ?a) (motiu ?m))
  (not (explicacio (sector ?s) (cicle ?c)))
  =>
  (bind ?riscos "")
  (do-for-all-facts ((?r risc)) (and (eq ?r:sector ?s) (eq ?r:cicle ?c))
    (bind ?riscos (str-cat ?riscos " " ?r:tipus "=" ?r:nivell)))
  (if (eq ?riscos "") then (bind ?riscos " cap"))
  (bind ?candidats "")
  (bind ?descartats "")
  (do-for-all-facts ((?o operador)) (and (eq ?o:sector ?s) (eq ?o:cicle ?c))
    (if (eq ?o:estat rebutjat)
     then (bind ?descartats (str-cat ?descartats " " ?o:nom))
     else (bind ?candidats (str-cat ?candidats " " ?o:nom "(" (puntuacio ?s ?o:nom ?c) ")"))))
  (if (eq ?descartats "") then (bind ?descartats " cap"))
  (bind ?txt (str-cat ?op " a " ?a " graus. Riscos:" ?riscos ". Candidats:" ?candidats
                      ". Descartats:" ?descartats ". Criteri: " ?m "."))
  (printout t crlf "[EXPLICACIO] " ?s ", cicle " ?c crlf
              "   Accio:      " ?op " a " ?a " graus" crlf
              "   Riscos:    " ?riscos crlf
              "   Candidats: " ?candidats crlf
              "   Descartats:" ?descartats crlf
              "   Criteri:    " ?m crlf)
  (assert (explicacio (sector ?s) (cicle ?c) (missatge ?txt))))

; v1_9: explicacio del reg (nomes s'escriu quan hi havia alguna opcio de regar).
(defrule explica-reg
  (declare (auto-focus TRUE))
  (fase (nom explicacio))
  (cicle (numero ?c))
  (ordre-reg (sector ?s) (cicle ?c) (accio ?op) (dosi ?d) (motiu ?m))
  (not (explicacio-reg (sector ?s) (cicle ?c)))
  =>
  (bind ?nec "cap")
  (do-for-fact ((?n necessitat-reg)) (and (eq ?n:sector ?s) (eq ?n:cicle ?c))
    (bind ?nec (str-cat ?n:nivell " (esgotat " (arrodoneix1 (* 100 ?n:esgotament)) "%)")))
  (bind ?candidats "")
  (bind ?descartats "")
  (bind ?n 0)
  (do-for-all-facts ((?o operador-reg)) (and (eq ?o:sector ?s) (eq ?o:cicle ?c))
    (bind ?n (+ ?n 1))
    (if (eq ?o:estat rebutjat)
     then (bind ?descartats (str-cat ?descartats " " ?o:nom))
     else (bind ?candidats (str-cat ?candidats " " ?o:nom "(" (puntuacio-reg ?s ?o:nom ?c) ")"))))
  (if (eq ?descartats "") then (bind ?descartats " cap"))
  (bind ?txt (str-cat ?op " (+" ?d "%). Necessitat: " ?nec ". Candidats:" ?candidats
                      ". Descartats:" ?descartats ". Criteri: " ?m "."))
  (if (> ?n 1) then
    (printout t crlf "[EXPLICACIO REG] " ?s ", cicle " ?c crlf
                "   Accio:      " ?op " (+" ?d "% de l'aigua disponible)" crlf
                "   Necessitat: " ?nec crlf
                "   Candidats: " ?candidats crlf
                "   Descartats:" ?descartats crlf
                "   Criteri:    " ?m crlf))
  (assert (explicacio-reg (sector ?s) (cicle ?c) (missatge ?txt))))

(defrule explicacio-a-monitoratge
  (declare (salience -10) (auto-focus TRUE))
  ?f <- (fase (nom explicacio))
  =>
  (printout t crlf "[EXPLICACIO -> MONITORATGE]" crlf)
  (retract ?f)
  (assert (fase (nom monitoratge))))


; --- MONITORATGE ---------------------------------------------------------------

; Historial: A -> B -> A en tres cicles seguits es una oscil.lacio.
(defrule detecta-oscillacio
  (declare (auto-focus TRUE))
  (fase (nom monitoratge))
  (cicle (numero ?c))
  (episodi (cicle ?c) (sector ?s) (operador ?op))
  (episodi (cicle =(- ?c 1)) (sector ?s) (operador ?op2&~?op))
  (episodi (cicle =(- ?c 2)) (sector ?s) (operador ?op))
  =>
  (printout t "[MONITORATGE] " ?s ": oscil.lacio " ?op " -> " ?op2 " -> " ?op " en tres cicles." crlf)
  (assert (traca (pas ?c) (fase monitoratge)
                 (missatge (str-cat ?s ": oscil.lacio entre " ?op " i " ?op2)))))

(defrule avisa-dades-pendents
  (declare (auto-focus TRUE))
  (fase (nom monitoratge))
  (cicle (numero ?c))
  (risc (sector ?s) (cicle ?c) (tipus dades) (nivell ?n))
  =>
  (printout t "[MONITORATGE] " ?s ": cal demanar al simulador les lectures que falten (risc de dades " ?n ")." crlf)
  (assert (traca (pas ?c) (fase monitoratge)
                 (missatge (str-cat ?s ": peticio de dades al simulador")))))

(defrule avisa-fallada-actuador
  (declare (auto-focus TRUE))
  (fase (nom monitoratge))
  (cicle (numero ?c))
  (risc (sector ?s) (cicle ?c) (tipus fallada-actuador))
  =>
  (printout t "[MONITORATGE] " ?s ": l'actuador no ha respost. Cal revisio de manteniment." crlf)
  (assert (traca (pas ?c) (fase monitoratge)
                 (missatge (str-cat ?s ": actuador sense resposta, avis de manteniment")))))

; Tanca el cicle: els objectius es tornen a calcular el cicle seguent.
; Nota de persistencia: els fets temporals del cicle es conserven de moment per
; traçabilitat i perquè el simulador consumeix ordre-actuador després de (run).
; Totes les regles temporals filtren pel slot cicle. Una neteja explicita es pot
; afegir quan la capa Python/clipspy confirmi que ja ha consumit els resultats.
(defrule tanca-cicle
  (declare (salience -10) (auto-focus TRUE))
  ?f <- (fase (nom monitoratge))
  ?k <- (cicle (numero ?c))
  =>
  (do-for-all-facts ((?o objectiu)) (eq ?o:estat actiu)
    (modify ?o (estat inactiu)))
  (printout t "[FI DEL CICLE " ?c "] Ordres enviades. Esperant les dades del cicle " (+ ?c 1) "." crlf crlf)
  (retract ?f)
  (modify ?k (numero (+ ?c 1)))
  (assert (fase (nom espera))))
