async function main(){
  const slug = location.pathname.split('/').pop().replace('.html','');
  const fmt = new Intl.DateTimeFormat(undefined,{year:'numeric',month:'short',day:'2-digit',hour:'numeric',minute:'2-digit',timeZoneName:'short'});
  const r = await fetch(`../data/teams/${slug}.json?ts=`+Date.now());
  const d = await r.json();
  document.getElementById('updated').textContent='Last updated: '+fmt.format(new Date(d.generatedAt));
  const latest=d.latest;
  document.getElementById('latest').innerHTML = latest ? `<b>Latest:</b> ${fmt.format(new Date(latest.sentAt))} — ${latest.matchup}` : 'No data';
  const tb=document.getElementById('rows'); tb.innerHTML='';
  for(const row of d.history||[]){
    const tr=document.createElement('tr');
    tr.innerHTML=`<td>${row.sentAt?fmt.format(new Date(row.sentAt)):''}</td><td>${row.matchup||''}</td><td>${(row.recipients||[]).join(', ')}</td>`;
    tb.appendChild(tr);
  }
}
main().catch(e=>{document.getElementById('updated').textContent='Failed: '+e});
