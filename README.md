# CFA Level 1 — EduRev result analyser

> **An independent project. Not affiliated with, endorsed by, or supported by EduRev.**
> It contains no EduRev code and no EduRev content. "CFA" is a trademark of CFA
> Institute, which is likewise unaffiliated.

EduRev tells you *that* you got 19 of 30 Fixed Income questions right. It does not tell
you that three of the eleven misses were the same confusion about premium bonds, or that
half your misses across every test were on questions it rated **Easy**.

This reads your own EduRev result pages, classifies every question against the CFA
Level 1 curriculum, and produces a ranked list of what to re-read — weighted by the
official topic weights, so a 12%-of-the-exam topic outranks a 6% one at the same miss
rate.

It is a personal study tool, not a scraper: it only reads result pages for tests **you**
have already sat, in **your** logged-in browser.

---

## What you get

A `report.md` with:

- **Topic rollup** — accuracy per topic next to the official exam weight, and an estimate
  of the exam points currently being left on the table in each.
- **Practice vs mock split** — most people's mocks score far higher than their topic
  drills. Seeing the gap per topic tells you which number to believe.
- **Ranked concepts to re-read**, each tied to a named curriculum module, with an
  `Easy misses` column — questions the bank itself rated Easy that you still got wrong.
  Those are definitional gaps and the cheapest points available.
- **Pace analysis** — seconds per question against the real 90 s budget, plus the misses
  that took more than 1.5× the average candidate's time. Long *and* wrong is the clearest
  evidence a concept is missing rather than misread.
- **Every miss, grouped by concept**, with the correct answer, your answer, and the
  explanation.

Plus `misses.csv` (one fully classified row per missed question — sort and filter it
however you like) and `by_concept.csv`.

The ranked table, two real rows from the author's own run:

| # | Topic | Concept | CFA module to read | Asked | Wrong | Accuracy | Easy misses |
|---|---|---|---|---|---|---|---|
| 1 | Equity | Market efficiency (weak/semi-strong/strong) | Market Efficiency | 11 | 5 | 54.5% | 2 |
| 2 | Alternatives | Contango, backwardation & roll yield | Natural Resources | 9 | 4 | 55.6% | 3 |

---

## How it works

Result pages ship the full solution set in the DOM — hidden behind the "Solutions" tab,
but already there on load. Nothing needs clicking, and no HTML is screen-scraped from
rendered text.

| File | Role |
|---|---|
| `extract.js` | Runs in a result page; reads `#solutionsDiv` and returns one record per question: status, difficulty, your time vs the average, stem, options, correct answer, your answer, explanation. |
| `collector.py` | Localhost sink on `:8787`. `POST /save` writes `raw/<slug>.json`; `GET /extract.js` serves the extractor so each page needs only a one-line bootstrap. |
| `bootstrap.js` | The one-liner to paste into each result page: fetch extractor → run → POST. |
| `taxonomy.py` | Topic weights plus ~90 concepts, each tied to a curriculum module and a keyword set. **This is the file to edit** as you spot mis-bucketed questions. |
| `analyze.py` | Classifies everything, writes the report and CSVs. |

---

## Use it

Requires Python 3 (standard library only — no dependencies) and a browser.

```bash
git clone https://github.com/ogmanojdev/cfa-edurev-analysis
cd cfa-edurev-analysis
python3 collector.py 8787
```

Leave that running. Then, for each of your result pages
(`https://edurev.in/course/quiz/result/...`), while logged in:

1. Open the page.
2. Open DevTools → Console.
3. Paste the contents of `bootstrap.js` and hit enter.

It prints the test name, your score, and the file it saved. Repeat for every test — it
takes a few seconds each. Then:

```bash
python3 analyze.py
open out/report.md
```

### Taking more tests later

Harvest the new result page the same way and re-run `analyze.py`. Nothing else to do —
the corpus grows and every number in the report is recomputed over all of it. Sitting
*Fixed Income 2* alongside *Fixed Income 1* simply gives that topic sixty questions of
evidence instead of thirty, and a concept you keep missing climbs the ranking as the
sample grows.

**Re-sitting a test you have already taken** is the one case that needs a rule, because
the questions repeat. Each attempt gets its own file, so an earlier try is never
overwritten, and by default only the most recent sit of each test counts — otherwise
questions you have now seen twice would be weighted double. The report lists any
attempts it set aside and shows a first-to-latest accuracy trend for every test sat more
than once.

```bash
python3 analyze.py --all    # count every attempt, including earlier sits
```

Tests are matched by title, so this only applies to a genuine re-sit; differently-named
tests always accumulate. Recency comes from the `capturedAt` stamp the extractor writes,
falling back to file mtime for files harvested before that field existed.

---

## Accuracy of the classification

It is keyword matching, and it is imperfect. Two things make it trustworthy enough to act
on, and you should re-check both against your own data:

- Mock exams run in curriculum order. When classified, the assigned topics come out as
  contiguous blocks matching that order — an independent check that the classifier is
  tracking the real topic, not coincidental vocabulary.
- On the data it was built against, 110 of 112 misses classified on the first pass, and
  the stragglers were fixed by adding keywords.

`analyze.py` prints an unclassified count every run. If it climbs, open `misses.csv`,
find what fell through, and add keywords to `taxonomy.py`. Anything unclassified still
appears in the report — it is never silently dropped.

The taxonomy reflects the current Level 1 curriculum. One thing it surfaced on the
author's own data: several Derivatives questions in the bank test **Level 2** material
(Black-Scholes inputs, two-period binomial trees, delta-hedge rebalancing). If a topic
looks alarmingly weak, check whether the questions are actually in scope before spending
days on it.

---

## Scope, and what this repository deliberately excludes

EduRev were asked before this was published, and were broadly supportive of the code
being open-sourced on four conditions. Those conditions are met as follows, and anyone
forking this is expected to keep them met.

**1. Only my own code.** Every file here was written for this project. There is no
EduRev source code. `extract.js` does reference EduRev's own CSS class names
(`#solutionsDiv`, `.solutionquestion`, `.wrng_ans`) because it has to read their markup
— the same way any client references the field names of the thing it reads. Those
selectors are not their code, but they are named here rather than hidden.

**2. No EduRev content, ever.** `.gitignore` excludes `raw/` (question text, options and
explanations, copied verbatim into local JSON) and `out/` (the generated report, which
quotes them). Nothing derived from the question bank is committed. If you build
something from your own report — a study plan, notes, a summary — check it for
reconstructed questions and worked answers before committing it; that is still their
content in paraphrase.

**3. Only data you are already authorised to see.** The extractor reads the solution set
that your own result page has already loaded into your own browser, for tests on your
own account. It makes no API calls, cannot enumerate tests, cannot reach another user's
data, and cannot retrieve anything you have not purchased.

**4. Independence stated.** See the top of this file.

---

## Adapting it

The extractor is specific to EduRev's result-page markup. The rest is not: `taxonomy.py`
is a plain mapping of concept → module → keywords, and `analyze.py` only needs a list of
questions with a status and some text. Point a different extractor at it and the same
report works for any question bank — or swap the taxonomy for Level 2, or for something
that is not the CFA at all.

MIT licensed. Not affiliated with EduRev or CFA Institute. "CFA" is a trademark of CFA
Institute.
