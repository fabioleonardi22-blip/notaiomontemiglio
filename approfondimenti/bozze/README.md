# Bozze editoriali

Questa cartella contiene esclusivamente contenuti generati automaticamente e non pubblicati.

## Flusso
1. Ogni lunedì alle 06:00 UTC (08:00 in Italia durante l'ora legale; 07:00 durante l'ora solare), oppure tramite avvio manuale, il workflow consulta le pagine istituzionali configurate.
2. Il generatore prepara una bozza in Markdown con titolo, metadati SEO, struttura editoriale e fonti.
3. GitHub apre una Pull Request per la revisione. La bozza non entra nel sito pubblico finché la PR non viene approvata e il contenuto non viene trasformato in una pagina editoriale pubblicabile.
4. Il Notaio verifica accuratezza, aggiornamento normativo, completezza delle fonti e formulazioni prima della pubblicazione.

## Segreto necessario
In GitHub: **Settings → Secrets and variables → Actions → New repository secret**.
- Nome: `OPENAI_API_KEY`
- Valore: chiave API OpenAI dello Studio.

Non inserire mai la chiave nel codice, nei commit o nei file del sito.

Il sistema non pubblica autonomamente contenuti legali: l'automazione produce proposte di articoli, non pareri notarili né aggiornamenti normativi certificati.
