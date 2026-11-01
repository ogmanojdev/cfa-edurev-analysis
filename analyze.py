#!/usr/bin/env python3
"""Turn harvested EduRev results into a weak-area / reading-priority report.

  python3 analyze.py            # latest attempt of each test (default)
  python3 analyze.py --all      # count every attempt, including earlier sits
"""
import json, glob, os, re, csv, sys, argparse
from collections import defaultdict
from taxonomy import TAXONOMY, WEIGHTS, TEST_TOPIC

HERE = os.path.dirname(os.path.abspath(__file__))
RAW, OUT = os.path.join(HERE, "raw"), os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

# ---------- classification ----------
COMPILED = {t: [(lab, mod, [re.compile(k, re.I) for k in ks])
                for lab, mod, ks in items] for t, items in TAXONOMY.items()}


def haystack(q):
    return " ".join(filter(None, [
        q.get("stem"), q.get("correctAnswer"), q.get("yourAnswer"),
        " ".join(q.get("options") or []), q.get("explanation")])).lower()


def classify(q, topic_hint=None):
    """Return (topic, concept, module, confidence)."""
    hay = haystack(q)
    best = (0, None, None, None)
    topics = [topic_hint] if topic_hint else list(COMPILED)
    for t in topics:
        for lab, mod, pats in COMPILED[t]:
            score = sum(1 for p in pats if p.search(hay))
            if score > best[0]:
                best = (score, t, lab, mod)
    if best[0] == 0 and topic_hint:          # fall back: scan every topic
        for t in COMPILED:
            for lab, mod, pats in COMPILED[t]:
                score = sum(1 for p in pats if p.search(hay))
                if score > best[0]:
                    best = (score, t, lab, mod)
    if best[0] == 0:
        return (topic_hint or "Unclassified", "Unclassified", "-", 0)
    return (best[1], best[2], best[3], best[0])


def test_topic(title):
    for pat, t in TEST_TOPIC:
        if re.search(pat, title, re.I):
            return t
    return None


ap = argparse.ArgumentParser()
ap.add_argument("--all", action="store_true",
                help="include every attempt, not just the latest sit of each test")
ARGS = ap.parse_args()

# ---------- load ----------
# One file per attempt. By default only the most recent sit of each test counts,
# so re-taking a test replaces its old numbers instead of double-counting
# questions you have now seen twice. Recency = capturedAt, falling back to mtime.
files = sorted(glob.glob(os.path.join(RAW, "*.json")))
loaded = []
for f in files:
    d = json.load(open(f))
    loaded.append((d.get("capturedAt") or "", os.path.getmtime(f), f, d))

attempts = defaultdict(list)
for cap, mt, f, d in loaded:
    attempts[d["test"]].append((cap, mt, f, d))
for k in attempts:
    attempts[k].sort(key=lambda x: (x[0], x[1]))

if ARGS.all:
    chosen = [t for v in attempts.values() for t in v]
else:
    chosen = [v[-1] for v in attempts.values()]
chosen.sort(key=lambda x: x[3]["test"])
superseded = sum(len(v) - 1 for v in attempts.values())

rows, tests = [], []
for cap, mt, f, d in chosen:
    is_mock = "mock" in d["test"].lower()
    hint = None if is_mock else test_topic(d["test"])
    tests.append({"test": d["test"], "kind": "mock" if is_mock else "practice",
                  "marks": d["marks"], "accuracy": d["accuracy"],
                  "time": d["timeTaken"], "sits": len(attempts[d["test"]]),
                  **d["counts"]})
    for q in d["questions"]:
        topic, concept, module, conf = classify(q, hint)
        rows.append({
            "test": d["test"], "kind": "mock" if is_mock else "practice",
            "q": q["num"], "status": q["status"],
            "difficulty": q["difficulty"] or "?", "topic": topic,
            "concept": concept, "module": module, "confidence": conf,
            "yourTime": q["yourTime"], "avgTime": q["avgTime"],
            "stem": re.sub(r"\s+", " ", q["stem"])[:400],
            "correct": (q["correctAnswer"] or "")[:200],
            "yours": (q["yourAnswer"] or ("BLANK" if q["status"] == "unattempted" else "")),
            "explanation": q["explanation"][:400],
        })

miss = [r for r in rows if r["status"] != "correct"]

