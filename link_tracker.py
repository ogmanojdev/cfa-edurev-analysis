#!/usr/bin/env python3
"""Inject EduRev result-page links into tracker.html.

Each study task is mapped to the taxonomy concepts it covers. For every task,
this finds the tests that actually contain misses for those concepts and adds a
link to each result page, ordered by how many of that task's misses live there.
Re-run after harvesting new tests to refresh the links.
"""
import sys, io, re, json, contextlib
from collections import defaultdict

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
 "d3": ["Credit risk components & spreads", "Term structure / spot-forward-par curves"],
 "e1": ["GIPS standards"],
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
 "k3": ["Financial reporting quality: accruals & earnings quality",
        "Ratio analysis & DuPont decomposition"],
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
added = skipped = 0
for tid, concepts in TASKS.items():
    tally = defaultdict(int)
    for c in concepts:
        for test, n in by_concept.get(c, {}).items():
            tally[test] += n
    links = [{"label": f"{short(t)} ({n})", "url": src[t]}
             for t, n in sorted(tally.items(), key=lambda kv: -kv[1]) if t in src]
    if not links:
        skipped += 1
        continue
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
