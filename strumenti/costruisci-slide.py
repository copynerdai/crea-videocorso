#!/usr/bin/env python3
"""Dai testi approvati ricava trascrizioni, piano delle slide e mazzo HTML.

  python3 costruisci-slide.py <cartella-progetto>              # piano se manca, poi HTML
  python3 costruisci-slide.py <cartella-progetto> --rigenera-piano
  python3 costruisci-slide.py <cartella-progetto> --solo-piano

Il piano sta in piano/slide.json e si corregge a mano: l'HTML si costruisce
sempre dal piano, quindi le correzioni restano finché non si rigenera.
"""

from __future__ import annotations

import argparse
import base64
import html
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import visuali  # noqa: E402
from comune import (  # noqa: E402
    Errore,
    accorcia,
    carica_corso,
    frasi,
    impronta_file,
    impronta_testo,
    leggi_json,
    nome_sicuro,
    scrivi_json,
    togli_markdown,
)

LIMITE_UNITA = 4300


@dataclass
class Blocco:
    testo: str
    titoletto: bool = False
    indicazioni: list[str] = field(default_factory=list)


@dataclass
class Lezione:
    id: str
    modulo: int
    numero: int
    titolo: str
    file: Path
    nome_export: str
    blocchi: list[Blocco]
    testo: str
    unita: list[str] = field(default_factory=list)
    slide: list[dict] = field(default_factory=list)


# --- lettura delle sorgenti ---------------------------------------------

def riconosci(file: Path, dentro: Path) -> tuple[int, int, str]:
    """Ricava modulo, numero e titolo dal nome del file o dalla sua cartella."""
    nome = file.stem
    for schema, gruppi in (
        (r"^M(\d+)[-_ ]*L(\d+)\s*[-–—]\s*(.+)$", (1, 2, 3)),
        (r"^(\d+)\.(\d+)\s*[-–—]?\s*(.+)$", (1, 2, 3)),
        (r"^M(\d+)\s*[-–—]\s*(\d+)\s*[-–—]\s*(.+)$", (1, 2, 3)),
    ):
        trovato = re.match(schema, nome, re.I)
        if trovato:
            return int(trovato.group(gruppi[0])), int(trovato.group(gruppi[1])), trovato.group(gruppi[2]).strip()

    modulo = 1
    cartella = re.search(r"(?:modulo|module|mod)\s*(\d+)", str(file.parent.relative_to(dentro)), re.I)
    if cartella:
        modulo = int(cartella.group(1))
    trovato = re.match(r"^(?:L|lezione\s*)?(\d+)\s*[-–—]\s*(.+)$", nome, re.I)
    if trovato:
        return modulo, int(trovato.group(1)), trovato.group(2).strip()
    return modulo, 0, nome.strip()


def leggi_sorgente(file: Path, salta_note: bool) -> tuple[list[Blocco], str]:
    righe = file.read_text(encoding="utf-8").splitlines()
    inizio = 0
    if righe and righe[0].strip() == "---":
        for i in range(1, len(righe)):
            if righe[i].strip() == "---":
                inizio = i + 1
                break
    fine = len(righe)
    if salta_note:
        coda = re.compile(r"^##\s+(?:note|fonti|sources|riferimenti|bibliografia)", re.I)
        for i in range(inizio, len(righe)):
            if coda.match(righe[i].strip()):
                fine = i
                break

    blocchi: list[Blocco] = []
    indicazioni_sospese: list[str] = []
    accumulo: list[str] = []

    def chiudi() -> None:
        nonlocal accumulo, indicazioni_sospese
        grezzo = " ".join(r.strip() for r in accumulo if r.strip()).strip()
        accumulo = []
        if not grezzo:
            return
        titoletto = bool(re.fullmatch(r"\*\*.+?\*\*\.?", grezzo)) or bool(re.match(r"^#{2,6}\s+", grezzo))
        pulito = re.sub(r"\[.+?\]", "", togli_markdown(grezzo)).strip()
        if pulito:
            blocchi.append(Blocco(pulito, titoletto, indicazioni_sospese))
            indicazioni_sospese = []

    for riga in righe[inizio:fine]:
        spogliata = riga.strip()
        if spogliata == "---":
            chiudi()
            continue
        if spogliata.startswith("[") and spogliata.endswith("]"):
            chiudi()
            indicazioni_sospese.append(spogliata[1:-1].strip())
            continue
        if not spogliata:
            chiudi()
        else:
            accumulo.append(riga)
    chiudi()

    testo = "\n\n".join(b.testo for b in blocchi).strip() + "\n"
    if not testo.strip():
        raise Errore(f"Nessun testo da leggere ad alta voce in {file}")
    return blocchi, testo


