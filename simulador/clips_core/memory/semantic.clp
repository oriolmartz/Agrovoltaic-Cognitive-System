(defmodule SEMANTICA
  (import DOMINI ?ALL)
  (import MEMORIA deffunction ?ALL)
  (import APRENENTATGE deffunction ?ALL)
  (export deffunction ?ALL))

;  MEMORIA SEMANTICA PER CONSOLIDACIO -------------------------------------------
; La memoria episodica guarda QUE VA PASSAR i QUAN; aquest modul en treu el que se
; SAP independentment de quan es va aprendre: per a cada (sector, situacio, operador),
; quantes vegades ha anat be, neutre o malament (smem-resum).
;
; D'on surt cada peca:
;   - Episodis -> coneixement general: "La consolidacio transforma episodis en
;     coneixement mes general" i "consolidar experiencies repetides"
;     (Arquitectures Cognitives INTRO, diap. 51 i 78); "Resums de memoria episodica
;     i creacio d'abstraccions semantiques" (Arquitectura SOAR, diap. 45).
;   - Que sigui semantica: es coneixement independent del moment (Laird 2022, sec. 6-7).
;   - Que la desi una regla: Soar no te aprenentatge automatic de la memoria semantica,
;     pero l'agent hi pot desar deliberadament (Laird 2022, sec. 6).
;   - Prudencia (minim-casos i k): "Consolidar episodis en coneixement semantic sense
;     introduir falsedats" (Arquitectura SOAR, diap. 54 i 57).
;   - Consulta per patro (Rete) i no recorrent el magatzem (Arquitectura SOAR, diap. 24).
;   - Finestra i arxiu: decisio NOSTRA. Soar no oblida episodis (Laird 2022, sec. 7);
;     aqui surten de la memoria de treball pero es conserven al fitxer d'arxiu.
;
; Cicle de vida:
;   proposta    : smem-situacio-actual calcula la clau de la situacio de cada sector;
;                 la valoracio de l'episodi anterior (MEMORIA) dispara la consolidacio
;   avaluacio   : DELIBERACIO::avalua-memoria-semantica fa servir el resum si n >= minim;
;                 si no, es consulta la memoria episodica com abans (avalua-memoria-consulta)
;   proposta    : smem-arxiva treu de la MT els episodis consolidats fora de la finestra

(deffacts smem-inicial
  (smem-config))

; Interficie per a l'usuari i el pont Python (com activa-reforc, epmem-aprenentatge).
(deffunction smem-configura (?actiu ?finestra ?arxiu)
  (do-for-all-facts ((?k smem-config)) TRUE
    (modify ?k (actiu ?actiu) (finestra ?finestra) (arxiu ?arxiu)))
  ?actiu)

; Afegeix un episodi al fitxer d'arxiu, en format de load-facts.
(deffunction smem-escriu-arxiu (?fitxer ?e)
  (if (not (open ?fitxer smem-arx "a")) then
     (printout t "[SMEM] No es pot escriure a " ?fitxer crlf)
     (return FALSE))
  (printout smem-arx "(epmem-episodi")
  (progn$ (?sl (fact-slot-names ?e))
    (printout smem-arx " (" ?sl " " (text-constant (fact-slot-value ?e ?sl)) ")"))
  (printout smem-arx ")" crlf)
  (close smem-arx)
  TRUE)

; 1. Clau de la situacio actual (els riscos del cicle ja estan elaborats a proposta).
(defrule smem-situacio-actual
  (declare (auto-focus TRUE))
  (smem-config (actiu on))
  (fase (nom proposta))
  (cicle (numero ?c))
  (sector (id ?s))
  (not (smem-situacio (sector ?s) (cicle ?c)))
  =>
  (assert (smem-situacio (sector ?s) (cicle ?c) (clau (epmem-clau-situacio ?s ?c)))))

; 2. CONSOLIDACIO: cada episodi valorat suma una vegada al seu resum.
(defrule smem-consolida-nou
  (declare (auto-focus TRUE))
  (smem-config (actiu on))
  ?e <- (epmem-episodi (cicle ?ec) (sector ?s) (operador ?op) (valoracio ?v&~pendent)
                       (consolidat no) (clau $?k&:(> (length$ ?k) 0)))
  (not (smem-resum (sector ?s) (operador ?op) (situacio $?k)))
  =>
  (assert (smem-resum (sector ?s) (operador ?op) (situacio ?k) (n 1) (darrer-cicle ?ec)
                      (bona (if (eq ?v bona) then 1 else 0))
                      (neutra (if (eq ?v neutra) then 1 else 0))
                      (dolenta (if (eq ?v dolenta) then 1 else 0))))
  (modify ?e (consolidat si)))

(defrule smem-consolida
  (declare (auto-focus TRUE))
  (smem-config (actiu on))
  ?e <- (epmem-episodi (cicle ?ec) (sector ?s) (operador ?op) (valoracio ?v&~pendent)
                       (consolidat no) (clau $?k&:(> (length$ ?k) 0)))
  ?r <- (smem-resum (sector ?s) (operador ?op) (situacio $?k)
                    (bona ?b) (neutra ?nt) (dolenta ?d) (n ?n))
  =>
  (modify ?r (n (+ ?n 1)) (darrer-cicle ?ec)
             (bona (+ ?b (if (eq ?v bona) then 1 else 0)))
             (neutra (+ ?nt (if (eq ?v neutra) then 1 else 0)))
             (dolenta (+ ?d (if (eq ?v dolenta) then 1 else 0))))
  (modify ?e (consolidat si)))

; 3. ARXIU: els episodis ja consolidats i fora de la finestra surten de la memoria de
;    treball (i, si hi ha fitxer, s'hi afegeixen). El que ensenyaven ja es al resum.
;    A proposta i no a monitoratge: alla tanca-cicle (auto-focus) pot tancar la fase abans.
(defrule smem-arxiva
  (declare (auto-focus TRUE))
  (smem-config (actiu on) (finestra ?w&:(> ?w 0)) (arxiu ?fx))
  (fase (nom proposta))
  (cicle (numero ?c))
  ?e <- (epmem-episodi (cicle ?ec&:(<= ?ec (- ?c ?w))) (consolidat si))
  =>
  (if (neq ?fx "") then (smem-escriu-arxiu ?fx ?e))
  (epmem-idx-invalida)              ; l'index de la memoria episodica es reconstruira
  (retract ?e))

; Que s'ha consolidat (equivalent a epmem-informe).
(deffunction smem-informe ()
  (printout t crlf "[SMEM] " (length$ (find-all-facts ((?r smem-resum)) TRUE)) " resums." crlf)
  (do-for-all-facts ((?r smem-resum)) TRUE
    (printout t "   " ?r:sector " " ?r:operador " " ?r:situacio ": " ?r:bona " bona, "
                ?r:neutra " neutra, " ?r:dolenta " dolenta" crlf))
  TRUE)