# ---------- aggregate ----------
def agg(key):
    d = defaultdict(lambda: {"n": 0, "wrong": 0, "easy_wrong": 0, "blank": 0})
    for r in rows:
        k = r[key] if key != "both" else (r["topic"], r["concept"], r["module"])
        s = d[k]; s["n"] += 1
        if r["status"] != "correct":
            s["wrong"] += 1
            if r["difficulty"].lower().startswith("easy"):
                s["easy_wrong"] += 1
            if r["status"] == "unattempted":
                s["blank"] += 1
    return d

by_topic, by_concept = agg("topic"), agg("both")

mid = {t: sum(w) / 2 for t, w in WEIGHTS.items()}


def priority(topic, wrong, n):
    """Expected exam points recoverable: miss-rate x topic weight."""
    if not n or topic not in mid:
        return 0.0
    return (wrong / n) * mid[topic]


# ---------- write CSVs ----------
with open(os.path.join(OUT, "misses.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(miss)

conc = []
for (topic, concept, module), s in by_concept.items():
    conc.append({"topic": topic, "concept": concept, "module": module,
                 "asked": s["n"], "wrong": s["wrong"],
                 "accuracy": round(100 * (1 - s["wrong"] / s["n"]), 1),
                 "easy_wrong": s["easy_wrong"], "blank": s["blank"],
                 "exam_weight_pct": mid.get(topic, 0),
                 "priority": round(priority(topic, s["wrong"], s["n"]) * s["wrong"], 2)})
conc.sort(key=lambda r: (-r["wrong"], -r["priority"]))
with open(os.path.join(OUT, "by_concept.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(conc[0].keys()))
    w.writeheader(); w.writerows(conc)

# ---------- report ----------
L = []
A = L.append
A("# CFA L1 — weak-area analysis from EduRev results\n")
A(f"Source: {len(tests)} tests, {len(rows)} questions, {len(miss)} not answered correctly.\n")

if superseded and not ARGS.all:
    A(f"_{superseded} earlier attempt(s) superseded by a later sit of the same test and "
      f"excluded. Run `python3 analyze.py --all` to count them._\n")

multi = {k: v for k, v in attempts.items() if len(v) > 1}
if multi:
    A("## Repeat attempts\n")
    A("| Test | Sits | Accuracy, first to latest |")
    A("|---|---|---|")
    for k, v in sorted(multi.items()):
        A(f"| {k} | {len(v)} | " + "  →  ".join(a[3]["accuracy"] for a in v) + " |")
    A("")

A("## Test-level results\n")
A("| Test | Marks | Accuracy | Correct | Wrong | Blank | Time |")
A("|---|---|---|---|---|---|---|")
for t in sorted(tests, key=lambda x: (x["kind"], x["test"])):
    A(f"| {t['test']} | {t['marks']} | {t['accuracy']} | {t['correct']} | "
      f"{t['incorrect']} | {t['unattempted']} | {t['time']} |")

A("\n## Topic rollup (practice + mock combined)\n")
A("| Topic | Asked | Wrong | Accuracy | Exam weight | Pts at stake | Easy misses |")
A("|---|---|---|---|---|---|---|")
tr = []
for t, s in by_topic.items():
    acc = 100 * (1 - s["wrong"] / s["n"])
    tr.append((priority(t, s["wrong"], s["n"]), t, s, acc))
for p, t, s, acc in sorted(tr, reverse=True):
    wt = WEIGHTS.get(t)
    A(f"| {t} | {s['n']} | {s['wrong']} | {acc:.1f}% | "
      f"{(str(wt[0])+'-'+str(wt[1])+'%') if wt else '-'} | {p:.2f} | {s['easy_wrong']} |")

# ---- practice vs mock, by topic ----
A("\n## Practice tests vs mocks, by topic\n")
A("The mocks run in curriculum order and score far higher than the topic drills. "
  "Where the gap is wide, the mock is the softer test — trust the drill.\n")
A("| Topic | Practice acc. | Mock acc. | Gap | Practice q | Mock q |")
A("|---|---|---|---|---|---|")
pm = defaultdict(lambda: {"p": [0, 0], "m": [0, 0]})
for r in rows:
    if r["topic"] not in mid:
        continue
    c = pm[r["topic"]]["p" if r["kind"] == "practice" else "m"]
    c[0] += 1
    c[1] += (r["status"] == "correct")
prs = []
for t, c in pm.items():
    pa = 100 * c["p"][1] / c["p"][0] if c["p"][0] else None
    ma = 100 * c["m"][1] / c["m"][0] if c["m"][0] else None
    gap = (ma - pa) if (pa is not None and ma is not None) else -999
    prs.append((gap, t, pa, ma, c))
for gap, t, pa, ma, c in sorted(prs, reverse=True):
    A(f"| {t} | {('%.1f%%' % pa) if pa is not None else '—'} | "
      f"{('%.1f%%' % ma) if ma is not None else '—'} | "
      f"{('+%.1f pp' % gap) if gap != -999 else '—'} | {c['p'][0]} | {c['m'][0]} |")

# ---- pace ----
def secs(s):
    if not s:
        return None
    tot = 0
    for v, u in re.findall(r"(\d+)\s*([hms])", s):
        tot += int(v) * {"h": 3600, "m": 60, "s": 1}[u]
    return tot or None

A("\n## Pace\n")
A("Real exam budget is 270 min for 180 questions = **90 s/question**.\n")
A("| Test | Questions | Total time | s/question | vs 90s |")
A("|---|---|---|---|---|")
for t in sorted(tests, key=lambda x: (x["kind"], x["test"])):
    tt = secs(t["time"])
    if not tt:
        continue
    per = tt / t["total"]
    A(f"| {t['test']} | {t['total']} | {t['time']} | {per:.0f} s | "
      f"{'+' if per > 90 else ''}{per-90:.0f} s |")

capped = [t for t in tests if secs(t["time"]) and 2600 < secs(t["time"]) <= 2700
          and t["total"] == 30]
if capped:
    A("\n**Note:** " + ", ".join(t["test"] for t in capped) +
      " each ended at ~44m58s — that is the 45-minute test cap, not a pacing choice. "
      "Blanks on those tests were time-outs, so the real pace on them is unknown and the "
      "90 s/question figure is a ceiling.\n")

slow = [r for r in miss if secs(r["yourTime"]) and secs(r["avgTime"])
        and secs(r["yourTime"]) > 1.5 * secs(r["avgTime"])]
A(f"\n{len(slow)} of your {len(miss)} misses also took **more than 1.5x the average "
  f"candidate's time** — long *and* wrong, which is the clearest signal the underlying "
  f"concept is missing rather than misread:\n")
for r in sorted(slow, key=lambda r: -(secs(r["yourTime"]) / secs(r["avgTime"])))[:15]:
    A(f"- {r['topic']} / {r['concept']} — {r['test']} Q{r['q']}: "
      f"you {r['yourTime']} vs avg {r['avgTime']}")

A("\n## Concepts to re-read, ranked by misses\n")
A("Only concepts you actually got wrong. `Easy misses` = questions EduRev tagged Easy "
  "that you still missed — those are definitional gaps, the cheapest points on this list.\n")
A("| # | Topic | Concept | CFA module to read | Asked | Wrong | Accuracy | Easy misses |")
A("|---|---|---|---|---|---|---|---|")
i = 0
for r in conc:
    if r["wrong"] == 0:
        continue
    i += 1
    A(f"| {i} | {r['topic']} | {r['concept']} | {r['module']} | {r['asked']} | "
      f"{r['wrong']} | {r['accuracy']}% | {r['easy_wrong']} |")

A("\n## Clean sheet — concepts tested with zero misses\n")
clean = [r for r in conc if r["wrong"] == 0 and r["asked"] >= 2]
clean.sort(key=lambda r: -r["asked"])
A(", ".join(f"{r['concept']} ({r['asked']})" for r in clean) or "_none_")

A("\n## Every miss, grouped by concept\n")
g = defaultdict(list)
for r in miss:
    g[(r["topic"], r["concept"], r["module"])].append(r)
for k in sorted(g, key=lambda k: -len(g[k])):
    topic, concept, module = k
    A(f"\n### {topic} — {concept}  ({len(g[k])} missed)")
    A(f"*Read: {module}*\n")
    for r in g[k]:
        tag = "BLANK" if r["status"] == "unattempted" else "wrong"
        A(f"- **{r['test']} Q{r['q']}** [{r['difficulty']}, {tag}] — {r['stem'][:220]}")
        A(f"  - correct: {r['correct'][:150]}")
        if r["yours"]:
            A(f"  - you chose: {r['yours'][:150]}")
        if r["explanation"]:
            A(f"  - why: {r['explanation'][:260]}")

open(os.path.join(OUT, "report.md"), "w").write("\n".join(L) + "\n")

unc = sum(1 for r in rows if r["concept"] == "Unclassified")
print(f"tests={len(tests)} questions={len(rows)} misses={len(miss)} "
      f"unclassified={unc} ({100*unc/len(rows):.1f}%)"
      + (f" superseded={superseded}" if superseded else ""))
print("wrote out/report.md, out/misses.csv, out/by_concept.csv")
