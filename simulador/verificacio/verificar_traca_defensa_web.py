"""Comprova que l'API envia la traça real al Mode Defensa.

Instruccions:
    1. En un PowerShell inicia `python webapp.py` des de simulador.
    2. En un segon PowerShell, des de simulador:
           python verificacio/verificar_traca_defensa_web.py
    3. Si la prova diu OK, obre la web i prem Ctrl+F5.

Fa una simulació real d'un dia, amb el mode de captura activat.
No inventa cap traça ni usa dades precalculades.
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = 'http://127.0.0.1:8000'
ESCENARI = 'dia_normal.json'


def request(path, data=None):
    payload = None if data is None else json.dumps(data).encode('utf-8')
    req = urllib.request.Request(BASE + path, data=payload,
                                 headers={'Content-Type':'application/json'} if payload else {},
                                 method='POST' if payload else 'GET')
    with urllib.request.urlopen(req, timeout=180) as res:
        return json.load(res)


def main():
    dies = request('/api/days?scenario=' + urllib.parse.quote(ESCENARI))['days']
    if not dies:
        raise AssertionError('Escenari sense dates disponibles')
    req = {'scenario': ESCENARI, 'controller': 'soar', 'day': dies[0],
           'compare': False, 'demo': True}
    result = request('/api/simulate', req)
    runs = result.get('runs') or []
    run = next((r for r in runs if r.get('controller') == 'soar'), None)
    if run is None:
        raise AssertionError('Resposta sense controlador SOAR')
    records = run.get('records') or []
    if not records:
        raise AssertionError('Resposta sense decisions')
    demos = [r['demo'] for r in records if isinstance(r.get('demo'), dict)]
    if not demos:
        raise AssertionError('FALLO: La resposta API omet el camp demo. Revisa simulador/webcore.py i reinicia webapp.py')
    campos = ('observacions','candidats','preferencies','seleccio','regles_disparades')
    missing = [k for k in campos if k not in demos[0]]
    if missing:
        raise AssertionError('Falten camps de traca: ' + ', '.join(missing))
    fires = sum(len(d.get('regles_disparades') or []) for d in demos)
    if not fires:
        raise AssertionError('Hi ha camps demo però cap regla disparada: comprova watch rules i controlador')
    print(f'OK Mode Defensa: {len(records)} decisions; {len(demos)} traces; {fires} activacions registrades (comptades per registre, poden repetir-se entre sectors).')
    print('L\'API ja envia observacions, candidats, preferencies, seleccio i regles disparades.')
    print('Actualitza el navegador (Ctrl+F5) i prem una fila de la taula.')


if __name__ == '__main__':
    try:
        main()
    except (urllib.error.URLError, TimeoutError) as e:
        print(f'ERROR de connexió amb {BASE}: {e}. Arrenca `python webapp.py` abans.')
        sys.exit(1)
    except Exception as e:
        print('ERROR:', e)
        sys.exit(1)
