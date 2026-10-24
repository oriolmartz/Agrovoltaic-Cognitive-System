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
;    fragment-apres, epmem-episodi (+ epmem-config, epmem-estat,
;    epmem-consulta, epmem-resultat per gestionar-lo)
;    Origen: seleccio, aplicacio, explicacio, monitoratge, chunking i MEMORIA.
;    Persistencia: resultats del cicle; episodi es la memoria de treball del cicle
;    anterior; fragment-apres i epmem-episodi son memoria a llarg termini (fitxer).
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
;   rl: un chunk après en un empat diu que op li convé (op2 = el que va perdre);
;       el valor no es aquí sinó a rl-valor (tret = nom del chunk) i el reforç l'ajusta
(deftemplate preferencia
  (slot op (type SYMBOL))                 ; nom de l'operador
  (slot sector (type SYMBOL))
  (slot cicle (type INTEGER))
  (slot tipus (allowed-symbols acceptable rebuig prohibida requerida millor pitjor
                               millor-que pitjor-que indiferent numerica rl))
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

; RESULTAT/APRENENTATGE | Origen: chunking | Persistencia: persistent (fitxer) | Modifica: APRENENTATGE
; Fragment après per chunking. 'codi' i 'signatura' permeten reconstruir la regla
; en una altra sessio i evitar duplicats.
(deftemplate fragment-apres
  (slot nom (type SYMBOL))
  (slot impas-origen (type SYMBOL))       ; tipus d'impasse que l'ha originat
  (slot cicle (type INTEGER))             ; cicle en què s'ha après
  (slot descripcio (type STRING) (default ""))
  (slot codi (type STRING) (default ""))
  (slot signatura (type STRING) (default "")))

; CONTROL | Origen: usuari/arquitectura | Persistencia: global | Modifica: usuari
; Parametres del reforç (equivalent a 'rl --set ...' de Soar).
(deftemplate rl-config
  (slot aprenentatge (allowed-symbols on off) (default on))  ; rl --set learning
  (slot alfa (type NUMBER) (default 0.3))                    ; rl --set learning-rate
  (slot prior (type NUMBER) (default 0.5))                   ; valor inicial d'un chunk d'empat
  (slot epsilon (type NUMBER) (default 0.05)))               ; diferencia minima per desfer un empat

; APRENENTATGE | Origen: REFORC | Persistencia: sessio | Modifica: REFORC
; Una "rajola" de la funcio de valor: Q(tret, operador). Cada fet fa el paper d'una
; regla RL de Soar que nomes comprova un tret de la situacio (tile coding):
;   tret = tot | sector=.. | cultiu=.. | risc=..-.. | cobertura=.. | chunk-N
; El valor d'un operador es la suma de les rajoles actives.
(deftemplate rl-valor
  (slot tret (type SYMBOL))
  (slot op (type SYMBOL))
  (slot q (type FLOAT) (default 0.0))
  (slot n (type INTEGER) (default 0)))    ; actualitzacions rebudes

; APRENENTATGE | Origen: REFORC | Persistencia: fins al cicle seguent | Modifica: REFORC
; Rajoles que han contribuit a l'operador triat, per actualitzar-les quan arribi la recompensa.
(deftemplate rl-traca
  (slot sector (type SYMBOL))
  (slot cicle (type INTEGER))
  (slot op (type SYMBOL))
  (multislot trets)
  (slot risc (type INTEGER))              ; risc influenciable en decidir
  (slot cobertura (type FLOAT))
  (slot estat (allowed-symbols pendent fet) (default pendent)))

; CONTROL/APRENENTATGE | Origen: regles del subestat | Persistencia: fins que es crea el chunk
; Registre del que un subobjectiu ha consultat (positiva/test/negacio) i produit (accio).
(deftemplate dependencia
  (slot goal (type SYMBOL))
  (slot tipus (allowed-symbols positiva test negacio accio))
  (slot ordre (type INTEGER))
  (slot text (type STRING))
  (multislot vars))                       ; parelles valor-numeric nom-variable


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
; Traça episòdica a CURT termini (memòria de treball): què es va decidir en cada
; cicle i sector. La memòria a LLARG termini és epmem-episodi (mòdul MEMORIA).
(deftemplate episodi
  (slot cicle (type INTEGER))
  (slot sector (type SYMBOL))
  (slot operador (type SYMBOL))
  (slot angle (type NUMBER))
  (multislot riscos)                      ; riscos presents (tipus-nivell)
  (slot resultat (allowed-symbols pendent correcte fallada) (default pendent)))

; =============================================================================
; MEMORIA EPISODICA A LLARG TERMINI (equivalent a EpMem de Soar)
; =============================================================================
; A diferencia de 'episodi' (memoria de treball: nomes el cicle anterior), aquests
; fets formen un magatzem que creix, s'indexa temporalment (id creixent) i es pot
; consultar per contingut. L'emmagatzematge es automatic (un episodi per sector i
; cicle, 'trigger dc'); la recuperacio es per indici ('cue'), com a Soar:
;   puntuacio d'un episodi = nombre de trets del cue que compleix;
;   es retorna el mes recent amb la puntuacio maxima.
; Cada episodi es descriu amb TRETS plans (simbols clau=valor), p. ex.
;   sector=Sector_1  cultiu=tomaquet  risc=temperatura-alt  cobertura=deficit
;   operador=orientar-ombra  impas=resoldre-empat  resultat=correcte  valoracio=bona
; Un tret del cue es "satisfet" si hi es al conjunt de trets de l'episodi.

