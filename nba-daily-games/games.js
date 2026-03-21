function normalizeStreak(v){
  if (v === null || v === undefined) return '';
  const s = String(v).trim();
  if (!s) return '';

  // Numeric form from feed: +3 / 3 means W3, -5 means L5
  if (/^[+-]?\d+$/.test(s)) {
    const n = parseInt(s, 10);
    if (Number.isNaN(n) || n === 0) return 'W0';
    return `${n > 0 ? 'W' : 'L'}${Math.abs(n)}`;
  }

  // Already in compact form
  if (/^[WwLl]\d+$/.test(s)) return s.toUpperCase();

  // Common forms: "W 3", "L-2", "Won 4", "Lost 1"
  let m = s.match(/\b([WwLl])\s*[-:]?\s*(\d+)\b/);
  if (m) return `${m[1].toUpperCase()}${m[2]}`;
  m = s.match(/\b(Won|Lost)\s*(\d+)\b/i);
  if (m) return `${m[1].toLowerCase().startsWith('w') ? 'W' : 'L'}${m[2]}`;

  return s;
}

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
    tr.innerHTML = `<td>${g.date||''}</td><td>${g.matchup||''}</td><td>${tip}</td>`;
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
      tr.innerHTML = `<td style='text-align:center'>${t.rank ?? ''}</td><td style='text-align:left'>${t.team||''}</td><td style='text-align:center'>${t.wins ?? ''}-${t.losses ?? ''}</td><td style='text-align:center'>${t.gb ?? ''}</td><td style='text-align:center'>${normalizeStreak(t.streak)}</td>`;
      if ((t.team||'').includes('San Antonio') || (t.team||'').includes('Portland')) {
        tr.style.fontWeight='700';
        tr.style.color='#d4a017';
      }
      wb.appendChild(tr);
    }
  }
}
main().catch(e=>{document.getElementById('updated').textContent='Failed: '+e});
