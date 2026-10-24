(defmodule DECISIO
  (import DOMINI ?ALL)
  (import DELIBERACIO deffunction ?ALL)
  (import REFORC deffunction ?ALL)
  (export ?ALL))

;  DECISIO -------------------------------------------------------------------
; Fase seleccio. Procediment de decisio, per a cada sector:
;   1. es descarten els operadors amb rebuig (restriccions dures);
;   2. si falten dades critiques i ningu ha dit que fer -> impasse dades-insuficients;
;   3. si no queda cap candidat -> impasse sense-canvi;
;   4. es tria el de mes puntuacio; si n'hi ha dos d'empatats -> impasse empat,
;      llevat que una preferencia millor-que ja desfaci l'empat.

(defrule descarta-rebutjat
  (declare (auto-focus TRUE))
  (fase (nom seleccio))
  (cicle (numero ?c))
  ?o <- (operador (sector ?s) (cicle ?c) (nom ?op) (estat proposat))
  (preferencia (sector ?s) (cicle ?c) (op ?op) (tipus rebuig) (font ?f))
  (not (preferencia (sector ?s) (cicle ?c) (op ?op) (tipus requerida)))
  =>
  (printout t "[SELECCIO] " ?s ": " ?op " queda descartat (" ?f ")." crlf)
  (modify ?o (estat rebutjat)))

(defrule detecta-impas-dades
  (declare (auto-focus TRUE))
  (fase (nom seleccio))
  (cicle (numero ?c))
  (risc (sector ?s) (cicle ?c) (tipus dades) (nivell critic))
  (not (preferencia (sector ?s) (cicle ?c) (tipus requerida)))
  (not (operador-seleccionat (sector ?s) (cicle ?c)))
  (not (impas (sector ?s) (cicle ?c)))
  =>
  (printout t crlf "[SELECCIO] " ?s ": IMPAS DE DADES INSUFICIENTS. Sense lectura fiable de vent "
              "no es pot saber si moure el panell es segur." crlf)
  (assert (impas (tipus dades-insuficients) (sector ?s) (cicle ?c)
                 (operadors sollicitar-dades mantenir-posicio)
                 (rao "falten dades critiques per garantir la seguretat")))
  (assert (subobjectiu (id (sym-cat G- ?s - ?c)) (tipus resoldre-dades) (sector ?s) (estat actiu)))
  (assert (traca (pas ?c) (fase seleccio)
                 (missatge (str-cat ?s ": impasse de dades insuficients")))))

(defrule detecta-impas-sense-candidat
  (declare (auto-focus TRUE))
  (fase (nom seleccio))
  (cicle (numero ?c))
  (sector (id ?s))
  (not (operador (sector ?s) (cicle ?c) (estat proposat)))
  (not (operador-seleccionat (sector ?s) (cicle ?c)))
  (not (impas (sector ?s) (cicle ?c)))
  =>
  (printout t crlf "[SELECCIO] " ?s ": IMPAS SENSE CANDIDAT. Totes les opcions s'han descartat." crlf)
  (assert (impas (tipus sense-canvi) (sector ?s) (cicle ?c)
                 (rao "cap operador compleix les restriccions dures")))
  (assert (subobjectiu (id (sym-cat G- ?s - ?c)) (tipus resoldre-sense-candidat) (sector ?s) (estat actiu)))
  (assert (traca (pas ?c) (fase seleccio)
                 (missatge (str-cat ?s ": impasse sense candidat")))))

