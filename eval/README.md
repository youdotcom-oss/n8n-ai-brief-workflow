# How the Filter Was Tuned

The brief is only useful if what it posts is real news. This folder holds the evaluation used to set the template's thresholds, with enough data to check every number.

## Setup

- **Articles:** 674 from eight one-week windows (Aug 11 to Oct 5, 2026) across three topics—AI model releases, AI agent tooling, and AI regulation. They came from the template's exact search: You.com Search, `<topic> news`, up to 40 results per topic per week.
- **Scores:** every article was scored with the template's exact Jev request, at about $0.000044 per article.
- **Labels:** 160 articles were labeled by hand as "belongs in the brief" or not, without seeing Jev's scores, using rules written down first ([`RUBRIC.md`](RUBRIC.md)). The sample was stratified, so precision and recall are weighted back to the full set.
- **Tuning:** thresholds were picked on weeks 0–3 and checked on weeks 4–7, which weren't used for tuning.

## Results

| | Original thresholds | Shipped thresholds |
|---|---|---|
| Cutoffs (new development / on topic / materiality) | 0.6 / 0.6 / 1.5 | **0.8 / 0.8 / 1.3** |
| Posts in the labeled sample | 60 (38 right, 22 wrong) | 39 (34 right, **5 wrong**) |
| Real developments missed (of 49) | 11 | 15 |
| Precision, held-out weeks | 0.74 | **0.89** |
| Recall, held-out weeks | 0.80 | 0.69 |
| Stories caught (any outlet's article got through) | 19 of 23 | 18 of 23 |

Precision is the share of posted items that are real news. Recall is the share of real news that gets posted. The shipped thresholds trade one missed story for about four times fewer wrong posts.

### Which Question Does the Work

| Questions used | Precision | Recall |
|---|---|---|
| Materiality only | 0.26 | 0.89 |
| + reports one new development | 0.80 | 0.83 |
| + on topic | 0.87 | 0.71 |

Asking only how much an article matters posts about three junk items for every real one. One narrow question—does this page report a single new development—fixes most of it.

## Reproduce It

```bash
python3 analyze.py   # every number above, from the files in this folder, no keys needed
```

To rebuild the dataset from scratch:

```bash
export YDC_API_KEY=...        # https://you.com/platform
export TYPESAFE_API_KEY=...   # https://console.typesafe.ai
python3 collect.py            # re-fetches the articles into corpus.json
python3 score.py              # scores them into scores.local.json
```

Search results for past weeks can drift, so a fresh collection won't match exactly.

## Files

| File | Contents |
|---|---|
| `articles.json` | The 674 articles: id, week, topic, search rank, and URL |
| `scores.json` | Jev's answers for every article |
| `labels.json` | The 160 hand labels, with a short reason for each |
| `RUBRIC.md` | The labeling rules |
| `analyze.py` | Recomputes the results |
| `collect.py` · `score.py` | Rebuild the dataset |

Article titles and descriptions aren't included because they belong to their publishers. `collect.py` fetches them again.

## Caveats

- **One labeler.** "Material" is a judgment call, and these are one person's calls.
- **Small sample.** 49 real developments, only 12 in the tuning weeks. Read the numbers as directional.
- **Historical search.** Older weeks returned fewer results, as few as 3 for one topic-week.
- **One setup.** Three topics and one audience. Other topics may need different thresholds.
