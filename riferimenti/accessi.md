# Ambiente e chiavi

## Che cosa serve

- **Python 3.10** o successivo, già presente su Mac.
- **ffmpeg** e **ffprobe**: uniscono l'audio e montano i video. Su Mac: `brew install ffmpeg`.
- **Google Chrome** o Chromium: trasforma le slide in immagini e in PDF. Non serve né Node né Playwright.

Controllo:

```bash
python3 "<skill>/strumenti/prepara-ambiente.py" --controlla
```

## Le chiavi

Stanno solo in `~/.crea-videocorso/segreti.env`, che il comando crea vuoto e leggibile solo dall'utente:

```
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
```

Regole da dire alla persona: apre il file con un editor, incolla il valore dopo l'uguale senza spazi né virgolette, salva. Non incolla mai una chiave in chat, in un documento condiviso o in una email. Se una chiave finisce in chat, la considera esposta: la revoca e ne crea una nuova.

Puoi aprire il file per lei senza leggerlo: `open -e ~/.crea-videocorso/segreti.env`. Non leggere mai il contenuto: gli strumenti lo leggono da soli e non stampano i valori.

## Per prendere la chiave di ElevenLabs

1. Entrare in elevenlabs.io con il proprio account.
2. Nel profilo aprire la sezione delle chiavi API e crearne una nuova con un nome riconoscibile.
3. Copiarla subito: viene mostrata una sola volta.
4. L'identificativo della voce si copia dalla pagina della voce scelta.

Controlla anche quanti caratteri restano nel piano: un corso da diecimila parole sono circa sessantamila caratteri.
