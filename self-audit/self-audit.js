async function main(){
  const fmt = new Intl.DateTimeFormat(undefined,{year:'numeric',month:'short',day:'2-digit',hour:'numeric',minute:'2-digit',second:'2-digit',timeZoneName:'short'});
  const r = await fetch('data/overview.json?ts='+Date.now());
  const d = await r.json();
  document.getElementById('updated').textContent = 'Last updated: '+fmt.format(new Date(d.generatedAt));

  const h=d.health||{};
  const hc=h.checks||{};
  document.getElementById('health').innerHTML = `
    <b>Overall health:</b> <span class="${h.overall||'ok'}">${(h.overall||'ok').toUpperCase()}</span><br>
    <b>Checks:</b> pass ${hc.pass ?? 0} / warn ${hc.warn ?? 0} / fail ${hc.fail ?? 0} (total ${hc.total ?? 0})<br>
    <b>Issues found:</b> ${h.issuesFound ?? 0}<br>
    <b>Actions taken:</b> ${h.actionsTaken ?? 0} &nbsp; <b>Actions pending:</b> ${h.actionsPending ?? 0}<br>
    <b>Cron jobs:</b> ${h.cron?.enabledJobs ?? 0} enabled of ${h.cron?.totalJobs ?? 0}
  `;

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

  const checksBody = document.getElementById('checks'); checksBody.innerHTML='';
  for (const c of d.checksPerformed||[]) {
    const tr=document.createElement('tr');
    const cls = c.status === 'fail' ? 'critical' : (c.status === 'warn' ? 'warning' : 'ok');
    tr.innerHTML = `<td>${c.name||''}</td><td class="${cls}">${(c.status||'').toUpperCase()}</td><td>${c.detail||''}</td>`;
    checksBody.appendChild(tr);
  }
  if (!(d.checksPerformed||[]).length) {
    const tr=document.createElement('tr'); tr.innerHTML = `<td colspan='3'>No checks recorded.</td>`; checksBody.appendChild(tr);
  }

  const findingsBody = document.getElementById('findings'); findingsBody.innerHTML='';
  for (const f of d.driftAndContradictions||[]) {
    const tr=document.createElement('tr');
    const sev = (f.severity||'info').toLowerCase();
    const cls = sev === 'critical' ? 'critical' : (sev === 'warning' ? 'warning' : 'ok');
    tr.innerHTML = `<td class="${cls}">${sev.toUpperCase()}</td><td>${f.text||''}</td>`;
    findingsBody.appendChild(tr);
  }
  if (!(d.driftAndContradictions||[]).length) {
    const tr=document.createElement('tr'); tr.innerHTML = `<td colspan='2'>No findings detected.</td>`; findingsBody.appendChild(tr);
  }

  const actionsBody = document.getElementById('actions'); actionsBody.innerHTML='';
  for (const a of d.correctiveActions||[]) {
    const tr=document.createElement('tr');
    tr.innerHTML = `<td>${a.type||''}</td><td>${a.detail||''}</td>`;
    actionsBody.appendChild(tr);
  }
  if (!(d.correctiveActions||[]).length) {
    const tr=document.createElement('tr'); tr.innerHTML = `<td colspan='2'>No corrective actions listed.</td>`; actionsBody.appendChild(tr);
  }

  document.getElementById('latestText').textContent = d.latestRunSummary?.text || 'No latest summary text available.';

  const jobsBody = document.getElementById('jobs'); jobsBody.innerHTML='';
  for (const j of d.allJobs||[]) {
    const tr=document.createElement('tr');
    tr.innerHTML = `<td>${j.name||''}</td><td>${j.enabled?'yes':'no'}</td><td>${j.lastStatus||''}</td><td>${j.consecutiveErrors ?? 0}</td><td>${j.nextRunAtMs?fmt.format(new Date(j.nextRunAtMs)):''}</td>`;
    jobsBody.appendChild(tr);
  }

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
