# Gli strumenti

Ognuno ha `--help` ed esce con un codice diverso da 0 quando qualcosa non va. Si lanciano con `python3 "<skill>/strumenti/<nome>.py"`.

| Strumento | Che cosa fa |
|---|---|
| `prepara-ambiente.py` | Controlla Python, ffmpeg e il browser; crea `~/.crea-videocorso/` e il file delle chiavi |
| `avvia-corso.py` | Crea la cartella del progetto e la scheda `corso.json` |
| `costruisci-slide.py` | Dai testi ricava trascrizioni, piano delle slide e mazzo HTML |
| `renderizza.py` | Trasforma il mazzo in un'immagine per slide e in un PDF |
| `genera-voce.py` | Pianifica la spesa, genera la voce vera o quella di prova |
| `unisci-audio.py` | Unisce i segmenti in una traccia per lezione e fonde i tempi |
| `monta-video.py` | Aggancia le slide alla voce e monta gli MP4 |
| `controlla.py` | Controlla struttura, file, media e sincronia |
| `impacchetta.py` | Prepara la cartella da consegnare, solo se i controlli passano |

`comune.py` e `visuali.py` sono moduli di supporto: non si lanciano.

## L'ordine normale

```bash
python3 prepara-ambiente.py --controlla
python3 avvia-corso.py <progetto> --titolo "..." --sorgenti <testi>
python3 costruisci-slide.py <progetto>
python3 renderizza.py <progetto> --pagine 1,4,9 --senza-pdf     # campione da far vedere
python3 renderizza.py <progetto>
python3 genera-voce.py <progetto>                                # quanto costa
python3 genera-voce.py <progetto> --lezione m01-l01 --esegui     # campione di voce
python3 genera-voce.py <progetto> --esegui
python3 unisci-audio.py <progetto>
python3 monta-video.py <progetto>
python3 controlla.py <progetto>
python3 impacchetta.py <progetto> --dove "<cartella>"
```

Rifare `costruisci-slide.py` non perde il lavoro già fatto: la voce resta se il testo non è cambiato, il video resta se anche le slide di quella lezione sono rimaste uguali.