# --- unità per la voce ---------------------------------------------------

def spezza_lungo(testo: str, limite: int) -> list[str]:
    pezzi: list[str] = []
    corrente = ""
    for frase in re.split(r"(?<=[.!?])\s+", testo):
        if corrente and len(corrente) + len(frase) + 1 > limite:
            pezzi.append(corrente)
            corrente = frase
        else:
            corrente = f"{corrente} {frase}".strip()
    if corrente:
        pezzi.append(corrente)
    return pezzi


def dividi_in_unita(testo: str, limite: int = LIMITE_UNITA) -> list[str]:
    espansi: list[str] = []
    for paragrafo in testo.strip().split("\n\n"):
        espansi.extend(spezza_lungo(paragrafo, limite) if len(paragrafo) > limite else [paragrafo])
    unita: list[str] = []
    corrente: list[str] = []
    misura = 0
    for paragrafo in espansi:
        aggiunta = len(paragrafo) + (2 if corrente else 0)
        if corrente and misura + aggiunta > limite:
            unita.append("\n\n".join(corrente))
            corrente, misura = [], 0
        corrente.append(paragrafo)
        misura += len(paragrafo) + (2 if len(corrente) > 1 else 0)
    if corrente:
        unita.append("\n\n".join(corrente))
    return unita


# --- piano delle slide ---------------------------------------------------

def aggancio(testo: str, massimo_parole: int = 13) -> str:
    parole = testo.split()
    if len(parole) <= massimo_parole:
        return testo
    return " ".join(parole[:massimo_parole]).rstrip(" ,;:")


def pianifica(lezione: Lezione, corso: dict, pacchetti: list, regolazioni: dict) -> list[dict]:
    blocchi = lezione.blocchi
    primo = blocchi[0].testo
    sottotitolo = accorcia((frasi(primo) or [primo])[0], 118)
    slide = [{
        "id": f"{lezione.id}-sl001",
        "lezione_id": lezione.id,
        "entra_da": "INIZIO",
        "occhiello": f"{corso['titolo']} · MODULO {lezione.modulo}",
        "titolo": lezione.titolo,
        "corpo": [sottotitolo],
        "indicazione": "",
        "visual": "copertina",
    }]
    if len(blocchi) == 1:
        return slide

    soglia = int(regolazioni.get("caratteri_per_slide", 620))
    massimo = int(regolazioni.get("massimo_per_slide", 950))
    per_slide = int(regolazioni.get("frasi_per_slide", 3))

    gruppi: list[list[Blocco]] = []
    corrente: list[Blocco] = []
    misura = 0
    for blocco in blocchi[1:]:
        stacco = bool(blocco.titoletto or blocco.indicazioni)
        if corrente and (stacco or misura + len(blocco.testo) > massimo):
            gruppi.append(corrente)
            corrente, misura = [], 0
        corrente.append(blocco)
        misura += len(blocco.testo)
        if misura >= soglia and not blocco.titoletto:
            gruppi.append(corrente)
            corrente, misura = [], 0
    if corrente:
        gruppi.append(corrente)
    if (len(gruppi) > 1
            and sum(len(b.testo) for b in gruppi[-1]) < 170
            and not gruppi[-1][0].titoletto
            and sum(len(b.testo) for b in gruppi[-2] + gruppi[-1]) <= massimo):
        gruppi[-2].extend(gruppi.pop())

    for gruppo in gruppi:
        guida = gruppo[0]
        indicazione = " · ".join(i for b in gruppo for i in b.indicazioni)
        titolo = guida.testo if guida.titoletto else accorcia((frasi(guida.testo) or [guida.testo])[0])
        corpo: list[str] = []
        confronto = titolo.casefold().rstrip(" .:;!?")
        for indice, blocco in enumerate(gruppo):
            if indice == 0 and blocco.titoletto:
                continue
            pozzo = frasi(blocco.testo)
            if indice == 0 and pozzo:
                pozzo = pozzo[1:]
            for frase in pozzo:
                candidata = accorcia(frase, 118)
                if candidata and candidata.casefold().rstrip(" .:;!?") != confronto and candidata not in corpo:
                    corpo.append(candidata)
                if len(corpo) == per_slide:
                    break
            if len(corpo) == per_slide:
                break
        if not corpo:
            corpo = [accorcia(guida.testo, 118)]
        testo_gruppo = " ".join(b.testo for b in gruppo)
        visual = visuali.classifica(f"{titolo} {testo_gruppo}", indicazione, pacchetti, corso.get("predefinito", "concetto"))
        slide.append({
            "id": f"{lezione.id}-sl{len(slide) + 1:03d}",
            "lezione_id": lezione.id,
            "entra_da": aggancio(guida.testo),
            "occhiello": visuali.etichetta(visual, indicazione, pacchetti),
            "titolo": accorcia(titolo, 94),
            "corpo": corpo,
            "indicazione": indicazione,
            "visual": visual,
        })
    return slide


