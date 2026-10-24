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
  (slot epsilon (type NUMBER) (default 0.05))                ; diferencia minima per desfer un empat
  (slot parelles (allowed-symbols on off) (default on)))     ; rajoles de parelles de trets

; APRENENTATGE | Origen: REFORC | Persistencia: sessio | Modifica: REFORC
; Una "rajola" de la funcio de valor: Q(tret, operador). Cada fet fa el paper d'una
; regla RL de Soar que nomes comprova un tret de la situacio (tile coding):
;   tret = tot | sector=.. | cultiu=.. | risc=..-.. | cobertura=.. | chunk-N
;          | risc=A+risc=B | risc=A+cobertura=C   (parelles: interaccions entre trets)
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


