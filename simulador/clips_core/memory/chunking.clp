(defmodule APRENENTATGE
  (import DOMINI ?ALL)
  (export deffunction ?ALL))

;  APRENENTATGE --------------------------------------------------------------
; Chunking generic. Un subobjectiu NO escriu cap regla a ma: mentre es resol,
; les regles del subestat DECLAREN el que han consultat (dep-fet, dep-test,
; dep-neg) i el que han produit (dep-resultat). Quan el subobjectiu acaba,
; crea-chunk converteix aquest registre en una regla:
;   condicions = fets consultats, amb identitats generalitzades (sector -> ?s,
;                cicle -> ?c, cicle-1 -> =(- ?c 1), numeros -> variables)
;                + tests + negacions
;   accions    = resultats del subobjectiu, amb les mateixes variables
; Tot queda guardat a fragment-apres (codi + signatura) i, si la persistencia
; esta activada, s'afegeix al fitxer perque sobrevisqui a un reinici.
;
; Limitacio assumida: CLIPS no exposa quins fets ha casat una regla, per aixo
; les regles del subestat han de declarar-ho (una crida per fet consultat).

(defglobal APRENENTATGE
  ?*fitxer-chunks* = ""
  ?*goal* = nil
  ?*ctx-s* = nil
  ?*ctx-c* = 0
  ?*ordre* = 0
  ?*chunking* = TRUE)

; Equivalent a 'chunk always' (TRUE) / 'chunk never' (FALSE). Per als experiments.
(deffunction activa-chunking (?v)
  (bind ?*chunking* ?v))

; --- utilitats de text ----------------------------------------------------

(deffunction substitueix (?txt ?vell ?nou)
  (bind ?res "")
  (bind ?n (str-length ?vell))
  (while (neq (bind ?i (str-index ?vell ?txt)) FALSE) do
    (bind ?res (str-cat ?res (sub-string 1 (- ?i 1) ?txt) ?nou))
    (bind ?txt (sub-string (+ ?i ?n) (str-length ?txt) ?txt)))
  (str-cat ?res ?txt))

(deffunction escapa (?txt)
  (substitueix (substitueix ?txt "\\" "\\\\") "\"" "\\\""))

(deffunction text-constant (?v)
  (if (multifieldp ?v) then
     (bind ?r "")
     (progn$ (?x ?v)
       (bind ?r (str-cat ?r (if (eq ?r "") then "" else " ") (text-constant ?x))))
     (return ?r))
  (if (stringp ?v) then (return (str-cat "\"" (escapa ?v) "\"")))
  (str-cat ?v))

(deffunction slot-de-cicle (?sl)
  (eq (str-index "cicle" (str-cat ?sl)) 1))

; Generalitzacio per identitat: el valor que coincideix amb el sector o el cicle
; del subobjectiu passa a ser una variable; la resta es queda com a constant.
(deffunction variabilitza (?sl ?v)
  (if (and (not (multifieldp ?v)) (eq ?v ?*ctx-s*)) then (return "?s"))
  (if (and (integerp ?v) (slot-de-cicle ?sl)) then
     (if (eq ?v ?*ctx-c*) then (return "?c"))
     (if (eq ?v (- ?*ctx-c* 1)) then (return "=(- ?c 1)")))
  (text-constant ?v))

; --- registre de dependencies (durant el subobjectiu) ----------------------

(deffunction inicia-aprenentatge (?gid ?s ?c)
  (bind ?*goal* ?gid)
  (bind ?*ctx-s* ?s)
  (bind ?*ctx-c* ?c)
  (bind ?*ordre* 0)
  (do-for-all-facts ((?d dependencia)) (eq ?d:goal ?gid) (retract ?d))
  TRUE)

(deffunction afegeix-dependencia (?tipus ?text ?vars)
  (bind ?*ordre* (+ ?*ordre* 1))
  (assert (dependencia (goal ?*goal*) (tipus ?tipus) (ordre ?*ordre*)
                       (text ?text) (vars ?vars))))