# --- mazzo HTML ----------------------------------------------------------

def caratteri_incorporati(cartella: Path, famiglia: str) -> str:
    regole = []
    if cartella.is_dir():
        for file in sorted(cartella.rglob("*")):
            if file.suffix.lower() not in {".ttf", ".otf", ".woff2"}:
                continue
            peso = re.search(r"(100|200|300|400|500|600|700|800|900)", file.stem)
            spessore = peso.group(1) if peso else "400"
            tipo = {"ttf": "truetype", "otf": "opentype", "woff2": "woff2"}[file.suffix.lower().lstrip(".")]
            dati = base64.b64encode(file.read_bytes()).decode()
            regole.append(
                f"@font-face{{font-family:{famiglia};font-weight:{spessore};font-style:normal;"
                f"font-display:block;src:url(data:font/{file.suffix.lstrip('.')};base64,{dati}) format('{tipo}')}}"
            )
    return "".join(regole)


def trova_logo(progetto: Path, marchio: dict) -> str:
    nome = marchio.get("logo")
    cartella = progetto / "intake/marchio"
    candidati = [cartella / nome] if nome else []
    candidati += [f for f in sorted(cartella.rglob("*")) if f.suffix.lower() in {".webp", ".png", ".svg"} and "logo" in f.stem.lower()]
    for file in candidati:
        if file.exists() and file.is_file():
            tipo = {"webp": "image/webp", "png": "image/png", "svg": "image/svg+xml"}[file.suffix.lower().lstrip(".")]
            return f"data:{tipo};base64," + base64.b64encode(file.read_bytes()).decode()
    return ""


def slide_html(slide: dict, corso: dict, lezione_titolo: str, pagina: int, totale: int, tav: dict, pacchetti: list) -> str:
    piede = f'<footer><span>{html.escape(corso["titolo_breve"])} · {html.escape(lezione_titolo)}</span><span>{pagina:03d} / {totale:03d}</span></footer>'
    if slide["visual"] == "copertina":
        nota = corso.get("nota_copertina") or ""
        riga = f'<div class="riga-titolo"><b>{html.escape(nota)}</b></div>' if nota else ""
        corpo = "".join(f"<p>{html.escape(v)}</p>" for v in slide["corpo"][:1])
        return (f'<section class="slide copertina" id="{slide["id"]}" data-lezione="{slide["lezione_id"]}">'
                f'<div class="dentro"><div class="occhiello">{html.escape(slide["occhiello"])}</div>'
                f'<h1>{html.escape(slide["titolo"])}</h1>{corpo}{riga}</div>'
                f'<footer><span>{html.escape(corso["titolo"])}</span><span>{pagina:03d} / {totale:03d}</span></footer></section>')
    punti = "".join(f"<li>{html.escape(v)}</li>" for v in slide["corpo"])
    disegno = visuali.disegna(slide["visual"], slide, tav, pacchetti)
    return (f'<section class="slide contenuto" id="{slide["id"]}" data-lezione="{slide["lezione_id"]}">'
            f'<div class="dentro"><div class="testo"><div class="occhiello">{html.escape(slide["occhiello"])}</div>'
            f'<h2>{html.escape(slide["titolo"])}</h2><ul>{punti}</ul></div>'
            f'<div class="figura">{disegno}</div></div>{piede}</section>')


