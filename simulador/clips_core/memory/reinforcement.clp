(defmodule REFORC
  (import DOMINI ?ALL)
  (import MEMORIA deffunction ?ALL)
  (export deffunction ?ALL))

; Reforç a l'estil de Soar-RL (Intro_to_SOAR, seccio 5):
;   - La funcio de valor Q(situacio, operador) es la SUMA de rajoles Q(tret, operador),
;     cada una amb un sol tret de la situacio (tile / coarse coding, Wang & Laird 2007).
;     Aixi s'apren de trets que es repeteixen encara que la situacio exacta no torni.
;   - Els chunks apresos en un empat son una rajola mes (tret = nom del chunk), amb
;     valor inicial 'prior' tret del subestat, que despres l'experiencia ajusta.
;   - Q nomes desfa empats entre els candidats amb mes puntuacio: com a Soar, el reforç
;     decideix nomes quan la resta de preferencies no ho fan (DECISIO::desfa-empat-per-reforc).
;   - Recompensa (cicle seguent): bona +1, neutra 0, dolenta -1 (la mateixa valoracio
;     que la memoria episodica, epmem-valora). gamma = 0: l'efecte dels operadors es immediat.
;   - Actualitzacio (gradient lineal): delta = r - suma Q; cada rajola += alfa * delta / n.
;   - Els rebuigs i les preferencies requerides (seguretat) no passen pel reforç.

(deffacts reforc-inicial
  (rl-config))

(deffunction rl-actiu ()
  (any-factp ((?k rl-config)) (eq ?k:aprenentatge on)))

(deffunction activa-reforc (?v)
  (do-for-all-facts ((?k rl-config)) TRUE (modify ?k (aprenentatge ?v)))
  ?v)

(deffunction rl-param (?slot)
  (bind ?r 0)
  (do-for-fact ((?k rl-config)) TRUE (bind ?r (fact-slot-value ?k ?slot)))
  ?r)

(deffunction rl-es-chunk (?tret)
  (eq (str-index "chunk-" (str-cat ?tret)) 1))

(deffunction rl-q (?tret ?op)
  (bind ?r (if (rl-es-chunk ?tret) then (float (rl-param prior)) else 0.0))
  (do-for-fact ((?v rl-valor)) (and (eq ?v:tret ?tret) (eq ?v:op ?op)) (bind ?r ?v:q))
  ?r)

; Rajoles actives per a ?op: trets de la situacio + chunks d'empat que l'han recomanat.
(deffunction rl-trets (?s ?op ?c)
  (bind ?t (create$ tot (epmem-cue-situacio ?s ?c)))
  (do-for-all-facts ((?p preferencia))
      (and (eq ?p:sector ?s) (eq ?p:cicle ?c) (eq ?p:op ?op) (eq ?p:tipus rl) (rl-es-chunk ?p:font))
    (bind ?t (create$ ?t ?p:font)))
  ?t)

(deffunction rl-suma (?trets ?op)
  (bind ?q 0.0)
  (progn$ (?t ?trets) (bind ?q (+ ?q (rl-q ?t ?op))))
  ?q)

(deffunction rl-valor-op (?s ?op ?c)
  (rl-suma (rl-trets ?s ?op ?c) ?op))

(deffunction rl-actualitza (?trets ?op ?r)
  (bind ?n (length$ ?trets))
  (if (= ?n 0) then (return 0.0))
  (bind ?delta (- ?r (rl-suma ?trets ?op)))
  (bind ?pas (/ (* (rl-param alfa) ?delta) ?n))
  (progn$ (?t ?trets)
    (bind ?nou (+ (rl-q ?t ?op) ?pas))
    (bind ?f (find-fact ((?v rl-valor)) (and (eq ?v:tret ?t) (eq ?v:op ?op))))
    (if (> (length$ ?f) 0)
     then (modify (nth$ 1 ?f) (q ?nou) (n (+ 1 (fact-slot-value (nth$ 1 ?f) n))))
     else (assert (rl-valor (tret ?t) (op ?op) (q ?nou) (n 1)))))
  ?delta)

(deffunction rl-recompensa (?valoracio)
  (switch ?valoracio (case bona then 1.0) (case dolenta then -1.0) (default 0.0)))

; Aquestes regles no depenen d'una fase concreta: amb auto-focus, el modul REFORC
; queda sota DELIBERACIO a la pila de focus i, si exigissin una sola fase, el canvi
; de fase podria esborrar-ne les activacions abans que REFORC tingues el focus.

; 1. Quan s'ha triat un operador es guarden les rajoles que l'han valorat.
(defrule rl-registra
  (declare (salience 10) (auto-focus TRUE))
  (rl-config (aprenentatge on))
  (operador-seleccionat (sector ?s) (cicle ?c) (nom ?op))
  (not (rl-traca (sector ?s) (cicle ?c)))
  =>
  (assert (rl-traca (sector ?s) (cicle ?c) (op ?op) (trets (rl-trets ?s ?op ?c))
                    (risc (epmem-risc-total ?s ?c)) (cobertura (epmem-cobertura ?s ?c)))))

; 2. Al cicle seguent (riscos ja elaborats) arriba la recompensa i s'actualitzen.
(defrule rl-recompensa-cicle-anterior
  (declare (auto-focus TRUE))
  (fase (nom proposta|avaluacio|seleccio|impas|aplicacio|explicacio|monitoratge))
  (cicle (numero ?c))
  (rl-config (aprenentatge on))
  ?t <- (rl-traca (sector ?s) (cicle =(- ?c 1)) (op ?op) (trets $?tr)
                  (risc ?r0) (cobertura ?cob0) (estat pendent))
  (episodi (cicle =(- ?c 1)) (sector ?s) (resultat ?res&~pendent))
  =>
  (bind ?v (epmem-valora ?res ?r0 (epmem-risc-total ?s ?c) ?cob0 (epmem-cobertura ?s ?c)))
  (bind ?r (rl-recompensa ?v))
  (bind ?delta (rl-actualitza ?tr ?op ?r))
  (printout t "[REFORC] " ?s ": " ?op " del cicle " (- ?c 1) " -> recompensa " ?r " (" ?v
              "), error " (/ (round (* 100 ?delta)) 100) ", " (length$ ?tr) " rajoles actualitzades." crlf)
  (modify ?t (estat fet)))


