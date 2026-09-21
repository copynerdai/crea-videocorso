# Come nascono le slide

## Dal testo al piano

Il testo si legge a blocchi separati da riga vuota. Un blocco tutto in grassetto, o preceduto da un'indicazione fra parentesi quadre, apre una slide nuova. Gli altri si accumulano finché non si superano i caratteri di `slide.caratteri_per_slide`.

Per ogni gruppo:

- il **titolo** è il titoletto in grassetto, se c'è; altrimenti la prima frase accorciata;
- il **corpo** sono le frasi successive, al massimo tre, accorciate a 118 caratteri, senza ripetere il titolo;
- il **punto d'ingresso** (`entra_da`) sono le prime tredici parole del blocco: serviranno per agganciare la slide alla voce;
- il **disegno** lo scelgono le parole del testo.

La prima slide di ogni lezione è la copertina: titolo della lezione, modulo e prima frase come sottotitolo.

## Correggere il piano

`piano/slide.json` è fatto per essere corretto a mano. Si possono cambiare titolo, corpo, occhiello e disegno; si possono togliere slide intere.

Una sola regola dura: **`entra_da` deve restare una frase che la voce pronuncia davvero**, copiata dal testo. Se la cambi con parole tue, il montaggio non la trova e si ferma.

Dopo aver corretto, ricostruisci senza `--rigenera-piano`: l'HTML si rifà dal piano corretto.

## I disegni

Nella skill ci sono dodici disegni neutri: `concetto` (tre passaggi), `ciclo`, `calendario`, `onda`, `mente`, `schermo`, `ritmo`, `dialogo`, `confronto`, `scala`, `avvertenza`, `elenco`.

Li sceglie un punteggio: vince la regola che riconosce più parole. Le parole scritte dall'autore fra parentesi quadre valgono il doppio, perché sono un'istruzione. Per imporre un disegno, scrivilo nel piano.

I pacchetti aggiuntivi stanno in `~/.crea-videocorso/pacchetti-visual/` e vincono sulle regole di base. Ognuno ha `pacchetto.json` con le sue regole ed etichette e `visuali.py` con una funzione `disegna(tipo, slide, tavolozza)`.

## Che cosa tenere d'occhio nel campione

Il testo fuori dal riquadro del disegno; le frasi troncate con i puntini; i titoli su tre righe; i disegni ripetuti troppe volte di seguito; il contrasto delle etichette sul fondo.
