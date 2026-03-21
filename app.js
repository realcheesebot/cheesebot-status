async function main(){
  const r = await fetch('status.json?ts='+Date.now());
  const d = await r.json();
  document.getElementById('updated').textContent = `Last updated: ${d.generatedAt}`;
  const s = d.summary;
  document.getElementById('summary').innerHTML = `
    <div><b>Overall:</b> <span class="${s.overall}">${s.overall.toUpperCase()}</span></div>
    <div><b>Enabled:</b> ${s.enabledJobs} &nbsp; <b>Disabled:</b> ${s.disabledJobs} &nbsp; <b>Total:</b> ${s.totalJobs}</div>
  `;
  const tbody = document.querySelector('#jobs tbody');
  tbody.innerHTML = '';
  for(const j of d.jobs){
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${j.name||''}</td><td>${j.enabled?'yes':'no'}</td><td>${j.lastStatus||''}</td><td>${j.consecutiveErrors||0}</td><td>${j.nextRunAtMs||''}</td>`;
    tbody.appendChild(tr);
  }
}
main().catch(e=>{document.getElementById('updated').textContent='Failed to load status.json: '+e;});