; CONTROL | Origen: usuari/arquitectura | Persistencia: global | Modifica: usuari, MEMORIA
; Parametres de la memoria episodica (equivalent a 'epmem --set ...').
(deftemplate epmem-config
  (slot aprenentatge (allowed-symbols on off) (default on)) ; epmem --set learning
  (slot pes-memoria (type NUMBER) (default 2))              ; valor maxim de la preferencia de memoria
  (slot llindar-similitud (type NUMBER) (default 0.5))      ; puntuacio normalitzada minima per fer cas d'un record
  (multislot exclusions)                                    ; claus de tret que no s'emmagatzemen
  (slot fitxer (type STRING) (default "")))                 ; fitxer de persistencia ("" = sense)

; CONTROL | Origen: MEMORIA | Persistencia: global | Modifica: MEMORIA
; Estat intern: id del proxim episodi (present-id de Soar).
(deftemplate epmem-estat
  (slot seguent-id (type INTEGER) (default 1))
  (slot sessio-inici (type INTEGER) (default 1))  ; primer id d'aquesta sessio (els anteriors venen del fitxer)
  (slot brut (allowed-symbols si no) (default no))) ; hi ha canvis sense desar

; RESULTAT/HISTORIC | Origen: ACCIO (monitoratge) | Persistencia: persistent (fitxer) | Modifica: MEMORIA
; Un episodi: la situacio d'un sector en un cicle, l'operador aplicat i com va anar.
;   resultat  = efecte directe (el panell ha arribat a l'angle ordenat?)
;   valoracio = efecte global al cicle seguent (bona / neutra / dolenta), vegeu epmem-valora-resultat
(deftemplate epmem-episodi
  (slot id (type INTEGER))
  (slot cicle (type INTEGER))
  (slot sector (type SYMBOL))
  (slot cultiu (type SYMBOL) (default desconegut))
  (slot operador (type SYMBOL))
  (slot angle (type NUMBER))
  (slot risc-total (type INTEGER) (default 0))    ; suma de nivells de risc ambientals
  (slot cobertura (type NUMBER) (default -1.0))   ; produccio / demanda (-1 = sense dades)
  (slot impas (type SYMBOL) (default cap))        ; subobjectiu resolt aquell cicle
  (slot motiu (type STRING) (default ""))         ; criteri de seleccio
  (slot resultat (allowed-symbols pendent correcte fallada) (default pendent))
  (slot valoracio (allowed-symbols pendent bona neutra dolenta) (default pendent))
  (multislot trets))                              ; descripcio indexable de l'episodi

; CONTROL | Origen: DELIBERACIO | Persistencia: fins al cicle seguent | Modifica: DELIBERACIO, MEMORIA
; Comanda de consulta (equivalent a epmem.command). Una consulta pendent es processa
; i passa a 'fet'; el resultat queda a epmem-resultat.
;   query    : millor episodi segons el cue
;   previous : episodi anterior (mateix sector) a 'ref'
;   next     : episodi posterior (mateix sector) a 'ref'
(deftemplate epmem-consulta
  (slot id (type SYMBOL))
  (slot sector (type SYMBOL))
  (slot cicle (type INTEGER))
  (slot etiqueta (type SYMBOL) (default cap))     ; dada del demandant, es copia al resultat
  (slot tipus (allowed-symbols query previous next) (default query))
  (multislot cue)                                 ; trets desitjats (es puntuen)
  (multislot requereix)                           ; trets obligatoris (filtre)
  (multislot exclou)                              ; trets prohibits (neg-query)
  (multislot prohibits)                           ; ids d'episodis que no es poden retornar
  (slot ref (type INTEGER) (default 0))
  (slot estat (allowed-symbols pendent fet) (default pendent)))

; CONTROL | Origen: MEMORIA | Persistencia: fins al cicle seguent | Modifica: MEMORIA
; Resultat d'una consulta (equivalent a epmem.result). L'episodi recuperat es el
; fet epmem-episodi amb id = memoria-id.
(deftemplate epmem-resultat
  (slot consulta (type SYMBOL))
  (slot sector (type SYMBOL))
  (slot cicle (type INTEGER))
  (slot etiqueta (type SYMBOL) (default cap))
  (slot exit (allowed-symbols si no))
  (slot memoria-id (type INTEGER) (default 0))
  (slot cardinalitat (type INTEGER) (default 0))   ; trets del cue satisfets
  (slot puntuacio (type NUMBER) (default 0))
  (slot normalitzada (type NUMBER) (default 0))    ; cardinalitat / mida del cue
  (slot perfecte (allowed-symbols si no) (default no))) ; tots els trets satisfets

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

(defmodule MAIN
  (import APRENENTATGE deffunction ?ALL)
  (import MEMORIA deffunction ?ALL))


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
