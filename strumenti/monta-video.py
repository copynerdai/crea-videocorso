#!/usr/bin/env python3
"""Aggancia ogni slide al momento in cui la voce la nomina e monta i video.

  python3 monta-video.py <cartella-progetto>
  python3 monta-video.py <cartella-progetto> --lezione m01-l02

Il punto d'ingresso di ogni slide è il campo «entra_da» del piano: una frase
presa dal testo. Lo si cerca fra i tempi per carattere dell'allineamento.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comune import Errore, canonico_con_mappa, leggi_json, nome_sicuro, percorso_interno, scrivi_json  # noqa: E402


def serve(programma: str) -> None:
    if shutil.which(programma) is None:
        raise Errore(f"Manca {programma}. Su Mac si installa con «brew install ffmpeg».")


def momento(aggancio: str, testo: str, inizi: list[float], da: int) -> tuple[float, int]:
    pagliaio, mappa = canonico_con_mappa(testo)
    ago, _ = canonico_con_mappa(aggancio)
    if not ago:
        raise Errore(f"Punto d'ingresso vuoto: {aggancio!r}")
    partenza = 0
    for posizione, originale in enumerate(mappa):
        if originale >= da:
            partenza = posizione
            break
    trovato = pagliaio.find(ago, partenza)
    if trovato < 0:
        # dopo la normalizzazione del fornitore una frase può cambiare:
        # le prime otto parole bastano a riconoscerla senza ambiguità.
        ridotto = " ".join(ago.split()[:8])
        trovato = pagliaio.find(ridotto, partenza)
    if trovato < 0:
        raise Errore(f"Punto d'ingresso non trovato nella voce: {aggancio!r}")
    indice = mappa[trovato]
    if indice >= len(inizi):
        raise Errore(f"Manca il tempo per il punto d'ingresso: {aggancio!r}")
    return float(inizi[indice]), indice + max(1, len(aggancio) // 2)


def principale() -> int:
    analizzatore = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizzatore.add_argument("progetto")
    analizzatore.add_argument("--lezione")
    analizzatore.add_argument("--qualita", type=int, default=18, help="CRF di x264: più basso, più pesante")
    argomenti = analizzatore.parse_args()

    serve("ffmpeg")
    progetto = Path(argomenti.progetto).expanduser().resolve()
    file_manifesto = progetto / "manifesti/manifesto.json"
    manifesto = leggi_json(file_manifesto)
    piano = leggi_json(progetto / "piano/slide.json")["lezioni"]
    pagina_di = {s["id"]: s["pagina"] for s in manifesto["slide"]}

    lezioni = [l for l in manifesto["lezioni"] if not argomenti.lezione or l["id"] == argomenti.lezione]
    if not lezioni:
        raise Errore("Nessuna lezione corrisponde al filtro")

    totale = 0.0
    for indice, lezione in enumerate(lezioni, 1):
        allineamento = leggi_json(percorso_interno(progetto, lezione["file_allineamento"], lezione["id"]))
        tempi = allineamento.get("normalized_alignment") or allineamento.get("alignment")
        if not isinstance(tempi, dict):
            raise Errore(f"Allineamento assente per {lezione['id']}. Lancia prima unisci-audio.py")
        testo = "".join(tempi["characters"])
        inizi = tempi["character_start_times_seconds"]
        lunghezza = float(allineamento["durata_secondi"])
        slide = piano.get(lezione["id"]) or []
        if not slide:
            raise Errore(f"Il piano non ha slide per {lezione['id']}")

        partenze: list[float] = []
        da = 0
        for posizione, voce in enumerate(slide):
            aggancio = voce["entra_da"]
            if posizione == 0 or aggancio == "INIZIO":
                inizio = 0.0
            else:
                inizio, da = momento(aggancio, testo, inizi, da)
            if partenze and inizio <= partenze[-1]:
                raise Errore(f"Punti d'ingresso fuori ordine in {lezione['id']}: {aggancio!r}")
            partenze.append(inizio)
        partenze.append(lunghezza)

        voci: list[tuple[Path, float]] = []
        for posizione, voce in enumerate(slide):
            quanto = partenze[posizione + 1] - partenze[posizione]
            if quanto <= 0.04:
                raise Errore(f"Slide troppo breve in {lezione['id']}: {voce['id']}")
            immagine = progetto / "tmp/slide" / f"pagina-{pagina_di[voce['id']]:03d}.png"
            if not immagine.exists():
                raise Errore(f"Manca l'immagine {immagine.name}. Lancia prima renderizza.py")
            voci.append((immagine, quanto))

        uscita = progetto / "consegne/video" / (nome_sicuro(lezione["nome_export"]) + ".mp4")
        uscita.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as maniglia:
            elenco = Path(maniglia.name)
            for immagine, quanto in voci:
                maniglia.write("file '{}'\n".format(str(immagine).replace("'", "'\\''")))
                maniglia.write(f"duration {quanto:.6f}\n")
            maniglia.write("file '{}'\n".format(str(voci[-1][0]).replace("'", "'\\''")))
        try:
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "concat", "-safe", "0", "-i", str(elenco),
                "-i", str(percorso_interno(progetto, lezione["file_audio"], lezione["id"])),
                "-map", "0:v:0", "-map", "1:a:0", "-r", "25",
                "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
                "-crf", str(argomenti.qualita), "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-t", f"{lunghezza:.6f}",
                "-movflags", "+faststart", str(uscita),
            ], check=True)
        finally:
            elenco.unlink(missing_ok=True)

        lezione["video_consegna"] = str(uscita.relative_to(progetto))
        lezione["ingressi_slide"] = [
            {"slide_id": voce["id"], "inizio_ms": round(inizio * 1000)}
            for voce, inizio in zip(slide, partenze[:-1])
        ]
        totale += lunghezza
        print(f"[{indice:02d}/{len(lezioni):02d}] {lezione['id']} · {len(slide)} slide · {lunghezza / 60:.1f} minuti", flush=True)

    if not argomenti.lezione:
        manifesto["progetto"]["stato"] = "video_completo"
        manifesto["consegne"]["durata_video_secondi"] = round(totale, 3)
    scrivi_json(file_manifesto, manifesto)
    print(f"Video montati: {len(lezioni)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(principale())
    except Errore as errore:
        print(str(errore), file=sys.stderr)
        raise SystemExit(2)
