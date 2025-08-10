import re, hashlib
from datetime import datetime, timezone
from dateutil import parser as du

def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip()).lower()

def hash_id(url, title):
    h = hashlib.sha1(((url or "") + "|" + (title or "")).encode("utf-8")).hexdigest()
    return h[:16]

def parse_date(dt_str):
    try:
        d = du.parse(dt_str)
        if not d.tzinfo:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        return None

def recency_score(published):
    if not published:
        return 0.0
    now = datetime.now(timezone.utc)
    age_hours = max(1, (now - published).total_seconds() / 3600.0)
    return 1.0 / age_hours

def keyword_score(title, summary, keywords):
    text = f"{title or ''} {summary or ''}".lower()
    return sum(1.0 for kw in keywords if kw.lower() in text)

def rank_item(item, keywords):
    r = recency_score(item.get("published_dt"))
    k = keyword_score(item.get("title"), item.get("summary"), keywords)
    return 0.7 * r + 0.3 * (k / 5.0)

def should_dedupe(seen, url, title):
    key = (norm(url), norm(title))
    if key in seen:
        return True
    seen.add(key)
    return False
