async function loadCockpit() {
  const res = await fetch('./data/latest.json', { cache: 'no-store' });
  const data = await res.json();

  const headline = data.headline || {};
  document.getElementById('headline').innerHTML = `
    <p><strong>Day:</strong> ${data.day}</p>
    <p><strong>Overall:</strong> ${headline.overall ?? 'unknown'}</p>
    <p><strong>Enabled jobs:</strong> ${headline.enabledJobs ?? '—'}</p>
    <p><strong>Slack sent:</strong> ${headline.slackSentTotal ?? '—'} · <strong>Email sent:</strong> ${headline.emailSentTotal ?? '—'} · <strong>Email received:</strong> ${headline.emailReceivedTotal ?? '—'}</p>
    <p><strong>Tokens today:</strong> ${headline.tokensToday ?? '—'} · <strong>Trend vs yesterday:</strong> ${headline.trendVsYesterdayPct ?? '—'}%</p>
  `;

  const insights = document.getElementById('insights');
  (data.insights || []).forEach(item => {
    const li = document.createElement('li');
    li.textContent = item;
    insights.appendChild(li);
  });

  const jobs = document.getElementById('jobs');
  (data.nextJobs || []).forEach(job => {
    const li = document.createElement('li');
    const when = job.nextRunAtMs ? new Date(job.nextRunAtMs).toLocaleString() : 'unknown';
    li.textContent = `${job.name} — ${job.status} — next: ${when}`;
    jobs.appendChild(li);
  });

  const activity = document.getElementById('activity');
  const items = (data.activity || {}).items || [];
  if (!items.length) {
    const li = document.createElement('li');
    li.textContent = 'No verified activity logged yet today.';
    activity.appendChild(li);
  } else {
    items.forEach(item => {
      const li = document.createElement('li');
      li.textContent = item;
      activity.appendChild(li);
    });
  }
}

loadCockpit().catch(err => {
  document.getElementById('headline').textContent = `Failed to load cockpit: ${err}`;
});
