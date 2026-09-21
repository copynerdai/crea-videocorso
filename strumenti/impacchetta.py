#!/usr/bin/env python3
"""Prepara la cartella finale da consegnare, dopo che i controlli sono passati.

  python3 impacchetta.py <cartella-progetto> --dove "<cartella di destinazione>"
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comune import Errore, leggi_json, nome_sicuro  # noqa: E402


def durata_leggibile(secondi: float) -> str:
    interi = round(secondi)
    ore, resto = divmod(interi, 3600)
    minuti, secondi_rimasti = divmod(resto, 60)
    return f"{ore}:{minuti:02d}:{secondi_rimasti:02d}"


def principale() -> int:
    analizzatore = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizzatore.add_argument("progetto")
    analizzatore.add_argument("--dove", required=True, help="Cartella dove creare il pacchetto")
    analizzatore.add_argument("--anche-se-di-prova", action="store_true",
                              help="Impacchetta anche con la voce finta: solo per mostrare il formato")
    argomenti = analizzatore.parse_args()

    progetto = Path(argomenti.progetto).expanduser().resolve()
    manifesto = leggi_json(progetto / "manifesti/manifesto.json")
    rapporto_file = progetto / "controlli/rapporto.json"
    if not rapporto_file.exists():
        raise Errore("Manca il rapporto dei controlli: lancia prima controlla.py")
    rapporto = leggi_json(rapporto_file)
    if rapporto.get("esito") != "PASSA":
        raise Errore("I controlli non sono passati: risolvi i guasti elencati in controlli/rapporto.json")
    di_prova = any("voce è quella finta" in a for a in rapporto.get("avvisi", []))
    if di_prova and not argomenti.anche_se_di_prova:
        raise Errore("Il progetto ha la voce finta di collaudo: non si consegna. "
                     "Rigenera la voce vera, oppure usa --anche-se-di-prova per un pacchetto di esempio.")

    titolo = manifesto["progetto"]["titolo"]
    destinazione = Path(argomenti.dove).expanduser().resolve() / nome_sicuro(titolo)
    if destinazione.exists():
        shutil.rmtree(destinazione)
    (destinazione / "Video").mkdir(parents=True)
    (destinazione / "Audio").mkdir(parents=True)
    (destinazione / "Slide").mkdir(parents=True)

    righe = []
    for lezione in manifesto["lezioni"]:
        for campo, sotto in (("video_consegna", "Video"), ("audio_consegna", "Audio")):
            relativo = lezione.get(campo)
            if not relativo:
                continue
            origine = progetto / relativo
            if origine.exists():
                shutil.copy2(origine, destinazione / sotto / origine.name)
        righe.append(f"- {lezione['nome_export']} — {durata_leggibile((lezione.get('durata_ms') or 0) / 1000)}")

    pdf = progetto / manifesto["consegne"]["pdf"]
    if pdf.exists():
        shutil.copy2(pdf, destinazione / "Slide" / pdf.name)
    html = progetto / manifesto["consegne"]["html"]
    if html.exists():
        shutil.copy2(html, destinazione / "Slide" / f"{nome_sicuro(titolo)} - slide.html")

    totale = manifesto["consegne"].get("durata_audio_secondi") or 0
    avviso = ("\n> Questo pacchetto contiene la voce finta di collaudo e non va consegnato.\n"
              if di_prova else "")
    (destinazione / "LEGGIMI.md").write_text(
        f"""# {titolo}

{manifesto['progetto'].get('pubblico') or ''}
{avviso}
Pacchetto preparato il {date.today().strftime('%d/%m/%Y')}.

## Cosa c'è dentro

- **Video**: un file MP4 per lezione, 1920×1080, voce e slide già sincronizzate.
- **Audio**: la sola voce di ogni lezione, in MP3.
- **Slide**: il PDF di tutte le slide e la stessa presentazione in HTML, che si apre in un browser e si può modificare.

Durata complessiva: {durata_leggibile(totale)}.

## Lezioni

{chr(10).join(righe)}

## Limiti dichiarati

{manifesto['progetto'].get('validazione_professionale', 'non eseguita')}
""", encoding="utf-8")

    print(f"Pacchetto pronto: {destinazione}")
    print(f"{len(manifesto['lezioni'])} lezioni · {durata_leggibile(totale)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(principale())
    except Errore as errore:
        print(str(errore), file=sys.stderr)
        raise SystemExit(2)