def costruisci_html(progetto: Path, dati: dict, piano: dict, titoli: dict[str, str], pacchetti: list) -> str:
    corso = dict(dati["corso"])
    marchio = dati["marchio"]
    corso["nota_copertina"] = marchio.get("nota_copertina", "")
    tav = visuali.tavolozza(marchio["colori"])
    famiglia = re.sub(r"[^A-Za-z0-9 ]", "", marchio.get("font") or "Montserrat") or "Montserrat"
    caratteri = caratteri_incorporati(progetto / "intake/marchio", famiglia)
    pila = f"{famiglia},'Helvetica Neue',Arial,sans-serif" if caratteri else "'Helvetica Neue',Arial,sans-serif"
    logo = trova_logo(progetto, marchio)
    sezioni = []
    pagina = 1
    totale = sum(len(v) for v in piano["lezioni"].values())
    for lezione_id, slide_lezione in piano["lezioni"].items():
        for slide in slide_lezione:
            sezioni.append(slide_html(slide, corso, titoli.get(lezione_id, ""), pagina, totale, tav, pacchetti))
            pagina += 1
    marchio_html = f'<img class="marchio" alt="" src="{logo}">' if logo else ""
    return f'''<!doctype html><html lang="{corso['lingua']}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(corso['titolo'])}</title><style>
{caratteri}
:root{{--scuro:{tav['scuro']};--primario:{tav['primario']};--accento:{tav['accento']};--fondo:{tav['fondo']};--tenue:{tav['neutro']}}}
*{{box-sizing:border-box}}html,body{{width:100%;height:100%;margin:0;overflow:hidden;background:#071426}}
.schermo{{position:fixed;inset:0;overflow:hidden}}
.palco{{position:absolute;left:0;top:0;width:1920px;height:1080px;overflow:hidden;transform-origin:0 0;background:var(--fondo)}}
.slide{{position:absolute;inset:0;width:1920px;height:1080px;visibility:hidden;opacity:0;pointer-events:none;background:linear-gradient(135deg,{tav['primario_chiaro']}66,transparent 48%,{tav['accento_chiaro']}55),var(--fondo);font-family:{pila};color:var(--scuro)}}
.slide.attiva,.slide.visibile{{visibility:visible;opacity:1;pointer-events:auto}}
.slide::before{{content:"";position:absolute;width:520px;height:520px;border-radius:50%;right:-240px;top:-280px;background:{tav['primario_chiaro']}}}
.slide::after{{content:"";position:absolute;width:390px;height:390px;border-radius:50%;left:-230px;bottom:-270px;background:{tav['accento_chiaro']}}}
.dentro{{position:absolute;inset:0;padding:92px 150px 116px;z-index:2}}
.marchio{{position:absolute;right:28px;top:24px;width:150px;z-index:50}}
.occhiello{{font-size:21px;line-height:1.2;font-weight:800;letter-spacing:.16em;color:var(--primario);text-transform:uppercase;margin-bottom:18px}}
h1,h2{{margin:0;font-weight:800;letter-spacing:-.045em}}h1{{font-size:101px;line-height:1.01;max-width:1390px}}h2{{font-size:62px;line-height:1.04;max-width:790px}}
footer{{position:absolute;z-index:5;left:150px;right:150px;bottom:45px;padding-top:17px;border-top:2px solid {tav['neutro_chiaro']};display:flex;justify-content:space-between;color:var(--tenue);font-size:17px;font-weight:700}}
.copertina{{color:#fff;background:radial-gradient(circle at 82% 20%,{tav['accento']}4d,transparent 35%),radial-gradient(circle at 15% 82%,{tav['primario']}5c,transparent 39%),var(--scuro)}}
.copertina::before{{background-color:transparent;background-image:linear-gradient(#ffffff12 1px,transparent 1px),linear-gradient(90deg,#ffffff12 1px,transparent 1px);background-size:64px 64px;inset:0;width:auto;height:auto;border-radius:0}}
.copertina::after{{display:none}}
.copertina .dentro{{display:flex;flex-direction:column;justify-content:center;padding-right:360px}}
.copertina .occhiello{{color:{tav['primario_tenue']}}}
.copertina p{{margin:35px 0 0;max-width:1150px;font-size:35px;line-height:1.38;color:#dce9f8;font-weight:500}}
.riga-titolo{{display:flex;gap:18px;align-items:center;margin-top:45px;color:#bcd0e5;font-size:20px}}
.copertina footer{{color:#9fb0c5;border-color:#ffffff26}}
.contenuto .dentro{{display:grid;grid-template-columns:minmax(600px,.92fr) minmax(0,1.08fr);gap:54px;align-items:center}}
.testo ul{{list-style:none;padding:0;margin:34px 0 0;display:grid;gap:17px;max-width:760px}}
.testo li{{position:relative;padding:17px 21px 17px 55px;border-radius:17px;background:#fff;border:2px solid {tav['primario_chiaro']};font-size:23px;line-height:1.32;font-weight:600;color:#405167;box-shadow:0 8px 27px #00489112}}
.testo li::before{{content:"";position:absolute;left:22px;top:25px;width:13px;height:13px;border-radius:50%;background:linear-gradient(135deg,var(--primario),var(--accento))}}
.figura{{height:650px;display:flex;align-items:center;justify-content:center;border-radius:30px;background:linear-gradient(145deg,#fff,#f8fbff);border:2px solid {tav['primario_chiaro']};box-shadow:0 18px 55px #00489114;overflow:hidden;padding:12px}}
.disegno{{width:100%;height:100%;display:block}}
.etichetta,.etichetta-grande,.battuta,.numero-cella,.numero-passo,.nodo text,.etichetta-guida text{{font-family:{pila};fill:{tav['scuro']};font-weight:800}}
.etichetta{{font-size:20px}}.etichetta-grande{{font-size:35px}}.battuta{{font-size:25px}}
.etichetta-guida text{{font-size:19px}}.etichetta-guida path{{fill:none;stroke:{tav['scuro']};stroke-width:4px;stroke-linecap:round}}
.etichetta,.etichetta-grande,.battuta,.etichetta-guida text{{paint-order:stroke fill;stroke:#fff;stroke-width:7px;stroke-linejoin:round}}
.numero-cella{{font-size:18px;text-anchor:middle}}.numero-passo{{font-size:48px;text-anchor:middle}}.nodo text{{font-size:18px;text-anchor:middle}}
.comandi{{position:fixed;z-index:100;left:50%;bottom:18px;transform:translateX(-50%);display:flex;align-items:center;gap:10px;padding:9px 15px;border-radius:999px;background:#071426d1;opacity:0;transition:opacity .2s}}
body:hover .comandi{{opacity:1}}
.comandi button{{width:40px;height:40px;border:0;border-radius:50%;background:#ffffff21;color:#fff;font-size:20px}}
.comandi span{{min-width:80px;text-align:center;color:#fff;font:600 14px {pila}}}
@page{{size:1920px 1080px;margin:0}}
@media print{{html,body{{width:1920px;height:auto;overflow:visible;background:#fff}}.schermo{{position:static;overflow:visible}}.palco{{position:static;width:auto;height:auto;transform:none!important}}.slide{{position:relative;display:block!important;visibility:visible!important;opacity:1!important;width:1920px;height:1080px;break-after:page}}.comandi{{display:none!important}}}}
</style></head><body><div class="schermo"><main class="palco" id="palco">{''.join(sezioni)}{marchio_html}</main></div>
<div class="comandi"><button id="indietro">‹</button><span id="contatore"></span><button id="avanti">›</button></div><script>
class Mazzo{{constructor(){{this.s=[...document.querySelectorAll('.slide')];this.palco=document.getElementById('palco');const q=new URLSearchParams(location.search);this.i=Math.max(0,Math.min(this.s.length-1,(parseInt(q.get('slide')||'1')-1)));this.scala();this.mostra(this.i);addEventListener('resize',()=>this.scala());document.getElementById('indietro').onclick=()=>this.mostra(this.i-1);document.getElementById('avanti').onclick=()=>this.mostra(this.i+1);addEventListener('keydown',e=>{{if(['ArrowRight','PageDown',' '].includes(e.key))this.mostra(this.i+1);if(['ArrowLeft','PageUp'].includes(e.key))this.mostra(this.i-1)}})}}scala(){{const f=Math.min(innerWidth/1920,innerHeight/1080),x=(innerWidth-1920*f)/2,y=(innerHeight-1080*f)/2;this.palco.style.transform=`translate(${{x}}px,${{y}}px) scale(${{f}})`}}mostra(i){{this.i=Math.max(0,Math.min(i,this.s.length-1));this.s.forEach((x,n)=>{{x.classList.toggle('attiva',n===this.i);x.classList.toggle('visibile',n===this.i)}});document.getElementById('contatore').textContent=`${{this.i+1}} / ${{this.s.length}}`}}}}new Mazzo();
</script></body></html>'''


