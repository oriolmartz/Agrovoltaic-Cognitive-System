;  DOMINI --------------------------------------------------------------------
(defmodule DOMINI
  (export deftemplate ?ALL))

; CONTRACTE DE MEMORIA DE TREBALL
; La memoria de treball distingeix explicitament les cinc families exigides:
;
; 1) OBSERVATS / INPUT EXTERN
;    energia, observacio, prediccio, estat-sensor
;    Origen: simulador, sensors o servei de prediccio.
;    Persistencia: normalment un cicle.
;    Modifica: capa d'entrada / simulador.
;
; 2) DERIVATS
;    risc
;    Origen: regles d'elaboracio.
;    Persistencia: cicle actual.
;    Modifica: modul DELIBERACIO durant elaboracio/percepcio.
;
; 3) CONTROL
;    fase, cicle, objectiu, prioritat, conflicte, activa, impas, subobjectiu
;    Origen: arquitectura cognitiva i coneixement de control.
;    Persistencia: fase/cicle, excepte coneixement estatic (prioritat/conflicte/activa).
;    Modifica: regles de transicio, DECISIO i IMPAS segons el cas.
;
; 4) CANDIDATS D'ACCIO
;    operador, preferencia
;    Origen: regles de proposta, avaluacio i deliberacio.
;    Persistencia: fins a completar la decisio del cicle.
;    Modifica: DELIBERACIO, DECISIO i IMPAS.
;
; 5) RESULTATS / HISTORIC
;    operador-seleccionat, ordre-actuador, explicacio, episodi, traca,
;    fragment-apres
;    Origen: seleccio, aplicacio, explicacio, monitoratge i chunking.
;    Persistencia: resultats del cicle; episodi i fragment-apres son persistents.
;    Modifica: DECISIO, ACCIO i IMPAS.
;
; A mes, sector, cultiu, llindars-cultiu i panell son coneixement/estat del domini
; que dona context a les cinc families anteriors.


; CONTROL | Origen: arquitectura | Persistencia: fins al canvi de fase | Modifica: regles de transicio
; Fase actual del cicle de decisió. N'hi ha una sola en tot moment.
(deftemplate fase
  (slot nom (type SYMBOL)))

; CONTROL | Origen: arquitectura/simulador | Persistencia: global | Modifica: tanca-cicle
; Cicle de decisió actual (pas de temps del simulador).
(deftemplate cicle
  (slot numero (type INTEGER) (default 1)))

; RESULTAT/HISTORIC | Origen: totes les fases | Persistencia: persistent per traçabilitat
; Missatge de traça: què ha passat, en quin pas i en quina fase.
(deftemplate traca
  (slot pas (type INTEGER) (default 0))
  (slot fase (type SYMBOL))
  (slot missatge (type STRING)))

; Sector de la planta i el cultiu que hi ha.         Ontologia: Sector, te_cultiu
(deftemplate sector
  (slot id (type SYMBOL))
  (slot cultiu (type SYMBOL)))

