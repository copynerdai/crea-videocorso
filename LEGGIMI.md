# crea-videocorso

Porta un corso già scritto dai testi ai video finiti: slide impaginate, voce narrante, sincronia, MP4 per lezione, PDF e un pacchetto da consegnare.

Non scrive i contenuti del corso: quelli arrivano già approvati.

## Che cosa produce

Per ogni lezione: un MP4 1920×1080 con la voce e le slide sincronizzate, un MP3 della sola voce, e le slide in PDF. Di tutto il corso: una presentazione HTML in un file solo, che si apre in un browser e si può modificare.

## Che cosa serve sul computer

- Python 3.10 o successivo (su Mac c'è già)
- ffmpeg: `brew install ffmpeg`
- Google Chrome o Chromium
- una chiave ElevenLabs, se si vuole la voce vera

Controllo: `python3 strumenti/prepara-ambiente.py --controlla`

## Come si installa

La cartella va in `~/.claude/skills/crea-videocorso/`. In Claude Code si richiama con `/crea-videocorso`.

I file personali stanno fuori dalla skill, in `~/.crea-videocorso/`: le chiavi in `segreti.env` e gli eventuali pacchetti di disegni in `pacchetti-visual/`. Così la cartella della skill si può copiare e passare a qualcun altro senza portarsi dietro nulla di privato.

## Come si usa

`/crea-videocorso` e poi si risponde alle domande. Oppure, a mano, nell'ordine descritto in `strumenti/LEGGIMI.md`.

## I due punti in cui si spende

La voce di ElevenLabs si paga a caratteri. `genera-voce.py` senza `--esegui` dice quanto costerebbe e non manda niente. Per spendere davvero servono due approvazioni segnate nel manifesto: il campione di voce e l'autorizzazione al lotto.

Per vedere come si muove il montaggio senza spendere c'è `--prova`, che usa la voce di sistema del Mac. Quella voce non si consegna: resta segnata nei file e i controlli la riconoscono.

## Da dove viene

Da sei videocorsi prodotti davvero fra agosto e settembre 2026: prima un corso pilota, poi cinque corsi interi. Gli strumenti sono quelli, generalizzati: la stessa impaginazione, la stessa sincronia basata sui tempi per carattere, gli stessi controlli.