# --- orchestrazione ------------------------------------------------------

def scopri(dati: dict) -> list[Lezione]:
    cartella = Path(dati["sorgenti"]["cartella"]).expanduser()
    if not cartella.is_dir():
        raise Errore(f"Cartella dei testi non trovata: {cartella}")
    estensioni = {e.lower() for e in dati["sorgenti"].get("estensioni", [".md", ".txt"])}
    salta_note = bool(dati["sorgenti"].get("salta_note", True))
    trovate: list[Lezione] = []
    for file in sorted(cartella.rglob("*")):
        if not file.is_file() or file.suffix.lower() not in estensioni or file.name.startswith("."):
            continue
        modulo, numero, titolo = riconosci(file, cartella)
        blocchi, testo = leggi_sorgente(file, salta_note)
        progressivo = numero or len(trovate) + 1
        identificativo = f"m{modulo:02d}-l{progressivo:02d}"
        nome_export = f"M{modulo} - {modulo}.{progressivo} {titolo}" if numero else f"{progressivo:02d} - {titolo}"
        lezione = Lezione(identificativo, modulo, progressivo, titolo, file, nome_sicuro(nome_export), blocchi, testo)
        lezione.unita = dividi_in_unita(testo)
        trovate.append(lezione)
    if not trovate:
        raise Errore(f"Nessun testo trovato in {cartella}")
    return sorted(trovate, key=lambda l: (l.modulo, l.numero, l.titolo))


