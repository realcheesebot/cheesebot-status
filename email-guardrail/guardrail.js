async function main(){
  const fmt = new Intl.DateTimeFormat(undefined,{year:'numeric',month:'short',day:'2-digit',hour:'numeric',minute:'2-digit',second:'2-digit',timeZoneName:'short'});
  const r = await fetch('data/overview.json?ts='+Date.now());
  const d = await r.json();
  document.getElementById('updated').textContent = 'Last updated: '+fmt.format(new Date(d.generatedAt));

  const j=d.job||{};
  const lastRun = j.lastRunAtMs ? fmt.format(new Date(j.lastRunAtMs)) : 'n/a';
  const nextRun = j.nextRunAtMs ? fmt.format(new Date(j.nextRunAtMs)) : 'n/a';
  document.getElementById('job').innerHTML = `
    <b>Job:</b> ${j.name || ''}<br>
    <b>Enabled:</b> ${j.enabled ? 'yes' : 'no'}<br>
    <b>Last status:</b> ${j.lastStatus || 'n/a'}<br>
    <b>Last run:</b> ${lastRun}<br>
    <b>Next run:</b> ${nextRun}<br>
    <b>Consecutive errors:</b> ${j.consecutiveErrors ?? 0}
  `;

  const s=d.emailStateSummary||{};
  document.getElementById('state').innerHTML = `
    <b>Email state summary</b><br>
    messages tracked: ${s.messagesTracked ?? 0}<br>
    threads tracked: ${s.threadsTracked ?? 0}<br>
    seen/acted/replied: ${s.seenCount ?? 0} / ${s.actedCount ?? 0} / ${s.repliedCount ?? 0}<br>
    lastHistoryId: ${s.lastCheckedHistoryId ?? 'n/a'}
  `;

  const received = d.receivedLast24h || [];
  const rcvb = document.getElementById('receivedRows'); rcvb.innerHTML='';
  if (!received.length) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td colspan='5'>No emails were observed in the last 24 hours.</td>`;
    rcvb.appendChild(tr);
  } else {
    for (const r of received) {
      const tr = document.createElement('tr');
      const at = r.seenAt ? fmt.format(new Date(r.seenAt)) : '';
      tr.innerHTML = `<td>${at}</td><td>${r.from || ''}</td><td>${r.subject || ''}</td><td>${r.status || ''}</td><td>${r.messageId || ''}</td>`;
      rcvb.appendChild(tr);
    }
  }

  const rb = document.getElementById('repliedRows'); rb.innerHTML='';
  const replied = d.repliedLast24h || [];
  if (!replied.length) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td colspan='4'>No replies were sent in the last 24 hours.</td>`;
    rb.appendChild(tr);
  } else {
    for (const r of replied) {
      const tr = document.createElement('tr');
      const at = r.repliedAt ? fmt.format(new Date(r.repliedAt)) : '';
      tr.innerHTML = `<td>${at}</td><td>${r.from || ''}</td><td>${r.subject || ''}</td><td>${r.messageId || ''}</td>`;
      rb.appendChild(tr);
    }
  }

  const tb = document.getElementById('runs'); tb.innerHTML='';
  for (const e of d.recentRuns||[]) {
    const tr=document.createElement('tr');
    tr.innerHTML = `<td>${e.runAtMs?fmt.format(new Date(e.runAtMs)):''}</td><td>${e.status||''}</td><td>${e.durationMs ?? ''}</td><td>${e.error || ''}</td>`;
    tb.appendChild(tr);
  }
}
main().catch(e=>{document.getElementById('updated').textContent='Failed: '+e});
