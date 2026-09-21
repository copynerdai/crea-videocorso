---
name: crea-videocorso
description: Trasforma i testi approvati di un corso in slide, voce narrante, video montati e un pacchetto da consegnare. Per la post-produzione di videocorsi e infoprodotti, non per scriverne i contenuti.
disable-model-invocation: true
argument-hint: "[nome del corso]"
---

# Crea videocorso

Porti un corso già scritto dai testi ai video finiti, in tre tempi: prima le **domande**, con cui la persona ti dice tutto ciò che serve; poi il **lavoro autonomo**, che controlli da solo; poi i **giri di revisione**, fino all'approvazione. Parli in italiano semplice, con frasi complete, e spieghi ogni termine tecnico la prima volta che lo usi.

Corso indicato dalla persona, se c'è: $ARGUMENTS

La cartella della skill è `${CLAUDE_SKILL_DIR}`: nei riferimenti è scritta come `<skill>`. I comandi elencati in `${CLAUDE_SKILL_DIR}/strumenti/LEGGIMI.md` si lanciano con `python3 "${CLAUDE_SKILL_DIR}/strumenti/<nome>.py"`: ciascuno ha `--help` ed esce con un codice diverso da 0 quando un controllo non passa.

## Il confine

**I testi del corso comandano.** Li trasformi, non li riscrivi: niente promesse nuove, niente numeri nuovi, niente avvertenze tolte per far scorrere meglio il ritmo.

Puoi fare solo interventi tecnici: dividere il testo in unità per la voce, sistemare la punteggiatura per il parlato, sciogliere sigle e numeri ambigui, condensare una frase sulla slide. Tutto il resto — ricerca, struttura del corso, riscritture, validazione medica o legale — torna a chi l'ha scritto.

**La qualità della produzione non è la validità del contenuto.** Un corso può essere prodotto benissimo e restare senza validazione professionale: se è così, resta scritto nel manifesto e nel pacchetto finale, e non lo si presenta mai come validato.

## Regole per tutto il percorso

- **Chiedi solo le decisioni.** I fatti (titoli, moduli, colori del marchio, dove stanno i testi) li cerchi tu. Alla persona chiedi ciò che solo lei può scegliere. Fuori dai giri di domande fai subito solo la domanda che blocca il lavoro.
- **La spesa si autorizza due volte.** La voce di ElevenLabs si paga: prima si approva un campione di voce, poi si autorizza il lotto intero. `genera-voce.py` senza `--esegui` non spende nulla e ti dice quanti caratteri costerà.
- **La voce di prova non si consegna mai.** `--prova` usa la voce di sistema del Mac per far vedere come si muove il montaggio. Resta scritto nei file e i controlli te lo ricordano.
- **Le chiavi non passano dalla chat.** Stanno in `~/.crea-videocorso/segreti.env`, come spiega `${CLAUDE_SKILL_DIR}/riferimenti/accessi.md`. Se una chiave compare in chat, non ripeterla e invita la persona a revocarla.
- **Il piano delle slide è il punto di controllo.** Sta in `piano/slide.json`, si legge e si corregge a mano; l'HTML si ricostruisce sempre da lì. Non rigeneri il piano senza dirlo, perché le correzioni della persona andrebbero perse.
- **Niente si pubblica da qui.** La skill produce file su disco. Caricare su una piattaforma, mandare al cliente o pubblicare sono decisioni della persona.
- **Dopo ogni passo dici dove sono i file**, con il percorso esatto.

## 1 · Inventario

1. **Apri chiedendo il corso**: come si chiama e dove stanno i testi approvati. Una riga di saluto e la domanda, nient'altro.
2. Guarda i testi: quanti file, come sono nominati, se hanno moduli, quanto sono lunghi, se contengono indicazioni visuali fra parentesi quadre, note o fonti in fondo.
3. Cerca il marchio: logo, caratteri, colori. Se mancano, dillo: vanno preparati fuori da questa skill.
4. Controlla se esiste già un progetto per questo corso. Se c'è, leggi `manifesti/manifesto.json` e riprendi dal primo passo non fatto, invece di rifare ciò che è già approvato.

**Completato quando:** sai dove sono i testi, quante lezioni sono, com'è il marchio, e hai detto alla persona che cosa c'è e che cosa manca.

## 2 · Domande

Segui `${CLAUDE_SKILL_DIR}/riferimenti/domande.md`: un giro solo di domande numerate, ciascuna con la tua raccomandazione. Le domande che la persona non commenta si considerano accettate come da raccomandazione.

**Completato quando:** la scheda `corso.json` è compilata con le risposte dentro e la persona l'ha confermata.

## 3 · Ambiente

```bash
python3 "${CLAUDE_SKILL_DIR}/strumenti/prepara-ambiente.py" --controlla
```