; Fet consultat. ?slots = slots que s'han mirat (nomes aquests entren al chunk).
; ?extres = parelles (slot "restriccio") que substitueixen la restriccio automatica.
(deffunction dep-fet (?alias ?fet ?slots ?extres)
  (bind ?txt (str-cat "(" (fact-relation ?fet)))
  (bind ?vars (create$))
  (progn$ (?sl ?slots)
    (bind ?v (fact-slot-value ?fet ?sl))
    (if (and (numberp ?v) (not (slot-de-cicle ?sl)))
     then (bind ?var (str-cat "?" ?alias "-" ?sl))
          (bind ?txt (str-cat ?txt " (" ?sl " " ?var "&:(numberp " ?var "))"))
          (bind ?vars (create$ ?vars ?v (sym-cat ?var)))
     else (bind ?txt (str-cat ?txt " (" ?sl " " (variabilitza ?sl ?v) ")"))))
  (loop-for-count (?k 1 (div (length$ ?extres) 2))
    (bind ?txt (str-cat ?txt " (" (nth$ (- (* 2 ?k) 1) ?extres) " "
                        (nth$ (* 2 ?k) ?extres) ")")))
  (afegeix-dependencia positiva (str-cat ?txt ")") ?vars))

; Relacio entre valors consultats; usa les variables ?alias-slot.
(deffunction dep-test (?expr)
  (afegeix-dependencia test (str-cat "(test " ?expr ")") (create$)))

; Condicio negativa (el subobjectiu ha comprovat que alguna cosa NO hi era).
(deffunction dep-neg (?text)
  (afegeix-dependencia negacio ?text (create$)))

(deffunction vars-del-goal ()
  (bind ?r (create$))
  (do-for-all-facts ((?d dependencia)) (and (eq ?d:goal ?*goal*) (eq ?d:tipus positiva))
    (bind ?r (create$ ?r ?d:vars)))
  ?r)

; Part central d'un id <sector>-<mig>-<cicle> (p. ex. "-seguretat-"), per regenerar-lo igual.
(deffunction mig-de-id (?id)
  (bind ?txt (str-cat ?id))
  (bind ?ini (+ 1 (str-length (str-cat ?*ctx-s*))))
  (bind ?fi (- (str-length ?txt) (str-length (str-cat ?*ctx-c*))))
  (sub-string ?ini ?fi ?txt))

(deffunction valor-accio (?sl ?v ?vars ?nom-op)
  (if (eq ?sl font) then (return "%NOM%"))
  (if (and (eq ?sl id) (neq ?nom-op nil)) then (return (str-cat "(sym-cat ?s " (mig-de-id ?v) " ?c)")))
  (if (and (not (multifieldp ?v)) (eq ?v ?*ctx-s*)) then (return "?s"))
  (if (and (integerp ?v) (slot-de-cicle ?sl) (eq ?v ?*ctx-c*)) then (return "?c"))
  (if (and (numberp ?v) (member$ ?v ?vars)) then
     (return (str-cat (nth$ (+ 1 (member$ ?v ?vars)) ?vars))))
  (text-constant ?v))

