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
    cert_url = "https://crt.sh/?d=4267304698"
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
        if (safe_url(absolute) and parsed.path.startswith(("/it/news/", "/it/comunicati-stampa/"))
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
    if not collected:
        raise SystemExit("Nessuna notizia istituzionale completa raggiungibile: nessuna bozza generata.")
    return collected[:12]

def main():
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("Secret OPENAI_API_KEY mancante.")
    today = dt.date.today()
    sources = collect_sources()
    prompt = f"""
Sei un redattore giuridico-divulgativo per lo Studio Notarile Daria Montemiglio (Roma e Albano Laziale).
Data: {today.isoformat()}.
Prepara una BOZZA, non un parere e non una consulenza. Usa solo i fatti presenti nelle fonti riportate qui sotto. Non inventare norme, date, sentenze, importi, aliquote, procedure o obblighi. Distingui chiaramente fatti della fonte, spiegazioni generali e aspetti da verificare.
Scegli un tema utile a cittadini, famiglie o imprese nelle categorie: Casa e compravendite; Successioni e donazioni; Famiglia e patrimonio; Imprese e società; Novità normative e fiscali.
Scrivi in italiano chiaro e sobrio, circa 600-850 parole, con titolo, introduzione, 3-4 sezioni H2, conclusione pratica e FAQ solo se le fonti consentono risposte affidabili. Includi meta description max 155 caratteri e slug. Inserisci un riquadro iniziale che dica: "BOZZA DA VERIFICARE: contenuto divulgativo non pubblicato, da sottoporre a revisione notarile; non costituisce consulenza sul caso concreto."
Non presentare le notizie territoriali come norme nazionali. Non usare una notizia locale come prova di una regola generale. Se le fonti non sostengono un articolo utile, restituisci {"skip":true,"reason":"..."}.
Rispondi esclusivamente con JSON valido: title, slug, category, meta_description, article_markdown, sources (array di oggetti name,url), oppure skip e reason.
FONTI ISTITUZIONALI:
{json.dumps(sources, ensure_ascii=False)}
"""
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        "messages": [
            {"role": "system", "content": "Sei rigoroso e prudente. Non inventare riferimenti giuridici. Cita solo le fonti fornite."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(request, timeout=150) as response:
        result = json.loads(response.read().decode("utf-8"))
    article = json.loads(result["choices"][0]["message"]["content"])
    if article.get("skip"):
        raise SystemExit("Nessuna bozza adatta: " + str(article.get("reason", "fonti insufficienti")))
    required = ("title", "slug", "category", "meta_description", "article_markdown")
    if any(not isinstance(article.get(key), str) or not article[key].strip() for key in required):
        raise SystemExit("Risposta del modello incompleta: bozza non salvata.")
    slug = re.sub(r"[^a-z0-9-]+", "-", article["slug"].lower()).strip("-")[:80]
    if not slug:
        raise SystemExit("Slug non valido.")
    source_rows = []
    for item in article.get("sources", []):
        url = item.get("url", "")
        if safe_url(url):
            source_rows.append(f"- [{item.get('name', 'Consiglio Nazionale del Notariato')}]({url})")
    if not source_rows:
        raise SystemExit("La bozza non contiene fonti istituzionali verificabili.")
    target = Path("approfondimenti/bozze")
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{today.isoformat()}-{slug}.md"
    # Non sovrascrivere mai una bozza già esistente.
    if path.exists():
        path = target / f"{today.isoformat()}-{slug}-{dt.datetime.now().strftime('%H%M%S')}.md"
    title = article["title"].replace('"', "'").replace("\n", " ")
    category = article["category"].replace('"', "'").replace("\n", " ")
    description = article["meta_description"].replace('"', "'").replace("\n", " ")
    content = f"""---
status: bozza-da-verificare
date: {today.isoformat()}
title: "{title}"
slug: {slug}
category: "{category}"
meta_description: "{description}"
---

# {article['title']}

> **BOZZA NON PUBBLICATA.** Da verificare integralmente dal Notaio prima di qualsiasi pubblicazione. Non costituisce consulenza sul caso concreto.

{article['article_markdown']}

## Fonti istituzionali

{chr(10).join(source_rows)}
"""
    path.write_text(content, encoding="utf-8")
    print(f"Bozza generata: {path}")

if __name__ == "__main__":
    main()
