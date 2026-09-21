# La scheda del corso e la cartella del progetto

## corso.json

La scheda sta nella radice del progetto e comanda tutto. Il modello vuoto è `<skill>/riferimenti/corso-modello.json`.

| Campo | A che serve |
|---|---|
| `corso.titolo` | Titolo pieno, sulle copertine e nel pacchetto finale |
| `corso.titolo_breve` | Va nel piede di ogni slide: tienilo corto |
| `corso.sottotitolo` | Una riga sotto il titolo |
| `corso.pubblico` | Per esempio «adulti 18+»: finisce nel LEGGIMI del pacchetto |
| `corso.rischio` | Etichetta libera, per esempio `salute` o `nessuno` |
| `corso.nota_validazione` | La frase che dichiara che cosa non è stato validato da un professionista |
| `sorgenti.cartella` | Dove stanno i testi approvati |
| `sorgenti.estensioni` | Quali file leggere, di solito `.md` e `.txt` |
| `sorgenti.salta_note` | Se `true`, taglia da «## Note» o «## Fonti» in giù |
| `moduli` | Numero del modulo e suo titolo: `{"1": "Le basi"}` |
| `marchio.cartella` | Cartella con logo e caratteri: vengono copiati dentro il progetto |
| `marchio.font` | Nome della famiglia; i file `.ttf` o `.woff2` vengono incorporati nell'HTML |
| `marchio.colori` | `scuro`, `primario`, `accento`, `fondo`: da questi nascono tutte le tinte |
| `marchio.nota_copertina` | Riga piccola sulla copertina, per esempio «18+» o il nome del marchio |
| `voce.voice_id` | La voce del fornitore; si può tenere in `segreti.env` |
| `voce.model_id` | Di norma `eleven_v3` |
| `voce.impostazioni` | Stabilità, somiglianza, stile, velocità |
| `visuali.pacchetti` | Pacchetti di disegni aggiuntivi installati in `~/.crea-videocorso/pacchetti-visual/` |
| `visuali.predefinito` | Il disegno da usare quando nessuna regola scatta |
| `slide.caratteri_per_slide` | Quanto testo prima di cambiare slide: più basso, più slide |
| `consegne` | Che cosa serve davvero: html, pdf, audio, video |

## I nomi dei file dei testi

Il riconoscitore capisce, in quest'ordine: `M1-L01 - Titolo`, `1.2 Titolo`, `M1 - 2 - Titolo`, `L01 - Titolo`, e il numero del modulo scritto nella cartella («Modulo 2»). Se non riconosce nulla, mette tutto nel modulo 1 nell'ordine alfabetico: in quel caso dillo alla persona e proponi di rinominare.

## Che cosa c'è nella cartella

```
corso.json            la scheda
intake/sorgenti/      copia dei testi al momento del congelamento
intake/marchio/       logo e caratteri copiati
piano/slide.json      il piano delle slide: si corregge a mano
slide/indice.html     il mazzo, un file solo, senza nulla da internet
voce/testi/           il testo pulito di ogni lezione e delle sue unità
voce/segmenti/        un audio per unità
voce/allineamenti/    i tempi per carattere, da cui nasce la sincronia
voce/lezioni/         la traccia unita di ogni lezione
consegne/             audio, video e PDF finiti
controlli/            rapporto e immagini di controllo
manifesti/manifesto.json   lo stato del lavoro
tmp/slide/            un'immagine per slide, serve al montaggio
```

## Il manifesto

È la memoria del lavoro: elenca moduli, lezioni, unità di voce, slide, approvazioni e consegne. Lo aggiornano gli strumenti: non si scrive a mano, se non per segnare un'approvazione.

Le **approvazioni** sono cinque: `testi-congelati`, `stile-slide`, `prova-voce`, `spesa-voce`, `consegna`. Ognuna ha `stato` (`da_fare` o `fatto`), `chi`, `quando`, `note`. Una modifica successiva ai testi, alla voce o allo stile riapre quella che riguarda.