Servono Python 3.10 o successivo, ffmpeg e un browser Chrome o Chromium. Senza `--controlla` crea `~/.crea-videocorso/` e il file delle chiavi vuoto. I dettagli sono in `${CLAUDE_SKILL_DIR}/riferimenti/accessi.md`.

**Completato quando:** il comando scrive «Ambiente pronto».

## 4 · Progetto e testi congelati

```bash
python3 "${CLAUDE_SKILL_DIR}/strumenti/avvia-corso.py" <progetto> --titolo "<titolo>" --sorgenti <cartella-testi>
```

Poi completa `corso.json` con le risposte del giro di domande: moduli, marchio, voce, pacchetti visuali, consegne richieste. La struttura di ogni campo è in `${CLAUDE_SKILL_DIR}/riferimenti/progetto.md`.

Prima di andare avanti chiedi alla persona di dichiarare i testi **congelati**: da quel momento una modifica al testo obbliga a rifare voce e video di quella lezione. Segna l'approvazione `testi-congelati` nel manifesto.

**Completato quando:** `corso.json` è completo e i testi sono dichiarati congelati.

## 5 · Slide

```bash
python3 "${CLAUDE_SKILL_DIR}/strumenti/costruisci-slide.py" <progetto>
```

Ricava le trascrizioni per la voce, il piano delle slide e il mazzo HTML. Le regole di impaginazione e la scelta dei disegni sono in `${CLAUDE_SKILL_DIR}/riferimenti/slide.md`.

Poi mostra un **campione** prima di renderizzare tutto:

```bash
python3 "${CLAUDE_SKILL_DIR}/strumenti/renderizza.py" <progetto> --pagine 1,4,9 --senza-pdf
```

Apri le immagini e chiedi un parere su: leggibilità, quantità di testo per slide, disegni azzeccati o no. Correggi `piano/slide.json` dove serve e ricostruisci. Quando lo stile è approvato, renderizza tutto:

```bash
python3 "${CLAUDE_SKILL_DIR}/strumenti/renderizza.py" <progetto>
```

**Completato quando:** la persona ha approvato il campione, esistono un'immagine per slide e il PDF, e l'approvazione `stile-slide` è segnata.

## 6 · Voce

Leggi `${CLAUDE_SKILL_DIR}/riferimenti/voce.md`. L'ordine è sempre questo:

```bash
python3 "${CLAUDE_SKILL_DIR}/strumenti/genera-voce.py" <progetto>                        # quanto costa
python3 "${CLAUDE_SKILL_DIR}/strumenti/genera-voce.py" <progetto> --lezione <id> --esegui  # una lezione sola
python3 "${CLAUDE_SKILL_DIR}/strumenti/genera-voce.py" <progetto> --esegui                 # tutto il resto
```

Fai ascoltare una lezione sola prima del lotto: è il campione di voce. Segna `prova-voce` solo dopo il suo sì, e `spesa-voce` solo dopo l'autorizzazione esplicita alla spesa. Senza le due approvazioni nel manifesto lo strumento si rifiuta di spendere.

Se la quota del fornitore è esaurita, non è un blocco di tutto: finisci slide, PDF e controlli, e scrivi che manca solo la voce.

```bash
python3 "${CLAUDE_SKILL_DIR}/strumenti/unisci-audio.py" <progetto>
```

**Completato quando:** ogni lezione ha la sua traccia in `consegne/audio/` e il suo allineamento.

## 7 · Montaggio

```bash
python3 "${CLAUDE_SKILL_DIR}/strumenti/monta-video.py" <progetto>
```

Ogni slide entra nel momento in cui la voce pronuncia la frase scritta nel suo campo `entra_da`. Se una frase non si trova, lo strumento si ferma e la nomina: quasi sempre vuol dire che il piano è stato corretto a mano con parole che nel testo non ci sono.

**Completato quando:** in `consegne/video/` c'è un MP4 per lezione.

## 8 · Controlli e consegna

```bash
python3 "${CLAUDE_SKILL_DIR}/strumenti/controlla.py" <progetto>
python3 "${CLAUDE_SKILL_DIR}/strumenti/impacchetta.py" <progetto> --dove "<cartella>"
```

I controlli guardano struttura, file, misure dei video, sincronia e silenzi; l'elenco è in `${CLAUDE_SKILL_DIR}/riferimenti/qa.md`. Il pacchetto si crea solo se passano.

Prima di consegnare, guarda e ascolta almeno una lezione intera insieme alla persona.

**Completato quando:** i controlli passano, la persona ha visto un video intero e l'approvazione `consegna` è segnata.

## Quando fermarsi

Fermi il passo e chiedi quando: i testi non sono stabili o si contraddicono; un'avvertenza andrebbe tolta o cambiata; manca la chiave, la voce o l'autorizzazione alla spesa; un adattamento cambierebbe il senso, una promessa o un limite di sicurezza; i controlli trovano guasti che non sai spiegare.
