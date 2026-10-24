"""Construeix clips_core/soar.clp a partir dels moduls CLIPS.

Els fitxers de ``modules.txt`` son la font canonica. ``soar.clp`` es un artefacte
generat per compatibilitat amb clipspy i els experiments. La v1.8 historica es
conserva a history/, pero des de la integracio RDF el nucli actiu divergeix de
manera intencional: la topologia ja no viu duplicada en un deffacts.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

ARREL = Path(__file__).resolve().parent
MANIFEST = ARREL / "modules.txt"
SORTIDA = ARREL / "soar.clp"
BASELINE = ARREL.parent.parent / "history" / "clips" / "simulator" / "soar_v1_8.clp"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def contingut_modular() -> tuple[list[str], bytes]:
    moduls = [x.strip() for x in MANIFEST.read_text(encoding="utf-8").splitlines()
              if x.strip() and not x.lstrip().startswith("#")]
    text = "".join((ARREL / rel).read_text(encoding="utf-8") for rel in moduls)
    return moduls, text.encode("utf-8")


def construeix() -> None:
    moduls, data = contingut_modular()
    # Bytes UTF-8 amb LF canonic: evita conversions CRLF a Windows.
    SORTIDA.write_bytes(data)
    print(f"Generat: {SORTIDA}")
    print(f"Moduls: {len(moduls)}")
    print(f"SHA256: {sha256(SORTIDA)}")


def comprova_generat() -> bool:
    moduls, data = contingut_modular()
    igual = SORTIDA.is_file() and SORTIDA.read_bytes() == data
    print(f"Moduls: {len(moduls)}")
    print("soar.clp:", "ACTUALITZAT" if igual else "DESACTUALITZAT")
    if SORTIDA.is_file():
        print(f"SHA256: {sha256(SORTIDA)}")
    return igual


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-generated", action="store_true",
                    help="comprova que soar.clp correspon exactament als moduls actuals")
    ap.add_argument("--check-baseline", action="store_true",
                    help="compara amb la v1.8 historica (des de la integracio RDF s'espera DIFERENT)")
    args = ap.parse_args()

    if args.check_generated:
        raise SystemExit(0 if comprova_generat() else 1)

    construeix()
    if args.check_baseline:
        igual = SORTIDA.read_bytes() == BASELINE.read_bytes()
        print("Baseline v1_8:", "IDENTIC" if igual else "DIFERENT")
        raise SystemExit(0 if igual else 1)


if __name__ == "__main__":
    main()
