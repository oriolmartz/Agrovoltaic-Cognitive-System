"""Execucio en paral·lel que es pot aturar amb Ctrl+C (tambe a Windows) i mostra el progres."""

from __future__ import annotations

import multiprocessing as mp
import os
import signal
import sys
import time


def _init_treballador(init, args):
    # els processos fills ignoren Ctrl+C: l'atura el pare i els mata a tots
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    # Els fills no escriuen res util per pantalla (els resultats tornen pel pipe). Silenciem la
    # seva sortida a nivell de sistema un sol cop: aixi els avisos interns de CLIPS en destruir
    # entorns (ENVRNMNT8, inofensius) no omplen la consola.
    try:
        nul = os.open(os.devnull, os.O_WRONLY)
        os.dup2(nul, 1)
        os.dup2(nul, 2)
        import clips_bridge
        clips_bridge.SORTIDA_SILENCIADA = True
    except Exception:
        pass
    if init is not None:
        init(*args)


ESPERA_MAXIMA = 180   # segons sense cap feina acabada -> es considera penjat


def mapa(funcio, elements, processos=None, initializer=None, initargs=(), titol="", cada=None,
         espera_maxima=ESPERA_MAXIMA, mida=None):
    """Com Pool.map, en ordre, pero amb progres, Ctrl+C i deteccio de processos penjats."""
    elements = list(elements)
    n = len(elements)
    processos = max(1, min(processos or os.cpu_count() or 1, n or 1))
    cada = cada or max(1, n // 20)
    t0 = time.time()
    if titol:
        print(f"{titol}: {n} feines amb {processos} processos", flush=True)
    # mida = feines per tros; les feines llargues (blocs de dies seguits) van d'una en una
    mida = mida or max(1, min(50, n // (processos * 8) or 1))
    trossos = [elements[i:i + mida] for i in range(0, n, mida)]
    fets = [0]
    seguent = [cada]
    ultim = [time.time()]

    def _avis(r):
        ultim[0] = time.time()
        fets[0] += len(r)
        if titol and (fets[0] >= seguent[0] or fets[0] == n):
            seguent[0] += cada
            t = time.time() - t0
            print(f"  {fets[0]}/{n}  ({t:.0f} s)", flush=True)

    pool = mp.Pool(processos, initializer=_init_treballador, initargs=(initializer, initargs),
                   maxtasksperchild=20)
    try:
        asinc = [pool.apply_async(_tros, (funcio, t), callback=_avis) for t in trossos]
        res = []
        for a in asinc:
            while True:
                try:
                    res += a.get(timeout=0.5)     # amb timeout, Ctrl+C es pot atendre
                    break
                except mp.TimeoutError:
                    if time.time() - ultim[0] > espera_maxima:
                        raise Penjat(f"{espera_maxima} s sense acabar cap feina ({fets[0]}/{n} fetes): "
                                     "algun proces s'ha penjat o ha petat")
                    continue
        pool.close()
    except KeyboardInterrupt:
        print("\nAturat per l'usuari.", flush=True)
        pool.terminate()
        pool.join()
        sys.exit(130)
    except Penjat as e:
        print(f"\nERROR: {e}. Prova-ho amb menys processos (--processos 4) i envia aquest missatge.",
              flush=True)
        pool.terminate()
        pool.join()
        sys.exit(1)
    except BaseException:
        pool.terminate()
        raise
    pool.join()
    return res


class Penjat(Exception):
    pass


def _tros(funcio, elements):
    return [funcio(e) for e in elements]
