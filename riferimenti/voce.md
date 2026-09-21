# La voce

## Come si divide il testo

Il testo di ogni lezione si taglia in unità da 4.300 caratteri al massimo, sui confini fra paragrafi. Ogni unità è una richiesta al fornitore. Le unità della stessa lezione vengono poi unite in una traccia sola.

## ElevenLabs

Si usa la chiamata che restituisce anche i **tempi per carattere**: senza quelli non si può sincronizzare nulla. Il modello `eleven_v3` non accetta i campi di continuità fra un pezzo e l'altro.

Le impostazioni della voce stanno in `corso.json`. Stabilità bassa rende la lettura più espressiva e meno prevedibile; alta la rende piatta ma costante. Per un corso conviene stare in mezzo.

## Le pronunce

Le parole che il lettore sbaglia (nomi propri, termini stranieri, sigle) si correggono **solo** nel testo tecnico in `voce/testi/`, mai nel testo approvato del corso. Tieni l'elenco delle correzioni in `corso.json` sotto `voce.pronunce` e dichiaralo alla persona.

## La voce di prova

`--prova` usa la voce di sistema del Mac e un allineamento uniforme. Serve solo a far vedere il ritmo del montaggio prima di spendere. Resta segnata nei file di allineamento: i controlli la riconoscono e il pacchetto finale si rifiuta di nascerne.

## Se la quota è esaurita

Non è un blocco del progetto: è un blocco di un passo. Finisci slide, PDF e controlli, scrivi nel manifesto che cosa manca, e riprendi da `genera-voce.py` quando la quota torna. Le unità già fatte non si rigenerano.
