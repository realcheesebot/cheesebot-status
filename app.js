async function main(){
  const r = await fetch('status.json?ts='+Date.now());
  const d = await r.json();
  const localFmt = new Intl.DateTimeFormat(undefined, {
    year: 'numeric', month: 'short', day: '2-digit',
    hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true,
    timeZoneName: 'short'
  });
  const generatedLocal = d.generatedAt ? localFmt.format(new Date(d.generatedAt)) : 'unknown';
  document.getElementById('updated').textContent = `Last updated (your local time): ${generatedLocal}`;
  const s = d.summary;
  document.getElementById('summary').innerHTML = `
    <div><b>Overall:</b> <span class="${s.overall}">${s.overall.toUpperCase()}</span></div>
    <div><b>Enabled:</b> ${s.enabledJobs} &nbsp; <b>Disabled:</b> ${s.disabledJobs} &nbsp; <b>Total:</b> ${s.totalJobs}</div>
    <div style="margin-top:6px"><b>Email sent:</b> ${s.emailSentTotal ?? 0} &nbsp; <b>Email received:</b> ${s.emailReceivedTotal ?? 0} &nbsp; <b>Slack sent:</b> ${s.slackSentTotal ?? 0}</div>
  `;
  const tbody = document.querySelector('#jobs tbody');
  tbody.innerHTML = '';
  for(const j of d.jobs){
    const tr = document.createElement('tr');
    const nextRun = j.nextRunAtMs ? localFmt.format(new Date(j.nextRunAtMs)) : '';
    tr.innerHTML = `<td>${j.name||''}</td><td>${j.enabled?'yes':'no'}</td><td>${j.lastStatus||''}</td><td>${j.consecutiveErrors||0}</td><td>${nextRun}</td>`;
    tbody.appendChild(tr);
  }
}
main().catch(e=>{document.getElementById('updated').textContent='Failed to load status.json: '+e;});
