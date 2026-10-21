import feedparser
import yaml
import json
from pathlib import Path
from html import escape
from datetime import datetime, timezone

with open("feeds.yml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

items = []

for feed_config in config["feeds"]:
    name = feed_config["name"]
    url = feed_config["url"]

    feed = feedparser.parse(url)

    for entry in feed.entries:
        items.append({
            "source": name,
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
            "summary": entry.get("summary", "")
        })

# Maak map voor de website
site = Path("site")
site.mkdir(exist_ok=True)

# JSON-versie
with open(site / "latest.json", "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

# HTML-versie
html = """<!doctype html>
<html lang="nl">
<head>
    <meta charset="utf-8">
    <title>Politieke monitor</title>
</head>
<body>
    <h1>Politieke monitor</h1>
"""

for item in items:
    html += f"""
    <article>
        <h2>{escape(item["title"])}</h2>
        <p><strong>Bron:</strong> {escape(item["source"])}</p>
        <p><strong>Gepubliceerd:</strong> {escape(item["published"])}</p>
        <div>{item["summary"]}</div>
        <p><a href="{escape(item["link"])}">Originele publicatie</a></p>
        <hr>
    </article>
    """

html += f"""
    <p>Laatste update: {datetime.now(timezone.utc).isoformat()}</p>
</body>
</html>
"""

with open(site / "index.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"{len(items)} berichten opgehaald.")
