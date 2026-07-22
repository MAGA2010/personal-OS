#!/usr/bin/env python3
"""
Fetch recent study-abroad news articles and replace old ones in news.json.
Run: python3 data-pipeline/fetch_news.py

Sources: EIC Education (启德教育), QS China, Study Abroad policy updates
"""
import json, time, urllib.request, urllib.parse, sys, os, re
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

UA = "PathOS/1.0 (coco; news-pipeline)"

data_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
news_path = os.path.join(data_dir, "frontend", "src", "data", "news.json")

def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  FAIL {url[:60]}: {e}", file=sys.stderr)
        return None

# ── Sources ──────────────────────────────────────
feeds = [
    # QS China - study abroad news
    {"url": "https://www.qschina.cn/feed", "source": "QS China", "category_map": {"admission": "admissions", "visa": "visa", "ranking": "ranking", "life": "life", "career": "career"}},
    # ICEF Monitor - international education (English)
    {"url": "https://feed.icef.com/", "source": "ICEF Monitor", "category_map": {"admission": "admissions", "visa": "visa", "market": "policy"}},
]

def guess_category(title, summary):
    t = (title + " " + (summary or "")).lower()
    for kw, cat in [("visa", "visa"), ("h1b", "visa"), ("opt", "visa"), ("student visa", "visa"),
                     ("ranking", "ranking"), ("qs", "ranking"), ("top university", "ranking"),
                     ("admission", "admissions"), ("application", "admissions"), ("apply", "admissions"),
                     ("career", "career"), ("job", "career"), ("employment", "career"),
                     ("policy", "policy"), ("regulation", "policy"),
                     ("life", "life"), ("cost", "life"), ("living", "life"),
                     ("scholarship", "admissions"), ("financial aid", "admissions")]:
        if kw in t:
            return cat
    return "admissions"

def generate_id(source, url):
    import hashlib
    h = hashlib.md5(url.encode()).hexdigest()[:12]
    return f"{source.lower().replace(' ', '-')}-{h}"

def parse_rss(xml_text, feed):
    articles = []
    try:
        root = ET.fromstring(xml_text)
        ns = {"atom": "http://www.w3.org/2005/Atom",
              "dc": "http://purl.org/dc/elements/1.1/"}
        for item in root.iter("item"):
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            desc = item.findtext("description", "")
            pub_date = item.findtext("pubDate", "")
            # Try to parse various date formats
            dt = None
            for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"]:
                try:
                    dt = datetime.strptime(pub_date.strip(), fmt)
                    break
                except: pass
            if not dt:
                dt = datetime.now(timezone.utc)

            summary = re.sub(r"<[^>]+>", "", desc or "")[:500]
            category = guess_category(title, summary)
            articles.append({
                "id": generate_id(feed["source"], link),
                "title": title.strip()[:200],
                "titleEn": title.strip()[:200],
                "summary": summary[:400],
                "source": feed["source"],
                "url": link,
                "publishedAt": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "category": category,
            })
        # Also parse Atom
        for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
            title = entry.findtext("{http://www.w3.org/2005/Atom}title", "")
            link_el = entry.find("{http://www.w3.org/2005/Atom}link")
            link = link_el.get("href", "") if link_el is not None else ""
            desc = entry.findtext("{http://www.w3.org/2005/Atom}summary", "")
            pub_date = entry.findtext("{http://www.w3.org/2005/Atom}published", "")
            dt = None
            for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%a, %d %b %Y %H:%M:%S %z"]:
                try:
                    dt = datetime.strptime(pub_date.strip(), fmt)
                    break
                except: pass
            if not dt:
                dt = datetime.now(timezone.utc)
            summary = re.sub(r"<[^>]+>", "", desc or "")[:500]
            category = guess_category(title, summary)
            articles.append({
                "id": generate_id(feed["source"], link),
                "title": title.strip()[:200],
                "titleEn": title.strip()[:200],
                "summary": summary[:400],
                "source": feed["source"],
                "url": link,
                "publishedAt": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "category": category,
            })
    except Exception as e:
        print(f"  Parse error: {e}", file=sys.stderr)
    return articles

# ── Main ────────────────────────────────────────
all_new = []
for feed in feeds:
    print(f"Fetching {feed['url']}...")
    xml = fetch(feed["url"])
    if xml:
        articles = parse_rss(xml, feed)
        print(f"  Got {len(articles)} articles")
        all_new.extend(articles)
    time.sleep(2)

if not all_new:
    print("No articles fetched. Saving empty sample.")
    all_new = []

# Load existing news
existing = json.load(open(news_path))
existing_ids = {a["id"] for a in existing["articles"]}

# Keep existing articles from 2025+ and add new ones
keep = [a for a in existing["articles"] if a["publishedAt"] >= "2025-01-01"]
added = 0
for a in all_new:
    if a["id"] not in existing_ids:
        keep.append(a)
        existing_ids.add(a["id"])
        added += 1

# Sort by date, newest first
keep.sort(key=lambda x: x["publishedAt"], reverse=True)

existing["articles"] = keep[:150]  # Cap at 150

json.dump(existing, open(news_path, "w"), ensure_ascii=False, indent=2)
print(f"\nDone. Kept {len([a for a in keep if a['publishedAt'] >= '2025-01-01'])} recent + {added} new = {len(keep)} articles")
