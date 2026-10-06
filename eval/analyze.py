#!/usr/bin/env python3
"""Reproduce every number in eval/README.md from the published data.

Inputs (all in this folder):
  articles.json  674 articles: id, week, window, topic, search rank, URL
  scores.json    Jev's answers for every article (the template's exact request)
  labels.json    160 hand labels, made without seeing Jev's scores

No API keys or network needed. Standard library only.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
articles = {a["id"]: a for a in json.load(open(os.path.join(HERE, "articles.json")))}
scores = json.load(open(os.path.join(HERE, "scores.json")))
labels = json.load(open(os.path.join(HERE, "labels.json")))

SHIPPED = dict(new=0.8, topic=0.8, mat=1.3)
ORIGINAL = dict(new=0.6, topic=0.6, mat=1.5)


def gates(a):
    return a["reports_new_development"]["noul"], a["about_topic"]["noul"], a["materiality"]["score"]


def passes(a, new, topic, mat, use=("new", "topic", "mat")):
    n, t, m = gates(a)
    return ("new" not in use or n >= new) and ("topic" not in use or t >= topic) and ("mat" not in use or m >= mat)


def stratum(a):
    """How the labeling sample was drawn (from the original thresholds)."""
    n, t, m = gates(a)
    if n >= 0.6 and t >= 0.6 and m >= 1.5:
        return "pass"
    if (1.0 <= m < 1.5 and n >= 0.4 and t >= 0.4) or (m >= 1.5 and (0.4 <= n < 0.6 or 0.4 <= t < 0.6)):
        return "near"
    return "fail"


# The sample oversampled likely passes, so weight each label back to its share of the corpus.
population, sampled = {}, {}
for aid, a in scores.items():
    population[stratum(a)] = population.get(stratum(a), 0) + 1
for row in labels:
    sampled[row["stratum"]] = sampled.get(row["stratum"], 0) + 1
weight = {s: population[s] / sampled[s] for s in sampled}


def precision_recall(rows, **kw):
    tp = fp = fn = 0.0
    for row in rows:
        w, pred, y = weight[row["stratum"]], passes(scores[row["id"]], **kw), row["label"]
        tp += w * (pred and y)
        fp += w * (pred and not y)
        fn += w * (not pred and y)
    return tp / (tp + fp), tp / (tp + fn)


def raw_counts(**kw):
    c = {"right": 0, "wrong": 0, "missed": 0}
    for row in labels:
        pred, y = passes(scores[row["id"]], **kw), row["label"]
        c["right" if pred and y else "wrong" if pred else "missed" if y else "_"] = \
            c.get("right" if pred and y else "wrong" if pred else "missed" if y else "_", 0) + 1
    return c


held_out = [r for r in labels if articles[r["id"]]["week"] >= 4]

print(f"Corpus: {len(articles)} articles, 8 weeks, 3 topics. Labeled: {len(labels)} "
      f"({sum(r['label'] for r in labels)} real developments).\n")

print("Funnel (all articles):")
for name, kw in (("original", ORIGINAL), ("shipped", SHIPPED)):
    kept = [aid for aid, a in scores.items() if passes(a, **kw)]
    briefs = {(articles[a]["week"], articles[a]["topic"]) for a in kept}
    print(f"  {name:<9} {len(kept):>3} material articles -> {len(briefs):>2} topic-week briefs (of 24)")

print("\nLabeled sample:")
for name, kw in (("original", ORIGINAL), ("shipped", SHIPPED)):
    c = raw_counts(**kw)
    print(f"  {name:<9} posts {c['right'] + c['wrong']:>2} ({c['right']} right, {c['wrong']} wrong), "
          f"misses {c['missed']} of {sum(r['label'] for r in labels)}")

print("\nPrecision / recall, weighted to the corpus:")
for name, kw in (("original", ORIGINAL), ("shipped", SHIPPED)):
    p, r = precision_recall(labels, **kw)
    ph, rh = precision_recall(held_out, **kw)
    print(f"  {name:<9} all P {p:.2f} R {r:.2f} | held-out weeks 4-7 P {ph:.2f} R {rh:.2f}")

print("\nWhich question does the work (shipped thresholds):")
for use in (("mat",), ("new", "mat"), ("new", "topic", "mat")):
    p, r = precision_recall(labels, use=use, **SHIPPED)
    print(f"  {' + '.join(use):<18} P {p:.2f} R {r:.2f}")
