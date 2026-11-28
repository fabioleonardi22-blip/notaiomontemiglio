#!/usr/bin/env python3
"""Prepara una bozza editoriale usando contenuti istituzionali verificabili. Non pubblica."""
import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASES = [
    ("Consiglio Nazionale del Notariato – News", "https://www.notariato.it/it/news/"),
    ("Consiglio Nazionale del Notariato – Archivio news", "https://www.notariato.it/it/archivio-news/"),
    ("Consiglio Nazionale del Notariato – Comunicati stampa", "https://www.notariato.it/it/comunicati-stampa/"),
]
ALLOWED_HOSTS = {"www.notariato.it", "notariato.it"}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; StudioMontemiglioEditorialBot/1.1; +https://notaiomontemiglio.vercel.app)"}

def safe_url(url):
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS

def sectigo_intermediate():
    """Scarica e verifica l'intermedio Sectigo OV R36 tramite fingerprint fissata."""
    cert_url = "http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR36.crt"
    expected = "6542D176BED50F193C0CE297AE44ECD8A0A86BEC2EDE682769344059B4E78530"
    curl = shutil.which("curl")
    openssl = shutil.which("openssl")
    if not curl or not openssl:
        raise RuntimeError("curl/openssl non disponibili per la verifica della CA intermedia.")
    import tempfile
    with tempfile.TemporaryDirectory() as temp:
        raw_path = Path(temp) / "sectigo.crt"
        pem_path = Path(temp) / "sectigo.pem"
        download = subprocess.run(
            [curl, "--fail", "--location", "--silent", "--show-error",
             "--max-time", "30", cert_url, "--output", str(raw_path)],
            capture_output=True, text=True, timeout=35
        )
        if download.returncode:
            raise RuntimeError("Impossibile scaricare il certificato intermedio Sectigo da crt.sh: " + download.stderr.strip())
        converted = subprocess.run(
            [openssl, "x509", "-inform", "DER", "-in", str(raw_path), "-out", str(pem_path)],
            capture_output=True, text=True
        )
        if converted.returncode:
            # crt.sh può restituire PEM; in tal caso lo si accetta solo dopo fingerprint.
            pem_path.write_bytes(raw_path.read_bytes())
        check = subprocess.run(
            [openssl, "x509", "-in", str(pem_path), "-noout", "-fingerprint", "-sha256"],
            capture_output=True, text=True
        )
        fingerprint = check.stdout.strip().split("=", 1)[-1].replace(":", "").upper()
        if check.returncode or fingerprint != expected:
            raise RuntimeError("Fingerprint della CA Sectigo non corrispondente: certificato rifiutato.")
        return pem_path.read_bytes()

def fetch(url, limit=1_800_000):
    if not safe_url(url):
        raise ValueError(f"URL non consentito: {url}")
    request = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            return response.read(limit).decode("utf-8", "replace")
    except Exception as first_error:
        # Il server Notariato non presenta correttamente la catena intermedia.
        # Si usa esclusivamente l'intermedio OV R36 ufficiale, verificato via SHA-256.
        curl = shutil.which("curl")
        if not curl:
            raise RuntimeError(f"Download fallito: {first_error}") from first_error
        import tempfile
        cert_pem = sectigo_intermediate()
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".pem") as cert_file:
            cert_file.write(cert_pem)
            cert_file.flush()
            result = subprocess.run(
                [curl, "--fail", "--location", "--silent", "--show-error",
                 "--max-time", "45", "--max-filesize", str(limit),
                 "--user-agent", HEADERS["User-Agent"], "--cacert", cert_file.name, url],
                capture_output=True, text=True, timeout=55
            )
        if result.returncode:
            raise RuntimeError(
                f"Download HTTPS non verificato anche con CA Sectigo OV R36 fissata: "
                f"{first_error}; {result.stderr.strip()}"
            )
        return result.stdout[:limit]

def clean_html(raw):
    raw = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header).*?>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    return re.sub(r"\s+", " ", raw).strip()

