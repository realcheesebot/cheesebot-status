async function main(){
  const fmt = new Intl.DateTimeFormat(undefined,{year:'numeric',month:'short',day:'2-digit',hour:'numeric',minute:'2-digit',timeZoneName:'short'});
  const r = await fetch('data/overview.json?ts='+Date.now());
  const d = await r.json();
  document.getElementById('updated').textContent='Last updated: '+fmt.format(new Date(d.generatedAt));
  const latest=d.latest;
  document.getElementById('latest').innerHTML = latest
    ? `<b>Latest weather report:</b> ${latest.subject || ''}<br><b>Sent:</b> ${fmt.format(new Date((latest.ts||0)*1000))}<br><b>Recipients:</b> ${(latest.recipients||[]).join(', ')}`
    : 'No weather report sends found yet in notifier log.';

  const tb=document.getElementById('rows'); tb.innerHTML='';
  for(const row of d.recent||[]){
    const tr=document.createElement('tr');
    tr.innerHTML=`<td>${fmt.format(new Date((row.ts||0)*1000))}</td><td>${row.subject||''}</td><td>${(row.recipients||[]).join(', ')}</td>`;
    tb.appendChild(tr);
  }
}
main().catch(e=>{document.getElementById('updated').textContent='Failed: '+e});