; Com a Soar, les preferencies numeriques apreses (Q) nomes decideixen entre
; candidats que la resta de coneixement deixa empatats. Si Q no distingeix prou
; (|Qa - Qb| <= epsilon, p. ex. sense experiencia), es dona l'impasse d'empat.
(defrule desfa-empat-per-reforc
  (declare (salience 5) (auto-focus TRUE))
  (fase (nom seleccio))
  (cicle (numero ?c))
  (rl-config (aprenentatge on) (epsilon ?eps))
  (operador (sector ?s) (cicle ?c) (nom ?a) (estat proposat))
  (operador (sector ?s) (cicle ?c) (nom ?b&:(> (str-compare ?b ?a) 0)) (estat proposat))
  (test (= (puntuacio ?s ?a ?c) (puntuacio ?s ?b ?c)))
  (not (and (operador (sector ?s) (cicle ?c) (nom ?x) (estat proposat))
            (test (> (puntuacio ?s ?x ?c) (puntuacio ?s ?a ?c)))))
  (not (preferencia (sector ?s) (cicle ?c) (op ?a) (tipus millor-que) (op2 ?b)))
  (not (preferencia (sector ?s) (cicle ?c) (op ?b) (tipus millor-que) (op2 ?a)))
  (not (and (operador (sector ?s) (cicle ?c) (nom ?r) (estat proposat))
            (preferencia (sector ?s) (cicle ?c) (op ?r) (tipus rebuig))))
  (not (and (risc (sector ?s) (cicle ?c) (tipus dades) (nivell critic))
            (not (preferencia (sector ?s) (cicle ?c) (tipus requerida)))))
  (not (operador-seleccionat (sector ?s) (cicle ?c)))
  (not (impas (sector ?s) (cicle ?c)))
  (test (> (abs (- (rl-valor-op ?s ?a ?c) (rl-valor-op ?s ?b ?c))) ?eps))
  =>
  (bind ?qa (rl-valor-op ?s ?a ?c))
  (bind ?qb (rl-valor-op ?s ?b ?c))
  (if (> ?qa ?qb)
   then (bind ?g ?a) (bind ?p ?b) (bind ?qg ?qa) (bind ?qp ?qb)
   else (bind ?g ?b) (bind ?p ?a) (bind ?qg ?qb) (bind ?qp ?qa))
  (printout t "[SELECCIO] " ?s ": empat entre " ?a " i " ?b " desfet pel reforç: Q("
              ?g ") = " (/ (round (* 100 ?qg)) 100) " > Q(" ?p ") = " (/ (round (* 100 ?qp)) 100) "." crlf)
  (assert (preferencia (op ?g) (sector ?s) (cicle ?c) (tipus millor-que) (op2 ?p) (font RL)))
  (assert (traca (pas ?c) (fase seleccio)
                 (missatge (str-cat ?s ": empat " ?a "/" ?b " desfet pel reforç a favor de " ?g)))))

(defrule detecta-impas-empat
  (declare (auto-focus TRUE))
  (fase (nom seleccio))
  (cicle (numero ?c))
  (operador (sector ?s) (cicle ?c) (nom ?a) (estat proposat))
  (operador (sector ?s) (cicle ?c) (nom ?b&:(> (str-compare ?b ?a) 0)) (estat proposat))
  (test (= (puntuacio ?s ?a ?c) (puntuacio ?s ?b ?c)))
  ; empatats al capdamunt
  (not (and (operador (sector ?s) (cicle ?c) (nom ?x) (estat proposat))
            (test (> (puntuacio ?s ?x ?c) (puntuacio ?s ?a ?c)))))
  ; ningu ha desfet l'empat
  (not (preferencia (sector ?s) (cicle ?c) (op ?a) (tipus millor-que) (op2 ?b)))
  (not (preferencia (sector ?s) (cicle ?c) (op ?b) (tipus millor-que) (op2 ?a)))
  ; abans cal haver descartat els rebutjats i resolt les dades
  (not (and (operador (sector ?s) (cicle ?c) (nom ?r) (estat proposat))
            (preferencia (sector ?s) (cicle ?c) (op ?r) (tipus rebuig))))
  (not (and (risc (sector ?s) (cicle ?c) (tipus dades) (nivell critic))
            (not (preferencia (sector ?s) (cicle ?c) (tipus requerida)))))
  (not (operador-seleccionat (sector ?s) (cicle ?c)))
  (not (impas (sector ?s) (cicle ?c)))
  =>
  (bind ?p (puntuacio ?s ?a ?c))
  (printout t crlf "[SELECCIO] " ?s ": IMPAS D'EMPAT entre " ?a " i " ?b
              " (tots dos " ?p " punts)." crlf)
  (assert (impas (tipus empat) (sector ?s) (cicle ?c) (operadors ?a ?b)
                 (rao (str-cat ?a " i " ?b " tenen la mateixa valoracio (" ?p ")"))))
  (assert (subobjectiu (id (sym-cat G- ?s - ?c)) (tipus resoldre-empat) (sector ?s) (estat actiu)))
  (assert (traca (pas ?c) (fase seleccio)
                 (missatge (str-cat ?s ": impasse d'empat entre " ?a " i " ?b)))))

