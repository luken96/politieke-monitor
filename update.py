import feedparser
import yaml
import json
import requests

from pathlib import Path
from html import escape
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin


# =========================
# RSS-FEEDS OPHALEN
# =========================

with open("feeds.yml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

items = []

for feed_config in config["feeds"]:
    name = feed_config["name"]
    url = feed_config["url"]

    print(f"RSS ophalen: {name}")

    feed = feedparser.parse(url)

    if feed.bozo:
        print(f"Waarschuwing bij {name}: {feed.bozo_exception}")

    for entry in feed.entries:
        items.append({
            "source": name,
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
            "summary": entry.get("summary", "")
        })


# =========================
# MINISTERRAAD VIA OPEN OVERHEID
# =========================
# Dit blok mag voorlopig blijven staan.
# Als Open Overheid geen resultaten meegeeft, crasht het script niet.

MINISTERRAAD_URL = (
    "https://open.overheid.nl/zoeken"
    "?aantal=50"
    "&beschikbaarSinds=Geen+periode"
    "&organisatie=ministerie%20van%20Algemene%20Zaken"
    "&pagina=1"
    "&sort=publicatiedatum"
    "&zoeken="
)

print("Open Overheid ophalen: Ministerraad")

try:
    response = requests.get(
        MINISTERRAAD_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "Chrome/150.0 Safari/537.36"
            )
        },
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    found_ministerraad = 0

    for link in soup.find_all("a", href=True):
        title = link.get_text(" ", strip=True)

        if not title:
            continue

        title_lower = title.lower()

        if (
            title_lower.startswith("agenda ministerraad")
            or title_lower.startswith("besluitenlijst ministerraad")
        ):
            full_url = urljoin(
                "https://open.overheid.nl",
                link["href"]
            )

            items.append({
                "source": "Ministerraad",
                "title": title,
                "link": full_url,
                "published": "",
                "summary": ""
            })

            found_ministerraad += 1

    print(f"{found_ministerraad} ministerraadstukken gevonden.")

except Exception as e:
    print(f"Ministerraad kon niet worden opgehaald: {e}")


# =========================
# DUBBELEN VERWIJDEREN
# =========================

unique_items = []
seen = set()

for item in items:
    key = (
        item["source"],
        item["title"],
        item["link"]
    )

    if key not in seen:
        seen.add(key)
        unique_items.append(item)

items = unique_items


# =========================
# CHRONOLOGISCH SORTEREN
# =========================

def parse_date(item):
    value = item.get("published", "")

    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)

    # Eerst standaard RSS-datums proberen
    try:
        dt = parsedate_to_datetime(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    except Exception:
        pass

    # Daarna ISO-datums proberen
    try:
        iso_value = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


items.sort(
    key=parse_date,
    reverse=True
)


# =========================
# WEBSITE MAKEN
# =========================

site = Path("site")
site.mkdir(exist_ok=True)


# =========================
# JSON-BESTAND
# =========================

with open(site / "latest.json", "w", encoding="utf-8") as f:
    json.dump(
        items,
        f,
        ensure_ascii=False,
        indent=2
    )


# =========================
# MARKDOWN-BESTAND VOOR CHATGPT
# =========================

markdown = "# Politieke monitor\n\n"
markdown += f"Laatste update: {datetime.now(timezone.utc).isoformat()}\n\n"

for item in items:
    markdown += f"## {item['title']}\n\n"
    markdown += f"**Bron:** {item['source']}\n\n"

    if item["published"]:
        markdown += f"**Gepubliceerd:** {item['published']}\n\n"

    if item["summary"]:
        # HTML-tags uit RSS-samenvattingen verwijderen
        clean_summary = BeautifulSoup(
            item["summary"],
            "html.parser"
        ).get_text(" ", strip=True)

        markdown += f"{clean_summary}\n\n"

    if item["link"]:
        markdown += f"**Originele publicatie:** {item['link']}\n\n"

    markdown += "---\n\n"


with open(site / "monitor.md", "w", encoding="utf-8") as f:
    f.write(markdown)


# =========================
# HTML-PAGINA
# =========================

html = """<!doctype html>
<html lang="nl">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Politieke monitor</title>
</head>

<body>

<h1>Politieke monitor</h1>
"""

for item in items:
    html += f"""
    <article>
        <h2>{escape(item["title"])}</h2>

        <p>
            <strong>Bron:</strong>
            {escape(item["source"])}
        </p>
"""

    if item["published"]:
        html += f"""
        <p>
            <strong>Gepubliceerd:</strong>
            {escape(item["published"])}
        </p>
"""

    if item["summary"]:
        html += f"""
        <div>
            {item["summary"]}
        </div>
"""

    html += f"""
        <p>
            <a href="{escape(item["link"])}">
                Originele publicatie
            </a>
        </p>

        <hr>
    </article>
    """


html += f"""
<p>
    Laatste update:
    {datetime.now(timezone.utc).isoformat()}
</p>

</body>
</html>
"""


with open(site / "index.html", "w", encoding="utf-8") as f:
    f.write(html)


print(f"Totaal: {len(items)} unieke berichten opgehaald.")
print("Bestanden aangemaakt:")
print("- site/index.html")
print("- site/latest.json")
print("- site/monitor.md")
