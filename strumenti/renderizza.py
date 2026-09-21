#!/usr/bin/env python3
"""Trasforma il mazzo HTML in una immagine per slide e in un PDF.

  python3 renderizza.py <cartella-progetto>
  python3 renderizza.py <cartella-progetto> --pagine 1,7,18   # solo un campione
  python3 renderizza.py <cartella-progetto> --senza-pdf

Usa il browser già installato sul computer (Chrome, Chromium, Brave o Edge)
in modo invisibile: non serve né Node né Playwright.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comune import Errore, leggi_json  # noqa: E402

BROWSER = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/microsoft-edge",
)


def trova_browser(indicato: str | None = None) -> str:
    if indicato:
        if not Path(indicato).exists():
            raise Errore(f"Browser non trovato: {indicato}")
        return indicato
    for candidato in BROWSER:
        if Path(candidato).exists():
            return candidato
    for nome in ("google-chrome", "chromium", "chromium-browser", "msedge"):
        trovato = shutil.which(nome)
        if trovato:
            return trovato
    raise Errore(
        "Nessun browser compatibile trovato. Installa Google Chrome o Chromium, "
        "oppure indicane il percorso con --browser."
    )


BANDIERE = (
    "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
    "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--mute-audio",
    "--disable-background-networking", "--disable-component-update", "--disable-sync",
    "--disable-default-apps", "--disable-popup-blocking",
)


def _attendi_file(processo: subprocess.Popen, destinazione: Path, limite: float) -> bool:
    """Chrome scrive il file ma non esce da solo: si aspetta il file, poi lo si chiude."""
    avvio = time.time()
    misura = -1
    while time.time() - avvio < limite:
        if processo.poll() is not None and destinazione.exists():
            break
        if destinazione.exists():
            attuale = destinazione.stat().st_size
            if attuale > 1024 and attuale == misura:
                break
            misura = attuale
        time.sleep(0.15)
    if processo.poll() is None:
        processo.terminate()
        try:
            processo.wait(timeout=5)
        except subprocess.TimeoutExpired:
            processo.kill()
            processo.wait()
    return destinazione.exists() and destinazione.stat().st_size > 1024


def _avvia(browser: str, profilo: str, extra: list[str], indirizzo: str, attesa: int) -> subprocess.Popen:
    return subprocess.Popen(
        [browser, *BANDIERE, f"--user-data-dir={profilo}", f"--virtual-time-budget={attesa}", *extra, indirizzo],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def scatta(browser: str, indirizzo: str, destinazione: Path, attesa: int, limite: float = 60.0) -> None:
    destinazione.parent.mkdir(parents=True, exist_ok=True)
    destinazione.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="crea-videocorso-") as profilo:
        processo = _avvia(browser, profilo, ["--window-size=1920,1080", f"--screenshot={destinazione}"], indirizzo, attesa)
        if not _attendi_file(processo, destinazione, limite):
            raise Errore(f"Il browser non ha prodotto {destinazione.name} entro {limite:.0f} secondi")


def stampa_pdf(browser: str, indirizzo: str, destinazione: Path, attesa: int, limite: float = 300.0) -> None:
    destinazione.parent.mkdir(parents=True, exist_ok=True)
    destinazione.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="crea-videocorso-pdf-") as profilo:
        processo = _avvia(browser, profilo, ["--no-pdf-header-footer", f"--print-to-pdf={destinazione}"], indirizzo, attesa)
        if not _attendi_file(processo, destinazione, limite):
            raise Errore(f"Il browser non ha prodotto il PDF entro {limite:.0f} secondi")


def principale() -> int:
    analizzatore = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizzatore.add_argument("progetto")
    analizzatore.add_argument("--pagine", help="Elenco di pagine separate da virgola: finiscono in controlli/immagini")
    analizzatore.add_argument("--senza-pdf", action="store_true")
    analizzatore.add_argument("--browser", help="Percorso di un browser diverso da quello trovato in automatico")
    analizzatore.add_argument("--parallele", type=int, default=4, help="Quante slide scattare insieme")
    analizzatore.add_argument("--attesa", type=int, default=2500, help="Millisecondi concessi al disegno della pagina")
    argomenti = analizzatore.parse_args()

    progetto = Path(argomenti.progetto).expanduser().resolve()
    manifesto = leggi_json(progetto / "manifesti/manifesto.json")
    html = progetto / manifesto["consegne"]["html"]
    if not html.exists():
        raise Errore(f"Mazzo non trovato: {html}. Lancia prima costruisci-slide.py")
    totale = len(manifesto["slide"])
    if not totale:
        raise Errore("Il manifesto non elenca nessuna slide")

    browser = trova_browser(argomenti.browser)
    base = "file://" + quote(str(html))
    campione = None
    if argomenti.pagine:
        campione = [int(v) for v in argomenti.pagine.split(",") if v.strip()]
        fuori = [p for p in campione if p < 1 or p > totale]
        if fuori:
            raise Errore(f"Pagine fuori intervallo (1-{totale}): {fuori}")
    pagine = campione or list(range(1, totale + 1))
    cartella = progetto / ("controlli/immagini" if campione else "tmp/slide")
    cartella.mkdir(parents=True, exist_ok=True)

    def lavora(pagina: int) -> int:
        nome = f"{'campione-' if campione else ''}pagina-{pagina:03d}.png"
        scatta(browser, f"{base}?slide={pagina}", cartella / nome, argomenti.attesa)
        return pagina

    fatte = 0
    with ThreadPoolExecutor(max_workers=max(1, argomenti.parallele)) as gruppo:
        for pagina in gruppo.map(lavora, pagine):
            fatte += 1
            if fatte % 25 == 0 or fatte == len(pagine):
                print(f"immagini {fatte}/{len(pagine)}", flush=True)

    if not campione and not argomenti.senza_pdf:
        stampa_pdf(browser, base, progetto / manifesto["consegne"]["pdf"], max(argomenti.attesa, 4000))
        print(f"PDF: {progetto / manifesto['consegne']['pdf']}")
    print(f"Immagini in {cartella}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(principale())
    except Errore as errore:
        print(str(errore), file=sys.stderr)
        raise SystemExit(2)