; Cultiu concret d'un sector.                         Ontologia: Cultiu + Estat_Cultiu
(deftemplate cultiu
  (slot id (type SYMBOL))
  (slot tipus (allowed-symbols tomaquet enciam vinya))
  ; fase fenològica (desconeguda si no s'informa)
  (slot fase (allowed-symbols desconeguda vegetativa floracio fructificacio maduracio repos))
  (slot sensibilitat (allowed-symbols baix mitja alt critic)))

; Llindars agronòmics per tipus de cultiu.            Ontologia: restriccions hasValue de cada classe
(deftemplate llindars-cultiu
  (slot tipus (allowed-symbols tomaquet enciam vinya))
  (slot temp-optima-min (type FLOAT))     
  (slot temp-optima-max (type FLOAT))       
  (slot temp-absoluta-min (type FLOAT))    
  (slot temp-absoluta-max (type FLOAT))     
  (slot fraccio-esgotament-p (type FLOAT) (range 0.0 1.0))  ; aigua esgotable sense estrès
  (slot radiacio-optima-max (type FLOAT))   
  (slot radiacio-estres (type FLOAT)))

; Panell: estat actual i límits mecànics.
;                                                     Ontologia: Panell + Estat_Panell
(deftemplate panell
  (slot id (type SYMBOL))
  (slot sector (type SYMBOL))
  ; estat (el comunica el controlador del panell a cada cicle)
  (slot angle (type FLOAT))                   ; angle actual
  (slot angle-optim-produccio (type FLOAT))   ; angle de màxima captació
  (slot angle-ombra (type FLOAT) (default 0.0)) ; angle que fa més ombra al cultiu
  (slot disponible (allowed-symbols si no))
  (slot estat-mecanic (allowed-symbols normal degradat avariat))
  ; límits mecànics 
  (slot angle-minim (type FLOAT) (default -55.0))
  (slot angle-maxim (type FLOAT) (default 55.0))
  (slot angle-seguretat (type FLOAT) (default 0.0))
  (slot vent-avis (type FLOAT) (default 12.0))        ; m/s, risc mecànic alt
  (slot vent-maxim (type FLOAT) (default 16.0))       ; m/s, risc mecànic crític
  (slot tolerancia-angle (type FLOAT) (default 2.0)))

; FETS OBSERVATS / INPUT EXTERN

; OBSERVAT | Origen: simulador | Persistencia: 1 cicle | Modifica: capa d'entrada
; Producció i demanda d'energia d'un sector.          Ontologia: Estat_Energia
; La demanda és la quota de la demanda de la planta assignada al sector.
(deftemplate energia
  (slot sector (type SYMBOL))
  (slot cicle (type INTEGER))
  (slot produccio-actual (type FLOAT))   ; kW
  (slot demanda (type FLOAT)))           ; kW

; OBSERVAT | Origen: sensors/simulador | Persistencia: 1 cicle | Modifica: capa d'entrada
; Lectures dels sensors d'un sector en un cicle.      Ontologia: Observacio_*
; Una lectura que no arriba = 'absent' (dades insuficients).
(deftemplate observacio
  (slot sector (type SYMBOL))
  (slot cicle (type INTEGER))
  (slot radiacio (type NUMBER SYMBOL) (allowed-symbols absent) (default absent))            ; W/m²
  (slot temperatura-aire (type NUMBER SYMBOL) (allowed-symbols absent) (default absent))    ; °C
  (slot temperatura-cultiu (type NUMBER SYMBOL) (allowed-symbols absent) (default absent))  ; °C
  (slot humitat-sol (type NUMBER SYMBOL) (allowed-symbols absent) (default absent))         ; % aigua disponible
  (slot vent (type NUMBER SYMBOL) (allowed-symbols absent) (default absent))                ; m/s
  (slot pluja (type NUMBER SYMBOL) (allowed-symbols absent) (default absent)))              ; mm

; OBSERVAT/INPUT EXTERN | Origen: servei de prediccio/simulador | Persistencia: 1 cicle | Modifica: capa d'entrada
; Prediccio a curt termini, separada de les lectures observades. Ontologia: Prediccio_*
(deftemplate prediccio
  (slot sector (type SYMBOL))
  (slot cicle (type INTEGER))
  (slot radiacio (type NUMBER SYMBOL) (allowed-symbols absent) (default absent))
  (slot temperatura (type NUMBER SYMBOL) (allowed-symbols absent) (default absent))
  (slot vent (type NUMBER SYMBOL) (allowed-symbols absent) (default absent))
  (slot pluja (type NUMBER SYMBOL) (allowed-symbols absent) (default absent)))

; OBSERVAT | Origen: diagnostica/simulador | Persistencia: fins a nova lectura | Modifica: capa d'entrada
; Estat d'un sensor.                                  Ontologia: Estat_Sensor
(deftemplate estat-sensor
  (slot sector (type SYMBOL))
  (slot tipus (allowed-symbols humitat-sol pluja radiacio temperatura-aire temperatura-cultiu vent))
  (slot operatiu (allowed-symbols si no))
  (slot qualitat (allowed-symbols valida absent incoherent))
  (slot cicle-ultima-lectura (type INTEGER)))

; FETS DERIVATS (elaboració)

; DERIVAT | Origen: percepcio/elaboracio | Persistencia: 1 cicle | Modifica: DELIBERACIO
; Risc detectat en un sector.                         Ontologia: Risc i subclasses
(deftemplate risc
  (slot sector (type SYMBOL))
  (slot cicle (type INTEGER))
  (slot tipus (allowed-symbols mecanic fallada-actuador dades
                               estres-hidric exces-radiacio temperatura meteorologic-advers))
  (slot nivell (allowed-symbols baix mitja alt critic))
  (slot font (type SYMBOL)))   ; regla que l'ha detectat (traçabilitat)

; FETS DE CONTROL / CONEIXEMENT DE CONTROL
; OBJECTIUS (coneixement de control estàtic)

; Objectiu del sistema.                               Ontologia: Objectiu i individus Obj_*
; dura: genera rebuig/prohibició; tova: genera preferència numèrica.
(deftemplate objectiu
  (slot id (type SYMBOL))
  (slot tipus (allowed-symbols seguretat produccio-cultiu produccio-energia
                               estabilitat minimitzar-moviment))
  (slot restriccio (allowed-symbols dura tova))
  (slot estat (allowed-symbols inactiu actiu)))

; L'objectiu 'major' preval sobre el 'menor'.         Ontologia: te_prioritat (transitiva)
(deftemplate prioritat
  (slot major (type SYMBOL))
  (slot menor (type SYMBOL)))

; Dos objectius que entren en conflicte.              Ontologia: entra_conflicte (simètrica)
(deftemplate conflicte
  (slot objectiu-1 (type SYMBOL))
  (slot objectiu-2 (type SYMBOL)))

; Quin tipus de risc activa quin objectiu.            Ontologia: activa (hasValue)
(deftemplate activa
  (slot tipus-risc (allowed-symbols mecanic fallada-actuador dades
                                    estres-hidric exces-radiacio temperatura meteorologic-advers))
  (slot objectiu (type SYMBOL)))



; CANDIDATS D'ACCIO + CONTROL D'IMPASSES + APRENENTATGE
; ARQUITECTURA SOAR: operadors, preferències, impasses i aprenentatge
; CANDIDAT D'ACCIO | Origen: PROPOSTA | Persistencia: fins a decisio | Modifica: PROPOSTA/DECISIO/ACCIO
; Operador candidat per a un sector.
(deftemplate operador
  (slot id (type SYMBOL))
  (slot cicle (type INTEGER))
  (slot sector (type SYMBOL))
  (slot nom (allowed-symbols orientar-produccio orientar-ombra posicio-seguretat
                             mantenir-posicio sollicitar-dades))
  (slot angle-objectiu (type NUMBER) (default 0))
  (slot estat (allowed-symbols proposat rebutjat seleccionat aplicat)))

; CANDIDAT D'ACCIO | Origen: AVALUACIO/IMPAS/chunks | Persistencia: decisio actual | Modifica: DELIBERACIO/IMPAS
; Preferència sobre un operador (equivalent a les preferències de SOAR).
;   acceptable: és candidat          rebuig / prohibida: restricció dura
;   requerida: s'ha de triar         millor / pitjor: qualificació extrema
;   millor-que / pitjor-que: respecte d'op2
;   indiferent: sense criteri         numerica: valor numèric (objectius tous)
(deftemplate preferencia
  (slot op (type SYMBOL))                 ; nom de l'operador
  (slot sector (type SYMBOL))
  (slot cicle (type INTEGER))
  (slot tipus (allowed-symbols acceptable rebuig prohibida requerida millor pitjor
                               millor-que pitjor-que indiferent numerica))
  (slot op2 (type SYMBOL) (default cap))  ; només per a millor-que / pitjor-que / indiferent
  (slot valor (type NUMBER) (default 0))
  (slot font (type SYMBOL)))              ; regla que l'ha generada

; RESULTAT | Origen: SELECCIO | Persistencia: 1 cicle | Modifica: DECISIO
; Operador que ha guanyat la decisió en un sector.
(deftemplate operador-seleccionat
  (slot sector (type SYMBOL))
  (slot cicle (type INTEGER))
  (slot nom (type SYMBOL))
  (slot motiu (type STRING) (default "")))   ; criteri que ha decidit

; CONTROL | Origen: SELECCIO | Persistencia: fins a resoldre'l | Modifica: DECISIO/IMPAS
; Impasse: el coneixement immediat no permet decidir.
(deftemplate impas
  (slot tipus (allowed-symbols empat sense-canvi dades-insuficients conflicte restriccio-fallida))
  (slot sector (type SYMBOL))
  (slot cicle (type INTEGER))
  (multislot operadors)                   ; operadors involucrats
  (slot rao (type STRING)))

; CONTROL | Origen: SELECCIO | Persistencia: durant deliberacio | Modifica: IMPAS
; Subobjectiu creat per resoldre un impasse (equivalent al subestat de SOAR).
(deftemplate subobjectiu
  (slot id (type SYMBOL))
  (slot tipus (type SYMBOL))
  (slot sector (type SYMBOL))
  (slot estat (allowed-symbols actiu resolt)))

; RESULTAT/APRENENTATGE | Origen: chunking | Persistencia: persistent | Modifica: IMPAS
; Fragment après per chunking.
(deftemplate fragment-apres
  (slot nom (type SYMBOL))
  (slot impas-origen (type SYMBOL))       ; tipus d'impasse que l'ha originat
  (slot cicle (type INTEGER)))            ; cicle en què s'ha après


; RESULTATS / HISTORIC
; RESULTAT | Origen: APLICACIO | Persistencia: fins que el simulador consumeix l'ordre | Modifica: ACCIO
; Ordre que s'envia al controlador del panell 
(deftemplate ordre-actuador
  (slot sector (type SYMBOL))
  (slot cicle (type INTEGER))
  (slot accio (allowed-symbols orientar-produccio orientar-ombra posicio-seguretat
                               mantenir-posicio sollicitar-dades))
  (slot angle-objectiu (type NUMBER))
  (slot motiu (type STRING)))

; RESULTAT | Origen: EXPLICACIO | Persistencia: 1 cicle/traça | Modifica: ACCIO
; Justificació de la decisió d'un sector.
(deftemplate explicacio
  (slot sector (type SYMBOL))
  (slot cicle (type INTEGER))
  (slot missatge (type STRING)))

; RESULTAT/HISTORIC | Origen: APLICACIO | Persistencia: persistent | Modifica: ACCIO/MONITORATGE
; Memòria episòdica: què es va decidir en cada cicle i sector.
(deftemplate episodi
  (slot cicle (type INTEGER))
  (slot sector (type SYMBOL))
  (slot operador (type SYMBOL))
  (slot angle (type NUMBER))
  (multislot riscos)                      ; riscos presents (tipus-nivell)
  (slot resultat (allowed-symbols pendent correcte fallada) (default pendent)))

; ESCENARI INICIAL (inventat)
; Dades d'estructura: OntologiaModel_v2.
; Observacions del cicle 1: dades SINTÈTIQUES d'operació normal (sense riscos).

(deffacts escenari-1
  ; control
  (fase (nom percepcio))
  (cicle (numero 1))
  (traca (pas 0) (fase inici)
         (missatge "Planta agrovoltaica amb 3 sectors (tomaquet, enciam, vinya). Inici del cicle 1."))

  ; sectors i cultius
  (sector (id Sector_1) (cultiu Tomaquet_1))
  (sector (id Sector_2) (cultiu Enciam_1))
  (sector (id Sector_3) (cultiu Vinya_1))

  (cultiu (id Tomaquet_1) (tipus tomaquet) (sensibilitat mitja))
  (cultiu (id Enciam_1) (tipus enciam) (sensibilitat alt))
  (cultiu (id Vinya_1) (tipus vinya) (sensibilitat baix))

  ; llindars per tipus de cultiu
  (llindars-cultiu (tipus tomaquet)
    (temp-optima-min 20.0) (temp-optima-max 27.0)
    (temp-absoluta-min 7.0) (temp-absoluta-max 35.0)
    (fraccio-esgotament-p 0.40)
    (radiacio-optima-max 350.0) (radiacio-estres 435.0))
  (llindars-cultiu (tipus enciam)
    (temp-optima-min 12.0) (temp-optima-max 21.0)
    (temp-absoluta-min 5.0) (temp-absoluta-max 30.0)
    (fraccio-esgotament-p 0.30)
    (radiacio-optima-max 170.0) (radiacio-estres 170.0))
  (llindars-cultiu (tipus vinya)
    (temp-optima-min 18.0) (temp-optima-max 30.0)
    (temp-absoluta-min 10.0) (temp-absoluta-max 38.0)
    (fraccio-esgotament-p 0.45)
    (radiacio-optima-max 610.0) (radiacio-estres 780.0))

  ; panells (els límits mecànics agafen els valors per defecte de la plantilla)
  (panell (id Panell_1_1) (sector Sector_1) (angle 25.0) (angle-optim-produccio 30.0)
          (disponible si) (estat-mecanic normal))
  (panell (id Panell_1_2) (sector Sector_1) (angle 25.5) (angle-optim-produccio 30.0)
          (disponible si) (estat-mecanic normal))
  (panell (id Panell_2_1) (sector Sector_2) (angle 35.0) (angle-optim-produccio 35.0)
          (disponible si) (estat-mecanic normal))
  (panell (id Panell_2_2) (sector Sector_2) (angle 34.5) (angle-optim-produccio 35.0)
          (disponible si) (estat-mecanic normal))
  (panell (id Panell_3_1) (sector Sector_3) (angle 15.0) (angle-optim-produccio 20.0)
          (disponible si) (estat-mecanic normal))
  (panell (id Panell_3_2) (sector Sector_3) (angle 15.5) (angle-optim-produccio 20.0)
          (disponible si) (estat-mecanic normal))

  ; objectius, prioritats i conflictes
  (objectiu (id Obj_Seguretat) (tipus seguretat) (restriccio dura) (estat inactiu))
  (objectiu (id Obj_Produccio_Cultiu) (tipus produccio-cultiu) (restriccio tova) (estat inactiu))
  (objectiu (id Obj_Produccio_Energia) (tipus produccio-energia) (restriccio tova) (estat inactiu))
  (objectiu (id Obj_Estabilitat) (tipus estabilitat) (restriccio tova) (estat inactiu))
  (objectiu (id Obj_Minimitzar_Moviment) (tipus minimitzar-moviment) (restriccio tova) (estat inactiu))

  (prioritat (major Obj_Seguretat) (menor Obj_Produccio_Cultiu))
  (prioritat (major Obj_Produccio_Cultiu) (menor Obj_Produccio_Energia))
  (prioritat (major Obj_Produccio_Energia) (menor Obj_Estabilitat))
  (prioritat (major Obj_Estabilitat) (menor Obj_Minimitzar_Moviment))

  (conflicte (objectiu-1 Obj_Produccio_Cultiu) (objectiu-2 Obj_Produccio_Energia))
  (conflicte (objectiu-1 Obj_Seguretat) (objectiu-2 Obj_Produccio_Energia))
  (conflicte (objectiu-1 Obj_Produccio_Energia) (objectiu-2 Obj_Minimitzar_Moviment))

  ; quin risc activa quin objectiu (Risc_Dades no n'activa cap: obre un impasse)
  (activa (tipus-risc estres-hidric) (objectiu Obj_Produccio_Cultiu))
  (activa (tipus-risc exces-radiacio) (objectiu Obj_Produccio_Cultiu))
  (activa (tipus-risc temperatura) (objectiu Obj_Produccio_Cultiu))
  (activa (tipus-risc meteorologic-advers) (objectiu Obj_Produccio_Cultiu))
  (activa (tipus-risc mecanic) (objectiu Obj_Seguretat))
  (activa (tipus-risc fallada-actuador) (objectiu Obj_Seguretat))

  ; energia (cicle 1)
  (energia (sector Sector_1) (cicle 1) (produccio-actual 18.5) (demanda 12.0))
  (energia (sector Sector_2) (cicle 1) (produccio-actual 16.2) (demanda 11.5))
  (energia (sector Sector_3) (cicle 1) (produccio-actual 21.8) (demanda 13.0))

  ; observacions (cicle 1, dades sintètiques: tots els valors dins del rang òptim)
  (observacio (sector Sector_1) (cicle 1)
    (radiacio 300.0) (temperatura-aire 23.0) (temperatura-cultiu 24.0)
    (humitat-sol 75.0) (vent 4.0) (pluja 0.0))
  (prediccio (sector Sector_1) (cicle 1)
    (radiacio 320.0) (temperatura 24.0) (vent 5.0) (pluja 0.0))
  (observacio (sector Sector_2) (cicle 1)
    (radiacio 150.0) (temperatura-aire 17.0) (temperatura-cultiu 18.0)
    (humitat-sol 80.0) (vent 4.0) (pluja 0.0))
  (prediccio (sector Sector_2) (cicle 1)
    (radiacio 160.0) (temperatura 18.0) (vent 5.0) (pluja 0.0))
  (observacio (sector Sector_3) (cicle 1)
    (radiacio 500.0) (temperatura-aire 24.0) (temperatura-cultiu 25.0)
    (humitat-sol 70.0) (vent 4.0) (pluja 0.0))
  (prediccio (sector Sector_3) (cicle 1)
    (radiacio 520.0) (temperatura 25.0) (vent 5.0) (pluja 0.0))

  ; estat dels sensors (tots operatius)
  (estat-sensor (sector Sector_1) (tipus humitat-sol) (operatiu si) (qualitat valida) (cicle-ultima-lectura 1))
  (estat-sensor (sector Sector_1) (tipus pluja) (operatiu si) (qualitat valida) (cicle-ultima-lectura 1))
  (estat-sensor (sector Sector_1) (tipus radiacio) (operatiu si) (qualitat valida) (cicle-ultima-lectura 1))
  (estat-sensor (sector Sector_1) (tipus temperatura-aire) (operatiu si) (qualitat valida) (cicle-ultima-lectura 1))
  (estat-sensor (sector Sector_1) (tipus temperatura-cultiu) (operatiu si) (qualitat valida) (cicle-ultima-lectura 1))
  (estat-sensor (sector Sector_1) (tipus vent) (operatiu si) (qualitat valida) (cicle-ultima-lectura 1))
  (estat-sensor (sector Sector_2) (tipus humitat-sol) (operatiu si) (qualitat valida) (cicle-ultima-lectura 1))
  (estat-sensor (sector Sector_2) (tipus pluja) (operatiu si) (qualitat valida) (cicle-ultima-lectura 1))
  (estat-sensor (sector Sector_2) (tipus radiacio) (operatiu si) (qualitat valida) (cicle-ultima-lectura 1))
  (estat-sensor (sector Sector_2) (tipus temperatura-aire) (operatiu si) (qualitat valida) (cicle-ultima-lectura 1))
  (estat-sensor (sector Sector_2) (tipus temperatura-cultiu) (operatiu si) (qualitat valida) (cicle-ultima-lectura 1))
  (estat-sensor (sector Sector_2) (tipus vent) (operatiu si) (qualitat valida) (cicle-ultima-lectura 1))
  (estat-sensor (sector Sector_3) (tipus humitat-sol) (operatiu si) (qualitat valida) (cicle-ultima-lectura 1))
  (estat-sensor (sector Sector_3) (tipus pluja) (operatiu si) (qualitat valida) (cicle-ultima-lectura 1))
  (estat-sensor (sector Sector_3) (tipus radiacio) (operatiu si) (qualitat valida) (cicle-ultima-lectura 1))
  (estat-sensor (sector Sector_3) (tipus temperatura-aire) (operatiu si) (qualitat valida) (cicle-ultima-lectura 1))
  (estat-sensor (sector Sector_3) (tipus temperatura-cultiu) (operatiu si) (qualitat valida) (cicle-ultima-lectura 1))
  (estat-sensor (sector Sector_3) (tipus vent) (operatiu si) (qualitat valida) (cicle-ultima-lectura 1)))


(defmodule DELIBERACIO
  (import DOMINI ?ALL)
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
(deffunction nivell-hidric (?h ?p)
  (bind ?e (- 1 (/ ?h 100)))
  (bind ?tram (/ (- 1 ?p) 3))
  (if (<= ?e ?p) then baix
   else (if (<= ?e (+ ?p ?tram)) then mitja
   else (if (<= ?e (+ ?p (* 2 ?tram))) then alt
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

(defrule avaluacio-a-seleccio
  (declare (salience -10) (auto-focus TRUE))
  ?f <- (fase (nom avaluacio))
  =>
  (printout t "[AVALUACIO -> SELECCIO]" crlf)
  (retract ?f)
  (assert (fase (nom seleccio))))


(defmodule DECISIO
  (import DOMINI ?ALL)
  (import DELIBERACIO deffunction ?ALL)
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
      (and (eq ?pr:sector ?s) (eq ?pr:cicle ?c) (eq ?pr:op ?op) (eq ?pr:tipus millor-que))
    (bind ?motiu (str-cat "empat amb " ?pr:op2 " desfet per " ?pr:font)))
  (do-for-fact ((?pr preferencia))
      (and (eq ?pr:sector ?s) (eq ?pr:cicle ?c) (eq ?pr:op ?op) (eq ?pr:tipus requerida))
    (bind ?motiu (str-cat "preferencia requerida (" ?pr:font ")")))
  (printout t "[SELECCIO] " ?s ": es selecciona " ?op ". Criteri: " ?motiu "." crlf)
  (modify ?o (estat seleccionat))
  (assert (operador-seleccionat (sector ?s) (cicle ?c) (nom ?op) (motiu ?motiu)))
  (assert (traca (pas ?c) (fase seleccio)
                 (missatge (str-cat ?s ": seleccionat " ?op ", " ?motiu)))))

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


(defmodule IMPAS
  (import DOMINI ?ALL)
  (import DELIBERACIO deffunction ?ALL)
  (export ?ALL))

;  IMPAS ---------------------------------------------------------------------

(deffunction condicio-energia (?s ?c)
  (bind ?txt "")
  (do-for-fact ((?e energia)) (and (eq ?e:sector ?s) (eq ?e:cicle ?c))
    (bind ?txt (if (< ?e:produccio-actual ?e:demanda)
                   then " (energia (sector ?s) (cicle ?c) (produccio-actual ?ep) (demanda ?ed&:(< ?ep ?ed)))"
                   else " (energia (sector ?s) (cicle ?c) (produccio-actual ?ep) (demanda ?ed&:(>= ?ep ?ed)))")))
  ?txt)

(deffunction condicio-alineat (?s)
  (bind ?txt "")
  (do-for-fact ((?p panell)) (eq ?p:sector ?s)
    (bind ?txt (if (<= (abs (- ?p:angle ?p:angle-optim-produccio)) ?p:tolerancia-angle)
                   then " (panell (sector ?s) (angle ?pa) (angle-optim-produccio ?po) (tolerancia-angle ?pt&:(<= (abs (- ?pa ?po)) ?pt)))"
                   else " (panell (sector ?s) (angle ?pa) (angle-optim-produccio ?po) (tolerancia-angle ?pt&:(> (abs (- ?pa ?po)) ?pt)))")))
  ?txt)

(deffunction alternatives (?valors)
  (bind ?txt (str-cat (nth$ 1 ?valors)))
  (foreach ?v (rest$ ?valors) (bind ?txt (str-cat ?txt "|" ?v)))
  ?txt)

(deffunction condicio-risc (?s ?c ?tipus ?nivells-que-compten)
  (bind ?n FALSE)
  (do-for-fact ((?r risc))
      (and (eq ?r:sector ?s) (eq ?r:cicle ?c) (eq ?r:tipus ?tipus)
           (member$ ?r:nivell ?nivells-que-compten))
    (bind ?n ?r:nivell))
  (if ?n
   then (str-cat " (risc (sector ?s) (cicle ?c) (tipus " ?tipus ") (nivell " ?n "))")
   else (str-cat " (not (risc (sector ?s) (cicle ?c) (tipus " ?tipus ") (nivell "
                 (alternatives ?nivells-que-compten) ")))")))

(deffunction condicions-operador (?s ?c ?op)
  (bind ?txt (str-cat " (operador (sector ?s) (cicle ?c) (nom " ?op ") (estat proposat))"))
  (switch ?op
    (case orientar-ombra then
      (foreach ?t (create$ temperatura exces-radiacio estres-hidric)
        (bind ?txt (str-cat ?txt (condicio-risc ?s ?c ?t (create$ mitja alt critic))))))
    (case orientar-produccio then
      (bind ?txt (str-cat ?txt (condicio-energia ?s ?c))))
    (case mantenir-posicio then
      (bind ?txt (str-cat ?txt (condicio-energia ?s ?c) (condicio-alineat ?s))))
    (case posicio-seguretat then
      (bind ?txt (str-cat ?txt (condicio-risc ?s ?c mecanic (create$ alt))))))
  ; estabilitat: el que es va fer el cicle anterior tambe compta
  (bind ?anterior FALSE)
  (do-for-fact ((?e episodi)) (and (eq ?e:sector ?s) (eq ?e:cicle (- ?c 1)) (eq ?e:operador ?op))
    (bind ?anterior TRUE))
  (str-cat ?txt
    (if ?anterior
     then (str-cat " (episodi (cicle =(- ?c 1)) (sector ?s) (operador " ?op "))")
     else (str-cat " (not (episodi (cicle =(- ?c 1)) (sector ?s) (operador " ?op ")))"))))

(deffunction nom-nou-chunk ()
  (sym-cat chunk- (+ 1 (length$ (find-all-facts ((?f fragment-apres)) TRUE)))))

(deffunction crea-chunk-empat (?s ?c ?guanya ?perd)
  (bind ?nom (nom-nou-chunk))
  (bind ?regla
    (str-cat "(defrule DELIBERACIO::" ?nom
             " (declare (auto-focus TRUE))"
             " (fase (nom avaluacio)) (cicle (numero ?c))"
             (condicions-operador ?s ?c ?guanya)
             (condicions-operador ?s ?c ?perd)
             " (not (preferencia (sector ?s) (cicle ?c) (op " ?guanya ") (tipus millor-que) (op2 " ?perd ")))"
             " =>"
             " (printout t \"[" ?nom "] \" ?s \": situacio coneguda, " ?guanya " millor que " ?perd ".\" crlf)"
             " (assert (preferencia (op " ?guanya ") (sector ?s) (cicle ?c) (tipus millor-que)"
             " (op2 " ?perd ") (font " ?nom ")))"
             " (assert (traca (pas ?c) (fase avaluacio) (missatge (str-cat ?s \": " ?nom " aplicat\")))))"))
  (if (not (build ?regla)) then
    (printout t "[CHUNKING] No s'ha pogut construir " ?nom "." crlf)
    (return FALSE))
  (assert (fragment-apres (nom ?nom) (impas-origen empat) (cicle ?c)))
  (printout t "[CHUNKING] Nova regla " ?nom ": " ?guanya " millor que " ?perd
              " quan es repeteixi aquesta situacio." crlf)
  ?nom)

; Condicions que distingeixen les tres maneres de resoldre les dades insuficients.
(deffunction condicio-previsio-vent (?si)
  (bind ?p "(prediccio (sector ?s) (cicle ?c) (vent ?pv&:(numberp ?pv))) (panell (sector ?s) (vent-avis ?av&:(>= ?pv ?av)) (angle-seguretat ?as))")
  (if ?si then (str-cat " " ?p)
   else (str-cat " (not (and (prediccio (sector ?s) (cicle ?c) (vent ?pv&:(numberp ?pv)))"
                 " (panell (sector ?s) (vent-avis ?av&:(>= ?pv ?av)))))")))

(deffunction condicio-historial-vent (?si)
  (bind ?e "(episodi (cicle =(- ?c 1)) (sector ?s) (riscos $? mecanic-alt|mecanic-critic $?))")
  (if ?si then (str-cat " " ?e) else (str-cat " (not " ?e ")")))

; El chunk fa el mateix que va fer la deliberacio:
;   previsio  -> posicio-seguretat requerida
;   historial -> posicio-seguretat requerida
;   hold      -> sollicitar-dades requerida (el panell no es mou)
(deffunction crea-chunk-dades (?s ?c ?mode)
  (bind ?nom (nom-nou-chunk))
  (bind ?cap (str-cat "(defrule DELIBERACIO::" ?nom
                      " (declare (auto-focus TRUE))"
                      " (fase (nom avaluacio)) (cicle (numero ?c))"
                      " (risc (sector ?s) (cicle ?c) (tipus dades) (nivell critic))"))
  (bind ?guarda " (not (preferencia (sector ?s) (cicle ?c) (tipus requerida)))")
  (bind ?traca (str-cat " (assert (traca (pas ?c) (fase avaluacio) (missatge (str-cat ?s \": " ?nom " aplicat\")))))"))
  (bind ?seguretat
    (str-cat " (if (not (any-factp ((?o operador)) (and (eq ?o:sector ?s) (eq ?o:cicle ?c) (eq ?o:nom posicio-seguretat))))"
             " then (assert (operador (id (sym-cat ?s -seguretat- ?c)) (cicle ?c) (sector ?s) (nom posicio-seguretat)"
             " (angle-objectiu ?as) (estat proposat))))"
             " (assert (preferencia (op posicio-seguretat) (sector ?s) (cicle ?c) (tipus requerida) (font " ?nom ")))"))
  (switch ?mode
    (case previsio then
      (bind ?descripcio "sense lectura de vent i previsio de vent fort, posicio-seguretat requerida")
      (bind ?regla (str-cat ?cap (condicio-previsio-vent TRUE) ?guarda " =>"
                            " (printout t \"[" ?nom "] \" ?s \": " ?descripcio ".\" crlf)" ?seguretat ?traca)))
    (case historial then
      (bind ?descripcio "sense lectura de vent i vent fort el cicle anterior, posicio-seguretat requerida")
      (bind ?regla (str-cat ?cap (condicio-previsio-vent FALSE) (condicio-historial-vent TRUE)
                            " (panell (sector ?s) (angle-seguretat ?as))" ?guarda " =>"
                            " (printout t \"[" ?nom "] \" ?s \": " ?descripcio ".\" crlf)" ?seguretat ?traca)))
    (default
      (bind ?descripcio "sense lectura de vent i res no indica vent fort, sollicitar-dades requerida i panell en hold")
      (bind ?regla (str-cat ?cap (condicio-previsio-vent FALSE) (condicio-historial-vent FALSE)
                            " (operador (sector ?s) (cicle ?c) (nom sollicitar-dades) (estat proposat))" ?guarda " =>"
                            " (printout t \"[" ?nom "] \" ?s \": " ?descripcio ".\" crlf)"
                            " (assert (preferencia (op sollicitar-dades) (sector ?s) (cicle ?c) (tipus requerida) (font " ?nom ")))"
                            ?traca))))
  (if (not (build ?regla)) then
    (printout t "[CHUNKING] No s'ha pogut construir " ?nom "." crlf)
    (return FALSE))
  (assert (fragment-apres (nom ?nom) (impas-origen dades-insuficients) (cicle ?c)))
  (printout t "[CHUNKING] Nova regla " ?nom ": " ?descripcio "." crlf)
  ?nom)


; --- resolucio dels impasses -------------------------------------------------

; Empat: criteri secundari = ordre de prioritats entre objectius.
; Si cap dels dos preval, es tria el mes reversible (el que mou menys el panel).
(defrule resol-empat
  (declare (auto-focus TRUE))
  (fase (nom impas))
  ?i <- (impas (tipus empat) (sector ?s) (cicle ?c) (operadors ?a ?b))
  ?g <- (subobjectiu (sector ?s) (tipus resoldre-empat) (estat actiu))
  =>
  (bind ?oa (id-objectiu (objectiu-operador ?a)))
  (bind ?ob (id-objectiu (objectiu-operador ?b)))
  (if (preval ?oa ?ob) then
     (bind ?guanya ?a) (bind ?perd ?b)
     (bind ?criteri (str-cat ?oa " te prioritat sobre " ?ob))
   else (if (preval ?ob ?oa) then
     (bind ?guanya ?b) (bind ?perd ?a)
     (bind ?criteri (str-cat ?ob " te prioritat sobre " ?oa))
   else
     (if (<= (moviment-operador ?s ?a ?c) (moviment-operador ?s ?b ?c))
      then (bind ?guanya ?a) (bind ?perd ?b)
      else (bind ?guanya ?b) (bind ?perd ?a))
     (bind ?criteri "mateixa prioritat; es tria el que mou menys el panell")))
  (printout t "[IMPAS] " ?s ": subobjectiu resoldre-empat. " ?criteri " -> " ?guanya
              " millor que " ?perd "." crlf)
  (assert (preferencia (op ?guanya) (sector ?s) (cicle ?c) (tipus millor-que) (op2 ?perd)
                       (font IMPAS-prioritat)))
  (assert (traca (pas ?c) (fase impas)
                 (missatge (str-cat ?s ": empat resolt, " ?criteri ", " ?guanya " millor que " ?perd))))
  (crea-chunk-empat ?s ?c ?guanya ?perd)
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
  ?g <- (subobjectiu (sector ?s) (tipus resoldre-dades) (estat actiu))
  (panell (sector ?s) (vent-avis ?avis) (angle-seguretat ?as))
  =>
  (bind ?pv (previsio-vent-sector ?s ?c))
  (bind ?vent-anterior (any-factp ((?e episodi))
      (and (eq ?e:sector ?s) (eq ?e:cicle (- ?c 1))
           (or (member$ mecanic-alt ?e:riscos) (member$ mecanic-critic ?e:riscos)))))
  (if (and (numberp ?pv) (>= ?pv ?avis)) then
     (bind ?mode previsio)
     (bind ?motiu (str-cat "la previsio de vent es de " ?pv " m/s (avis a " ?avis ")"))
   else (if ?vent-anterior then
     (bind ?mode historial)
     (bind ?motiu "el cicle anterior ja hi havia risc mecanic")
   else
     (bind ?mode hold)
     (bind ?motiu "ni la previsio ni l'historial indiquen vent fort")))
  (if (eq ?mode hold) then
     (printout t "[IMPAS] " ?s ": subobjectiu resoldre-dades. Falta la lectura de vent i " ?motiu
                 ". Es demanen dades i es mante la posicio." crlf)
     (assert (preferencia (op sollicitar-dades) (sector ?s) (cicle ?c) (tipus requerida)
                          (font IMPAS-dades)))
     (assert (traca (pas ?c) (fase impas)
                    (missatge (str-cat ?s ": dades insuficients, " ?motiu ", sollicitar-dades i hold"))))
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
     (assert (preferencia (op posicio-seguretat) (sector ?s) (cicle ?c) (tipus requerida)
                          (font IMPAS-dades)))
     (assert (traca (pas ?c) (fase impas)
                    (missatge (str-cat ?s ": dades insuficients, " ?motiu ", posicio-seguretat requerida")))))
  (crea-chunk-dades ?s ?c ?mode)
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