(defrule selecciona-operador
  (declare (auto-focus TRUE))
  (fase (nom seleccio))
  (cicle (numero ?c))
  ?o <- (operador (sector ?s) (cicle ?c) (nom ?op) (estat proposat))
  ; ningu el supera
  (not (and (operador (sector ?s) (cicle ?c) (nom ?x&~?op) (estat proposat))
            (test (> (puntuacio ?s ?x ?c) (puntuacio ?s ?op ?c)))))
  ; si algu l'iguala, hi ha d'haver una preferencia que el prefereixi
  (not (and (operador (sector ?s) (cicle ?c) (nom ?x&~?op) (estat proposat))
            (test (= (puntuacio ?s ?x ?c) (puntuacio ?s ?op ?c)))
            (not (preferencia (sector ?s) (cicle ?c) (op ?op) (tipus millor-que) (op2 ?x)))))
  (not (and (operador (sector ?s) (cicle ?c) (nom ?r) (estat proposat))
            (preferencia (sector ?s) (cicle ?c) (op ?r) (tipus rebuig))
            (not (preferencia (sector ?s) (cicle ?c) (op ?r) (tipus requerida)))))
  (not (and (risc (sector ?s) (cicle ?c) (tipus dades) (nivell critic))
            (not (preferencia (sector ?s) (cicle ?c) (tipus requerida)))))
  (not (operador-seleccionat (sector ?s) (cicle ?c)))
  (not (impas (sector ?s) (cicle ?c)))
  =>
  (bind ?p (puntuacio ?s ?op ?c))
  ; el criteri que ha decidit, per a l'explicacio
  (bind ?motiu (str-cat "maxima valoracio (" ?p " punts)"))
  (if (and (not (any-factp ((?x operador)) (and (eq ?x:sector ?s) (eq ?x:cicle ?c)
                                                (neq ?x:nom ?op) (neq ?x:estat rebutjat))))
           (any-factp ((?x operador)) (and (eq ?x:sector ?s) (eq ?x:cicle ?c) (eq ?x:estat rebutjat))))
   then (bind ?motiu "unica opcio que compleix les restriccions dures"))
  (do-for-fact ((?pr preferencia))
      (and (eq ?pr:sector ?s) (eq ?pr:cicle ?c) (eq ?pr:op ?op) (eq ?pr:tipus millor-que)
           ; nomes si hi havia empat de veritat amb ?pr:op2
           (any-factp ((?x operador)) (and (eq ?x:sector ?s) (eq ?x:cicle ?c)
                                           (eq ?x:nom ?pr:op2) (eq ?x:estat proposat)
                                           (= (puntuacio ?s ?pr:op2 ?c) ?p))))
    (bind ?motiu (str-cat "empat amb " ?pr:op2 " desfet per " ?pr:font)))
  (do-for-fact ((?pr preferencia))
      (and (eq ?pr:sector ?s) (eq ?pr:cicle ?c) (eq ?pr:op ?op) (eq ?pr:tipus requerida))
    (bind ?motiu (str-cat "preferencia requerida (" ?pr:font ")")))
  (printout t "[SELECCIO] " ?s ": es selecciona " ?op ". Criteri: " ?motiu "." crlf)
  (modify ?o (estat seleccionat))
  (assert (operador-seleccionat (sector ?s) (cicle ?c) (nom ?op) (motiu ?motiu)))
  (assert (traca (pas ?c) (fase seleccio)
                 (missatge (str-cat ?s ": seleccionat " ?op ", " ?motiu)))))