def principale() -> int:
    analizzatore = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizzatore.add_argument("progetto")
    analizzatore.add_argument("--rigenera-piano", action="store_true", help="Riscrive il piano perdendo le correzioni a mano")
    analizzatore.add_argument("--solo-piano", action="store_true", help="Si ferma al piano, senza costruire l'HTML")
    argomenti = analizzatore.parse_args()

    progetto = Path(argomenti.progetto).expanduser().resolve()
    dati = carica_corso(progetto / "corso.json")
    corso = dati["corso"]
    pacchetti = visuali.carica_pacchetti(dati["visuali"]["pacchetti"])
    lezioni = scopri(dati)

    file_piano = progetto / "piano" / "slide.json"
    titoli = {l.id: l.titolo for l in lezioni}
    adesso = datetime.now(timezone.utc).isoformat()

    sorgenti_registrate = []
    indice_testi = []
    for lezione in lezioni:
        copia = progetto / "intake/sorgenti" / lezione.file.name
        copia.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(lezione.file, copia)
        sorgenti_registrate.append({
            "lezione_id": lezione.id,
            "originale": str(lezione.file),
            "copia": f"intake/sorgenti/{lezione.file.name}",
            "impronta": impronta_file(copia),
        })
        file_testo = progetto / "voce/testi" / f"{lezione.id}.txt"
        file_testo.parent.mkdir(parents=True, exist_ok=True)
        file_testo.write_text(lezione.testo, encoding="utf-8")
        indice_testi.append({
            "lezione_id": lezione.id,
            "titolo": lezione.titolo,
            "percorso": f"voce/testi/{lezione.id}.txt",
            "caratteri": len(lezione.testo.strip()),
            "parole": len(lezione.testo.split()),
        })
        for ordine, testo_unita in enumerate(lezione.unita, 1):
            file_unita = progetto / "voce/testi/unita" / f"{lezione.id}-u{ordine:03d}.txt"
            file_unita.parent.mkdir(parents=True, exist_ok=True)
            file_unita.write_text(testo_unita.strip() + "\n", encoding="utf-8")

    scrivi_json(progetto / "voce/testi/indice.json", {"schema": "crea-videocorso/1", "lezioni": indice_testi})

    if file_piano.exists() and not argomenti.rigenera_piano:
        piano = leggi_json(file_piano)
        print(f"Piano esistente riusato: {file_piano}")
    else:
        regolazioni = dati.get("slide", {})
        contesto = {**corso, "predefinito": dati["visuali"]["predefinito"]}
        piano = {
            "schema": "crea-videocorso/1",
            "corso": corso["titolo"],
            "generato": adesso,
            "lezioni": {l.id: pianifica(l, contesto, pacchetti, regolazioni) for l in lezioni},
        }
        scrivi_json(file_piano, piano)
        print(f"Piano scritto: {file_piano}")

    mancanti = [i for i in piano["lezioni"] if i not in titoli]
    if mancanti:
        raise Errore(f"Il piano contiene lezioni che non esistono più fra i testi: {', '.join(mancanti)}")

    manifesto = {
        "schema": "crea-videocorso/1",
        "progetto": {
            "slug": corso["slug"],
            "titolo": corso["titolo"],
            "stato": "slide_pronte",
            "lingua": corso["lingua"],
            "pubblico": corso.get("pubblico", ""),
            "rischio": corso.get("rischio", "none"),
            "validazione_professionale": corso.get("nota_validazione", "non eseguita"),
            "aggiornato": adesso,
        },
        "voce": {**dati["voce"], "stato": "da_generare"},
        "moduli": [
            {"id": f"m{numero:02d}", "ordine": numero, "titolo": titolo}
            for numero, titolo in sorted(((int(k), v) for k, v in (dati.get("moduli") or {}).items()))
        ] or [{"id": f"m{m:02d}", "ordine": m, "titolo": ""} for m in sorted({l.modulo for l in lezioni})],
        "lezioni": [],
        "unita": [],
        "slide": [],
        "sorgenti": sorgenti_registrate,
        "approvazioni": (leggi_json(progetto / "manifesti/manifesto.json").get("approvazioni")
                         if (progetto / "manifesti/manifesto.json").exists() else None) or [
            {"id": "app-01", "passaggio": "testi-congelati", "stato": "da_fare", "chi": "", "quando": "", "note": ""},
            {"id": "app-02", "passaggio": "stile-slide", "stato": "da_fare", "chi": "", "quando": "", "note": ""},
            {"id": "app-03", "passaggio": "prova-voce", "stato": "da_fare", "chi": "", "quando": "", "note": ""},
            {"id": "app-04", "passaggio": "spesa-voce", "stato": "da_fare", "chi": "", "quando": "", "note": ""},
            {"id": "app-05", "passaggio": "consegna", "stato": "da_fare", "chi": "", "quando": "", "note": ""},
        ],
        "consegne": {
            "html": "slide/indice.html",
            "pdf": f"consegne/pdf/{nome_sicuro(corso['titolo'])} - Slide.pdf",
            "audio": "consegne/audio",
            "video": "consegne/video",
            "richieste": dati["consegne"],
        },
    }

    pagina = 1
    for lezione in lezioni:
        slide_lezione = piano["lezioni"].get(lezione.id, [])
        manifesto["lezioni"].append({
            "id": lezione.id,
            "modulo_id": f"m{lezione.modulo:02d}",
            "ordine": lezione.numero,
            "titolo": lezione.titolo,
            "nome_export": lezione.nome_export,
            "file_audio": f"voce/lezioni/{lezione.id}.mp3",
            "file_allineamento": f"voce/allineamenti/{lezione.id}-completo.json",
            "durata_ms": None,
        })
        for ordine, testo_unita in enumerate(lezione.unita, 1):
            identificativo = f"{lezione.id}-u{ordine:03d}"
            manifesto["unita"].append({
                "id": identificativo,
                "lezione_id": lezione.id,
                "ordine": ordine,
                "testo": f"voce/testi/unita/{identificativo}.txt",
                "impronta_testo": impronta_testo(testo_unita.strip()),
                "file_audio": None,
                "file_allineamento": None,
                "durata_ms": None,
            })
        for ordine, slide in enumerate(slide_lezione, 1):
            manifesto["slide"].append({
                "id": slide["id"],
                "lezione_id": lezione.id,
                "ordine": ordine,
                "pagina": pagina,
                "visual": slide["visual"],
            })
            pagina += 1

    vecchio = progetto / "manifesti/manifesto.json"
    if vecchio.exists():
        precedente = leggi_json(vecchio)
        indice_unita = {u["id"]: u for u in precedente.get("unita", [])}
        intatte: dict[str, bool] = {}
        for unita in manifesto["unita"]:
            vecchia = indice_unita.get(unita["id"])
            uguale = bool(vecchia and vecchia.get("impronta_testo") == unita["impronta_testo"])
            if uguale:
                unita.update({k: vecchia.get(k) for k in ("file_audio", "file_allineamento", "durata_ms", "generato", "prova")})
            intatte[unita["lezione_id"]] = intatte.get(unita["lezione_id"], True) and uguale
        # La voce dipende solo dal testo: se il testo non è cambiato, l'audio resta valido.
        # Il video dipende anche dalle slide: si riporta solo se le slide di quella lezione
        # sono rimaste identiche, altrimenti va rimontato.
        slide_vecchie: dict[str, list[str]] = {}
        for slide in precedente.get("slide", []):
            slide_vecchie.setdefault(slide["lezione_id"], []).append(slide["id"])
        slide_nuove: dict[str, list[str]] = {}
        for slide in manifesto["slide"]:
            slide_nuove.setdefault(slide["lezione_id"], []).append(slide["id"])
        indice_lezioni = {l["id"]: l for l in precedente.get("lezioni", [])}
        for lezione in manifesto["lezioni"]:
            vecchia = indice_lezioni.get(lezione["id"])
            if not vecchia or not intatte.get(lezione["id"]):
                continue
            for campo in ("durata_ms", "audio_consegna"):
                if vecchia.get(campo):
                    lezione[campo] = vecchia[campo]
            if slide_vecchie.get(lezione["id"]) == slide_nuove.get(lezione["id"]):
                for campo in ("video_consegna", "ingressi_slide"):
                    if vecchia.get(campo):
                        lezione[campo] = vecchia[campo]
        for campo in ("durata_audio_secondi", "durata_video_secondi"):
            if precedente.get("consegne", {}).get(campo):
                manifesto["consegne"][campo] = precedente["consegne"][campo]
        if any(u.get("file_audio") for u in manifesto["unita"]):
            manifesto["voce"]["stato"] = "prova" if any(u.get("prova") for u in manifesto["unita"]) else "parziale"
        if precedente.get("progetto", {}).get("stato") and all(u.get("file_audio") for u in manifesto["unita"]):
            manifesto["progetto"]["stato"] = precedente["progetto"]["stato"]
    scrivi_json(vecchio, manifesto)

    if argomenti.solo_piano:
        print(f"Slide pianificate: {len(manifesto['slide'])} in {len(lezioni)} lezioni")
        return 0

    file_html = progetto / "slide/indice.html"
    file_html.parent.mkdir(parents=True, exist_ok=True)
    file_html.write_text(costruisci_html(progetto, dati, piano, titoli, pacchetti), encoding="utf-8")
    parole = sum(len(l.testo.split()) for l in lezioni)
    print(f"Mazzo scritto: {file_html}")
    print(f"{len(lezioni)} lezioni · {len(manifesto['slide'])} slide · {len(manifesto['unita'])} unità di voce · {parole} parole")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(principale())
    except Errore as errore:
        print(str(errore), file=sys.stderr)
        raise SystemExit(2)
