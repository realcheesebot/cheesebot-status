async function main(){
  const fmt = new Intl.DateTimeFormat(undefined,{year:'numeric',month:'short',day:'2-digit',hour:'numeric',minute:'2-digit',timeZoneName:'short'});
  const r = await fetch('data/overview.json?ts='+Date.now());
  const d = await r.json();
  document.getElementById('updated').textContent='Last updated: '+fmt.format(new Date(d.generatedAt));
  document.getElementById('summary').innerHTML = `<b>Games listed:</b> ${d.count} (today + tomorrow)`;
  const tb=document.getElementById('rows'); tb.innerHTML='';
  for(const g of d.games||[]){
    const tr=document.createElement('tr');
    const tip = g.tipoffUtc ? fmt.format(new Date(g.tipoffUtc)) : '';
    tr.innerHTML = `<td>${g.date||''}</td><td>${g.matchup||''}</td><td>${tip}</td><td>${g.arena||''}</td>`;
    tb.appendChild(tr);
  }
}
main().catch(e=>{document.getElementById('updated').textContent='Failed: '+e});
