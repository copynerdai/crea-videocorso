#!/usr/bin/env python3
"""Controlla il progetto prima della consegna: struttura, file, media, sincronia.

  python3 controlla.py <cartella-progetto>

Scrive controlli/rapporto.json e stampa l'esito. Esce con 1 se qualcosa non va.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comune import Errore, leggi_json, percorso_interno, scrivi_json  # noqa: E402


def sonda(file: Path) -> dict:
    esito = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(file)],
        capture_output=True, text=True)
    if esito.returncode != 0:
        raise Errore(f"ffprobe non legge {file.name}")
    return json.loads(esito.stdout)


def decodifica(file: Path) -> str | None:
    esito = subprocess.run(["ffmpeg", "-v", "error", "-i", str(file), "-f", "null", "-"],
                           capture_output=True, text=True)
    return None if esito.returncode == 0 else (esito.stderr.strip()[:300] or f"uscita {esito.returncode}")


def volume_massimo(file: Path) -> float | None:
    esito = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(file),
                            "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True)
    trovato = re.search(r"max_volume:\s*(-?inf|[-+0-9.]+) dB", esito.stderr)
    if not trovato or trovato.group(1) == "-inf":
        return None
    return float(trovato.group(1))


def principale() -> int:
    analizzatore = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizzatore.add_argument("progetto")
    analizzatore.add_argument("--senza-media", action="store_true", help="Salta i controlli su audio e video")
    argomenti = analizzatore.parse_args()

    progetto = Path(argomenti.progetto).expanduser().resolve()
    manifesto = leggi_json(progetto / "manifesti/manifesto.json")
    piano = leggi_json(progetto / "piano/slide.json")["lezioni"]
    richieste = manifesto["consegne"].get("richieste", {})
    guasti: list[str] = []
    avvisi: list[str] = []

    # struttura
    pagine = [s["pagina"] for s in manifesto["slide"]]
    if sorted(pagine) != list(range(1, len(pagine) + 1)):
        guasti.append("Le pagine delle slide non sono una sequenza continua da 1")
    nel_piano = sum(len(v) for v in piano.values())
    if nel_piano != len(manifesto["slide"]):
        guasti.append(f"Il piano ha {nel_piano} slide, il manifesto {len(manifesto['slide'])}: ricostruisci")
    for lezione in manifesto["lezioni"]:
        if not any(u["lezione_id"] == lezione["id"] for u in manifesto["unita"]):
            guasti.append(f"Lezione senza testo per la voce: {lezione['id']}")
        if lezione["id"] not in piano:
            guasti.append(f"Lezione assente dal piano: {lezione['id']}")

    # mazzo
    html = progetto / manifesto["consegne"]["html"]
    if not html.exists():
        guasti.append("Manca il mazzo HTML")
    else:
        sorgente = html.read_text(encoding="utf-8")
        quante = sorgente.count('class="slide ')
        if quante != len(manifesto["slide"]):
            guasti.append(f"L'HTML ha {quante} slide, il manifesto {len(manifesto['slide'])}")
        if "http://" in sorgente or re.search(r'src="https?://', sorgente):
            avvisi.append("Il mazzo carica qualcosa da internet: non sarà autonomo")

    if richieste.get("pdf"):
        pdf = progetto / manifesto["consegne"]["pdf"]
        if not pdf.exists() or pdf.stat().st_size < 10_000:
            guasti.append("PDF mancante o vuoto")

    # voce: il segno della voce finta si cerca anche nei file, così non si perde mai
    di_prova = manifesto["voce"].get("stato") == "prova" or any(u.get("prova") for u in manifesto["unita"])
    for elemento in list(manifesto["unita"]) + list(manifesto["lezioni"]):
        relativo = elemento.get("file_allineamento")
        if not relativo:
            continue
        file_allineamento = progetto / relativo
        if file_allineamento.exists() and leggi_json(file_allineamento).get("prova"):
            di_prova = True
            break
    if di_prova:
        avvisi.append("ATTENZIONE: la voce è quella finta di collaudo, non si consegna")
    da_fare = [u["id"] for u in manifesto["unita"] if not u.get("file_audio")]
    if richieste.get("audio") and da_fare:
        guasti.append(f"Unità senza voce: {len(da_fare)} (prima {da_fare[0]})")

    # media
    if not argomenti.senza_media and richieste.get("audio") and not da_fare:
        if shutil.which("ffprobe") is None:
            avvisi.append("ffprobe non installato: controlli su audio e video saltati")
        else:
            for lezione in manifesto["lezioni"]:
                audio = percorso_interno(progetto, lezione["file_audio"], lezione["id"])
                if not audio.exists():
                    guasti.append(f"Traccia mancante: {lezione['id']}")
                    continue
                guasto = decodifica(audio)
                if guasto:
                    guasti.append(f"Audio danneggiato in {lezione['id']}: {guasto}")
                picco = volume_massimo(audio)
                if picco is None:
                    guasti.append(f"Traccia silenziosa: {lezione['id']}")
                elif picco > -0.5:
                    avvisi.append(f"Audio al limite in {lezione['id']}: picco {picco} dB")

                if not richieste.get("video"):
                    continue
                relativo = lezione.get("video_consegna")
                if not relativo:
                    guasti.append(f"Video non montato: {lezione['id']}")
                    continue
                video = percorso_interno(progetto, relativo, lezione["id"])
                if not video.exists():
                    guasti.append(f"Video mancante: {relativo}")
                    continue
                dati = sonda(video)
                flussi = {s["codec_type"]: s for s in dati.get("streams", [])}
                if "video" not in flussi or "audio" not in flussi:
                    guasti.append(f"Il video di {lezione['id']} non ha entrambe le tracce")
                    continue
                if (flussi["video"].get("width"), flussi["video"].get("height")) != (1920, 1080):
                    guasti.append(f"Il video di {lezione['id']} non è 1920×1080")
                durata_video = float(dati["format"]["duration"])
                durata_audio = (lezione.get("durata_ms") or 0) / 1000
                if durata_audio and abs(durata_video - durata_audio) > 0.75:
                    guasti.append(f"Video e voce non combaciano in {lezione['id']}: "
                                  f"{durata_video:.1f}s contro {durata_audio:.1f}s")
                ingressi = [v["inizio_ms"] for v in lezione.get("ingressi_slide", [])]
                if ingressi != sorted(ingressi):
                    guasti.append(f"Ingressi delle slide fuori ordine in {lezione['id']}")
                if ingressi and ingressi[-1] / 1000 >= durata_video:
                    guasti.append(f"Una slide entra dopo la fine del video in {lezione['id']}")

    # approvazioni
    mancanti = [a["passaggio"] for a in manifesto.get("approvazioni", []) if a.get("stato") == "da_fare"]
    if mancanti:
        avvisi.append("Passaggi ancora da approvare: " + ", ".join(mancanti))

    esito = "NON PASSA" if guasti else "PASSA"
    rapporto = {
        "schema": "crea-videocorso/1",
        "corso": manifesto["progetto"]["titolo"],
        "quando": datetime.now(timezone.utc).isoformat(),
        "esito": esito,
        "guasti": guasti,
        "avvisi": avvisi,
        "numeri": {
            "lezioni": len(manifesto["lezioni"]),
            "slide": len(manifesto["slide"]),
            "unita_voce": len(manifesto["unita"]),
            "durata_audio_secondi": manifesto["consegne"].get("durata_audio_secondi"),
        },
    }
    scrivi_json(progetto / "controlli/rapporto.json", rapporto)
    print(f"Esito: {esito}")
    for guasto in guasti:
        print(f"  guasto · {guasto}")
    for avviso in avvisi:
        print(f"  avviso · {avviso}")
    print(f"Rapporto: {progetto / 'controlli/rapporto.json'}")
    return 1 if guasti else 0


if __name__ == "__main__":
    try:
        raise SystemExit(principale())
    except Errore as errore:
        print(str(errore), file=sys.stderr)
        raise SystemExit(2)
