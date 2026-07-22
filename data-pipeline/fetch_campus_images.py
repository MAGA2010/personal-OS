#!/usr/bin/env python3
"""
Fetch campus images from Wikipedia for schools that don't have them.
Run: python3 data-pipeline/fetch_campus_images.py

Uses 2.5s delay between requests to respect rate limits.
"""
import json, time, urllib.request, urllib.parse, sys, os

WIKI_API = "https://en.wikipedia.org/w/api.php"
UA = "PathOS/1.0 (coco; campus-images-pipeline)"

def wiki(params):
    p = dict(params)
    p["format"] = "json"
    url = WIKI_API + "?" + urllib.parse.urlencode(p)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except Exception as e:
            if attempt < 2:
                time.sleep(5)
                continue
            print(f"  FAIL: {e}", file=sys.stderr)
            return None

data_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
uni_path = os.path.join(data_dir, "frontend", "src", "data", "universities.json")
u = json.load(open(uni_path))

missing = [uu for uu in u["universities"] if len(uu.get("campusImages", [])) == 0]
print(f"Missing campusImages: {len(missing)} schools\n")

success = 0
for i, school in enumerate(missing):
    name = school["name"]
    # Wikipedia title mapping for known edge cases
    title = {
        "Purdue University\u2014Main Campus": "Purdue University",
        "The Ohio State University": "Ohio State University",
        "Indiana University Bloomington": "Indiana University Bloomington",
        "Loyola University Chicago": "Loyola University Chicago",
        "Olin College of Engineering": "Olin College",
        "Texas A&M University": "Texas A&M University",
    }.get(name, name)

    print(f"[{i+1}/{len(missing)}] {name} -> {title}")
    resp = wiki({"action": "query", "titles": title, "prop": "pageimages", "pithumbsize": 800})
    time.sleep(2.5)

    if not resp:
        print(f"  No response\n")
        continue

    img_url = None
    for pid, pdata in resp.get("query", {}).get("pages", {}).items():
        if pid != "-1" and "thumbnail" in pdata:
            img_url = pdata["thumbnail"]["source"]
            break

    if not img_url:
        # Try search fallback
        resp2 = wiki({"action": "query", "list": "search", "srsearch": name, "srlimit": 1})
        time.sleep(2.5)
        if resp2 and resp2.get("query", {}).get("search"):
            best = resp2["query"]["search"][0]
            resp3 = wiki({"action": "query", "titles": best["title"], "prop": "pageimages", "pithumbsize": 800})
            time.sleep(2.5)
            if resp3:
                for pid, pdata in resp3.get("query", {}).get("pages", {}).items():
                    if pid != "-1" and "thumbnail" in pdata:
                        img_url = pdata["thumbnail"]["source"]
                        break

    if img_url:
        label = "Campus view" if any(k in img_url for k in ["Campus", "aerial", "Quad", "view"]) else "Campus"
        school["campusImages"] = [{"url": img_url, "label": label, "source": "Wikipedia"}]
        success += 1
        print(f"  + {img_url[:80]}")
    else:
        print(f"  No image found")

    print()
    sys.stdout.flush()

json.dump(u, open(uni_path, "w"), ensure_ascii=False, indent=2)
print(f"\nDone. {success}/{len(missing)} schools updated")
