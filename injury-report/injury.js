async function main(){
  const fmt = new Intl.DateTimeFormat(undefined,{year:'numeric',month:'short',day:'2-digit',hour:'numeric',minute:'2-digit',timeZoneName:'short'});
  const r = await fetch('data/overview.json?ts='+Date.now());
  const d = await r.json();
  document.getElementById('updated').textContent = 'Last updated: '+fmt.format(new Date(d.generatedAt));
  document.getElementById('overview').innerHTML = `<b>Total reports:</b> ${d.totalReports}`;
  const ul = document.getElementById('teams'); ul.innerHTML='';
  for(const t of d.teams){
    const li=document.createElement('li');
    const when=t.latest?.sentAt?fmt.format(new Date(t.latest.sentAt)):'n/a';
    li.innerHTML = `<a href='teams/${t.slug}.html'>${t.team}</a> — ${t.count} reports, latest: ${when}`;
    ul.appendChild(li);
  }
}
main().catch(e=>{document.getElementById('updated').textContent='Failed: '+e});
