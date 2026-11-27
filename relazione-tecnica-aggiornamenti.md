# Relazione tecnica – aggiornamenti del sito

**Progetto:** Studio Notarile Daria Montemiglio  
**Repository:** `fabioleonardi22-blip/notaiomontemiglio`  
**Data verifica:** 27 novembre 2026

## Interventi verificati

- **Home page:** la sezione dedicata allo studio è presentata come “Lo Studio”. I collegamenti interni dalla Home a `studio.html` sono stati uniformati alla navigazione nella stessa scheda, evitando aperture superflue in nuove finestre.
- **Privacy Policy:** è presente `privacy-policy.html`, con informazioni su titolare, categorie di dati, finalità e basi giuridiche, modulo di contatto, destinatari, conservazione, diritti e servizi esterni.
- **Cookie Policy:** è presente `cookie-policy.html`, che descrive le preferenze e il caricamento subordinato delle mappe Google.
- **Footer:** sono presenti i collegamenti a Privacy Policy e Cookie Policy; lo script rende disponibile anche il collegamento “Preferenze cookie”.
- **Modulo Contatti:** il modulo richiede la presa visione dell’informativa tramite checkbox obbligatoria. La richiesta viene preparata nel programma email dell’utente tramite `mailto:`; il sito non la invia a un proprio endpoint né la conserva direttamente.
- **Contenuti esterni:** Google Maps è inizialmente bloccato. Il caricamento avviene solo dopo una scelta esplicita dell’utente; restano disponibili indirizzi e collegamenti alle indicazioni stradali.
- **Risorse di terze parti:** lo stile usa caratteri di sistema e le immagini del sito sono locali; non risultano richieste a Google Fonts o a immagini Unsplash nei file verificati.

## File principali esaminati

`index.html`, `studio.html`, `contatti.html`, `sedi.html`, `privacy-policy.html`, `cookie-policy.html`, `assets/site.js`, `assets/style.css`.

## Note e verifiche ancora necessarie

Le informative presenti nel repository riportano espressamente indicazioni da verificare prima della loro approvazione definitiva. In particolare, lo Studio deve confermare i dati identificativi completi del titolare, i recapiti e gli eventuali ruoli privacy, i fornitori effettivamente utilizzati, i tempi di conservazione e l'eventuale presenza di cookie o strumenti aggiuntivi introdotti dall'hosting o da servizi terzi.

Questa relazione descrive la configurazione tecnica esaminata e non costituisce una certificazione di conformità normativa. Le informative devono essere validate dal titolare e, ove opportuno, dal consulente privacy prima di essere considerate definitive.

## Pubblicazione

Le modifiche alla Home sono state registrate nel branch `main`. La relativa build Vercel di produzione risulta **READY**. Il deployment è associato al commit `39e0c3640d40d5bdd4f1dc8acf1770c96840e4c6` e agli alias di produzione del progetto `notaiomontemiglio2026`.
