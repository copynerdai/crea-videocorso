#!/usr/bin/env python3
"""Controlla che il computer abbia tutto il necessario e prepara segreti.env.

  python3 prepara-ambiente.py --controlla
  python3 prepara-ambiente.py
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comune import CASA, PACCHETTI_VISUAL, SEGRETI  # noqa: E402

MODELLO_SEGRETI = """# Chiavi di crea-videocorso. Una per riga, senza spazi né virgolette.
# Questo file non si incolla mai in chat.
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
"""


def versione(programma: str) -> str | None:
    percorso = shutil.which(programma)
    if not percorso:
        return None
    try:
        esito = subprocess.run([percorso, "-version"], capture_output=True, text=True, timeout=20)
        return esito.stdout.splitlines()[0] if esito.stdout else percorso
    except Exception:
        return percorso


def browser() -> str | None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import importlib.util

    specifica = importlib.util.spec_from_file_location("renderizza", Path(__file__).resolve().parent / "renderizza.py")
    modulo = importlib.util.module_from_spec(specifica)  # type: ignore[arg-type]
    specifica.loader.exec_module(modulo)  # type: ignore[union-attr]
    try:
        return modulo.trova_browser()
    except Exception:
        return None


def principale() -> int:
    analizzatore = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizzatore.add_argument("--controlla", action="store_true", help="Riferisce e basta, senza creare nulla")
    argomenti = analizzatore.parse_args()

    mancano: list[str] = []
    print(f"Python: {sys.version.split()[0]}")
    if sys.version_info < (3, 10):
        mancano.append("Python 3.10 o successivo")

    for programma, come in (("ffmpeg", "brew install ffmpeg"), ("ffprobe", "brew install ffmpeg")):
        trovato = versione(programma)
        print(f"{programma}: {trovato or 'MANCA'}")
        if not trovato:
            mancano.append(f"{programma} (si installa con «{come}»)")

    trovato = browser()
    print(f"browser: {trovato or 'MANCA'}")
    if not trovato:
        mancano.append("Google Chrome o Chromium")

    if not argomenti.controlla:
        CASA.mkdir(parents=True, exist_ok=True)
        PACCHETTI_VISUAL.mkdir(parents=True, exist_ok=True)
        if not SEGRETI.exists():
            SEGRETI.write_text(MODELLO_SEGRETI, encoding="utf-8")
        SEGRETI.chmod(0o600)
        print(f"Cartella personale: {CASA}")
        print(f"Chiavi da riempire in: {SEGRETI}")
    else:
        print(f"segreti.env: {'c’è' if SEGRETI.exists() else 'da creare'}")
        pacchetti = sorted(p.name for p in PACCHETTI_VISUAL.glob("*") if p.is_dir()) if PACCHETTI_VISUAL.exists() else []
        print(f"pacchetti visuali installati: {', '.join(pacchetti) if pacchetti else 'nessuno'}")

    if mancano:
        print("\nManca ancora: " + "; ".join(mancano))
        return 1
    print("\nAmbiente pronto")
    return 0


if __name__ == "__main__":
    raise SystemExit(principale())
