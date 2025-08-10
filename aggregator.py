import json, feedparser, yaml
from datetime import datetime, timezone
from utils import parse_date, rank_item, should_dedupe, hash_id

CONFIG = "feeds.yaml"
OUT_JSON = "data/feed.json"
OUT_HTML = "templates/index.html"

def load_config():
    with open(CONFIG, "r") as f:
        return yaml.safe_load(f)

def fetch_feed(url):
    return feedparser.parse(url)

def collect(config):
    items_by_cat = {}
    for cat, urls in config["categories"].items():
        items = []
        seen = set()
        for url in urls:
            try:
                feed = fetch_feed(url)
                for e in feed.entries:
                    link = getattr(e, "link", None)
                    title = getattr(e, "title", None)
                    if should_dedupe(seen, link, title):
                        continue
                    published = getattr(e, "published", None) or getattr(e, "updated", None)
                    pd = parse_date(published)
                    summary = getattr(e, "summary", None)
                    itm = {
                        "id": hash_id(link, title),
                        "title": title,
                        "url": link,
                        "source": getattr(feed.feed, "title", url),
                        "published": published,
                        "published_dt": pd,
                        "summary": summary
                    }
                    items.append(itm)
            except Exception as ex:
                print(f"[warn] {cat} :: {url} :: {ex}")
        kws = config.get("keywords", {}).get(cat, [])
        for itm in items:
            itm["score"] = float(rank_item(itm, kws))
        items.sort(key=lambda x: x["score"], reverse=True)
        items_by_cat[cat] = items[: config.get("max_items_per_category", 25)]
    return items_by_cat

def export_json(items_by_cat):
    safe = {}
    for cat, items in items_by_cat.items():
        safe[cat] = [
            {
                k: (v.isoformat() if k == "published_dt" and v else v)
                for k, v in itm.items() if k != "score"
            }
            for itm in items
        ]
    with open(OUT_JSON, "w") as f:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(), "categories": safe}, f, indent=2)
    print(f"Wrote {OUT_JSON}")

def export_html(items_by_cat):
    from html import escape as esc
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = []
    parts.append("<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>")
    parts.append("<title>College News Hub</title>")
    parts.append("""<style>
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu; margin:24px; background:#0b0d10; color:#e8eaed}
    h1{font-size:28px; margin:0 0 8px}
    .sub{color:#9aa0a6; margin-bottom:24px}
    .grid{display:grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap:16px}
    .card{background:#15181c; border:1px solid #23262b; border-radius:16px; padding:16px}
    .card h2{margin:0 0 8px; font-size:18px}
    .item{padding:8px 0; border-top:1px solid #23262b}
    .item:first-child{border-top:none}
    .item a{color:#8ab4f8; text-decoration:none}
    .src{color:#9aa0a6; font-size:12px}
    </style>""")
    parts.append("</head><body>")
    parts.append(f"<h1>College News Hub</h1><div class='sub'>Updated {now}</div>")
    parts.append("<div class='grid'>")
    for cat, items in items_by_cat.items():
        parts.append("<div class='card'>")
        parts.append(f"<h2>{esc(cat)}</h2>")
        if not items:
            parts.append("<div class='item'><div class='src'>No items yet — run the aggregator.</div></div>")
        for itm in items[:10]:
            t = esc(itm.get('title') or '(no title)')
            u = esc(itm.get('url') or '#')
            s = esc(itm.get('source') or '')
            parts.append(f"<div class='item'><a href='{u}' target='_blank' rel='noopener'>{t}</a><div class='src'>{s}</div></div>")
        parts.append("</div>")
    parts.append("</div></body></html>")
    with open(OUT_HTML, "w") as f:
        f.write("\n".join(parts))
    print(f"Wrote {OUT_HTML}")

if __name__ == "__main__":
    cfg = load_config()
    data = collect(cfg)
    export_json(data)
    export_html(data)
    print("Done.")
