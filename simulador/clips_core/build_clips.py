"""Construeix clips_core/soar.clp a partir dels moduls CLIPS.

Els fitxers de ``modules.txt`` son la font canònica. El resultat concatenat es
manté com un únic .clp perquè clipspy, E11 i els scripts històrics puguin
continuar treballant exactament igual que amb la v1_8 monolítica.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

ARREL = Path(__file__).resolve().parent
MANIFEST = ARREL / "modules.txt"
SORTIDA = ARREL / "soar.clp"
BASELINE = ARREL.parent.parent / "history" / "clips" / "simulator" / "soar_v1_8.clp"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def construeix() -> None:
    moduls = [x.strip() for x in MANIFEST.read_text(encoding="utf-8").splitlines()
              if x.strip() and not x.lstrip().startswith("#")]
    contingut = "".join((ARREL / rel).read_text(encoding="utf-8") for rel in moduls)
    # Escriu bytes UTF-8 amb LF canònic. Això evita que Windows transformi
    # els salts de línia a CRLF i permet comparar el build byte a byte amb v1_8.
    SORTIDA.write_bytes(contingut.encode("utf-8"))
    print(f"Generat: {SORTIDA}")
    print(f"Mòduls: {len(moduls)}")
    print(f"SHA256: {sha256(SORTIDA)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-baseline", action="store_true",
                    help="comprova que el build segueix sent idèntic a soar_v1_8.clp")
    args = ap.parse_args()
    construeix()
    if args.check_baseline:
        igual = SORTIDA.read_bytes() == BASELINE.read_bytes()
        print("Baseline v1_8:", "IDENTIC" if igual else "DIFERENT")
        raise SystemExit(0 if igual else 1)


if __name__ == "__main__":
    main()
