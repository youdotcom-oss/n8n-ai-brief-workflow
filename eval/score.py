#!/usr/bin/env python3
"""Score corpus.json with the template's exact Jev request.

Reads the Jev questions and the Config values straight from ../workflow.json,
so the scores always match the shipped template. Run collect.py first.
Writes scores.local.json (gitignored) so it never overwrites the published
scores.json. Needs TYPESAFE_API_KEY. Standard library only.
"""
import concurrent.futures as cf
import json
import os
import re
import time
import urllib.request

KEY = os.environ["TYPESAFE_API_KEY"]
HERE = os.path.dirname(os.path.abspath(__file__))


def template_config():
    wf = json.load(open(os.path.join(HERE, "..", "workflow.json")))
    nodes = {n["name"]: n for n in wf["nodes"]}
    cfg = {a["name"]: a["value"] for a in nodes["Config"]["parameters"]["assignments"]["assignments"]}
    body = nodes["Jev: judge each article"]["parameters"]["jsonBody"]
    questions = re.search(r"questions: (\{.*\}) \}\) \}\}$", body, re.S).group(1)
    # n8n expressions can't contain '}}', so the template spaces it out. Undo that here.
    questions = json.loads(questions.replace("} }", "}}").replace("{ {", "{{"))
    return questions, cfg["team"], json.loads(cfg["caresAbout"])


def judge(article, questions, team, cares):
    state = {"watch": {"topic": article["topic"], "team": team, "cares_about": cares},
             "article": {k: article[k] for k in ("title", "description", "url")}
             | {"published_at": article["published_at"]}}
    body = json.dumps({"model": "jev-latest", "state": state, "questions": questions}).encode()
    req = urllib.request.Request("https://api.typesafe.ai/v1/systemone", data=body, method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"})
    for attempt in range(4):
        try:
            return article["id"], json.load(urllib.request.urlopen(req, timeout=60))["answers"]
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


if __name__ == "__main__":
    questions, team, cares = template_config()
    corpus = json.load(open(os.path.join(HERE, "corpus.json")))
    out = os.path.join(HERE, "scores.local.json")
    with cf.ThreadPoolExecutor(max_workers=8) as pool:
        scores = dict(pool.map(lambda a: judge(a, questions, team, cares), corpus))
    json.dump(scores, open(out, "w"), indent=1)
    print(f"scored {len(scores)} articles -> {out}")
