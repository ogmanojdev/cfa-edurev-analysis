# Adding a new test result

Three steps. The whole thing takes under a minute per test.

## 1. Start the collector (once per session)

```bash
cd ~/Documents/GitHub/cfa-edurev-analysis
python3 collector.py 8787
```

Leave it running in its own terminal tab. It prints a line for each test it saves.

## 2. Harvest the result page

Open the result page on EduRev, logged in, then **either**:

- **Click the bookmarklet** (set up once, below) — nothing else needed, or
- Open DevTools → Console, paste the contents of `bootstrap.js`, press enter.

Either way a green banner (or a console line) confirms the test name, your score
and the number of questions saved.

### Setting up the bookmarklet (once)

1. Show the bookmarks bar: **⌘⇧B** in Chrome.
2. Right-click the bar → **Add page…**
3. Name it `Harvest`, and paste the entire contents of `bookmarklet.min.txt`
   into the URL field.

From then on it is one click on any result page.

## 3. Rebuild the analysis

```bash
python3 analyze.py && python3 rebuild_tracker.py
```

`analyze.py` rewrites `out/report.md` and the CSVs over the whole corpus.
`rebuild_tracker.py` then refreshes every figure inside `tracker.html` — the
masthead counts, the topic table, the worst-concepts table, each task's stat
chip and easy-miss count, and the result-page links. Only the numbers change;
none of the written guidance is touched. Both are safe to re-run as often as
you like.

Then ask Claude to republish the tracker, or open `out/report.md` directly.

## Notes

- **Each attempt gets its own file.** Re-sitting a test never overwrites the
  earlier try; by default only the latest sit of a given test counts. See the
  README.
- **A new, differently-named test just adds** to the corpus — no flags needed.
- Harvest the same evening you sit a test, so the next day's ranking reflects it.
- Everything written lands in `raw/` and `out/`, both gitignored.
