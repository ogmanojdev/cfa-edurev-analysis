#!/usr/bin/env python3
"""Build a cold re-attempt worksheet from the questions you got wrong.

  python3 worksheet.py "Financial Statement Analysis - 2"
  python3 worksheet.py --topic "Fixed Income"
  python3 worksheet.py --concept "Market efficiency"

Writes out/worksheet-<slug>.md: the stems and options with no answers, then a
separate key at the end. Re-attempt cold, then score yourself — a question you
now get right was a misread; one you still cannot do is a real gap.

Output stays in out/, which is gitignored. It contains question text.
"""
import sys, io, re, os, argparse, contextlib

ap = argparse.ArgumentParser()
ap.add_argument("match", nargs="?", default="", help="substring of the test name")
ap.add_argument("--topic", default="", help="filter by classified topic")
ap.add_argument("--concept", default="", help="filter by classified concept")
ARGS = ap.parse_args()

sys.argv = ["analyze"]
with contextlib.redirect_stdout(io.StringIO()):
    import analyze

sel = analyze.miss
if ARGS.match:
    sel = [r for r in sel if ARGS.match.lower() in r["test"].lower()]
if ARGS.topic:
    sel = [r for r in sel if ARGS.topic.lower() in r["topic"].lower()]
if ARGS.concept:
    sel = [r for r in sel if ARGS.concept.lower() in r["concept"].lower()]
if not sel:
    sys.exit("nothing matched — check the name against out/misses.csv")

sel.sort(key=lambda r: (r["test"], r["q"]))

# options and the source result page live on the raw records, not the flattened rows
opts, src = {}, {}
for cap, mt, f, d in analyze.chosen:
    if d.get("url"):
        src[d["test"]] = "https://edurev.in" + d["url"]
    for q in d["questions"]:
        opts[(d["test"], q["num"])] = q.get("options") or []

label = ARGS.concept or ARGS.topic or ARGS.match or "all"
slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
path = os.path.join(analyze.OUT, f"worksheet-{slug}.md")

L = [f"# Cold re-attempt — {label}", "",
     f"{len(sel)} questions you got wrong. Work them without the key, then score.",
     "A question you now get right was a misread. One you still cannot do is a real gap.",
     "",
     "Tag each one as you score it. If more than a third come back misread or calc slip,",
     "the remaining problem is exam technique, not content — and the last days should",
     "shift toward timed drilling rather than reading.",
     ""]
seen = [t for t in dict.fromkeys(r["test"] for r in sel) if t in src]
if seen:
    L.append("Source result page" + ("s" if len(seen) > 1 else "") + ":")
    L += [f"- [{t}]({src[t]})" for t in seen]
    L.append("")
for i, r in enumerate(sel, 1):
    L += [f"### {i}. {r['test']} Q{r['q']}  ·  {r['difficulty']}", "", r["stem"], ""]
    for o in opts.get((r["test"], r["q"]), []):
        L.append(f"- {o}")
    # deliberately NOT showing last time's pick — it would narrow three options to two
    L += ["", "Your answer: ______",
          "",
          "Tag it:  `[ ] concept gap`   `[ ] misread`   `[ ] calc slip`",
          "", "---", ""]

L += ["", "## Key", ""]
for i, r in enumerate(sel, 1):
    L += [f"**{i}.** {r['correct']}",
          f"   *Last time you picked: {r['yours'] or 'blank'}*", "",
          f"> {r['explanation']}" if r["explanation"] else "", ""]

open(path, "w").write("\n".join(L) + "\n")
print(f"{len(sel)} questions -> {path}")