; --- v1_9: SELECCIO del reg ---------------------------------------------------------
; Mateix procediment que el panell: es descarten els rebutjats i es tria la valoracio mes
; alta. Si dos operadors empaten, guanya el que gasta menys aigua (objectiu estalvi-aigua);
; per aixo el reg no te impasses.

(defrule descarta-reg-rebutjat
  (declare (auto-focus TRUE))
  (fase (nom seleccio))
  (cicle (numero ?c))
  ?o <- (operador-reg (sector ?s) (cicle ?c) (nom ?op) (estat proposat))
  (preferencia-reg (sector ?s) (cicle ?c) (op ?op) (tipus rebuig) (font ?f))
  =>
  (printout t "[SELECCIO] " ?s ": " ?op " queda descartat (" ?f ")." crlf)
  (modify ?o (estat rebutjat)))

(defrule selecciona-reg
  (declare (auto-focus TRUE))
  (fase (nom seleccio))
  (cicle (numero ?c))
  ?o <- (operador-reg (sector ?s) (cicle ?c) (nom ?op) (dosi ?d) (estat proposat))
  ; abans cal haver descartat els rebutjats
  (not (and (operador-reg (sector ?s) (cicle ?c) (nom ?r) (estat proposat))
            (preferencia-reg (sector ?s) (cicle ?c) (op ?r) (tipus rebuig))))
  ; ningu el supera
  (not (and (operador-reg (sector ?s) (cicle ?c) (nom ?x&~?op) (estat proposat))
            (test (> (puntuacio-reg ?s ?x ?c) (puntuacio-reg ?s ?op ?c)))))
  ; si algu l'iguala, ha de gastar mes aigua
  (not (and (operador-reg (sector ?s) (cicle ?c) (nom ?x&~?op) (dosi ?dx&:(< ?dx ?d)) (estat proposat))
            (test (= (puntuacio-reg ?s ?x ?c) (puntuacio-reg ?s ?op ?c)))))
  (not (reg-seleccionat (sector ?s) (cicle ?c)))
  =>
  (bind ?p (puntuacio-reg ?s ?op ?c))
  (bind ?motiu (str-cat "maxima valoracio (" ?p " punts)"))
  (do-for-fact ((?x operador-reg))
      (and (eq ?x:sector ?s) (eq ?x:cicle ?c) (neq ?x:nom ?op) (eq ?x:estat proposat)
           (= (puntuacio-reg ?s ?x:nom ?c) ?p))
    (bind ?motiu (str-cat "empat amb " ?x:nom " (" ?p " punts) desfet per estalvi d'aigua")))
  (if (and (not (any-factp ((?x operador-reg)) (and (eq ?x:sector ?s) (eq ?x:cicle ?c)
                                                    (neq ?x:nom ?op) (eq ?x:estat proposat))))
           (any-factp ((?x operador-reg)) (and (eq ?x:sector ?s) (eq ?x:cicle ?c) (eq ?x:estat rebutjat))))
   then (bind ?motiu "unica opcio que compleix les restriccions dures"))
  (printout t "[SELECCIO] " ?s ": reg " ?op ". Criteri: " ?motiu "." crlf)
  (modify ?o (estat seleccionat))
  (assert (reg-seleccionat (sector ?s) (cicle ?c) (nom ?op) (dosi ?d) (motiu ?motiu)))
  (assert (traca (pas ?c) (fase seleccio)
                 (missatge (str-cat ?s ": reg " ?op ", " ?motiu)))))

(defrule seleccio-a-impas
  (declare (salience -10) (auto-focus TRUE))
  ?f <- (fase (nom seleccio))
  (exists (impas))
  =>
  (printout t "[SELECCIO -> IMPAS]" crlf)
  (retract ?f)
  (assert (fase (nom impas))))

(defrule seleccio-a-aplicacio
  (declare (salience -10) (auto-focus TRUE))
  ?f <- (fase (nom seleccio))
  (cicle (numero ?c))
  (not (impas))
  (not (and (sector (id ?s)) (not (operador-seleccionat (sector ?s) (cicle ?c)))))
  =>
  (printout t "[SELECCIO -> APLICACIO]" crlf)
  (retract ?f)
  (assert (fase (nom aplicacio))))


