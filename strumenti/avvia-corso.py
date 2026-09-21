#!/usr/bin/env python3
"""Crea la cartella di un videocorso e la sua scheda corso.json.

  python3 avvia-corso.py <cartella-progetto> --titolo "Titolo" --sorgenti <cartella-testi>
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comune import Errore, leggi_json, scivola, scrivi_json  # noqa: E402

CARTELLE = (
    "intake/sorgenti",
    "intake/marchio",
    "manifesti",
    "piano",
    "slide",
    "voce/testi/unita",
    "voce/segmenti",
    "voce/allineamenti",
    "voce/lezioni",
    "consegne/audio",
    "consegne/video",
    "consegne/pdf",
    "controlli/immagini",
    "tmp/slide",
)


def principale() -> int:
    analizzatore = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizzatore.add_argument("progetto", help="Cartella del progetto da creare")
    analizzatore.add_argument("--titolo", help="Titolo del corso")
    analizzatore.add_argument("--sottotitolo", default="")
    analizzatore.add_argument("--sorgenti", help="Cartella con i testi approvati delle lezioni")
    analizzatore.add_argument("--marchio", help="Cartella con logo e caratteri del marchio")
    analizzatore.add_argument("--pacchetto-visuale", action="append", default=[], help="Pacchetto di disegni aggiuntivo, ripetibile")
    argomenti = analizzatore.parse_args()

    progetto = Path(argomenti.progetto).expanduser().resolve()
    scheda = progetto / "corso.json"
    if scheda.exists():
        dati = leggi_json(scheda)
        print(f"Scheda già presente: {scheda}")
    else:
        if not argomenti.titolo or not argomenti.sorgenti:
            raise Errore("Per un progetto nuovo servono --titolo e --sorgenti")
        sorgenti = Path(argomenti.sorgenti).expanduser().resolve()
        if not sorgenti.is_dir():
            raise Errore(f"Cartella dei testi non trovata: {sorgenti}")
        modello = leggi_json(Path(__file__).resolve().parents[1] / "riferimenti" / "corso-modello.json")
        modello["corso"].update({
            "slug": scivola(argomenti.titolo),
            "titolo": argomenti.titolo,
            "sottotitolo": argomenti.sottotitolo,
            "titolo_breve": argomenti.titolo,
        })
        modello["sorgenti"]["cartella"] = str(sorgenti)
        if argomenti.marchio:
            modello["marchio"]["cartella"] = str(Path(argomenti.marchio).expanduser().resolve())
        if argomenti.pacchetto_visuale:
            modello["visuali"]["pacchetti"] = argomenti.pacchetto_visuale
        dati = modello

    for relativo in CARTELLE:
        (progetto / relativo).mkdir(parents=True, exist_ok=True)
    if not scheda.exists():
        scrivi_json(scheda, dati)

    marchio = (dati.get("marchio") or {}).get("cartella")
    if marchio:
        origine = Path(marchio).expanduser()
        if origine.is_dir():
            for file in origine.rglob("*"):
                if file.is_file() and file.suffix.lower() in {".ttf", ".otf", ".woff2", ".png", ".webp", ".jpg", ".jpeg", ".svg"}:
                    destinazione = progetto / "intake/marchio" / file.relative_to(origine)
                    destinazione.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file, destinazione)
        else:
            print(f"Attenzione: cartella del marchio non trovata: {origine}")

    print(f"Progetto pronto: {progetto}")
    print(f"Scheda del corso: {scheda}")
    print("Prossimo passo: controlla la scheda, poi lancia costruisci-slide.py")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(principale())
    except Errore as errore:
        print(str(errore), file=sys.stderr)
        raise SystemExit(2)