; Resultat del subobjectiu: fet que ha creat i que el chunk tornara a crear.
; Si es un operador, nomes es crea si encara no hi es (idempotent).
(deffunction dep-resultat (?fet)
  (bind ?rel (fact-relation ?fet))
  (bind ?vars (vars-del-goal))
  (bind ?nom-op nil)
  (if (eq ?rel operador) then (bind ?nom-op (fact-slot-value ?fet nom)))
  (bind ?txt (str-cat "(" ?rel))
  (progn$ (?sl (fact-slot-names ?fet))
    (bind ?v (fact-slot-value ?fet ?sl))
    (if (not (and (eq ?sl valor) (eq ?v 0)))
     then (bind ?txt (str-cat ?txt " (" ?sl " " (valor-accio ?sl ?v ?vars ?nom-op) ")"))))
  (bind ?txt (str-cat ?txt ")"))
  (if (eq ?rel operador)
   then (afegeix-dependencia accio
          (str-cat "(if (not (any-factp ((?o operador)) (and (eq ?o:sector ?s) (eq ?o:cicle ?c) (eq ?o:nom "
                   ?nom-op ")))) then (assert " ?txt "))") (create$))
   else (afegeix-dependencia accio (str-cat "(assert " ?txt ")") (create$)))
  ; guarda: el chunk no es torna a disparar si el resultat ja hi es
  (if (eq ?rel preferencia) then
     (bind ?g (str-cat "(not (preferencia (sector ?s) (cicle ?c) (op " (fact-slot-value ?fet op)
                       ") (tipus " (fact-slot-value ?fet tipus) ")"))
     (if (neq (fact-slot-value ?fet op2) cap) then
        (bind ?g (str-cat ?g " (op2 " (fact-slot-value ?fet op2) ")")))
     (afegeix-dependencia negacio (str-cat ?g "))") (create$)))
  TRUE)

; Cadena de prioritats entre dos objectius (fets prioritat, per transitivitat).
(deffunction cadena-prioritat (?a ?b)
  (bind ?res (create$))
  (do-for-all-facts ((?p prioritat)) (and (eq ?p:major ?a) (= (length$ ?res) 0))
    (if (eq ?p:menor ?b) then (bind ?res (create$ ?p))
     else (bind ?sub (cadena-prioritat ?p:menor ?b))
          (if (> (length$ ?sub) 0) then (bind ?res (create$ ?p ?sub)))))
  ?res)

; --- construccio del chunk --------------------------------------------------

(deffunction junta-dependencies (?tipus)
  (bind ?r "")
  (loop-for-count (?k 1 ?*ordre*)
    (do-for-fact ((?d dependencia))
        (and (eq ?d:goal ?*goal*) (eq ?d:tipus ?tipus) (= ?d:ordre ?k))
      (bind ?r (str-cat ?r " " ?d:text))))
  ?r)

(deffunction nom-nou-chunk ()
  (bind ?max 0)
  (progn$ (?r (get-defrule-list DELIBERACIO))
    (bind ?n (str-cat ?r))
    (if (eq (str-index "chunk-" ?n) 1) then
       (bind ?k (string-to-field (sub-string 7 (str-length ?n) ?n)))
       (if (and (integerp ?k) (> ?k ?max)) then (bind ?max ?k))))
  (do-for-all-facts ((?f fragment-apres)) TRUE
    (bind ?n (str-cat ?f:nom))
    (bind ?k (string-to-field (sub-string 7 (str-length ?n) ?n)))
    (if (and (integerp ?k) (> ?k ?max)) then (bind ?max ?k)))
  (sym-cat chunk- (+ ?max 1)))

(deffunction desa-fragment (?nom ?impas ?c ?descr ?codi ?sig)
  (if (eq ?*fitxer-chunks* "") then (return FALSE))
  (if (not (open ?*fitxer-chunks* chk-w "a")) then
     (printout t "[CHUNKING] No es pot escriure a " ?*fitxer-chunks* crlf)
     (return FALSE))
  (printout chk-w "(fragment-apres (nom " ?nom ") (impas-origen " ?impas ") (cicle " ?c
                  ") (descripcio \"" (escapa ?descr) "\") (codi \"" (escapa ?codi)
                  "\") (signatura \"" (escapa ?sig) "\"))" crlf)
  (close chk-w)
  TRUE)

