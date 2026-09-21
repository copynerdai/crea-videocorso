#!/usr/bin/env python3
"""Prepara o genera la voce narrante delle lezioni.

  python3 genera-voce.py <cartella-progetto>                 # solo il piano e il costo
  python3 genera-voce.py <cartella-progetto> --esegui        # chiama ElevenLabs (a pagamento)
  python3 genera-voce.py <cartella-progetto> --prova         # voce finta di collaudo, gratis

Senza --esegui non parte nessuna chiamata a pagamento. La modalità --prova usa
la voce di sistema del Mac e serve solo a vedere come si muove il montaggio:
non si consegna mai al cliente.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comune import Errore, impronta_testo, leggi_json, percorso_interno, scrivi_json, segreto  # noqa: E402

RADICE = "https://api.elevenlabs.io/v1"
LIMITE_UNITA = 4500


def approvazione(manifesto: dict, passaggio: str) -> bool:
    for voce in manifesto.get("approvazioni", []):
        if voce.get("passaggio") == passaggio and voce.get("stato") in {"fatto", "approvato"}:
            return True
    return False


def prepara(progetto: Path, manifesto: dict) -> list[dict]:
    ordine_lezioni = {l["id"]: (l.get("modulo_id", ""), l.get("ordine", 0)) for l in manifesto["lezioni"]}
    pronte = []
    for unita in manifesto.get("unita", []):
        file_testo = percorso_interno(progetto, unita.get("testo"), unita["id"])
        try:
            testo = file_testo.read_text(encoding="utf-8").strip()
        except FileNotFoundError as errore:
            raise Errore(f"Manca il testo di {unita['id']}: {file_testo}") from errore
        if not testo:
            raise Errore(f"Testo vuoto: {unita['id']}")
        if len(testo) > LIMITE_UNITA:
            raise Errore(f"Unità oltre il limite prudenziale di {LIMITE_UNITA} caratteri: {unita['id']}")
        pronte.append({"unita": unita, "testo": testo, "ordine": (*ordine_lezioni.get(unita["lezione_id"], ("", 0)), unita.get("ordine", 0))})
    pronte.sort(key=lambda v: v["ordine"])
    return pronte


def chiedi_audio(*, chiave: str, voice_id: str, model_id: str, formato: str, testo: str,
                 impostazioni: dict, lingua: str, attesa: int) -> tuple[dict, str | None]:
    carico: dict = {"text": testo, "model_id": model_id}
    if impostazioni:
        carico["voice_settings"] = impostazioni
    if lingua:
        carico["language_code"] = lingua
    carico["apply_text_normalization"] = "auto"
    indirizzo = (f"{RADICE}/text-to-speech/{quote(voice_id, safe='')}/with-timestamps?"
                 + urlencode({"output_format": formato, "enable_logging": "true"}))
    richiesta = Request(
        indirizzo,
        data=json.dumps(carico).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json", "xi-api-key": chiave},
    )
    try:
        with urlopen(richiesta, timeout=attesa) as risposta:
            corpo = json.loads(risposta.read().decode("utf-8"))
            identificativo = risposta.headers.get("request-id") or risposta.headers.get("x-request-id")
    except HTTPError as errore:
        dettaglio = errore.read().decode("utf-8", errors="replace")[:600]
        raise Errore(f"ElevenLabs ha risposto {errore.code}: {dettaglio}") from errore
    except URLError as errore:
        raise Errore(f"Chiamata a ElevenLabs non riuscita: {errore.reason}") from errore
    if not isinstance(corpo, dict) or not isinstance(corpo.get("audio_base64"), str):
        raise Errore("La risposta di ElevenLabs non contiene audio")
    return corpo, identificativo


def durata_da_allineamento(corpo: dict) -> int | None:
    for chiave in ("normalized_alignment", "alignment"):
        dati = corpo.get(chiave)
        if isinstance(dati, dict):
            fini = dati.get("character_end_times_seconds")
            if isinstance(fini, list) and fini:
                numeri = [v for v in fini if isinstance(v, (int, float))]
                if numeri:
                    return round(max(numeri) * 1000)
    return None


def voce_di_prova(testo: str, destinazione: Path, velocita: int) -> dict:
    """Genera un audio con la voce di sistema e un allineamento uniforme."""
    if sys.platform != "darwin":
        raise Errore("La modalità --prova usa la voce di sistema del Mac e qui non è disponibile")
    destinazione.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as maniglia:
        grezzo = Path(maniglia.name)
    try:
        subprocess.run(["say", "-r", str(velocita), "-o", str(grezzo), testo], check=True, capture_output=True)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(grezzo),
                        "-c:a", "libmp3lame", "-b:a", "128k", "-ar", "44100", "-ac", "1", str(destinazione)], check=True)
    finally:
        grezzo.unlink(missing_ok=True)
    durata = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
         "default=noprint_wrappers=1:nokey=1", str(destinazione)],
        check=True, capture_output=True, text=True).stdout.strip())
    caratteri = list(testo)
    passo = durata / max(1, len(caratteri))
    return {
        "characters": caratteri,
        "character_start_times_seconds": [round(i * passo, 6) for i in range(len(caratteri))],
        "character_end_times_seconds": [round((i + 1) * passo, 6) for i in range(len(caratteri))],
    }


def principale() -> int:
    analizzatore = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizzatore.add_argument("progetto")
    analizzatore.add_argument("--lezione", help="Una sola lezione")
    analizzatore.add_argument("--unita", help="Una sola unità")
    analizzatore.add_argument("--esegui", action="store_true", help="Manda le richieste a pagamento")
    analizzatore.add_argument("--prova", action="store_true", help="Voce di sistema per collaudo, senza costi")
    analizzatore.add_argument("--rifai", action="store_true", help="Rigenera anche le unità già fatte")
    analizzatore.add_argument("--velocita-prova", type=int, default=180)
    analizzatore.add_argument("--attesa", type=int, default=180, help="Secondi di attesa per richiesta")
    argomenti = analizzatore.parse_args()

    if argomenti.lezione and argomenti.unita:
        raise Errore("Scegli --lezione oppure --unita, non tutti e due")
    if argomenti.esegui and argomenti.prova:
        raise Errore("--esegui e --prova si escludono")

    progetto = Path(argomenti.progetto).expanduser().resolve()
    file_manifesto = progetto / "manifesti/manifesto.json"
    manifesto = leggi_json(file_manifesto)
    pronte = prepara(progetto, manifesto)
    if not pronte:
        raise Errore("Il manifesto non elenca unità di voce")

    scelte = [v for v in pronte
              if (not argomenti.lezione or v["unita"]["lezione_id"] == argomenti.lezione)
              and (not argomenti.unita or v["unita"]["id"] == argomenti.unita)]
    if not scelte:
        raise Errore("Nessuna unità corrisponde al filtro")

    voce = manifesto.get("voce") or {}
    voice_id = voce.get("voice_id") or segreto("ELEVENLABS_VOICE_ID")
    model_id = voce.get("model_id") or "eleven_v3"
    formato = voce.get("output_format") or "mp3_44100_128"
    caratteri = sum(len(v["testo"]) for v in scelte)

    print(f"Modo: {'PROVA' if argomenti.prova else 'ESECUZIONE' if argomenti.esegui else 'SOLO PIANO'}")
    print(f"Unità: {len(scelte)} · caratteri: {caratteri} · modello: {model_id}")
    print(f"Voce impostata: {'sì' if voice_id else 'no'}")

    if not argomenti.esegui and not argomenti.prova:
        for v in scelte:
            unita = v["unita"]
            esiste = unita.get("file_audio") and percorso_interno(progetto, unita["file_audio"], unita["id"]).exists()
            print(f"{unita['id']}\t{unita['lezione_id']}\t{len(v['testo'])}\t{'già fatta' if esiste else 'da fare'}")
        print("Nessuna richiesta inviata. Aggiungi --esegui solo dopo l'approvazione della voce e della spesa.")
        return 0

    chiave = None
    if argomenti.esegui:
        if not approvazione(manifesto, "prova-voce"):
            raise Errore("Serve il passaggio «prova-voce» approvato nel manifesto prima di spendere")
        if not approvazione(manifesto, "spesa-voce"):
            raise Errore("Serve il passaggio «spesa-voce» approvato nel manifesto prima di spendere")
        chiave = segreto("ELEVENLABS_API_KEY")
        if not chiave:
            raise Errore("Manca ELEVENLABS_API_KEY in ~/.crea-videocorso/segreti.env")
        if not voice_id:
            raise Errore("Manca la voce: scrivila in corso.json oppure in segreti.env come ELEVENLABS_VOICE_ID")

    fatte = saltate = 0
    for v in scelte:
        unita = v["unita"]
        gia = unita.get("file_audio") and percorso_interno(progetto, unita["file_audio"], unita["id"]).exists()
        if gia and not argomenti.rifai:
            print(f"SALTO {unita['id']}: audio già presente")
            saltate += 1
            continue
        relativo_audio = f"voce/segmenti/{unita['id']}.mp3"
        relativo_allineamento = f"voce/allineamenti/{unita['id']}.json"
        file_audio = percorso_interno(progetto, relativo_audio, unita["id"])
        file_allineamento = percorso_interno(progetto, relativo_allineamento, unita["id"])
        adesso = datetime.now(timezone.utc).isoformat()

        if argomenti.prova:
            print(f"PROVA {unita['id']} ({len(v['testo'])} caratteri)", flush=True)
            allineamento = voce_di_prova(v["testo"], file_audio, argomenti.velocita_prova)
            carico = {"unita_id": unita["id"], "generato": adesso, "fornitore": "voce-di-sistema",
                      "prova": True, "impronta_testo": impronta_testo(v["testo"]),
                      "alignment": allineamento, "normalized_alignment": allineamento}
            durata = round(max(allineamento["character_end_times_seconds"]) * 1000)
        else:
            print(f"GENERO {unita['id']} ({len(v['testo'])} caratteri)", flush=True)
            corpo, identificativo = chiedi_audio(
                chiave=chiave, voice_id=voice_id, model_id=model_id, formato=formato, testo=v["testo"],
                impostazioni=voce.get("impostazioni") or {}, lingua=manifesto["progetto"].get("lingua", ""),
                attesa=argomenti.attesa)
            file_audio.parent.mkdir(parents=True, exist_ok=True)
            file_audio.write_bytes(base64.b64decode(corpo["audio_base64"], validate=True))
            carico = {"unita_id": unita["id"], "generato": adesso, "fornitore": "elevenlabs",
                      "voice_id": voice_id, "model_id": model_id, "output_format": formato,
                      "richiesta_id": identificativo, "impronta_testo": impronta_testo(v["testo"]),
                      "alignment": corpo.get("alignment"), "normalized_alignment": corpo.get("normalized_alignment")}
            durata = durata_da_allineamento(corpo)

        scrivi_json(file_allineamento, carico)
        unita.update({"file_audio": relativo_audio, "file_allineamento": relativo_allineamento,
                      "durata_ms": durata, "generato": adesso,
                      "impronta_testo": impronta_testo(v["testo"]), "prova": bool(argomenti.prova)})
        manifesto["voce"]["stato"] = "prova" if argomenti.prova else "parziale"
        scrivi_json(file_manifesto, manifesto)
        fatte += 1

    complete = all(u.get("file_audio") and percorso_interno(progetto, u["file_audio"], u["id"]).exists()
                   for u in manifesto["unita"])
    if complete:
        manifesto["voce"]["stato"] = "prova" if argomenti.prova else "completa"
    scrivi_json(file_manifesto, manifesto)
    print(f"Fatte: {fatte} · saltate: {saltate} · stato voce: {manifesto['voce']['stato']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(principale())
    except Errore as errore:
        print(str(errore), file=sys.stderr)
        raise SystemExit(2)
