async function main(){
  const fmt = new Intl.DateTimeFormat(undefined,{year:'numeric',month:'short',day:'2-digit',hour:'numeric',minute:'2-digit',timeZoneName:'short'});
  const r = await fetch('data/overview.json?ts='+Date.now());
  const d = await r.json();
  document.getElementById('updated').textContent='Last updated: '+fmt.format(new Date(d.generatedAt));
  document.getElementById('summary').innerHTML = `<b>Games listed:</b> ${d.count} (today + tomorrow)`;
  const tb=document.getElementById('rows'); tb.innerHTML='';
  const games = [...(d.games||[])].sort((a,b)=>{
    const aFav = /(^|@)(SAS|POR)($|@)/.test(a.matchup||'') ? 1 : 0;
    const bFav = /(^|@)(SAS|POR)($|@)/.test(b.matchup||'') ? 1 : 0;
    if (aFav !== bFav) return bFav - aFav; // favored teams first
    return new Date(a.tipoffUtc||0) - new Date(b.tipoffUtc||0);
  });

  for(const g of games){
    const tr=document.createElement('tr');
    const tip = g.tipoffUtc ? fmt.format(new Date(g.tipoffUtc)) : '';
    const fav = /(^|@)(SAS|POR)($|@)/.test(g.matchup||'');
    tr.innerHTML = `<td>${g.date||''}</td><td>${g.matchup||''}</td><td>${tip}</td><td>${g.arena||''}</td>`;
    if (fav) {
      tr.style.fontWeight = '700';
      tr.style.color = '#d4a017'; // dark yellow/gold
    }
    tb.appendChild(tr);
  }

  const wb=document.getElementById('westRows');
  if (wb) {
    wb.innerHTML='';
    for (const t of d.westStandings||[]) {
      const tr=document.createElement('tr');
      tr.innerHTML = `<td>${t.rank ?? ''}</td><td>${t.team||''}</td><td>${t.wins ?? ''}-${t.losses ?? ''}</td><td>${t.winPct ?? ''}</td>`;
      if ((t.team||'').includes('San Antonio') || (t.team||'').includes('Portland')) {
        tr.style.fontWeight='700';
        tr.style.color='#d4a017';
      }
      wb.appendChild(tr);
    }
  }
}
main().catch(e=>{document.getElementById('updated').textContent='Failed: '+e});
