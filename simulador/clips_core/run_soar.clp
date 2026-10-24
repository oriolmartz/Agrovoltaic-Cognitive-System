; ============================================================================
; run_soar.clp - execucio manual minima de la versio modular canonica
;
; Des de simulador/clips_core:
;   clips -f run_soar.clp
;
; La logica cognitiva NO viu en aquest fitxer. soar.clp es genera a partir
; dels moduls de modules.txt amb:
;   python build_clips.py --check-baseline
; ============================================================================

(load "soar.clp")
(reset)
(run)
