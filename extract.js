/* EduRev quiz-result extractor.
   Paste/run in the page context of any
   https://edurev.in/course/quiz/result/<id> page while logged in.
   Returns one JSON object per test with a row per question. */
(() => {
  const clean = s => (s || '')
    .replace(/ /g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    // defang long opaque tokens (base64 / ids) that trip output filters
    .replace(/[A-Za-z0-9+/]{25,}={0,2}/g, '~');

  const crumb = clean(
    (document.querySelector('.breadcrumb, #breadcrumb') || {}).innerText ||
    document.body.innerText.split('\n').find(l => l.includes('>')) || ''
  );

  // ---- scorecard ----
  const txt = document.body.innerText;
  const grab = re => { const m = txt.match(re); return m ? m[1].trim() : null; };
  // .../quiz/result/<courseId>_<testId>_<attemptUuid>
  const m = location.pathname.match(/result\/(\d+)_(\d+)_([0-9a-f-]+)/i) || [];
  const meta = {
    test: clean(document.title).replace(/\s*\|.*$/, ''),
    testId: m[2] || null,
    attemptId: m[3] || null,
    capturedAt: new Date().toISOString(),
    url: location.pathname,
    breadcrumb: crumb,
    marks: grab(/Total Marks\s*\n\s*([\d.]+\/[\d.]+)/),
    accuracy: grab(/Accuracy\s*\n\s*([\d.]+%)/),
    percentile: grab(/Percentile\s*\n\s*([\d.]+)/),
    rank: grab(/Rank\s*\n\s*(\S+)/),
    timeTaken: grab(/Time Taken\s*\n\s*(.+)/)
  };

  // ---- per question ----
  const secs = [...document.querySelectorAll('#solutionsDiv .solutionquestion')];
  const questions = secs.map((sec, i) => {
    const cls = sec.className || '';
    const status = /wrng_ans/.test(cls) ? 'incorrect'
                 : /crt_ans/.test(cls) ? 'correct'
                 : 'unattempted';

    const head = clean((sec.querySelector('.accordion-section-title') || {}).innerText);
    // head looks like: "Q12Incorrect | Medium | 1m 37s<stem...>"
    const hm = head.match(/^Q(\d+)\s*(Correct|Incorrect|Unattempted)?\s*\|?\s*(Easy|Medium|Hard|Difficult)?\s*\|?\s*([\dhms ]+)?/i);
    const num        = hm ? +hm[1] : i + 1;
    const difficulty = hm && hm[3] ? hm[3] : null;
    const yourTime   = hm && hm[4] ? hm[4].trim() : null;
    const stem       = head.replace(/^Q\d+\s*(Correct|Incorrect|Unattempted)?\s*\|?\s*(Easy|Medium|Hard|Difficult)?\s*\|?\s*[\dhms ]*/i, '').trim();

    const opts = [...sec.querySelectorAll('ul.answerList li')].map(li => {
      const t = clean(li.innerText);
      return {
        text: t.replace(/(Correct Answer|Your Answer)/g, '').trim(),
        isCorrect: /Correct Answer/.test(t),
        isYours: /Your Answer/.test(t)
      };
    });

    const avgTime = clean((sec.querySelector('.avgscordivsol') || {}).innerText)
      .replace(/^Avg Time Taken\s*:?\s*/i, '');

    return {
      num, status, difficulty, yourTime, avgTime,
      stem,
      correctAnswer: (opts.find(o => o.isCorrect) || {}).text || null,
      yourAnswer:    (opts.find(o => o.isYours)   || {}).text || null,
      options: opts.map(o => o.text),
      explanation: clean((sec.querySelector('.qz_rst_sl') || {}).innerText).slice(0, 700)
    };
  });

  return {
    ...meta,
    counts: {
      total: questions.length,
      correct: questions.filter(q => q.status === 'correct').length,
      incorrect: questions.filter(q => q.status === 'incorrect').length,
      unattempted: questions.filter(q => q.status === 'unattempted').length
    },
    questions
  };
})()
