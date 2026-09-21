#!/usr/bin/env python3
"""Unisce i segmenti di voce in una traccia per lezione e fonde gli allineamenti.

  python3 unisci-audio.py <cartella-progetto>
  python3 unisci-audio.py <cartella-progetto> --lezione m01-l02
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comune import Errore, leggi_json, nome_sicuro, percorso_interno, scrivi_json  # noqa: E402


def serve(programma: str) -> None:
    if shutil.which(programma) is None:
        raise Errore(f"Manca {programma}. Su Mac si installa con «brew install ffmpeg».")


def durata(file: Path) -> float:
    esito = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(file)],
        check=True, capture_output=True, text=True)
    return float(esito.stdout.strip())


def concatena(ingressi: list[Path], uscita: Path) -> None:
    uscita.parent.mkdir(parents=True, exist_ok=True)
    if len(ingressi) == 1:
        shutil.copy2(ingressi[0], uscita)
        return
    with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as maniglia:
        elenco = Path(maniglia.name)
        for file in ingressi:
            maniglia.write("file '{}'\n".format(str(file).replace("'", "'\\''")))
    try:
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
             "-i", str(elenco), "-map", "0:a:0", "-c:a", "libmp3lame", "-b:a", "128k",
             "-ar", "44100", "-ac", "1", str(uscita)], check=True)
    finally:
        elenco.unlink(missing_ok=True)


def aggiungi(destinazione: dict, origine: dict, scarto: float) -> None:
    for chiave in ("alignment", "normalized_alignment"):
        dati = origine.get(chiave)
        if not isinstance(dati, dict):
            continue
        caratteri = dati.get("characters")
        inizi = dati.get("character_start_times_seconds")
        fini = dati.get("character_end_times_seconds")
        if not (isinstance(caratteri, list) and isinstance(inizi, list) and isinstance(fini, list)):
            continue
        quanti = min(len(caratteri), len(inizi), len(fini))
        unito = destinazione.setdefault(chiave, {
            "characters": [], "character_start_times_seconds": [], "character_end_times_seconds": []})
        if unito["characters"]:
            unito["characters"].append("\n")
            unito["character_start_times_seconds"].append(round(scarto, 6))
            unito["character_end_times_seconds"].append(round(scarto, 6))
        unito["characters"].extend(caratteri[:quanti])
        unito["character_start_times_seconds"].extend(round(float(v) + scarto, 6) for v in inizi[:quanti])
        unito["character_end_times_seconds"].extend(round(float(v) + scarto, 6) for v in fini[:quanti])


def principale() -> int:
    analizzatore = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizzatore.add_argument("progetto")
    analizzatore.add_argument("--lezione")
    argomenti = analizzatore.parse_args()

    serve("ffmpeg")
    serve("ffprobe")
    progetto = Path(argomenti.progetto).expanduser().resolve()
    file_manifesto = progetto / "manifesti/manifesto.json"
    manifesto = leggi_json(file_manifesto)

    unita_per_lezione: dict[str, list[dict]] = {}
    for unita in manifesto["unita"]:
        unita_per_lezione.setdefault(unita["lezione_id"], []).append(unita)

    lezioni = [l for l in manifesto["lezioni"] if not argomenti.lezione or l["id"] == argomenti.lezione]
    if not lezioni:
        raise Errore("Nessuna lezione corrisponde al filtro")

    totale = 0.0
    for indice, lezione in enumerate(lezioni, 1):
        pezzi = sorted(unita_per_lezione.get(lezione["id"], []), key=lambda u: u["ordine"])
        if not pezzi:
            raise Errore(f"Nessuna unità per la lezione {lezione['id']}")
        file_audio: list[Path] = []
        allineamenti: list[dict] = []
        for unita in pezzi:
            if not unita.get("file_audio") or not unita.get("file_allineamento"):
                raise Errore(f"Unità senza voce: {unita['id']}. Lancia prima genera-voce.py")
            audio = percorso_interno(progetto, unita["file_audio"], unita["id"])
            allineamento = percorso_interno(progetto, unita["file_allineamento"], unita["id"])
            if not audio.exists() or not allineamento.exists():
                raise Errore(f"File mancante per {unita['id']}")
            file_audio.append(audio)
            allineamenti.append(leggi_json(allineamento))

        traccia = percorso_interno(progetto, lezione["file_audio"], lezione["id"])
        concatena(file_audio, traccia)
        lunghezza = durata(traccia)
        durate = [durata(f) for f in file_audio]

        unito = {
            "lezione_id": lezione["id"],
            "generato": datetime.now(timezone.utc).isoformat(),
            "unita": [u["id"] for u in pezzi],
            "durata_secondi": round(lunghezza, 6),
            "prova": any(a.get("prova") for a in allineamenti),
        }
        scarto = 0.0
        scarti = []
        for allineamento, lunghezza_pezzo in zip(allineamenti, durate):
            scarti.append(round(scarto, 6))
            aggiungi(unito, allineamento, scarto)
            scarto += lunghezza_pezzo
        unito["scarti_secondi"] = scarti
        unito["durate_segmenti"] = [round(v, 6) for v in durate]
        scrivi_json(percorso_interno(progetto, lezione["file_allineamento"], lezione["id"]), unito)

        export = progetto / "consegne/audio" / (nome_sicuro(lezione["nome_export"]) + ".mp3")
        export.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(traccia, export)
        lezione["durata_ms"] = round(lunghezza * 1000)
        lezione["audio_consegna"] = str(export.relative_to(progetto))
        totale += lunghezza
        print(f"[{indice:02d}/{len(lezioni):02d}] {lezione['id']} · {lunghezza / 60:.1f} minuti", flush=True)

    if not argomenti.lezione:
        manifesto["progetto"]["stato"] = "audio_completo"
        manifesto["consegne"]["durata_audio_secondi"] = round(totale, 3)
    scrivi_json(file_manifesto, manifesto)
    print(f"Audio unito: {len(lezioni)} lezioni · {totale / 60:.1f} minuti")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(principale())
    except Errore as errore:
        print(str(errore), file=sys.stderr)
        raise SystemExit(2)
