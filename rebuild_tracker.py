#!/usr/bin/env python3
"""Inject EduRev result-page links into tracker.html.

Each study task is mapped to the taxonomy concepts it covers. For every task,
this finds the tests that actually contain misses for those concepts and adds a
link to each result page, ordered by how many of that task's misses live there.
Re-run after harvesting new tests to refresh the links.
"""
import sys, io, re, json, contextlib
from collections import defaultdict

from taxonomy import WEIGHTS

sys.argv = ["analyze"]
with contextlib.redirect_stdout(io.StringIO()):
    import analyze

# task id -> the taxonomy concepts that task covers
TASKS = {
 "a1": ["Market efficiency (weak/semi-strong/strong)"],
 "a2": ["Industry & competitive analysis (Porter)"],
 "a3": ["Security market indexes & weighting", "Valuation multiples (P/E, P/B, EV/EBITDA)"],
 "b1": ["Revenue recognition (5-step model)"],
 "b2": ["Accrual vs cash basis & statement fundamentals"],
 "b3": ["IFRS vs US GAAP differences"],
 "c1": ["Premium/discount & price-yield relationship"],
 "c2": ["Yield measures & ranking (YTM vs current yield)"],
 "d1": ["Duration (Macaulay / modified / effective)"],
 "d2": ["Convexity", "Interest rate vs reinvestment risk"],
 "d3": ["Credit risk components & spreads"],
 "e1": ["GIPS standards"],
 "e3": ["Term structure / spot-forward-par curves"],
 "e2": ["Standard II: Integrity of Capital Markets", "Standard III: Duties to Clients",
        "Standard I: Professionalism", "Standard VI: Conflicts of Interest",
        "Ethical decision-making & professionalism framework"],
 "f1": ["Elasticity of demand"],
 "f2": ["Market structures: monopoly, oligopoly, competition"],
 "f3": ["Demand & supply analysis, surplus, price controls"],
 "g1": ["Currency exchange rates & parity conditions"],
 "g2": ["Money, inflation & quantity theory"],
 "g3": ["Business cycles & aggregate output", "Fiscal policy & automatic stabilisers",
        "Fiscal policy & automatic stabilizers", "International trade & comparative advantage"],
 "j1": ["Contango, backwardation & roll yield"],
 "j2": ["Performance measurement: IRR, MOIC, TVPI"],
 "j3": ["Fund structures: open-end vs closed-end, fee terms",
        "Real estate & infrastructure valuation (NAV, cap rate)",
        "Hedge fund strategies & due diligence"],
 "k1": ["CML, SML & two-fund separation"],
 "k2": ["Portfolio variance, covariance & correlation math",
        "Efficient frontier & diversification benefits"],
 # scoped to earnings quality alone: folding in DuPont (2/39) would mask the
 # 74% signal behind a flattering aggregate
 "k3": ["Financial reporting quality: accruals & earnings quality"],
 "l1": ["Binomial option pricing"],
 "l2": ["Put-call parity & synthetic positions"],
 "l3": ["Option moneyness, intrinsic & time value"],
 "m2": ["Leases (lessee accounting)", "Income taxes & deferred tax",
        "Financial instruments: FVOCI / FVPL classification",
        "Long-lived assets: capitalization, depreciation, impairment",
        "Bonds payable: discount/premium amortization",
        "Off-balance-sheet obligations"],
 "m3": ["Statistical measures: dispersion, skew, kurtosis",
        "Simple linear regression & R-squared",
        "Probability: Bayes, conditional & total probability",
        "Time value of money: annuities & perpetuities"],
}

src = {}
for cap, mt, f, d in analyze.chosen:
    if d.get("url"):
        src[d["test"]] = "https://edurev.in" + d["url"]

by_concept = defaultdict(lambda: defaultdict(int))
for r in analyze.miss:
    by_concept[r["concept"]][r["test"]] += 1


def short(name):
    n = re.sub(r"^(Practice Test|Mock Test)\s*:?\s*", "", name).strip()
    n = n.replace("CFA Level 1 - ", "Mock ")
    return n


html = open("tracker.html").read()

# ---------- headline counts ----------
n_tests = len({r["test"] for r in analyze.rows})
n_q, n_miss = len(analyze.rows), len(analyze.miss)
html = re.sub(r"Built from [\d,]+ answered questions across \d+ EduRev tests &mdash; [\d,]+ misses",
              f"Built from {n_q:,} answered questions across {n_tests} EduRev tests &mdash; {n_miss} misses",
              html)
