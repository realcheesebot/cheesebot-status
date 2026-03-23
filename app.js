function formatNumber(value){
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return new Intl.NumberFormat().format(value);
}

function formatUsd(value){
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(value);
}

function trendLabel(value){
  if (value === null || value === undefined || Number.isNaN(value)) return 'vs yesterday: n/a';
  const arrow = value > 0 ? '↑' : (value < 0 ? '↓' : '→');
  const cls = value > 0 ? 'warning' : (value < 0 ? 'ok' : '');
  return `<span class="${cls}">${arrow} ${Math.abs(value)}%</span> vs yesterday`;
}

function openclawLabel(u){
  if (!u.openclawVersion && !u.latestOpenclawVersion) return '—';
  const base = u.openclawVersion || 'unknown';
  if (u.updateAvailable && u.latestOpenclawVersion) {
    return `${base} <span class="warning" style="font-size:12px">(Update available: ${u.latestOpenclawVersion})</span>`;
  }
  return base;
}

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
  const u = d.usage || {};
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
    <div class="tagline" style="margin-top:10px">CheeseBot is here to serve and defend. I will help where I can, and offer witty puns when I can't.</div>
  `;

  document.getElementById('usage').innerHTML = `
    <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap">
      <div>
        <h2 style="margin:0">Token Usage</h2>
        <div class="metric-sub">Runtime + model metadata</div>
      </div>
      <div class="metric-sub">${trendLabel(u.trendVsYesterdayPct)}</div>
    </div>
    <div class="metric-grid">
      <div class="metric">
        <div class="metric-label">Today</div>
        <div class="metric-value">${formatNumber(u.tokensToday)}</div>
        <div class="metric-sub">tokens</div>
      </div>
      <div class="metric">
        <div class="metric-label">Last 7 days</div>
        <div class="metric-value">${formatNumber(u.tokens7d)}</div>
        <div class="metric-sub">tokens</div>
      </div>
      <div class="metric">
        <div class="metric-label">Cost today</div>
        <div class="metric-value">${formatUsd(u.estimatedCostTodayUsd)}</div>
        <div class="metric-sub">estimated</div>
      </div>
      <div class="metric">
        <div class="metric-label">Cost 7d</div>
        <div class="metric-value">${formatUsd(u.estimatedCost7dUsd)}</div>
        <div class="metric-sub">estimated</div>
      </div>
      <div class="metric">
        <div class="metric-label">OpenClaw</div>
        <div class="metric-value" style="font-size:16px">${openclawLabel(u)}</div>
        <div class="metric-sub">installed version</div>
      </div>
      <div class="metric">
        <div class="metric-label">AI model</div>
        <div class="metric-value" style="font-size:16px">${u.model || '—'}</div>
        <div class="metric-sub">active session model</div>
      </div>
    </div>
  `;
}
main().catch(e=>{
  document.getElementById('summary').textContent='Failed to load status.json: '+e;
  const usage = document.getElementById('usage');
  if (usage) usage.textContent = 'Failed to load usage metrics.';
});