def page_links(raw, base_url):
    links = []
    # Estrazione link essenziale senza dipendenze: i link vengono poi validati.
    for match in re.finditer(r"""(?is)<a\b[^>]*href\s*=\s*["']([^"']+)["'][^>]*>(.*?)</a>""", raw):
        href, label = match.groups()
        title = clean_html(label)
        absolute = urllib.parse.urljoin(base_url, html.unescape(href))
        parsed = urllib.parse.urlparse(absolute)
        if (safe_url(absolute) and "{" not in absolute and "}" not in absolute
                and parsed.path.startswith(("/it/news/", "/it/archivio-news/", "/it/comunicati-stampa/"))
                and len(title) > 24 and not title.lower().startswith(("leggi", "scopri", "torna"))):
            links.append({"title": title[:240], "url": absolute})
    unique = {}
    for item in links:
        unique[item["url"]] = item
    return list(unique.values())

def collect_sources():
    collected = []
    failures = []
    seen = set()
    for name, url in BASES:
        try:
            listing = fetch(url)
            links = page_links(listing, url)
            # Se il markup cambia, il listing stesso resta una fonte verificabile,
            # ma non viene usato come unico fondamento per un articolo lungo.
            for item in links[:8]:
                if item["url"] in seen:
                    continue
                seen.add(item["url"])
                try:
                    detail = fetch(item["url"], limit=1_200_000)
                    text = clean_html(detail)
                    if len(text) >= 500:
                        collected.append({
                            "source": name,
                            "title": item["title"],
                            "url": item["url"],
                            "extract": text[:10000]
                        })
                except Exception as exc:
                    failures.append(f"{item['url']}: {exc}")
        except Exception as exc:
            failures.append(f"{url}: {exc}")
        time.sleep(1)
    if failures:
        for failure in failures:
            print(f"Fonte non disponibile: {failure}")
    # Non basta la sola pagina indice: almeno un contenuto editoriale completo.
    if len(collected) < 2:
        raise SystemExit(
            f"Solo {len(collected)} contenuto/i istituzionale/i completo/i recuperato/i: "
            "ne servono almeno due per verificare il tema. Nessuna bozza generata."
        )
    print(f"Contenuti istituzionali completi raccolti: {len(collected)}")
    return collected[:12]

def normalize_quote(value):
    value = html.unescape(value).lower()
    value = re.sub(r"[^a-zàèéìòù0-9 ]+", " ", value)
    return re.sub(r"\\s+", " ", value).strip()
