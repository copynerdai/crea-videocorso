#!/usr/bin/env python3
"""Funzioni condivise dagli strumenti di crea-videocorso."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

CASA = Path.home() / ".crea-videocorso"
PACCHETTI_VISUAL = CASA / "pacchetti-visual"
SEGRETI = CASA / "segreti.env"

COLORI_PREDEFINITI = {
    "scuro": "#09182d",
    "primario": "#0070e0",
    "accento": "#e91e8c",
    "fondo": "#f3f7fc",
}


class Errore(Exception):
    """Errore d'uso da mostrare alla persona senza traccia di stack."""


# --- file ---------------------------------------------------------------

def leggi_json(percorso: Path) -> dict[str, Any]:
    try:
        dati = json.loads(Path(percorso).read_text(encoding="utf-8"))
    except FileNotFoundError as errore:
        raise Errore(f"File mancante: {percorso}") from errore
    except json.JSONDecodeError as errore:
        raise Errore(f"JSON non valido in {percorso}: {errore}") from errore
    if not isinstance(dati, dict):
        raise Errore(f"Atteso un oggetto JSON: {percorso}")
    return dati


def scrivi_json(percorso: Path, valore: Any) -> None:
    percorso = Path(percorso)
    percorso.parent.mkdir(parents=True, exist_ok=True)
    temporaneo = percorso.with_suffix(percorso.suffix + ".tmp")
    temporaneo.write_text(json.dumps(valore, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporaneo.replace(percorso)


def impronta_file(percorso: Path) -> str:
    return hashlib.sha256(Path(percorso).read_bytes()).hexdigest()


def impronta_testo(testo: str) -> str:
    return hashlib.sha256(testo.encode("utf-8")).hexdigest()


def percorso_interno(progetto: Path, relativo: Any, etichetta: str) -> Path:
    """Risolve un percorso del manifesto impedendo che esca dal progetto."""
    if not isinstance(relativo, str) or not relativo:
        raise Errore(f"Percorso mancante per {etichetta}")
    candidato = Path(relativo)
    if candidato.is_absolute() or ".." in candidato.parts:
        raise Errore(f"Percorso non ammesso per {etichetta}: {relativo}")
    risolto = (progetto / candidato).resolve()
    try:
        risolto.relative_to(progetto.resolve())
    except ValueError as errore:
        raise Errore(f"Il percorso esce dal progetto per {etichetta}: {relativo}") from errore
    return risolto


def nome_sicuro(valore: str) -> str:
    return valore.replace("/", "-").replace(":", " -").strip()


def segreto(nome: str) -> str | None:
    """Legge una chiave da ~/.crea-videocorso/segreti.env o dall'ambiente."""
    import os

    valore = os.environ.get(nome)
    if valore:
        return valore.strip()
    if not SEGRETI.exists():
        return None
    for riga in SEGRETI.read_text(encoding="utf-8").splitlines():
        riga = riga.strip()
        if not riga or riga.startswith("#") or "=" not in riga:
            continue
        chiave, _, resto = riga.partition("=")
        if chiave.strip() == nome:
            return resto.strip().strip('"').strip("'") or None
    return None


# --- configurazione del corso -------------------------------------------

def carica_corso(percorso: Path) -> dict[str, Any]:
    """Legge corso.json e riempie i valori predefiniti."""
    dati = leggi_json(percorso)
    corso = dati.get("corso")
    if not isinstance(corso, dict) or not corso.get("titolo"):
        raise Errore(f"In {percorso} manca «corso.titolo»")
    corso.setdefault("slug", scivola(corso["titolo"]))
    corso.setdefault("titolo_breve", corso["titolo"])
    corso.setdefault("sottotitolo", "")
    corso.setdefault("lingua", "it")
    corso.setdefault("pubblico", "")
    corso.setdefault("rischio", "none")

    sorgenti = dati.setdefault("sorgenti", {})
    if not sorgenti.get("cartella"):
        raise Errore(f"In {percorso} manca «sorgenti.cartella»")

    marchio = dati.setdefault("marchio", {})
    colori = dict(COLORI_PREDEFINITI)
    colori.update(marchio.get("colori") or {})
    marchio["colori"] = colori
    marchio.setdefault("font", "Montserrat")
    marchio.setdefault("nota_copertina", "")

    voce = dati.setdefault("voce", {})
    voce.setdefault("fornitore", "elevenlabs")
    voce.setdefault("model_id", "eleven_v3")
    voce.setdefault("output_format", "mp3_44100_128")
    voce.setdefault("impostazioni", {
        "stability": 0.4,
        "similarity_boost": 0.75,
        "style": 0.0,
        "use_speaker_boost": True,
        "speed": 1.0,
    })

    visuali = dati.setdefault("visuali", {})
    visuali.setdefault("pacchetti", [])
    visuali.setdefault("predefinito", "concetto")

    dati.setdefault("moduli", {})
    consegne = dati.setdefault("consegne", {})
    for chiave in ("html", "pdf", "audio", "video"):
        consegne.setdefault(chiave, True)
    return dati


def scivola(testo: str) -> str:
    piano = unicodedata.normalize("NFKD", testo)
    piano = "".join(c for c in piano if not unicodedata.combining(c))
    piano = re.sub(r"[^a-zA-Z0-9]+", "-", piano).strip("-").lower()
    return piano or "corso"


# --- testo ---------------------------------------------------------------

def togli_markdown(testo: str) -> str:
    testo = re.sub(r"!\[([^]]*)\]\([^)]+\)", r"\1", testo)
    testo = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", testo)
    testo = re.sub(r"\*\*([^*]+)\*\*", r"\1", testo)
    testo = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", testo)
    testo = re.sub(r"^#{1,6}\s+", "", testo)
    testo = re.sub(r"^>\s*", "", testo)
    return re.sub(r"\s+", " ", testo).strip()


def frasi(testo: str) -> list[str]:
    return [f.strip() for f in re.split(r"(?<=[.!?])\s+", testo) if f.strip()]


def accorcia(testo: str, limite: int = 82) -> str:
    testo = testo.strip(" —–-.\n")
    if len(testo) <= limite:
        return testo
    parti = re.split(r"(?<=[,:;.!?])\s+|\s+[—–]\s+", testo)
    if parti and 22 <= len(parti[0]) <= limite:
        return parti[0].rstrip(" ,;:.")
    taglio = testo[:limite].rsplit(" ", 1)[0]
    return taglio.rstrip(" ,;:.") + "…"


def canonico_con_mappa(testo: str) -> tuple[str, list[int]]:
    """Riduce il testo a lettere e numeri minuscoli, tenendo la posizione originale."""
    uscita: list[str] = []
    posizioni: list[int] = []
    spazio_sospeso = False
    indice_sospeso = 0
    for indice, carattere in enumerate(testo):
        scomposto = unicodedata.normalize("NFKD", carattere)
        tenuto = "".join(p for p in scomposto if not unicodedata.combining(p))
        for pezzo in tenuto.lower():
            if pezzo.isalnum():
                if spazio_sospeso and uscita:
                    uscita.append(" ")
                    posizioni.append(indice_sospeso)
                spazio_sospeso = False
                uscita.append(pezzo)
                posizioni.append(indice)
            else:
                if not spazio_sospeso:
                    indice_sospeso = indice
                spazio_sospeso = True
    return "".join(uscita), posizioni
