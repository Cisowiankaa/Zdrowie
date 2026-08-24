function dashboard(){
  title('Dzisiaj',`Centrum dnia — ${activeName()}.`);
  const meds=byProfile('medications');
  const appointments=byProfile('appointments').filter(x=>x.date&&new Date(x.date)>=new Date()).sort((a,b)=>a.date.localeCompare(b.date));
  const measurements=byProfile('measurements').filter(x=>x.date).sort((a,b)=>b.date.localeCompare(a.date));
  const low=meds.filter(x=>Number(x.stock||0)<=Number(x.threshold||5));
  const alertsNow=buildAlerts();
  const latest=measurements[0];
  const next=appointments[0];
  const medsToday=meds.slice(0,6);
  const fmtDate=v=>v?new Date(v).toLocaleString('pl-PL',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';
  const latestText=latest?[latest.bp&&`Ciśnienie ${latest.bp}`,latest.pulse&&`Puls ${latest.pulse}`,latest.glucose&&`Glukoza ${latest.glucose}`,latest.weight&&`Masa ${latest.weight} kg`,latest.spo2&&`SpO₂ ${latest.spo2}%`].filter(Boolean).join(' • '):'Brak pomiarów';
  document.getElementById('content').innerHTML=`
    <div class="today-grid">
      <button class="today-stat" data-go="medications"><span class="today-icon">💊</span><span><small>Aktywne leki</small><strong>${meds.length}</strong><em>${low.length?`${low.length} wymaga uwagi`:'Zapasy bez alertu'}</em></span></button>
      <button class="today-stat" data-go="appointments"><span class="today-icon">📅</span><span><small>Najbliższa wizyta</small><strong class="today-text">${next?fmtDate(next.date):'Brak'}</strong><em>${next?esc(next.title||'Wizyta'):'Nic nie zaplanowano'}</em></span></button>
      <button class="today-stat" data-go="measurements"><span class="today-icon">❤️</span><span><small>Ostatni pomiar</small><strong class="today-text">${latest?fmtDate(latest.date):'Brak'}</strong><em>${esc(latestText)}</em></span></button>
      <button class="today-stat ${alertsNow.length?'today-danger':''}" data-go="alerts"><span class="today-icon">🔔</span><span><small>Aktywne alerty</small><strong>${alertsNow.length}</strong><em>${alertsNow.length?'Sprawdź wymagające uwagi':'Wszystko spokojnie'}</em></span></button>
    </div>

    <div class="dashboard-columns">
      <section class="panel dashboard-main">
        <div class="section-head"><div><h3>Najbliższe zdarzenia</h3><p>Wizyty i terminy dla aktywnego profilu.</p></div><button class="secondary" data-go="calendar">Oś czasu</button></div>
        ${appointments.length?`<div class="event-list">${appointments.slice(0,5).map(x=>`<button class="event-row" data-go="appointments"><span class="event-date">${fmtDate(x.date)}</span><span class="event-body"><b>${esc(x.title||'Wizyta')}</b><small>${esc([x.doctor,x.location].filter(Boolean).join(' • ')||'Bez dodatkowych informacji')}</small></span><span>›</span></button>`).join('')}</div>`:'<div class="empty compact">Brak zaplanowanych wizyt.</div>'}
      </section>

      <section class="panel dashboard-side">
        <div class="section-head"><div><h3>Szybkie akcje</h3><p>Najczęstsze czynności.</p></div></div>
        <div class="quick-dashboard">
          <button id="dashAddMed">+ Lek</button>
          <button id="dashAddVisit">+ Wizyta</button>
          <button id="dashAddMeasure">+ Pomiar</button>
          <button class="secondary" data-go="documents">Dokumentacja</button>
          <button class="secondary" data-go="report">Raport PDF</button>
          <button class="secondary" data-go="patient">Karta pacjenta</button>
        </div>
      </section>
    </div>

    <div class="dashboard-columns lower">
      <section class="panel dashboard-main">
        <div class="section-head"><div><h3>Leki i zapasy</h3><p>Najważniejsze informacje o lekach.</p></div><button class="secondary" data-go="medications">Wszystkie leki</button></div>
        ${medsToday.length?`<div class="mini-list">${medsToday.map(x=>{const isLow=Number(x.stock||0)<=Number(x.threshold||5);return `<div class="mini-row ${isLow?'mini-alert':''}"><span><b>${esc(x.name||'Lek')}</b><small>${esc([x.dose,x.times&&`${x.times}× dziennie`].filter(Boolean).join(' • ')||'Brak dawkowania')}</small></span><span class="stock-pill">${esc(x.stock||'0')} szt.</span></div>`}).join('')}</div>`:'<div class="empty compact">Brak zapisanych leków.</div>'}
      </section>

      <section class="panel dashboard-side">
        <div class="section-head"><div><h3>Ostatni pomiar</h3><p>${latest?fmtDate(latest.date):'Brak danych'}</p></div><button class="secondary" data-go="measurements">Historia</button></div>
        ${latest?`<div class="measure-grid"><div><small>Ciśnienie</small><b>${esc(latest.bp||'—')}</b></div><div><small>Puls</small><b>${esc(latest.pulse||'—')}</b></div><div><small>Glukoza</small><b>${esc(latest.glucose||'—')}</b></div><div><small>Masa</small><b>${esc(latest.weight||'—')}</b></div><div><small>SpO₂</small><b>${esc(latest.spo2||'—')}</b></div></div>`:'<div class="empty compact">Dodaj pierwszy pomiar.</div>'}
      </section>
    </div>`;

  document.querySelectorAll('[data-go]').forEach(el=>el.onclick=()=>{current=el.dataset.go;render();});
  document.getElementById('dashAddMed').onclick=()=>formModal('medications','Leki',[{k:'name',label:'Nazwa leku'},{k:'dose',label:'Dawka'},{k:'times',label:'Ile razy dziennie',type:'number'},{k:'stock',label:'Stan zapasu',type:'number'},{k:'threshold',label:'Próg alarmowy',type:'number'}]);
  document.getElementById('dashAddVisit').onclick=()=>formModal('appointments','Wizyty',[{k:'date',label:'Termin',type:'datetime-local'},{k:'title',label:'Nazwa wizyty'},{k:'doctor',label:'Lekarz'},{k:'location',label:'Miejsce'}]);
  document.getElementById('dashAddMeasure').onclick=()=>formModal('measurements','Pomiary',[{k:'date',label:'Data i godzina',type:'datetime-local'},{k:'bp',label:'Ciśnienie np. 120/80'},{k:'pulse',label:'Puls',type:'number'},{k:'glucose',label:'Glukoza'},{k:'weight',label:'Masa kg'},{k:'spo2',label:'SpO₂ %'}]);
}
