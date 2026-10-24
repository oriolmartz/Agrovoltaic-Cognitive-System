; ============================================================================
; run_soar.clp - smoke test manual del nucli modular
;
; Des de simulador/clips_core:
;   clips -f run_soar.clp
;
; IMPORTANT: la topologia activa es carrega des de ontologia_model.rdf a traves
; de Python/clipspy (ontology_loader.py). Per tant, aquest fitxer nomes comprova
; que el nucli es pot carregar i resetejar; per executar un cicle complet useu:
;   cd ..
;   python simulador.py escenaris/dia_normal.json
;
; La logica cognitiva NO viu en aquest fitxer. soar.clp es genera amb:
;   python build_clips.py
; ============================================================================

(load "soar.clp")
(reset)
