/* One-liner to run on any EduRev result page: pulls extract.js from the
   local collector, runs it, and POSTs the result back for storage. */
await (async () => {
  const base = 'http://localhost:8787';
  const src = await fetch(base + '/extract.js').then(r => r.text());
  const data = eval(src);
  // one file per ATTEMPT, so re-sitting a test never overwrites the earlier try
  const stem = data.test.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
  const slug = stem + (data.attemptId ? '__' + data.attemptId.slice(0, 8) : '');
  const res = await fetch(base + '/save', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ slug, data })
  }).then(r => r.json());
  return { slug, test: data.test, marks: data.marks, accuracy: data.accuracy, ...res };
})()
