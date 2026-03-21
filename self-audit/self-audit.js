async function main(){
  const fmt = new Intl.DateTimeFormat(undefined,{year:'numeric',month:'short',day:'2-digit',hour:'numeric',minute:'2-digit',second:'2-digit',timeZoneName:'short'});
  const r = await fetch('data/overview.json?ts='+Date.now());
  const d = await r.json();
  document.getElementById('updated').textContent = 'Last updated: '+fmt.format(new Date(d.generatedAt));

  const j=d.job||{};
  const sched=j.schedule||{};
  const lastRun = j.lastRunAtMs ? fmt.format(new Date(j.lastRunAtMs)) : 'n/a';
  const nextRun = j.nextRunAtMs ? fmt.format(new Date(j.nextRunAtMs)) : 'n/a';
  document.getElementById('job').innerHTML = `
    <b>Job:</b> ${d.jobName || ''}<br>
    <b>Enabled:</b> ${j.enabled ? 'yes' : 'no'}<br>
    <b>Schedule:</b> ${sched.kind || ''}${sched.expr ? ` (${sched.expr}${sched.tz ? ', '+sched.tz : ''})` : ''}<br>
    <b>Last status:</b> ${j.lastStatus || 'n/a'}<br>
    <b>Last run:</b> ${lastRun}<br>
    <b>Next run:</b> ${nextRun}<br>
    <b>Consecutive errors:</b> ${j.consecutiveErrors ?? 0}
  `;

  const s=d.runSummary||{};
  document.getElementById('summary').innerHTML = `
    <b>Run summary (last ${s.total ?? 0}):</b><br>
    ok: ${s.ok ?? 0} &nbsp; error: ${s.error ?? 0} &nbsp; other: ${s.other ?? 0}
  `;

  const tb = document.getElementById('runs'); tb.innerHTML='';
  for (const e of d.recentRuns||[]) {
    const tr=document.createElement('tr');
    tr.innerHTML = `<td>${e.runAtMs?fmt.format(new Date(e.runAtMs)):''}</td><td>${e.status||''}</td><td>${e.durationMs ?? ''}</td><td>${e.error || ''}</td>`;
    tb.appendChild(tr);
  }

  if (!(d.recentRuns||[]).length) {
    const tr=document.createElement('tr');
    tr.innerHTML = `<td colspan='4'>No runs found yet.</td>`;
    tb.appendChild(tr);
  }
}
main().catch(e=>{document.getElementById('updated').textContent='Failed: '+e});