def markdown_to_html(markdown):
    """Convertitore minimale e sicuro per il Markdown prodotto dal modello."""
    out = []
    in_list = False
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            if in_list:
                out.append("</ul>")
                in_list = False
            continue
        if line.startswith("# "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append("<h2>" + html.escape(line[2:]) + "</h2>")
        elif line.startswith("## "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append("<h2>" + html.escape(line[3:]) + "</h2>")
        elif line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append("<li>" + html.escape(line[2:]) + "</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append("<p>" + html.escape(line) + "</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)

def main():
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("Secret GEMINI_API_KEY mancante.")
    today = dt.date.today()
    sources = collect_sources()
    prompt = f"""
Sei un redattore giuridico-divulgativo per lo Studio Notarile Daria Montemiglio (Roma e Albano Laziale).
Data: {today.isoformat()}.
Prepara un articolo divulgativo per la pubblicazione automatica, non un parere e non una consulenza. Usa esclusivamente informazioni effettivamente documentate nelle fonti riportate qui sotto. Non inventare norme, date, sentenze, importi, aliquote, procedure o obblighi.
Scegli un tema utile a cittadini, famiglie o imprese nelle categorie: Casa e compravendite; Successioni e donazioni; Famiglia e patrimonio; Imprese e società; Novità normative e fiscali.
Prima di scrivere, confronta le fonti: devono esserci almeno DUE articoli istituzionali completi che trattino direttamente lo stesso tema o aspetti strettamente collegati. Se le fonti sono solo annunci di eventi, iniziative locali, titoli o comunicati non pertinenti tra loro, restituisci skip. Non riempire i vuoti con nozioni giuridiche generiche.
Scrivi in italiano chiaro e sobrio, circa 450-650 parole, con titolo, introduzione, 2-3 sezioni H2 e conclusione pratica. Ogni affermazione giuridica o fiscale deve essere direttamente supportata dagli estratti forniti; se non è supportata, omettila o segnala che necessita di verifica notarile. Non introdurre norme, sentenze, aliquote, scadenze, procedure o obblighi non esplicitamente documentati dalle fonti. Le fonti di un articolo locale non dimostrano una regola nazionale.
Includi meta description max 155 caratteri e slug. Inserisci una breve nota iniziale: "Contenuto divulgativo basato sulle fonti istituzionali citate. Non sostituisce la valutazione del caso concreto."
Rispondi skip se non puoi sostenere un approfondimento utile con almeno due fonti dirette e coerenti.
Per ogni affermazione fattuale o giuridica sostanziale, inserisci una voce evidence con claim, source_url e exact_quote: una citazione letterale continua di almeno 12 parole copiata dall’estratto di quella fonte. Le fonti devono sostenere davvero le affermazioni; non basta aggiungere link generici. Se le fonti non documentano un tema in modo sufficiente, restituisci skip.\nRispondi esclusivamente con JSON valido: title, slug, category, meta_description, article_markdown, sources (array di oggetti name,url), evidence (array di oggetti claim, source_url, exact_quote), oppure skip e reason.
FONTI ISTITUZIONALI:
{json.dumps(sources, ensure_ascii=False)}
"""
    model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + urllib.parse.quote(model, safe="")
        + ":generateContent"
    )
    payload = {
        "systemInstruction": {
            "parts": [{"text": "Sei rigoroso e prudente. Non inventare riferimenti giuridici. Cita solo le fonti fornite."}]
        },
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
            "maxOutputTokens": 8192
        }
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"], "Content-Type": "application/json"},
        method="POST"
    )
    result = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                result = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            try:
                api_error = json.loads(detail).get("error", {})
                code = api_error.get("status", "")
                message = api_error.get("message", detail[:1200])
            except Exception:
                code, message = "", detail[:1200]
            # Retry solo per limiti temporanei e indisponibilità, mai per quota esaurita
            # o errori di configurazione/autenticazione.
            retryable = exc.code in (429, 500, 502, 503, 504)
            if retryable and attempt < 2 and "quota" not in message.lower():
                wait = 20 * (attempt + 1)
                print(f"Gemini temporaneamente non disponibile (tentativo {attempt + 1}/3): attesa {wait}s.")
                time.sleep(wait)
                continue
            raise SystemExit(f"Gemini API HTTP {exc.code} ({code or 'errore'}): {message}")
        except (TimeoutError, urllib.error.URLError) as exc:
            if attempt < 2:
                wait = 20 * (attempt + 1)
                print(f"Connessione Gemini temporaneamente non disponibile: attesa {wait}s.")
                time.sleep(wait)
                continue
            raise SystemExit(f"Connessione Gemini non riuscita: {exc}")
    if result is None:
        raise SystemExit("Gemini non ha restituito una risposta.")
    try:
        generated_text = result["candidates"][0]["content"]["parts"][0]["text"]
        article = json.loads(generated_text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        feedback = result.get("promptFeedback", {})
        raise SystemExit(f"Risposta Gemini non valida o bloccata; bozza non salvata. Dettaglio: {feedback or str(exc)}")

    if article.get("skip"):
        raise SystemExit("Nessuna bozza adatta: " + str(article.get("reason", "fonti insufficienti")))
    required = ("title", "slug", "category", "meta_description", "article_markdown")
    if any(not isinstance(article.get(key), str) or not article[key].strip() for key in required):
        raise SystemExit("Risposta del modello incompleta: bozza non salvata.")
    slug = re.sub(r"[^a-z0-9-]+", "-", article["slug"].lower()).strip("-")[:80]
    if not slug:
        raise SystemExit("Slug non valido.")
    source_rows = []
    allowed_sources = {item["url"]: item for item in sources}
    selected_urls = set()
    for item in article.get("sources", []):
        url = item.get("url", "")
        if safe_url(url) and url in allowed_sources:
            selected_urls.add(url)
            source_rows.append(f"- [{allowed_sources[url]['title']}]({url})")
    if len(selected_urls) < 2:
        raise SystemExit("Bozza scartata: non cita almeno due articoli istituzionali effettivamente letti.")
    evidence = article.get("evidence", [])
    source_text = {item["url"]: item["extract"] for item in sources}
    if not isinstance(evidence, list) or len(evidence) < 3:
        raise SystemExit("Pubblicazione annullata: servono almeno tre prove testuali.")
    evidence_urls = set()
    for entry in evidence:
        claim = entry.get("claim", "")
        url = entry.get("source_url", "")
        quote = entry.get("exact_quote", "").strip()
        if (not claim or url not in selected_urls or len(quote.split()) < 12
                or normalize_quote(quote) not in normalize_quote(source_text.get(url, ""))):
            raise SystemExit("Pubblicazione annullata: citazione non letterale, non verificata o non collegata a una fonte selezionata.")
        evidence_urls.add(url)
    if len(evidence_urls) < 2:
        raise SystemExit("Pubblicazione annullata: le prove devono provenire da almeno due fonti pertinenti.")
    target = Path("approfondimenti/articoli")
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{slug}.html"
    if path.exists():
        raise SystemExit(f"Articolo già esistente: {path}; pubblicazione duplicata bloccata.")
    title_html = html.escape(article["title"])
    category_html = html.escape(article["category"])
    description_html = html.escape(article["meta_description"])
    body_html = markdown_to_html(article["article_markdown"])
    sources_html = "\n".join(
        f'<li><a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(allowed_sources[url]["title"])}</a></li>'
        for url in sorted(selected_urls)
    )
    article_html = f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{description_html}"><meta name="robots" content="index,follow">
<title>{title_html} | Studio Daria Montemiglio</title>
<link rel="canonical" href="https://notaiomontemiglio.vercel.app/approfondimenti/articoli/{slug}.html">
<link rel="stylesheet" href="../../assets/style.css"></head><body>
<header class="topbar"><div class="wrap nav"><a class="brand" href="../../index.html"><span class="monogram">DM</span><span class="brandname">DARIA MONTEMIGLIO<small>NOTAIO</small></span></a><nav><a href="../../index.html">Home</a><a href="../../studio.html">Lo Studio</a><a href="../../attivita.html">Attività</a><a href="../../approfondimenti.html">Approfondimenti</a><a href="../../sedi.html">Sedi</a><a href="../../contatti.html">Contatti</a></nav></div></header>
<main class="section"><article class="wrap" style="max-width:850px"><p class="eyebrow">Approfondimenti · {category_html}</p><h1>{title_html}</h1><p class="insights-intro-note">Contenuto divulgativo basato sulle fonti istituzionali indicate. Aggiornato al {today.isoformat()}. Non sostituisce la valutazione del caso concreto.</p><div class="article-body">{body_html}</div><section class="insights-sources"><h2>Fonti</h2><ul>{sources_html}</ul></section><p><a href="../../approfondimenti.html">← Torna agli Approfondimenti</a></p></article></main>
<footer><div class="wrap foot"><span>© {today.year} Studio Notarile Daria Montemiglio</span><span>Roma · Albano Laziale</span><a href="../../privacy-policy.html">Privacy Policy</a><a href="../../cookie-policy.html">Cookie Policy</a></div></footer>
<script src="../../assets/site.js"></script></body></html>"""
    path.write_text(article_html, encoding="utf-8")

    manifest_path = Path("approfondimenti/articoli.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    except json.JSONDecodeError:
        raise SystemExit("Indice articoli non valido: pubblicazione annullata.")
    manifest = [item for item in manifest if item.get("slug") != slug]
    manifest.insert(0, {
        "title": article["title"],
        "slug": slug,
        "category": article["category"],
        "description": article["meta_description"],
        "date": today.isoformat(),
        "url": f"approfondimenti/articoli/{slug}.html",
        "sources": sorted(selected_urls)
    })
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"ARTICOLO PUBBLICATO NEL REPOSITORY: {path}")
    print(f"Indice aggiornato: {manifest_path}")


if __name__ == "__main__":
    main()
