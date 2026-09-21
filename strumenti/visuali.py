#!/usr/bin/env python3
"""Libreria dei disegni delle slide e regole che scelgono quale usare.

I disegni sono SVG scritti a mano, senza dipendenze e senza immagini esterne.
I colori arrivano dalla tavolozza del marchio; i pacchetti aggiuntivi
installati in ~/.crea-videocorso/pacchetti-visual/ possono aggiungere disegni
e regole proprie senza toccare questo file.
"""

from __future__ import annotations

import html
import importlib.util
import re
from typing import Any, Callable

from comune import PACCHETTI_VISUAL, Errore, accorcia, leggi_json


# --- colori --------------------------------------------------------------

def _componenti(colore: str) -> tuple[int, int, int]:
    valore = colore.lstrip("#")
    if len(valore) == 3:
        valore = "".join(c * 2 for c in valore)
    if len(valore) != 6:
        raise Errore(f"Colore non valido: {colore}")
    return tuple(int(valore[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def tinta(colore: str, quanto: float) -> str:
    """Schiarisce un colore verso il bianco: quanto 0 = pieno, 1 = bianco."""
    r, g, b = _componenti(colore)
    mescola = lambda c: round(c + (255 - c) * quanto)
    return "#{:02x}{:02x}{:02x}".format(mescola(r), mescola(g), mescola(b))


def tavolozza(colori: dict[str, str]) -> dict[str, str]:
    primario = colori["primario"]
    accento = colori["accento"]
    return {
        "scuro": colori["scuro"],
        "primario": primario,
        "accento": accento,
        "fondo": colori["fondo"],
        "primario_chiaro": tinta(primario, 0.86),
        "primario_tenue": tinta(primario, 0.62),
        "accento_chiaro": tinta(accento, 0.86),
        "accento_tenue": tinta(accento, 0.62),
        "neutro": tinta(colori["scuro"], 0.78),
        "neutro_chiaro": tinta(colori["scuro"], 0.92),
    }


def testo_xml(valore: str) -> str:
    return html.escape(valore, quote=True)


def _breve(testo: str, limite: int) -> str:
    """Restituisce il frammento solo se ci sta intero: meglio niente che troncato."""
    pulito = (testo or "").strip(" .:;!?")
    return pulito if pulito and len(pulito) <= limite else ""


# --- disegni generici ----------------------------------------------------

def _passi(slide: dict, tav: dict[str, str]) -> str:
    etichette = [accorcia(v, 22) for v in (slide.get("corpo") or [])[:3]]
    while len(etichette) < 3:
        etichette.append("")
    cerchi = []
    for indice, (x, colore) in enumerate(((155, tav["primario_chiaro"]), (350, tav["neutro_chiaro"]), (545, tav["accento_chiaro"]))):
        cerchi.append(
            f'<circle cx="{x}" cy="350" r="67" fill="{colore}"/>'
            f'<text class="numero-passo" x="{x}" y="367">{indice + 1}</text>'
        )
    righe = "".join(
        f'<text class="etichetta-grande" x="{x}" y="{y}">{testo_xml(etichette[i])}</text>'
        for i, (x, y) in enumerate(((120, 105), (300, 175), (420, 245)))
        if etichette[i]
    )
    return f'''<svg class="disegno" viewBox="0 0 700 500" role="img" aria-label="Progressione in tre passaggi">
      <path d="M105 350H595" stroke="{tav['neutro_chiaro']}" stroke-width="13"/>
      <path d="M574 328L614 350L574 372" fill="{tav['primario']}"/>{''.join(cerchi)}{righe}
    </svg>'''


def _ciclo(slide: dict, tav: dict[str, str]) -> str:
    nodi = [accorcia(v, 14) for v in (slide.get("corpo") or [])[:4]]
    predefiniti = ["innesco", "spinta", "gesto", "vuoto"]
    nodi = [nodi[i] if i < len(nodi) and nodi[i] else predefiniti[i] for i in range(4)]
    posizioni = ((350, 72, False), (528, 250, False), (350, 428, True), (172, 250, True))
    disegno = []
    for testo, (x, y, acceso) in zip(nodi, posizioni):
        riempimento = tav["accento_chiaro"] if acceso else tav["primario_chiaro"]
        bordo = tav["accento"] if acceso else tav["primario"]
        disegno.append(
            f'<g class="nodo"><circle cx="{x}" cy="{y}" r="54" fill="{riempimento}" stroke="{bordo}" stroke-width="7"/>'
            f'<text x="{x}" y="{y + 7}">{testo_xml(testo)}</text></g>'
        )
    return f'''<svg class="disegno" viewBox="0 0 700 500" role="img" aria-label="Ciclo che si ripete">
      <circle cx="350" cy="250" r="170" fill="none" stroke="{tav['neutro_chiaro']}" stroke-width="14"/>
      <path d="M471 117L525 109L510 161" fill="{tav['primario']}"/>
      <path d="M226 383L172 391L190 340" fill="{tav['accento']}"/>{''.join(disegno)}
    </svg>'''


def _calendario(slide: dict, tav: dict[str, str]) -> str:
    numeri = re.findall(r"\b(\d{1,2})\s*giorni\b", " ".join(slide.get("corpo") or []) + " " + slide.get("titolo", ""), re.I)
    giorni = max(7, min(int(numeri[0]), 42)) if numeri else 30
    colori = [tav["primario_chiaro"], tav["accento_chiaro"], tav["neutro_chiaro"], tinta(tav["primario"], 0.75), tinta(tav["accento"], 0.75)]
    celle = []
    for i in range(giorni):
        x = 84 + (i % 7) * 78
        y = 95 + (i // 7) * 72
        celle.append(
            f'<rect x="{x}" y="{y}" width="58" height="52" rx="11" fill="{colori[min(i // 7, 4)]}"/>'
            f'<text class="numero-cella" x="{x + 29}" y="{y + 34}">{i + 1}</text>'
        )
    titolo = testo_xml(_breve(slide.get("titolo", ""), 38) or f"{giorni} giorni, un passo al giorno")
    return (f'<svg class="disegno" viewBox="0 0 700 500" role="img" aria-label="Percorso a giorni">'
            f'<text class="etichetta-grande" x="84" y="54">{titolo}</text>' + "".join(celle) + "</svg>")


def _onda(slide: dict, tav: dict[str, str]) -> str:
    return f'''<svg class="disegno" viewBox="0 0 700 500" role="img" aria-label="Qualcosa che sale, resta e scende">
      <path d="M54 366C145 366 157 125 300 125S448 366 646 366" fill="none" stroke="{tav['primario']}" stroke-width="22" stroke-linecap="round"/>
      <circle cx="300" cy="125" r="24" fill="{tav['accento']}"/><path d="M300 75V40" stroke="{tav['accento']}" stroke-width="8"/>
      <text class="etichetta" x="258" y="30">picco</text>
      <text class="etichetta-grande" x="120" y="440">sale · resta · scende</text>
    </svg>'''


def _mente(slide: dict, tav: dict[str, str]) -> str:
    return f'''<svg class="disegno" viewBox="0 0 700 500" role="img" aria-label="Come funziona la testa">
      <path d="M220 410C141 355 119 260 159 178C189 116 250 91 310 105C353 51 445 63 479 126C548 127 591 191 571 253C615 313 576 405 496 419Z" fill="{tav['primario_chiaro']}" stroke="{tav['primario']}" stroke-width="10"/>
      <path d="M245 325C279 258 326 226 381 225C428 224 466 192 487 142" fill="none" stroke="{tav['accento']}" stroke-width="18" stroke-linecap="round"/>
      <circle cx="245" cy="325" r="20" fill="{tav['accento']}"/><circle cx="381" cy="225" r="20" fill="{tav['accento']}"/><circle cx="487" cy="142" r="20" fill="{tav['accento']}"/>
    </svg>'''


def _schermo(slide: dict, tav: dict[str, str]) -> str:
    return f'''<svg class="disegno" viewBox="0 0 700 500" role="img" aria-label="Telefono fuori dalla scena">
      <rect x="230" y="42" width="240" height="408" rx="38" fill="{tav['scuro']}"/>
      <rect x="250" y="78" width="200" height="310" rx="12" fill="{tav['primario_chiaro']}"/>
      <circle cx="350" cy="418" r="14" fill="{tav['neutro']}"/>
      <path d="M177 92L521 436" stroke="{tav['accento']}" stroke-width="24" stroke-linecap="round"/>
    </svg>'''


def _ritmo(slide: dict, tav: dict[str, str]) -> str:
    sopra = testo_xml(_breve(slide.get("titolo", ""), 28))
    return f'''<svg class="disegno" viewBox="0 0 700 500" role="img" aria-label="Ritmo costante">
      <path d="M65 285C115 285 115 175 165 175S215 285 265 285S315 175 365 175S415 285 465 285S515 175 565 175S615 285 650 285" fill="none" stroke="{tav['accento']}" stroke-width="18" stroke-linecap="round"/>
      <path d="M75 370H625" stroke="{tav['primario']}" stroke-width="9" stroke-linecap="round"/>
      <path d="M603 350L640 370L603 390" fill="{tav['primario']}"/>
      <text class="etichetta-grande" x="90" y="90">{sopra}</text>
    </svg>'''


def _dialogo(slide: dict, tav: dict[str, str]) -> str:
    corpo = slide.get("corpo") or []
    sinistra = accorcia(slide.get("titolo", ""), 30) or "Ti va?"
    destra = accorcia(corpo[0], 30) if corpo else "Ti ascolto"
    return f'''<svg class="disegno" viewBox="0 0 700 500" role="img" aria-label="Due persone che si parlano">
      <circle cx="213" cy="270" r="102" fill="{tav['primario_chiaro']}"/><circle cx="487" cy="270" r="102" fill="{tav['accento_chiaro']}"/>
      <path d="M116 74H350Q382 74 382 106V190Q382 222 350 222H220L171 260L180 222H116Q84 222 84 190V106Q84 74 116 74Z" fill="#fff" stroke="{tav['primario']}" stroke-width="7"/>
      <path d="M584 248H350Q318 248 318 280V364Q318 396 350 396H480L529 434L520 396H584Q616 396 616 364V280Q616 248 584 248Z" fill="#fff" stroke="{tav['accento']}" stroke-width="7"/>
      <text class="battuta" x="120" y="157">{testo_xml(sinistra)}</text><text class="battuta" x="350" y="335">{testo_xml(destra)}</text>
    </svg>'''


def _confronto(slide: dict, tav: dict[str, str]) -> str:
    corpo = [accorcia(v, 34) for v in (slide.get("corpo") or [])[:2]]
    while len(corpo) < 2:
        corpo.append("")
    return f'''<svg class="disegno" viewBox="0 0 700 500" role="img" aria-label="Due possibilità a confronto">
      <rect x="54" y="92" width="272" height="316" rx="34" fill="{tav['primario_chiaro']}" stroke="{tav['primario']}" stroke-width="7"/>
      <rect x="374" y="92" width="272" height="316" rx="34" fill="{tav['accento_chiaro']}" stroke="{tav['accento']}" stroke-width="7"/>
      <path d="M350 118V382" stroke="{tav['neutro_chiaro']}" stroke-width="6" stroke-dasharray="16 14"/>
      <text class="battuta" x="86" y="252">{testo_xml(corpo[0])}</text><text class="battuta" x="406" y="252">{testo_xml(corpo[1])}</text>
    </svg>'''


def _scala(slide: dict, tav: dict[str, str]) -> str:
    voci = [accorcia(v, 20) for v in (slide.get("corpo") or [])[:3]]
    while len(voci) < 3:
        voci.append("")
    barre = []
    for indice, (x, altezza, colore) in enumerate(((120, 120, tav["primario_chiaro"]), (300, 200, tav["neutro_chiaro"]), (480, 280, tav["accento_chiaro"]))):
        y = 400 - altezza
        barre.append(
            f'<rect x="{x}" y="{y}" width="130" height="{altezza}" rx="22" fill="{colore}"/>'
            f'<text class="etichetta" x="{x + 10}" y="{y - 18}">{testo_xml(voci[indice])}</text>'
        )
    return f'''<svg class="disegno" viewBox="0 0 700 500" role="img" aria-label="Progressione a tre livelli">
      <path d="M72 412H648" stroke="{tav['neutro_chiaro']}" stroke-width="10"/>{''.join(barre)}
    </svg>'''


def _avvertenza(slide: dict, tav: dict[str, str]) -> str:
    nota = testo_xml(_breve((slide.get("corpo") or [slide.get("titolo", "")])[0], 40))
    return f'''<svg class="disegno" viewBox="0 0 700 500" role="img" aria-label="Attenzione">
      <path d="M350 68L638 430H62Z" fill="{tav['accento_chiaro']}" stroke="{tav['accento']}" stroke-width="12" stroke-linejoin="round"/>
      <rect x="334" y="196" width="32" height="112" rx="16" fill="{tav['accento']}"/><circle cx="350" cy="352" r="21" fill="{tav['accento']}"/>
      <text class="etichetta" x="120" y="480">{nota}</text>
    </svg>'''


def _elenco(slide: dict, tav: dict[str, str]) -> str:
    voci = [accorcia(v, 30) for v in (slide.get("corpo") or [])[:4]]
    righe = []
    for indice, voce in enumerate(voci):
        y = 120 + indice * 92
        righe.append(
            f'<rect x="70" y="{y - 42}" width="560" height="72" rx="24" fill="#fff" stroke="{tav["neutro_chiaro"]}" stroke-width="5"/>'
            f'<circle cx="122" cy="{y - 6}" r="17" fill="{tav["primario"] if indice % 2 == 0 else tav["accento"]}"/>'
            f'<text class="battuta" x="160" y="{y + 3}">{testo_xml(voce)}</text>'
        )
    return f'<svg class="disegno" viewBox="0 0 700 500" role="img" aria-label="Elenco di punti">{"".join(righe)}</svg>'


DISEGNI: dict[str, Callable[[dict, dict[str, str]], str]] = {
    "concetto": _passi,
    "ciclo": _ciclo,
    "calendario": _calendario,
    "onda": _onda,
    "mente": _mente,
    "schermo": _schermo,
    "ritmo": _ritmo,
    "dialogo": _dialogo,
    "confronto": _confronto,
    "scala": _scala,
    "avvertenza": _avvertenza,
    "elenco": _elenco,
}

ETICHETTE = {
    "concetto": "IL PUNTO",
    "ciclo": "IL CICLO",
    "calendario": "IL PERCORSO",
    "onda": "COME SALE E SCENDE",
    "mente": "COME FUNZIONA",
    "schermo": "ABITUDINE",
    "ritmo": "RITMO",
    "dialogo": "PAROLE UTILI",
    "confronto": "A CONFRONTO",
    "scala": "PROGRESSIONE",
    "avvertenza": "ATTENZIONE",
    "elenco": "IN BREVE",
}

REGOLE_BASE = [
    {"visual": "avvertenza", "parole": ["attenzione", "mai ", "non fare", "pericol", "rischio", "controindicaz", "fermati", "smetti"]},
    {"visual": "dialogo", "parole": ["chiedi", "chiedere", "dire", "parlare", "conversazione", "ascolt", "domanda", "risposta", "consenso"]},
    {"visual": "calendario", "parole": ["giorni", "settiman", "calendario", "ogni giorno", "protocollo"]},
    {"visual": "ciclo", "parole": ["ciclo", "si ripete", "abitudine", "rituale", "ricadut", "innesco", "trigger"]},
    {"visual": "onda", "parole": ["onda", "sale e scende", "impulso", "respiro", "respira", "picco"]},
    {"visual": "mente", "parole": ["cervello", "mente", "testa", "dopamina", "pensier", "emozion"]},
    {"visual": "schermo", "parole": ["schermo", "telefono", "video", "social", "app "]},
    {"visual": "ritmo", "parole": ["ritmo", "costante", "velocit", "lentamente", "pressione"]},
    {"visual": "confronto", "parole": ["invece", "differenza", "a confronto", "meglio di", "mentre", "due strade"]},
    {"visual": "scala", "parole": ["gradual", "progression", "livello", "un passo alla volta", "aument"]},
    {"visual": "elenco", "parole": ["elenco", "lista", "checklist", "cosa serve", "tre cose", "quattro cose"]},
]


# --- pacchetti aggiuntivi ------------------------------------------------

class Pacchetto:
    def __init__(self, nome: str, cartella: object, dati: dict[str, Any], modulo: Any) -> None:
        self.nome = nome
        self.cartella = cartella
        self.regole = dati.get("regole") or []
        self.etichette = dati.get("etichette") or {}
        self.modulo = modulo

    def disegna(self, tipo: str, slide: dict, tav: dict[str, str]) -> str | None:
        funzione = getattr(self.modulo, "disegna", None) if self.modulo else None
        return funzione(tipo, slide, tav) if funzione else None


def carica_pacchetti(nomi: list[str]) -> list[Pacchetto]:
    pacchetti: list[Pacchetto] = []
    for nome in nomi:
        cartella = PACCHETTI_VISUAL / nome
        if not cartella.is_dir():
            raise Errore(
                f"Pacchetto visuale «{nome}» non installato in {PACCHETTI_VISUAL}. "
                "Installalo o togli il suo nome da «visuali.pacchetti» in corso.json."
            )
        dati = leggi_json(cartella / "pacchetto.json")
        modulo = None
        file_modulo = cartella / "visuali.py"
        if file_modulo.exists():
            specifica = importlib.util.spec_from_file_location(f"pacchetto_{nome.replace('-', '_')}", file_modulo)
            modulo = importlib.util.module_from_spec(specifica)  # type: ignore[arg-type]
            specifica.loader.exec_module(modulo)  # type: ignore[union-attr]
        pacchetti.append(Pacchetto(nome, cartella, dati, modulo))
    return pacchetti


def classifica(testo: str, indicazione: str, pacchetti: list[Pacchetto], predefinito: str) -> str:
    """Sceglie il disegno dalle parole della slide.

    Vince la regola con più parole riconosciute, non la prima dell'elenco.
    Le parole scritte nell'indicazione fra parentesi quadre pesano il doppio,
    perché sono un'istruzione di chi ha scritto il testo. A parità di punteggio
    vincono i pacchetti aggiuntivi, poi l'ordine delle regole base.
    """
    corpo = testo.casefold()
    guida = indicazione.casefold()
    migliore = (0, predefinito)
    for regola in [r for p in pacchetti for r in p.regole] + REGOLE_BASE:
        punti = 0
        for parola in regola.get("parole", []):
            if parola in guida:
                punti += 2
            elif parola in corpo:
                punti += 1
        if punti > migliore[0]:
            migliore = (punti, regola["visual"])
    return migliore[1]


def etichetta(visual: str, indicazione: str, pacchetti: list[Pacchetto]) -> str:
    if indicazione:
        titolo = re.split(r"[:;]", indicazione, maxsplit=1)[0]
        if 3 <= len(titolo) <= 42:
            return titolo.upper()
    for pacchetto in pacchetti:
        if visual in pacchetto.etichette:
            return pacchetto.etichette[visual]
    return ETICHETTE.get(visual, "IL PUNTO")


def disegna(visual: str, slide: dict, tav: dict[str, str], pacchetti: list[Pacchetto]) -> str:
    for pacchetto in pacchetti:
        disegno = pacchetto.disegna(visual, slide, tav)
        if disegno:
            return disegno
    funzione = DISEGNI.get(visual, DISEGNI["concetto"])
    return funzione(slide, tav)


def tipi_disponibili(pacchetti: list[Pacchetto]) -> list[str]:
    tipi = set(DISEGNI)
    for pacchetto in pacchetti:
        tipi.update(regola["visual"] for regola in pacchetto.regole)
        tipi.update(getattr(pacchetto.modulo, "TIPI", []) or [])
    return sorted(tipi)
