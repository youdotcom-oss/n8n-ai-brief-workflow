#!/usr/bin/env python3
"""Re-collect the article corpus with the template's exact search.

Writes corpus.json (titles and descriptions included) for local use. That file
is gitignored: article text belongs to its publishers, so the repo ships only
URLs (articles.json). Search results for past weeks can drift over time.

8 one-week windows x 3 topics x 2 pages (count=20) from You.com Search,
query '<topic> news' like the template. Dedupes on the template's urlKey
(URL without query/fragment) within each topic, which matches what Remove
Duplicates would do across consecutive runs. Reads YDC_API_KEY.
"""
import json
import os
import time
import urllib.request
from datetime import date, timedelta

KEY = os.environ["YDC_API_KEY"]
HERE = os.path.dirname(os.path.abspath(__file__))
TOPICS = ["AI model releases", "AI agent tooling", "AI regulation"]
END = date(2026, 10, 5)
WEEKS = [(END - timedelta(days=7 * (i + 1) - 1), END - timedelta(days=7 * i)) for i in range(8)][::-1]


def search(query, freshness, offset):
    body = {"query": query, "freshness": freshness, "count": 20, "offset": offset}
    req = urllib.request.Request("https://ydc-index.io/v1/search", method="POST", data=json.dumps(body).encode(),
                                 headers={"X-API-Key": KEY, "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            return json.load(urllib.request.urlopen(req, timeout=40))["results"].get("web", [])
        except Exception as e:  # transient network errors: back off and retry
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


corpus, calls, seen = [], 0, set()
for wi, (start, end) in enumerate(WEEKS):
    window = f"{start.isoformat()}to{end.isoformat()}"
    for topic in TOPICS:
        got = 0
        for offset in (0, 1):
            results = search(f"{topic} news", window, offset)
            calls += 1
            for rank, a in enumerate(results):
                url = a.get("url") or ""
                key = (topic, url.split("?")[0].split("#")[0])
                if not url or key in seen:
                    continue
                seen.add(key)
                corpus.append({
                    "id": f"w{wi}-{len(corpus):04d}", "week": wi, "window": window, "topic": topic,
                    "rank": offset * 20 + rank, "title": a.get("title") or "",
                    "description": a.get("description") or "", "url": url, "published_at": a.get("page_age") or "",
                })
                got += 1
            if len(results) < 20:
                break
        print(f"week {wi} {window}  {topic:<18} {got:>3} new articles")

json.dump(corpus, open(os.path.join(HERE, "corpus.json"), "w"), indent=1)
print(f"\n{len(corpus)} articles from {calls} search calls (${calls * 0.005:.2f})")
