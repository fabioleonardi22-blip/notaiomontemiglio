#!/usr/bin/env python3
"""Genera una bozza editoriale da fonti istituzionali. Non pubblica direttamente."""
import datetime as dt
import html
import json
import os
import re
import urllib.request
from pathlib import Path

SOURCES = [
    ("Consiglio Nazionale del Notariato – News", "https://www.notariato.it/it/news/"),
    ("Consiglio Nazionale del Notariato – Comunicati stampa", "https://www.notariato.it/it/comunicati-stampa/"),
    ("Agenzia delle Entrate", "https://www.agenziaentrate.gov.it/portale/web/guest/home"),
]
def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent":"StudioMontemiglioEditorialBot/1.0 (informazione; contatto: dmontemiglio@notariato.it)"})
    with urllib.request.urlopen(req, timeout=25) as r:
        raw = r.read(1_500_000)
    text = raw.decode("utf-8", "replace")
    text = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text)[:12000]

def main():
    today = dt.date.today()
    gathered = []
    for name, url in SOURCES:
        try:
            gathered.append({"source": name, "url": url, "extract": fetch(url)})
        except Exception as exc:
            print(f"Fonte non disponibile: {url}: {exc}")
    if not gathered:
        raise SystemExit("Nessuna fonte istituzionale raggiungibile: bozza non generata.")
    prompt = f"""
Sei un redattore giuridico-divulgativo che prepara una BOZZA per lo Studio Notarile Daria Montemiglio (Roma e Albano Laziale).
Data di redazione: {today.isoformat()}.
Usa esclusivamente le informazioni supportate dagli estratti delle fonti istituzionali qui sotto. Non inventare norme, date, soglie, aliquote, procedure, sentenze o obblighi. Se gli estratti non bastano per un articolo concreto, crea un approfondimento prudente che spieghi il tema e segnali con precisione cosa deve essere verificato dal Notaio; non colmare lacune con supposizioni.
Scegli un argomento utile per cittadini, famiglie o imprese tra casa/compravendite, successioni/donazioni, famiglia/patrimonio, impresa/società, novità normative e fiscali.
Scrivi in italiano, tono sobrio e chiaro, 700-1000 parole, con titolo SEO naturale, meta description (max 155 caratteri), slug, categoria, introduzione, 3-5 sezioni H2, conclusione pratica, 3 FAQ solo se rispondibili dagli estratti e fonti con URL e data se disponibile.
Non dare consulenza personalizzata. Inserisci in evidenza: "Contenuto divulgativo da sottoporre a verifica notarile prima della pubblicazione; non costituisce consulenza sul caso concreto."
Rispondi SOLO con JSON valido avente chiavi: title, slug, category, meta_description, article_markdown, sources (array di oggetti name,url).
FONTI:
{json.dumps(gathered, ensure_ascii=False)}
"""
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        "messages": [
            {"role":"system","content":"Produci bozze giuridiche rigorose, prudenti e tracciabili. Non inventare mai riferimenti normativi."},
            {"role":"user","content":prompt}
        ],
        "response_format":{"type":"json_object"},
        "temperature":0.3
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization":"Bearer "+os.environ["OPENAI_API_KEY"],"Content-Type":"application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        result=json.loads(response.read().decode())
    article=json.loads(result["choices"][0]["message"]["content"])
    slug=re.sub(r"[^a-z0-9-]+","-",article["slug"].lower()).strip("-")[:80]
    if not slug:
        raise SystemExit("Slug non valido")
    target=Path("approfondimenti/bozze")
    target.mkdir(parents=True, exist_ok=True)
    path=target/f"{today.isoformat()}-{slug}.md"
    source_lines="\\n".join(f"- [{s['name']}]({s['url']})" for s in article.get("sources",[]))
    content=f"""---
status: bozza-da-verificare
date: {today.isoformat()}
title: "{article['title'].replace('"', chr(39))}"
slug: {slug}
category: "{article['category'].replace('"', chr(39))}"
meta_description: "{article['meta_description'].replace('"', chr(39))}"
---

# {article['title']}

> **BOZZA NON PUBBLICATA.** Da verificare integralmente dal Notaio prima di qualsiasi pubblicazione. Non costituisce consulenza sul caso concreto.

{article['article_markdown']}

## Fonti istituzionali

{source_lines}
"""
    path.write_text(content, encoding="utf-8")
    print(f"Bozza generata: {path}")

if __name__ == "__main__":
    main()