html = re.sub(r"Where the [\d,]+ misses sit", f"Where the {n_miss} misses sit", html)

# ---------- topic table ----------
tstat = defaultdict(lambda: [0, 0])
for r in analyze.rows:
    if r["topic"] in WEIGHTS:
        c = tstat[r["topic"]]; c[0] += 1; c[1] += (r["status"] != "correct")
trows = []
for t, (n, w) in tstat.items():
    acc = 100 * (1 - w / n)
    mid = sum(WEIGHTS[t]) / 2
    pts = (w / n) * mid
    lo, hi = WEIGHTS[t]
    trows.append((pts, f' ["{t}","{acc:.1f}%",{pts:.2f},"{lo}\u2013{hi}%",{w}]'))
topics = "const TOPICS = [\n" + ",\n".join(r for _, r in sorted(trows, reverse=True)) + "\n];"
html = re.sub(r"const TOPICS = \[.*?\n\];", topics, html, flags=re.S)

# ---------- worst concepts ----------
crows = []
for c in analyze.conc:
    # a 1-of-1 miss is a 100% miss rate and tells you nothing; require a real
    # sample and more than one miss before a concept earns a place in the rail
    if c["wrong"] >= 2 and c["asked"] >= 4 and c["topic"] in WEIGHTS:
        crows.append((c["wrong"] / c["asked"], c["wrong"],
                      f' ["{c["concept"]}","{c["topic"]}",{c["wrong"]},{c["asked"]}]'))
crows.sort(key=lambda r: (-r[0], -r[1]))
concepts = "const CONCEPTS = [\n" + ",\n".join(r for _, _, r in crows[:14]) + "\n];"
html = re.sub(r"const CONCEPTS = \[.*?\n\];", concepts, html, flags=re.S)

added = skipped = 0
for tid, concepts_of in TASKS.items():
    tally = defaultdict(int)
    for c in concepts_of:
        for test, n in by_concept.get(c, {}).items():
            tally[test] += n
    links = [{"label": f"{short(t)} ({n})", "url": src[t]}
             for t, n in sorted(tally.items(), key=lambda kv: -kv[1]) if t in src]

    # refresh this task's stat chip, easy-miss count and priority flag
    asked = wrong = easy = 0
    for c in concepts_of:
        hit = [r for r in analyze.rows if r["concept"] == c]
        asked += len(hit)
        wrong += sum(1 for r in hit if r["status"] != "correct")
        easy += sum(1 for r in hit if r["status"] != "correct"
                    and r["difficulty"].lower().startswith("easy"))
    if asked:
        acc = 100 * (1 - wrong / asked)
        stat = f"{wrong} of {asked} wrong \u00b7 {acc:.0f}%"
        pat_s = re.compile(r'(\{id:"' + tid + r'",.*?)stat:"[^"]*"', re.S)
        if pat_s.search(html):
            html = pat_s.sub(lambda m: m.group(1) + f'stat:"{stat}"', html, count=1)
        # bad: flagged when the task is below 60% or carries 4+ misses
        pat_f = re.compile(r'(\{id:"' + tid + r'",.*?stat:"[^"]*",\s*)(?:bad:1,\s*)?(?:ez:\d+,\s*)?', re.S)
        flags = ("bad:1, " if (acc < 60 or wrong >= 4) else "") + (f"ez:{easy}, " if easy else "")
        html = pat_f.sub(lambda m: m.group(1) + flags, html, count=1)

    if not links:
        skipped += 1
        continue
    # drop any links: already on this task, so re-running stays idempotent
    html = re.sub(r'(\{id:"' + tid + r'",.*?)\n\s*links:\[.*?\],(?=\n\s*fix:)',
                  lambda m: m.group(1), html, count=1, flags=re.S)
    # attach to the task object, right before its fix: field
    pat = re.compile(r'(\{id:"' + tid + r'",.*?)(\n\s*fix:)', re.S)
    if not pat.search(html):
        skipped += 1
        continue
    payload = "\n    links:" + json.dumps(links, ensure_ascii=False) + ","
    html = pat.sub(lambda m: m.group(1).rstrip().rstrip(",") + "," + payload + m.group(2), html, count=1)
    added += 1

open("tracker.html", "w").write(html)
print(f"linked {added} tasks, skipped {skipped}")