(deffunction crea-chunk (?impas ?descr)
  (if (not ?*chunking*) then
     (do-for-all-facts ((?d dependencia)) (eq ?d:goal ?*goal*) (retract ?d))
     (return FALSE))
  (bind ?s ?*ctx-s*)
  (bind ?c ?*ctx-c*)
  (bind ?lhs (str-cat " (fase (nom avaluacio)) (cicle (numero ?c))"
                      (junta-dependencies positiva)
                      (junta-dependencies test)
                      (junta-dependencies negacio)))
  (bind ?accions (junta-dependencies accio))
  (bind ?sig (str-cat ?lhs " =>" ?accions))
  (bind ?existent (find-fact ((?f fragment-apres)) (eq ?f:signatura ?sig)))
  (if (> (length$ ?existent) 0) then
     (bind ?nom (fact-slot-value (nth$ 1 ?existent) nom))
     (printout t "[CHUNKING] Ja existeix " ?nom " per a aquesta situacio; no se'n crea cap de nou." crlf)
     (do-for-all-facts ((?d dependencia)) (eq ?d:goal ?*goal*) (retract ?d))
     (return ?nom))
  (bind ?nom (nom-nou-chunk))
  (bind ?codi
    (substitueix
      (str-cat "(defrule DELIBERACIO::%NOM% (declare (auto-focus TRUE))" ?lhs " =>"
               " (printout t \"[%NOM%] \" ?s \": " ?descr ".\" crlf)" ?accions
               " (assert (traca (pas ?c) (fase avaluacio) (missatge (str-cat ?s \": %NOM% aplicat\")))))")
      "%NOM%" (str-cat ?nom)))
  (if (not (build ?codi)) then
     (printout t "[CHUNKING] No s'ha pogut construir " ?nom ": " ?codi crlf)
     (return FALSE))
  (assert (fragment-apres (nom ?nom) (impas-origen ?impas) (cicle ?c)
                          (descripcio ?descr) (codi ?codi) (signatura ?sig)))
  (desa-fragment ?nom ?impas ?c ?descr ?codi ?sig)
  (printout t "[CHUNKING] Nova regla " ?nom ": " ?descr "." crlf)
  (do-for-all-facts ((?d dependencia)) (eq ?d:goal ?*goal*) (retract ?d))
  ?nom)

; --- persistencia ------------------------------------------------------------

; Llegeix el fitxer, elimina duplicats (mateixa signatura), resol col.lisions de
; nom i reconstrueix les regles que encara no existeixen. Retorna quantes en construeix.
(deffunction carrega-chunks (?fitxer)
  (if (not (open ?fitxer chk-r "r")) then (return 0))
  (close chk-r)
  (bind ?m (set-current-module DOMINI))
  (load-facts ?fitxer)
  (set-current-module ?m)
  (bind ?n 0)
  (progn$ (?fr (find-all-facts ((?x fragment-apres)) TRUE))
    (if (fact-existp ?fr) then
      (bind ?f ?fr)
      (bind ?idx (fact-index ?f))
      (bind ?sig (fact-slot-value ?f signatura))
      (bind ?nom (fact-slot-value ?f nom))
      (if (any-factp ((?o fragment-apres)) (and (< (fact-index ?o) ?idx) (eq ?o:signatura ?sig)))
       then (retract ?f)
       else
        (if (any-factp ((?o fragment-apres)) (and (< (fact-index ?o) ?idx) (eq ?o:nom ?nom)))
         then (bind ?nou (nom-nou-chunk))
              (bind ?codi (substitueix (fact-slot-value ?f codi) (str-cat "DELIBERACIO::" ?nom " ")
                                       (str-cat "DELIBERACIO::" ?nou " ")))
              (bind ?codi (substitueix ?codi (str-cat "[" ?nom "]") (str-cat "[" ?nou "]")))
              (bind ?codi (substitueix ?codi (str-cat ": " ?nom " aplicat") (str-cat ": " ?nou " aplicat")))
              (bind ?f (modify ?f (nom ?nou) (codi ?codi)))
              (bind ?nom ?nou))
        (if (not (member$ ?nom (get-defrule-list DELIBERACIO))) then
           (if (build (fact-slot-value ?f codi))
            then (bind ?n (+ ?n 1))
            else (printout t "[CHUNKING] No s'ha pogut reconstruir " ?nom crlf))))))
  (printout t "[CHUNKING] Carregats " ?n " chunks de " ?fitxer "." crlf)
  ?n)

(deffunction activa-persistencia (?fitxer)
  (bind ?*fitxer-chunks* ?fitxer)
  (carrega-chunks ?fitxer))

