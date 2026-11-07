"""Catàleg de protocols existents i executor supervisat per a la UI.

No implementa cap experiment ni cap decisió: invoca els scripts originals.
El catàleg diferencia registres meteorològics reals, escenaris modificats
sobre dades reals i casos CLIPS completament sintètics.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import time
import threading
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "resultats" / "ui_execucions"
LOCK = threading.Lock()
ACTIVE = None
RUNS = {}

SOURCES = {
  "ribera": {"id":"ribera", "title":"Ribera de Sió · 2023", "class":"reanalisi_i_mesures", "label":"Meteorologia reanalitzada + mesures de sòl reals", "items":[
    {"provider":"Open-Meteo Historical API · ERA5", "role":"Temperatura, radiació, vent, pluja, ET₀ horàries (reanàlisi, no sensor directe)", "file":"dades_reals/openmeteo_ribera-sio_abr-set2023.json", "url":"https://archive-api.open-meteo.com/v1/archive"},
    {"provider":"XMS-Cat · ICGC / ISMN", "role":"Humitat del sòl mesurada a l'estació Ribera de Sió; ús segons experiment", "file":"dades_reals/xmscat_ribera-sio_abr-set2023.csv", "url":"https://visors.icgc.cat/mesurasols/"},
    {"provider":"PVGIS · Comissió Europea (JRC)", "role":"Referència per calibració de captació fotovoltaica; no és producció observada dels panells simulats", "file":"dades_reals/pvgis_ribera-sio_2023.json", "url":"https://re.jrc.ec.europa.eu/pvg_tools/"},
  ]},
  "cantallops":{"id":"cantallops", "title":"Cantallops · 2023", "class":"reanalisi_i_mesures", "label":"Meteorologia reanalitzada + mesures de sòl reals", "items":[
    {"provider":"Open-Meteo Historical API · ERA5", "role":"Sèrie horària de vent, ratxes i altres variables meteorològiques", "file":"dades_reals/openmeteo_cantallops_gen-abr2023.json", "url":"https://archive-api.open-meteo.com/v1/archive"},
    {"provider":"XMS-Cat · ICGC / ISMN", "role":"Mesures de sòl quan l'experiment les utilitza", "file":"dades_reals/xmscat_cantallops_gen-abr2023.csv", "url":"https://visors.icgc.cat/mesurasols/"},
    {"provider":"PVGIS · JRC", "role":"Calibració fotovoltaica", "file":"dades_reals/pvgis_cantallops_2023.json", "url":"https://re.jrc.ec.europa.eu/pvg_tools/"},
  ]},
  "multi":{"id":"multi", "title":"Ribera de Sió i Cantallops", "class":"reanalisi_i_mesures", "label":"Sèries dels dos emplaçaments; consulta les fitxes de fonts", "items":[]},
  "long":{"id":"long", "title":"Ribera de Sió · 2022–2023", "class":"reanalisi_i_mesures", "label":"Històrics ERA5 i estació XMS-Cat (ISMN)", "items":[
    {"provider":"Open-Meteo / ERA5", "role":"Històric meteorològic 2022–2023", "file":"dades_reals/openmeteo_ribera-sio_2022-2023.json", "url":"https://archive-api.open-meteo.com/v1/archive"},
    {"provider":"XMS-Cat via ISMN", "role":"Humitat mesurada 2022–2023", "file":"dades_reals/xmscat_ribera-sio_2022-2023_ismn.csv", "url":"https://ismn.earth/"}
  ]},
  "cp":{"id":"cp", "title":"Cas de prova determinista CLIPS", "class":"sintetic", "label":"Entrades sintètiques definides per l'equip; NO són observacions reals", "items":[
    {"provider":"verificacio/casos_prova.py", "role":"Valors de sensors, expectatives i cicles de prova; definits manualment", "file":"verificacio/casos_prova.py", "url":None}
  ]}
}

def row(id, title, verify, source, kind="validacio", details="", risk="normal", command=None, tag=None):
    return dict(id=id,title=title,verify=verify,source=source,kind=kind,details=details,risk=risk,
                command=command or ["experiments.py",id], tag=tag or "Protocol oficial", supported=True)

CATALOG = [
 row("E4", "Seguretat amb tramuntana", "Confirma que el controlador prioritza la seguretat mecànica amb dies de vent i el compara amb un seguidor.", "cantallops", details="95 dies de Cantallops · SOAR vs seguidor"),
 row("E5", "Fallada del sensor de vent", "Mesura la robustesa de les decisions quan falta la lectura de vent en proporcions controlades.", "cantallops", details="40 dies de vent · absència sintètica de lectures 0/5/20 % · 3 llavors"),
 row("E6", "Actuador bloquejat", "Avalua la detecció i el tractament de moviments que el panell no arriba a efectuar.", "ribera", details="40 dies meteorològics · fallada simulada del 5 % · 3 llavors"),
 row("E7", "SOAR versus referències", "Compara energia, estrès, seguretat i moviment entre SOAR, seguidor comercial i panell fix.", "ribera", details="48 dies aparellats a Ribera de Sió · 3 controladors"),
 row("E8", "Generalització del chunking", "Comprova si els chunks apresos milloren o conserven decisions en dies no vistos.", "ribera", details="Entrenament abril–juny; prova juliol–setembre · comparació amb/sense chunking"),
 row("E9", "Aprenentatge per reforç", "Compara variants de la funció de reforç en dies no vistos amb el mateix protocol d'aprenentatge.", "ribera", details="Entrenament i test de dies reals; alternatives de representació de trets"),
 row("E11", "Agenda CLIPS", "Verifica que l'estratègia de l'agenda i la salience no introdueixen canvis indeguts en les decisions.", "ribera", kind="verificacio", details="20 dies · depth/breadth/LEX/MEA/especificitat/random/salience"),
 row("E12", "Sensibilitat del model", "Estudia si la conclusió SOAR–seguidor es manté en variar paràmetres del simulador.", "ribera", details="Variacions sintètiques de paràmetres sobre dies meteorològics històrics"),
 row("E13", "Consistència del coneixement", "Comprova invariants de chunks, valors Q i episodis a mesura que evoluciona la memòria.", "ribera", kind="verificacio", details="5 execucions de 20 dies seguits · controls K1–K8"),
 row("E14", "Escenaris adversos", "Contrasta la robustesa sota calor, vent extrem i sequera respecte de sistemes de referència.", "multi", details="Calor +3 °C, vent ×1,3 i sequera sense reg: modificacions SINTÈTIQUES sobre meteorologia històrica"),
 row("E15", "Reg CLIPS contra referències", "Avalua si el reg governat per CLIPS consumeix menys aigua mantenint l'estrès respecte de FAO/finca/cap reg.", "ribera", details="Abril–setembre · blocs mensuals · 4 polítiques de reg · 4 llavors"),
 row("E16", "Memòria episòdica a llarg termini", "Contrasta l'efecte de conservar o reiniciar la memòria entre dos anys meteorològics.", "long", details="2022 entrenament, 2023 avaluació · per trams amb punts de control", risk="llarg", command=["experiments.py","E16","--part","0","--minuts-tram","5"]),
 row("E18", "Cicle deliberatiu SOAR", "Verifica l'ordre de les fases, l'única acció per sector i la transició d'impasses.", "multi", kind="verificacio", details="20 dies: Ribera i Cantallops; fallada sintètica de sensor del 10 %",command=["verificacio/e18_cicle_soar.py"]),
 row("E19", "Prioritats i pesos", "Comprova analíticament i en dies reals que les prioritats, restriccions i pesos són coherents.", "multi", kind="verificacio", details="Graelles i comparació en 40 dies reals amb variants de pesos",risk="llarg", command=["verificacio/e19_pesos.py"]),
 row("E20", "Memòria semàntica i escalabilitat", "Avalua cobertura, consistència, latència i efecte de la memòria semàntica comparada amb l'episòdica.", "long", details="2023 seqüencial · part 0 de l'experiment, no representa el resultat global",risk="llarg", command=["experiments.py","E20","--part","0"]),
 row("E21", "Model físic i fenologia", "Compara l'efecte del model de temperatura de coberta i calendari de cultiu sobre SOAR i baselines.", "ribera", details="48 dies del 2023; dues versions del model físic"),
 row("E22", "Sensors i fallades de reg", "Mesura l'ús de lectures històriques i la detecció de fallades de vàlvula i reg.", "ribera", details="30 dies amb errors de sensor; juny–agost amb avaria sintètica de vàlvula"),
 row("E23", "Polítiques d’oblit de memòria episòdica", "Compara l’efecte de les polítiques d’oblit sobre el cost, la conservació del coneixement i el rendiment del controlador.", "ribera", details="Històric de Ribera de Sió 2023; polítiques i paràmetres d’oblit són intervencions experimentals; part 0, no és la campanya completa", risk="llarg", command=["experiments.py","E23","--part","0"]),
 row("CP05", "Impasse: empat entre objectius", "Provoca un empat real de CLIPS i comprova la deliberació, el chunk generat i la reutilització al cicle següent.", "cp", kind="impasse",details="Dos cicles deterministes · enciam · preferències cultiu/energia", command=None,tag="Cas de prova CLIPS"),
 row("CP06", "Impasse: dades insuficients", "Provoca una observació absent i comprova la deliberació i la resposta segura del controlador.", "cp", kind="impasse",details="Dos cicles deterministes · sensor de vent absent", command=None,tag="Cas de prova CLIPS"),
]

# Els casos CP05 i CP06 són executats per l'endpoint oficial existent.
for entry in CATALOG:
    if entry['id'].startswith('CP'):entry['command']=None


def public_catalog():
    return {"experiments": [{**e,"source_detail":SOURCES[e['source']]} for e in CATALOG],
      "method":"Els scripts originals generen resultats a simulador/resultats. La UI no transforma una simulació lliure en un experiment formal.",
      "sources_document":"dades_reals/FONTS.md", "protocols_document":"EXPERIMENTS.md"}


def _metadata(exp_id):
    match = next((e for e in CATALOG if e['id']==exp_id),None)
    if not match:raise ValueError('Experiment no permès')
    return match


def start(exp_id):
    global ACTIVE
    e=_metadata(exp_id)
    if e['kind']=='impasse':raise ValueError('El cas CLIPS s\'executa per /api/defensa/impasses/{id}')
    with LOCK:
        if ACTIVE and RUNS[ACTIVE]['proc'].poll() is None:raise RuntimeError('Ja hi ha un experiment executant-se; cal esperar o aturar-lo')
        LOG_DIR.mkdir(parents=True,exist_ok=True)
        run_id=uuid4().hex[:12]
        log=LOG_DIR / f'{exp_id}_{run_id}.log'
        command=[sys.executable,'-u',*e['command']]
        handle=log.open('w',encoding='utf-8',errors='replace')
        try:
            process=subprocess.Popen(command,cwd=ROOT,stdout=handle,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
        finally:handle.close()
        RUNS[run_id]={'proc':process,'id':exp_id,'log':log,'started':time.time(),'command':command}
        ACTIVE=run_id
        return status(run_id)


def status(run_id):
    r=RUNS.get(run_id)
    if r is None:raise KeyError(run_id)
    rc=r['proc'].poll()
    try:
        # Evita llegir un log potencialment molt gran sencer.
        with r['log'].open('rb') as f:
            f.seek(0,2);f.seek(max(0,f.tell()-32000));tail=f.read().decode('utf-8','replace')
    except OSError:tail=''
    return {'run_id':run_id,'experiment':r['id'],'state':'running' if rc is None else ('done' if rc==0 else 'failed'),
            'returncode':rc,'seconds':round(time.time()-r['started'],1),
            'command':' '.join([Path(x).name if i==0 else x for i,x in enumerate(r['command'])]),
            'log_tail':tail[-16000:], 'log_path':str(r['log'].relative_to(ROOT))}


def stop(run_id):
    r=RUNS.get(run_id)
    if r is None:raise KeyError(run_id)
    if r['proc'].poll() is None:r['proc'].terminate()
    return status(run_id)


def artifacts(run_id):
    """Artefactes creats durant aquesta execució, sense incloure logs d'altres execucions."""
    r=RUNS.get(run_id)
    if r is None:raise KeyError(run_id)
    root=ROOT/'resultats'
    if not root.exists():return []
    out=[]
    for p in root.rglob('*'):
        if not p.is_file() or 'ui_execucions' in p.parts:continue
        try:
            st=p.stat()
        except OSError:continue
        if st.st_mtime+2<r['started']:continue
        out.append({'path':str(p.relative_to(root)).replace('\\','/'),'bytes':st.st_size,'modified':st.st_mtime})
    return sorted(out,key=lambda a:a['modified'],reverse=True)[:60]


def artifact_path(run_id, relative):
    """Només fitxers associats a un run autoritzat en memòria, cap accés arbitrari."""
    available={x['path'] for x in artifacts(run_id)}
    if relative not in available:raise KeyError(relative)
    p=(ROOT/'resultats'/relative).resolve()
    if not p.is_relative_to((ROOT/'resultats').resolve()):raise ValueError(relative)
    return p
