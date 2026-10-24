(defmodule DELIBERACIO
  (import DOMINI ?ALL)
  (import MEMORIA deffunction ?ALL)
  (export ?ALL))

;  DELIBERACIÓ --------------------------------------------------------------------

; Les fases percepcio, elaboracio, proposta i avaluacio viuen en aquest modul.
; Les regles de canvi de fase tenen salience -10: una fase nomes acaba quan
; ja no queda cap altra regla d'aquella fase per disparar.

; --- funcions auxiliars ------------------------------------------------------

(deffunction nivell-a-numero (?n)
  (switch ?n
    (case baix then 0)
    (case mitja then 1)
    (case alt then 2)
    (case critic then 3)
    (default 0)))

; Pes de cada objectiu en les valoracions. Segueix l'ordre de prioritats.
; Cultiu i energia pesen igual: si empaten, ho resol l'impasse.
(deffunction pes-objectiu (?o)
  (switch ?o
    (case seguretat then 5)
    (case produccio-cultiu then 3)
    (case produccio-energia then 3)
    (case estabilitat then 2)
    (case minimitzar-moviment then 1)
    (default 0)))

; baix dins l'optim, mitja fins a mig cami del limit absolut,
; alt fins al limit absolut, critic per sobre
(deffunction nivell-calor (?t ?opt ?abs)
  (if (<= ?t ?opt) then baix
   else (if (<= ?t (+ ?opt (/ (- ?abs ?opt) 2))) then mitja
   else (if (<= ?t ?abs) then alt
   else critic))))

; ?h = % d'aigua disponible que queda al sol; ?p = fraccio esgotable sense estres
; v1_8: les comparacions porten un marge de 1e-9. Sense, 1 - 70/100 val 0.30000000000000004
; (coma flotant) i l'enciam al limit exacte (70 %, p = 0.30) sortia amb estres mitja (E3, cas A07).
(deffunction nivell-hidric (?h ?p)
  (bind ?eps 1.0e-9)
  (bind ?e (- 1 (/ ?h 100)))
  (bind ?tram (/ (- 1 ?p) 3))
  (if (<= ?e (+ ?p ?eps)) then baix
   else (if (<= ?e (+ ?p ?tram ?eps)) then mitja
   else (if (<= ?e (+ ?p (* 2 ?tram) ?eps)) then alt
   else critic))))

(deffunction nivell-radiacio (?r ?opt ?estres)
  (if (<= ?r ?opt) then baix
   else (if (<= ?r ?estres) then mitja
   else alt)))

; Recupera la previsio de vent del sector/cicle. Si no n'hi ha, retorna absent.
(deffunction previsio-vent-sector (?s ?c)
  (bind ?pv absent)
  (do-for-fact ((?p prediccio))
      (and (eq ?p:sector ?s) (eq ?p:cicle ?c))
    (bind ?pv ?p:vent))
  ?pv)

; si hi ha previsio de vent, es te en compte la pitjor de les dues
(deffunction vent-efectiu (?v ?pv)
  (if (numberp ?pv) then (max ?v ?pv) else ?v))

(deffunction nivell-vent (?v ?avis ?max)
  (if (>= ?v ?max) then critic
   else (if (>= ?v ?avis) then alt
   else baix)))

; Puntuacio total d'un operador: suma de valoracions numeriques.
; requerida i millor/pitjor pesen molt mes que qualsevol valoracio.
(deffunction puntuacio (?s ?op ?c)
  (bind ?total 0)
  (do-for-all-facts ((?p preferencia))
      (and (eq ?p:sector ?s) (eq ?p:op ?op) (eq ?p:cicle ?c))
    (switch ?p:tipus
      (case numerica then (bind ?total (+ ?total ?p:valor)))
      (case requerida then (bind ?total (+ ?total 1000)))
      (case millor then (bind ?total (+ ?total 100)))
      (case pitjor then (bind ?total (- ?total 100)))))
  ?total)

; Objectiu al qual serveix cada operador.
(deffunction objectiu-operador (?op)
  (switch ?op
    (case orientar-ombra then produccio-cultiu)
    (case orientar-produccio then produccio-energia)
    (case mantenir-posicio then minimitzar-moviment)
    (case posicio-seguretat then seguretat)
    (case sollicitar-dades then seguretat)
    (default nil)))

(deffunction id-objectiu (?tipus)
  (bind ?id nil)
  (do-for-fact ((?o objectiu)) (eq ?o:tipus ?tipus) (bind ?id ?o:id))
  ?id)

