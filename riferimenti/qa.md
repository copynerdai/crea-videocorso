# I controlli

`controlla.py` scrive `controlli/rapporto.json` ed esce con 1 se trova guasti.

## Guasti (fermano la consegna)

- pagine delle slide non consecutive, o piano e manifesto che non concordano;
- una lezione senza testo per la voce, o assente dal piano;
- mazzo HTML mancante, o con un numero di slide diverso dal manifesto;
- PDF mancante o vuoto, quando è richiesto;
- unità senza voce, quando l'audio è richiesto;
- traccia silenziosa o audio che non si decodifica;
- video mancante, non 1920×1080, senza una delle due tracce;
- durata del video lontana più di 0,75 secondi dalla voce;
- ingressi delle slide fuori ordine, o una slide che entra dopo la fine.

## Avvisi (si valutano)

- la voce è quella finta di collaudo: non si consegna;
- audio al limite, con picco sopra −0,5 dB;
- il mazzo carica qualcosa da internet: non sarebbe più autonomo;
- passaggi ancora da approvare.

## Quello che nessuno strumento può controllare

Guarda e ascolta almeno una lezione intera prima di consegnare: pronuncia dei nomi, slide che cambiano nel punto giusto, disegni adatti a ciò che si sta dicendo, avvertenze rimaste dov'erano. Il resto è misura; questo è giudizio.
