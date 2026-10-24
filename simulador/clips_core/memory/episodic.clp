(defmodule MEMORIA
  (import DOMINI ?ALL)
  (export deffunction ?ALL))

;  MEMORIA EPISODICA ---------------------------------------------------------
; Memoria a llarg termini d'esdeveniments passats. Complementa el chunking:
;   - el chunking converteix la resolucio d'un impasse en una REGLA (memoria procedimental);
;   - la memoria episodica guarda QUE VA PASSAR (situacio + operador + resultat)
;     i permet recordar quin operador va funcionar bé en una situacio semblant.
;
; Cicle de vida (mapa amb Soar):
;   1. monitoratge : epmem-emmagatzema desa l'episodi del cicle        (trigger dc)
;   2. proposta    : epmem-valora-resultat completa l'episodi del cicle anterior
;                    amb el resultat i la valoracio (bona/neutra/dolenta)
;   3. avaluacio   : DELIBERACIO crea epmem-consulta per a cada operador proposat;
;                    epmem-processa-query la resol (cue-based retrieval) i
;                    avalua-memoria converteix el record en una preferencia numerica
;   4. monitoratge : epmem-persisteix desa el magatzem al fitxer (si n'hi ha)
;
; Com es valora que un operador "ha funcionat bé" (heuristica ajustable a valora-resultat):
;   dolenta : l'actuador no ha arribat a l'angle, o el risc ambiental ha augmentat
;   (assignacio de credit: nomes compten els riscos que l'ombreig dels panells pot
;    modificar; el vent no depen de l'operador i no penalitza qui era al cicle anterior)
;   bona    : el panell ha arribat i el risc ha baixat (o s'ha mantingut sense perdre cobertura)
;   neutra  : el panell ha arribat, el risc s'ha mantingut i la cobertura ha baixat

; --- utilitats --------------------------------------------------------------

(deffunction epmem-nivell (?n)
  (switch ?n
    (case baix then 0)
    (case mitja then 1)
    (case alt then 2)
    (case critic then 3)
    (default 0)))

; Suma de nivells dels riscos que l'accio pot influir. Dades i fallada no en son una
; conseqüencia, i el risc mecanic ve del vent, que cap operador pot canviar.
(deffunction epmem-risc-total (?s ?c)
  (bind ?t 0)
  (do-for-all-facts ((?r risc))
      (and (eq ?r:sector ?s) (eq ?r:cicle ?c)
           (member$ ?r:tipus (create$ temperatura estres-hidric exces-radiacio)))
    (bind ?t (+ ?t (epmem-nivell ?r:nivell))))
  ?t)

; Produccio / demanda del sector; -1.0 si no hi ha dades d'energia.
(deffunction epmem-cobertura (?s ?c)
  (bind ?r -1.0)
  (do-for-fact ((?e energia)) (and (eq ?e:sector ?s) (eq ?e:cicle ?c))
    (bind ?r (if (> ?e:demanda 0) then (/ ?e:produccio-actual ?e:demanda) else 1.0)))
  ?r)

(deffunction epmem-banda-cobertura (?cob)
  (if (< ?cob 0) then (return desconeguda))
  (if (< ?cob 1.0) then (return deficit))
  (return suficient))

(deffunction epmem-cultiu (?s)
  (bind ?r desconegut)
  (do-for-fact ((?sc sector) (?cu cultiu)) (and (eq ?sc:id ?s) (eq ?cu:id ?sc:cultiu))
    (bind ?r ?cu:tipus))
  ?r)

; Subobjectiu (impasse resolt) d'aquell sector i cicle, o cap.
(deffunction epmem-impas (?s ?c)
  (bind ?r cap)
  (do-for-fact ((?g subobjectiu)) (eq ?g:id (sym-cat G- ?s - ?c))
    (bind ?r ?g:tipus))
  ?r)

; --- trets (descripcio indexable d'un episodi) ---------------------------------

(deffunction epmem-exclos (?clau)
  (bind ?r FALSE)
  (do-for-fact ((?c epmem-config)) (member$ ?clau ?c:exclusions)
    (bind ?r TRUE))
  ?r)

; Un tret clau=valor (multifield buit si la clau esta exclosa).
(deffunction epmem-tret (?clau ?valor)
  (if (epmem-exclos ?clau) then (return (create$)))
  (create$ (sym-cat ?clau "=" ?valor)))

; Trets de la SITUACIO d'un sector en un cicle. Es el que s'usa com a cue.
(deffunction epmem-cue-situacio (?s ?c)
  (bind ?cue (epmem-tret sector ?s))
  (bind ?cue (create$ ?cue (epmem-tret cultiu (epmem-cultiu ?s))))
  (do-for-all-facts ((?r risc)) (and (eq ?r:sector ?s) (eq ?r:cicle ?c))
    (bind ?cue (create$ ?cue (epmem-tret risc (sym-cat ?r:tipus - ?r:nivell)))))
  (create$ ?cue (epmem-tret cobertura (epmem-banda-cobertura (epmem-cobertura ?s ?c)))))

; Trets complets d'un episodi: situacio + operador + impasse + resultat + valoracio.
(deffunction epmem-trets (?s ?c ?op ?imp ?res ?val)
  (bind ?t (epmem-cue-situacio ?s ?c))
  (bind ?t (create$ ?t (epmem-tret operador ?op)))
  (if (neq ?imp cap) then (bind ?t (create$ ?t (epmem-tret impas ?imp))))
  (create$ ?t (epmem-tret resultat ?res) (epmem-tret valoracio ?val)))

; Substitueix els trets resultat= i valoracio= d'un episodi ja emmagatzemat.
(deffunction epmem-actualitza-trets (?trets ?res ?val)
  (bind ?nou (create$))
  (progn$ (?t ?trets)
    (bind ?txt (str-cat ?t))
    (if (and (neq (str-index "resultat=" ?txt) 1) (neq (str-index "valoracio=" ?txt) 1))
     then (bind ?nou (create$ ?nou ?t))))
  (create$ ?nou (epmem-tret resultat ?res) (epmem-tret valoracio ?val)))

; --- valoracio ------------------------------------------------------------------

(deffunction epmem-valora (?res ?r0 ?r1 ?cob0 ?cob1)
  (if (eq ?res fallada) then (return dolenta))
  (if (> ?r1 ?r0) then (return dolenta))
  (if (< ?r1 ?r0) then (return bona))
  (if (and (>= ?cob0 0) (>= ?cob1 0)) then
     (if (>= ?cob1 (- ?cob0 0.01)) then (return bona) else (return neutra)))
  (return neutra))

; --- recuperacio per indici (cue-based retrieval) -----------------------------------

(deffunction epmem-cardinalitat (?cue ?trets)
  (bind ?k 0)
  (progn$ (?t ?cue)
    (if (member$ ?t ?trets) then (bind ?k (+ ?k 1))))
  ?k)

(deffunction epmem-conte-tots (?llista ?trets)
  (progn$ (?t ?llista)
    (if (not (member$ ?t ?trets)) then (return FALSE)))
  TRUE)

(deffunction epmem-conte-algun (?llista ?trets)
  (progn$ (?t ?llista)
    (if (member$ ?t ?trets) then (return TRUE)))
  FALSE)

; Retorna (id cardinalitat) del millor episodi: maxima cardinalitat de trets del cue
; satisfets i, a igualtat, el mes recent (id mes gran). (0 0) si no n'hi ha cap.
(deffunction epmem-cerca (?cue ?requereix ?exclou ?prohibits)
  (bind ?millor 0)
  (bind ?card-millor -1)
  (bind ?min (if (> (length$ ?cue) 0) then 1 else 0))
  (do-for-all-facts ((?e epmem-episodi))
      (and (not (member$ ?e:id ?prohibits))
           (epmem-conte-tots ?requereix ?e:trets)
           (not (epmem-conte-algun ?exclou ?e:trets)))
    (bind ?k (epmem-cardinalitat ?cue ?e:trets))
    (if (and (>= ?k ?min)
             (or (> ?k ?card-millor)
                 (and (= ?k ?card-millor) (> ?e:id ?millor))))
     then (bind ?millor ?e:id)
          (bind ?card-millor ?k)))
  (if (= ?millor 0) then (return (create$ 0 0)))
  (create$ ?millor ?card-millor))

; Progressio temporal: id de l'episodi anterior (?dir < 0) o posterior (?dir > 0)
; del mateix sector que ?ref; 0 si no n'hi ha.
(deffunction epmem-veinat (?ref ?dir)
  (bind ?sec nil)
  (do-for-fact ((?e epmem-episodi)) (= ?e:id ?ref)
    (bind ?sec ?e:sector))
  (bind ?r 0)
  (do-for-all-facts ((?e epmem-episodi)) (eq ?e:sector ?sec)
    (if (> ?dir 0)
     then (if (and (> ?e:id ?ref) (or (= ?r 0) (< ?e:id ?r))) then (bind ?r ?e:id))
     else (if (and (< ?e:id ?ref) (> ?e:id ?r)) then (bind ?r ?e:id))))
  ?r)

; --- interficie per a l'usuari (equivalent a epmem --set / --print) --------------------

(deffunction epmem-aprenentatge (?valor)
  (progn$ (?c (find-all-facts ((?x epmem-config)) TRUE))
    (modify ?c (aprenentatge ?valor)))
  ?valor)

; Afegeix la clau a les exclusions o, si ja hi es, la treu (com 'epmem --set exclusions').
(deffunction epmem-alterna-exclusio (?clau)
  (progn$ (?c (find-all-facts ((?x epmem-config)) TRUE))
    (bind ?ex (fact-slot-value ?c exclusions))
    (bind ?p (member$ ?clau ?ex))
    (if ?p
     then (modify ?c (exclusions (delete$ ?ex ?p ?p)))
     else (modify ?c (exclusions (create$ ?ex ?clau)))))
  ?clau)

(deffunction epmem-imprimeix (?id)
  (if (not (any-factp ((?e epmem-episodi)) (= ?e:id ?id))) then
     (printout t "[EPMEM] No existeix l'episodi " ?id "." crlf)
     (return FALSE))
  (do-for-fact ((?e epmem-episodi)) (= ?e:id ?id)
    (printout t "[EPMEM] Episodi #" ?e:id " (cicle " ?e:cicle ", " ?e:sector ", " ?e:cultiu ")" crlf
                "   operador:  " ?e:operador " -> " ?e:angle " graus" crlf
                "   resultat:  " ?e:resultat ", valoracio: " ?e:valoracio crlf
                "   risc total: " ?e:risc-total ", cobertura: " ?e:cobertura ", impasse: " ?e:impas crlf
                "   criteri:   " ?e:motiu crlf
                "   trets:     " ?e:trets crlf))
  TRUE)

; Que ha funcionat i que no, per operador.
(deffunction epmem-informe ()
  (printout t crlf "[EPMEM] Experiencia acumulada: "
              (length$ (find-all-facts ((?e epmem-episodi)) TRUE)) " episodis." crlf)
  (progn$ (?op (create$ orientar-produccio orientar-ombra posicio-seguretat
                        mantenir-posicio sollicitar-dades))
    (bind ?b (length$ (find-all-facts ((?e epmem-episodi))
               (and (eq ?e:operador ?op) (eq ?e:valoracio bona)))))
    (bind ?n (length$ (find-all-facts ((?e epmem-episodi))
               (and (eq ?e:operador ?op) (eq ?e:valoracio neutra)))))
    (bind ?d (length$ (find-all-facts ((?e epmem-episodi))
               (and (eq ?e:operador ?op) (eq ?e:valoracio dolenta)))))
    (if (> (+ ?b ?n ?d) 0) then
      (printout t "   " ?op ": " ?b " bona, " ?n " neutra, " ?d " dolenta" crlf)))
  TRUE)

; --- persistencia ---------------------------------------------------------------------

(deffunction desa-epmem (?fitxer)
  (bind ?m (set-current-module DOMINI))
  (save-facts ?fitxer local epmem-episodi)
  (set-current-module ?m)
  TRUE)

; Carrega els episodis d'un fitxer, elimina ids duplicats i fa que els nous episodis
; continuïn la numeracio. Cridar-la DESPRES de (reset).
(deffunction carrega-epmem (?fitxer)
  (if (not (open ?fitxer epm-r "r")) then (return 0))
  (close epm-r)
  (bind ?m (set-current-module DOMINI))
  (load-facts ?fitxer)
  (set-current-module ?m)
  (bind ?max 0)
  (bind ?n 0)
  (progn$ (?fr (find-all-facts ((?x epmem-episodi)) TRUE))
    (if (fact-existp ?fr) then
      (bind ?id (fact-slot-value ?fr id))
      (if (any-factp ((?o epmem-episodi)) (and (< (fact-index ?o) (fact-index ?fr)) (= ?o:id ?id)))
       then (retract ?fr)
       else (bind ?n (+ ?n 1))
            (if (> ?id ?max) then (bind ?max ?id)))))
  (progn$ (?st (find-all-facts ((?x epmem-estat)) TRUE))
    (modify ?st (seguent-id (+ ?max 1)) (sessio-inici (+ ?max 1))))
  (printout t "[EPMEM] Carregats " ?n " episodis de " ?fitxer "." crlf)
  ?n)

(deffunction activa-epmem (?fitxer)
  (progn$ (?c (find-all-facts ((?x epmem-config)) TRUE))
    (modify ?c (fitxer ?fitxer)))
  (carrega-epmem ?fitxer))

; --- regles ----------------------------------------------------------------------------

; 1. EMMAGATZEMATGE AUTOMATIC (trigger dc): un episodi per sector al final de cada cicle.
(defrule epmem-emmagatzema
  (declare (auto-focus TRUE))
  (fase (nom monitoratge))
  (cicle (numero ?c))
  (epmem-config (aprenentatge on))
  ?st <- (epmem-estat (seguent-id ?id) (sessio-inici ?ini))
  (episodi (cicle ?c) (sector ?s) (operador ?op) (angle ?a))
  (not (epmem-episodi (id ?i&:(>= ?i ?ini)) (cicle ?c) (sector ?s)))
  =>
  (bind ?imp (epmem-impas ?s ?c))
  (bind ?mot "")
  (do-for-fact ((?o operador-seleccionat)) (and (eq ?o:sector ?s) (eq ?o:cicle ?c))
    (bind ?mot ?o:motiu))
  (assert (epmem-episodi (id ?id) (cicle ?c) (sector ?s) (cultiu (epmem-cultiu ?s))
                         (operador ?op) (angle ?a)
                         (risc-total (epmem-risc-total ?s ?c))
                         (cobertura (epmem-cobertura ?s ?c))
                         (impas ?imp) (motiu ?mot)
                         (trets (epmem-trets ?s ?c ?op ?imp pendent pendent))))
  (printout t "[EPMEM] NOU EPISODI #" ?id ": " ?s ", cicle " ?c ", " ?op "." crlf)
  (modify ?st (seguent-id (+ ?id 1)) (brut si)))

; 2. VALORACIO: amb el cicle seguent ja es sap com ha anat l'operador.
;    S'executa a proposta: en aquest punt els riscos del cicle actual ja estan elaborats.
(defrule epmem-valora-resultat
  (declare (auto-focus TRUE))
  (fase (nom proposta))
  (cicle (numero ?c))
  (epmem-config (aprenentatge on))
  ?st <- (epmem-estat (sessio-inici ?ini))
  ?m <- (epmem-episodi (id ?i&:(>= ?i ?ini)) (cicle =(- ?c 1)) (sector ?s) (operador ?op)
                       (valoracio pendent) (risc-total ?r0) (cobertura ?cob0) (trets $?tr))
  (episodi (cicle =(- ?c 1)) (sector ?s) (resultat ?res&~pendent))
  =>
  (bind ?r1 (epmem-risc-total ?s ?c))
  (bind ?cob1 (epmem-cobertura ?s ?c))
  (bind ?v (epmem-valora ?res ?r0 ?r1 ?cob0 ?cob1))
  (printout t "[EPMEM] " ?s ": l'episodi #" ?i " (" ?op ") es valora '" ?v "' (resultat " ?res
              ", risc " ?r0 " -> " ?r1 ")." crlf)
  (modify ?m (resultat ?res) (valoracio ?v) (trets (epmem-actualitza-trets ?tr ?res ?v)))
  (modify ?st (brut si)))

; 3. CONSULTES. Nomes es processen amb l'aprenentatge activat (com a Soar).
(defrule epmem-processa-query
  (declare (auto-focus TRUE))
  (epmem-config (aprenentatge on))
  ?q <- (epmem-consulta (id ?id) (sector ?s) (cicle ?c) (etiqueta ?et) (tipus query)
                        (cue $?cue) (requereix $?req) (exclou $?exc) (prohibits $?pro)
                        (estat pendent))
  =>
  (bind ?r (epmem-cerca ?cue ?req ?exc ?pro))
  (bind ?m (nth$ 1 ?r))
  (bind ?k (nth$ 2 ?r))
  (bind ?n (length$ ?cue))
  (if (> ?m 0)
   then (assert (epmem-resultat (consulta ?id) (sector ?s) (cicle ?c) (etiqueta ?et)
                                (exit si) (memoria-id ?m) (cardinalitat ?k)
                                (puntuacio (float ?k))
                                (normalitzada (if (> ?n 0) then (/ ?k ?n) else 0.0))
                                (perfecte (if (= ?k ?n) then si else no))))
   else (assert (epmem-resultat (consulta ?id) (sector ?s) (cicle ?c) (etiqueta ?et) (exit no))))
  (modify ?q (estat fet)))

(defrule epmem-processa-temporal
  (declare (auto-focus TRUE))
  (epmem-config (aprenentatge on))
  ?q <- (epmem-consulta (id ?id) (sector ?s) (cicle ?c) (etiqueta ?et)
                        (tipus ?t&next|previous) (ref ?ref) (estat pendent))
  =>
  (bind ?m (epmem-veinat ?ref (if (eq ?t next) then 1 else -1)))
  (assert (epmem-resultat (consulta ?id) (sector ?s) (cicle ?c) (etiqueta ?et)
                          (exit (if (> ?m 0) then si else no)) (memoria-id ?m)))
  (modify ?q (estat fet)))

; Neteja de les consultes i resultats de cicles anteriors (com Soar, que neteja epmem.result).
(defrule epmem-neteja-consultes
  (declare (auto-focus TRUE))
  (fase (nom percepcio))
  (cicle (numero ?c))
  ?f <- (epmem-consulta (cicle ?k&:(< ?k ?c)))
  =>
  (retract ?f))

(defrule epmem-neteja-resultats
  (declare (auto-focus TRUE))
  (fase (nom percepcio))
  (cicle (numero ?c))
  ?f <- (epmem-resultat (cicle ?k&:(< ?k ?c)))
  =>
  (retract ?f))

; 4. PERSISTENCIA: una escriptura per cicle, abans de tancar-lo.
(defrule epmem-persisteix
  (declare (salience -5) (auto-focus TRUE))
  (fase (nom monitoratge))
  (epmem-config (fitxer ?f&~""))
  ?st <- (epmem-estat (brut si))
  =>
  (desa-epmem ?f)
  (modify ?st (brut no)))

(deffacts epmem-inicial
  (epmem-config)
  (epmem-estat))