; TRUE si l'objectiu ?a preval sobre ?b seguint la cadena de prioritats
; (la transitivitat que a l'ontologia fa el raonador, aqui la fa la recursio).
(deffunction preval (?a ?b))
(deffunction preval (?a ?b)
  (if (eq ?a ?b) then (return FALSE))
  (bind ?res FALSE)
  (do-for-all-facts ((?p prioritat)) (eq ?p:major ?a)
    (if (or (eq ?p:menor ?b) (preval ?p:menor ?b)) then (bind ?res TRUE)))
  ?res)

; Quant s'ha de moure el panell per aplicar l'operador (per a la reversibilitat).
(deffunction moviment-operador (?s ?op ?c)
  (bind ?m 0)
  (do-for-fact ((?o operador)) (and (eq ?o:sector ?s) (eq ?o:cicle ?c) (eq ?o:nom ?op))
    (do-for-fact ((?p panell)) (eq ?p:sector ?s)
      (bind ?m (abs (- ?o:angle-objectiu ?p:angle)))))
  ?m)


; --- PERCEPCIO: comprovar que les dades son fiables -------------------------

(defrule percep-lectura-absent
  (declare (auto-focus TRUE))
  (fase (nom percepcio))
  (cicle (numero ?c))
  (observacio (sector ?s) (cicle ?c) (vent ?v) (temperatura-cultiu ?t)
              (humitat-sol ?h) (radiacio ?r))
  (test (or (eq ?v absent) (eq ?t absent) (eq ?h absent) (eq ?r absent)))
  (not (risc (sector ?s) (cicle ?c) (tipus dades)))
  =>
  ; sense vent no es pot garantir la seguretat del panell
  (bind ?n (if (eq ?v absent) then critic else alt))
  (printout t "[PERCEPCIO] " ?s ": falten lectures (vent=" ?v ", temp-cultiu=" ?t
              ", humitat=" ?h ", radiacio=" ?r "). Risc de dades " ?n "." crlf)
  (assert (risc (sector ?s) (cicle ?c) (tipus dades) (nivell ?n) (font P1-lectura-absent)))
  (assert (traca (pas ?c) (fase percepcio)
                 (missatge (str-cat ?s ": lectura absent, risc de dades " ?n)))))

(defrule percep-sensor-no-valid
  (declare (auto-focus TRUE))
  (fase (nom percepcio))
  (cicle (numero ?c))
  (estat-sensor (sector ?s) (tipus ?tp) (operatiu ?op) (qualitat ?q))
  (test (or (eq ?op no) (neq ?q valida)))
  (not (risc (sector ?s) (cicle ?c) (tipus dades)))
  =>
  (bind ?n (if (eq ?tp vent) then critic else alt))
  (printout t "[PERCEPCIO] " ?s ": el sensor de " ?tp " no es fiable (operatiu=" ?op
              ", qualitat=" ?q "). Risc de dades " ?n "." crlf)
  (assert (risc (sector ?s) (cicle ?c) (tipus dades) (nivell ?n) (font P2-sensor-no-valid)))
  (assert (traca (pas ?c) (fase percepcio)
                 (missatge (str-cat ?s ": sensor de " ?tp " no fiable, risc de dades " ?n)))))

; si ja hi havia un risc de dades alt i el problema afecta el vent, passa a critic
(defrule percep-dades-vent-critic
  (declare (auto-focus TRUE))
  (fase (nom percepcio))
  (cicle (numero ?c))
  ?r <- (risc (sector ?s) (cicle ?c) (tipus dades) (nivell alt))
  (or (observacio (sector ?s) (cicle ?c) (vent absent))
      (estat-sensor (sector ?s) (tipus vent) (qualitat ~valida))
      (estat-sensor (sector ?s) (tipus vent) (operatiu no)))
  =>
  (printout t "[PERCEPCIO] " ?s ": el problema de dades afecta el vent; el risc passa a critic." crlf)
  (modify ?r (nivell critic) (font P3-dades-vent)))

(defrule percep-sense-observacio
  (declare (auto-focus TRUE))
  (fase (nom percepcio))
  (cicle (numero ?c))
  (sector (id ?s))
  (not (observacio (sector ?s) (cicle ?c)))
  (not (risc (sector ?s) (cicle ?c) (tipus dades)))
  =>
  (printout t "[PERCEPCIO] " ?s ": no ha arribat cap observacio aquest cicle. Risc de dades critic." crlf)
  (assert (risc (sector ?s) (cicle ?c) (tipus dades) (nivell critic) (font P4-sense-observacio)))
  (assert (traca (pas ?c) (fase percepcio)
                 (missatge (str-cat ?s ": sense observacio, risc de dades critic")))))

; Efecte de l'accio anterior: el panell ha arribat a l'angle ordenat?
(defrule percep-accio-correcta
  (declare (auto-focus TRUE))
  (fase (nom percepcio))
  (cicle (numero ?c))
  ?e <- (episodi (cicle =(- ?c 1)) (sector ?s) (operador ?op) (angle ?a) (resultat pendent))
  (panell (sector ?s) (tolerancia-angle ?tol))
  (not (panell (sector ?s) (angle ?x&:(> (abs (- ?x ?a)) ?tol))))
  =>
  (modify ?e (resultat correcte)))

(defrule percep-fallada-actuador
  (declare (auto-focus TRUE))
  (fase (nom percepcio))
  (cicle (numero ?c))
  ?e <- (episodi (cicle =(- ?c 1)) (sector ?s) (operador ?op) (angle ?a) (resultat pendent))
  (panell (id ?p) (sector ?s) (angle ?x) (tolerancia-angle ?tol))
  (test (> (abs (- ?x ?a)) ?tol))
  =>
  (printout t "[PERCEPCIO] " ?s ": " ?p " es a " ?x " graus pero se li va ordenar " ?a
              " (" ?op "). Fallada d'actuacio." crlf)
  (modify ?e (resultat fallada))
  (assert (risc (sector ?s) (cicle ?c) (tipus fallada-actuador) (nivell alt) (font P5-fallada)))
  (assert (traca (pas ?c) (fase percepcio)
                 (missatge (str-cat ?s ": " ?p " no ha arribat a " ?a " graus, fallada d'actuacio")))))

(defrule percepcio-a-elaboracio
  (declare (salience -10) (auto-focus TRUE))
  ?f <- (fase (nom percepcio))
  =>
  (printout t "[PERCEPCIO -> ELABORACIO]" crlf)
  (retract ?f)
  (assert (fase (nom elaboracio))))


; --- ELABORACIO: de lectures a riscos (classificacio heuristica) -------------

(defrule elabora-risc-mecanic
  (declare (auto-focus TRUE))
  (fase (nom elaboracio))
  (cicle (numero ?c))
  (observacio (sector ?s) (cicle ?c) (vent ?v&:(numberp ?v)))
  (panell (sector ?s) (vent-avis ?avis) (vent-maxim ?max))
  (not (risc (sector ?s) (cicle ?c) (tipus mecanic)))
  =>
  (bind ?pv (previsio-vent-sector ?s ?c))
  (bind ?ve (vent-efectiu ?v ?pv))
  (bind ?n (nivell-vent ?ve ?avis ?max))
  (if (neq ?n baix) then
    (printout t "[ELABORACIO] " ?s ": vent " ?v " m/s (previsio " ?pv ") >= "
                (if (eq ?n critic) then ?max else ?avis) " m/s. Risc mecanic " ?n "." crlf)
    (assert (risc (sector ?s) (cicle ?c) (tipus mecanic) (nivell ?n) (font E1-vent)))
    (assert (traca (pas ?c) (fase elaboracio)
                   (missatge (str-cat ?s ": vent efectiu " ?ve " m/s, risc mecanic " ?n))))))

;  Si no arriba la lectura de vent pero hi ha previsio, el risc es calcula amb la previsio.
(defrule elabora-risc-mecanic-per-previsio
  (declare (auto-focus TRUE))
  (fase (nom elaboracio))
  (cicle (numero ?c))
  (observacio (sector ?s) (cicle ?c) (vent absent))
  (prediccio (sector ?s) (cicle ?c) (vent ?pv&:(numberp ?pv)))
  (panell (sector ?s) (vent-avis ?avis) (vent-maxim ?max))
  (not (risc (sector ?s) (cicle ?c) (tipus mecanic)))
  =>
  (bind ?n (nivell-vent ?pv ?avis ?max))
  (if (neq ?n baix) then
    (printout t "[ELABORACIO] " ?s ": sense lectura de vent, pero la previsio es de " ?pv " m/s >= "
                (if (eq ?n critic) then ?max else ?avis) " m/s. Risc mecanic " ?n "." crlf)
    (assert (risc (sector ?s) (cicle ?c) (tipus mecanic) (nivell ?n) (font E1-previsio-vent)))
    (assert (traca (pas ?c) (fase elaboracio)
                   (missatge (str-cat ?s ": sense lectura de vent, previsio " ?pv " m/s, risc mecanic " ?n))))))

(defrule elabora-risc-temperatura
  (declare (auto-focus TRUE))
  (fase (nom elaboracio))
  (cicle (numero ?c))
  (sector (id ?s) (cultiu ?cu))
  (cultiu (id ?cu) (tipus ?tc))
  (llindars-cultiu (tipus ?tc) (temp-optima-max ?opt) (temp-absoluta-max ?abs))
  (observacio (sector ?s) (cicle ?c) (temperatura-cultiu ?t&:(numberp ?t)))
  (not (risc (sector ?s) (cicle ?c) (tipus temperatura)))
  =>
  (bind ?n (nivell-calor ?t ?opt ?abs))
  (if (neq ?n baix) then
    (printout t "[ELABORACIO] " ?s ": " ?tc " a " ?t " C (optim fins a " ?opt
                ", maxim " ?abs "). Risc de temperatura " ?n "." crlf)
    (assert (risc (sector ?s) (cicle ?c) (tipus temperatura) (nivell ?n) (font E2-calor)))
    (assert (traca (pas ?c) (fase elaboracio)
                   (missatge (str-cat ?s ": " ?tc " a " ?t " C, risc de temperatura " ?n))))))

(defrule elabora-risc-hidric
  (declare (auto-focus TRUE))
  (fase (nom elaboracio))
  (cicle (numero ?c))
  (sector (id ?s) (cultiu ?cu))
  (cultiu (id ?cu) (tipus ?tc))
  (llindars-cultiu (tipus ?tc) (fraccio-esgotament-p ?p))
  (observacio (sector ?s) (cicle ?c) (humitat-sol ?h&:(numberp ?h)))
  (not (risc (sector ?s) (cicle ?c) (tipus estres-hidric)))
  =>
  (bind ?n (nivell-hidric ?h ?p))
  (if (neq ?n baix) then
    (printout t "[ELABORACIO] " ?s ": queda un " ?h "% d'aigua disponible (" ?tc
                " tolera esgotar fins al " (* 100 ?p) "%). Estres hidric " ?n "." crlf)
    (assert (risc (sector ?s) (cicle ?c) (tipus estres-hidric) (nivell ?n) (font E3-aigua)))
    (assert (traca (pas ?c) (fase elaboracio)
                   (missatge (str-cat ?s ": humitat " ?h "%, estres hidric " ?n))))))

(defrule elabora-risc-radiacio
  (declare (auto-focus TRUE))
  (fase (nom elaboracio))
  (cicle (numero ?c))
  (sector (id ?s) (cultiu ?cu))
  (cultiu (id ?cu) (tipus ?tc))
  (llindars-cultiu (tipus ?tc) (radiacio-optima-max ?opt) (radiacio-estres ?est))
  (observacio (sector ?s) (cicle ?c) (radiacio ?r&:(numberp ?r)))
  (not (risc (sector ?s) (cicle ?c) (tipus exces-radiacio)))
  =>
  (bind ?n (nivell-radiacio ?r ?opt ?est))
  (if (neq ?n baix) then
    (printout t "[ELABORACIO] " ?s ": radiacio " ?r " W/m2 (" ?tc ": optim fins a " ?opt
                ", estres des de " ?est "). Risc de radiacio " ?n "." crlf)
    (assert (risc (sector ?s) (cicle ?c) (tipus exces-radiacio) (nivell ?n) (font E4-radiacio)))
    (assert (traca (pas ?c) (fase elaboracio)
                   (missatge (str-cat ?s ": radiacio " ?r " W/m2, risc de radiacio " ?n))))))

; molta llum i molta calor alhora fan mal de veritat al cultiu
(defrule elabora-radiacio-amb-calor
  (declare (auto-focus TRUE))
  (fase (nom elaboracio))
  (cicle (numero ?c))
  ?r <- (risc (sector ?s) (cicle ?c) (tipus exces-radiacio) (nivell alt))
  (risc (sector ?s) (cicle ?c) (tipus temperatura) (nivell alt|critic))
  =>
  (printout t "[ELABORACIO] " ?s ": radiacio alta amb calor alta. El risc de radiacio passa a critic." crlf)
  (modify ?r (nivell critic) (font E5-radiacio-calor))
  (assert (traca (pas ?c) (fase elaboracio)
                 (missatge (str-cat ?s ": radiacio i calor altes alhora, risc de radiacio critic")))))

; energia, estabilitat i moviment sempre es tenen en compte
(defrule activa-objectius-base
  (declare (auto-focus TRUE))
  (fase (nom elaboracio))
  ?o <- (objectiu (id ?id) (tipus produccio-energia|estabilitat|minimitzar-moviment) (estat inactiu))
  =>
  (modify ?o (estat actiu)))

(defrule activa-objectiu-per-risc
  (declare (auto-focus TRUE))
  (fase (nom elaboracio))
  (cicle (numero ?c))
  (risc (sector ?s) (cicle ?c) (tipus ?tr) (nivell mitja|alt|critic))
  (activa (tipus-risc ?tr) (objectiu ?id))
  ?o <- (objectiu (id ?id) (estat inactiu))
  =>
  (printout t "[ELABORACIO] El risc " ?tr " de " ?s " activa l'objectiu " ?id "." crlf)
  (modify ?o (estat actiu)))

(defrule elaboracio-a-proposta
  (declare (salience -10) (auto-focus TRUE))
  ?f <- (fase (nom elaboracio))
  (cicle (numero ?c))
  =>
  (printout t "[ELABORACIO -> PROPOSTA]" crlf)
  (retract ?f)
  (assert (fase (nom proposta))))


; --- PROPOSTA: tots els operadors aplicables -------------

(defrule proposa-mantenir-posicio
  (declare (auto-focus TRUE))
  (fase (nom proposta))
  (cicle (numero ?c))
  (sector (id ?s))
  (panell (sector ?s) (angle ?a))
  (not (operador (sector ?s) (cicle ?c) (nom mantenir-posicio)))
  =>
  (printout t "[PROPOSTA] " ?s ": mantenir-posicio (" ?a " graus)." crlf)
  (assert (operador (id (sym-cat ?s -mantenir- ?c)) (cicle ?c) (sector ?s)
                    (nom mantenir-posicio) (angle-objectiu ?a) (estat proposat)))
  (assert (preferencia (op mantenir-posicio) (sector ?s) (cicle ?c) (tipus acceptable) (font R1))))

(defrule proposa-orientar-produccio
  (declare (auto-focus TRUE))
  (fase (nom proposta))
  (cicle (numero ?c))
  (sector (id ?s))
  (panell (sector ?s) (angle-optim-produccio ?ang))
  (not (panell (sector ?s) (disponible no)))
  (not (panell (sector ?s) (estat-mecanic avariat)))
  (not (operador (sector ?s) (cicle ?c) (nom orientar-produccio)))
  =>
  (printout t "[PROPOSTA] " ?s ": orientar-produccio (" ?ang " graus)." crlf)
  (assert (operador (id (sym-cat ?s -produccio- ?c)) (cicle ?c) (sector ?s)
                    (nom orientar-produccio) (angle-objectiu ?ang) (estat proposat)))
  (assert (preferencia (op orientar-produccio) (sector ?s) (cicle ?c) (tipus acceptable) (font R2))))

(defrule proposa-orientar-ombra
  (declare (auto-focus TRUE))
  (fase (nom proposta))
  (cicle (numero ?c))
  (risc (sector ?s) (cicle ?c) (tipus temperatura|exces-radiacio|estres-hidric)
        (nivell mitja|alt|critic))
  (panell (sector ?s) (angle-ombra ?ang))
  (not (panell (sector ?s) (disponible no)))
  (not (panell (sector ?s) (estat-mecanic avariat)))
  (not (operador (sector ?s) (cicle ?c) (nom orientar-ombra)))
  =>
  (printout t "[PROPOSTA] " ?s ": orientar-ombra (" ?ang " graus), hi ha risc per al cultiu." crlf)
  (assert (operador (id (sym-cat ?s -ombra- ?c)) (cicle ?c) (sector ?s)
                    (nom orientar-ombra) (angle-objectiu ?ang) (estat proposat)))
  (assert (preferencia (op orientar-ombra) (sector ?s) (cicle ?c) (tipus acceptable) (font R3))))

; amb risc mecanic alt o critic, la posicio de seguretat es aplicable.
; La manca de dades, per si sola, NO implica moure el panell: obre un impasse
; que es resol sol.licitant dades i mantenint temporalment l'angle actual.
(defrule proposa-posicio-seguretat
  (declare (auto-focus TRUE))
  (fase (nom proposta))
  (cicle (numero ?c))
  (risc (sector ?s) (cicle ?c) (tipus mecanic) (nivell alt|critic))
  (panell (sector ?s) (angle-seguretat ?ang))
  (not (operador (sector ?s) (cicle ?c) (nom posicio-seguretat)))
  =>
  (printout t "[PROPOSTA] " ?s ": posicio-seguretat (" ?ang " graus)." crlf)
  (assert (operador (id (sym-cat ?s -seguretat- ?c)) (cicle ?c) (sector ?s)
                    (nom posicio-seguretat) (angle-objectiu ?ang) (estat proposat)))
  (assert (preferencia (op posicio-seguretat) (sector ?s) (cicle ?c) (tipus acceptable) (font R4))))

(defrule proposa-sollicitar-dades
  (declare (auto-focus TRUE))
  (fase (nom proposta))
  (cicle (numero ?c))
  (risc (sector ?s) (cicle ?c) (tipus dades))
  (panell (sector ?s) (angle ?a))
  (not (operador (sector ?s) (cicle ?c) (nom sollicitar-dades)))
  =>
  (printout t "[PROPOSTA] " ?s ": sollicitar-dades (no es mou el panell)." crlf)
  (assert (operador (id (sym-cat ?s -dades- ?c)) (cicle ?c) (sector ?s)
                    (nom sollicitar-dades) (angle-objectiu ?a) (estat proposat)))
  (assert (preferencia (op sollicitar-dades) (sector ?s) (cicle ?c) (tipus acceptable) (font R5))))

(defrule proposta-a-avaluacio
  (declare (salience -10) (auto-focus TRUE))
  ?f <- (fase (nom proposta))
  =>
  (printout t "[PROPOSTA -> AVALUACIO]" crlf)
  (retract ?f)
  (assert (fase (nom avaluacio))))


; --- AVALUACIO: restriccions dures i valoracions (resolucio constructiva) ----

; Restriccio dura: amb risc mecanic critic nomes es pot anar a seguretat.
(defrule avalua-rebuig-per-vent-critic
  (declare (auto-focus TRUE))
  (fase (nom avaluacio))
  (cicle (numero ?c))
  (risc (sector ?s) (cicle ?c) (tipus mecanic) (nivell critic))
  (operador (sector ?s) (cicle ?c) (nom ?op&~posicio-seguretat))
  (not (preferencia (op ?op) (sector ?s) (cicle ?c) (tipus rebuig)))
  =>
  (printout t "[AVALUACIO] " ?s ": REBUIG de " ?op " (vent critic, restriccio de seguretat)." crlf)
  (assert (preferencia (op ?op) (sector ?s) (cicle ?c) (tipus rebuig) (font AV1-vent-critic)))
  (assert (traca (pas ?c) (fase avaluacio)
                 (missatge (str-cat ?s ": " ?op " rebutjat per vent critic")))))

; Restriccio dura: cap operador pot portar el panell fora dels seus limits.
(defrule avalua-rebuig-fora-de-limits
  (declare (auto-focus TRUE))
  (fase (nom avaluacio))
  (cicle (numero ?c))
  (operador (sector ?s) (cicle ?c) (nom ?op) (angle-objectiu ?a))
  (panell (sector ?s) (angle-minim ?min) (angle-maxim ?max))
  (test (or (< ?a ?min) (> ?a ?max)))
  (not (preferencia (op ?op) (sector ?s) (cicle ?c) (tipus rebuig)))
  =>
  (printout t "[AVALUACIO] " ?s ": REBUIG de " ?op " (" ?a " graus fora de [" ?min ", " ?max "])." crlf)
  (assert (preferencia (op ?op) (sector ?s) (cicle ?c) (tipus rebuig) (font AV2-limits)))
  (assert (traca (pas ?c) (fase avaluacio)
                 (missatge (str-cat ?s ": " ?op " rebutjat, angle fora de limits")))))

; Restriccio dura: si l'actuador ha fallat no se li envien ordres de seguiment.
(defrule avalua-rebuig-per-fallada
  (declare (auto-focus TRUE))
  (fase (nom avaluacio))
  (cicle (numero ?c))
  (risc (sector ?s) (cicle ?c) (tipus fallada-actuador))
  (operador (sector ?s) (cicle ?c) (nom ?op&orientar-produccio|orientar-ombra))
  (not (preferencia (op ?op) (sector ?s) (cicle ?c) (tipus rebuig)))
  =>
  (printout t "[AVALUACIO] " ?s ": REBUIG de " ?op " (l'actuador no respon)." crlf)
  (assert (preferencia (op ?op) (sector ?s) (cicle ?c) (tipus rebuig) (font AV9-fallada)))
  (assert (traca (pas ?c) (fase avaluacio)
                 (missatge (str-cat ?s ": " ?op " rebutjat per fallada d'actuacio")))))

; Vent alt (no critic): la seguretat no es obligatoria pero pesa molt.
(defrule avalua-seguretat
  (declare (auto-focus TRUE))
  (fase (nom avaluacio))
  (cicle (numero ?c))
  (risc (sector ?s) (cicle ?c) (tipus mecanic) (nivell alt))
  (objectiu (tipus seguretat) (estat actiu))
  (operador (sector ?s) (cicle ?c) (nom posicio-seguretat))
  (not (preferencia (op posicio-seguretat) (sector ?s) (cicle ?c) (font AV3-seguretat)))
  =>
  (bind ?v (* (pes-objectiu seguretat) (nivell-a-numero alt)))
  (printout t "[AVALUACIO] " ?s ": posicio-seguretat +" ?v " (seguretat, vent alt)." crlf)
  (assert (preferencia (op posicio-seguretat) (sector ?s) (cicle ?c) (tipus numerica)
                       (valor ?v) (font AV3-seguretat))))

; Cada risc per al cultiu suma a favor de fer ombra.
(defrule avalua-cultiu
  (declare (auto-focus TRUE))
  (fase (nom avaluacio))
  (cicle (numero ?c))
  (risc (sector ?s) (cicle ?c) (tipus ?tr&temperatura|exces-radiacio|estres-hidric)
        (nivell ?n&mitja|alt|critic))
  (objectiu (tipus produccio-cultiu) (estat actiu))
  (operador (sector ?s) (cicle ?c) (nom orientar-ombra))
  (not (preferencia (op orientar-ombra) (sector ?s) (cicle ?c) (font =(sym-cat AV4-cultiu- ?tr))))
  =>
  (bind ?v (* (pes-objectiu produccio-cultiu) (nivell-a-numero ?n)))
  (printout t "[AVALUACIO] " ?s ": orientar-ombra +" ?v " (cultiu, risc " ?tr " " ?n ")." crlf)
  (assert (preferencia (op orientar-ombra) (sector ?s) (cicle ?c) (tipus numerica)
                       (valor ?v) (font (sym-cat AV4-cultiu- ?tr)))))

; Produir: val el doble si el sector no cobreix la seva demanda.
(defrule avalua-energia-produccio
  (declare (auto-focus TRUE))
  (fase (nom avaluacio))
  (cicle (numero ?c))
  (objectiu (tipus produccio-energia) (estat actiu))
  (operador (sector ?s) (cicle ?c) (nom orientar-produccio))
  (energia (sector ?s) (cicle ?c) (produccio-actual ?prod) (demanda ?dem))
  (not (preferencia (op orientar-produccio) (sector ?s) (cicle ?c) (font AV5-energia)))
  =>
  (bind ?n (if (< ?prod ?dem) then alt else mitja))
  (bind ?v (* (pes-objectiu produccio-energia) (nivell-a-numero ?n)))
  (printout t "[AVALUACIO] " ?s ": orientar-produccio +" ?v " (energia, produccio " ?prod
              " / demanda " ?dem ")." crlf)
  (assert (preferencia (op orientar-produccio) (sector ?s) (cicle ?c) (tipus numerica)
                       (valor ?v) (font AV5-energia))))

; Si el panell ja es a l'angle optim (dins la tolerancia), quedar-s'hi tambe produeix.
(defrule avalua-energia-mantenir
  (declare (auto-focus TRUE))
  (fase (nom avaluacio))
  (cicle (numero ?c))
  (objectiu (tipus produccio-energia) (estat actiu))
  (operador (sector ?s) (cicle ?c) (nom mantenir-posicio))
  (panell (sector ?s) (angle ?a) (angle-optim-produccio ?opt) (tolerancia-angle ?tol))
  (test (<= (abs (- ?a ?opt)) ?tol))
  (energia (sector ?s) (cicle ?c) (produccio-actual ?prod) (demanda ?dem))
  (not (preferencia (op mantenir-posicio) (sector ?s) (cicle ?c) (font AV6-energia)))
  =>
  (bind ?n (if (< ?prod ?dem) then alt else mitja))
  (bind ?v (* (pes-objectiu produccio-energia) (nivell-a-numero ?n)))
  (printout t "[AVALUACIO] " ?s ": mantenir-posicio +" ?v " (ja es a l'angle optim, "
              ?a " vs " ?opt ")." crlf)
  (assert (preferencia (op mantenir-posicio) (sector ?s) (cicle ?c) (tipus numerica)
                       (valor ?v) (font AV6-energia))))

; No moure's no gasta energia ni desgasta el mecanisme.
(defrule avalua-moviment
  (declare (auto-focus TRUE))
  (fase (nom avaluacio))
  (cicle (numero ?c))
  (objectiu (tipus minimitzar-moviment) (estat actiu))
  (operador (sector ?s) (cicle ?c) (nom mantenir-posicio))
  (not (preferencia (op mantenir-posicio) (sector ?s) (cicle ?c) (font AV7-moviment)))
  =>
  (bind ?v (* (pes-objectiu minimitzar-moviment) 1))
  (printout t "[AVALUACIO] " ?s ": mantenir-posicio +" ?v " (sense moviment)." crlf)
  (assert (preferencia (op mantenir-posicio) (sector ?s) (cicle ?c) (tipus numerica)
                       (valor ?v) (font AV7-moviment))))

; Historial: repetir l'operador del cicle anterior evita oscil.lacions.
(defrule avalua-estabilitat
  (declare (auto-focus TRUE))
  (fase (nom avaluacio))
  (cicle (numero ?c))
  (objectiu (tipus estabilitat) (estat actiu))
  (episodi (cicle =(- ?c 1)) (sector ?s) (operador ?op))
  (operador (sector ?s) (cicle ?c) (nom ?op))
  (not (preferencia (op ?op) (sector ?s) (cicle ?c) (font AV8-estabilitat)))
  =>
  (bind ?v (* (pes-objectiu estabilitat) 1))
  (printout t "[AVALUACIO] " ?s ": " ?op " +" ?v " (es el que es va fer el cicle anterior)." crlf)
  (assert (preferencia (op ?op) (sector ?s) (cicle ?c) (tipus numerica)
                       (valor ?v) (font AV8-estabilitat))))

; Memoria episodica: abans de decidir, es pregunta a l'experiencia "que va passar
; l'ultima vegada que vaig fer aixo en una situacio com aquesta?". El cue es la
; situacio actual del sector (sector, cultiu, riscos, cobertura) i es exigeix que
; l'episodi recuperat hagi usat el mateix operador.
(defrule avalua-memoria-consulta
  (declare (auto-focus TRUE))
  (fase (nom avaluacio))
  (cicle (numero ?c))
  (epmem-config (aprenentatge on))
  (operador (sector ?s) (cicle ?c) (nom ?op) (estat proposat))
  (not (epmem-consulta (id =(sym-cat Q- ?s - ?op - ?c))))
  =>
  (assert (epmem-consulta (id (sym-cat Q- ?s - ?op - ?c)) (sector ?s) (cicle ?c)
                          (etiqueta ?op)
                          (cue (epmem-cue-situacio ?s ?c))
                          (requereix (epmem-tret operador ?op)))))

; El record es converteix en una preferencia numerica: positiva si l'operador va
; funcionar be en aquella situacio, negativa si va anar malament. El pes depen de
; la semblança entre la situacio recordada i l'actual. Es un criteri tou: no
; pot superar una restriccio dura (rebuig) ni una preferencia requerida.
(defrule avalua-memoria
  (declare (auto-focus TRUE))
  (fase (nom avaluacio))
  (cicle (numero ?c))
  (epmem-config (pes-memoria ?pes) (llindar-similitud ?ll))
  (epmem-resultat (sector ?s) (cicle ?c) (etiqueta ?op) (exit si)
                  (memoria-id ?m) (normalitzada ?n&:(>= ?n ?ll)))
  (epmem-episodi (id ?m) (cicle ?mc) (valoracio ?v&bona|dolenta))
  (operador (sector ?s) (cicle ?c) (nom ?op) (estat proposat))
  (not (preferencia (op ?op) (sector ?s) (cicle ?c) (font AV10-memoria)))
  =>
  (bind ?val (/ (round (* 100 ?pes ?n)) 100))
  (if (eq ?v dolenta) then (bind ?val (* -1 ?val)))
  (printout t "[AVALUACIO] " ?s ": " ?op " " ?val " (memoria: a l'episodi #" ?m ", cicle " ?mc
              ", va funcionar " (if (eq ?v bona) then "be" else "malament")
              ", similitud " ?n ")." crlf)
  (assert (preferencia (op ?op) (sector ?s) (cicle ?c) (tipus numerica)
                       (valor ?val) (font AV10-memoria)))
  (assert (traca (pas ?c) (fase avaluacio)
                 (missatge (str-cat ?s ": " ?op " " ?val " per memoria episodica (episodi " ?m ")")))))

(defrule avaluacio-a-seleccio
  (declare (salience -10) (auto-focus TRUE))
  ?f <- (fase (nom avaluacio))
  =>
  (printout t "[AVALUACIO -> SELECCIO]" crlf)
  (retract ?f)
  (assert (fase (nom seleccio))))


;  REFORC --------------------------------------------------------------------
