async function main(){
  const r = await fetch('status.json?ts='+Date.now());
  const d = await r.json();
  const localFmt = new Intl.DateTimeFormat(undefined, {
    year: 'numeric', month: 'short', day: '2-digit',
    hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true,
    timeZoneName: 'short'
  });
  const generatedLocal = d.generatedAt ? localFmt.format(new Date(d.generatedAt)) : 'unknown';
  const s = d.summary;
  const selfAuditJob = (d.jobs || []).find(j => j.name === 'daily-10am-self-audit');
  let selfAuditState = 'warn';
  if (selfAuditJob) {
    if (selfAuditJob.lastStatus === 'ok' && (selfAuditJob.consecutiveErrors || 0) === 0) selfAuditState = 'ok';
    else if ((selfAuditJob.consecutiveErrors || 0) >= 3 || selfAuditJob.lastStatus === 'error') selfAuditState = 'fail';
    else selfAuditState = 'warn';
  }
  const selfAuditClass = selfAuditState === 'ok' ? 'ok' : (selfAuditState === 'fail' ? 'critical' : 'warning');
  const selfAuditLabel = selfAuditState === 'ok' ? 'OK' : (selfAuditState === 'fail' ? 'FAIL' : 'WARN');

  const overallClass = s.overall === 'ok' ? 'ok' : (s.overall === 'critical' ? 'critical' : 'warning');

  document.getElementById('summary').innerHTML = `
    <div class="summary-wrap">
      <img src="assets/cheesebot.png" alt="CheeseBot avatar" class="avatar" />
      <div>
        <div><span style="display:inline-block;padding:2px 8px;border-radius:999px;border:1px solid #334155;font-size:12px"><b>Overall:</b> <span class="${overallClass}">${s.overall.toUpperCase()}</span></span> &nbsp; <span style="display:inline-block;padding:2px 8px;border-radius:999px;border:1px solid #334155;font-size:12px"><b>Self-Audit:</b> <span class="${selfAuditClass}">${selfAuditLabel}</span></span></div>
        <div style="margin-top:6px"><b>Email sent:</b> ${s.emailSentTotal ?? 0} &nbsp; <b>Email received:</b> ${s.emailReceivedTotal ?? 0} &nbsp; <b>Slack sent:</b> ${s.slackSentTotal ?? 0}</div>
        <div style="margin-top:8px;font-size:12px;color:#94a3b8">Last updated: ${generatedLocal}</div>
      </div>
    </div>
  `;
}
main().catch(e=>{document.getElementById('summary').textContent='Failed to load status.json: '+e;});
